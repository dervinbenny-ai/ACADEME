# Academe

## AI-Based Smart Academic Data Collection and Management System

**Collect only what you need. Reuse what you already know.**

A Flask application with a MySQL database, server-rendered Jinja pages, a dynamic form builder, verification workflows and locally hosted frontend assets. Start it with `python app.py`; no Node build step is needed.

Start with [QUICKSTART.md](QUICKSTART.md). The [UI delivery guide](UI_DELIVERY.md) describes the design modules, project tree, interactions, motion, and responsive behavior. See [VALIDATION.md](VALIDATION.md) for completed checks and limitations.

This edition uses `academe_db` as its default MySQL database. The September 29 enhancements extend the existing application in place. See [ENHANCEMENTS.md](ENHANCEMENTS.md) for the complete change inventory and upgrade procedure. Keep your existing database configuration and private uploads when upgrading.

## What it solves

Institutions repeatedly collect the same student identity and contact information in separate spreadsheets. Academe keeps one master student profile, reuses existing values in new requests, collects missing information and merges approved changes with a version history.

## Role hierarchy

| Role | Responsibility |
|---|---|
| Super Admin | Create/manage HOD accounts, inspect system audit and control institution policies |
| Admin / HOD | Create departments, classes and teachers; assign classes; send requirements to teachers; monitor and export data |
| Teacher | Create students only in assigned classes, build/publish requests, review submissions, resolve conflicts and return completed reports |
| Student | View own profile, complete assigned requests, upload documents, respond to corrections and track status |

Super Admin is a system role. The three academic modules are Admin, Teacher and Student. An Admin cannot create students or publish student forms. The server checks roles and current class assignments on every protected operation. Each HOD sees their own departments and managed teachers; teachers see their assigned classes; students see only their own data.

## Main workflow

1. Setup creates roles, the field library, policy defaults and the initial Super Admin only.
2. Super Admin signs in at `/admin/login`, changes the initial password and creates an HOD account.
3. HOD creates a department, a teacher and a class, and assigns the teacher to that class.
4. Teacher signs in at `/teacher/login`, changes the temporary password and creates students in their assigned class.
5. HOD creates an information requirement with a class, assigned teacher and deadline.
6. Teacher receives a notification and creates a linked data request. Local recommendations can suggest placement, internship, medical and other fields.
7. Teacher selects students, configures fields and reuse policies, saves a draft, reviews it and explicitly publishes it.
8. Student signs in at `/student/login`. Existing master values appear as **Already available**. Missing values and document uploads are collected.
9. A normal submission locks immediately. Teacher verifies, approves, requests a field-scoped correction, or rejects it. Student-requested revisions require teacher approval and are usable once. Every submitted revision is preserved.
10. Verification opens a separate **Update Master Student Profile?** review. Teacher selects fields, resolves conflicts with **Keep existing**, **Accept new**, or **Request clarification**, or skips the update. Only selected accepted values update the profile and its history; a skipped update leaves the submission valid.
11. When every target in the requirement's published requests is verified or approved, Teacher sends the completed report to HOD.
12. HOD previews, filters and exports the report, then accepts/completes or returns it for correction.

## Features

- Separate login pages, database-derived roles, password hashing, first-login password change, account activation/deactivation and authorized password reset.
- Five failed login attempts lock an account for 15 minutes. Sessions expire after 30 minutes of inactivity; remember-me is configurable per login.
- Custom CSS design system, responsive sidebar, mobile navigation, confirmation dialogs, loading states and contextual empty states.
- Flexible profile field storage and a reusable field library.
- Form builder: text, textarea, integer, decimal, date, email, phone, URL, select, multi-select, radio, checkbox and file fields; required/optional flags, ordering, help text, choices and numeric bounds.
- Draft editing and template duplication. Published field definitions are locked to preserve the meaning of submitted data.
- Automatic reuse, explicit confirmation and permitted-update policies. Identity fields always reuse canonical records; teachers edit identity through the student account screen.
- Submission drafts, one-time submission, immutable revision snapshots, approved field-scoped revisions, separate verification and selective profile merge, and actor-attributed version history.
- Student Master Profile editing for permitted personal fields; teacher approval for sensitive changes; institution-managed academic fields.
- HOD student directory grouped by department and class with explicit stable ordering and scoped filters.
- Student and HOD deadlines, Teacher → HOD extension approval for published linked requests, deadline history, and notifications only to students who have never submitted. Independent requests retain direct teacher deadline changes with a reason.
- Internal notifications with destination links and read state.
- Threaded messages restricted to HOD ↔ Teacher and assigned Teacher ↔ Student relationships.
- Academic events and student registration.
- Authenticated document downloads, UUID storage names, extension/content checks, bounded file sizes, text PDF extraction and optional image OCR.
- Rule-based recommendations, a form assistant, safe natural-language search and a student assistant that queries the logged-in student's records.
- Real charts for departments, classes, requirements, monthly request activity, profile completion and submissions.
- Filtered reports with selected columns and sorting; styled Excel with metadata, frozen headers, filters and summary sheet; paginated server-generated PDF; CSV with spreadsheet formula neutralization.
- Secure QR URLs containing opaque tokens. Login and normal record access checks are still required.
- Audit records for account, collection, verification, document and report operations.

