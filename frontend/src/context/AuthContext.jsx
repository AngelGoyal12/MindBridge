import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { AuthContext } from "./authContext";
import {
  clearCsrfToken,
  setUnauthorizedHandler,
} from "../services/api";
import {
  getCurrentUser,
  login,
  logout,
  refreshCsrfToken,
  updateMyProfile,
} from "../services/authService";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const mounted = useRef(false);

  const clearUser = useCallback(() => {
    clearCsrfToken();
    setUser(null);
    setAuthError("");
  }, []);

  const verifySession = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser();
      await refreshCsrfToken();
      if (!mounted.current) return;
      setUser(currentUser);
      setAuthError("");
    } catch (error) {
      if (!mounted.current) return;
      clearUser();
      if (error.status !== 401 && error.status !== 403) {
        setAuthError("Unable to verify your session. Check your connection and retry.");
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [clearUser]);

  const restoreSession = useCallback(() => {
    setLoading(true);
    setAuthError("");
    return verifySession();
  }, [verifySession]);

  useEffect(() => {
    mounted.current = true;
    setUnauthorizedHandler(clearUser);
    Promise.resolve().then(verifySession);
    return () => {
      mounted.current = false;
      setUnauthorizedHandler(null);
    };
  }, [clearUser, verifySession]);

  const signIn = useCallback(async (email, password) => {
    const authenticatedUser = await login(email, password);
    setAuthError("");
    setUser(authenticatedUser);
    return authenticatedUser;
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      clearUser();
    }
  }, [clearUser]);

  const updateProfile = useCallback(async (profile) => {
    const updatedUser = await updateMyProfile(profile);
    setUser(updatedUser);
    return updatedUser;
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      authError,
      restoreSession,
      signIn,
      signOut,
      updateProfile,
    }),
    [user, loading, authError, restoreSession, signIn, signOut, updateProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
