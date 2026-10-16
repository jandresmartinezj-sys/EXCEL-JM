-- JARVIZ · modelo de datos v1 (SQLite). Ver DATA_MODEL.md.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner','staff','client')),
  client_id INTEGER REFERENCES clients(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (role <> 'client' OR client_id IS NOT NULL)
);

-- Tokens de sesión y tokens personales (Atajos de iOS). Solo se guarda el hash.
CREATE TABLE IF NOT EXISTS tokens (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL CHECK (kind IN ('session','personal')),
  label TEXT,
  expires_at TEXT NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  nit TEXT,
  segment TEXT,
  plan TEXT,
  monthly_fee REAL NOT NULL DEFAULT 0,
  start_date TEXT,
  status TEXT NOT NULL DEFAULT 'Activo' CHECK (status IN ('Activo','Suspendido','Retirado')),
  risk TEXT NOT NULL DEFAULT 'Bajo' CHECK (risk IN ('Bajo','Medio','Alto')),
  nps INTEGER CHECK (nps BETWEEN 0 AND 10),
  is_demo INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prospects (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (date('now')),
  name TEXT NOT NULL,
  segment TEXT,
  channel TEXT,
  contact TEXT,
  stage TEXT NOT NULL DEFAULT '1 Prospecto',
  plan TEXT,
  monthly_value REAL NOT NULL DEFAULT 0,
  next_step TEXT,
  next_step_date TEXT,
  owner TEXT,
  lost_reason TEXT,
  dedupe_key TEXT UNIQUE,
  is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS obligations (
  id INTEGER PRIMARY KEY,
  client_id INTEGER NOT NULL REFERENCES clients(id),
  kind TEXT NOT NULL,
  period TEXT,
  due_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Pendiente'
    CHECK (status IN ('Pendiente','En preparación','Enviada al cliente','Aprobada','Presentada')),
  owner TEXT,
  reference TEXT,
  source_note TEXT,            -- de dónde salió la fecha (calendario oficial, resolución…)
  is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY,
  number TEXT NOT NULL,
  client_id INTEGER NOT NULL REFERENCES clients(id),
  issue_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  amount REAL NOT NULL CHECK (amount >= 0),
  paid REAL NOT NULL DEFAULT 0 CHECK (paid >= 0),
  paid_date TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS time_entries (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  client_id INTEGER NOT NULL REFERENCES clients(id),
  activity TEXT,
  hours REAL NOT NULL CHECK (hours > 0 AND hours <= 24),
  note TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  client_id INTEGER NOT NULL REFERENCES clients(id),
  title TEXT NOT NULL,
  kind TEXT,
  period TEXT,
  source TEXT,                 -- procedencia (correo, portal, carga manual…)
  sha256 TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tareas: unidad de trabajo de JARVIZ y de las personas. Estado explícito.
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'manual',
  agent TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','running','awaiting_approval','completed','failed','cancelled')),
  client_id INTEGER REFERENCES clients(id),
  due_date TEXT,
  assignee TEXT,
  input_json TEXT,
  result_json TEXT,
  error TEXT,
  idempotency_key TEXT UNIQUE,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY,
  task_id INTEGER REFERENCES tasks(id),
  action TEXT NOT NULL,
  level INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  requested_by TEXT NOT NULL,
  decided_by TEXT,
  decided_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY,
  rule TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  severity TEXT NOT NULL CHECK (severity IN ('alta','media','baja')),
  title TEXT NOT NULL,
  why TEXT NOT NULL,
  evidence TEXT NOT NULL,
  impact TEXT NOT NULL,
  confidence TEXT NOT NULL,
  action TEXT NOT NULL,
  decision TEXT NOT NULL,
  client_id INTEGER REFERENCES clients(id),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','ack','resolved')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Memoria empresarial por niveles, con procedencia y retención.
CREATE TABLE IF NOT EXISTS memory (
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL CHECK (scope IN ('work','business','client','decision','preference')),
  client_id INTEGER REFERENCES clients(id),
  key TEXT,
  content TEXT NOT NULL,
  source TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT,
  deleted_at TEXT,
  CHECK (scope <> 'client' OR client_id IS NOT NULL)
);

-- Memoria de conversación (retención corta).
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  role TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS llm_usage (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  model TEXT NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens INTEGER NOT NULL DEFAULT 0,
  task_id INTEGER
);

-- Registro de auditoría: solo inserción, encadenado por hash.
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  detail_json TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log es de solo inserción'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log es de solo inserción'); END;

CREATE INDEX IF NOT EXISTS ix_obl_due ON obligations(due_date);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_mem_scope ON memory(scope, client_id);
