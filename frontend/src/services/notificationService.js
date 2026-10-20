import { getMyCases } from "./caseService";

export async function getMyNotificationActivity() {
  const cases = await getMyCases();

  const notifications = cases
    .flatMap((caseItem) =>
      (Array.isArray(caseItem.progress_updates)
        ? caseItem.progress_updates
        : []
      ).map((update) => ({
        id: `${caseItem.id}-${update.id}`,
        caseId: caseItem.id,
        caseTitle: caseItem.title,
        title: update.title,
        message: update.message,
        type: update.type,
        createdAt: update.created_at,
      })),
    )
    .sort(
      (left, right) =>
        new Date(right.createdAt || 0).getTime() -
        new Date(left.createdAt || 0).getTime(),
    );
  return { cases, notifications };
}

export function notificationReadStorageKey(userKey) {
  return `mindbridge_notifications_read:${userKey}`;
}
