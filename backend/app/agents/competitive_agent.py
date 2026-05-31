"""Competitive Agent — 8% weight. Analyzes positioning vs competitors, differentiation, SEO moat."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class CompetitiveAgent(BaseAgent):
    name = "competitive"
    display_name = "Competitive Intelligence"
    weight = 0.08
    provider_hint = "nvidia"
    max_tokens = 1200

    def build_prompt(self, crawl: CrawlResult) -> str:
        return f"""Analyze the COMPETITIVE POSITIONING of this website based on observable signals.

WEBSITE DATA:
{self._homepage_summary(crawl)}
Tech Stack: {crawl.tech_stack}

Based on the website content alone (without visiting competitor sites), evaluate:
1. Unique value proposition clarity (how clearly do they differentiate from competitors?)
2. Competitive moat signals (what makes them hard to copy? network effects? data? brand?)
3. Keyword targeting strength (are they targeting the right competitive keywords?)
4. Brand authority vs inferred competition (testimonials, media, case studies suggest authority?)
5. Pricing competitiveness signals (visible pricing? competitive anchoring?)
6. Missing competitive elements (what do leading competitors typically have that this site lacks?)

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences>",
  "findings": ["<competitive gap 1>", ...],
  "strengths": ["<competitive advantage 1>", ...],
  "quick_wins": ["<immediate competitive improvement 1>", ...],
  "recommendations": ["<strategic recommendation 1>", ...]
}}"""
