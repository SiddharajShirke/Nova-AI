"""
Nova AI — Web Crawler & Page Data Extractor
Uses httpx (async) + BeautifulSoup for parsing.
Detects tech stack, security headers, extracts structured page data.
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 15.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovaAI-Audit/1.0; +https://nova-ai.io/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Tech stack detection patterns
TECH_SIGNATURES = {
    "WordPress": ["wp-content", "wp-includes", "wp-json"],
    "Shopify": ["cdn.shopify.com", "Shopify.theme"],
    "React": ["react", "_next/static", "__NEXT_DATA__"],
    "Next.js": ["__NEXT_DATA__", "_next/static"],
    "Vue.js": ["vue.js", "vue.min.js", "__vue__"],
    "Angular": ["ng-version", "angular.js"],
    "Webflow": ["webflow.com", "w-webflow"],
    "Wix": ["wix.com", "_wix_"],
    "Squarespace": ["squarespace.com", "squarespace-cdn"],
    "HubSpot": ["hubspot.com", "hs-scripts"],
    "Google Analytics": ["google-analytics.com", "gtag(", "ga("],
    "Stripe": ["js.stripe.com"],
    "Intercom": ["widget.intercom.io"],
    "Hotjar": ["static.hotjar.com"],
    "Tailwind CSS": ["tailwind"],
}

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]


@dataclass
class PageData:
    url: str
    status_code: int = 0
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    body_text: str = ""
    word_count: int = 0
    cta_text: list[str] = field(default_factory=list)
    form_count: int = 0
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    image_count: int = 0
    images_without_alt: int = 0
    has_og_tags: bool = False
    has_twitter_cards: bool = False
    has_schema_markup: bool = False
    canonical_url: str = ""
    robots_meta: str = ""
    response_time_ms: float = 0.0
    security_headers: dict = field(default_factory=dict)
    raw_html_excerpt: str = ""  # First 5000 chars for agents


@dataclass
class CrawlResult:
    target_url: str
    pages: list[PageData] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    business_type: str = "other"
    has_https: bool = False
    error: Optional[str] = None

    @property
    def homepage(self) -> Optional[PageData]:
        return self.pages[0] if self.pages else None

    @property
    def combined_text(self) -> str:
        texts = [p.body_text for p in self.pages]
        return " ".join(texts)[:8000]


def _extract_ctas(soup: BeautifulSoup) -> list[str]:
    ctas = []
    cta_selectors = ["a", "button"]
    cta_keywords = ["get started", "sign up", "try", "free", "buy", "shop", "learn more",
                    "start", "demo", "contact", "book", "schedule", "download", "watch"]
    for tag in soup.find_all(cta_selectors):
        text = tag.get_text(strip=True).lower()
        if any(kw in text for kw in cta_keywords) and len(text) < 60:
            ctas.append(tag.get_text(strip=True))
    return list(dict.fromkeys(ctas))[:10]


def _detect_tech(html: str, headers: dict) -> list[str]:
    detected = []
    html_lower = html.lower()
    for tech, sigs in TECH_SIGNATURES.items():
        if any(sig.lower() in html_lower for sig in sigs):
            detected.append(tech)
    return detected


def _detect_business_type(text: str) -> str:
    text_lower = text.lower()
    scores = {
        "saas": sum(1 for w in ["software", "saas", "platform", "api", "dashboard", "subscription", "per month", "per user"] if w in text_lower),
        "ecommerce": sum(1 for w in ["shop", "buy now", "cart", "checkout", "product", "shipping", "order"] if w in text_lower),
        "agency": sum(1 for w in ["agency", "services", "clients", "portfolio", "case study", "we help"] if w in text_lower),
        "local": sum(1 for w in ["location", "store", "near me", "address", "hours", "call us"] if w in text_lower),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "other"


def _parse_page(url: str, response: httpx.Response, elapsed_ms: float) -> PageData:
    soup = BeautifulSoup(response.text, "lxml")

    # Remove script/style tags for clean text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""
    meta_desc = ""
    meta_kw = ""
    canonical = ""
    robots_meta = ""

    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower()
        prop = meta.get("property", "").lower()
        content = meta.get("content", "")
        if name == "description":
            meta_desc = content
        elif name == "keywords":
            meta_kw = content
        elif name == "robots":
            robots_meta = content

    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag:
        canonical = canonical_tag.get("href", "")

    h1 = [t.get_text(strip=True) for t in soup.find_all("h1")][:5]
    h2 = [t.get_text(strip=True) for t in soup.find_all("h2")][:10]
    h3 = [t.get_text(strip=True) for t in soup.find_all("h3")][:10]

    body_text = soup.get_text(separator=" ", strip=True)
    body_text = re.sub(r"\s+", " ", body_text)[:6000]
    word_count = len(body_text.split())

    base = urlparse(url)
    internal_links = []
    external_links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https"):
            if parsed.netloc == base.netloc:
                internal_links.append(href)
            else:
                external_links.append(href)

    images = soup.find_all("img")
    images_without_alt = sum(1 for img in images if not img.get("alt"))

    has_og = bool(soup.find("meta", property=lambda p: p and p.startswith("og:")))
    has_twitter = bool(soup.find("meta", attrs={"name": lambda n: n and n.startswith("twitter:")}))
    has_schema = bool(soup.find("script", type="application/ld+json"))

    sec_headers = {}
    for h in SECURITY_HEADERS:
        sec_headers[h] = response.headers.get(h, "MISSING")

    return PageData(
        url=url,
        status_code=response.status_code,
        title=title,
        meta_description=meta_desc,
        meta_keywords=meta_kw,
        h1=h1,
        h2=h2,
        h3=h3,
        body_text=body_text,
        word_count=word_count,
        cta_text=_extract_ctas(soup),
        form_count=len(soup.find_all("form")),
        internal_links=list(dict.fromkeys(internal_links))[:20],
        external_links=list(dict.fromkeys(external_links))[:10],
        image_count=len(images),
        images_without_alt=images_without_alt,
        has_og_tags=has_og,
        has_twitter_cards=has_twitter,
        has_schema_markup=has_schema,
        canonical_url=canonical,
        robots_meta=robots_meta,
        response_time_ms=elapsed_ms,
        security_headers=sec_headers,
        raw_html_excerpt=response.text[:5000],
    )


async def crawl_site(url: str, max_pages: int = 3) -> CrawlResult:
    """Crawl a website starting from `url`, visiting up to `max_pages` pages."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    result = CrawlResult(
        target_url=url,
        has_https=url.startswith("https://"),
    )

    visited: set[str] = set()
    to_visit: list[str] = [url]
    pages_crawled = 0

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=CRAWL_TIMEOUT,
        verify=False,
    ) as client:
        while to_visit and pages_crawled < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                start = asyncio.get_event_loop().time()
                response = await client.get(current_url)
                elapsed = (asyncio.get_event_loop().time() - start) * 1000

                if "text/html" not in response.headers.get("content-type", ""):
                    continue

                page = _parse_page(current_url, response, elapsed)
                result.pages.append(page)
                pages_crawled += 1

                # Queue internal links for next pages
                if pages_crawled < max_pages:
                    for link in page.internal_links[:5]:
                        if link not in visited and urlparse(link).netloc == parsed.netloc:
                            to_visit.append(link)

            except httpx.HTTPError as e:
                logger.warning(f"[Crawler] Failed to fetch {current_url}: {e}")
                if pages_crawled == 0:
                    result.error = f"Could not fetch URL: {e}"

    if result.pages:
        all_html = " ".join(p.raw_html_excerpt for p in result.pages)
        result.tech_stack = _detect_tech(all_html, {})
        result.business_type = _detect_business_type(result.combined_text)

    return result
