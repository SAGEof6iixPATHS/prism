"""Tests for prism.datasource — SessionDataSource protocol."""

from __future__ import annotations

from pathlib import Path

from prism.datasource import SessionDataSource
from prism.parser import ParseResult, ProjectInfo


class _MockDataSource:
    """Minimal implementation that satisfies the protocol."""

    def discover_projects(self) -> list[ProjectInfo]:
        return []

    def load_sessions(self, project: ProjectInfo) -> list[ParseResult]:
        return []

    def find_claude_md(self, project: ProjectInfo) -> Path | None:
        return None


class TestSessionDataSourceProtocol:
    def test_mock_is_instance(self):
        assert isinstance(_MockDataSource(), SessionDataSource)

    def test_discover_projects_returns_list(self):
        ds = _MockDataSource()
        assert ds.discover_projects() == []

    def test_load_sessions_returns_list(self, tmp_path):
        ds = _MockDataSource()
        proj = ProjectInfo(
            encoded_name="test",
            project_dir=tmp_path,
            session_files=[],
        )
        assert ds.load_sessions(proj) == []

    def test_find_claude_md_returns_none(self, tmp_path):
        ds = _MockDataSource()
        proj = ProjectInfo(
            encoded_name="test",
            project_dir=tmp_path,
            session_files=[],
        )
        assert ds.find_claude_md(proj) is None
