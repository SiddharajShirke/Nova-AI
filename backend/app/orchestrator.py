"""
Nova AI — Audit Orchestrator
Runs the full pipeline: crawl → 8 agents (concurrent) → score → narrative → PDF
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Callable, Optional

from app.crawler.fetcher import crawl_site, CrawlResult
from app.agents.base import AgentResult
from app.agents.content_agent import ContentAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.conversion_agent import ConversionAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.webvitals_agent import WebVitalsAgent
from app.agents.competitive_agent import CompetitiveAgent
from app.agents.accessibility_agent import AccessibilityAgent
from app.agents.security_agent import SecurityAgent

logger = logging.getLogger(__name__)

# Agent semaphore: max 4 concurrent LLM calls
AGENT_SEMAPHORE = asyncio.Semaphore(4)

AGENT_WEIGHTS = {
    "content": 0.15,
    "strategy": 0.13,
    "conversion": 0.12,
    "technical": 0.12,
    "webvitals": 0.08,
    "competitive": 0.08,
    "accessibility": 0.06,
    "security": 0.04,
}
# Normalize to 100% (total = 0.78)
WEIGHT_SUM = sum(AGENT_WEIGHTS.values())
NORMALIZED_WEIGHTS = {k: v / WEIGHT_SUM for k, v in AGENT_WEIGHTS.items()}


def _compute_composite_score(results: list[AgentResult]) -> float:
    """Weighted average — failed agents (score=0 with error) are excluded."""
    valid = [r for r in results if r.error is None]
    if not valid:
        return 0.0
    total_weight = sum(NORMALIZED_WEIGHTS.get(r.module, r.weight) for r in valid)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(r.score * NORMALIZED_WEIGHTS.get(r.module, r.weight) for r in valid)
    return weighted_sum / total_weight


def _aggregate_findings(results: list[AgentResult]) -> tuple[list, list, list]:
    """Merge findings/strengths/quick_wins from all agents, deduplicate."""
    all_findings = []
    all_strengths = []
    all_quick_wins = []
    seen_findings = set()

    for r in results:
        for f in r.findings:
            key = f.lower()[:60]
            if key not in seen_findings:
                seen_findings.add(key)
                all_findings.append({"agent": r.module, "text": f})
        all_strengths.extend(r.strengths)
        all_quick_wins.extend(r.quick_wins)

    return all_findings[:20], list(dict.fromkeys(all_strengths))[:15], list(dict.fromkeys(all_quick_wins))[:10]


async def _run_agent_with_semaphore(agent, crawl: CrawlResult, progress_cb: Optional[Callable] = None):
    async with AGENT_SEMAPHORE:
        logger.info(f"[Orchestrator] Running {agent.name} agent...")
        start = time.time()
        result = await agent.analyze(crawl)
        elapsed = time.time() - start
        logger.info(f"[Orchestrator] {agent.name} done in {elapsed:.1f}s — score: {result.score:.1f}")
        if progress_cb:
            await progress_cb(agent.name, result)
        return result


async def run_audit(
    url: str,
    progress_cb: Optional[Callable] = None,
) -> dict:
    """
    Full audit pipeline. Returns result dict with all scores, findings, narrative.
    progress_cb(agent_name, AgentResult) is called as each agent completes.
    """
    pipeline_start = time.time()

    # ── 1. Crawl ──────────────────────────────────────────────────────────────
    logger.info(f"[Orchestrator] Crawling {url}")
    crawl: CrawlResult = await crawl_site(url, max_pages=3)

    if crawl.error and not crawl.pages:
        return {
            "status": "failed",
            "error": f"Could not crawl website: {crawl.error}",
        }

    # ── 2. Initialize agents ──────────────────────────────────────────────────
    standard_agents = [
        ContentAgent(),
        StrategyAgent(),
        ConversionAgent(),
        TechnicalAgent(),
        CompetitiveAgent(),
        AccessibilityAgent(),
        SecurityAgent(),
    ]
    webvitals_agent = WebVitalsAgent()

    # ── 3. Run all agents concurrently ────────────────────────────────────────
    pagespeed_data = None

    async def run_webvitals():
        nonlocal pagespeed_data
        async with AGENT_SEMAPHORE:
            result, ps_data = await webvitals_agent.analyze(crawl)
            pagespeed_data = ps_data
            if progress_cb:
                await progress_cb("webvitals", result)
            return result

    tasks = [_run_agent_with_semaphore(a, crawl, progress_cb) for a in standard_agents]
    tasks.append(run_webvitals())

    results: list[AgentResult] = await asyncio.gather(*tasks, return_exceptions=False)

    # ── 4. Score ──────────────────────────────────────────────────────────────
    overall_score = _compute_composite_score(results)
    grade = AgentResult.score_to_grade(overall_score)

    findings, strengths, quick_wins = _aggregate_findings(results)

    modules = {r.module: r.to_dict() for r in results}

    elapsed_total = time.time() - pipeline_start

    return {
        "status": "completed",
        "url": url,
        "business_type": crawl.business_type,
        "overall_score": round(overall_score, 1),
        "grade": grade,
        "modules": modules,
        "findings": findings,
        "strengths": strengths,
        "quick_wins": quick_wins,
        "tech_stack": crawl.tech_stack,
        "pagespeed_data": pagespeed_data,
        "has_https": crawl.has_https,
        "pages_crawled": len(crawl.pages),
        "elapsed_seconds": round(elapsed_total, 1),
    }
