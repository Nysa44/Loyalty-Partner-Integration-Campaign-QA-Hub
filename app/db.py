import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS partners (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, earn_rate REAL NOT NULL CHECK(earn_rate >= 0)
);
CREATE TABLE IF NOT EXISTS members (
  id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  partner_id TEXT NOT NULL REFERENCES partners(id),
  transaction_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES members(id),
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  points INTEGER NOT NULL,
  campaign_id TEXT,
  source_file TEXT NOT NULL,
  posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(partner_id, transaction_id)
);
CREATE TABLE IF NOT EXISTS rejects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  partner_id TEXT NOT NULL,
  transaction_id TEXT,
  source_file TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  details TEXT NOT NULL,
  row_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feed_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  partner_id TEXT NOT NULL,
  source_file TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  row_count INTEGER NOT NULL,
  posted_count INTEGER NOT NULL,
  rejected_count INTEGER NOT NULL,
  duplicate_count INTEGER NOT NULL DEFAULT 0,
  declared_total REAL NOT NULL DEFAULT 0,
  posted_total REAL NOT NULL DEFAULT 0,
  rejected_total REAL NOT NULL DEFAULT 0,
  duplicate_total REAL NOT NULL DEFAULT 0,
  discrepancy REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS campaigns (
  id TEXT PRIMARY KEY,
  partner_id TEXT NOT NULL REFERENCES partners(id),
  name TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  budget_cap REAL,
  earn_multiplier REAL NOT NULL,
  bonus_weekends INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  entity_key TEXT NOT NULL,
  details TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
