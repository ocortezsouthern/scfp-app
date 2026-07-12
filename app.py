"""
SCFP Inspection Tracker - Tornado web app.

Run locally:
    pip install -r requirements.txt
    python app.py --port=8888

First run walks you through creating the first admin account at /setup.
"""
import os
import re
import json
import datetime
import argparse

import tornado.ioloop
import tornado.web
import jinja2

import db
import auth
import pdf_gen
from forms_config import INSPECTION_TYPES, get_type_config, CLOSING_SECTION, all_types, asset_prefill_data

BASE_DIR = os.path.dirname(__file__)
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(BASE_DIR, "templates")),
    autoescape=True,
)


def months_label(m):
    if m % 12 == 0:
        y = m // 12
        return f"Every {y} year" + ("s" if y != 1 else "")
    return f"Every {m} months"


JINJA_ENV.filters["months_label"] = months_label


ASSET_TYPE_LABELS = {
    "backflow": "Backflow Assembly",
    "fire_pump": "Fire Pump",
    "hydrant": "Hydrant",
    "wet_pipe": "Wet Pipe Sprinkler System",
    "dry_pipe": "Dry Pipe Sprinkler System",
    "fire_hose": "Fire Hose",
    "fire_alarm_panel": "Fire Alarm Panel",
    "other": "Other Equipment",
}

CALL_TYPES = ["Emergency Call", "Service Call", "Scheduled Inspection", "Follow-Up"]
CALL_STATUSES = [
    "Scheduled",
    "In Progress",
    "Completed",
    "Completed - Repairs Required",
    "Completed - Return Trip Required",
    "Cancelled",
]
# Statuses that still need follow-up even though work has started/finished —
# used to color their badges amber instead of "all done" green.
CALL_STATUSES_NEEDS_FOLLOWUP = ["In Progress", "Completed - Repairs Required", "Completed - Return Trip Required"]


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        uid = self.get_secure_cookie("user_id")
        if not uid:
            return None
        return db.get_user(int(uid.decode("utf-8")))

    def render_tpl(self, name, **kwargs):
        tpl = JINJA_ENV.get_template(name)
        ctx = dict(
            current_user=self.current_user,
            all_types=all_types(),
            xsrf_token=self.xsrf_token.decode("utf-8"),
            today=db.today_iso(),
        )
        ctx.update(kwargs)
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.write(tpl.render(**ctx))

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.write(f"<h1>{status_code}</h1><p>Something went wrong.</p><a href='/'>Home</a>")


