import { createContext, useContext, useState } from "react";

const AuthContext = createContext();

// Hardcoded admin credentials
// In production: replace with API call to your backend
const ADMINS = [
  { username: "admin",   password: "smartlight123", role: "Admin",      name: "Traffic Authority" },
  { username: "officer", password: "officer456",    role: "Officer",    name: "Traffic Officer"   },
  { username: "super",   password: "super789",      role: "Supervisor", name: "Supervisor"        },
];

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("sl_admin");
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  const [error, setError] = useState("");

  const login = (username, password) => {
    const found = ADMINS.find(
      a => a.username === username.trim() && a.password === password
    );
    if (found) {
      const u = { username: found.username, role: found.role, name: found.name };
      setUser(u);
      sessionStorage.setItem("sl_admin", JSON.stringify(u));
      setError("");
      return true;
    }
    setError("Invalid username or password.");
    return false;
  };

  const logout = () => {
    setUser(null);
    sessionStorage.removeItem("sl_admin");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, error, setError }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);