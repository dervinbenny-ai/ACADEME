# Academe — UI delivery

The September 24 interface is retained and extended by the September 29 workflow release. New profile, revision, selective-merge, and deadline-approval screens use the same shared shell, confirmation dialogs, tokens, and responsive styles. The workflow release includes an additive database migration; no frontend build framework is introduced.

## Project tree

```text
academe/
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── .env.example
├── QUICKSTART.md
├── README.md
├── UI_DELIVERY.md
├── VALIDATION.md
├── models/                  32-table relational schema
├── routes/
│   ├── auth.py              Login, password, recovery
│   ├── management.py        Institution and user management
│   ├── collection.py        Requirements, requests, submissions
│   ├── core.py              Role dashboards and reports
│   ├── extras.py            Documents, messages, activities, local AI
│   ├── workspace.py         Scoped search and notification API
│   └── student_workflows.py Profile, revision and extension approvals
├── services/                Authorization and workflow services
├── ai/                      Local recommendations, search, analytics
├── migrations/              Initial and workflow migrations
├── scripts/                 Setup, Super Admin, deadline reminders
├── tests/                   30 integration/security/migration tests
├── templates/
│   ├── base.html            Shared shell, sidebar, topbar, dialogs
│   ├── portal.html          Public home and portal selector
│   ├── login.html           Three role portals
│   ├── dashboard.html       Four role dashboards
│   ├── builder.html         Library / canvas / settings & suggestions
│   ├── profile.html         Profile tabs and completion ring
│   ├── review.html          Submission verification
│   ├── profile_merge.html   Separate selective profile update review
│   ├── submission_snapshot.html Immutable submitted revisions
│   ├── change_review.html   Profile/submission change decisions
│   ├── deadline_extension.html Teacher request / HOD approval
│   ├── macros.html          Shared fields, badges, empty states, paging
│   ├── components/          Avatar, stat card, deadline, SVG illustration
│   └── ...                  All management and collection screens
└── static/
    ├── css/
    │   ├── app.css          Stylesheet entry point
    │   ├── variables.css    Design tokens and role accents
    │   ├── base.css         Typography, focus, surface defaults
    │   ├── layout.css       Sidebar, topbar, page layout
    │   ├── dashboard.css    Dashboards, login, landing page
    │   ├── components.css  Cards, dialogs, badges, profile, review
    │   ├── forms.css        Inputs, builder, upload surfaces
    │   ├── tables.css       Tables, filters, sorting, report chips
    │   ├── animations.css  Motion and reduced-motion rules
    │   ├── themes.css       Dark theme
    │   ├── responsive.css  Tablet and mobile behavior
    │   ├── workflows.css    Profile, revisions, approvals and class directory
    │   └── legacy.css       Baseline coverage for supporting screens
    ├── js/
    │   ├── app.js           Shared DOM helpers, toasts, avatars
    │   ├── theme.js         Saved light/dark appearance
    │   ├── sidebar.js       Collapse, offcanvas, keyboard handling
    │   ├── cursor-effects.js
    │   ├── animations.js
    │   ├── counters.js
    │   ├── dashboard.js     Greeting, deadlines, profile tabs
    │   ├── charts.js
    │   ├── analytics.js
    │   ├── form-builder.js
    │   ├── forms.js
    │   ├── tables.js
    │   ├── modals.js
    │   ├── notifications.js
    │   ├── uploads.js
    │   └── search.js
    ├── images/              SVG favicon
    └── vendor/              Bootstrap 5, Icons, Chart.js, Inter, licenses
```

## UI files and screens

The shell, landing page, logins, dashboards, builder, profile, review, and error templates are redesigned. Shared styling also covers departments, class assignment, staff management, student management, requirements, collection requests, submission forms, document review, reports, analytics, notifications, messages, activities, settings, audit, account recovery, passwords, and the student assistant.

Supporting templates gain sortable tables, mobile record cards, asynchronous filters, report column chips, and the requirement timeline where relevant. Existing form actions, field names, CSRF fields, role gates, and document access checks are retained.

