# September 29 workflow enhancements

The existing Academe Flask application has been extended in place. Its role hierarchy, existing account/data model, local frontend assets, form builder, authentication, document handling, messaging, analytics and launcher remain in use. Verification now preserves collected information independently of selective Master Profile updates.

## 1. Files modified

| Area | Existing files |
|---|---|
| Application and schema | `app.py`, `models/__init__.py`, `requirements.txt` |
| Routes | `routes/collection.py`, `routes/core.py`, `routes/management.py`, `routes/workspace.py` |
| Services | `services/access.py`, `services/common.py`, `services/deadline_service.py`, `services/report_service.py` |
| Local AI | `ai/chatbot.py`, `ai/merge_engine.py` |
| UI assets | `static/css/app.css`, `static/js/tables.js` |
| Existing pages | `templates/builder.html`, `profile.html`, `report.html`, `reports.html`, `request_detail.html`, `requests.html`, `requirement_detail.html`, `review.html`, `students.html`, `submit.html` (all under `templates/`) |
| Tests and guides | `tests/test_workflow.py`, `README.md`, `QUICKSTART.md`, `UI_DELIVERY.md`, `VALIDATION.md`, generated `PROJECT_TREE.txt` |

## 2. New files

```text
migrations/versions/20260929_workflows_add_submission_changes_profile_review_.py
routes/student_workflows.py
services/change_request_service.py
services/pdf_report_service.py
services/profile_merge_service.py
services/profile_service.py
services/submission_service.py
static/css/workflows.css
templates/change_requests.html
templates/change_review.html
templates/deadline_extension.html
templates/deadline_extensions.html
templates/profile_change_form.html
templates/profile_edit.html
templates/profile_merge.html
templates/submission_change_form.html
templates/submission_history.html
templates/submission_snapshot.html
tests/test_acceptance_enhancements.py
tests/test_student_workflows.py
tests/test_workflow_migration.py
ENHANCEMENTS.md
```

## 3. Database models

Seven new tables bring the schema to 32 tables:

| Model | Stored information |
|---|---|
| `ProfileChangeRequest` | Student, field, old/requested value, reason, pending/approved/rejected state, reviewer, timestamps and note |
| `SubmissionChangeRequest` | Submission/student/teacher, requested fields, original values, reason, decision and completed state |
| `SubmissionRevision` | Immutable values, captured identity, field provenance, revision number, submitter and timestamp |
| `SubmissionReview` | Revision-specific verification/correction/rejection history and feedback |
| `ProfileMergeDecision` | Per-field old/submitted values, selected decision, revision and reviewer |
| `DeadlineExtensionRequest` | Linked requirement/request, teacher, proposed deadline, pending count, reason and HOD review |
| `DeadlineHistory` | Previous/new deadline, actor, reason and approved extension reference |

`Submission` gains `revision_allowed`, `revision_fields`, `revision_count`, and independent `profile_merge_status`. `ProfileVersion` gains `change_source` and `approved_by`. `Notification` gains `kind`. Department → HOD and profile-version actor/approver ORM relationships support the new views.

## 4. Migration

Revision `20260929_workflows` follows `7471d89f7d7a`. It adds tables/columns with compatible defaults and preserves existing accounts, profiles, submissions, values, documents, requirements and requests. The submitted record's latest stored values become a `LEGACY_STORED` snapshot. Existing verified/approved records are marked `LEGACY_REVIEWED`; existing correction requests retain a scoped revision path.

Earlier responses overwritten by the old application cannot be reconstructed. Legacy identity is captured from the records available at migration time, not represented as a historic identity snapshot. Historical automatic merges are not undone. New submissions and revisions capture exact values and identity at submission time. The migration is an online data migration; execute it against the configured database, not with `--sql`.

Back up the database and private uploads before upgrading. A downgrade removes the new workflow history; restoring the backup is the reliable rollback procedure. An unversioned legacy database requires an operator to verify its baseline schema before any Alembic stamping. Do not stamp an unknown database automatically.