## Technology

Python 3.11+, Flask, SQLAlchemy, Flask-Migrate/Alembic, Flask-Login, Flask-WTF CSRF, PyMySQL, MySQL 8+, Werkzeug, python-dotenv, email-validator, OpenPyXL, ReportLab, Pillow, PyTesseract, pypdf, qrcode and pytest. HTML, Jinja, custom CSS, Bootstrap 5, Bootstrap Icons, Chart.js and ES6 JavaScript. No paid AI API is required.

## Project structure

```text
app.py                    Application factory and primary launcher
config.py                 Environment configuration
extensions.py             Database, login, migration and CSRF extensions
models/                   Relational schema (32 tables)
routes/                   Auth, management, collection, dashboard and supporting features
services/                 Authorization, validation, profiles, reports, documents and reminders
ai/                       Local recommendations, merge engine, search, assistant and analytics
templates/                Jinja screens and shared components
static/css/               Responsive custom design system
static/js/                Form builder, interactions and charts
static/vendor/            Local Bootstrap, icons, Chart.js and Inter font
migrations/               Initial and additive workflow Alembic migrations
scripts/                  Setup, Super Admin creation and reminders
tests/                    Acceptance and security integration tests
```

## Upgrade an existing installation

Back up the configured database and private uploads, stop the application, and keep your existing `.env`. From the project directory, with its virtual environment active:

```powershell
python -m pip install -r requirements.txt
python -m flask --app app db upgrade
python app.py
```

The additive revision is `20260929_workflows`. Do not recreate or reset the database. [ENHANCEMENTS.md](ENHANCEMENTS.md) explains legacy snapshots and rollback limitations.

## Install on Windows / VS Code

Install Python 3.11 or newer and MySQL 8 or newer. Ensure Python is on PATH. Open this project directory in VS Code, then use its terminal:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your MySQL username/password, institution name, Super Admin credentials and a random secret:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Put the result in `SECRET_KEY`. `SuperAdmin@123` in `.env.example` is **development-only**. Replace it before using real records.

### MySQL setup

