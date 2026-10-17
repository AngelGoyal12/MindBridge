
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

export function updateCoordinatorCaseStatus(caseId, status) {
  return apiRequest(
    `/api/v1/coordinator/cases/${encodeURIComponent(caseId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    },
  );
}

export function requestCoordinatorIdentityDisclosure(caseId, consentDetails) {
  return apiRequest(
    `/api/v1/coordinator/cases/${encodeURIComponent(caseId)}/identity-disclosure`,
    {
      method: "POST",
      body: JSON.stringify(consentDetails),
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
