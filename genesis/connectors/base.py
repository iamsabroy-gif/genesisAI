"""
Base Connector Interface for Project Genesis.
Standardizes external application adapters and MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, List


class BaseConnector(ABC):
    """Abstract base class for all Genesis external application connectors."""

    name: str = "base_connector"
    description: str = "Abstract base connector"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if required local bridges, binaries, or credentials are valid."""
        pass

    @abstractmethod
    def get_tool_map(self) -> Dict[str, Callable[..., Any]]:
        """Return mapping of tool_name -> executable Python callable."""
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI-compatible JSON function schemas for this connector's tools."""
        pass

    def get_status(self) -> str:
        """Return human-readable status string for 'genesis status'."""
        configured = self.is_configured()
        status_tag = "[READY]" if configured else "[NOT CONFIGURED]"
        return f"{self.name} {status_tag}: {self.description}"
