# Team workflow update

## Apply
```
cd backend
alembic upgrade head            # new migration f7c3d9e2b615
MINDBRIDGE_TESTING=1 pytest -q  # includes the new test_team_workflow.py
cd ../frontend
npm install && npm run lint && npm run build
```

## What changed

**Role labels (display only).** admin -> Main Coordinator, coordinator ->
Department Coordinator, department_staff -> Department Staff. Stored role
values, login, permissions and the email invitation flow are untouched.

**Main Coordinator can send tasks to departments.** New admin task endpoints;
the admin dashboard shows a task panel on each redacted case brief.

**Staff-level assignment and claiming.** The Department Coordinator (or Main
Coordinator) hands a task to one staff member, or leaves it in the department
pool where any staff member can claim it. Staff see only their own tasks plus
the unclaimed pool.

**Messaging.** Staff -> Main Coordinator / coordinators / other departments;
coordinators -> Main Coordinator / departments; Main Coordinator ->
coordinators / departments. Inbox, sent, unread count, reply. Student identity
is redacted per reader.

**Dashboard failure fix.** The dashboard used to load everything in one
Promise.all, so any single failed request blanked the whole page. The case list
is now loaded first and the rest is optional: a failure shows a notice with a
Retry button and the workspace still opens.

## Files
Backend: `main.py`, `models.py`, `alembic/versions/f7c3d9e2b615_*.py`,
`test_team_workflow.py`, `docs/SCHEMA.md`.
Frontend: `components/MessageCenter.jsx` (new), `CaseTaskManager.jsx`,
`DepartmentTaskDashboard.jsx`, `pages/RoleDashboard.jsx`,
`services/caseService.js`, `services/casePresentation.js`, `App.jsx`, `App.css`.
