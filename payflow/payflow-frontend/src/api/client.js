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
        const response = await axios.post(
          `${API_BASE_URL}/api/token/refresh/`,
          { refresh: refreshToken }
        );

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