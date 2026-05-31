"""Content Agent — 15% weight. Analyzes headline clarity, copy quality, value props, readability."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class ContentAgent(BaseAgent):
    name = "content"
    display_name = "Content & Messaging"
    weight = 0.15
    provider_hint = "nvidia"
    max_tokens = 1200

    def build_prompt(self, crawl: CrawlResult) -> str:
        return f"""Analyze the CONTENT and MESSAGING quality of this website.

WEBSITE DATA:
{self._homepage_summary(crawl)}

Evaluate:
1. Headline clarity & impact (does it immediately communicate the value prop?)
2. Value proposition strength (clear, compelling, differentiated?)
3. Copy quality (professional, concise, benefit-focused vs feature-focused?)
4. Readability (appropriate level, jargon-free, scannable?)
5. Storytelling & emotional resonance
6. Content completeness (enough info to make a purchase decision?)

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences explaining the score>",
  "findings": ["<specific issue 1>", "<specific issue 2>", ...],
  "strengths": ["<what they do well 1>", ...],
  "quick_wins": ["<actionable improvement in <1 week 1>", ...],
  "recommendations": ["<strategic recommendation 1>", ...]
}}"""
