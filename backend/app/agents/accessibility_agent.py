"""Accessibility Agent — 6% weight. Analyzes WCAG compliance: alt text, headings, contrast, ARIA."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class AccessibilityAgent(BaseAgent):
    name = "accessibility"
    display_name = "Accessibility (WCAG)"
    weight = 0.06
    max_tokens = 1000

    def build_prompt(self, crawl: CrawlResult) -> str:
        hp = crawl.homepage
        return f"""Analyze ACCESSIBILITY (WCAG 2.1 compliance) for this website.

WEBSITE DATA:
URL: {crawl.target_url}
Images without alt text: {hp.images_without_alt if hp else 'N/A'} of {hp.image_count if hp else 'N/A'} total images
H1 Tags: {hp.h1 if hp else []}
H2 Tags: {hp.h2 if hp else []}
H3 Tags: {hp.h3 if hp else []}
Form Count: {hp.form_count if hp else 0}
HTML Excerpt (check for ARIA, role attributes, skip links):
{hp.raw_html_excerpt[:2000] if hp else 'N/A'}

Evaluate (score 0-100):
1. Image alt text (all images have descriptive alt text?)
2. Heading hierarchy (logical H1→H2→H3 structure, single H1?)
3. ARIA attributes (roles, labels, landmarks present in HTML?)
4. Form accessibility (labels, fieldsets, error messages?)
5. Skip navigation links
6. Keyboard navigability signals from HTML structure
7. Color contrast signals from HTML/CSS class names or inline styles

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences>",
  "findings": ["<WCAG issue 1>", ...],
  "strengths": ["<accessibility strength 1>", ...],
  "quick_wins": ["<easy accessibility fix 1>", ...],
  "recommendations": ["<accessibility recommendation 1>", ...]
}}"""