## 5. New routes

All mutation routes retain CSRF protection and perform role/ownership checks on the server.

| Route | Methods | Access |
|---|---|---|
| `/student/profile/edit` | GET, POST | Student's permitted fields |
| `/student/profile/change` | GET, POST | Student's sensitive field requests |
| `/student/submissions` | GET | Student's submitted history |
| `/student/submissions/<sub_id>` | GET | Student's own snapshots |
| `/student/submissions/<sub_id>/change` | GET, POST | Student's own revision request |
| `/student/changes` | GET | Student's change history |
| `/change-requests` | GET | Assigned teacher's queue |
| `/profile-changes/<change_id>` | GET, POST | Current class teacher |
| `/submission-changes/<change_id>` | GET, POST | Request owner with current class access |
| `/submissions/<sub_id>/profile-review` | GET, POST | Request owner; verified/approved submission |
| `/deadline-extensions` | GET | Scoped Teacher/HOD queue |
| `/requests/<item_id>/extension` | GET, POST | Request owner |
| `/deadline-extensions/<change_id>` | GET, POST | Teacher can view; owning HOD can decide |
| `/requirements/<item_id>/report` | GET | Authorized Teacher/HOD preview and export |

Existing `/requests/<id>/submit`, `/submissions/<id>`, `/students`, `/students/<id>` and `/reports/<id>` retain their URLs and gain the new behavior. Report GET parameters support search, status, selected columns, sorting and `format=xlsx`, `pdf`, or `csv`.

## 6. Services and behavioral decisions

| Service | Responsibility |
|---|---|
| `profile_service.py` | Field policy, typed validation, direct edits, sensitive approval, version/audit records and stale-value guards |
| `submission_service.py` | First submission lock, database row locking, scoped single-use revision, immutable snapshots and verification history |
| `change_request_service.py` | Student revision requests, duplicate rejection, approval/rejection and permission grant |
| `profile_merge_service.py` | Explicit field selection, conflict decisions, stale baseline protection and separate merge state |
| `pdf_report_service.py` | Paginated landscape PDF with metadata, counts, wrapped text, repeating headers and numbered pages |
| Extended `deadline_service.py` | HOD extension workflow, deadline audit, never-submitted notification targeting and reminders |
| Extended `report_service.py` | Shared filtered preview/export dataset, request and requirement aggregation, Excel dates and formula neutralization |

Direct student fields are phone, address, emergency contact, skills, LinkedIn, portfolio and bio. Name, date of birth, email, gender and blood group require class-teacher approval. Academic identity and assignments are institution managed. Crafted payloads containing restricted fields are rejected.

A first normal submission locks even if an old request has `allow_edit` enabled. Approval grants one revision of named non-institutional fields; saving it consumes permission and creates a new snapshot. Teacher corrections use the same scoped mechanism. Explicit revision permission remains usable after the normal deadline or request closure. A rejection alone never unlocks a response. Reopening a completed requirement returns it to `IN_PROGRESS` for another review.

Verification does not merge profile values. The reviewer can select accepted changes, keep existing values, request clarification, or skip. Unselected values stay in the submitted record. Repeated/stale profile merges are rejected. Merge states include `NOT_REVIEWED`, `APPLIED`, `PARTIALLY_APPLIED`, `SKIPPED`, `NO_ELIGIBLE_FIELDS`, and migration-only `LEGACY_REVIEWED`.

The student directory orders by department, class, register number, name and ID, with department/class navigation and department/class/teacher/account-status/missing-field/completion filters. Academic contacts come from relationships rather than hardcoded names.

Exports use the same selected rows as the preview. Submitted rows use captured response values, including reused profile values saved at submission time. Pending/draft rows show identity without misrepresenting unsent profile fields as collected responses. Requirement totals count request-target rows: a student targeted by two requests appears once in each request's result. Wide PDFs repeat name/register number across column groups and repeat table headings on subsequent pages.

