#!/usr/bin/env python3
"""Query AICA todos database for summaries and analysis."""

import sqlite3
import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = r"D:\Users\Admin\.aica\aica.db"


def get_connection(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def query_todos(
    db_path: str = DEFAULT_DB,
    status: str = None,
    group_name: str = None,
    days: int = None,
    limit: int = 50,
    include_events: bool = False,
    event_limit: int = 5,
) -> list[dict]:
    """Query todos with optional filters."""
    conn = get_connection(db_path)
    try:
        sql = "SELECT * FROM todos WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)

        if group_name:
            sql += " AND group_name LIKE ?"
            params.append(f"%{group_name}%")

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            sql += " AND updated_at >= ?"
            params.append(cutoff)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        results = []

        for row in rows:
            todo = dict(row)
            if include_events:
                events = conn.execute(
                    "SELECT * FROM todo_timeline_events WHERE todo_id = ? ORDER BY timestamp DESC LIMIT ?",
                    [todo["id"], event_limit],
                ).fetchall()
                todo["events"] = [dict(e) for e in events]
            results.append(todo)

        return results
    finally:
        conn.close()


def query_todo_detail(todo_id: str, db_path: str = DEFAULT_DB, event_limit: int = 20) -> dict | None:
    """Get single todo with all timeline events."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", [todo_id]).fetchone()
        if not row:
            return None

        todo = dict(row)
        events = conn.execute(
            "SELECT * FROM todo_timeline_events WHERE todo_id = ? ORDER BY timestamp DESC LIMIT ?",
            [todo_id, event_limit],
        ).fetchall()
        todo["events"] = [dict(e) for e in events]

        # Get project info if available
        projects = conn.execute(
            """SELECT p.* FROM projects p
               JOIN project_group_aliases pa ON p.id = pa.project_id
               WHERE pa.group_name = ?""",
            [todo.get("group_name", "")],
        ).fetchall()
        todo["projects"] = [dict(p) for p in projects]

        return todo
    finally:
        conn.close()


def get_summary_stats(db_path: str = DEFAULT_DB, days: int = 30) -> dict:
    """Get summary statistics for todos."""
    conn = get_connection(db_path)
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        total = conn.execute("SELECT count(*) FROM todos").fetchone()[0]
        open_count = conn.execute("SELECT count(*) FROM todos WHERE status = 'open'").fetchone()[0]
        done_count = conn.execute("SELECT count(*) FROM todos WHERE status = 'done'").fetchone()[0]
        recent = conn.execute("SELECT count(*) FROM todos WHERE updated_at >= ?", [cutoff]).fetchone()[0]

        by_group = conn.execute(
            "SELECT group_name, count(*) as cnt FROM todos WHERE group_name != '' GROUP BY group_name ORDER BY cnt DESC"
        ).fetchall()

        by_status_recent = conn.execute(
            "SELECT status, count(*) as cnt FROM todos WHERE updated_at >= ? GROUP BY status",
            [cutoff],
        ).fetchall()

        return {
            "total": total,
            "open": open_count,
            "done": done_count,
            "recent_days": days,
            "recent_updated": recent,
            "by_group": [{"group": r[0], "count": r[1]} for r in by_group],
            "recent_by_status": [{"status": r[0], "count": r[1]} for r in by_status_recent],
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Query AICA todos database")
    parser.add_argument("--db", default=DEFAULT_DB, help="Database path")
    parser.add_argument("--action", choices=["list", "detail", "stats"], default="list")

    # Filters for list
    parser.add_argument("--status", choices=["open", "done"])
    parser.add_argument("--group", help="Filter by group name (partial match)")
    parser.add_argument("--days", type=int, help="Only items updated within N days")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--with-events", action="store_true", help="Include timeline events")

    # For detail
    parser.add_argument("--todo-id", help="Todo ID for detail view")

    parser.add_argument("--format", choices=["json", "text"], default="json")

    args = parser.parse_args()

    if args.action == "stats":
        result = get_summary_stats(args.db, args.days or 365)
    elif args.action == "detail":
        if not args.todo_id:
            print("Error: --todo-id required for detail", file=sys.stderr)
            sys.exit(1)
        result = query_todo_detail(args.db, args.todo_id, event_limit=args.limit)
        if not result:
            print(f"Todo not found: {args.todo_id}", file=sys.stderr)
            sys.exit(1)
    else:
        result = query_todos(
            db_path=args.db,
            status=args.status,
            group_name=args.group,
            days=args.days,
            limit=args.limit,
            include_events=args.with_events,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
