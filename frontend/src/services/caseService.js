
import { apiRequest } from "./api";

export function getMyCases() {
  return apiRequest("/api/v1/cases");
}

export function getCaseById(caseId) {
  return apiRequest(`/api/v1/cases/${encodeURIComponent(caseId)}`);
}

export function updateCaseIdentity(caseId, identityMode) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/identity`,
    {
      method: "PATCH",
      body: JSON.stringify({ identity_mode: identityMode }),
    },
  );
}

export function getCaseConsents(caseId) {
  return apiRequest(`/api/v1/cases/${encodeURIComponent(caseId)}/consent`);
}

export function grantCaseConsent(caseId, consent) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/consent`,
    {
      method: "POST",
      body: JSON.stringify(consent),
    },
  );
}

export function withdrawCaseConsent(caseId, consentId) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/consent/${encodeURIComponent(consentId)}/withdraw`,
    { method: "PATCH" },
  );
}

export function getCaseDisclosureAudit(caseId) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/disclosure-audit`,
  );
}

export function createCase(caseData) {
  return apiRequest("/api/v1/cases", {
    method: "POST",
    body: JSON.stringify(caseData),
  });
}

export function updateCase(caseId, updates) {
  return apiRequest(`/api/v1/cases/${encodeURIComponent(caseId)}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export function getCoordinatorCases() {
  return apiRequest("/api/v1/coordinator/cases");
}

export function updateCoordinatorCaseStatus(caseId, status, closureOutcome) {
  return apiRequest(
    `/api/v1/coordinator/cases/${encodeURIComponent(caseId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status,
        ...(closureOutcome ? { closure_outcome: closureOutcome } : {}),
      }),
    },
  );
}

export function createCoordinatorProgressUpdate(caseId, update) {
  return apiRequest(
    `/api/v1/coordinator/cases/${encodeURIComponent(caseId)}/updates`,
    {
      method: "POST",
      body: JSON.stringify(update),
    },
  );
}

export function getCoordinatorActionRequests() {
  return apiRequest("/api/v1/coordinator/action-requests");
}

export function decideCoordinatorActionRequest(requestId, status) {
  return apiRequest(
    `/api/v1/coordinator/action-requests/${encodeURIComponent(requestId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    },
  );
}

export function getAdminCases() {
  return apiRequest("/api/v1/admin/cases");
}

export function getCoordinators() {
  return apiRequest("/api/v1/admin/coordinators");
}

export function assignCoordinator(caseId, coordinatorEmail) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/assign`,
    {
      method: "PATCH",
      body: JSON.stringify({ coordinator_email: coordinatorEmail }),
    },
  );
}

export function acceptCoordinatorInvitation(invitation) {
  return apiRequest("/api/v1/coordinator-invitations/accept", {
    method: "POST",
    body: JSON.stringify(invitation),
  });
}

export function assignDepartment(caseId, department) {
  return apiRequest(
    `/api/v1/cases/${encodeURIComponent(caseId)}/department`,
    {
      method: "PATCH",
      body: JSON.stringify({ department }),
    },
  );
}

export function getAuthorizedDepartments() {
  return apiRequest("/api/v1/departments");
}

export function getDepartmentCases() {
  return apiRequest("/api/v1/department/cases");
}

export function createDepartmentActionRequest(caseId, request) {
  return apiRequest(
    `/api/v1/department/cases/${encodeURIComponent(caseId)}/action-requests`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}
