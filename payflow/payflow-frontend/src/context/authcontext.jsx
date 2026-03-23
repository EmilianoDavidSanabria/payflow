import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {

  const [accessToken, setAccessToken] = useState(
    localStorage.getItem("access_token")
  );

  const [refreshToken, setRefreshToken] = useState(
    localStorage.getItem("refresh_token")
  );

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
  };

  const value = useMemo(() => {
    return {
      accessToken,
      refreshToken,
      isAuthenticated: !!accessToken,
      login,
      logout,
    };
  }, [accessToken, refreshToken]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}