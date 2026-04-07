import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();

if (!API_BASE_URL) {
  throw new Error("Missing VITE_API_BASE_URL environment variable");
}

const redirectToLogin = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/";
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const getApiErrorMessage = (
  error,
  fallback = "Something went wrong. Please try again."
) => {
  if (!error) return fallback;

  const data = error.response?.data;

  if (typeof data === "string" && data.trim()) {
    return data;
  }

  if (data?.detail && typeof data.detail === "string") {
    return data.detail;
  }

  if (data?.error && typeof data.error === "string") {
    return data.error;
  }

  if (data?.message && typeof data.message === "string") {
    return data.message;
  }

  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length > 0) {
    return data.non_field_errors[0];
  }

  if (typeof data === "object" && data !== null) {
    for (const value of Object.values(data)) {
      if (Array.isArray(value) && value.length > 0 && typeof value[0] === "string") {
        return value[0];
      }

      if (typeof value === "string" && value.trim()) {
        return value;
      }
    }
  }

  if (error.code === "ECONNABORTED") {
    return "The request took too long. Please try again.";
  }

  if (!error.response) {
    return "Could not reach the server. Check your connection and try again.";
  }

  if (error.response.status >= 500) {
    return "The server could not complete the request. Please try again.";
  }

  if (error.response.status === 404) {
    return "The requested resource was not found.";
  }

  if (error.response.status === 401) {
    return "Your session is no longer valid. Please sign in again.";
  }

  if (error.response.status === 403) {
    return "You do not have permission to perform this action.";
  }

  if (error.response.status === 400) {
    return fallback;
  }

  return fallback;
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const requestUrl = originalRequest.url || "";

    const isLoginRequest = requestUrl.includes("/api/token/");
    const isRefreshRequest = requestUrl.includes("/api/token/refresh/");

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isLoginRequest &&
      !isRefreshRequest
    ) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        redirectToLogin();
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/api/token/refresh/`, {
          refresh: refreshToken,
        });

        const newAccess = response.data.access;

        localStorage.setItem("access_token", newAccess);

        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${newAccess}`,
        };

        return api(originalRequest);
      } catch (refreshError) {
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);