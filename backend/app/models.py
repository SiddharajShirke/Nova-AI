"""
Nova AI — SQLAlchemy Data Models
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    # queued | crawling | analyzing | scoring | generating_report | completed | failed

    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    executive_narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # JSON fields: per-agent results, pagespeed data, tech stack, timings
    modules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    findings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    strengths: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    quick_wins: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pagespeed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tech_stack: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Progress tracking (for frontend polling)
    agents_completed: Mapped[int] = mapped_column(Integer, default=0)
    agents_total: Mapped[int] = mapped_column(Integer, default=8)
    current_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
