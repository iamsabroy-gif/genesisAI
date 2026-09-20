"""
Project Genesis: High-Performance Sovereign Web Scraper & Research Engine.
Enables zero-API-key web search, semantic HTML-to-Markdown scraping, and multi-source research.
"""

import re
import urllib.request
import urllib.parse
from typing import Dict, Any, List
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the public web using DuckDuckGo with resilient Bing fallback (zero API key required).
    Returns a structured markdown summary of top search results with clean URLs.
    """
    if not query.strip():
        return "Error: Search query cannot be empty."

    encoded_query = urllib.parse.quote_plus(query.strip())
    headers = {"User-Agent": USER_AGENT}
    results = []

    # 1. Primary Engine: DuckDuckGo
    try:
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            soup = BeautifulSoup(resp.read(), "html.parser")

        for item in soup.find_all("div", class_="result")[:max_results]:
            a_tag = item.find("a", class_="result__a")
            snippet_tag = item.find("a", class_="result__snippet")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            raw_href = a_tag.get("href", "")

            # Decode DuckDuckGo redirect
            parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
            clean_url = parsed_query.get("uddg", [raw_href])[0]
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No snippet available."

            results.append(
                f"### [{title}]({clean_url})\n"
                f"- **URL**: `{clean_url}`\n"
                f"- **Snippet**: {snippet}\n"
            )
    except Exception:
        pass

    # 2. Resilient Fallback Engine: Bing
    if not results:
        try:
            import base64
            b_url = f"https://www.bing.com/search?q={encoded_query}"
            req = urllib.request.Request(b_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")

            for li in soup.find_all("li", class_="b_algo")[:max_results]:
                h2 = li.find("h2")
                p = li.find("p") or li.find("div", class_="b_caption")
                if h2 and h2.find("a"):
                    a = h2.find("a")
                    title = h2.get_text(strip=True)
                    raw_url = a.get("href", "")
                    clean_url = raw_url

                    # Decode Bing redirect
                    if "/ck/a?!" in raw_url:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                        u_val = parsed.get("u", [""])[0]
                        if u_val.startswith("a1"):
                            b64_str = u_val[2:]
                            padding = 4 - (len(b64_str) % 4)
                            if padding != 4:
                                b64_str += "=" * padding
                            try:
                                clean_url = base64.b64decode(b64_str).decode("utf-8", errors="ignore")
                            except Exception:
                                pass

                    snippet = p.get_text(strip=True) if p else "No snippet available."
                    results.append(
                        f"### [{title}]({clean_url})\n"
                        f"- **URL**: `{clean_url}`\n"
                        f"- **Snippet**: {snippet}\n"
                    )
        except Exception as e:
            return f"Web Search Error: {e}"

    if not results:
        return f"No search results found for query: '{query}'."

    header = f"## Web Search Results for: '{query}'\n\n"
    return header + "\n".join(results)


def web_scrape(url: str, max_chars: int = 4000) -> str:
    """
    Scrape a webpage and convert its contents into clean, semantic Markdown.
    Strips ads, navigation bars, scripts, and CSS. Enforces strict context bounds.
    """
    if not url.strip().startswith(("http://", "https://")):
        return f"Error: Invalid URL '{url}'. Must start with http:// or https://"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_html = resp.read()

        soup = BeautifulSoup(raw_html, "html.parser")

        # Decompose noisy / non-content elements
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "noscript",
                "svg",
                "form",
                "button",
                "iframe",
            ]
        ):
            tag.decompose()

        page_title = soup.title.get_text(strip=True) if soup.title else "Scraped Webpage"
        text_blocks = [f"# {page_title}\n*Source: {url}*\n"]

        # Target primary content container
        container = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"id": re.compile(r"content|main|article", re.I)})
            or soup.find("div", {"class": re.compile(r"content|post|article", re.I)})
            or soup.body
        )

        if container:
            for el in container.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
                txt = el.get_text(" ", strip=True)
                if not txt or len(txt) < 8:
                    continue

                if el.name == "h1":
                    text_blocks.append(f"# {txt}")
                elif el.name == "h2":
                    text_blocks.append(f"## {txt}")
                elif el.name == "h3":
                    text_blocks.append(f"### {txt}")
                elif el.name == "li":
                    text_blocks.append(f"- {txt}")
                else:
                    text_blocks.append(txt)

        content = "\n\n".join(text_blocks)
        content = re.sub(r"\n{3,}", "\n\n", content)

        if len(content) > max_chars:
            truncated = content[:max_chars]
            return (
                truncated
                + f"\n\n... [Content truncated; showing {max_chars} of {len(content)} characters to protect context window]"
            )

        return content

    except Exception as e:
        return f"Web Scrape Error ({url}): {e}"


def web_research(topic: str, max_sources: int = 3) -> str:
    """
    Autonomous multi-source research workflow:
    1. Searches the web for the topic.
    2. Scrapes the top sources into clean Markdown.
    3. Synthesizes a structured research brief for high-level insight.
    """
    search_output = web_search(topic, max_results=max_sources * 2)
    if "Web Search Error" in search_output or "No search results" in search_output:
        return search_output

    # Extract clean target URLs
    urls = re.findall(r"- \*\*URL\*\*: `(https?://[^`]+)`", search_output)
    if not urls:
        return f"Could not extract target URLs from search for topic '{topic}'."

    dossier = [f"# Research Dossier: '{topic}'\n"]
    scraped_count = 0

    for u in urls:
        if scraped_count >= max_sources:
            break
        # Skip PDFs or raw media files
        if any(u.lower().endswith(ext) for ext in [".pdf", ".jpg", ".png", ".zip"]):
            continue

        scraped_text = web_scrape(u, max_chars=2500)
        if "Web Scrape Error" not in scraped_text:
            dossier.append(f"---\n## Source {scraped_count + 1}: {u}\n")
            dossier.append(scraped_text)
            scraped_count += 1

    if scraped_count == 0:
        return f"Search succeeded, but failed to scrape sources for '{topic}'. Search summary:\n{search_output}"

    return "\n\n".join(dossier)


def deep_research_report(topic: str, max_sources: int = 5, save_to_vault: bool = True) -> str:
    """
    Gemini Notebook / NotebookLM-style Deep Research & Analysis Report Generator.
    1. Multi-query search (triangulates overview, technical details, and trade-offs).
    2. Scrapes and cleans top authoritative sources.
    3. Synthesizes a structured analysis report with key takeaways and citation table.
    4. Automatically archives the full report to ~/.genesis/research/<slug>.md.
    """
    from genesis.config import RESEARCH_DIR
    import datetime

    # 1. Multi-Query Triangulation
    sub_queries = [
        topic,
        f"{topic} architecture technical details",
        f"{topic} comparison pros cons use cases",
    ]

    all_urls = []
    seen_urls = set()

    for q in sub_queries:
        out = web_search(q, max_results=3)
        found = re.findall(r"- \*\*URL\*\*: `(https?://[^`]+)`", out)
        for u in found:
            # Clean tracking parameters
            base_u = u.split("?")[0]
            if base_u not in seen_urls and not any(base_u.lower().endswith(x) for x in [".pdf", ".jpg", ".zip"]):
                seen_urls.add(base_u)
                all_urls.append(u)

    if not all_urls:
        return f"Deep Research Error: No accessible web sources found for topic '{topic}'."

    # 2. Deep Content Ingestion
    sources_data = []
    for u in all_urls:
        if len(sources_data) >= max_sources:
            break
        text = web_scrape(u, max_chars=3000)
        if "Web Scrape Error" not in text and len(text) > 200:
            lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
            summary_points = lines[:5]
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            page_title = title_match.group(1).strip() if title_match else urllib.parse.urlparse(u).netloc
            sources_data.append({
                "title": page_title,
                "url": u,
                "domain": urllib.parse.urlparse(u).netloc,
                "excerpts": summary_points,
                "full_text": text,
            })

    if not sources_data:
        return f"Deep Research Error: Failed to extract readable content from sources for '{topic}'."

    # 3. Assemble Structured Notebook-Style Report
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", topic.lower())[:50]
    report_file = RESEARCH_DIR / f"{slug}.md"

    report = [
        f"# Deep Research Analysis Report: {topic}",
        f"*Generated by Project Genesis | Date: {timestamp} | Sources Analyzed: {len(sources_data)}*\n",
        "## 1. Executive Summary & Core Insights",
        f"This deep research report synthesizes data and insights on **{topic}** gathered from {len(sources_data)} distinct primary and technical web sources.",
    ]

    for idx, s in enumerate(sources_data, 1):
        if s["excerpts"]:
            lead_point = s["excerpts"][0]
            report.append(f"- **Key Insight {idx}** ({s['domain']}): {lead_point}")

    report.append("\n## 2. Synthesized Topic Analysis")
    for idx, s in enumerate(sources_data, 1):
        report.append(f"\n### Perspective {idx}: {s['title']}")
        report.append(f"**Source**: `{s['url']}`\n")
        report.append("\n".join([f"> {p}" for p in s["excerpts"][:4]]))

    report.append("\n## 3. Source Attribution & Citations Matrix\n")
    report.append("| # | Source Title | Domain | Reference URL |")
    report.append("| :--- | :--- | :--- | :--- |")
    for idx, s in enumerate(sources_data, 1):
        clean_title = s['title'].replace("|", "-")[:45]
        report.append(f"| {idx} | {clean_title} | {s['domain']} | [Link]({s['url']}) |")

    final_report_md = "\n".join(report)

    # 4. Save to Sovereign Research Vault
    if save_to_vault:
        try:
            report_file.write_text(final_report_md, encoding="utf-8")
            vault_msg = f"\n\n---\n*Full Research Report saved to local vault:* `{report_file}`"
        except Exception:
            vault_msg = ""
    else:
        vault_msg = ""

    return final_report_md + vault_msg

