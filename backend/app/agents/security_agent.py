"""Security Agent — 4% weight. Analyzes HTTPS, security headers, cookie/privacy signals."""
from app.agents.base import BaseAgent
from app.crawler.fetcher import CrawlResult


class SecurityAgent(BaseAgent):
    name = "security"
    display_name = "Security & Trust"
    weight = 0.04
    max_tokens = 900

    def build_prompt(self, crawl: CrawlResult) -> str:
        hp = crawl.homepage
        return f"""Analyze SECURITY and TRUST signals for this website.

WEBSITE DATA:
URL: {crawl.target_url}
HTTPS Enabled: {crawl.has_https}
Security Headers Present/Missing:
{chr(10).join(f'  {k}: {v}' for k, v in (hp.security_headers.items() if hp else {}.items()))}

Body text excerpt (check for privacy policy, terms, cookie consent mentions):
{hp.body_text[:1000] if hp else 'N/A'}

HTML Excerpt (check for cookie banners, SSL badges, security seals):
{hp.raw_html_excerpt[:1500] if hp else 'N/A'}

Evaluate (score 0-100):
1. HTTPS implementation (full SSL/TLS? HTTP→HTTPS redirect?)
2. HSTS header (Strict-Transport-Security present and configured?)
3. Content Security Policy (prevents XSS attacks?)
4. X-Frame-Options (prevents clickjacking?)
5. Privacy policy / cookie consent (GDPR compliance signals?)
6. Security trust badges (SSL seal, payment security logos?)
7. X-Content-Type-Options and Referrer-Policy

Return ONLY this JSON:
{{
  "score": <0-100>,
  "score_justification": "<2 sentences>",
  "findings": ["<security issue 1>", ...],
  "strengths": ["<security strength 1>", ...],
  "quick_wins": ["<quick security fix 1>", ...],
  "recommendations": ["<security recommendation 1>", ...]
}}"""