Reusable components are in `templates/components/` and `templates/macros.html`. The compact `legacy.css` layer retains baseline styles for all supporting screens; the focused modules define the final theme and behavior.

## JavaScript interactions

- Persistent light/dark theme; system appearance is used until a choice is saved.
- 260px desktop sidebar, 80px collapsed sidebar, mobile drawer, Escape handling, and focus containment.
- Ctrl/Cmd+K command search with debouncing, cancellation, role-scoped ORM queries, and keyboard navigation.
- Server-backed live table search and status chips. Sorting affects the displayed page and is labeled accordingly.
- Notification dropdown, unread counts, mark one/all read, visible-page polling, and toasts for newly observed unread notifications.
- Actual-data dashboard counters, local-time greeting, date display, and deadline countdowns. Backend deadlines remain UTC.
- Builder library search, categorized fields, click to add, drag reorder, keyboard move buttons, duplication, removal, required flags, labels, field keys, reuse policies, options, numeric validation, and a form preview.
- Local field suggestions, individual acceptance, Add all, and regeneration. The UI explicitly identifies the local provider.
- Student profile tabs with arrow/Home/End keyboard navigation, verified field categories, and a real completion ring.
- Password visibility, native validation plus inline feedback, character counts, and submit feedback without dropping button name/value payloads.
- Native confirmation dialogs for consequential actions, including cancellation and preservation of the intended submitter.
- File drop zones, chosen file details, removal, real upload byte progress, processing state, and network failure recovery.
- Report column chips and asynchronous Excel/PDF/CSV download with explicit success/failure feedback.

## Motion

- Soft eased cursor glow using `requestAnimationFrame`.
- Subtle card spotlight and approximately 2-degree tilt on the insight card.
- Up to 3px magnetic movement on selected calls to action.
- Click-origin ripple feedback.
- 200–350ms content/dialog entrances and short card insertion transitions.
- One-time number animations, chart entrance, progress transitions, and intersection-based landing section reveals.
- Slow decorative illustration movement and skeleton shimmer while data is requested.

Reduced-motion preferences disable decorative movement, transitions, counters, and chart animation. Pointer effects require a fine pointer, hover capability, and a desktop-width viewport. No normal pointer replacement is used.

## Responsive and accessibility improvements

- Deliberate mobile navigation with a scrim, focus handling, and an accessible close action.
- Two-column mobile statistics, stacked dashboard panels, responsive hero art, and sticky builder actions.
- Directory/request rows become labeled record cards. Wide reports retain contained horizontal scrolling.
- Builder library, canvas, and settings stack on smaller screens; move buttons support touch and keyboard ordering.
- Touch-sized primary controls, visible focus, labeled icon actions, skip link, semantic forms, native dialogs, status announcements, and text labels alongside status colors.
- No placeholder trends or invented dashboard counts. Empty datasets display an empty state.

## Run and dependencies

After the one-time environment/database setup in `QUICKSTART.md`:

```powershell
python app.py
```

ReportLab is the one new Python dependency for PDF reports. No new package is needed for UI effects. No React, npm, external animation library, paid AI API, or asset CDN is required.

## Practical boundaries

Table sorting is local to the displayed result page; server filters still search the authorized dataset. Notifications poll once per minute while the page is visible. AI suggestions and insights use the included local rule engine. Tesseract is optional and external. Test records are isolated outside this deliverable. See `VALIDATION.md` for verification details and MySQL testing limits.

## September 29 workflow screens

Students can edit permitted Master Profile fields, request approval for sensitive changes, read immutable submitted revisions, and request a single field-scoped revision. The profile connects academic contacts, documents, requests and history. Teachers get a shared change-request queue and an explicit selective profile-update screen after verification. Teachers request linked deadline extensions; HOD reviews them with pending counts and an audit trail. The HOD directory provides department/class navigation, stable ordering, and retained filters. Request and requirement report previews offer the same selected dataset in Excel, PDF and CSV.
