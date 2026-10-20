# MindBridge database and authorization

MindBridge uses FastAPI, SQLAlchemy, Alembic, and MySQL. Authorization is
enforced by the backend on each endpoint and case resource; frontend route
guards are only a user-experience layer.

## Roles

| Role | Server-enforced access |
|---|---|
| `student` | Create cases with per-case department disclosure consent, view only owned cases and their student-visible progress, withdraw department consent |
| `coordinator` | View full details and student identity only for assigned cases, manage status/follow-ups/closure, route cases to provisioned departments |
| `admin` | View redacted case briefs and assign cases to coordinators or provisioned departments; no protected identity or contact details |
| `department_staff` | View only cases routed to the provisioned staff member's trusted department; receive only identity fields authorized by active case consent; send private action requests, but cannot change status or close cases |

Public registration always creates a student and ignores role and department
claims. New student registrations remain pending until email OTP verification.
Existing users and privileged accounts created by trusted provisioning remain
compatible; they are not automatically demoted or forced through student OTP.
Student registration stores the selected Department/Course and current
semester separately from the trusted `users.department` staff-routing field.
Students enter their own Department/Course; it is not used for trusted case
routing.
Existing user and pending-verification records remain compatible with null
academic fields; pending OTP verifications issued before this change can still
complete. No existing profile data is overwritten.
Apply the student academic profile Alembic migration
(`a7f19c42d801_add_student_academic_profile_fields`) manually as part of a
planned deployment. The migration adds nullable columns to `users` and
`pending_email_verifications`; it does not rewrite existing rows.
Create coordinator, admin, and department staff accounts from the backend using
an authorized operator account:

```powershell
cd MindBridge\backend
python provision_user.py --name "Coordinator Name" --email coordinator@example.edu --role coordinator
python provision_user.py --name "Department Staff" --email staff@example.edu --role department_staff --department "Counselling"
python provision_user.py --name "Administrator" --email admin@example.edu --role admin
```

The script prompts for the password, hashes it, and only creates new privileged
accounts. Provisioning passwords must be 12-128 characters and include an
uppercase letter, lowercase letter, digit, and special character. Admins and
coordinators must not be given a department assignment; department staff
require one. Department names are trusted administrative input to this
provisioning command. New staff accounts reuse the case-insensitive canonical
department name already assigned to provisioned staff, when one exists.
Database access and the provisioning host are therefore part of the trusted
provisioning boundary; public registration cannot create staff accounts or
choose a department.

All roles use the shared session-based login and CSRF-protected logout. The
frontend chooses a role dashboard using the user returned by the authenticated
backend; backend role checks remain authoritative. Only the assigned
Coordinator can change case status, add student-visible follow-ups, or close a
case. Closing requires a student-visible outcome. Department action requests
are private to the assigned Coordinator and do not change case status until the
Coordinator acts.

## Production deployment security

Production must be served over HTTPS at both the frontend and API entry points.
Terminate TLS and redirect HTTP to HTTPS at the trusted reverse proxy or
hosting platform; the FastAPI application does not perform that redirect.
Set these backend environment values explicitly:

```text
APP_ENV=production
SESSION_COOKIE_SECURE=true
FRONTEND_ORIGINS=https://mindbridge.example.edu
```

`FRONTEND_ORIGINS` must contain the exact browser origin(s), comma-separated
when there is more than one; do not use a wildcard. Include scheme and port
when non-default, and do not include paths. The backend checks the browser
Origin when refreshing CSRF tokens and uses the same allowlist for
credentialed CORS. Keep the frontend and API same-site (preferably same-origin
behind a reverse proxy) so the session cookie's `SameSite=Lax` policy works
without weakening it. Cross-site frontend/API hosting requires an explicit
security review and is not supported by changing CORS alone.

