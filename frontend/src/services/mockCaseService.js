const STORAGE_KEY = "mindbridge_cases";

const sampleCases = [
  {
    id: "MB-1024",
    title: "Hostel maintenance concern",
    category: "hostel_issue",
    description: "A sample concern about hostel maintenance.",
    identityMode: "restricted",
    status: "in_progress",
    createdAt: "2026-10-12T10:00:00.000Z",
  },
  {
    id: "MB-1018",
    title: "Academic guidance request",
    category: "academic_support",
    description: "A sample request for academic guidance.",
    identityMode: "identified",
    status: "under_review",
    createdAt: "2026-10-08T10:00:00.000Z",
  },
];

function readCases() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (saved) {
      const parsed = JSON.parse(saved);

      if (Array.isArray(parsed)) {
        return parsed;
      }
    }
  } catch (error) {
    console.error("Could not read saved cases:", error);
  }

  return sampleCases;
}

export function getCases() {
  return readCases();
}

export function saveCase(caseData) {
  const cases = readCases();

  const newCase = {
    ...caseData,
    id: `MB-${Date.now().toString().slice(-6)}`,
    status: "awaiting_review",
    createdAt: new Date().toISOString(),
  };

  const updatedCases = [newCase, ...cases];

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedCases));
  } catch (error) {
    console.error("Could not save case:", error);
    throw new Error("The case could not be saved in this browser.");
  }

  return newCase;
}

export function updateCaseStatus(caseId, newStatus) {
  const validStatuses = [
    "awaiting_review",
    "under_review",
    "in_progress",
    "resolved",
    "closed",
  ];

  if (!validStatuses.includes(newStatus)) {
    throw new Error("Invalid case status.");
  }

  const cases = readCases();
  const caseIndex = cases.findIndex((item) => item.id === caseId);

  if (caseIndex === -1) {
    throw new Error("This case cannot be updated in the current demo.");
  }

  const currentCase = cases[caseIndex];

  if (currentCase.status === newStatus) {
    return currentCase;
  }

  const statusLabels = {
    awaiting_review: "Awaiting review",
    under_review: "Under review",
    in_progress: "In progress",
    resolved: "Resolved",
    closed: "Closed",
  };

  const now = new Date();

  const updatedCase = {
    ...currentCase,
    status: newStatus,
    updatedAt: now.toISOString(),
    updates: [
      ...(currentCase.updates ?? []),
      {
        date: now.toLocaleDateString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        }),
        title: `Status changed to ${statusLabels[newStatus]}`,
        description:
          "This status update was made in the local frontend demo.",
        type: "current",
      },
    ],
  };

  cases[caseIndex] = updatedCase;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cases));
  } catch (error) {
    throw new Error("The status update could not be saved in this browser.");
  }

  return updatedCase;
}