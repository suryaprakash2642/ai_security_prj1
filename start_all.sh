#!/bin/bash
# ============================================================
# Apollo Hospitals Zero Trust NL-to-SQL — Start All Services
# ============================================================
# Starts L1-L8 in background and serves the frontend on :3000
# Usage: ./start_all.sh
# Stop:  ./stop_all.sh
# ============================================================

BASE="/Users/apple/Documents/projects/ai_security"
LOG_DIR="$BASE/logs"
mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()  { echo -e "${GREEN}[START]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN ]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# PID file for stop script
PID_FILE="$BASE/.service_pids"
> "$PID_FILE"

port_in_use() { lsof -ti tcp:"$1" > /dev/null 2>&1; }

start_service() {
  local name="$1"
  local dir="$2"
  local venv="$3"       # .venv or venv or "system"
  local module="$4"     # python module e.g. app.main:app
  local port="$5"

  # Skip if already running on that port
  if port_in_use "$port"; then
    info "$name already running on port $port — skipping"
    return 0
  fi

  # Resolve python binary
  local python
  if [ "$venv" = "system" ]; then
    python=$(which python3)
  else
    python="$dir/$venv/bin/python"
  fi

  if [ ! -f "$python" ]; then
    warn "$name: venv not found at $dir/$venv"
    warn "  Fix: cd $dir && python3 -m venv $venv && $venv/bin/pip install -r requirements.txt"
    return 1
  fi

  info "Starting $name on port $port…"
  cd "$dir"
  # L4 needs Neo4j cloud credentials (Aura) passed as env vars
  if [ "$port" = "8400" ]; then
    NEO4J_URI="neo4j+s://5ddec823.databases.neo4j.io" \
    NEO4J_USER="5ddec823" \
    NEO4J_PASSWORD="ONSdw4TWjQSwIhR_0edgqxvNF0JS-4dw7df4nxXeiec" \
    "$python" -m uvicorn "$module" --host 0.0.0.0 --port "$port" \
      >> "$LOG_DIR/${name}.log" 2>&1 &
  else
    "$python" -m uvicorn "$module" --host 0.0.0.0 --port "$port" \
      >> "$LOG_DIR/${name}.log" 2>&1 &
  fi
  local pid=$!
  echo "$pid $name" >> "$PID_FILE"
  echo "  PID $pid → $LOG_DIR/${name}.log"
  sleep 0.3
}

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║    Apollo Hospitals Zero Trust NL-to-SQL Pipeline    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Layer services ─────────────────────────────────────────
start_service "L1-identity"    "$BASE/l1-identity-context"    ".venv"   "app.main:app"      8001 || true
start_service "L2-knowledge"   "$BASE/l2-knowledge-graph-v3"  ".venv" "app.main:app"      8002 || true
start_service "L3-retrieval"   "$BASE/l3-intelligent-retrieval" ".venv" "app.main:app"    8300 || true
start_service "L4-policy"      "$BASE/l4-policy-resolution"   "venv"  "app.main:app"      8400 || true
start_service "L5-generation"  "$BASE/l5-secure-generation"   ".venv" "app.main:app"      8500 || true
start_service "L6-validation"  "$BASE/l6-multi-gate-validation" ".venv" "app.main:app"    8600 || true
start_service "L7-execution"   "$BASE/l7-secure-execution"    "venv"  "app.main:app"      8700 || true
start_service "L8-audit"       "$BASE/l8-audit-anomaly"       "venv"  "app.main:app"      8800 || true

# ── Frontend on port 3000 ──────────────────────────────────
info "Starting frontend on port 3000…"
cd "$BASE/frontend"
python3 -m http.server 3000 >> "$LOG_DIR/frontend.log" 2>&1 &
FPID=$!
echo "$FPID frontend" >> "$PID_FILE"
echo "  PID $FPID → $LOG_DIR/frontend.log"

# ── Wait and health check ──────────────────────────────────
echo ""
info "Waiting 4s for services to boot…"
sleep 4

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   Service Status                    ║"
echo "╚══════════════════════════════════════════════════════╝"

check_health() {
  local name="$1"; local url="$2"
  if curl -sf --max-time 3 "$url" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $name ($url)"
  else
    echo -e "  ${RED}✗${NC} $name ($url)"
  fi
}

check_health "L1 Identity"   "http://localhost:8001/health"
check_health "L2 Knowledge"  "http://localhost:8002/health"
check_health "L3 Retrieval"  "http://localhost:8300/api/v1/retrieval/health"
check_health "L4 Policy"     "http://localhost:8400/health"
check_health "L5 Generation" "http://localhost:8500/health"
check_health "L6 Validation" "http://localhost:8600/health"
check_health "L7 Execution"  "http://localhost:8700/health"
check_health "L8 Audit"      "http://localhost:8800/health"
check_health "Frontend"      "http://localhost:3000"

echo ""
echo -e "${GREEN}Frontend Dashboard:${NC} http://localhost:3000"
echo -e "${GREEN}Swagger UIs:${NC}"
echo "  L1: http://localhost:8001/docs   L5: http://localhost:8500/docs"
echo "  L3: http://localhost:8300/docs   L6: http://localhost:8600/docs"
echo "  L7: http://localhost:8700/docs   L8: http://localhost:8800/docs"
echo ""
echo "Logs: $LOG_DIR/"
echo "PIDs: $PID_FILE"
echo ""
echo "To stop all services: ./stop_all.sh"
