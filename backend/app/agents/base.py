"""
Nova AI — Base Agent
All 8 agents inherit from this. Provides JSON parsing, scoring, and result structure.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.llm.gateway import llm_complete
from app.crawler.fetcher import CrawlResult

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    module: str
    score: float          # 0–100
    weight: float         # agent's weight in composite (e.g. 0.15)
    grade: str            # A+ A B+ B C+ C D F
    findings: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    quick_wins: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    score_justification: str = ""
    error: Optional[str] = None

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    @staticmethod
    def score_to_grade(score: float) -> str:
        if score >= 93: return "A+"
        if score >= 87: return "A"
        if score >= 80: return "B+"
        if score >= 73: return "B"
        if score >= 67: return "C+"
        if score >= 60: return "C"
        if score >= 50: return "D"
        return "F"

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "score": round(self.score, 1),
            "weight": self.weight,
            "grade": self.grade,
            "findings": self.findings,
            "strengths": self.strengths,
            "quick_wins": self.quick_wins,
            "recommendations": self.recommendations,
            "score_justification": self.score_justification,
            "error": self.error,
        }


def _extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM output even if wrapped in markdown."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from LLM response: {text[:300]}")


class BaseAgent:
    name: str = "base"
    display_name: str = "Base Agent"
    weight: float = 0.10
    provider_hint: str = "auto"  # "nvidia" | "gemini" | "auto"
    max_tokens: int = 1024

    SYSTEM_PROMPT = """You are a world-class marketing analyst AI. 
Analyze the provided website data and return a JSON object ONLY.
No explanation outside the JSON. Be specific and actionable."""

    def build_prompt(self, crawl: CrawlResult) -> str:
        raise NotImplementedError

    async def analyze(self, crawl: CrawlResult) -> AgentResult:
        prompt = self.build_prompt(crawl)
        try:
            raw = await llm_complete(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                max_tokens=self.max_tokens,
                provider_hint=self.provider_hint,
            )
            data = _extract_json(raw)
            score = max(0.0, min(100.0, float(data.get("score", 50))))
            return AgentResult(
                module=self.name,
                score=score,
                weight=self.weight,
                grade=AgentResult.score_to_grade(score),
                findings=data.get("findings", [])[:6],
                strengths=data.get("strengths", [])[:6],
                quick_wins=data.get("quick_wins", [])[:5],
                recommendations=data.get("recommendations", [])[:5],
                score_justification=data.get("score_justification", ""),
            )
        except Exception as e:
            logger.error(f"[{self.name}] Agent failed: {e}")
            return AgentResult(
                module=self.name,
                score=0.0,
                weight=self.weight,
                grade="F",
                error=str(e),
            )

    def _homepage_summary(self, crawl: CrawlResult) -> str:
        hp = crawl.homepage
        if not hp:
            return "No homepage data available."
        return f"""
URL: {hp.url}
Title: {hp.title}
Meta Description: {hp.meta_description}
H1 Tags: {hp.h1}
H2 Tags: {hp.h2[:5]}
Word Count: {hp.word_count}
CTAs Found: {hp.cta_text}
Forms: {hp.form_count}
Has OG Tags: {hp.has_og_tags}
Has Schema Markup: {hp.has_schema_markup}
Business Type Detected: {crawl.business_type}
Body Text (excerpt): {hp.body_text[:2000]}
""".strip()
