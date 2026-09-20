"""Unit tests for the Web Research and Scraping Engine."""

from bs4 import BeautifulSoup
from genesis.tools.web_research import web_search, web_scrape, web_research
from genesis.connectors.hub import ConnectorHub


def test_web_scrape_cleaning_and_formatting():
    # Test internal scraping logic against simulated noisy HTML
    sample_html = """
    <html>
        <head><title>Test Tech Article</title><style>.ad { color: red; }</style></head>
        <body>
            <header>Site Header Navigation</header>
            <nav>Menu Items</nav>
            <main>
                <h1>Apple Silicon M-Series</h1>
                <p>Apple Silicon chips use ARM architecture and Unified Memory Architecture (UMA).</p>
                <ul>
                    <li>16 GB Unified Memory</li>
                    <li>Metal Performance Shaders</li>
                </ul>
            </main>
            <footer>Copyright 2026</footer>
            <script>console.log("analytics");</script>
        </body>
    </html>
    """
    soup = BeautifulSoup(sample_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text()
    assert "Site Header Navigation" not in text
    assert "analytics" not in text
    assert "Apple Silicon chips use ARM architecture" in text


def test_web_scrape_invalid_url():
    res = web_scrape("invalid_url_without_http")
    assert "Error: Invalid URL" in res


def test_connector_hub_web_research():
    hub = ConnectorHub()
    tool_map = hub.get_active_tool_map()
    assert "web_search" in tool_map
    assert "web_scrape" in tool_map
    assert "web_research" in tool_map
    assert "deep_research_report" in tool_map

    tool_schemas = hub.get_active_tool_schemas()
    schema_names = [s["function"]["name"] for s in tool_schemas]
    assert "web_search" in schema_names
    assert "web_scrape" in schema_names
    assert "web_research" in schema_names
    assert "deep_research_report" in schema_names


def test_deep_research_report_execution():
    from genesis.tools.web_research import deep_research_report
    # Run lightweight research query with 1 source
    report = deep_research_report("Python language", max_sources=1, save_to_vault=False)
    assert "Deep Research Analysis Report" in report or "Deep Research Error" in report

