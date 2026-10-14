# Start Academe

The September 29 release extends this existing Flask application. It still starts with `python app.py`.

## Upgrade your existing installation

Back up your configured database and private uploads, stop the application, and keep the existing `.env`. Activate your current virtual environment, then run from this folder:

```powershell
python -m pip install -r requirements.txt
python -m flask --app app db upgrade
python app.py
```

Do not delete/recreate your database or run `db init`. The new migration adds workflow tables and preserves existing records. Read `ENHANCEMENTS.md` before upgrading.

## First run on Windows

Install Python 3.11+ and MySQL 8+, then open a terminal in the `academe` folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your MySQL connection, institution name, a random `SECRET_KEY`, and your initial Super Admin credentials. The new project defaults to its own `academe_db` database. Start MySQL, then run:

```powershell
python scripts/setup_database.py
python app.py
```

Open http://127.0.0.1:5000. Choose **Admin & HOD**, sign in using the Super Admin credentials from `.env`, and complete the first-login password change.

## Every subsequent run

```powershell
.venv\Scripts\activate
python app.py
```

No npm install, build command, frontend server, or external AI key is required. Fonts, Bootstrap, icons, and Chart.js are bundled locally.

## Build your institution

1. Super Admin creates an Admin/HOD.
2. HOD creates departments, teachers, and classes, then assigns teachers to classes.
3. Teacher creates student accounts in assigned classes.
4. HOD creates a requirement for a teacher.
5. Teacher builds a linked request, saves the draft, reviews it, and publishes.
6. Students provide missing information and documents.
7. Teacher verifies the submission, then separately chooses which values to save to the Master Profile. Skipping profile updates keeps the verified submission valid.
8. Teacher returns the completed requirement to HOD; HOD reviews and exports the report.

Setup creates essential roles, the field library, and one Super Admin. It does not insert sample academic data.

## Optional evaluation without MySQL

For a separate local evaluation database, add this explicit setting to `.env` before running setup:

```dotenv
DATABASE_URL=sqlite:///academic.db
```

Run the same setup and startup commands. Remove this override when using MySQL. This does not migrate data between databases.

## Documentation

- `ENHANCEMENTS.md`: changed files, models, migration, routes, services, notifications, tests, and upgrade details.
- `README.md`: configuration, full workflow, OCR, reminders, and troubleshooting.
- `UI_DELIVERY.md`: project tree, UI modules, interactions, motion, and responsive behavior.
- `VALIDATION.md`: completed checks and testing limitations.

PDF text extraction works through the Python dependencies. Image OCR additionally requires a local Tesseract installation; manual review remains available without it.
