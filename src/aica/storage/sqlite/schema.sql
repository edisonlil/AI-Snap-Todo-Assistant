PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  current_summary TEXT NOT NULL DEFAULT '',
  group_name TEXT NOT NULL DEFAULT '',
  environment TEXT NOT NULL DEFAULT '',
  ticket_type TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_status_updated
ON todos(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_todos_group_name
ON todos(group_name);

CREATE TABLE IF NOT EXISTS todo_timeline_events (
  id TEXT PRIMARY KEY,
  todo_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'analysis',
  scenario TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timeline_todo_time
ON todo_timeline_events(todo_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS todo_timeline_attachments (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES todo_timeline_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attachments_event
ON todo_timeline_attachments(event_id);

CREATE TABLE IF NOT EXISTS todo_bindings (
  todo_id TEXT NOT NULL,
  integration_id TEXT NOT NULL,
  external_id TEXT NOT NULL DEFAULT '',
  external_url TEXT NOT NULL DEFAULT '',
  last_event_id TEXT NOT NULL DEFAULT '',
  last_event_type TEXT NOT NULL DEFAULT '',
  last_sync_status TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  deleted_locally INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(todo_id, integration_id),
  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  customer_name TEXT NOT NULL DEFAULT '',
  task_order_no TEXT NOT NULL DEFAULT '',
  follow_up_started_at TEXT NOT NULL DEFAULT '',
  support_ended_at TEXT NOT NULL DEFAULT '',
  product_line TEXT NOT NULL DEFAULT '',
  product_version TEXT NOT NULL DEFAULT '',
  project_manager TEXT NOT NULL DEFAULT '',
  project_level TEXT NOT NULL DEFAULT 'normal',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_support_end
ON projects(support_ended_at);

CREATE INDEX IF NOT EXISTS idx_projects_project_name
ON projects(project_name);

CREATE INDEX IF NOT EXISTS idx_projects_task_order_no
ON projects(task_order_no);

CREATE TABLE IF NOT EXISTS project_group_aliases (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  alias_name TEXT NOT NULL,
  alias_name_normalized TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_project_group_aliases_normalized
ON project_group_aliases(alias_name_normalized, project_id);

CREATE INDEX IF NOT EXISTS idx_project_group_alias_lookup
ON project_group_aliases(alias_name_normalized);

CREATE TABLE IF NOT EXISTS todo_project_links (
  todo_id TEXT PRIMARY KEY,
  project_id TEXT,
  match_status TEXT NOT NULL,
  match_reason TEXT NOT NULL DEFAULT '',
  matched_group_name TEXT NOT NULL DEFAULT '',
  matched_alias TEXT NOT NULL DEFAULT '',
  project_snapshot_json TEXT NOT NULL DEFAULT '{}',
  matched_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);
