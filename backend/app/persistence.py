"""Small durable SQLite repository for the hackathon deployment.

The schema is intentionally compact, but all security-sensitive state survives
process restarts: users, organizations, API keys, proposals, decisions,
approvals, payment orders, audit events, idempotency keys, and webhook events.
"""
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("DATABASE_PATH", "agentshield.db"))


def _conn() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _conn() as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS organizations (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS api_keys (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, key_hash TEXT UNIQUE NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evaluations (proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS payments (approval_id TEXT PRIMARY KEY, order_id TEXT UNIQUE NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, organization_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS idempotency_keys (key TEXT PRIMARY KEY, organization_id TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS webhook_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload TEXT NOT NULL, received_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS policies (organization_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        """)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_organization(name: str) -> str:
    org_id = secrets.token_urlsafe(12)
    with _conn() as db: db.execute("INSERT INTO organizations VALUES (?, ?, ?)", (org_id, name, now()))
    return org_id


def create_user(org_id: str, email: str, password_hash: str, role: str = "owner") -> str:
    user_id = secrets.token_urlsafe(12)
    with _conn() as db: db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (user_id, org_id, email.lower(), password_hash, role, now()))
    return user_id


def get_user(email: str) -> sqlite3.Row | None:
    with _conn() as db: return db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()


def issue_api_key(org_id: str, label: str) -> tuple[str, str]:
    key_id, raw = secrets.token_urlsafe(12), "ash_" + secrets.token_urlsafe(32)
    with _conn() as db: db.execute("INSERT INTO api_keys VALUES (?, ?, ?, ?, ?, NULL)", (key_id, org_id, hash_secret(raw), label, now()))
    return key_id, raw


def organization_for_api_key(raw: str) -> str | None:
    with _conn() as db:
        row = db.execute("SELECT organization_id FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL", (hash_secret(raw),)).fetchone()
    return row["organization_id"] if row else None


def save_payload(table: str, key: str, payload: dict[str, Any], organization_id: str = "demo") -> None:
    allowed = {"proposals": "id", "evaluations": "proposal_id", "approvals": "id"}
    if table not in allowed: raise ValueError("Unsupported persistence table")
    column = allowed[table]
    with _conn() as db:
        if table == "proposals": db.execute("INSERT OR REPLACE INTO proposals(id, organization_id, payload, created_at) VALUES (?, ?, ?, ?)", (key, organization_id, json.dumps(payload, default=str), now()))
        elif table == "evaluations": db.execute("INSERT OR REPLACE INTO evaluations VALUES (?, ?, ?)", (key, json.dumps(payload, default=str), now()))
        else: db.execute("INSERT OR REPLACE INTO approvals VALUES (?, ?, ?, ?)", (key, str(payload.get("proposal_id")), json.dumps(payload, default=str), now()))


def load_payloads(table: str) -> list[dict[str, Any]]:
    queries = {"proposals": "SELECT payload FROM proposals", "evaluations": "SELECT payload FROM evaluations", "approvals": "SELECT payload FROM approvals"}
    if table not in queries: raise ValueError("Unsupported persistence table")
    with _conn() as db: rows = db.execute(queries[table]).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def save_payment(approval_id: str, order_id: str, status: str, payload: dict[str, Any]) -> None:
    with _conn() as db: db.execute("INSERT OR REPLACE INTO payments VALUES (?, ?, ?, ?, ?)", (approval_id, order_id, status, json.dumps(payload, default=str), now()))


def load_payments() -> list[dict[str, Any]]:
    with _conn() as db: rows = db.execute("SELECT approval_id, order_id, status, payload FROM payments").fetchall()
    return [{"approval_id": row["approval_id"], "order_id": row["order_id"], "status": row["status"], "payload": json.loads(row["payload"])} for row in rows]


def captured_total() -> float:
    total = 0.0
    for payment in load_payments():
        if payment["status"] != "COMPLETED": continue
        for unit in payment["payload"].get("purchase_units", []):
            captures = unit.get("payments", {}).get("captures", [])
            for capture in captures: total += float(capture.get("amount", {}).get("value", 0))
    return total


def save_policy(organization_id: str, payload: dict[str, Any]) -> None:
    with _conn() as db: db.execute("INSERT OR REPLACE INTO policies VALUES (?, ?, ?)", (organization_id, json.dumps(payload, default=str), now()))


def load_policy(organization_id: str) -> dict[str, Any] | None:
    with _conn() as db: row = db.execute("SELECT payload FROM policies WHERE organization_id = ?", (organization_id,)).fetchone()
    return json.loads(row["payload"]) if row else None


def audit(event_type: str, payload: dict[str, Any], organization_id: str | None = None) -> None:
    with _conn() as db: db.execute("INSERT INTO audit_events(event_type, organization_id, payload, created_at) VALUES (?, ?, ?, ?)", (event_type, organization_id, json.dumps(payload, default=str), now()))


def audit_list() -> list[dict[str, Any]]:
    with _conn() as db: rows = db.execute("SELECT event_type, organization_id, payload, created_at FROM audit_events ORDER BY id").fetchall()
    return [{"event": r["event_type"], "organization_id": r["organization_id"], **json.loads(r["payload"]), "at": r["created_at"]} for r in rows]


def remember_webhook(event_id: str, event_type: str, payload: dict[str, Any]) -> bool:
    try:
        with _conn() as db: db.execute("INSERT INTO webhook_events VALUES (?, ?, ?, ?)", (event_id, event_type, json.dumps(payload), now()))
        return True
    except sqlite3.IntegrityError:
        return False


def idempotent_response(key: str, organization_id: str) -> dict[str, Any] | None:
    with _conn() as db: row = db.execute("SELECT response FROM idempotency_keys WHERE key = ? AND organization_id = ?", (key, organization_id)).fetchone()
    return json.loads(row["response"]) if row else None


def save_idempotent_response(key: str, organization_id: str, response: dict[str, Any]) -> None:
    with _conn() as db: db.execute("INSERT OR REPLACE INTO idempotency_keys VALUES (?, ?, ?, ?)", (key, organization_id, json.dumps(response), now()))