## 7. Notifications and audit

New typed notifications:

- `MASTER_PROFILE_CHANGE_REQUEST`, `PROFILE_CHANGE_APPROVED`, `PROFILE_CHANGE_REJECTED`.
- `STUDENT_SUBMISSION_CHANGE_REQUEST`, `SUBMISSION_CHANGE_APPROVED`, `SUBMISSION_CHANGE_REJECTED`.
- `DEADLINE_EXTENSION_REQUESTED`, `DEADLINE_EXTENSION_APPROVED`, `DEADLINE_EXTENSION_REJECTED`, `DEADLINE_EXTENDED`.

Existing general notifications cover submission/resubmission, verification, clarification and requirement reopening. Approved deadline changes notify only active students who have never submitted; draft-only responses count as pending. Submitted, verified, rejected and correction/revision records are excluded. No email service is introduced.

Profile versions preserve old/new values, timestamp, actor, source, reason, approver and linked data request where applicable. Sources are `STUDENT_DIRECT_EDIT`, `STUDENT_CHANGE_REQUEST`, `TEACHER_UPDATE`, `VERIFIED_FORM_SUBMISSION` and `SYSTEM_UPDATE`. Account identity and class/semester changes are also recorded. Submission/merge/extension reviews and report exports create audit records.

## 8. UI pages

Ten new templates provide Master Profile editing, sensitive-change requests, Submitted Data history/snapshots, submission-change requests, shared review queues, change review, selective merge review, and deadline-extension queue/detail. The existing profile connects Master Profile, academic class/teachers/HOD, Submitted Data, documents, change requests and version history. Completed forms replace submission controls with history and Request a Change actions. Report pages add a PDF download and loading feedback. All use the existing theme, layout, dialogs and responsive components.

## 9. Tests added

`test_student_workflows.py` adds ten tests for direct/sensitive edits, locked submissions, selective merges, revision approvals/rejections, scoped ownership, pending-only deadline notifications, stable directory context, Teacher/HOD Excel/PDF exports and exclusion of legacy draft values from collected data.

`test_acceptance_enhancements.py` adds the complete 28-step Rahul/Arun scenario, stale/conflicting profile merge and clarification, stale sensitive approval and student ID isolation, and teacher/institution version tracking.

`test_workflow_migration.py` adds a legacy-schema upgrade test verifying preservation, snapshot backfill, repeated upgrade safety and zero model/schema differences. The existing workflow test now requires explicit selective profile merging rather than the removed automatic merge.

## 10. Test results

The full suite passed: **29 passed, 6 deprecation warnings in 349.49 seconds**. A final legacy-draft report fix added one regression test; it and the affected Teacher/HOD export integration test passed afterward (**2 passed in 18.87 seconds**), giving **30 distinct tests verified**. The warnings come from the existing Alembic environment's deprecated `get_engine()` compatibility call. Python sources, all 47 Jinja templates, all 16 custom JavaScript modules and all 32 MySQL-dialect table definitions passed static checks. See `VALIDATION.md` for browser coverage and environment limitations. Run with `python -m pytest tests -q`. Tests use isolated SQLite databases; production MySQL and Tesseract require checks in the deployment environment.

## 11. Migration command

Keep the existing `.env` and uploads. Stop the application and back up the configured database. With the application's virtual environment active:

```powershell
python -m pip install -r requirements.txt
python -m flask --app app db upgrade
python -m flask --app app db current
```

The expected migration head is `20260929_workflows`. ReportLab is the new dependency. Do not run `db init`, recreate tables, or reset data. Fresh installations can continue to use `python scripts/setup_database.py` as described in `QUICKSTART.md`.

## 12. Run command

```powershell
python app.py
```

The default local URL is `http://127.0.0.1:5000`. No Node build, external AI key or frontend server is required.
