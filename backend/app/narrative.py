"""
Nova AI — AI Executive Narrative Generator
Produces a C-level plain-English summary with revenue impact framing.
"""
import logging
from app.llm.gateway import llm_complete

logger = logging.getLogger(__name__)

NARRATIVE_SYSTEM = """You are a senior marketing consultant writing for a C-suite executive.
Be insightful, specific, revenue-focused, and written in plain English.
No jargon. No bullet points. Use paragraph prose."""


def _build_narrative_prompt(result: dict) -> str:
    modules = result.get("modules", {})
    module_summary = "\n".join(
        f"- {k.upper()} ({v.get('score', 0):.0f}/100 {v.get('grade', '')}): {v.get('score_justification', '')}"
        for k, v in modules.items() if not v.get("error")
    )
    top_findings = "\n".join(
        f"- {f.get('text', f) if isinstance(f, dict) else f}"
        for f in result.get("findings", [])[:6]
    )
    top_wins = "\n".join(f"- {w}" for w in result.get("quick_wins", [])[:4])

    return f"""Write a 4-paragraph executive summary for: {result.get('url')}

OVERALL: {result.get('overall_score', 0):.0f}/100 (Grade: {result.get('grade')})
BUSINESS TYPE: {result.get('business_type')}

MODULE SCORES:
{module_summary}

TOP ISSUES:
{top_findings}

QUICK WINS:
{top_wins}

4 paragraphs: (1) Overall health + revenue impact (2) Critical problems (3) Opportunities + quick wins (4) CEO/CMO priority action.
Be specific, reference scores, mention revenue where possible."""


async def generate_narrative(result: dict) -> str:
    try:
        narrative = await llm_complete(
            prompt=_build_narrative_prompt(result),
            system=NARRATIVE_SYSTEM,
            max_tokens=1200,
            provider_hint="nvidia",
        )
        return narrative.strip()
    except Exception as e:
        logger.error(f"[Narrative] Failed: {e}")
        return (
            f"This website scored {result.get('overall_score', 0):.0f}/100 (Grade: {result.get('grade', 'N/A')}) "
            f"across 8 marketing dimensions. {len(result.get('findings', []))} issues identified. "
            f"[Narrative generation failed: {e}]"
        )
