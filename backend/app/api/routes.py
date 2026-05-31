"""
Nova AI — FastAPI Routes
Endpoints: POST /audit, GET /audit/{id}, GET /audit/{id}/report, GET /health, GET /stats
"""
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Audit
from app.orchestrator import run_audit
from app.narrative import generate_narrative
from app.reports.generator import generate_pdf_report
from app.llm.gateway import get_gateway_stats

logger = logging.getLogger(__name__)
router = APIRouter()


class AuditRequest(BaseModel):
    url: str


class AuditResponse(BaseModel):
    audit_id: str
    status: str
    message: str


# ── Background task ───────────────────────────────────────────────────────────

async def _run_audit_background(audit_id: str, url: str):
    """Full audit pipeline runs in background. Updates DB as it progresses."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Fetch audit record
        audit = await db.get(Audit, audit_id)
        if not audit:
            return

        try:
            audit.status = "crawling"
            await db.commit()

            completed_agents = 0

            async def progress_cb(agent_name: str, agent_result):
                nonlocal completed_agents
                completed_agents += 1
                async with AsyncSessionLocal() as progress_db:
                    a = await progress_db.get(Audit, audit_id)
                    if a:
                        a.status = "analyzing"
                        a.agents_completed = completed_agents
                        a.current_agent = agent_name
                        await progress_db.commit()

            audit.status = "analyzing"
            await db.commit()

            result = await run_audit(url, progress_cb=progress_cb)

            if result.get("status") == "failed":
                audit.status = "failed"
                audit.error_message = result.get("error", "Unknown error")
                await db.commit()
                return

            audit.status = "scoring"
            audit.overall_score = result.get("overall_score")
            audit.grade = result.get("grade")
            audit.business_type = result.get("business_type")
            audit.modules = result.get("modules")
            audit.findings = result.get("findings")
            audit.strengths = result.get("strengths")
            audit.quick_wins = result.get("quick_wins")
            audit.tech_stack = result.get("tech_stack")
            audit.pagespeed_data = result.get("pagespeed_data")
            audit.agents_completed = 8
            await db.commit()

            # Generate executive narrative
            narrative = await generate_narrative(result)
            audit.executive_narrative = narrative
            result["executive_narrative"] = narrative
            await db.commit()

            # Generate PDF
            audit.status = "generating_report"
            await db.commit()
            pdf_path = await generate_pdf_report(result, audit_id)
            audit.report_path = pdf_path

            audit.status = "completed"
            audit.completed_at = datetime.utcnow()
            await db.commit()
            logger.info(f"[Routes] Audit {audit_id} completed. Score: {audit.overall_score}")

        except Exception as e:
            logger.error(f"[Routes] Audit {audit_id} failed: {e}", exc_info=True)
            try:
                audit.status = "failed"
                audit.error_message = str(e)
                await db.commit()
            except Exception:
                pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/audit", response_model=AuditResponse, status_code=202)
async def create_audit(
    body: AuditRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start a new website audit. Returns audit_id immediately; poll /audit/{id} for progress."""
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    audit_id = str(uuid.uuid4())
    audit = Audit(id=audit_id, url=url, status="queued", agents_total=8)
    db.add(audit)
    await db.commit()

    background_tasks.add_task(_run_audit_background, audit_id, url)
    logger.info(f"[Routes] Queued audit {audit_id} for {url}")

    return AuditResponse(
        audit_id=audit_id,
        status="queued",
        message=f"Audit started. Poll GET /api/v1/audit/{audit_id} for progress.",
    )


@router.get("/audit/{audit_id}")
async def get_audit(audit_id: str, db: AsyncSession = Depends(get_db)):
    """Get audit status and results."""
    audit = await db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    return {
        "audit_id": audit.id,
        "url": audit.url,
        "status": audit.status,
        "overall_score": audit.overall_score,
        "grade": audit.grade,
        "business_type": audit.business_type,
        "agents_completed": audit.agents_completed,
        "agents_total": audit.agents_total,
        "current_agent": audit.current_agent,
        "modules": audit.modules,
        "findings": audit.findings,
        "strengths": audit.strengths,
        "quick_wins": audit.quick_wins,
        "tech_stack": audit.tech_stack,
        "pagespeed_data": audit.pagespeed_data,
        "executive_narrative": audit.executive_narrative,
        "report_available": bool(audit.report_path and Path(audit.report_path).exists()),
        "error_message": audit.error_message,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }


@router.get("/audit/{audit_id}/report")
async def download_report(audit_id: str, db: AsyncSession = Depends(get_db)):
    """Download the PDF report for a completed audit."""
    audit = await db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.status != "completed" or not audit.report_path:
        raise HTTPException(status_code=404, detail="Report not yet available")
    path = Path(audit.report_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"nova_audit_{audit_id[:8]}.pdf",
    )


@router.get("/audits")
async def list_audits(db: AsyncSession = Depends(get_db), limit: int = 20):
    """List recent audits."""
    result = await db.execute(
        select(Audit).order_by(Audit.created_at.desc()).limit(limit)
    )
    audits = result.scalars().all()
    return [
        {
            "audit_id": a.id,
            "url": a.url,
            "status": a.status,
            "overall_score": a.overall_score,
            "grade": a.grade,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in audits
    ]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "nova-ai-backend"}


@router.get("/stats/llm")
async def llm_stats():
    """LLM gateway stats: provider health, circuit breaker state, cost."""
    return get_gateway_stats()
