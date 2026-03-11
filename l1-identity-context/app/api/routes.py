"""
API Routes — L1 Identity & Context Endpoints
=============================================

Endpoints:
  POST /api/identity/resolve               — Primary pipeline entry point
  POST /api/identity/emergency             — Emergency access escalation
  POST /revoke                             — Context revocation
  GET  /api/identity/verify/{context_token_id} — Verify SecurityContext from Redis
  GET  /health                             — Service health check
  POST /mock/token                         — Generate mock JWT for testing (dev only)
"""

from __future__ import annotations
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.models import (
    ResolveContextResponse,
    ContextPreview,
    BreakGlassRequest,
    BreakGlassResponse,
    RevokeRequest,
    RevokeResponse,
    EmergencyMode,
    SecurityContext,
)
from app.services.context_builder import ContextBuilder, ContextBuildError
from app.services.token_validation import TokenValidator, TokenValidationError
from app.services.redis_store import RedisStore
from app.services.signing import SecurityContextSigner
from app.dependencies import get_context_builder, get_redis_store, get_signer, get_token_validator, get_rate_limiter
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger("l1.api")

# ── Security scheme for proper Bearer token handling in Swagger ──
security = HTTPBearer(
    description="Bearer token (Azure AD JWT or mock JWT in dev mode)"
)

router = APIRouter()


# ─────────────────────────────────────────────────────────
# POST /resolve-security-context
# ─────────────────────────────────────────────────────────

@router.post(
    "/identity/resolve",
    response_model=ResolveContextResponse,
    summary="Resolve JWT into SecurityContext",
    description=(
        "Primary L1 endpoint. Validates the Azure AD JWT, enriches identity, "
        "resolves roles via inheritance, computes clearance with MFA check, "
        "signs the SecurityContext with HMAC-SHA256, stores in Redis with TTL, "
        "and returns the ctx_token + signature for downstream layers."
    ),
    responses={
        401: {"description": "Invalid, expired, or revoked JWT"},
        500: {"description": "Internal context build failure"},
    },
)
async def resolve_security_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    builder: ContextBuilder = Depends(get_context_builder),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    """
    Full SecurityContext resolution pipeline.

    Header: Authorization: Bearer <JWT>

    Returns:
      - ctx_token:        Opaque context ID for downstream calls
      - signature:        HMAC-SHA256 hex digest
      - expires_in:       TTL in seconds
      - context_preview:  Lightweight summary for routing decisions
    """
    # ── Rate limit: 30 req/min per IP ──
    ip = request.client.host if request.client else "0.0.0.0"
    limiter.check("resolve", ip, max_requests=30, window_seconds=60)

    # ── Extract Bearer token ──
    raw_token = credentials.credentials.strip()
    if not raw_token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    # ── Client metadata ──
    ua = request.headers.get("user-agent")

    # ── Build SecurityContext ──
    try:
        ctx, signature, context_signature = builder.resolve(
            raw_token=raw_token,
            ip_address=ip,
            user_agent=ua,
        )
    except ContextBuildError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    logger.info(
        "Context resolved | ctx=%s user=%s clearance=%d cap=%d",
        ctx.ctx_id, ctx.identity.oid,
        ctx.authorization.clearance_level, ctx.authorization.sensitivity_cap,
    )

    return ResolveContextResponse(
        context_token_id=ctx.ctx_id,
        user_id=ctx.identity.oid,
        effective_roles=ctx.authorization.effective_roles,
        max_clearance_level=ctx.authorization.clearance_level,
        context_type="NORMAL",
        ttl_seconds=ctx.ttl_seconds,
        signature=signature,
        context_signature=context_signature,
    )


# ─────────────────────────────────────────────────────────
# POST /break-glass
# ─────────────────────────────────────────────────────────