Session cookies are `HttpOnly`, `SameSite=Lax`, scoped to `/`, and are marked
`Secure` only when `SESSION_COOKIE_SECURE=true`. Production startup refuses to
run unless `APP_ENV=production` is paired with that secure-cookie setting.
The backend also emits `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, a restrictive Referrer-Policy and Permissions-Policy,
and a content security policy. HSTS (`max-age=31536000`) is emitted by the API
only when both production settings are active; configure the HTTPS redirect
and HSTS at the frontend host/reverse proxy as well. Do not enable HSTS until
the domain is reliably HTTPS-only.

The production frontend build emits a CSP meta policy that permits the bundled
same-origin scripts, the existing inline style attributes, the Google Fonts
CSS/font origins used by the app, and same-origin API calls. If the frontend
calls a separately hosted API, set `VITE_API_BASE_URL` to that API's HTTPS
origin at build time; the Vite build adds exactly that origin to `connect-src`
and rejects non-HTTPS external API origins. The static frontend host must also
send equivalent CSP response headers including `frame-ancestors 'none'`
(which browsers ignore in a meta policy), plus `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff`, Referrer-Policy, Permissions-Policy, and
HSTS after TLS is configured. Review the deployed page's CSP console reports,
font loading, login/session restoration, API requests, and CSRF-protected
updates after every frontend origin or API-host change. API CSP headers secure
API responses; they do not replace the CSP on the HTML document.
After building, run `npm run test:security` from `frontend` to check that the
generated CSP precedes resource tags and permits the actual bundled assets,
font import, and configured API origin. This build check does not replace
browser testing through the production reverse proxy.

Login throttling is in-process. Multi-worker deployments must enforce
equivalent per-account and per-client limits at the trusted gateway or use a
shared rate-limit store. Forwarded client IP headers must be trusted only from
known proxy hops.

## Controlled manual authentication test accounts

Create manual test accounts only in an isolated, non-production database after
confirming `DB_HOST` and `DB_NAME` in the local ignored `.env`. Never copy
production data, passwords, session cookies, or OTP secrets into test
environments. Run the existing provisioning command from `backend`; it prompts
for the password twice without echoing it, validates the password policy, and
stores only the password hash. Generate a unique password in a trusted password
manager for each account; do not put it on the command line or in this
documentation.

Example commands (replace the `.invalid` email addresses and department with
controlled test identities and departments):

```powershell
python provision_user.py --name "Test Administrator" --email test-admin@example.invalid --role admin
python provision_user.py --name "Test Coordinator" --email test-coordinator@example.invalid --role coordinator
python provision_user.py --name "Test Department Staff" --email test-staff@example.invalid --role department_staff --department "Test Support"
```

An existing department staff account establishes the canonical department for
subsequent staff accounts. For local student tests, use the public registration
and OTP flow with a local SMTP catcher; never insert privileged roles through
public registration. Remove manual test accounts through the approved
non-production database maintenance process when no longer needed. The
automated API tests instead create ephemeral users and isolated in-memory
SQLite databases; they are not reusable login accounts.

## Student email OTP configuration

Copy `backend\.env.example` to a local, untracked `backend\.env`. Registration
always requires a syntactically valid email address ending in `.edu.in`.
Optionally set `COLLEGE_EMAIL_DOMAINS` to a comma-separated list of exact
institution domains to restrict registration; every configured domain must
end in `.edu.in`. When the list is blank, all valid `.edu.in` addresses are
accepted. The legacy `COLLEGE_EMAIL_DOMAIN` variable remains supported for a
single institution domain. Matching is case-insensitive and email addresses
are normalized before duplicate checks.

Set `OTP_HASH_SECRET` to a unique random value of at least 32 characters and
keep it outside source control. OTP hashes are keyed with this secret;
changing it invalidates outstanding verification codes.

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`, and,
when needed, `SMTP_USERNAME` / `SMTP_PASSWORD`. For safe local testing, use a
local SMTP catcher such as MailHog with its SMTP listener and web inbox. The
API never returns or logs the code. If delivery fails, the pending account
remains unverified and may request a resend after cooldown.

Passwords must be at least 12 characters and include uppercase, lowercase,
numeric, and special characters. They are hashed before storage. Indian mobile
numbers are normalized to `+91` plus the ten-digit number and retained during
profile updates unless a new number is supplied.

New codes expire after five minutes by default, permit five verification
attempts, and can be resent no more than five times with a 60-second cooldown.
The pending verification table stores the name, normalized phone and email,
password hash, keyed OTP hash, expiry, and counters. A successful OTP
verification creates a student user and consumes the pending record.
Resend/registration request limits are process-local; multi-worker deployments
should also enforce email/API limits at a trusted gateway. Existing privileged
accounts provisioned by `provision_user.py` do not use public registration OTP.

## Coordinator assignment and invitations