Start the MySQL service. Configure:

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-local-password
MYSQL_DATABASE=academe_db
```

Run:

```powershell
python scripts/setup_database.py
python app.py
```

The setup command creates the database when needed, applies the committed migration, then idempotently seeds essential roles, reusable fields and the Super Admin. It does **not** create HODs, teachers, students, classes or submissions.

To intentionally erase all application database records and start again with only a new Super Admin, stop the app and run `python scripts/reset_database.py`. Confirm by typing `RESET`; the script asks for the new account details and reads the password without echoing it. This does not delete files in `instance/uploads`, so remove those separately if they should also be purged. Back up anything you may need first.

If your MySQL account cannot create databases, create `academe_db` with a database administrator and grant the application account schema privileges. For deployment, use a dedicated least-privilege application account rather than root.

Open [the local application](http://127.0.0.1:5000). Select **Admin portal** for both Super Admin and HOD. No role dropdown exists.

### Additional migration commands

The migration repository already exists; do not run `flask db init` again.

```powershell
flask --app app:create_app db upgrade
flask --app app:create_app db current
# Only after intentionally changing models:
flask --app app:create_app db migrate -m "Describe schema change"
flask --app app:create_app db upgrade
```

To ensure the initial Super Admin exists after migration:

```powershell
python scripts/create_superadmin.py
```

This command never resets an existing Super Admin password. For operator recovery, use a trusted Python application context to find that account, call `set_password()` and set `first_login=True`; never write a plaintext password into a database column.

### Optional SQLite evaluation

MySQL is the default deployment database. For an isolated local evaluation without MySQL, set this explicit override in `.env`, then run the same setup and startup commands:

```dotenv
DATABASE_URL=sqlite:///academic.db
```

Remove this override to use MySQL. SQLite files are stored under `instance/`. Automated tests create isolated temporary databases; their fixture records never populate your normal application database.

## Environment variables

| Variable | Purpose |
|---|---|
| `FLASK_ENV` | Set `production` to require an explicit strong secret |
| `SECRET_KEY` | Stable random signing/CSRF secret; development generates a local secret if unset |
| `MYSQL_*` | MySQL connection settings |
| `DATABASE_URL` | Optional full SQLAlchemy URL override |
| `SUPERADMIN_USERNAME`, `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD` | Initial Super Admin setup credentials |
| `UPLOAD_FOLDER` | Defaults to private `instance/uploads`; never place under public static assets |
| `MAX_UPLOAD_MB` | Maximum size of the complete HTTP upload request; default 10 MB |
| `TESSERACT_CMD` | Optional full path to the Tesseract executable |
| `AI_PROVIDER` | Local engine; this release does not send records to an external LLM |
| `INSTITUTION_NAME` | Workspace and exported report institution name |
| `SESSION_COOKIE_SECURE` | Set `true` when serving over HTTPS |
| `PORT` | Development server port; default 5000 |

All displayed deadlines use **UTC**, explicitly labeled in forms and views.

## OCR and document handling

PDF text is extracted with pypdf. Scanned PDFs do not contain text; upload a page as PNG/JPEG for image OCR. Install Tesseract separately and set `TESSERACT_CMD` if it is not on PATH. The Python wrapper does not include the OCR executable.

If OCR is unavailable or times out, the document is still saved and manual entry remains available. Extracted text and candidate fields are shown for student review. Confirmation saves the reviewed extraction, not the master profile. Enter the reviewed values into a teacher request for verification. Do not rely on OCR output without checking the source document.

Documents are stored outside static routes. PDF/image validation and size limits are implemented; malware scanning is not included. Use an antivirus or document scanning service before deploying a public upload service.

## Local AI behavior

Recommendations map recognized keywords and field labels to the reusable library. Teachers accept, remove, add and reorder suggestions manually. The engine never publishes forms automatically. Unknown prompts show a helpful message and retain the normal field library.

The student assistant recognizes pending forms, deadlines, submitted requests, profile completeness, missing fields and teacher questions. It returns actual database values; unsupported questions receive an explicit not-found response.

Student search accepts normal names/register numbers/email or these known intents:

```text
Show S4 MCA students without blood group
Show students who haven't submitted internship details
Show incomplete student profiles
```

Known intents map to scoped ORM queries. Arbitrary SQL is never generated or executed.

## Reminder scheduling

```powershell
python scripts/send_reminders.py
```

Run daily in Windows Task Scheduler using the virtual environment's Python executable, with this project directory as **Start in**, and `scripts/send_reminders.py` as the argument. Reminders are sent at three days, one day and the deadline day. Only students who have never submitted (including draft-only responses) receive student deadline reminders. HOD deadline reminders go to teachers. Unique reminder keys prevent repeats on the same deadline schedule. No scheduler is installed automatically.

## Testing

```powershell
python -m pytest -q
```

Tests cover the complete creation/collection/correction/verification/export flow, portal restrictions, class ownership, target access, deadlines, unverified completion rejection, explicit conflict decisions, notifications, reminder deduplication, smart search, account controls, documents, messaging, QR access, activities, CSV formula safety, CSRF and page rendering.

See `VALIDATION.md` for the checks performed during delivery and environment limitations.

## Troubleshooting

- **Python not recognized:** install Python and enable Add Python to PATH, then reopen the terminal.
- **Module not found:** activate the virtual environment and reinstall requirements.
- **Connection refused / 503:** start MySQL, check `.env`, then run setup. Normal startup intentionally does not silently switch databases.
- **Access denied:** check the MySQL username, password and schema privileges.
- **No assigned class:** HOD must edit the class and select the teacher. The server rejects unrelated class IDs.
- **Cannot publish:** add active students and at least one field; ensure the deadline is in the future.
- **Cannot return report:** every target in the requirement's published requests must be verified or approved.
- **Correction after deadline:** an explicitly approved field-scoped revision permits one resubmission even after the normal deadline; other students remain subject to the deadline. A rejected submission stays locked until the student requests and receives revision approval.
- **CSRF expired:** reload the page and sign in again if necessary.
- **Missing OCR:** configure Tesseract or enter the extracted details manually.
- **Password recovery:** the forgot-password page notifies the account manager internally. Email delivery is not configured in this release.
- **Report cells begin with an apostrophe:** dangerous spreadsheet formula prefixes are neutralized on export.

## Deployment notes

`python app.py` is the intended local development launcher. For a public deployment, use a production WSGI server behind HTTPS, configure secure cookies, provide a persistent secret, back up both MySQL and private uploads, apply database migrations during release, and restrict database credentials. No public hosting, email provider or paid AI provider has been configured.

## Frontend licenses

Bundled frontend dependencies: Bootstrap 5.3.3 (MIT), Bootstrap Icons 1.11.3 (MIT), Chart.js 4.4.8 (MIT), and Inter (SIL Open Font License). Their license texts are included in `static/vendor/licenses/`.
