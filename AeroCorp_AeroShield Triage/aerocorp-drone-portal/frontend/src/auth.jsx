import { createContext, useCallback, useContext, useMemo, useState } from "react";

const KEY = "aerocorp.session";
const AuthContext = createContext(null);

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession);

  const login = useCallback((next) => {
    setSession(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* storage blocked: the session lasts until the tab closes */
    }
  }, []);

  const logout = useCallback(() => {
    setSession(null);
    try {
      localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(() => ({ session, token: session?.token ?? null, login, logout }), [session, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
