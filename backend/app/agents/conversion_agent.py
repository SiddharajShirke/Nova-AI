"""Conversion Agent — 12% weight. Analyzes CTAs, forms, trust signals, friction points."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class ConversionAgent(BaseAgent):
    name = "conversion"
    display_name = "Conversion Optimization"
    weight = 0.12
    provider_hint = "nvidia"
    max_tokens = 1200

    def build_prompt(self, crawl: CrawlResult) -> str:
        hp = crawl.homepage
        return f"""Analyze CONVERSION RATE OPTIMIZATION for this website.

WEBSITE DATA:
{self._homepage_summary(crawl)}
Forms Found: {hp.form_count if hp else 0}
CTA Buttons/Links: {hp.cta_text if hp else []}
Internal Links: {len(hp.internal_links) if hp else 0}

Evaluate:
1. CTA quality (clear, compelling, above-the-fold, sufficient quantity?)
2. Form optimization (fields, placement, friction, clarity?)
3. Trust signals (testimonials, logos, reviews, guarantees, security badges?)
4. Conversion path clarity (is the desired action obvious? is there a clear funnel?)
5. Friction points (what might stop a visitor from converting?)
6. Social proof (reviews, ratings, user counts, named customers?)

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences explaining the score>",
  "findings": ["<conversion issue 1>", ...],
  "strengths": ["<conversion strength 1>", ...],
  "quick_wins": ["<quick conversion fix 1>", ...],
  "recommendations": ["<strategic CRO recommendation 1>", ...]
}}"""
