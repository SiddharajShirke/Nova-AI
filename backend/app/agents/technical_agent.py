"""Technical SEO Agent — 12% weight. Analyzes meta tags, canonicals, indexability, structure."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class TechnicalAgent(BaseAgent):
    name = "technical"
    display_name = "Technical SEO"
    weight = 0.12
    provider_hint = "gemini"
    max_tokens = 1200

    def build_prompt(self, crawl: CrawlResult) -> str:
        hp = crawl.homepage
        return f"""Analyze TECHNICAL SEO for this website.

WEBSITE DATA:
URL: {crawl.target_url}
HTTPS: {crawl.has_https}
Title: {hp.title if hp else 'N/A'}  (length: {len(hp.title) if hp else 0} chars)
Meta Description: {hp.meta_description if hp else 'N/A'}  (length: {len(hp.meta_description) if hp else 0} chars)
Meta Keywords: {hp.meta_keywords if hp else 'N/A'}
H1 Tags: {hp.h1 if hp else []}  (count: {len(hp.h1) if hp else 0})
H2 Tags: {hp.h2 if hp else []}
Canonical URL: {hp.canonical_url if hp else 'N/A'}
Robots Meta: {hp.robots_meta if hp else 'N/A'}
Has Schema Markup: {hp.has_schema_markup if hp else False}
Has OG Tags: {hp.has_og_tags if hp else False}
Images Without Alt Text: {hp.images_without_alt if hp else 0} / {hp.image_count if hp else 0}
Internal Links: {len(hp.internal_links) if hp else 0}
Pages Discoverable: {len(crawl.pages)}

Evaluate (score 0-100):
1. Title tag (optimal length 50-60 chars, keyword-rich, unique?)
2. Meta description (optimal 150-160 chars, compelling, unique?)
3. Heading hierarchy (single H1, logical H2/H3 structure?)
4. Canonicalization (self-referencing canonical? no duplicate issues?)
5. Schema markup (present, relevant type?)
6. Image optimization (alt text, descriptive filenames?)
7. Internal linking structure
8. Crawlability (robots meta, sitemap signals?)

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences explaining the score>",
  "findings": ["<specific SEO issue 1>", ...],
  "strengths": ["<SEO strength 1>", ...],
  "quick_wins": ["<quick SEO fix (implemented in hours) 1>", ...],
  "recommendations": ["<strategic SEO recommendation 1>", ...]
}}"""
