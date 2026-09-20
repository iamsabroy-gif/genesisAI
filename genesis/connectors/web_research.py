"""
Project Genesis: Web Research Connector.
Integrates DuckDuckGo public search, semantic web scraping, and deep research synthesis.
"""

from typing import Dict, Any, Callable, List
from genesis.connectors.base import BaseConnector
from genesis.tools.web_research import web_search, web_scrape, web_research, deep_research_report
from genesis.tools.person_diligence import person_due_diligence


class WebResearchConnector(BaseConnector):
    """Sovereign web search, scraping, and research connector."""

    name = "web_research"
    description = "Public Web Search, Semantic HTML-to-Markdown Scraper & Deep Research Engine"

    def is_configured(self) -> bool:
        # Standard internet connectivity required; always available if socket connection works
        return True

    def get_tool_map(self) -> Dict[str, Callable[..., Any]]:
        return {
            "web_search": web_search,
            "web_scrape": web_scrape,
            "web_research": web_research,
            "deep_research_report": deep_research_report,
            "person_due_diligence": person_due_diligence,
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the public web using DuckDuckGo (zero API key needed). Returns titles, snippets, and clean URLs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search keywords or question.",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Number of top results to return (default: 5).",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_scrape",
                    "description": "Fetch and convert any webpage into clean semantic Markdown, stripping ads, navigation, and boilerplate.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The full HTTP or HTTPS URL of the webpage to scrape.",
                            },
                            "max_chars": {
                                "type": "integer",
                                "description": "Maximum characters to extract to protect memory/tokens (default: 4000).",
                                "default": 4000,
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_research",
                    "description": "Perform multi-source autonomous web research on any topic: searches, scrapes top pages, and builds a consolidated dossier.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The subject, technology, or topic to research.",
                            },
                            "max_sources": {
                                "type": "integer",
                                "description": "Number of unique web pages to scrape and synthesize (default: 3).",
                                "default": 3,
                            },
                        },
                        "required": ["topic"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "deep_research_report",
                    "description": "NotebookLM-style Deep Research Engine. Multi-query search, multi-source scraping, synthesis of insights, and archives a Markdown report to ~/.genesis/research/.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The complex subject or question to analyze and report on.",
                            },
                            "max_sources": {
                                "type": "integer",
                                "description": "Maximum primary sources to ingest and cross-reference (default: 5).",
                                "default": 5,
                            },
                        },
                        "required": ["topic"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "person_due_diligence",
                    "description": "Perform OSINT background verification on an educator, tutor, or contractor. Scans professional, tutoring, and academic pillars, calculates a 1-10 triangulation score, generates safety checklist, and archives to vault.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Full name of the individual to investigate.",
                            },
                            "location": {
                                "type": "string",
                                "description": "City, area, or locality (e.g., 'Kolkata', 'Bangalore', 'Salt Lake').",
                                "default": "",
                            },
                            "affiliation": {
                                "type": "string",
                                "description": "Subject, school, or organization (e.g., 'Math teacher', 'Physics tutor', 'DPS').",
                                "default": "",
                            },
                            "identifier": {
                                "type": "string",
                                "description": "Known phone number, email handle, or unique ID to resolve collisions.",
                                "default": "",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
        ]
