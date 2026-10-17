# MindBridge frontend

MindBridge is a React + Vite interface for student support and case
coordination. It uses the FastAPI backend as the authority for authentication,
role checks, case access, routing, consent, and notifications.

## Run locally

Start the backend from `MindBridge\backend` first. For local HTTP development,
configure `SESSION_COOKIE_SECURE=false` in the backend environment. Then run:

```powershell
cd MindBridge\frontend
npm install
npm run dev
```

In development, requests to `/api` are proxied to
`http://127.0.0.1:8000` by Vite, avoiding browser cross-origin configuration.
Set `VITE_API_PROXY_TARGET` when the development backend runs elsewhere. For a
separately hosted API, set `VITE_API_BASE_URL` to its origin and configure the
backend `FRONTEND_ORIGINS` to include the exact frontend origin.

The public home page and navigation include a direct Create account link.
Opening the student portal still follows the existing `/dashboard` route and
login/session guards.

## Validation

```powershell
npm run lint
npm run build
```

## Authentication and workspaces

The frontend restores the current session through `/api/v1/auth/me`, refreshes
its CSRF token, and centralizes authenticated-user state. Dashboards are
selected by the server-returned role. Student pages are limited to students;
coordinator, administrator, and department workspaces call role-scoped APIs.
All API calls include the session cookie, and state-changing calls include the
CSRF token. Frontend guards do not replace backend authorization.

Public registration creates student accounts only. Privileged accounts are
created through the backend's trusted provisioning command. Department staff
must have a trusted department assignment before they can log in or access
routed cases.

New student registrations require a verification code delivered to the exact
domain configured by the institution as `COLLEGE_EMAIL_DOMAIN`. Configure
SMTP and the OTP hash secret in the backend's local `.env`; use a local SMTP
catcher such as MailHog when developing. The verification API does not reveal
the code. See `backend/docs/SCHEMA.md` for required settings and the local
registration and verification sequence.

The Department Portal entry is available at `/department-portal`. It reuses
the normal login flow and provides administrator-provisioned access guidance;
it does not offer public staff account creation or a self-service access
request until the Department module includes an authorized approval workflow.

Set `APP_ENV=production` and `SESSION_COOKIE_SECURE=true` for HTTPS production
deployments; the backend rejects production startup without the secure-cookie
setting. Login throttling is enforced per backend process; deployments with
multiple workers should also configure rate limiting at the trusted proxy or
API gateway.

The privacy-preference page saves its default to browser local storage only;
it is not synchronized across devices. Each submitted case stores its own
identity mode on the server. Cases remain linked to their student account;
coordinator routine responses omit free text and identity, and identity
disclosure requires active, purpose- and scope-specific consent. The
`anonymous` case mode blocks the identity disclosure endpoint but does not
guarantee anonymity or remove identifying information from student-written
text.
