"""
Web Vitals Agent — 8% weight.
Fetches real Core Web Vitals from Google PageSpeed Insights API.
Falls back to response-time heuristics if no API key.
"""
import asyncio
import logging
from typing import Optional

import httpx

from app.agents.base import BaseAgent, AgentResult
from app.crawler.fetcher import CrawlResult
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def fetch_pagespeed(url: str) -> Optional[dict]:
    """Fetch PageSpeed Insights data. Works without API key (rate limited)."""
    params = {
        "url": url,
        "strategy": "mobile",
        "category": ["performance", "accessibility", "seo", "best-practices"],
    }
    pagespeed_key = getattr(settings, "pagespeed_key_valid", None) or settings.pagespeed_api_key
    if pagespeed_key and "XXX" not in pagespeed_key and "xxx" not in pagespeed_key:
        params["key"] = pagespeed_key

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(PAGESPEED_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            cats = data.get("lighthouseResult", {}).get("categories", {})
            audits = data.get("lighthouseResult", {}).get("audits", {})

            lcp = audits.get("largest-contentful-paint", {}).get("displayValue", "N/A")
            cls_val = audits.get("cumulative-layout-shift", {}).get("displayValue", "N/A")
            fid = audits.get("total-blocking-time", {}).get("displayValue", "N/A")
            fcp = audits.get("first-contentful-paint", {}).get("displayValue", "N/A")
            speed_index = audits.get("speed-index", {}).get("displayValue", "N/A")

            return {
                "performance_score": int((cats.get("performance", {}).get("score", 0) or 0) * 100),
                "accessibility_score": int((cats.get("accessibility", {}).get("score", 0) or 0) * 100),
                "seo_score": int((cats.get("seo", {}).get("score", 0) or 0) * 100),
                "best_practices_score": int((cats.get("best-practices", {}).get("score", 0) or 0) * 100),
                "lcp": lcp,
                "cls": cls_val,
                "tbt": fid,
                "fcp": fcp,
                "speed_index": speed_index,
            }
    except Exception as e:
        logger.warning(f"[WebVitals] PageSpeed API failed: {e}")
        return None


class WebVitalsAgent(BaseAgent):
    name = "webvitals"
    display_name = "Web Vitals & Performance"
    weight = 0.08
    max_tokens = 800

    async def analyze(self, crawl: CrawlResult) -> AgentResult:
        hp = crawl.homepage
        pagespeed_data = await fetch_pagespeed(crawl.target_url)

        if pagespeed_data:
            # Use real PageSpeed score directly
            ps_score = pagespeed_data["performance_score"]
            findings = []
            strengths = []
            quick_wins = []

            if ps_score < 50:
                findings.append(f"Critical: Performance score is {ps_score}/100 — extremely slow for mobile users")
                quick_wins.append("Enable image compression and lazy loading immediately")
                quick_wins.append("Add a CDN to serve static assets")
            elif ps_score < 70:
                findings.append(f"Performance score is {ps_score}/100 — below Google's 'Good' threshold of 90")
                quick_wins.append("Optimize largest contentful paint (LCP) element")

            if ps_score >= 90:
                strengths.append(f"Excellent performance score: {ps_score}/100")

            lcp = pagespeed_data["lcp"]
            findings.append(f"LCP: {lcp} (target: <2.5s)")
            findings.append(f"CLS: {pagespeed_data['cls']} (target: <0.1)")
            findings.append(f"TBT (proxy for INP): {pagespeed_data['tbt']}")

            score = float(ps_score)
            justification = (
                f"Real Google PageSpeed score of {ps_score}/100 on mobile. "
                f"LCP: {lcp}, CLS: {pagespeed_data['cls']}."
            )
            recommendations = [
                "Implement Largest Contentful Paint optimizations (preload hero image)",
                "Reduce Cumulative Layout Shift by specifying image dimensions",
                "Use next-gen image formats (WebP/AVIF)",
                "Eliminate render-blocking resources",
            ]
        else:
            # Heuristic fallback from crawl response time
            response_time = hp.response_time_ms if hp else 2000
            if response_time < 500:
                score = 82.0
                findings = ["Unable to fetch PageSpeed data — using response time heuristic"]
                strengths = [f"Fast server response time: {response_time:.0f}ms"]
                quick_wins = ["Run Google PageSpeed Insights for real Core Web Vitals data"]
            elif response_time < 1500:
                score = 62.0
                findings = [f"Server response time: {response_time:.0f}ms (target <500ms)", "PageSpeed API unavailable — add PAGESPEED_API_KEY for real metrics"]
                strengths = []
                quick_wins = ["Enable server-side caching", "Use a CDN for static assets"]
            else:
                score = 38.0
                findings = [f"Slow server response time: {response_time:.0f}ms", "PageSpeed API unavailable"]
                strengths = []
                quick_wins = ["Switch to a faster hosting provider or enable caching immediately"]

            justification = f"Heuristic score based on server response time ({response_time:.0f}ms). Add PAGESPEED_API_KEY for real Core Web Vitals."
            recommendations = [
                "Configure PAGESPEED_API_KEY for real Google PageSpeed data",
                "Implement HTTP/2 on your server",
                "Enable Gzip/Brotli compression",
            ]

        agent_result = AgentResult(
            module=self.name,
            score=score,
            weight=self.weight,
            grade=AgentResult.score_to_grade(score),
            findings=findings,
            strengths=strengths,
            quick_wins=quick_wins,
            recommendations=recommendations,
            score_justification=justification,
        )
        return agent_result, pagespeed_data
