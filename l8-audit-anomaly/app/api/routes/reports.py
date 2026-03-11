"""Compliance report generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import ComplianceReport, ReportRequest
from app.services import compliance_reporter

router = APIRouter(prefix="/api/v1/audit/reports", tags=["reports"])


@router.post("/generate", response_model=ComplianceReport)
async def generate_report(req: ReportRequest) -> ComplianceReport:
    """Generate a compliance report on demand."""
    return compliance_reporter.generate(
        report_type=req.report_type,
        time_range=req.time_range,
        filters=req.filters,
    )