def require_login(method):
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            self.redirect("/login?next=" + self.request.path)
            return
        return method(self, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------- auth ----

class SetupHandler(BaseHandler):
    def get(self):
        if db.count_users() > 0:
            self.redirect("/login")
            return
        self.render_tpl("setup.html", error=None)

    def post(self):
        if db.count_users() > 0:
            self.redirect("/login")
            return
        name = self.get_body_argument("name", "").strip()
        email = self.get_body_argument("email", "").strip()
        password = self.get_body_argument("password", "")
        if not name or not email or len(password) < 6:
            self.render_tpl("setup.html", error="Please fill all fields; password must be 6+ characters.")
            return
        uid = db.create_user(name, email, auth.hash_password(password), role="admin")
        self.set_secure_cookie("user_id", str(uid))
        self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        if db.count_users() == 0:
            self.redirect("/setup")
            return
        self.render_tpl("login.html", error=None, next=self.get_argument("next", "/"))

    def post(self):
        email = self.get_body_argument("email", "").strip()
        password = self.get_body_argument("password", "")
        user = db.get_user_by_email(email)
        if not user or not auth.verify_password(password, user["password_hash"]):
            self.render_tpl("login.html", error="Invalid email or password.", next="/")
            return
        self.set_secure_cookie("user_id", str(user["id"]))
        self.redirect(self.get_body_argument("next", "/") or "/")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user_id")
        self.redirect("/login")


# ----------------------------------------------------------- dashboard ----

class DashboardHandler(BaseHandler):
    @require_login
    def get(self):
        overdue = db.list_schedules(overdue_only=True, active_only=True)
        due_soon = [s for s in db.list_schedules(upcoming_days=30, active_only=True) if s["next_due_date"] >= db.today_iso()]
        counts = db.dashboard_counts()
        counts["open_calls"] = db.count_open_service_calls()
        recent = db.recent_inspections(limit=10)
        upcoming_calls = db.upcoming_service_calls(days=14)
        self.render_tpl("dashboard.html", overdue=overdue, due_soon=due_soon,
                         counts=counts, recent=recent, type_cfg=INSPECTION_TYPES,
                         upcoming_calls=upcoming_calls, sites=db.list_sites(),
                         techs=db.list_users(), call_types=CALL_TYPES,
                         clients=db.list_clients(),
                         suggested_wo=db.next_service_call_wo_number())


# -------------------------------------------------------------- users -----

class UsersHandler(BaseHandler):
    @require_login
    def get(self):
        self.render_tpl("users.html", users=db.list_users(), error=None)

    @require_login
    def post(self):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Admins only")
            return
        name = self.get_body_argument("name", "").strip()
        email = self.get_body_argument("email", "").strip()
        password = self.get_body_argument("password", "")
        role = self.get_body_argument("role", "inspector")
        cert_number = self.get_body_argument("cert_number", "")
        phone = self.get_body_argument("phone", "")
        if not name or not email or len(password) < 6:
            self.render_tpl("users.html", users=db.list_users(),
                             error="Name, email, and a 6+ character password are required.")
            return
        try:
            db.create_user(name, email, auth.hash_password(password), role, cert_number, phone)
        except Exception as e:
            self.render_tpl("users.html", users=db.list_users(), error=f"Could not create user: {e}")
            return
        self.redirect("/users")


# ------------------------------------------------------------ clients -----

class ClientsHandler(BaseHandler):
    @require_login
    def get(self):
        search = self.get_argument("q", "").strip()
        self.render_tpl("clients.html", clients=db.list_clients(search or None), search=search)

    @require_login
    def post(self):
        name = self.get_body_argument("name", "").strip()
        if not name:
            self.redirect("/clients")
            return
        cid = db.create_client(
            name,
            contact_name=self.get_body_argument("contact_name", ""),
            phone=self.get_body_argument("phone", ""),
            email=self.get_body_argument("email", ""),
            billing_address=self.get_body_argument("billing_address", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/clients/{cid}")


class ClientDetailHandler(BaseHandler):
    @require_login
    def get(self, client_id):
        client = db.get_client(int(client_id))
        if not client:
            raise tornado.web.HTTPError(404)
        sites = db.list_sites(client_id=int(client_id))
        impact = db.client_delete_impact(int(client_id))
        self.render_tpl("client_detail.html", client=client, sites=sites, impact=impact)


class ClientDeleteHandler(BaseHandler):
    @require_login
    def post(self, client_id):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Only admins can delete clients.")
            return
        client_id = int(client_id)
        if not db.get_client(client_id):
            raise tornado.web.HTTPError(404)
        db.delete_client(client_id)
        self.redirect("/clients")


class ClientEditHandler(BaseHandler):
    @require_login
    def post(self, client_id):
        client_id = int(client_id)
        if not db.get_client(client_id):
            raise tornado.web.HTTPError(404)
        name = self.get_body_argument("name", "").strip()
        if not name:
            self.redirect(f"/clients/{client_id}")
            return
        db.update_client(
            client_id,
            name=name,
            contact_name=self.get_body_argument("contact_name", ""),
            phone=self.get_body_argument("phone", ""),
            email=self.get_body_argument("email", ""),
            billing_address=self.get_body_argument("billing_address", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/clients/{client_id}")


class SiteNewHandler(BaseHandler):
    @require_login
    def post(self, client_id):
        client_id = int(client_id)
        name = self.get_body_argument("name", "").strip()
        if not name:
            self.redirect(f"/clients/{client_id}")
            return
        sid = db.create_site(
            client_id, name,
            street=self.get_body_argument("street", ""),
            city=self.get_body_argument("city", ""),
            state=self.get_body_argument("state", ""),
            zip=self.get_body_argument("zip", ""),
            jurisdiction=self.get_body_argument("jurisdiction", ""),
            division=self.get_body_argument("division", ""),
            contact_person=self.get_body_argument("contact_person", ""),
            contact_phone=self.get_body_argument("contact_phone", ""),
            store_number=self.get_body_argument("store_number", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/sites/{sid}")


# -------------------------------------------------------------- sites -----

class SiteDetailHandler(BaseHandler):
    @require_login
    def get(self, site_id):
        site_id = int(site_id)
        site = db.get_site(site_id)
        if not site:
            raise tornado.web.HTTPError(404)
        assets = db.list_assets(site_id=site_id)
        schedules = db.list_schedules(site_id=site_id)
        inspections = db.list_inspections(site_id=site_id, limit=25)
        impact = db.site_delete_impact(site_id)
        self.render_tpl("site_detail.html", site=site, assets=assets, schedules=schedules,
                         inspections=inspections, type_cfg=INSPECTION_TYPES,
                         asset_type_labels=ASSET_TYPE_LABELS, impact=impact)


class SiteDeleteHandler(BaseHandler):
    @require_login
    def post(self, site_id):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Only admins can delete sites.")
            return
        site_id = int(site_id)
        site = db.get_site(site_id)
        if not site:
            raise tornado.web.HTTPError(404)
        client_id = site["client_id"]
        db.delete_site(site_id)
        self.redirect(f"/clients/{client_id}")


class SiteEditHandler(BaseHandler):
    @require_login
    def post(self, site_id):
        site_id = int(site_id)
        if not db.get_site(site_id):
            raise tornado.web.HTTPError(404)
        name = self.get_body_argument("name", "").strip()
        if not name:
            self.redirect(f"/sites/{site_id}")
            return
        db.update_site(
            site_id,
            name=name,
            street=self.get_body_argument("street", ""),
            city=self.get_body_argument("city", ""),
            state=self.get_body_argument("state", ""),
            zip=self.get_body_argument("zip", ""),
            jurisdiction=self.get_body_argument("jurisdiction", ""),
            division=self.get_body_argument("division", ""),
            contact_person=self.get_body_argument("contact_person", ""),
            contact_phone=self.get_body_argument("contact_phone", ""),
            store_number=self.get_body_argument("store_number", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/sites/{site_id}")


class AssetNewHandler(BaseHandler):
    @require_login
    def post(self, site_id):
        site_id = int(site_id)
        label = self.get_body_argument("label", "").strip()
        asset_type = self.get_body_argument("asset_type", "other")
        if not label:
            self.redirect(f"/sites/{site_id}")
            return
        db.create_asset(
            site_id, asset_type, label,
            location=self.get_body_argument("location", ""),
            manufacturer=self.get_body_argument("manufacturer", ""),
            model=self.get_body_argument("model", ""),
            serial_number=self.get_body_argument("serial_number", ""),
            size=self.get_body_argument("size", ""),
            install_date=self.get_body_argument("install_date", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/sites/{site_id}")


class AssetDetailHandler(BaseHandler):
    @require_login
    def get(self, asset_id):
        asset_id = int(asset_id)
        asset = db.get_asset(asset_id)
        if not asset:
            raise tornado.web.HTTPError(404)
        site = db.get_site(asset["site_id"])
        schedules = db.list_schedules(site_id=asset["site_id"])
        schedules = [s for s in schedules if s["asset_id"] == asset_id]
        inspections = db.list_inspections(asset_id=asset_id, limit=25)
        impact = db.asset_delete_impact(asset_id)
        self.render_tpl("asset_detail.html", asset=asset, site=site, schedules=schedules,
                         inspections=inspections, type_cfg=INSPECTION_TYPES, impact=impact,
                         asset_type_labels=ASSET_TYPE_LABELS)


class AssetDeleteHandler(BaseHandler):
    @require_login
    def post(self, asset_id):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Only admins can delete equipment.")
            return
        asset_id = int(asset_id)
        asset = db.get_asset(asset_id)
        if not asset:
            raise tornado.web.HTTPError(404)
        site_id = asset["site_id"]
        db.delete_asset(asset_id)
        self.redirect(f"/sites/{site_id}")


class AssetEditHandler(BaseHandler):
    @require_login
    def post(self, asset_id):
        asset_id = int(asset_id)
        asset = db.get_asset(asset_id)
        if not asset:
            raise tornado.web.HTTPError(404)
        label = self.get_body_argument("label", "").strip()
        if not label:
            self.redirect(f"/assets/{asset_id}")
            return
        status = self.get_body_argument("status", "active")
        if status not in ("active", "inactive"):
            status = "active"
        db.update_asset(
            asset_id,
            label=label,
            asset_type=self.get_body_argument("asset_type", asset["asset_type"]),
            status=status,
            location=self.get_body_argument("location", ""),
            manufacturer=self.get_body_argument("manufacturer", ""),
            model=self.get_body_argument("model", ""),
            serial_number=self.get_body_argument("serial_number", ""),
            size=self.get_body_argument("size", ""),
            install_date=self.get_body_argument("install_date", ""),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/assets/{asset_id}")


class ScheduleSetHandler(BaseHandler):
    @require_login
    def post(self):
        site_id = int(self.get_body_argument("site_id"))
        asset_id = self.get_body_argument("asset_id", "") or None
        asset_id = int(asset_id) if asset_id else None
        inspection_type = self.get_body_argument("inspection_type")
        next_due_date = self.get_body_argument("next_due_date")
        cfg = get_type_config(inspection_type)
        freq = cfg["frequency_months"] if cfg else 12
        db.set_manual_due_date(site_id, asset_id, inspection_type, freq, next_due_date)
        back = self.get_body_argument("back", f"/sites/{site_id}")
        self.redirect(back)


# ----------------------------------------------------------- service calls -

class ServiceCallsHandler(BaseHandler):
    @require_login
    def get(self):
        status = self.get_argument("status", "") or None
        self.render_tpl("service_calls.html", calls=db.list_service_calls(status=status),
                         selected_status=status or "", call_types=CALL_TYPES,
                         call_statuses=CALL_STATUSES, sites=db.list_sites(), techs=db.list_users(),
                         clients=db.list_clients(), suggested_wo=db.next_service_call_wo_number())

    @require_login
    def post(self):
        site_id = self.get_body_argument("site_id", "") or None
        site_id = int(site_id) if site_id else None
        existing_client_id = self.get_body_argument("existing_client_id", "") or None
        existing_client_id = int(existing_client_id) if existing_client_id else None
        new_site_name = self.get_body_argument("new_site_name", "").strip()
        customer_name = self.get_body_argument("customer_name", "").strip()
        location_address = self.get_body_argument("location_address", "").strip()
        scheduled_date = self.get_body_argument("scheduled_date", "").strip()
        description = self.get_body_argument("description", "").strip()
        if not scheduled_date or not description or not (site_id or customer_name or new_site_name):
            self.redirect(self.get_body_argument("back", "/service-calls"))
            return

        # If no existing site was picked but there's enough info to set one up
        # (either an existing client + a new site name, or a brand-new
        # customer name + a new site name), create the client/site now so
        # this call — and every future one — is tracked against a real record.
        if not site_id and new_site_name:
            client_id = existing_client_id
            if not client_id and customer_name:
                client_id = db.create_client(customer_name)
            if client_id:
                site_id = db.create_site(client_id, new_site_name, street=location_address)

        assigned_to = self.get_body_argument("assigned_to", "") or None
        assigned_to = int(assigned_to) if assigned_to else None
        db.create_service_call(
            scheduled_date=scheduled_date,
            description=description,
            site_id=site_id,
            customer_name=customer_name,
            location_address=location_address,
            contact_name=self.get_body_argument("contact_name", ""),
            contact_phone=self.get_body_argument("contact_phone", ""),
            call_type=self.get_body_argument("call_type", "Service Call"),
            work_order_number=self.get_body_argument("work_order_number", ""),
            scheduled_time=self.get_body_argument("scheduled_time", ""),
            assigned_to=assigned_to,
            notes=self.get_body_argument("notes", ""),
            created_by=self.current_user["id"],
        )
        self.redirect(self.get_body_argument("back", "/service-calls"))


class ServiceCallDetailHandler(BaseHandler):
    @require_login
    def get(self, call_id):
        call_id = int(call_id)
        call = db.get_service_call(call_id)
        if not call:
            raise tornado.web.HTTPError(404)
        self.render_tpl("service_call_detail.html", call=call, call_types=CALL_TYPES,
                         call_statuses=CALL_STATUSES, sites=db.list_sites(), techs=db.list_users(),
                         attachments=db.list_attachments(call_id), attachment_kinds=db.ATTACHMENT_KINDS)


MAX_ATTACHMENT_SIZE = 15 * 1024 * 1024  # 15MB per file — generous for phone photos, PDFs, etc.


class ServiceCallAttachmentsHandler(BaseHandler):
    @require_login
    def post(self, call_id):
        call_id = int(call_id)
        if not db.get_service_call(call_id):
            raise tornado.web.HTTPError(404)
        kind = self.get_body_argument("kind", "photo")
        if kind not in db.ATTACHMENT_KINDS:
            kind = "other"
        caption = self.get_body_argument("caption", "")
        files = self.request.files.get("file", [])
        skipped = 0
        for f in files:
            if len(f["body"]) > MAX_ATTACHMENT_SIZE:
                skipped += 1
                continue
            db.create_attachment(
                call_id, kind, f["filename"], f["content_type"] or "application/octet-stream",
                f["body"], caption, self.current_user["id"],
            )
        back = f"/service-calls/{call_id}"
        if skipped:
            back += f"?skipped={skipped}"
        self.redirect(back)


class ServiceCallAttachmentFileHandler(BaseHandler):
    @require_login
    def get(self, call_id, attachment_id):
        att = db.get_attachment_file(int(attachment_id))
        if not att or att["service_call_id"] != int(call_id):
            raise tornado.web.HTTPError(404)
        self.set_header("Content-Type", att["content_type"] or "application/octet-stream")
        if not (att["content_type"] or "").startswith("image/"):
            self.set_header("Content-Disposition", f'attachment; filename="{att["filename"] or "file"}"')
        self.write(att["file_data"])


class ServiceCallAttachmentDeleteHandler(BaseHandler):
    @require_login
    def post(self, call_id, attachment_id):
        call_id = int(call_id)
        att = db.get_attachment_file(int(attachment_id))
        if not att or att["service_call_id"] != call_id:
            raise tornado.web.HTTPError(404)
        db.delete_attachment(int(attachment_id))
        self.redirect(f"/service-calls/{call_id}")


class ServiceCallPdfHandler(BaseHandler):
    @require_login
    def get(self, call_id):
        call = db.get_service_call(int(call_id))
        if not call:
            raise tornado.web.HTTPError(404)
        pdf_bytes = pdf_gen.generate_service_call_pdf(call)
        self.set_header("Content-Type", "application/pdf")
        self.set_header("Content-Disposition",
                         f'inline; filename="SCFP_WorkOrder_{call_id}.pdf"')
        self.write(pdf_bytes)


class ServiceCallEditHandler(BaseHandler):
    @require_login
    def post(self, call_id):
        call_id = int(call_id)
        if not db.get_service_call(call_id):
            raise tornado.web.HTTPError(404)
        site_id = self.get_body_argument("site_id", "") or None
        site_id = int(site_id) if site_id else None
        assigned_to = self.get_body_argument("assigned_to", "") or None
        assigned_to = int(assigned_to) if assigned_to else None
        db.update_service_call(
            call_id,
            site_id=site_id,
            customer_name=self.get_body_argument("customer_name", "").strip(),
            location_address=self.get_body_argument("location_address", ""),
            contact_name=self.get_body_argument("contact_name", ""),
            contact_phone=self.get_body_argument("contact_phone", ""),
            call_type=self.get_body_argument("call_type", "Service Call"),
            work_order_number=self.get_body_argument("work_order_number", ""),
            description=self.get_body_argument("description", "").strip(),
            scheduled_date=self.get_body_argument("scheduled_date", "").strip(),
            scheduled_time=self.get_body_argument("scheduled_time", ""),
            assigned_to=assigned_to,
            status=self.get_body_argument("status", "Scheduled"),
            notes=self.get_body_argument("notes", ""),
        )
        self.redirect(f"/service-calls/{call_id}")


class ServiceCallStatusHandler(BaseHandler):
    @require_login
    def post(self, call_id):
        call_id = int(call_id)
        if not db.get_service_call(call_id):
            raise tornado.web.HTTPError(404)
        status = self.get_body_argument("status", "Scheduled")
        if status not in CALL_STATUSES:
            status = "Scheduled"
        db.set_service_call_status(call_id, status)
        self.redirect(self.get_body_argument("back", "/service-calls"))


class ServiceCallDeleteHandler(BaseHandler):
    @require_login
    def post(self, call_id):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Only admins can delete service calls.")
            return
        call_id = int(call_id)
        if not db.get_service_call(call_id):
            raise tornado.web.HTTPError(404)
        db.delete_service_call(call_id)
        self.redirect("/service-calls")


# --------------------------------------------------------- inspections ----

TABLE_ROW_RE = re.compile(r"^tbl_(?P<field>[A-Za-z0-9_]+)_(?P<idx>\d+)_(?P<col>[A-Za-z0-9_]+)$")


def parse_form_data(handler, cfg):
    """Reconstructs the form_data dict (incl. table rows) from posted args."""
    data = {}
    all_fields = list(CLOSING_SECTION["fields"])
    if cfg:
        for section in cfg["sections"]:
            all_fields.extend(section["fields"])

    simple_keys = {f["key"] for f in all_fields if f["type"] != "table"}
    table_fields = {f["key"]: f for f in all_fields if f["type"] == "table"}

    for key in simple_keys:
        val = handler.get_body_argument(key, "")
        if val != "":
            data[key] = val

    tables = {}
    for arg_key in handler.request.body_arguments:
        m = TABLE_ROW_RE.match(arg_key)
        if not m:
            continue
        field, idx, col = m.group("field"), int(m.group("idx")), m.group("col")
        if field not in table_fields:
            continue
        val = handler.get_body_argument(arg_key, "")
        tables.setdefault(field, {}).setdefault(idx, {})[col] = val

    for field, idx_map in tables.items():
        rows = []
        for idx in sorted(idx_map):
            row = idx_map[idx]
            if any(v not in (None, "") for v in row.values()):
                rows.append(row)
        if rows:
            data[field] = rows

    return data


class InspectionNewHandler(BaseHandler):
    @require_login
    def get(self):
        inspection_type = self.get_argument("type", "")
        site_id = self.get_argument("site_id", "")
        asset_id = self.get_argument("asset_id", "")
        cfg = get_type_config(inspection_type) if inspection_type else None
        site = db.get_site(int(site_id)) if site_id else None
        asset = db.get_asset(int(asset_id)) if asset_id else None
        assets = db.list_assets(site_id=int(site_id)) if site_id else []
        prefill = asset_prefill_data(asset, inspection_type) if asset else {}
        self.render_tpl("inspection_form.html", cfg=cfg, inspection_type=inspection_type,
                         site=site, asset=asset, assets=assets, closing=CLOSING_SECTION,
                         site_id=site_id, asset_id=asset_id, data=prefill,
                         prefilled_from_asset=bool(prefill))

    @require_login
    def post(self):
        inspection_type = self.get_body_argument("inspection_type")
        cfg = get_type_config(inspection_type)
        if not cfg:
            raise tornado.web.HTTPError(400, "Unknown inspection type")
        site_id = int(self.get_body_argument("site_id"))
        asset_id = self.get_body_argument("asset_id", "") or None
        asset_id = int(asset_id) if asset_id else None
        inspection_date = self.get_body_argument("inspection_date", db.today_iso())

        data = parse_form_data(self, cfg)

        overall_result = data.get("overall_result", "")
        system_impaired = 1 if data.get("system_impaired") == "Yes" else 0
        critical = 1 if data.get("critical_deficiencies") == "Yes" else 0
        non_critical = 1 if data.get("non_critical_deficiencies") == "Yes" else 0
        satisfactory = 1 if data.get("satisfactory") == "Yes" else 0

        iid = db.create_inspection(
            site_id, asset_id, inspection_type, self.current_user["id"], inspection_date,
            overall_result, system_impaired, critical, non_critical, satisfactory,
            data, self.current_user["id"],
        )

        if overall_result != "Incomplete":
            db.upsert_schedule(site_id, asset_id, inspection_type, cfg["frequency_months"], inspection_date)

        self.redirect(f"/inspections/{iid}")


class InspectionEditHandler(BaseHandler):
    """Edit an already-submitted inspection. Site/asset/type are fixed once
    created (correcting those means logging a fresh inspection); everything
    else — the date and every form field — can be corrected here."""

    @require_login
    def get(self, inspection_id):
        inspection = db.get_inspection(int(inspection_id))
        if not inspection:
            raise tornado.web.HTTPError(404)
        cfg = get_type_config(inspection["inspection_type"])
        data = json.loads(inspection["form_data"] or "{}")
        site = db.get_site(inspection["site_id"])
        self.render_tpl("inspection_form.html", cfg=cfg, inspection_type=inspection["inspection_type"],
                         site=site, asset=None, assets=[], closing=CLOSING_SECTION,
                         site_id=str(inspection["site_id"]), asset_id="",
                         edit_mode=True, inspection=inspection, data=data)

    @require_login
    def post(self, inspection_id):
        inspection_id = int(inspection_id)
        existing = db.get_inspection(inspection_id)
        if not existing:
            raise tornado.web.HTTPError(404)
        cfg = get_type_config(existing["inspection_type"])
        inspection_date = self.get_body_argument("inspection_date", existing["inspection_date"])

        data = parse_form_data(self, cfg)

        overall_result = data.get("overall_result", "")
        system_impaired = 1 if data.get("system_impaired") == "Yes" else 0
        critical = 1 if data.get("critical_deficiencies") == "Yes" else 0
        non_critical = 1 if data.get("non_critical_deficiencies") == "Yes" else 0
        satisfactory = 1 if data.get("satisfactory") == "Yes" else 0

        db.update_inspection(
            inspection_id, inspection_date, overall_result, system_impaired, critical,
            non_critical, satisfactory, data, self.current_user["id"],
        )

        if overall_result != "Incomplete":
            db.upsert_schedule(existing["site_id"], existing["asset_id"], existing["inspection_type"],
                                cfg["frequency_months"], inspection_date)

        self.redirect(f"/inspections/{inspection_id}")


class InspectionDetailHandler(BaseHandler):
    @require_login
    def get(self, inspection_id):
        inspection = db.get_inspection(int(inspection_id))
        if not inspection:
            raise tornado.web.HTTPError(404)
        cfg = get_type_config(inspection["inspection_type"])
        data = json.loads(inspection["form_data"] or "{}")
        self.render_tpl("inspection_detail.html", inspection=inspection, cfg=cfg,
                         data=data, closing=CLOSING_SECTION)


class InspectionDeleteHandler(BaseHandler):
    """Admin-only: permanently removes an inspection (e.g. an accidental
    duplicate entry) and recalculates the due-date schedule from whatever
    inspections of that type remain."""

    @require_login
    def post(self, inspection_id):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Only admins can delete inspections.")
            return
        inspection_id = int(inspection_id)
        inspection = db.get_inspection(inspection_id)
        if not inspection:
            raise tornado.web.HTTPError(404)
        cfg = get_type_config(inspection["inspection_type"])
        site_id = inspection["site_id"]
        deleted = db.delete_inspection(inspection_id)
        if deleted and cfg:
            db.recompute_schedule(deleted["site_id"], deleted["asset_id"],
                                   deleted["inspection_type"], cfg["frequency_months"])
        self.redirect(f"/sites/{site_id}")


class InspectionPdfHandler(BaseHandler):
    @require_login
    def get(self, inspection_id):
        inspection = db.get_inspection(int(inspection_id))
        if not inspection:
            raise tornado.web.HTTPError(404)
        client = db.get_client(inspection["client_id"])
        site = db.get_site(inspection["site_id"])
        asset = db.get_asset(inspection["asset_id"]) if inspection["asset_id"] else None
        pdf_bytes = pdf_gen.generate_inspection_pdf(inspection, client, site, asset)
        self.set_header("Content-Type", "application/pdf")
        self.set_header("Content-Disposition",
                         f'inline; filename="SCFP_Inspection_{inspection_id}.pdf"')
        self.write(pdf_bytes)


class InspectionsListHandler(BaseHandler):
    @require_login
    def get(self):
        inspection_type = self.get_argument("type", "") or None
        inspections = db.list_inspections(inspection_type=inspection_type, limit=200)
        self.render_tpl("inspections_list.html", inspections=inspections,
                         type_cfg=INSPECTION_TYPES, selected_type=inspection_type or "")


# -------------------------------------------------------------- search ----

class SearchHandler(BaseHandler):
    @require_login
    def get(self):
        q = self.get_argument("q", "").strip()
        clients = db.list_clients(q) if q else []
        sites = db.list_sites(search=q) if q else []
        self.render_tpl("search.html", q=q, clients=clients, sites=sites)


# -------------------------------------------------------------- backup ----

class BackupHandler(BaseHandler):
    @require_login
    def get(self):
        if self.current_user["role"] != "admin":
            self.set_status(403)
            self.write("Admins only")
            return
        if not os.path.exists(db.DB_PATH):
            raise tornado.web.HTTPError(404, "Database file not found")
        stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M")
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", f'attachment; filename="scfp_backup_{stamp}.db"')
        with open(db.DB_PATH, "rb") as f:
            self.write(f.read())


def make_app():
    settings = dict(
        cookie_secret=os.environ.get("SCFP_COOKIE_SECRET", "dev-secret-change-me-in-production"),
        xsrf_cookies=True,
        static_path=os.path.join(BASE_DIR, "static"),
        debug=os.environ.get("SCFP_DEBUG", "0") == "1",
    )
    return tornado.web.Application([
        (r"/setup", SetupHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/", DashboardHandler),
        (r"/users", UsersHandler),
        (r"/clients", ClientsHandler),
        (r"/clients/(\d+)", ClientDetailHandler),
        (r"/clients/(\d+)/edit", ClientEditHandler),
        (r"/clients/(\d+)/delete", ClientDeleteHandler),
        (r"/clients/(\d+)/sites/new", SiteNewHandler),
        (r"/sites/(\d+)", SiteDetailHandler),
        (r"/sites/(\d+)/edit", SiteEditHandler),
        (r"/sites/(\d+)/delete", SiteDeleteHandler),
        (r"/sites/(\d+)/assets/new", AssetNewHandler),
        (r"/assets/(\d+)", AssetDetailHandler),
        (r"/assets/(\d+)/edit", AssetEditHandler),
        (r"/assets/(\d+)/delete", AssetDeleteHandler),
        (r"/schedules/set", ScheduleSetHandler),
        (r"/service-calls", ServiceCallsHandler),
        (r"/service-calls/(\d+)", ServiceCallDetailHandler),
        (r"/service-calls/(\d+)/edit", ServiceCallEditHandler),
        (r"/service-calls/(\d+)/pdf", ServiceCallPdfHandler),
        (r"/service-calls/(\d+)/attachments", ServiceCallAttachmentsHandler),
        (r"/service-calls/(\d+)/attachments/(\d+)/file", ServiceCallAttachmentFileHandler),
        (r"/service-calls/(\d+)/attachments/(\d+)/delete", ServiceCallAttachmentDeleteHandler),
        (r"/service-calls/(\d+)/status", ServiceCallStatusHandler),
        (r"/service-calls/(\d+)/delete", ServiceCallDeleteHandler),
        (r"/inspections", InspectionsListHandler),
        (r"/inspections/new", InspectionNewHandler),
        (r"/inspections/(\d+)", InspectionDetailHandler),
        (r"/inspections/(\d+)/edit", InspectionEditHandler),
        (r"/inspections/(\d+)/delete", InspectionDeleteHandler),
        (r"/inspections/(\d+)/pdf", InspectionPdfHandler),
        (r"/search", SearchHandler),
        (r"/admin/backup", BackupHandler),
    ], **settings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()
    db.init_db()
    app = make_app()
    app.listen(args.port)
    print(f"SCFP Inspection Tracker running at http://localhost:{args.port}")
    tornado.ioloop.IOLoop.current().start()
