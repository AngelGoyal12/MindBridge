
import {
  apiRequest,
  setCsrfToken,
  clearCsrfToken,
} from "./api";

// Login and store the CSRF token in memory.
export async function refreshCsrfToken() {
  const response = await apiRequest("/api/v1/auth/csrf", {
    method: "POST",
  });

  setCsrfToken(response.csrf_token);
  return response.csrf_token;
}
export async function login(email, password) {
  const response = await apiRequest("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  setCsrfToken(response.csrf_token);

  return response.user;
}

export function registerStudent({
  name,
  email,
  phone,
  password,
  confirmPassword,
}) {
  return apiRequest("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      name,
      email,
      phone,
      password,
      confirm_password: confirmPassword,
    }),
  });
}

export function verifyStudentEmail(email, otp) {
  return apiRequest("/api/v1/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ email, otp }),
  });
}

export function resendStudentVerification(email) {
  return apiRequest("/api/v1/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

// Get the currently authenticated user.
export function getCurrentUser() {
  return apiRequest("/api/v1/auth/me");
}

export function updateMyProfile(profile) {
  return apiRequest("/api/v1/auth/me", {
    method: "PATCH",
    body: JSON.stringify(profile),
  });
}

export function getMyNotifications() {
  return apiRequest("/api/v1/notifications");
}

// Logout and clear the local CSRF token.
export async function logout() {
  try {
    await apiRequest("/api/v1/auth/logout", {
      method: "POST",
    });
  } finally {
    clearCsrfToken();
  }
}