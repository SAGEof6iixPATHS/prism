"""Tests for prism.cli — CLI commands and datasource wiring."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from prism.cli import app, resolve_agentsview_db

runner = CliRunner()


# ---------------------------------------------------------------------------
# resolve_agentsview_db priority chain
# ---------------------------------------------------------------------------


class TestResolveAgentsviewDb:
    def test_explicit_path_wins(self, tmp_path: Path) -> None:
        p = tmp_path / "my.db"
        assert resolve_agentsview_db(p) == p

    def test_agentsview_data_dir_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGENTSVIEW_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("AGENT_VIEWER_DATA_DIR", raising=False)
        assert resolve_agentsview_db() == tmp_path / "sessions.db"

    def test_agent_viewer_data_dir_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AGENTSVIEW_DATA_DIR", raising=False)
        monkeypatch.setenv("AGENT_VIEWER_DATA_DIR", str(tmp_path))
        assert resolve_agentsview_db() == tmp_path / "sessions.db"

    def test_agentsview_takes_precedence_over_agent_viewer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        newer = tmp_path / "newer"
        older = tmp_path / "older"
        newer.mkdir()
        older.mkdir()
        monkeypatch.setenv("AGENTSVIEW_DATA_DIR", str(newer))
        monkeypatch.setenv("AGENT_VIEWER_DATA_DIR", str(older))
        assert resolve_agentsview_db() == newer / "sessions.db"

    def test_default_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENTSVIEW_DATA_DIR", raising=False)
        monkeypatch.delenv("AGENT_VIEWER_DATA_DIR", raising=False)
        result = resolve_agentsview_db()
        assert result == Path.home() / ".agentsview" / "sessions.db"

    def test_explicit_overrides_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGENTSVIEW_DATA_DIR", str(tmp_path / "env"))
        explicit = tmp_path / "explicit.db"
        assert resolve_agentsview_db(explicit) == explicit


# ---------------------------------------------------------------------------
# DB builder (reused from test_agentsview)
# ---------------------------------------------------------------------------


def _build_test_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            project TEXT,
            model TEXT,
            created_at TEXT,
            deleted_at TEXT
        );
        CREATE TABLE messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            uuid TEXT,
            parent_uuid TEXT,
            is_sidechain INTEGER DEFAULT 0,
            cwd TEXT,
            version TEXT,
            git_branch TEXT,
            is_compact_boundary INTEGER DEFAULT 0,
            is_system INTEGER DEFAULT 0
        );
        CREATE TABLE tool_calls (
            tool_call_id TEXT PRIMARY KEY,
            message_id TEXT,
            tool_name TEXT,
            input_json TEXT,
            output_text TEXT,
            is_error INTEGER DEFAULT 0
        );
    """)
    conn.close()


def _populate_db(db_path: Path) -> None:
    """Insert a minimal project with one session and a user+assistant exchange."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        ("sess-1", "/home/user/proj", "claude-4", "2026-04-20T10:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("m1", "sess-1", "user", "hello", "2026-04-20T10:00:00Z",
         "u1", None, 0, "/home/user/proj", "2.1.98", "main", 0, 0),
    )
    conn.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("m2", "sess-1", "assistant", "hi there", "2026-04-20T10:00:01Z",
         "u2", "u1", 0, "/home/user/proj", "2.1.98", "main", 0, 0),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CLI: --source agentsview
# ---------------------------------------------------------------------------


class TestAnalyzeAgentsview:
    def test_analyze_agentsview_source(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sessions.db"
        _build_test_db(db_path)
        _populate_db(db_path)
        result = runner.invoke(
            app, ["analyze", "--source", "agentsview", "--agentsview-db", str(db_path)]
        )
        assert result.exit_code == 0
        assert "PRISM Health Report" in result.output

    def test_analyze_agentsview_json(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sessions.db"
        _build_test_db(db_path)
        _populate_db(db_path)
        result = runner.invoke(
            app,
            ["analyze", "--source", "agentsview", "--agentsview-db", str(db_path), "--json"],
        )
        assert result.exit_code == 0
        assert '"overall_grade"' in result.output

    def test_analyze_agentsview_db_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["analyze", "--source", "agentsview", "--agentsview-db", str(tmp_path / "nope.db")],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_analyze_agentsview_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sessions.db"
        _build_test_db(db_path)
        _populate_db(db_path)
        monkeypatch.setenv("AGENTSVIEW_DATA_DIR", str(tmp_path))
        result = runner.invoke(app, ["analyze", "--source", "agentsview"])
        assert result.exit_code == 0


class TestAdviseAgentsview:
    def test_advise_agentsview_source(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sessions.db"
        _build_test_db(db_path)
        _populate_db(db_path)
        result = runner.invoke(
            app, ["advise", "--source", "agentsview", "--agentsview-db", str(db_path)]
        )
        assert result.exit_code == 0


class TestDashboardAgentsview:
    def test_dashboard_agentsview_source(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sessions.db"
        _build_test_db(db_path)
        _populate_db(db_path)
        result = runner.invoke(
            app,
            ["dashboard", "--source", "agentsview", "--agentsview-db", str(db_path), "--no-open"],
        )
        assert result.exit_code == 0
        assert "Dashboard generated" in result.output


# ---------------------------------------------------------------------------
# CLI: default --source jsonl unchanged
# ---------------------------------------------------------------------------


class TestDefaultJsonlBehavior:
    def test_analyze_default_no_sessions(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["analyze", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "No Claude Code sessions found" in result.output

    def test_analyze_default_with_sessions(self, tmp_path: Path) -> None:
        proj_dir = tmp_path / "test-project"
        proj_dir.mkdir()
        session = proj_dir / "session1.jsonl"
        session.write_text(
            '{"uuid":"u1","parentUuid":null,"isSidechain":false,'
            '"sessionId":"s1","timestamp":"2026-04-20T10:00:00Z",'
            '"version":"2.1","cwd":"/tmp","type":"user",'
            '"message":{"content":[{"type":"text","text":"hi"}]}}\n'
            '{"uuid":"u2","parentUuid":"u1","isSidechain":false,'
            '"sessionId":"s1","timestamp":"2026-04-20T10:00:01Z",'
            '"version":"2.1","cwd":"/tmp","type":"assistant",'
            '"message":{"content":[{"type":"text","text":"hello"}]}}\n',
            encoding="utf-8",
        )
        result = runner.invoke(app, ["analyze", "--base-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "PRISM Health Report" in result.output
