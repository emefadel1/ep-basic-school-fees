import React from "react";
import { clearStoredSession, getStoredSession, persistSession } from "@/lib/auth";

const AuthContext = React.createContext(undefined as any);

const LOGIN_URL = "/api/v1/auth/login/";
const LOGOUT_URL = "/api/v1/auth/logout/";

export function AuthProvider(props: any) {
  const [session, setSession] = React.useState({ accessToken: null, refreshToken: null, user: null });
  const [booting, setBooting] = React.useState(true);
  const [submitting, setSubmitting] = React.useState(false);

  const refreshFromStorage = React.useCallback(function refreshFromStorage() {
    setSession(getStoredSession());
  }, []);

  React.useEffect(function bootstrap() {
    setSession(getStoredSession());
    setBooting(false);
  }, []);

  React.useEffect(function bindStorage() {
    if (typeof window === "undefined") {
      return undefined;
    }
    function onStorage() {
      refreshFromStorage();
    }
    window.addEventListener("storage", onStorage);
    return function cleanup() {
      window.removeEventListener("storage", onStorage);
    };
  }, [refreshFromStorage]);

  const login = React.useCallback(async function login(credentials: any) {
    setSubmitting(true);
    try {
      const response = await fetch(LOGIN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(credentials),
      });
      let payload: any = {};
      try {
        payload = await response.json();
      } catch (error) {
        payload = { success: false, error: { message: "Unable to sign in." } };
      }
      if (response.ok === false) {
        throw payload;
      }
      if (typeof payload.access !== "string") {
        throw new Error("Login response did not include an access token.");
      }
      if (typeof payload.refresh !== "string") {
        throw new Error("Login response did not include a refresh token.");
      }
      if (payload.user === undefined) {
        throw new Error("Login response did not include a user payload.");
      }
      const stored = persistSession(payload.access, payload.refresh, payload.user);
      setSession(stored);
      return stored.user;
    } finally {
      setSubmitting(false);
    }
  }, []);

  const logout = React.useCallback(async function logout() {
    const current = getStoredSession();
    setSubmitting(true);
    try {
      if (current.refreshToken !== null) {
        if (current.accessToken !== null) {
          await fetch(LOGOUT_URL, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer " + current.accessToken,
            },
            credentials: "include",
            body: JSON.stringify({ refresh: current.refreshToken }),
          });
        }
      }
    } catch (error) {
    }
    clearStoredSession();
    setSession(getStoredSession());
    setSubmitting(false);
  }, []);

  const isAuthenticated = session.accessToken !== null ? session.user !== null : false;
  const isLoading = booting === true ? true : submitting;

  const hasAnyRole = React.useCallback(function hasAnyRole(roles: any) {
    if (roles === undefined) {
      return true;
    }
    if (Array.isArray(roles) === false) {
      return true;
    }
    if (roles.length === 0) {
      return true;
    }
    if (session.user === null) {
      return false;
    }
    return roles.indexOf(session.user.role) !== -1;
  }, [session.user]);

  const value = React.useMemo(function createValue() {
    return {
      user: session.user,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      isAuthenticated: isAuthenticated,
      isLoading: isLoading,
      login: login,
      logout: logout,
      hasAnyRole: hasAnyRole,
      refreshFromStorage: refreshFromStorage,
    };
  }, [hasAnyRole, isAuthenticated, isLoading, login, logout, refreshFromStorage, session.accessToken, session.refreshToken, session.user]);

  return React.createElement(AuthContext.Provider, { value: value }, props.children);
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
