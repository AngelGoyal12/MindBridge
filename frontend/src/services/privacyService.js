const STORAGE_KEY = "mindbridge_identity_preference";

const VALID_PREFERENCES = ["identified", "restricted", "anonymous"];

export function getIdentityPreference() {
  try {
    const savedPreference = localStorage.getItem(STORAGE_KEY);

    if (VALID_PREFERENCES.includes(savedPreference)) {
      return savedPreference;
    }
  } catch (error) {
    console.error("Could not read identity preference:", error);
  }

  return "restricted";
}

export function saveIdentityPreference(preference) {
  if (!VALID_PREFERENCES.includes(preference)) {
    throw new Error("Please select a valid identity-sharing preference.");
  }

  try {
    localStorage.setItem(STORAGE_KEY, preference);
  } catch (error) {
    console.error("Could not save identity preference:", error);
    throw new Error("Could not save your preference in this browser.", {
      cause: error,
    });
  }

  return preference;
}