
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

let csrfToken = null;
let unauthorizedHandler = null;

// Call this after a successful login.
export function setCsrfToken(token) {
  csrfToken = token;
}

// Clear the token after logout.
export function clearCsrfToken() {
  csrfToken = null;
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

export async function apiRequest(endpoint, options = {}) {
  const method = (options.method || "GET").toUpperCase();

  const headers = {
    ...options.headers,
  };

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const unsafeMethods = ["POST", "PUT", "PATCH", "DELETE"];

  if (unsafeMethods.includes(method) && csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method,
      credentials: "include",
      headers,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Unable to reach the MindBridge API. Check that the backend is running and the API URL is configured correctly.",
        { cause: error },
      );
    }
    throw error;
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const errorData = await response.json();
      const detail = errorData.detail;
      message = Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join(" ")
        : detail || message;
    } catch {
      // Keep the default error message if the response isn't JSON.
    }

    if (
      response.status === 401 &&
      !endpoint.endsWith("/auth/login") &&
      !endpoint.endsWith("/auth/register")
    ) {
      unauthorizedHandler?.();
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