Admins assign each case by entering a coordinator email. An existing account
is eligible only when its server-side role is `coordinator`; the email field
cannot promote a student or create a privileged account. Existing coordinators
must be provisioned through the trusted backend process. A new email receives a
single-use invitation link and can create a coordinator account only by setting
its own password through that link. The new account is assigned only after
successful activation. Invitation tokens are generated securely and only
their SHA-256 hashes are stored. Reassignment changes the case's
`assigned_coordinator_id`, immediately removing the previous coordinator's
access. Assignment alone never grants access to protected identity or report
text.

The invitation email contains only the case reference and category, plus the
login/dashboard or activation link. It never contains a student identity or
case description. Set `FRONTEND_URL` to the exact frontend origin included in
these links (for example `http://localhost:5173` locally). If unset, the first
configured `FRONTEND_ORIGINS` entry is used, then the local Vite origin.
`COORDINATOR_INVITATION_EXPIRATION_HOURS` controls token lifetime (1-168 hours;
default 72). Existing SMTP variables listed above are required. If email
delivery fails, the API reports failure and cleans up the pending invitation;
it does not claim that the assignment or invitation succeeded.

Revision `9ac0f3e8b241` adds the `coordinator_invitations` table for hashed
tokens, expiry, acceptance, and revocation. It is an additive migration
parented to `7f4a2c9e1d30`; it is not applied automatically. Review the
database's current Alembic revision before applying it through the normal
authorized migration procedure. The existing case assignment field is
reused; no case or user columns are added.

## Department routing

The existing `cases.department` column is the routing assignment; no additional
schema migration is required. The authorized department list is derived from
the distinct department names on securely provisioned `department_staff`
accounts. Admins and coordinators can retrieve that list from
`GET /api/v1/departments`. The application does not define a category-to-
department mapping; the assigned Coordinator selects the provisioned team
based on the category and support needs. The backend canonicalizes the
department name and rejects values without a provisioned staff association.

Admins retain routing permission. Coordinators can route only cases whose
`assigned_coordinator_id` matches their authenticated account, and the
operation requires the session's CSRF token. Routing updates only
`cases.department`; it does not change the Coordinator assignment. Department
case queries compare the routed department to the authenticated staff member's
server-provisioned department, so rerouting immediately removes the case from
the previous team's list. Department responses contain case details and expose
name/email/phone only while the case's recorded consent is active. Staff can
send private messages or closure requests to the currently assigned
Coordinator; they cannot change status or close cases.

Local sequence:

1. Configure a local-only database and the variables above.
2. Apply migrations using the project's normal authorized local procedure:
   `python -m alembic upgrade head`.
3. Start the API from `backend` with `python -m uvicorn main:app --reload`.
4. Start Vite from `frontend` with `npm run dev`.
5. Register with a valid `.edu.in` college address and Indian mobile number,
   open the local mail-catcher inbox, enter the code at `/verify-email`, then
   sign in. Accounts cannot log in before verification.
6. Provision privileged local accounts with `provision_user.py` using a local
   database. Department staff must receive a trusted department name.

The Department Portal currently provides existing staff sign-in and explains
the authorized provisioning request process. It intentionally does not create
accounts or department requests; Person 4's Department module must provide an
approved request workflow before self-service access requests can be submitted.

For local HTTP development, set `SESSION_COOKIE_SECURE=false`; production must
set `APP_ENV=production`, use HTTPS, and set `SESSION_COOKIE_SECURE=true`.
The application refuses to start in production mode unless secure cookies are
explicitly enabled. Sessions are stored as token hashes,
expire after eight hours, can be revoked on logout, and require a per-session
CSRF token for state-changing requests. Set `FRONTEND_ORIGINS` to a
comma-separated list of exact trusted origins in production, for example
`https://mindbridge.example.edu`. Wildcards and empty origin lists are rejected.
Login attempts are throttled per account and per IP for a 15-minute window
(five failures per account and 20 per IP). This limiter is process-local;
multi-worker deployments must also configure equivalent throttling at the
trusted reverse proxy or API gateway.

Every case remains linked to its student account internally. At submission the
student chooses Anonymous (the default), Restricted (individual name, email,
phone, and available student-department fields), or Full disclosure. The
existing `case_consents.scope` text stores the level and selected fields;
withdrawal immediately removes profile identity/contact fields from every
department case response. Existing Boolean-era granted records retain their
original name/email/phone scope and are not widened to include student
department. Coordinators assigned to a case can see the full case and student
identity regardless of department consent, and can see the recorded consent
choice. Admin case briefs include category, title, a redacted summary,
submission date, and status, but no student identity/contact fields. No
urgency field currently exists in the case schema. Department-to-Coordinator
action requests are private and are never included in student case progress.
Student progress includes submission, assignment, routing, status, follow-up,
and closure events and is returned only to the case owner.

