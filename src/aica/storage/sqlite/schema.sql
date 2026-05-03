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
  product_line TEXT NOT NULL DEFAULT '',
  ticket_type TEXT NOT NULL DEFAULT '',
  ach_no TEXT NOT NULL DEFAULT '',
  ach_filled_at TEXT NOT NULL DEFAULT '',
  ticket_version TEXT NOT NULL DEFAULT '',
  feature_point TEXT NOT NULL DEFAULT '',
  feature_point_source TEXT NOT NULL DEFAULT '',
  root_cause_desc TEXT NOT NULL DEFAULT '',
  root_cause_desc_source TEXT NOT NULL DEFAULT '',
  root_cause TEXT NOT NULL DEFAULT '',
  root_cause_source TEXT NOT NULL DEFAULT '',
  conclusion_content TEXT NOT NULL DEFAULT '',
  conclusion_updated_at TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT NOT NULL DEFAULT '',
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
  event_type TEXT NOT NULL DEFAULT 'default',
  payload_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS log_analysis_tasks (
  id TEXT PRIMARY KEY,
  todo_id TEXT NOT NULL,
  timeline_entry_id TEXT NOT NULL,
  status TEXT NOT NULL,
  current_step TEXT NOT NULL DEFAULT '',
  raw_command TEXT NOT NULL DEFAULT '',
  parsed_focus_json TEXT NOT NULL DEFAULT '{}',
  attachment_snapshot_json TEXT NOT NULL DEFAULT '[]',
  investigation_context_json TEXT NOT NULL DEFAULT '{}',
  evidence_bundle_json TEXT NOT NULL DEFAULT '{}',
  result_summary TEXT NOT NULL DEFAULT '',
  result_payload_json TEXT NOT NULL DEFAULT '{}',
  error_message TEXT NOT NULL DEFAULT '',
  model_binding_used TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT '',
  failed_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE,
  FOREIGN KEY(timeline_entry_id) REFERENCES todo_timeline_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_log_analysis_tasks_todo_created
ON log_analysis_tasks(todo_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_log_analysis_tasks_timeline_entry
ON log_analysis_tasks(todo_id, timeline_entry_id);

CREATE INDEX IF NOT EXISTS idx_log_analysis_tasks_status_updated
ON log_analysis_tasks(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS error_codes (
  code TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  meaning TEXT NOT NULL DEFAULT '',
  suggestion TEXT NOT NULL DEFAULT '',
  source_name TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL DEFAULT 'online_doc',
  source_url TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  raw_payload_json TEXT NOT NULL DEFAULT '{}',
  cache_status TEXT NOT NULL DEFAULT 'fresh',
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_error_codes_category
ON error_codes(category);

CREATE INDEX IF NOT EXISTS idx_error_codes_last_seen
ON error_codes(last_seen_at DESC);

CREATE TABLE IF NOT EXISTS todo_conclusion_attachments (
  id TEXT PRIMARY KEY,
  todo_id TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(todo_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conclusion_attachments_todo
ON todo_conclusion_attachments(todo_id);

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

CREATE TABLE IF NOT EXISTS project_environments (
  id TEXT PRIMARY KEY,
  project_id TEXT DEFAULT '',
  env_name TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'project',
  env_type TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK(scope IN ('global', 'project')),
  CHECK((scope = 'global' AND (project_id = '' OR project_id IS NULL)) OR (scope = 'project' AND project_id <> '')),
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_environments_project
ON project_environments(project_id, scope, is_active, sort_order, updated_at DESC);

CREATE TABLE IF NOT EXISTS environment_access_entries (
  id TEXT PRIMARY KEY,
  environment_id TEXT NOT NULL,
  access_name TEXT NOT NULL,
  access_type TEXT NOT NULL DEFAULT '',
  url_or_host TEXT NOT NULL DEFAULT '',
  username TEXT NOT NULL DEFAULT '',
  password_encrypted TEXT NOT NULL DEFAULT '',
  otp_secret_encrypted TEXT NOT NULL DEFAULT '',
  requires_otp INTEGER NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT '',
  open_command TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(environment_id) REFERENCES project_environments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_environment_access_entries_environment
ON environment_access_entries(environment_id, is_active, sort_order, updated_at DESC);