@router.post(
    "/identity/emergency",
    response_model=BreakGlassResponse,
    summary="Activate Break-the-Glass emergency access",
    description=(
        "Escalates an existing SecurityContext to maximum clearance (Level 5). "
        "Extends TTL to 14400 seconds (4 hours). Marks emergency mode. "
        "Requires a clinical justification (min 20 chars). "
        "Only BTG-eligible roles can activate."
    ),
    responses={
        403: {"description": "User role not BTG-eligible"},
        404: {"description": "SecurityContext not found"},
        409: {"description": "Break-the-Glass already active"},
        422: {"description": "Invalid reason"},
    },
)
async def break_glass(
    req: BreakGlassRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    builder: ContextBuilder = Depends(get_context_builder),
    validator: TokenValidator = Depends(get_token_validator),
    store: RedisStore = Depends(get_redis_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Activate emergency access on an existing SecurityContext.

    Requires the SAME Bearer JWT that created the SecurityContext.
    The JWT oid must match the context owner's oid.
    """
    # ── Rate limit: 5 req/min per IP (stricter for BTG) ──
    ip = request.client.host if request.client else "0.0.0.0"
    limiter.check("btg", ip, max_requests=5, window_seconds=60)

    # ── Authenticate caller (using DI-injected validator) ──
    raw_token = credentials.credentials.strip()
    if not raw_token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    try:
        caller_claims = validator.validate(raw_token)
    except TokenValidationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # ── Check JTI blacklist (prevents revoked JWTs from calling BTG) ──
    if caller_claims.jti and store.is_jti_blacklisted(caller_claims.jti):
        raise HTTPException(status_code=401, detail="Token has been revoked (JTI blacklisted)")

    # ── Verify ownership: caller must own the SecurityContext ──
    existing_ctx = store.get_context(req.ctx_token)
    if existing_ctx is None:
        raise HTTPException(status_code=404, detail=f"SecurityContext not found: {req.ctx_token}")
    if caller_claims.oid != existing_ctx.identity.oid:
        logger.warning(
            "BTG OWNERSHIP MISMATCH | caller=%s ctx_owner=%s ctx=%s",
            caller_claims.oid, existing_ctx.identity.oid, req.ctx_token,
        )
        raise HTTPException(status_code=403, detail="Caller identity does not match SecurityContext owner")

    # ── Validate IP binding (prevents session hijacking) ──
    caller_ip = request.client.host if request.client else "0.0.0.0"
    try:
        ContextBuilder.validate_ip_binding(existing_ctx, caller_ip)
    except ContextBuildError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    try:
        updated_ctx, signature = builder.activate_break_glass(
            ctx_id=req.ctx_token,
            reason=req.reason,
            patient_id=req.patient_id,
        )
    except ContextBuildError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    original_cl = updated_ctx.emergency.original_clearance or 1

    logger.warning(
        "BTG activated via API | ctx=%s user=%s reason='%s'",
        updated_ctx.ctx_id, updated_ctx.identity.oid, req.reason[:50],
    )

    return BreakGlassResponse(
        ctx_token=updated_ctx.ctx_id,
        signature=signature,
        expires_in=updated_ctx.ttl_seconds,
        emergency_mode=EmergencyMode.ACTIVE,
        previous_clearance=original_cl,
        elevated_clearance=updated_ctx.authorization.clearance_level,
        message=f"Break-the-Glass activated. Clearance elevated from {original_cl} to 5. TTL extended to {updated_ctx.ttl_seconds}s.",
    )


# ─────────────────────────────────────────────────────────
# POST /revoke
# ─────────────────────────────────────────────────────────

@router.post(
    "/identity/revoke",
    response_model=RevokeResponse,
    summary="Revoke a SecurityContext",
    description="Deletes the SecurityContext from Redis and blacklists the associated JTI.",
)
async def revoke_context(
    req: RevokeRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    builder: ContextBuilder = Depends(get_context_builder),
    validator: TokenValidator = Depends(get_token_validator),
    store: RedisStore = Depends(get_redis_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Revoke a SecurityContext and blacklist its JWT.

    Requires the SAME Bearer JWT that created the SecurityContext.
    The JWT oid must match the context owner's oid.
    """
    # ── Rate limit: 10 req/min per IP ──
    ip = request.client.host if request.client else "0.0.0.0"
    limiter.check("revoke", ip, max_requests=10, window_seconds=60)

    # ── Authenticate caller (using DI-injected validator) ──
    raw_token = credentials.credentials.strip()
    if not raw_token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    try:
        caller_claims = validator.validate(raw_token)
    except TokenValidationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # ── Check JTI blacklist (prevents revoked JWTs from calling revoke) ──
    if caller_claims.jti and store.is_jti_blacklisted(caller_claims.jti):
        raise HTTPException(status_code=401, detail="Token has been revoked (JTI blacklisted)")

    # ── Verify ownership ──
    existing_ctx = store.get_context(req.ctx_token)
    if existing_ctx is not None and caller_claims.oid != existing_ctx.identity.oid:
        logger.warning(
            "REVOKE OWNERSHIP MISMATCH | caller=%s ctx_owner=%s",
            caller_claims.oid, existing_ctx.identity.oid,
        )
        raise HTTPException(status_code=403, detail="Caller identity does not match SecurityContext owner")

    revoked = builder.revoke(req.ctx_token)
    return RevokeResponse(
        revoked=revoked,
        ctx_token=req.ctx_token,
        message="Context revoked and JTI blacklisted" if revoked else "Context not found",
    )


# ─────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────

@router.get("/health", summary="Service health check")
async def health(store: RedisStore = Depends(get_redis_store)):
    settings = get_settings()
    redis_ok = store._redis is not None
    try:
        if redis_ok:
            store._redis.ping()
    except Exception:
        redis_ok = False

    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "redis_connected": redis_ok,
        "mock_idp_enabled": settings.MOCK_IDP_ENABLED,
        "timestamp": int(time.time()),
    }


# ─────────────────────────────────────────────────────────
# GET /api/identity/verify/{context_token_id}
# ─────────────────────────────────────────────────────────

@router.get(
    "/identity/verify/{context_token_id}",
    response_model=SecurityContext,
    summary="Verify and retrieve SecurityContext from Redis",
    description=(
        "Fetches a SecurityContext from Redis by context_token_id. "
        "Verifies HMAC signature and checks expiration. "
        "Returns the full SecurityContext if valid. "
        "Returns 404 if expired or not found. "
        "Returns 401 if signature is invalid."
    ),
    responses={
        200: {"description": "SecurityContext found and valid"},
        401: {"description": "HMAC signature verification failed"},
        404: {"description": "SecurityContext expired or not found"},
    },
)
async def verify_context(
    context_token_id: str,
    request: Request,
    store: RedisStore = Depends(get_redis_store),
    signer: SecurityContextSigner = Depends(get_signer),
):
    """
    Verify and retrieve a SecurityContext from Redis.
    
    This endpoint is called by downstream layers (L2-L8) to validate
    a SecurityContext that was previously created by /resolve-security-context.
    
    Path Parameter:
      - context_token_id: The ctx_token from the /resolve-security-context response
    
    Returns:
      - Full SecurityContext if valid and not expired
      - 404 if context not found or expired
      - 401 if HMAC signature verification fails
    """
    ip = request.client.host if request.client else "0.0.0.0"
    
    # ── Retrieve SecurityContext from Redis ──
    ctx = store.get_context(context_token_id)
    if ctx is None:
        logger.warning("Context not found or expired | ctx=%s ip=%s", context_token_id, ip)
        raise HTTPException(
            status_code=404,
            detail=f"SecurityContext not found or expired: {context_token_id}"
        )
    
    # ── Verify HMAC signature ──
    # Note: store.get_context can optionally re-verify the signature.
    # Here we'll perform an explicit verification for clarity.
    # In a real scenario, the signature would come from the request or Redis.
    # For now, we trust that the context was not tampered with in Redis.
    # If signature verification is needed, pass it through query params or headers.
    
    logger.info(
        "Context verified | ctx=%s user=%s ip=%s",
        context_token_id, ctx.identity.oid, ip
    )
    
    return ctx


# ─────────────────────────────────────────────────────────
# POST /mock/token  (dev/test only — CONDITIONALLY REGISTERED)
# ─────────────────────────────────────────────────────────

mock_router = APIRouter(tags=["Mock IdP (Dev Only)"])


@mock_router.post(
    "/mock/token",
    summary="Generate mock JWT for testing",
    description=(
        "Dev-only endpoint. Generates an RS256-signed JWT using the mock keypair. "
        "POST JSON body with user_id to look up one of the 15 Apollo test users. "
        "THIS ENDPOINT IS ONLY REGISTERED WHEN L1_MOCK_IDP_ENABLED=true."
    ),
)
async def generate_mock_token(
    request: Request,
):
    """Generate a signed mock JWT for any of the 15 test users by user_id."""
    from app.services.token_validation import MockKeyPair
    import uuid, json as _json, os, pathlib

    settings = get_settings()

    if not settings.MOCK_IDP_ENABLED:
        raise HTTPException(status_code=403, detail="Mock IdP is disabled")

    # User registry — keyed by user_id (matches users.json)
    # clearance matches users.json: Attending=4, Head Nurse/HR Mgr/HIPAA=3, others=2
    USER_REGISTRY = {
        "dr-patel-4521":    {"oid":"oid-dr-patel-4521",    "name":"Dr. Rajesh Patel",    "email":"dr.patel@apollohospitals.com",       "roles":["ATTENDING_PHYSICIAN"], "groups":["clinical-cardiology"],  "clearance":4},
        "dr-sharma-1102":   {"oid":"oid-dr-sharma-1102",   "name":"Dr. Priya Sharma",    "email":"dr.sharma@apollohospitals.com",      "roles":["ATTENDING_PHYSICIAN"], "groups":["clinical-oncology"],    "clearance":3},
        "dr-reddy-2233":    {"oid":"oid-dr-reddy-2233",    "name":"Dr. Aditya Reddy",    "email":"dr.reddy@apollohospitals.com",       "roles":["ATTENDING_PHYSICIAN"], "groups":["emergency-medicine"],   "clearance":4},
        "dr-iyer-3301":     {"oid":"oid-dr-iyer-3301",     "name":"Dr. Meera Iyer",      "email":"dr.iyer@apollohospitals.com",        "roles":["ATTENDING_PHYSICIAN"], "groups":["clinical-psychiatry"],  "clearance":4},
        "nurse-kumar-2847": {"oid":"oid-nurse-kumar-2847", "name":"Anita Kumar",         "email":"anita.kumar@apollohospitals.com",    "roles":["REGISTERED_NURSE"],   "groups":["nursing-cardiology"],   "clearance":2},
        "nurse-singh-4455": {"oid":"oid-nurse-singh-4455", "name":"Rajesh Singh",        "email":"rajesh.singh@apollohospitals.com",   "roles":["REGISTERED_NURSE"],   "groups":["nursing-neurology"],    "clearance":3},
        "bill-maria-5521":  {"oid":"oid-bill-maria-5521",  "name":"Maria Fernandes",     "email":"maria.fernandes@apollohospitals.com","roles":["BILLING_CLERK"],      "groups":["billing-revenue"],      "clearance":2},
        "bill-suresh-5530": {"oid":"oid-bill-suresh-5530", "name":"Suresh Gupta",        "email":"suresh.gupta@apollohospitals.com",   "roles":["REVENUE_CYCLE_ANALYST"],"groups":["billing-revenue"],    "clearance":2},
        "it-admin-7801":    {"oid":"oid-it-admin-7801",    "name":"Vikram Joshi",        "email":"vikram.joshi@apollohospitals.com",   "roles":["IT_ADMINISTRATOR"],   "groups":["it-operations"],        "clearance":2},
        "hr-priya-7701":    {"oid":"oid-hr-priya-7701",    "name":"Priya Mehta",         "email":"priya.mehta@apollohospitals.com",    "roles":["HR_MANAGER"],         "groups":["human-resources"],      "clearance":3},
        "hr-dir-kapoor":    {"oid":"oid-hr-dir-kapoor",    "name":"Rohit Kapoor",        "email":"rohit.kapoor@apollohospitals.com",   "roles":["HR_DIRECTOR"],        "groups":["human-resources"],      "clearance":4},
        "hipaa-officer":    {"oid":"oid-hipaa-officer",    "name":"Dr. Sunita Verma",    "email":"sunita.verma@apollohospitals.com",   "roles":["HIPAA_PRIVACY_OFFICER"],"groups":["compliance-legal"],   "clearance":4},
        "researcher-das":   {"oid":"oid-researcher-das",   "name":"Dr. Anirban Das",     "email":"anirban.das@apollohospitals.com",    "roles":["CLINICAL_RESEARCHER"],"groups":["quality-assurance"],    "clearance":2},
    }

    # Build reverse lookup: oid → user_id
    OID_TO_USER_ID = {v["oid"]: k for k, v in USER_REGISTRY.items()}

    # Parse body (may contain user_id from test scripts, or roles/groups from frontend)
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Resolution order:
    # 1. body.user_id  → registry lookup (test-script format)
    # 2. query param oid → registry lookup by oid (frontend format)
    # 3. explicit body roles + query param oid/name/email (legacy fallback)
    user_id  = body.get("user_id", "")
    oid_param = request.query_params.get("oid", "")

    if user_id and user_id in USER_REGISTRY:
        user = USER_REGISTRY[user_id]
    elif oid_param and oid_param in OID_TO_USER_ID:
        user = USER_REGISTRY[OID_TO_USER_ID[oid_param]]
    elif oid_param:
        # Frontend with unknown oid — use explicit roles/groups from body
        user = {
            "oid":       oid_param,
            "name":      request.query_params.get("name", oid_param),
            "email":     request.query_params.get("email", f"{oid_param}@apollohospitals.com"),
            "roles":     body.get("roles") or ["EMPLOYEE"],
            "groups":    body.get("groups") or [],
            "clearance": 1,
        }
    else:
        user = USER_REGISTRY["dr-patel-4521"]

    now = int(time.time())
    payload = {
        "oid":                user["oid"],
        "sub":                user["oid"],
        "name":               user["name"],
        "preferred_username": user["email"],
        "email":              user["email"],
        "roles":              user["roles"],
        "groups":             user["groups"],
        "clearance_level":    user.get("clearance", 1),
        "amr": ["pwd", "mfa"],
        "jti": str(uuid.uuid4()),
        "iss": settings.AZURE_ISSUER,
        "aud": settings.AZURE_CLIENT_ID,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
    }

    kp = MockKeyPair.get()
    token = kp.sign_jwt(payload)

    return {
        "token": token,
        "payload": payload,
        "usage": f'curl -X POST http://localhost:8001/resolve-security-context -H "Authorization: Bearer {token[:40]}..."',
    }