## Existing schema

The current SQLAlchemy models already include the fields needed for RBAC:

- `users`: account role, phone number, and the trusted department assignment
  for staff.
- `pending_email_verifications`: temporary student registration information,
  password hash, keyed OTP hash, expiry, and resend/verification counters.
- `coordinator_invitations`: case-specific invitation email, token hash,
  inviter, expiry, and accepted/revoked timestamps.
- `user_sessions`: hashed session token, CSRF token hash, expiration, and
  revocation timestamp.
- `cases`: student owner, assigned coordinator, trusted department routing,
  case content, status, and identity mode.
- `case_consents`: case owner/grantor, recipient, purpose, scope, grant,
  withdrawal, and timestamps.
- `case_disclosure_audits`: actor, recipient, purpose, decision, reason, and
  timestamp.
- `case_progress_updates`: student-visible status, routing, follow-up, and
  closure outcome updates, kept separate from staff-only requests.
- `department_action_requests`: department messages addressed to the
  Coordinator assigned to that case, with an open/handled/dismissed state.

Alembic revision `3d6b2f9a8c41` additively creates the progress and action
request tables; no existing columns or records are altered. Do not apply this
migration automatically. An operator must review the migration head and apply
it through the normal authorized deployment procedure when ready.

## Safe tests and migration inspection

Backend test collection sets `MINDBRIDGE_TESTING=1` before importing the
application. In that mode the application engine is always in-memory SQLite;
each API test also overrides its database dependency with its own in-memory
SQLite fixture. Tests must not use `test_db.py`, which deliberately connects to
configured MySQL as a connectivity check.

Install backend test dependencies and run the full isolated suite from the
backend directory:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

`test_db.py` does not connect when imported or collected by pytest. Running it
directly is an explicit connectivity check against the configured database and
must not be part of test automation. Inspect the migration graph without
applying changes:

```powershell
$env:MINDBRIDGE_TESTING = "1"
python -m alembic heads
python -m alembic history
Remove-Item Env:MINDBRIDGE_TESTING
```

## Protected API surfaces

| Method | Endpoint | Authorization |
|---|---|---|
| GET | `/api/v1/auth/me` | Authenticated user |
| PATCH | `/api/v1/auth/me` | Authenticated user; name only, with CSRF |
| POST | `/api/v1/cases` | Student |
| GET | `/api/v1/cases`, `/api/v1/cases/count`, `/api/v1/cases/{id}` | Student, owned records only |
| GET/PATCH | `/api/v1/coordinator/cases...` | Coordinator, assigned records only; status updates limited to in-review, in-progress, or closed |
| POST | `/api/v1/coordinator/cases/{id}/updates` | Assigned Coordinator; student-visible follow-up, CSRF required |
| GET/PATCH | `/api/v1/coordinator/action-requests...` | Assigned Coordinator only; CSRF required for decisions |
| GET | `/api/v1/admin/cases`, `/api/v1/admin/coordinators` | Admin, redacted case information |
| PATCH | `/api/v1/cases/{id}/assign` | Admin, coordinator accounts or case-specific invitations; CSRF required |
| POST | `/api/v1/coordinator-invitations/accept` | Public single-use token activation; creates only a coordinator |
| GET | `/api/v1/departments` | Admin or Coordinator; departments of provisioned staff only |
| PATCH | `/api/v1/cases/{id}/department` | Admin or the assigned Coordinator, provisioned departments only; CSRF required |
| GET/POST | `/api/v1/department/cases...` | Department staff, routed department only; contact data is consent-gated; action request POST requires CSRF |
| GET | `/api/v1/notifications` | Student, own cases only |

The `/api/v1/cases/{id}` family also includes student-only identity preference,
consent withdrawal, and disclosure-audit operations. Department identity
consent is recorded at case submission; assigned Coordinators may access case
identity, while Department responses include only the selected fields while
consent is active. Unauthorized requests are rejected with `401` when
unauthenticated and `403` when the authenticated role lacks permission. A
resource outside the caller's data scope returns `404` where revealing its
existence would disclose information.
