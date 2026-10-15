
import { apiRequest } from "./api";

export function getMyCases() {
  return apiRequest("/api/v1/cases");
}

export function getCaseById(caseId) {
  return apiRequest(`/api/v1/cases/${encodeURIComponent(caseId)}`);
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
