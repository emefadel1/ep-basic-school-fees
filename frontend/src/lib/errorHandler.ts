export interface APIError {
  success: false;
  error: any;
  timestamp?: string;
  context?: any;
}

export function isAPIError(error: unknown): error is APIError {
  if (!error) {
    return false;
  }
  if (typeof error !== "object") {
    return false;
  }
  if ((error as any).success !== false) {
    return false;
  }
  return Boolean((error as any).error);
}

export function getFieldErrors(error: unknown): { [key: string]: string } {
  const result: { [key: string]: string } = {};
  if (!isAPIError(error)) {
    return result;
  }
  if (!error.error.errors) {
    return result;
  }
  for (const key of Object.keys(error.error.errors)) {
    const value = error.error.errors[key];
    if (Array.isArray(value)) {
      if (value.length) {
        result[key] = String(value[0]);
      }
    }
  }
  return result;
}

export function getErrorMessage(error: unknown): string {
  if (typeof navigator !== "undefined") {
    if (navigator.onLine === false) {
      return "You appear to be offline. Check your connection and try again.";
    }
  }
  if (isAPIError(error)) {
    const fieldErrors = getFieldErrors(error);
    const keys = Object.keys(fieldErrors);
    if (keys.length) {
      return fieldErrors[keys[0]];
    }
    if (error.error.message) {
      return error.error.message;
    }
    return "Request failed.";
  }
  if (error instanceof Error) {
    if (error.message === "Failed to fetch") {
      return "Network error. Check your connection and try again.";
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

export function handleAPIError(error: unknown): never {
  if (isAPIError(error)) {
    if (typeof window !== "undefined") {
      if (error.error.status === 401) {
        window.localStorage.removeItem("access_token");
        window.localStorage.removeItem("refresh_token");
        if (window.location.pathname !== "/login") {
            window.location.assign("/login");
        }
      }
      if (error.error.code === "token_expired") {
        window.localStorage.removeItem("access_token");
        window.localStorage.removeItem("refresh_token");
        if (window.location.pathname !== "/login") {
            window.location.assign("/login");
        }
      }
    }
    if (Object.keys(getFieldErrors(error)).length) {
      throw error;
    }
  }
  throw new Error(getErrorMessage(error));
}
export function setupAxiosErrorInterceptor(client: any): any {
  if (!client) {
    return client;
  }
  if (!client.interceptors) {
    return client;
  }
  if (!client.interceptors.response) {
    return client;
  }
  if (typeof client.interceptors.response.use !== "function") {
    return client;
  }
  client.interceptors.response.use(
    function onFulfilled(response: any) {
      return response;
    },
    function onRejected(error: any) {
      let payload: any = error;
      if (error) {
        if (error.response) {
            payload = error.response.data;
        }
      }
      if (isAPIError(payload)) {
        if (Object.keys(getFieldErrors(payload)).length) {
            return Promise.reject(payload);
        }
      }
      handleAPIError(payload);
    },
  );
  return client;
}
