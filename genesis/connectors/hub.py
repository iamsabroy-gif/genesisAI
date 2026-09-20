"""
Project Genesis: Universal Sovereign Connector Hub.
Aggregates and dynamically exposes tools from active application connectors.
"""

from typing import Dict, Any, Callable, List
from genesis.connectors.base import BaseConnector
from genesis.connectors.macos_bridge import MacOSBridgeConnector
from genesis.connectors.web_research import WebResearchConnector


class ConnectorHub:
    """Central registry and dispatcher for all external application connectors."""

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self._register_default_connectors()

    def _register_default_connectors(self):
        # Register zero-config macOS Native Bridge
        macos_conn = MacOSBridgeConnector()
        if macos_conn.is_configured():
            self.register(macos_conn)

        # Register sovereign Web Research & Scraping Connector
        web_conn = WebResearchConnector()
        if web_conn.is_configured():
            self.register(web_conn)

    def register(self, connector: BaseConnector):
        """Register a new application connector."""
        self.connectors[connector.name] = connector

    def get_connector(self, name: str) -> BaseConnector | None:
        return self.connectors.get(name)

    def get_active_tool_map(self) -> Dict[str, Callable[..., Any]]:
        """Return unified tool mapping across all active/configured connectors."""
        tools = {}
        for conn in self.connectors.values():
            if conn.is_configured():
                tools.update(conn.get_tool_map())
        return tools

    def get_active_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return unified JSON function schemas across all active/configured connectors."""
        schemas = []
        for conn in self.connectors.values():
            if conn.is_configured():
                schemas.extend(conn.get_tool_schemas())
        return schemas

    def list_connectors(self) -> List[Dict[str, Any]]:
        """List all known connectors and their configuration status."""
        return [
            {
                "name": conn.name,
                "description": conn.description,
                "configured": conn.is_configured(),
                "status": conn.get_status(),
                "tool_count": len(conn.get_tool_schemas()),
            }
            for conn in self.connectors.values()
        ]


_default_hub = None


def get_default_hub() -> ConnectorHub:
    """Singleton getter for the global ConnectorHub."""
    global _default_hub
    if _default_hub is None:
        _default_hub = ConnectorHub()
    return _default_hub
