# SCFP Inspection Tracker

A web app for Southern Cross Fire Protection to manage clients, sites,
equipment, inspection results, and due dates — built from your actual
inspection forms.

## What it does

- **Clients & Sites** — every customer, every location, with contact info,
  jurisdiction, and store numbers.
- **Equipment** — track individual assets (backflow assemblies, fire pumps,
  hydrants) per site with make/model/serial.
- **12 inspection types**, matching your paper forms field-for-field:
  - Backflow Prevention Assembly Inspection
  - Fire Sprinkler Annual Inspection (Wet Pipe)
  - Fire Sprinkler Annual Inspection (Dry Pipe)
  - Sprinkler 5-Year Internal Obstruction Investigation
  - Annual Dry Riser Full Trip Test
  - Annual Dry Riser Partial Trip Test
  - Fire Alarm Inspection
  - Annual Electric Fire Pump Inspection
  - Hydrant Inspection
  - Fire Hose Service Test
  - Fire Department Connection (FDC) Visual Inspection
  - Annual Fire Protection Systems Walkthrough (comprehensive site checklist)
- **Automatic due dates** — logging a completed inspection automatically
  schedules the next one (most are annual, the 5-year investigation is every
  5 years). Due dates can also be set manually for equipment you haven't
  inspected in the system yet.
- **Dashboard** — overdue and due-in-30-days lists across every client/site.
- **PDF reports** — every logged inspection can be downloaded/printed as a
  branded PDF report.
- **Multi-user logins** — each inspector/office staffer gets their own
  account; every inspection records who logged it.

## How the inspection types map to your forms

The field-by-field layout was pulled directly from the 15 PDF forms you
uploaded (backflow reports, sprinkler wet/dry/5-year reports, dry riser trip
tests, fire alarm report, fire pump report, hydrant form, hose test log, and
the FDC/comprehensive walkthrough). Long boilerplate checklists (e.g. the
alarm device inventory, sprinkler system-components checklist) were built as
flexible add-a-row tables rather than dozens of fixed checkboxes, so
inspectors aren't limited to exactly what's on the paper form.

## Quick start (run it locally first)

Requires Python 3.9+.

```bash
cd scfp-inspect
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py --port=8888
```

Open http://localhost:8888 — the first visit walks you through creating an
admin account. Add your team under **Users**, then start adding **Clients**
→ **Sites** → **Equipment**, and logging inspections.

The database is a single SQLite file at `data/scfp.db` (created
automatically). Back this file up regularly — it's your entire database.

## Getting it hosted online for the whole team

This app is plain Python (Tornado + SQLite) with no external services
required, so it can run on almost any host. I can't create hosting accounts
on your behalf, but here's the fastest path — about 15 minutes:

### Option A: Render.com (easiest, ~$7/mo for persistent disk)
1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `python app.py --port=$PORT`
4. Add a **persistent disk** mounted at `/opt/render/project/src/data` (so
   the SQLite file survives restarts/deploys).
5. Add an environment variable `SCFP_COOKIE_SECRET` set to a long random
   string (`python3 -c "import secrets; print(secrets.token_hex(32))"`).
6. Deploy. Render gives you an `https://your-app.onrender.com` URL — that's
   what your team logs into from any phone/tablet/laptop browser.

### Option B: Railway.app or Fly.io
Same idea — both support a persistent volume for `/app/data` and a Python
buildpack/Dockerfile. A minimal `Dockerfile` is included below if you'd
rather containerize:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV SCFP_DB_PATH=/app/data/scfp.db
VOLUME /app/data
EXPOSE 8888
CMD ["python", "app.py", "--port=8888"]
```

### Option C: Your own VPS (DigitalOcean, Linode, etc.)
Standard `systemd` service running `python app.py --port=8888` behind Nginx
(for HTTPS via Let's Encrypt / certbot) works fine — this is a single
lightweight Python process.

## Environment variables

| Variable              | Purpose                                         | Default              |
|------------------------|--------------------------------------------------|-----------------------|
| `SCFP_DB_PATH`         | Path to the SQLite database file                 | `data/scfp.db`        |
| `SCFP_COOKIE_SECRET`   | Secret for signed login cookies — **set this in production** | dev placeholder |
| `SCFP_DEBUG`           | `1` to enable Tornado autoreload/debug           | `0`                    |

## Known limitations / good next additions

- Inspections can be created and viewed/PDF'd, but not edited after saving —
  corrections currently mean logging a new entry. Straightforward to add if
  useful.
- No photo attachments on inspections yet (several of your forms reference
  documenting deficiencies — photos would be a natural add-on).
- No automatic email/text reminders for upcoming due dates yet — the
  dashboard surfaces them, but nothing proactively pings anyone. Easy to add
  once it's hosted somewhere that can send email (e.g. via SendGrid/SES).
- Single-company setup (no multi-tenant billing/separation) — appropriate
  since this is for SCFP internally.
- SQLite comfortably handles a small office/field team; if SCFP grows a lot,
  migrating to Postgres later is a moderate, well-trodden path.

## Project structure

```
app.py             Tornado web server & all routes
db.py               SQLite schema + queries
auth.py             Password hashing helpers
forms_config.py     Declarative field definitions for all 12 inspection types
pdf_gen.py          Generic PDF report generator (reportlab)
templates/          Jinja2 HTML templates
static/             CSS + the dynamic add-row table JS
requirements.txt    Python dependencies
```
