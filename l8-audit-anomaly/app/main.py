"""L8 Audit & Anomaly Detection — FastAPI application entry point."""

from __future__ import annotations

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alerts, ingest, query, reports
from app.config import get_settings
from app.services import audit_store, anomaly_detector, alert_manager

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="L8 — Audit & Anomaly Detection",
    description="Immutable audit log, anomaly detection, and compliance reporting",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(alerts.router)
app.include_router(reports.router)


@app.on_event("startup")
async def startup() -> None:
    settings = get_settings()
    audit_store.initialize(settings.db_path)
    anomaly_detector.configure(
        z_high=settings.volume_anomaly_z_score_high,
        z_critical=settings.volume_anomaly_z_score_critical,
        work_start=settings.temporal_working_hours_start,
        work_end=settings.temporal_working_hours_end,
        block_threshold=settings.validation_block_threshold,
        sanitization_threshold=settings.sanitization_event_threshold,
        btg_duration_hours=settings.btg_duration_threshold_hours,
    )
    alert_manager.configure(
        dedup_window_minutes=settings.alert_dedup_window_minutes,
    )
    logger.info("l8_started", port=settings.service_port, db=settings.db_path)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "l8-audit-anomaly", "version": "1.0.0"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.service_port, reload=False)
