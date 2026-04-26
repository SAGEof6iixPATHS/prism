"""AgentsviewDataSource — reads session data from the agentsview SQLite DB."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from prism.parser import (
    AssistantRecord,
    ContentBlock,
    ParseResult,
    ProjectInfo,
    SessionRecord,
    SystemRecord,
    UserRecord,
    classify_system_message,
    project_path_to_encoded_name,
)


def _envelope_kwargs(row: sqlite3.Row) -> dict:
    """Extract Envelope constructor kwargs from a messages row."""
    return {
        "uuid": row["uuid"] or "",
        "parent_uuid": row["parent_uuid"],
        "is_sidechain": bool(row["is_sidechain"]),
        "session_id": row["session_id"],
        "timestamp": row["timestamp"] or "",
        "version": row["version"] or "",
        "cwd": row["cwd"] or "",
        "git_branch": row["git_branch"],
        "type": row["role"] or "",
        "raw": {},
    }


def _row_to_record(row: sqlite3.Row) -> SessionRecord | None:
    """Convert a messages table row to a typed SessionRecord."""
    kwargs = _envelope_kwargs(row)
    content_text = row["content"] or ""

    if row["is_compact_boundary"]:
        kwargs["type"] = "system"
        return SystemRecord(**kwargs, subtype="compact_boundary", summary=content_text[:200])

    if row["is_system"]:
        kwargs["type"] = "system"
        subtype = classify_system_message(content_text)
        return SystemRecord(**kwargs, subtype=subtype, summary=content_text[:200])

    role = row["role"]
    blocks = [ContentBlock(type="text", text=content_text)] if content_text else []

    if role == "assistant":
        return AssistantRecord(**kwargs, content=blocks)
    if role == "user":
        return UserRecord(**kwargs, content=blocks)
    if role == "system":
        return SystemRecord(**kwargs, subtype=None, summary=content_text[:200])

    return None


class AgentsviewDataSource:
    """Data source backed by an agentsview SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._project_paths: dict[str, str] = {}  # encoded_name → original DB path

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> AgentsviewDataSource:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def discover_projects(self) -> list[ProjectInfo]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT DISTINCT project FROM sessions"
            " WHERE deleted_at IS NULL AND project IS NOT NULL"
            " ORDER BY project"
        ).fetchall()
        projects: list[ProjectInfo] = []
        for row in rows:
            project_path = row["project"]
            encoded = project_path_to_encoded_name(project_path)
            self._project_paths[encoded] = project_path
            # Synthetic non-filesystem path — agentsview projects have no local directory
            projects.append(ProjectInfo(
                encoded_name=encoded,
                project_dir=Path(f"agentsview://{encoded}"),
                session_files=[],
            ))
        return projects

    def _resolve_project_path(self, encoded_name: str) -> str:
        """Get the original DB project path from encoded_name."""
        if encoded_name in self._project_paths:
            return self._project_paths[encoded_name]
        # Fallback: query DB directly for the original path
        conn = self._connect()
        rows = conn.execute(
            "SELECT DISTINCT project FROM sessions"
            " WHERE project IS NOT NULL AND deleted_at IS NULL"
        ).fetchall()
        for row in rows:
            if project_path_to_encoded_name(row["project"]) == encoded_name:
                self._project_paths[encoded_name] = row["project"]
                return row["project"]
        return ""

    def load_sessions(self, project: ProjectInfo) -> list[ParseResult]:
        project_path = self._resolve_project_path(project.encoded_name)
        if not project_path:
            return []
        conn = self._connect()
        session_rows = conn.execute(
            "SELECT session_id FROM sessions"
            " WHERE project = ? AND deleted_at IS NULL",
            (project_path,),
        ).fetchall()
        if not session_rows:
            return []

        session_ids = [r["session_id"] for r in session_rows]
        placeholders = ",".join("?" * len(session_ids))
        msg_rows = conn.execute(
            f"SELECT * FROM messages WHERE session_id IN ({placeholders})"
            " ORDER BY timestamp",
            session_ids,
        ).fetchall()

        grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in msg_rows:
            grouped[row["session_id"]].append(row)

        # Order sessions by latest message timestamp (most recent first)
        def _latest_ts(sid: str) -> str:
            msgs = grouped.get(sid, [])
            return msgs[-1]["timestamp"] if msgs else ""

        results: list[ParseResult] = []
        for sid in sorted(session_ids, key=_latest_ts, reverse=True):
            records = [_row_to_record(r) for r in grouped.get(sid, [])]
            records = [r for r in records if r is not None]
            results.append(ParseResult(
                path=Path(f"agentsview://{sid}.jsonl"),
                records=records,
            ))
        return results

    def find_claude_md(self, project: ProjectInfo) -> Path | None:
        return None
