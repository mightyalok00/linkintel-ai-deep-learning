import asyncio
from urllib.parse import parse_qs, unquote, urlparse
import httpx
from bs4 import BeautifulSoup

from app.providers.base import ProspectProvider
from app.schemas import ProspectInput
from app.security import normalize_domain

class LiveSearchProvider(ProspectProvider):
    name = "live_search"

    async def _fetch_query(self, client: httpx.AsyncClient, query: str,
                           link_type: str, category: str, website_domain: str) -> list[ProspectInput]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        items = []
        try:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.select(".result__title a")
            snippets = soup.select(".result__snippet")

            for link, snippet in zip(links, snippets):
                raw_url = link.get("href", "").strip()
                if not raw_url:
                    continue
                if "uddg=" in raw_url:
                    parsed_qs = parse_qs(urlparse(raw_url).query)
                    if "uddg" in parsed_qs:
                        raw_url = unquote(parsed_qs["uddg"][0])

                try:
                    domain = normalize_domain(raw_url)
                except ValueError:
                    continue

                if website_domain and domain == website_domain.lower():
                    continue
                if any(ignored in domain for ignored in ["duckduckgo.com", "google.com", "bing.com"]):
                    continue

                title = link.get_text(strip=True)
                desc = snippet.get_text(strip=True)
                text_lower = f"{title.lower()} {desc.lower()} {raw_url.lower()}"

                # Fine-grained link classification
                inferred_type = link_type
                if ".pdf" in raw_url.lower() or "filetype:pdf" in query or "pdf" in title.lower() or "whitepaper" in text_lower:
                    inferred_type = "📄 PDF Document Backlink"
                elif "infographic" in text_lower or "image" in text_lower or "badge" in text_lower or "photo" in text_lower:
                    inferred_type = "🖼️ Image / Infographic Backlink"
                elif "citation" in link_type.lower() or "practice" in text_lower or "clinic" in text_lower or "register" in text_lower:
                    inferred_type = "🏢 Niche Business Citation"
                else:
                    inferred_type = "🌐 Resource Directory"

                free_hints = any(w in text_lower for w in [
                    "free", "submit", "submit your", "add listing", "add tool",
                    "add site", "directory", "resource", "suggest a link", "contribute",
                    "upload", "whitepaper", "download", "infographic"
                ])

                items.append(ProspectInput(
                    domain=domain,
                    page_url=raw_url,
                    title=title,
                    description=desc,
                    category=category,
                    evidence_url=raw_url,
                    free_submission_available=free_hints,
                    link_type=inferred_type,
                    placement_fee=None,
                    submission_fee=None,
                    mandatory_purchase=None,
                    paid_plan_required=None,
                    terms_verified=False,
                ))
        except (httpx.HTTPError, Exception):
            return []

        return items

    async def discover(self, website_domain: str, category: str,
                       keywords: list[str], country: str,
                       target_count: int = 100,
                       progress_callback=None, **kwargs) -> list[ProspectInput]:
        """
        Discovers up to target_count (default 100) live working backlink opportunities
        across Directories, PDF Document Repositories, Image/Infographic submission sites,
        and Niche Business Citations.
        """
        kw_str = " ".join(keywords) if keywords else ""
        geo_str = f" {country.strip()}" if country and country.upper() != "GLOBAL" else ""

        if progress_callback:
            scope_desc = "globally" if not geo_str else f"for region {country.upper()}"
            await progress_callback(f"Initiating multi-bucket live search {scope_desc} across directories, PDFs, and citations...", 15, 0)

        # Multi-bucket search queries to gather comprehensive, diverse backlink types
        query_buckets = [
            # 1. Directory Submissions
            (f"{category} {kw_str} directory resources submit site free{geo_str}", "🌐 Resource Directory"),
            (f"{category} {kw_str} curated resource list add listing suggest a link", "🌐 Resource Directory"),
            (f"{category} {kw_str} best portals useful tools directory recommend site{geo_str}", "🌐 Resource Directory"),
            
            # 2. PDF & Document Backlinks
            (f"{category} {kw_str} filetype:pdf useful links resources recommended reading", "📄 PDF Document Backlink"),
            (f"{category} {kw_str} whitepaper research references filetype:pdf", "📄 PDF Document Backlink"),
            (f"{category} upload pdf document sharing library whitepaper directory", "📄 PDF Document Backlink"),
            (f"{category} guide checklist doc pdf repository", "📄 PDF Document Backlink"),

            # 3. Image & Infographic Backlinks
            (f"{category} {kw_str} submit infographic image directory visual resources", "🖼️ Image / Infographic Backlink"),
            (f"{category} {kw_str} infographic submissions photo catalog embed badge", "🖼️ Image / Infographic Backlink"),
            (f"{category} charts visual data graphics directory upload infographic", "🖼️ Image / Infographic Backlink"),

            # 4. Citations & Local / Niche Portals
            (f"{category} {kw_str} business directory free listing{geo_str}", "🏢 Niche Business Citation"),
            (f"{category} {kw_str} professional register provider directory search{geo_str}", "🏢 Niche Business Citation"),
            (f"{category} {kw_str} industry index catalog join directory", "🌐 Resource Directory"),
        ]

        if progress_callback:
            await progress_callback(f"Dispatching {len(query_buckets)} search workers across web buckets...", 25, 0)

        async with httpx.AsyncClient(timeout=18, follow_redirects=True) as client:
            tasks = [
                self._fetch_query(client, q, ltype, category, website_domain)
                for q, ltype in query_buckets
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        if progress_callback:
            await progress_callback("Aggregating search responses and deduplicating domains...", 50, 0)

        unique: dict[str, ProspectInput] = {}
        for res in batch_results:
            if isinstance(res, list):
                for p in res:
                    # Prefer distinct page URLs or domains
                    if p.page_url not in unique and p.domain not in [x.domain for x in unique.values()]:
                        unique[p.page_url] = p
                    elif p.page_url not in unique and len(unique) < target_count:
                        unique[p.page_url] = p

        results = list(unique.values())[:target_count]
        if progress_callback:
            await progress_callback(f"Extracted {len(results)} live candidate opportunities.", 65, len(results))

        return results
