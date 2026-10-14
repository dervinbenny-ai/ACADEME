# Verification record

Updated September 29, 2026, for the in-place workflow enhancements.

## Automated application checks

The full suite completed with **29 passed, 6 warnings in 349.49 seconds** using isolated SQLite databases and temporary uploads. The six warnings originate from the existing Alembic environment's `db.get_engine()` compatibility call, deprecated by Flask-SQLAlchemy. They did not prevent migration or tests.

The original 15 regression tests continue to cover authentication, roles, first-login/CSRF controls, institution and account management, assigned-class ownership, requirements, local field suggestions, request publishing, profile reuse, documents, correction workflows, reporting, QR access, messages, events, assistants, notifications and scoped workspace APIs. The old automatic-merge expectation was updated to require explicit selected profile updates.

Fifteen added tests cover:

- Permitted direct profile edits, restricted payload rejection, sensitive approval/rejection, duplicate requests and profile history.
- Repeated normal submission rejection, immutable snapshots, one-use field-scoped revisions and revision rejection.
- Verification without merging, selective two-of-five merging, skip validity, conflict choices, stale-baseline rejection and clarification.
- Teacher/request ownership and other-student access rejection.
- Deadline-extension approval/rejection, invalid dates, HOD-only decisions, and notices only to never-submitted students.
- Matching filtered Excel/PDF exports for Teacher and HOD, including requirement-level exports.
- Legacy drafts with an inconsistent submission timestamp still exclude unsent response values from reports.
- Stable department/class ordering and academic contact relationships.
- Teacher identity and HOD class changes recorded in version history.
- A complete 28-step Rahul/Arun acceptance scenario from initial submission through selected merging, revision, re-verification, deadline extension, exports and profile context.
- Upgrade from the original schema with legacy account/profile/submission preservation, snapshot backfill, repeated-upgrade safety and no model/schema differences afterward.

A final browser check exposed a legacy draft with a non-null submission timestamp. The report service was tightened to exclude its unsent values. The new regression test and the Teacher/HOD export test both passed afterward (**2 passed in 18.87 seconds**). This brings the suite to **30 distinct tests verified**: the full 29-test run plus the added case, with the affected export integration test repeated after the fix.

Run after installing dependencies:

```powershell
python -m pytest tests -q
```

If the operating system's default temporary directory is restricted, choose a fresh accessible path:

```powershell
python -m pytest tests -q --basetemp=.test-tmp
```

The first final-run attempt could not create fixtures in the restricted system temp directory; the recorded successful full run used a new workspace temporary directory. No production database was used.

## Static and startup checks

- All Python application sources compiled.
- All **47 Jinja templates** compiled.
- All **16 custom JavaScript modules** passed Node syntax checking. Node is only a development verification dependency.
- All **32 table definitions** compiled with the SQLAlchemy MySQL dialect.
- The additive migration upgraded an isolated copy of the previous preview database and preserved its accounts, profiles and stored submissions.
- `app.py` started and served the new pages and bundled assets against that migrated preview.
- The application still defaults to the existing `academe_db` MySQL database; configuration remains explicit.

## Browser and PDF checks

The preview uses fictional academic records stored outside the deliverable. The September 24–25 interface review covered all four roles at 1366px desktop and 390px phone widths, theme switching, navigation, command search, notifications, builder interactions, profile tabs, report download and PDF upload/extraction review.

September 29 checks exercised the new direct profile edit and sensitive change request through real browser forms with CSRF, teacher approval and confirmation dialog, the change queue, immutable submission history and student revision-request form. The teacher approved a single internship-role field; only that field was editable, the student resubmitted, and the response locked again. Teacher verification opened the separate merge screen; applying company and role left the unselected CGPA conflict unchanged and recorded a partially applied decision. Teacher requested an extension and HOD approved it through the UI. The new HOD directory displayed S2 then S4 with stable register-number ordering. A teacher PDF download returned successfully. A legacy draft-report edge case found during browser QA was fixed and verified both in the browser and targeted tests.

New queue/history/request, selective-merge, extension and directory pages were checked at desktop and phone widths; checked pages had no persistent document-level horizontal overflow after layout transitions. No JavaScript console errors were recorded in these checks.

The HOD report was filtered to two verified students; PDF and Excel export actions both returned HTTP 200. The browser's download-event hook did not provide a saved path for the generated blob download, so downloaded-file correctness is established by the passing export integration tests and separately rendered PDF samples rather than by a browser filesystem assertion.

ReportLab generated a four-page sample collection report and an eleven-page stress report with long wrapped notes and many rows. Every page was rendered with Poppler and visually inspected in a contact sheet; the first sample page was also inspected at full size. Headers, column groups, table continuation, footer page numbers and long text remained inside page boundaries. Export tests additionally parsed PDF text and workbook cell values to verify actual filtered data rather than only file signatures.

This is functional and layout verification, not a formal accessibility certification or a complete cross-browser/device test matrix.

## Environment-dependent checks

- A live MySQL server was unavailable. MySQL dialect/schema checks passed; migration and application runtime tests used SQLite. Run the migration and acceptance checks against a backed-up MySQL staging database before production release.
- Tesseract image OCR requires an external binary and was not exercised. Existing PDF handling and manual-review fallback tests passed.
- No production deployment, public hosting, email delivery, Firefox/Safari, real mobile hardware, or assistive-technology certification was performed.
- Earlier overwritten responses from before this release cannot be recovered by migration. The new immutable history starts with the latest available legacy response and all subsequent submitted revisions.

## Package contents

The ZIP contains source, local frontend assets and licenses, both migrations, setup scripts, tests and documentation. It excludes `.env`, virtual environments, caches, databases, uploaded files, logs and preview/test records. Existing installations keep their own `.env` and uploads. Initial setup seeds essential roles/library/settings and the configured Super Admin, without sample academic data.
