"""
SQLite data layer for the SCFP inspection tracker.

SQLite is used so the whole app can run anywhere with just Python +
requirements.txt (no external database service to stand up). It comfortably
handles a small team of office/field staff. If/when the company outgrows a
single-file database, the SQL here is close enough to Postgres that a
migration is a small effort later.
"""
import sqlite3
import os
import json
import datetime

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.environ.get("SCFP_DB_PATH", os.path.join(_DATA_DIR, "scfp.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'inspector',   -- 'admin' or 'inspector'
    cert_number TEXT,
    phone TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    billing_address TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    jurisdiction TEXT,
    division TEXT,
    contact_person TEXT,
    contact_phone TEXT,
    store_number TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,          -- backflow, fire_pump, hydrant, other
    label TEXT NOT NULL,               -- e.g. "Backflow - Domestic DCVA" or "Hydrant #3"
    location TEXT,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    size TEXT,
    install_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    inspection_type TEXT NOT NULL,
    frequency_months INTEGER NOT NULL,
    last_completed_date TEXT,
    next_due_date TEXT,
    UNIQUE(site_id, asset_id, inspection_type)
);

CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    inspection_type TEXT NOT NULL,
    inspector_id INTEGER REFERENCES users(id),
    inspection_date TEXT NOT NULL,
    overall_result TEXT,
    system_impaired INTEGER,
    critical_deficiencies INTEGER,
    non_critical_deficiencies INTEGER,
    satisfactory INTEGER,
    form_data TEXT NOT NULL,      -- JSON blob of all type-specific fields
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sites_client ON sites(client_id);
CREATE INDEX IF NOT EXISTS idx_assets_site ON assets(site_id);
CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(next_due_date);
CREATE INDEX IF NOT EXISTS idx_inspections_site ON inspections(site_id);
CREATE INDEX IF NOT EXISTS idx_inspections_asset ON inspections(asset_id);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def now_iso():
    return datetime.datetime.utcnow().isoformat(timespec="seconds")


def today_iso():
    return datetime.date.today().isoformat()


def add_months(date_str, months):
    d = datetime.date.fromisoformat(date_str)
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return datetime.date(year, month, day).isoformat()


# ---------- Users ----------

def create_user(name, email, password_hash, role="inspector", cert_number=None, phone=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, role, cert_number, phone, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, email.lower().strip(), password_hash, role, cert_number, phone, now_iso()),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ? AND active = 1", (email.lower().strip(),)).fetchone()
    conn.close()
    return row


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
    conn.close()
    return rows


def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    conn.close()
    return n


def set_user_active(user_id, active):
    conn = get_conn()
    conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()


# ---------- Clients ----------

def create_client(name, contact_name="", phone="", email="", billing_address="", notes=""):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO clients (name, contact_name, phone, email, billing_address, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, contact_name, phone, email, billing_address, notes, now_iso()),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def update_client(client_id, **fields):
    if not fields:
        return
    conn = get_conn()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE clients SET {cols} WHERE id = ?", (*fields.values(), client_id))
    conn.commit()
    conn.close()


def list_clients(search=None):
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT * FROM clients WHERE name LIKE ? ORDER BY name", (f"%{search}%",)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return row


# ---------- Sites ----------

def create_site(client_id, name, **fields):
    conn = get_conn()
    fields.setdefault("street", "")
    fields.setdefault("city", "")
    fields.setdefault("state", "")
    fields.setdefault("zip", "")
    fields.setdefault("jurisdiction", "")
    fields.setdefault("division", "")
    fields.setdefault("contact_person", "")
    fields.setdefault("contact_phone", "")
    fields.setdefault("store_number", "")
    fields.setdefault("notes", "")
    cols = ["client_id", "name"] + list(fields.keys()) + ["created_at"]
    vals = [client_id, name] + list(fields.values()) + [now_iso()]
    placeholders = ", ".join("?" for _ in vals)
    cur = conn.execute(f"INSERT INTO sites ({', '.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def update_site(site_id, **fields):
    if not fields:
        return
    conn = get_conn()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE sites SET {cols} WHERE id = ?", (*fields.values(), site_id))
    conn.commit()
    conn.close()


def list_sites(client_id=None, search=None):
    conn = get_conn()
    query = "SELECT sites.*, clients.name AS client_name FROM sites JOIN clients ON clients.id = sites.client_id"
    conditions, params = [], []
    if client_id:
        conditions.append("sites.client_id = ?")
        params.append(client_id)
    if search:
        conditions.append("(sites.name LIKE ? OR sites.city LIKE ? OR clients.name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY sites.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_site(site_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT sites.*, clients.name AS client_name FROM sites "
        "JOIN clients ON clients.id = sites.client_id WHERE sites.id = ?",
        (site_id,),
    ).fetchone()
    conn.close()
    return row


# ---------- Assets ----------

def create_asset(site_id, asset_type, label, **fields):
    conn = get_conn()
    for k in ["location", "manufacturer", "model", "serial_number", "size", "install_date", "notes"]:
        fields.setdefault(k, "")
    cols = ["site_id", "asset_type", "label"] + list(fields.keys()) + ["created_at"]
    vals = [site_id, asset_type, label] + list(fields.values()) + [now_iso()]
    placeholders = ", ".join("?" for _ in vals)
    cur = conn.execute(f"INSERT INTO assets ({', '.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_assets(site_id=None, asset_type=None):
    conn = get_conn()
    query = "SELECT * FROM assets"
    conditions, params = [], []
    if site_id:
        conditions.append("site_id = ?")
        params.append(site_id)
    if asset_type:
        conditions.append("asset_type = ?")
        params.append(asset_type)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY label"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_asset(asset_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return row


# ---------- Schedules / Due dates ----------

def upsert_schedule(site_id, asset_id, inspection_type, frequency_months, completed_date):
    next_due = add_months(completed_date, frequency_months)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO schedules (site_id, asset_id, inspection_type, frequency_months, last_completed_date, next_due_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(site_id, asset_id, inspection_type) DO UPDATE SET
            frequency_months = excluded.frequency_months,
            last_completed_date = excluded.last_completed_date,
            next_due_date = excluded.next_due_date
        WHERE excluded.last_completed_date >= schedules.last_completed_date
           OR schedules.last_completed_date IS NULL
        """,
        (site_id, asset_id, inspection_type, frequency_months, completed_date, next_due),
    )
    conn.commit()
    conn.close()
    return next_due


def set_manual_due_date(site_id, asset_id, inspection_type, frequency_months, next_due_date):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO schedules (site_id, asset_id, inspection_type, frequency_months, next_due_date)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(site_id, asset_id, inspection_type) DO UPDATE SET
            frequency_months = excluded.frequency_months,
            next_due_date = excluded.next_due_date
        """,
        (site_id, asset_id, inspection_type, frequency_months, next_due_date),
    )
    conn.commit()
    conn.close()


def list_schedules(site_id=None, upcoming_days=None, overdue_only=False):
    conn = get_conn()
    query = """
        SELECT schedules.*, sites.name AS site_name, sites.city AS site_city,
               clients.name AS client_name, clients.id AS client_id,
               assets.label AS asset_label
        FROM schedules
        JOIN sites ON sites.id = schedules.site_id
        JOIN clients ON clients.id = sites.client_id
        LEFT JOIN assets ON assets.id = schedules.asset_id
    """
    conditions, params = [], []
    if site_id:
        conditions.append("schedules.site_id = ?")
        params.append(site_id)
    if overdue_only:
        conditions.append("schedules.next_due_date < ?")
        params.append(today_iso())
    elif upcoming_days is not None:
        conditions.append("schedules.next_due_date <= ?")
        cutoff = (datetime.date.today() + datetime.timedelta(days=upcoming_days)).isoformat()
        params.append(cutoff)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY schedules.next_due_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def dashboard_counts():
    conn = get_conn()
    today = today_iso()
    soon = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    overdue = conn.execute("SELECT COUNT(*) c FROM schedules WHERE next_due_date < ?", (today,)).fetchone()["c"]
    due_soon = conn.execute(
        "SELECT COUNT(*) c FROM schedules WHERE next_due_date >= ? AND next_due_date <= ?", (today, soon)
    ).fetchone()["c"]
    total_clients = conn.execute("SELECT COUNT(*) c FROM clients").fetchone()["c"]
    total_sites = conn.execute("SELECT COUNT(*) c FROM sites").fetchone()["c"]
    total_inspections = conn.execute("SELECT COUNT(*) c FROM inspections").fetchone()["c"]
    conn.close()
    return {
        "overdue": overdue,
        "due_soon": due_soon,
        "total_clients": total_clients,
        "total_sites": total_sites,
        "total_inspections": total_inspections,
    }


# ---------- Inspections ----------

def create_inspection(site_id, asset_id, inspection_type, inspector_id, inspection_date,
                       overall_result, system_impaired, critical_deficiencies,
                       non_critical_deficiencies, satisfactory, form_data, created_by):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO inspections
        (site_id, asset_id, inspection_type, inspector_id, inspection_date, overall_result,
         system_impaired, critical_deficiencies, non_critical_deficiencies, satisfactory,
         form_data, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (site_id, asset_id, inspection_type, inspector_id, inspection_date, overall_result,
         system_impaired, critical_deficiencies, non_critical_deficiencies, satisfactory,
         json.dumps(form_data), created_by, now_iso(), now_iso()),
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def get_inspection(inspection_id):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT inspections.*, sites.name AS site_name, sites.id AS site_id,
               clients.name AS client_name, clients.id AS client_id,
               assets.label AS asset_label,
               users.name AS inspector_name
        FROM inspections
        JOIN sites ON sites.id = inspections.site_id
        JOIN clients ON clients.id = sites.client_id
        LEFT JOIN assets ON assets.id = inspections.asset_id
        LEFT JOIN users ON users.id = inspections.inspector_id
        WHERE inspections.id = ?
        """,
        (inspection_id,),
    ).fetchone()
    conn.close()
    return row


def list_inspections(site_id=None, asset_id=None, inspection_type=None, limit=100):
    conn = get_conn()
    query = """
        SELECT inspections.*, sites.name AS site_name, clients.name AS client_name,
               assets.label AS asset_label, users.name AS inspector_name
        FROM inspections
        JOIN sites ON sites.id = inspections.site_id
        JOIN clients ON clients.id = sites.client_id
        LEFT JOIN assets ON assets.id = inspections.asset_id
        LEFT JOIN users ON users.id = inspections.inspector_id
    """
    conditions, params = [], []
    if site_id:
        conditions.append("inspections.site_id = ?")
        params.append(site_id)
    if asset_id:
        conditions.append("inspections.asset_id = ?")
        params.append(asset_id)
    if inspection_type:
        conditions.append("inspections.inspection_type = ?")
        params.append(inspection_type)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY inspections.inspection_date DESC, inspections.id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def recent_inspections(limit=20):
    return list_inspections(limit=limit)
