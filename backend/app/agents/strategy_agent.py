"""Strategy Agent — 13% weight. Analyzes business model, positioning, growth loops, pricing."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class StrategyAgent(BaseAgent):
    name = "strategy"
    display_name = "Business Strategy"
    weight = 0.13
    provider_hint = "nvidia"
    max_tokens = 1200

    def build_prompt(self, crawl: CrawlResult) -> str:
        return f"""Analyze the BUSINESS STRATEGY and MARKET POSITIONING of this website.

WEBSITE DATA:
{self._homepage_summary(crawl)}
Business Type Detected: {crawl.business_type}
Pages Crawled: {len(crawl.pages)}

Evaluate:
1. Market positioning (clear niche? unique angle? differentiation from competitors?)
2. Pricing strategy (visible? competitive? value-aligned?)
3. Target audience clarity (who is this for? is it clearly communicated?)
4. Business model clarity (how do they make money? is it obvious?)
5. Growth levers (referrals, virality, community, content, SEO moat?)
6. Brand authority signals (testimonials, case studies, social proof, media mentions?)

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences explaining the score>",
  "findings": ["<specific strategic gap 1>", ...],
  "strengths": ["<strategic strength 1>", ...],
  "quick_wins": ["<actionable strategic fix 1>", ...],
  "recommendations": ["<high-level strategic recommendation 1>", ...]
}}"""
