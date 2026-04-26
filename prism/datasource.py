"""Data source protocol for PRISM.

Defines the interface that all session backends must implement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from prism.parser import ParseResult, ProjectInfo


@runtime_checkable
class SessionDataSource(Protocol):
    """Backend-agnostic interface for session data access."""

    def discover_projects(self) -> list[ProjectInfo]: ...

    def load_sessions(self, project: ProjectInfo) -> list[ParseResult]: ...

    def find_claude_md(self, project: ProjectInfo) -> Path | None: ...
