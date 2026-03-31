import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(
    localStorage.getItem("access_token")
  );
  const [refreshToken, setRefreshToken] = useState(
    localStorage.getItem("refresh_token")
  );
  const [currentUser, setCurrentUser] = useState(null);
  const [authResolved, setAuthResolved] = useState(false);

  const login = (access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);

    setAccessToken(access);
    setRefreshToken(refresh);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    setAccessToken(null);
    setRefreshToken(null);
    setCurrentUser(null);
    setAuthResolved(true);
  };

  useEffect(() => {
    async function loadCurrentUser() {
      if (!accessToken) {
        setCurrentUser(null);
        setAuthResolved(true);
        return;
      }

      try {
        const response = await api.get("/users/me/");
        setCurrentUser(response.data);
      } catch (error) {
        console.error("LOAD CURRENT USER ERROR:", error);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setAccessToken(null);
        setRefreshToken(null);
        setCurrentUser(null);
      } finally {
        setAuthResolved(true);
      }
    }

    setAuthResolved(false);
    loadCurrentUser();
  }, [accessToken]);

  const value = useMemo(() => {
    return {
      accessToken,
      refreshToken,
      currentUser,
      authResolved,
      isAuthenticated: !!accessToken,
      login,
      logout,
    };
  }, [accessToken, refreshToken, currentUser, authResolved]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}