export const APP_ROLES = ["TEACHER", "CONTACT_PERSON", "HEADTEACHER", "BURSAR", "BOARD"] as const;
export type AppRole = (typeof APP_ROLES)[number];

export interface AuthUser {
  id?: number;
  username: string;
  role: AppRole;
  full_name?: string;
}

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "auth_user";

function normalizeRole(value: any) {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.toUpperCase().trim();
  if (APP_ROLES.indexOf(normalized as AppRole) === -1) {
    return null;
  }
  return normalized as AppRole;
}

function decodeTokenPayload(token: string) {
  try {
    const parts = token.split(".");
    if (parts[1] === undefined) {
      return null;
    }
    if (typeof atob === "undefined") {
      return null;
    }
    let encoded = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const remainder = encoded.length - Math.floor(encoded.length / 4) * 4;
    if (remainder === 2) {
      encoded += "==";
    }
    if (remainder === 3) {
      encoded += "=";
    }
    return JSON.parse(atob(encoded));
  } catch (error) {
    return null;
  }
}

function readStoredUser() {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(USER_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw);
    const role = normalizeRole(parsed.role);
    if (role === null) {
      return null;
    }
    if (parsed.username === undefined) {
      return null;
    }
    return { id: parsed.id, username: String(parsed.username), role: role, full_name: parsed.full_name };
  } catch (error) {
    return null;
  }
}

function getUserFromToken(accessToken: any) {
  if (accessToken === null) {
    return null;
  }
  const payload = decodeTokenPayload(accessToken);
  if (payload === null) {
    return null;
  }
  const role = normalizeRole(payload.role);
  if (role === null) {
    return null;
  }
  if (typeof payload.username !== "string") {
    return null;
  }
  return { username: payload.username, role: role, full_name: payload.username };
}

export function getStoredSession() {
  if (typeof window === "undefined") {
    return { accessToken: null, refreshToken: null, user: null };
  }
  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  let user = readStoredUser();
  if (user === null) {
    user = getUserFromToken(accessToken);
  }
  return { accessToken: accessToken, refreshToken: refreshToken, user: user };
}

export function persistSession(accessToken: string, refreshToken: string, user: AuthUser) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  return { accessToken: accessToken, refreshToken: refreshToken, user: user };
}

export function clearStoredSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function roleLabel(role: any) {
  switch (role) {
    case "CONTACT_PERSON":
      return "Contact Person";
    case "HEADTEACHER":
      return "Headteacher";
    case "BURSAR":
      return "Bursar";
    case "BOARD":
      return "Board";
    default:
      return "Teacher";
  }
}
