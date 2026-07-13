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
    status TEXT NOT NULL DEFAULT 'active',   -- 'active' or 'inactive' (out of service)
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
    updated_at TEXT NOT NULL,
    service_call_id INTEGER REFERENCES service_calls(id),   -- set when this inspection was scheduled/started from a service call
    manager_name TEXT,           -- on-site manager sign-off, captured from the app
    manager_sign_date TEXT,
    manager_signature BLOB,      -- PNG bytes from the signature pad
    tech_signoff_name TEXT,      -- on-site technician sign-off (separate from inspector_id/who logged it)
    tech_sign_date TEXT,
    tech_signature BLOB
);

CREATE TABLE IF NOT EXISTS service_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    customer_name TEXT,           -- free-text fallback if site isn't in the system yet
    location_address TEXT,        -- free-text fallback address
    contact_name TEXT,
    contact_phone TEXT,
    call_type TEXT NOT NULL DEFAULT 'Service Call',   -- Emergency Call / Service Call / Scheduled Inspection / Follow-Up
    work_order_number TEXT,
    description TEXT,
    scheduled_date TEXT NOT NULL,
    scheduled_time TEXT,
    assigned_to INTEGER REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'Scheduled',   -- Scheduled / In Progress / Completed / Cancelled
    notes TEXT,
    check_in_time TEXT,     -- on-site arrival time (HH:MM), filled in by the tech from the app
    check_out_time TEXT,    -- on-site departure time (HH:MM)
    work_performed TEXT,    -- description of work completed, filled in by the tech from the app
    num_technicians TEXT,   -- number of technicians on site
    technician_names TEXT,  -- name(s) of technician(s) on site
    manager_name TEXT,      -- on-site manager sign-off, captured from the app
    manager_sign_date TEXT,
    manager_signature BLOB, -- PNG bytes from the signature pad
    tech_signoff_name TEXT, -- on-site technician sign-off
    tech_sign_date TEXT,
    tech_signature BLOB,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_call_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_call_id INTEGER NOT NULL REFERENCES service_calls(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'photo',   -- photo / material_list / deficiency_report / other
    filename TEXT,
    content_type TEXT,
    file_data BLOB NOT NULL,
    caption TEXT,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    service_call_id INTEGER REFERENCES service_calls(id) ON DELETE SET NULL,
    inspection_id INTEGER REFERENCES inspections(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',   -- Open / Completed
    reported_date TEXT NOT NULL,
    completed_date TEXT,
    completed_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inspection_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    filename TEXT,
    content_type TEXT,
    file_data BLOB NOT NULL,
    caption TEXT,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    filename TEXT,
    content_type TEXT,
    file_data BLOB NOT NULL,
    caption TEXT,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sites_client ON sites(client_id);
CREATE INDEX IF NOT EXISTS idx_assets_site ON assets(site_id);
CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(next_due_date);
CREATE INDEX IF NOT EXISTS idx_inspections_site ON inspections(site_id);
CREATE INDEX IF NOT EXISTS idx_inspections_asset ON inspections(asset_id);
CREATE INDEX IF NOT EXISTS idx_service_calls_date ON service_calls(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_service_calls_status ON service_calls(status);
CREATE INDEX IF NOT EXISTS idx_sc_attachments_call ON service_call_attachments(service_call_id);
CREATE INDEX IF NOT EXISTS idx_repairs_site ON repairs(site_id);
CREATE INDEX IF NOT EXISTS idx_repairs_status ON repairs(status);
CREATE INDEX IF NOT EXISTS idx_repairs_call ON repairs(service_call_id);
CREATE INDEX IF NOT EXISTS idx_insp_attachments_insp ON inspection_attachments(inspection_id);
CREATE INDEX IF NOT EXISTS idx_asset_attachments_asset ON asset_attachments(asset_id);
"""

ATTACHMENT_KINDS = {
    "photo": "Photo",
    "material_list": "Material List",
    "deficiency_report": "Deficiency Report",
    "other": "Other",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _column_exists(conn, table, column):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    return column in cols


def _migrate(conn):
    """Small additive schema migrations, safe to re-run on an existing DB with data."""
    if not _column_exists(conn, "inspections", "updated_by"):
        conn.execute("ALTER TABLE inspections ADD COLUMN updated_by INTEGER REFERENCES users(id)")
    if not _column_exists(conn, "assets", "status"):
        conn.execute("ALTER TABLE assets ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if not _column_exists(conn, "inspections", "service_call_id"):
        conn.execute("ALTER TABLE inspections ADD COLUMN service_call_id INTEGER REFERENCES service_calls(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inspections_call ON inspections(service_call_id)")
    if not _column_exists(conn, "service_calls", "check_in_time"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN check_in_time TEXT")
    if not _column_exists(conn, "service_calls", "check_out_time"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN check_out_time TEXT")
    if not _column_exists(conn, "service_calls", "work_performed"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN work_performed TEXT")
    if not _column_exists(conn, "service_calls", "manager_name"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN manager_name TEXT")
        conn.execute("ALTER TABLE service_calls ADD COLUMN manager_sign_date TEXT")
        conn.execute("ALTER TABLE service_calls ADD COLUMN manager_signature BLOB")
    if not _column_exists(conn, "inspections", "manager_name"):
        conn.execute("ALTER TABLE inspections ADD COLUMN manager_name TEXT")
        conn.execute("ALTER TABLE inspections ADD COLUMN manager_sign_date TEXT")
        conn.execute("ALTER TABLE inspections ADD COLUMN manager_signature BLOB")
    if not _column_exists(conn, "service_calls", "num_technicians"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN num_technicians TEXT")
        conn.execute("ALTER TABLE service_calls ADD COLUMN technician_names TEXT")
    if not _column_exists(conn, "service_calls", "tech_signoff_name"):
        conn.execute("ALTER TABLE service_calls ADD COLUMN tech_signoff_name TEXT")
        conn.execute("ALTER TABLE service_calls ADD COLUMN tech_sign_date TEXT")
        conn.execute("ALTER TABLE service_calls ADD COLUMN tech_signature BLOB")
    if not _column_exists(conn, "inspections", "tech_signoff_name"):
        conn.execute("ALTER TABLE inspections ADD COLUMN tech_signoff_name TEXT")
        conn.execute("ALTER TABLE inspections ADD COLUMN tech_sign_date TEXT")
        conn.execute("ALTER TABLE inspections ADD COLUMN tech_signature BLOB")
    conn.commit()


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
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


def set_user_password(user_id, password_hash):
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()


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


def client_delete_impact(client_id):
    """Counts what would be cascade-deleted along with this client, so a
    confirmation dialog can warn the user before it happens."""
    conn = get_conn()
    sites = conn.execute("SELECT COUNT(*) c FROM sites WHERE client_id = ?", (client_id,)).fetchone()["c"]
    assets = conn.execute(
        "SELECT COUNT(*) c FROM assets WHERE site_id IN (SELECT id FROM sites WHERE client_id = ?)",
        (client_id,),
    ).fetchone()["c"]
    inspections = conn.execute(
        "SELECT COUNT(*) c FROM inspections WHERE site_id IN (SELECT id FROM sites WHERE client_id = ?)",
        (client_id,),
    ).fetchone()["c"]
    conn.close()
    return {"sites": sites, "assets": assets, "inspections": inspections}


def delete_client(client_id):
    conn = get_conn()
    conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


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


def site_delete_impact(site_id):
    conn = get_conn()
    assets = conn.execute("SELECT COUNT(*) c FROM assets WHERE site_id = ?", (site_id,)).fetchone()["c"]
    inspections = conn.execute("SELECT COUNT(*) c FROM inspections WHERE site_id = ?", (site_id,)).fetchone()["c"]
    conn.close()
    return {"assets": assets, "inspections": inspections}


def delete_site(site_id):
    conn = get_conn()
    conn.execute("DELETE FROM sites WHERE id = ?", (site_id,))
    conn.commit()
    conn.close()


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


def update_asset(asset_id, **fields):
    if not fields:
        return
    conn = get_conn()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE assets SET {cols} WHERE id = ?", (*fields.values(), asset_id))
    conn.commit()
    conn.close()


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


def asset_delete_impact(asset_id):
    conn = get_conn()
    inspections = conn.execute("SELECT COUNT(*) c FROM inspections WHERE asset_id = ?", (asset_id,)).fetchone()["c"]
    conn.close()
    return {"inspections": inspections}


def delete_asset(asset_id):
    conn = get_conn()
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()


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


def recompute_schedule(site_id, asset_id, inspection_type, frequency_months):
    """Recalculates the schedule row from whatever inspections of this type
    remain (used after a delete/edit so a due date never points at an
    inspection that no longer exists). Unlike upsert_schedule, this always
    overwrites — it's meant to reflect ground truth, not just move forward."""
    conn = get_conn()
    latest = conn.execute(
        """
        SELECT inspection_date FROM inspections
        WHERE site_id = ? AND asset_id IS ? AND inspection_type = ?
          AND (overall_result IS NULL OR overall_result != 'Incomplete')
        ORDER BY inspection_date DESC LIMIT 1
        """,
        (site_id, asset_id, inspection_type),
    ).fetchone()
    if latest:
        next_due = add_months(latest["inspection_date"], frequency_months)
        conn.execute(
            """
            INSERT INTO schedules (site_id, asset_id, inspection_type, frequency_months, last_completed_date, next_due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, asset_id, inspection_type) DO UPDATE SET
                frequency_months = excluded.frequency_months,
                last_completed_date = excluded.last_completed_date,
                next_due_date = excluded.next_due_date
            """,
            (site_id, asset_id, inspection_type, frequency_months, latest["inspection_date"], next_due),
        )
    else:
        conn.execute(
            "DELETE FROM schedules WHERE site_id = ? AND asset_id IS ? AND inspection_type = ?",
            (site_id, asset_id, inspection_type),
        )
    conn.commit()
    conn.close()


def delete_inspection(inspection_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT site_id, asset_id, inspection_type FROM inspections WHERE id = ?", (inspection_id,)
    ).fetchone()
    conn.execute("DELETE FROM inspections WHERE id = ?", (inspection_id,))
    conn.commit()
    conn.close()
    return row


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


def list_schedules(site_id=None, upcoming_days=None, overdue_only=False, active_only=False):
    conn = get_conn()
    query = """
        SELECT schedules.*, sites.name AS site_name, sites.city AS site_city,
               clients.name AS client_name, clients.id AS client_id,
               assets.label AS asset_label, assets.status AS asset_status
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
    if active_only:
        conditions.append("(schedules.asset_id IS NULL OR assets.status = 'active')")
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
    overdue = conn.execute(
        """
        SELECT COUNT(*) c FROM schedules LEFT JOIN assets ON assets.id = schedules.asset_id
        WHERE schedules.next_due_date < ? AND (schedules.asset_id IS NULL OR assets.status = 'active')
        """,
        (today,),
    ).fetchone()["c"]
    due_soon = conn.execute(
        """
        SELECT COUNT(*) c FROM schedules LEFT JOIN assets ON assets.id = schedules.asset_id
        WHERE schedules.next_due_date >= ? AND schedules.next_due_date <= ?
          AND (schedules.asset_id IS NULL OR assets.status = 'active')
        """,
        (today, soon),
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
                       non_critical_deficiencies, satisfactory, form_data, created_by,
                       service_call_id=None):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO inspections
        (site_id, asset_id, inspection_type, inspector_id, inspection_date, overall_result,
         system_impaired, critical_deficiencies, non_critical_deficiencies, satisfactory,
         form_data, created_by, created_at, updated_at, service_call_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (site_id, asset_id, inspection_type, inspector_id, inspection_date, overall_result,
         system_impaired, critical_deficiencies, non_critical_deficiencies, satisfactory,
         json.dumps(form_data), created_by, now_iso(), now_iso(), service_call_id),
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def update_inspection(inspection_id, inspection_date, overall_result, system_impaired,
                       critical_deficiencies, non_critical_deficiencies, satisfactory,
                       form_data, updated_by):
    conn = get_conn()
    conn.execute(
        """
        UPDATE inspections SET
            inspection_date = ?, overall_result = ?, system_impaired = ?,
            critical_deficiencies = ?, non_critical_deficiencies = ?, satisfactory = ?,
            form_data = ?, updated_by = ?, updated_at = ?
        WHERE id = ?
        """,
        (inspection_date, overall_result, system_impaired, critical_deficiencies,
         non_critical_deficiencies, satisfactory, json.dumps(form_data), updated_by,
         now_iso(), inspection_id),
    )
    conn.commit()
    conn.close()


def set_inspection_signoff(inspection_id, manager_name, manager_sign_date, manager_signature=None):
    fields = ["manager_name = ?", "manager_sign_date = ?"]
    params = [manager_name, manager_sign_date]
    if manager_signature is not None:
        fields.append("manager_signature = ?")
        params.append(manager_signature)
    params.append(inspection_id)
    conn = get_conn()
    conn.execute(f"UPDATE inspections SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def get_inspection_signature(inspection_id):
    conn = get_conn()
    row = conn.execute("SELECT manager_signature FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    conn.close()
    return row["manager_signature"] if row else None


def set_inspection_tech_signoff(inspection_id, tech_signoff_name, tech_sign_date, tech_signature=None):
    fields = ["tech_signoff_name = ?", "tech_sign_date = ?"]
    params = [tech_signoff_name, tech_sign_date]
    if tech_signature is not None:
        fields.append("tech_signature = ?")
        params.append(tech_signature)
    params.append(inspection_id)
    conn = get_conn()
    conn.execute(f"UPDATE inspections SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def get_inspection_tech_signature(inspection_id):
    conn = get_conn()
    row = conn.execute("SELECT tech_signature FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    conn.close()
    return row["tech_signature"] if row else None


def get_inspection(inspection_id):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT inspections.*, sites.name AS site_name, sites.id AS site_id,
               clients.name AS client_name, clients.id AS client_id,
               assets.label AS asset_label,
               users.name AS inspector_name,
               editor.name AS updated_by_name
        FROM inspections
        JOIN sites ON sites.id = inspections.site_id
        JOIN clients ON clients.id = sites.client_id
        LEFT JOIN assets ON assets.id = inspections.asset_id
        LEFT JOIN users ON users.id = inspections.inspector_id
        LEFT JOIN users AS editor ON editor.id = inspections.updated_by
        WHERE inspections.id = ?
        """,
        (inspection_id,),
    ).fetchone()
    conn.close()
    return row


def list_inspections(site_id=None, asset_id=None, inspection_type=None, service_call_id=None, limit=100):
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
    if service_call_id:
        conditions.append("inspections.service_call_id = ?")
        params.append(service_call_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY inspections.inspection_date DESC, inspections.id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def recent_inspections(limit=20):
    return list_inspections(limit=limit)


def previous_inspection(site_id, asset_id, inspection_type, exclude_id):
    """Finds the most recent earlier inspection of the same type against the
    same site/asset, for building a previous-vs-current comparison view."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT * FROM inspections
        WHERE site_id = ? AND asset_id IS ? AND inspection_type = ? AND id != ?
        ORDER BY inspection_date DESC, id DESC LIMIT 1
        """,
        (site_id, asset_id, inspection_type, exclude_id),
    ).fetchone()
    conn.close()
    return row


# ---------- Service Calls (emergency / ad-hoc work orders) ----------

SERVICE_CALL_JOIN = """
    SELECT service_calls.*,
           sites.name AS site_name, sites.street AS site_street, sites.city AS site_city,
           sites.state AS site_state, sites.zip AS site_zip,
           clients.name AS client_name, clients.id AS client_id,
           tech.name AS assigned_to_name,
           creator.name AS created_by_name
    FROM service_calls
    LEFT JOIN sites ON sites.id = service_calls.site_id
    LEFT JOIN clients ON clients.id = sites.client_id
    LEFT JOIN users AS tech ON tech.id = service_calls.assigned_to
    LEFT JOIN users AS creator ON creator.id = service_calls.created_by
"""


WO_PREFIX = "SC-"
WO_START = 1001


def next_service_call_wo_number():
    """Suggests the next sequential SCFP-generated work order number
    (e.g. SC-1001, SC-1002...). This is only a starting suggestion — the
    office can always type over it with a customer-supplied PO/WO # instead.
    Only considers our own SC-### numbers so it never collides with or gets
    thrown off by customer PO numbers typed into the same field."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT work_order_number FROM service_calls WHERE work_order_number LIKE ?",
        (WO_PREFIX + "%",),
    ).fetchall()
    conn.close()
    highest = WO_START - 1
    for r in rows:
        val = (r["work_order_number"] or "")[len(WO_PREFIX):]
        if val.isdigit():
            highest = max(highest, int(val))
    return f"{WO_PREFIX}{highest + 1}"


def create_service_call(scheduled_date, description, site_id=None, customer_name="",
                         location_address="", contact_name="", contact_phone="",
                         call_type="Service Call", work_order_number="", scheduled_time="",
                         assigned_to=None, status="Scheduled", notes="", created_by=None):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO service_calls
        (site_id, customer_name, location_address, contact_name, contact_phone, call_type,
         work_order_number, description, scheduled_date, scheduled_time, assigned_to, status,
         notes, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (site_id, customer_name, location_address, contact_name, contact_phone, call_type,
         work_order_number, description, scheduled_date, scheduled_time, assigned_to, status,
         notes, created_by, now_iso(), now_iso()),
    )
    conn.commit()
    scid = cur.lastrowid
    conn.close()
    return scid


def update_service_call(call_id, **fields):
    if not fields:
        return
    fields["updated_at"] = now_iso()
    conn = get_conn()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE service_calls SET {cols} WHERE id = ?", (*fields.values(), call_id))
    conn.commit()
    conn.close()


def set_service_call_status(call_id, status):
    update_service_call(call_id, status=status)


def set_service_call_signoff(call_id, manager_name, manager_sign_date, manager_signature=None):
    """manager_signature is PNG bytes from the signature pad, or None to leave
    whatever signature is already on file untouched (so re-saving just the
    name/date doesn't wipe out a signature captured moments earlier)."""
    fields = {"manager_name": manager_name, "manager_sign_date": manager_sign_date}
    if manager_signature is not None:
        fields["manager_signature"] = manager_signature
    update_service_call(call_id, **fields)


def get_service_call_signature(call_id):
    conn = get_conn()
    row = conn.execute("SELECT manager_signature FROM service_calls WHERE id = ?", (call_id,)).fetchone()
    conn.close()
    return row["manager_signature"] if row else None


def set_service_call_tech_signoff(call_id, tech_signoff_name, tech_sign_date, tech_signature=None):
    fields = {"tech_signoff_name": tech_signoff_name, "tech_sign_date": tech_sign_date}
    if tech_signature is not None:
        fields["tech_signature"] = tech_signature
    update_service_call(call_id, **fields)


def get_service_call_tech_signature(call_id):
    conn = get_conn()
    row = conn.execute("SELECT tech_signature FROM service_calls WHERE id = ?", (call_id,)).fetchone()
    conn.close()
    return row["tech_signature"] if row else None


def get_service_call(call_id):
    conn = get_conn()
    row = conn.execute(SERVICE_CALL_JOIN + " WHERE service_calls.id = ?", (call_id,)).fetchone()
    conn.close()
    return row


def list_service_calls(status=None, upcoming_only=False, site_id=None, limit=200):
    conn = get_conn()
    query = SERVICE_CALL_JOIN
    conditions, params = [], []
    if status:
        conditions.append("service_calls.status = ?")
        params.append(status)
    if upcoming_only:
        conditions.append("service_calls.status NOT IN ('Completed', 'Cancelled')")
    if site_id:
        conditions.append("service_calls.site_id = ?")
        params.append(site_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY service_calls.scheduled_date ASC, service_calls.scheduled_time ASC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


FOLLOWUP_STATUSES = ("Completed - Repairs Required", "Completed - Return Trip Required")


def list_followup_calls(limit=50):
    """Calls that were closed out but still need something done — material/parts
    ordered and a repair completed, or a return trip made. Stays on this list
    until the office/tech updates the status again (e.g. to Completed)."""
    conn = get_conn()
    placeholders = ", ".join("?" for _ in FOLLOWUP_STATUSES)
    rows = conn.execute(
        SERVICE_CALL_JOIN + f"""
        WHERE service_calls.status IN ({placeholders})
        ORDER BY service_calls.updated_at DESC LIMIT ?
        """,
        (*FOLLOWUP_STATUSES, limit),
    ).fetchall()
    conn.close()
    return rows


def upcoming_service_calls(days=14, limit=50):
    """Open (not completed/cancelled) calls due within the window, plus anything
    already overdue — sorted soonest first, for the dashboard panel."""
    conn = get_conn()
    cutoff = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    rows = conn.execute(
        SERVICE_CALL_JOIN + """
        WHERE service_calls.status NOT IN ('Completed', 'Cancelled')
          AND service_calls.scheduled_date <= ?
        ORDER BY service_calls.scheduled_date ASC, service_calls.scheduled_time ASC
        LIMIT ?
        """,
        (cutoff, limit),
    ).fetchall()
    conn.close()
    return rows


def count_open_service_calls():
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) c FROM service_calls WHERE status NOT IN ('Completed', 'Cancelled')"
    ).fetchone()["c"]
    conn.close()
    return n


def delete_service_call(call_id):
    conn = get_conn()
    # Inspections logged against this call (via the schedule + fill-in-now
    # flow) reference it with no ON DELETE rule, so SQLite blocks the delete
    # with a foreign key error unless we unlink them first. The inspection
    # records themselves are real compliance history and must NOT be
    # deleted — only the link back to this call is cleared.
    conn.execute("UPDATE inspections SET service_call_id = NULL WHERE service_call_id = ?", (call_id,))
    conn.execute("DELETE FROM service_calls WHERE id = ?", (call_id,))
    conn.commit()
    conn.close()


# ---------- Service Call Attachments (photos, material lists, deficiency reports) ----------

def create_attachment(service_call_id, kind, filename, content_type, file_data, caption="", uploaded_by=None):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO service_call_attachments
        (service_call_id, kind, filename, content_type, file_data, caption, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (service_call_id, kind, filename, content_type, file_data, caption, uploaded_by, now_iso()),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_attachments(service_call_id):
    """Lists attachment metadata (no file bytes) — kept light since each
    attachment's image/file is fetched separately by its own <img>/link."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT service_call_attachments.id, service_call_id, kind, filename, content_type,
               caption, uploaded_at, length(file_data) AS size_bytes,
               users.name AS uploaded_by_name
        FROM service_call_attachments
        LEFT JOIN users ON users.id = service_call_attachments.uploaded_by
        WHERE service_call_id = ?
        ORDER BY uploaded_at DESC
        """,
        (service_call_id,),
    ).fetchall()
    conn.close()
    return rows


def get_attachment_file(attachment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM service_call_attachments WHERE id = ?", (attachment_id,)).fetchone()
    conn.close()
    return row


def delete_attachment(attachment_id):
    conn = get_conn()
    conn.execute("DELETE FROM service_call_attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    conn.close()


# ---------- Repairs (pending/completed repair log) ----------

REPAIR_JOIN = """
    SELECT repairs.*, sites.name AS site_name, clients.name AS client_name, clients.id AS client_id,
           assets.label AS asset_label, creator.name AS created_by_name,
           completer.name AS completed_by_name
    FROM repairs
    JOIN sites ON sites.id = repairs.site_id
    JOIN clients ON clients.id = sites.client_id
    LEFT JOIN assets ON assets.id = repairs.asset_id
    LEFT JOIN users AS creator ON creator.id = repairs.created_by
    LEFT JOIN users AS completer ON completer.id = repairs.completed_by
"""


def create_repair(site_id, description, asset_id=None, service_call_id=None, inspection_id=None,
                   reported_date=None, notes="", created_by=None):
    conn = get_conn()
    reported_date = reported_date or today_iso()
    cur = conn.execute(
        """
        INSERT INTO repairs
        (site_id, asset_id, service_call_id, inspection_id, description, status,
         reported_date, notes, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?)
        """,
        (site_id, asset_id, service_call_id, inspection_id, description, reported_date,
         notes, created_by, now_iso(), now_iso()),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def complete_repair(repair_id, completed_by, notes=None, completed_date=None):
    conn = get_conn()
    completed_date = completed_date or today_iso()
    if notes is not None:
        conn.execute(
            "UPDATE repairs SET status='Completed', completed_date=?, completed_by=?, notes=?, updated_at=? WHERE id=?",
            (completed_date, completed_by, notes, now_iso(), repair_id),
        )
    else:
        conn.execute(
            "UPDATE repairs SET status='Completed', completed_date=?, completed_by=?, updated_at=? WHERE id=?",
            (completed_date, completed_by, now_iso(), repair_id),
        )
    conn.commit()
    conn.close()


def reopen_repair(repair_id):
    conn = get_conn()
    conn.execute(
        "UPDATE repairs SET status='Open', completed_date=NULL, completed_by=NULL, updated_at=? WHERE id=?",
        (now_iso(), repair_id),
    )
    conn.commit()
    conn.close()


def get_repair(repair_id):
    conn = get_conn()
    row = conn.execute(REPAIR_JOIN + " WHERE repairs.id = ?", (repair_id,)).fetchone()
    conn.close()
    return row


def list_repairs(site_id=None, status=None, service_call_id=None, limit=200):
    conn = get_conn()
    query = REPAIR_JOIN
    conditions, params = [], []
    if site_id:
        conditions.append("repairs.site_id = ?")
        params.append(site_id)
    if status:
        conditions.append("repairs.status = ?")
        params.append(status)
    if service_call_id:
        conditions.append("repairs.service_call_id = ?")
        params.append(service_call_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY (repairs.status = 'Open') DESC, repairs.reported_date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def count_open_repairs():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM repairs WHERE status = 'Open'").fetchone()["c"]
    conn.close()
    return n


def delete_repair(repair_id):
    conn = get_conn()
    conn.execute("DELETE FROM repairs WHERE id = ?", (repair_id,))
    conn.commit()
    conn.close()


# ---------- Site activity log (combined history: inspections, calls, repairs) ----------

def site_activity(site_id, limit=200):
    """Unified, chronological record of everything that has happened at a
    site — every inspection conducted, every service/emergency call, and
    every repair (pending or completed) — newest first."""
    conn = get_conn()
    events = []

    for r in conn.execute(
        """
        SELECT inspections.id AS id, inspections.inspection_date AS date,
               inspections.inspection_type AS inspection_type, inspections.overall_result AS overall_result,
               assets.label AS asset_label, users.name AS who
        FROM inspections
        LEFT JOIN assets ON assets.id = inspections.asset_id
        LEFT JOIN users ON users.id = inspections.inspector_id
        WHERE inspections.site_id = ?
        """,
        (site_id,),
    ).fetchall():
        events.append({
            "kind": "inspection", "id": r["id"], "date": r["date"],
            "inspection_type": r["inspection_type"], "overall_result": r["overall_result"],
            "asset_label": r["asset_label"], "who": r["who"],
        })

    for r in conn.execute(
        """
        SELECT service_calls.id AS id, service_calls.scheduled_date AS date,
               service_calls.call_type AS call_type, service_calls.status AS status,
               service_calls.description AS description, tech.name AS who
        FROM service_calls
        LEFT JOIN users AS tech ON tech.id = service_calls.assigned_to
        WHERE service_calls.site_id = ?
        """,
        (site_id,),
    ).fetchall():
        events.append({
            "kind": "service_call", "id": r["id"], "date": r["date"],
            "call_type": r["call_type"], "status": r["status"],
            "description": r["description"], "who": r["who"],
        })

    for r in conn.execute(
        """
        SELECT repairs.id AS id, repairs.status AS status, repairs.description AS description,
               repairs.reported_date AS reported_date, repairs.completed_date AS completed_date,
               assets.label AS asset_label
        FROM repairs
        LEFT JOIN assets ON assets.id = repairs.asset_id
        WHERE repairs.site_id = ?
        """,
        (site_id,),
    ).fetchall():
        events.append({
            "kind": "repair", "id": r["id"], "date": r["completed_date"] or r["reported_date"],
            "status": r["status"], "description": r["description"], "asset_label": r["asset_label"],
            "reported_date": r["reported_date"], "completed_date": r["completed_date"],
        })

    conn.close()
    events.sort(key=lambda e: (e["date"] or "", e["id"]), reverse=True)
    return events[:limit]


# ---------- Inspection attachments (deficiency photos, etc.) ----------

def create_inspection_attachment(inspection_id, filename, content_type, file_data, caption="", uploaded_by=None):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO inspection_attachments
        (inspection_id, filename, content_type, file_data, caption, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (inspection_id, filename, content_type, file_data, caption, uploaded_by, now_iso()),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_inspection_attachments(inspection_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT inspection_attachments.id, inspection_id, filename, content_type,
               caption, uploaded_at, length(file_data) AS size_bytes,
               users.name AS uploaded_by_name
        FROM inspection_attachments
        LEFT JOIN users ON users.id = inspection_attachments.uploaded_by
        WHERE inspection_id = ?
        ORDER BY uploaded_at DESC
        """,
        (inspection_id,),
    ).fetchall()
    conn.close()
    return rows


def get_inspection_attachment_file(attachment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM inspection_attachments WHERE id = ?", (attachment_id,)).fetchone()
    conn.close()
    return row


def delete_inspection_attachment(attachment_id):
    conn = get_conn()
    conn.execute("DELETE FROM inspection_attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    conn.close()


# ---------- Asset attachments (photos of equipment/devices) ----------

def create_asset_attachment(asset_id, filename, content_type, file_data, caption="", uploaded_by=None):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO asset_attachments
        (asset_id, filename, content_type, file_data, caption, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (asset_id, filename, content_type, file_data, caption, uploaded_by, now_iso()),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_asset_attachments(asset_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT asset_attachments.id, asset_id, filename, content_type,
               caption, uploaded_at, length(file_data) AS size_bytes,
               users.name AS uploaded_by_name
        FROM asset_attachments
        LEFT JOIN users ON users.id = asset_attachments.uploaded_by
        WHERE asset_id = ?
        ORDER BY uploaded_at DESC
        """,
        (asset_id,),
    ).fetchall()
    conn.close()
    return rows


def get_asset_attachment_file(attachment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM asset_attachments WHERE id = ?", (attachment_id,)).fetchone()
    conn.close()
    return row


def delete_asset_attachment(attachment_id):
    conn = get_conn()
    conn.execute("DELETE FROM asset_attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    conn.close()
