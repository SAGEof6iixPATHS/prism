"""Tests for prism.agentsview — AgentsviewDataSource."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from prism.agentsview import AgentsviewDataSource
from prism.datasource import SessionDataSource
from prism.parser import ProjectInfo, project_path_to_encoded_name


def _build_test_db(db_path: Path) -> None:
    """Create a minimal agentsview SQLite DB with the tables needed by the adapter."""
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


class TestAgentsviewDataSourceProtocol:
    def test_is_session_data_source(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        assert isinstance(AgentsviewDataSource(db), SessionDataSource)


class TestDiscoverProjects:
    def test_empty_db_returns_empty(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        ds = AgentsviewDataSource(db)
        assert ds.discover_projects() == []

    def test_one_project(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO sessions (session_id, project) VALUES (?, ?)",
            ("s1", "/home/user/proj"),
        )
        conn.commit()
        conn.close()

        ds = AgentsviewDataSource(db)
        projects = ds.discover_projects()
        assert len(projects) == 1
        expected_encoded = project_path_to_encoded_name("/home/user/proj")
        assert projects[0].encoded_name == expected_encoded
        assert projects[0].session_files == []

    def test_soft_deleted_excluded(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO sessions (session_id, project, deleted_at) VALUES (?, ?, ?)",
            ("s1", "/home/user/proj", "2026-04-20T10:00:00Z"),
        )
        conn.commit()
        conn.close()

        ds = AgentsviewDataSource(db)
        assert ds.discover_projects() == []

    def test_multiple_sessions_same_project_deduped(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        conn = sqlite3.connect(db)
        conn.executemany(
            "INSERT INTO sessions (session_id, project) VALUES (?, ?)",
            [("s1", "/home/user/proj"), ("s2", "/home/user/proj")],
        )
        conn.commit()
        conn.close()

        ds = AgentsviewDataSource(db)
        projects = ds.discover_projects()
        assert len(projects) == 1

    def test_multiple_distinct_projects(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        conn = sqlite3.connect(db)
        conn.executemany(
            "INSERT INTO sessions (session_id, project) VALUES (?, ?)",
            [("s1", "/home/user/alpha"), ("s2", "/home/user/beta")],
        )
        conn.commit()
        conn.close()

        ds = AgentsviewDataSource(db)
        projects = ds.discover_projects()
        assert len(projects) == 2
        names = {p.encoded_name for p in projects}
        assert project_path_to_encoded_name("/home/user/alpha") in names
        assert project_path_to_encoded_name("/home/user/beta") in names

    def test_null_project_excluded(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO sessions (session_id, project) VALUES (?, ?)",
            ("s1", None),
        )
        conn.commit()
        conn.close()

        ds = AgentsviewDataSource(db)
        assert ds.discover_projects() == []


class TestConnectionLifecycle:
    def test_close(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        ds = AgentsviewDataSource(db)
        ds.discover_projects()
        ds.close()
        assert ds._conn is None

    def test_context_manager(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        with AgentsviewDataSource(db) as ds:
            ds.discover_projects()
        assert ds._conn is None

    def test_safe_defaults(self, tmp_path: Path):
        db = tmp_path / "test.db"
        _build_test_db(db)
        ds = AgentsviewDataSource(db)
        proj = ds.discover_projects()
        assert ds.load_sessions(
            ProjectInfo(encoded_name="x", project_dir=Path("."), session_files=[])
        ) == []
        assert ds.find_claude_md(
            ProjectInfo(encoded_name="x", project_dir=Path("."), session_files=[])
        ) is None
