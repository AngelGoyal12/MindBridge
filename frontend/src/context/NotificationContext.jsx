import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useAuth } from "./authContext";
import { NotificationContext } from "./notificationContext";
import {
  getMyNotificationActivity,
  notificationReadStorageKey,
} from "../services/notificationService";

function loadReadState(storageKey) {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey) || "{}");
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  } catch {
    return {};
  }
}

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const userKey = user?.id ?? user?.email ?? "";
  const storageKey = userKey ? notificationReadStorageKey(userKey) : "";
  const [activity, setActivity] = useState({
    ownerKey: "",
    cases: [],
    items: [],
  });
  const [readStates, setReadStates] = useState({});
  const [loadState, setLoadState] = useState({
    ownerKey: "",
    loading: false,
  });
  const [errors, setErrors] = useState({});
  const [readErrors, setReadErrors] = useState({});
  const requestSequence = useRef(0);

  const refresh = useCallback(async () => {
    const requestId = ++requestSequence.current;
    if (user?.role !== "student") return;

    setLoadState({ ownerKey: userKey, loading: true });
    setErrors((current) => ({ ...current, [userKey]: "" }));
    try {
      const result = await getMyNotificationActivity();
      if (requestId === requestSequence.current) {
        setActivity({
          ownerKey: userKey,
          cases: result.cases,
          items: result.notifications,
        });
      }
    } catch (loadError) {
      if (requestId === requestSequence.current) {
        setActivity({ ownerKey: userKey, cases: [], items: [] });
        setErrors((current) => ({
          ...current,
          [userKey]: loadError.message || "Could not load your updates.",
        }));
      }
    } finally {
      if (requestId === requestSequence.current) {
        setLoadState({ ownerKey: userKey, loading: false });
      }
    }
  }, [user?.role, userKey]);

  useEffect(() => {
    if (user?.role === "student") {
      refresh();
    } else {
      requestSequence.current += 1;
    }
  }, [refresh, user?.role]);

  const visibleActivity = useMemo(
    () =>
      activity.ownerKey === userKey
        ? activity
        : { ownerKey: userKey, cases: [], items: [] },
    [activity, userKey],
  );
  const { items, cases } = visibleActivity;
  const readState = useMemo(
    () =>
      storageKey
        ? readStates[storageKey] ?? loadReadState(storageKey)
        : {},
    [readStates, storageKey],
  );
  const loading =
    user?.role === "student" &&
    (loadState.ownerKey === userKey ? loadState.loading : true);
  const error = errors[userKey] || "";
  const readStateError = readErrors[storageKey] || "";
  const unreadCount = items.reduce(
    (count, item) => count + (readState[item.id] ? 0 : 1),
    0,
  );

  const updateReadState = useCallback(
    (nextState) => {
      if (!storageKey) return false;
      try {
        localStorage.setItem(storageKey, JSON.stringify(nextState));
        setReadStates((current) => ({ ...current, [storageKey]: nextState }));
        setReadErrors((current) => ({ ...current, [storageKey]: "" }));
        return true;
      } catch {
        setReadErrors((current) => ({
          ...current,
          [storageKey]: "Read status could not be saved in this browser.",
        }));
        return false;
      }
    },
    [storageKey],
  );

  const markAsRead = useCallback(
    (id) => updateReadState({ ...readState, [id]: true }),
    [readState, updateReadState],
  );

  const markAllAsRead = useCallback(() => {
    const nextState = { ...readState };
    items.forEach((item) => {
      nextState[item.id] = true;
    });
    return updateReadState(nextState);
  }, [items, readState, updateReadState]);

  const value = useMemo(
    () => ({
      items,
      cases,
      unreadCount,
      loading,
      error,
      readStateError,
      refresh,
      markAsRead,
      markAllAsRead,
      isRead: (id) => Boolean(readState[id]),
    }),
    [
      items,
      cases,
      unreadCount,
      loading,
      error,
      readStateError,
      refresh,
      markAsRead,
      markAllAsRead,
      readState,
    ],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}
