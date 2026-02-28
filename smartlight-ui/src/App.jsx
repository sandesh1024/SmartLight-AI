import { useState } from "react";
import { useAuth } from "./context/AuthContext";
import Login from "./components/Login";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Emergency from "./components/Emergency";
import Alerts from "./components/Alerts";
import Reports from "./components/Reports";
import { useTraffic } from "./context/TrafficContext";

export default function App() {
  const { user, logout } = useAuth();
  const [activePage,  setActivePage]  = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { addLog } = useTraffic();

  // Not logged in → show login page only
  if (!user) return <Login />;

  return (
    <>
      {/* Admin info bar — only renders when logged in */}
      <div style={{
        background: "rgba(13,71,161,0.92)",
        backdropFilter: "blur(8px)",
        color: "white",
        padding: "0.3rem 1rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: "1rem",
        fontSize: "0.78rem",
        fontWeight: 700,
        fontFamily: "'Nunito', sans-serif",
        position: "relative",   // ← NOT fixed, so it doesn't overlap other apps
        zIndex: 999,
      }}>
        <span>👤 {user.name} · {user.role}</span>
        <button
          onClick={logout}
          style={{
            background: "rgba(255,255,255,0.2)",
            border: "1px solid rgba(255,255,255,0.3)",
            color: "white",
            padding: "0.2rem 0.7rem",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "0.75rem",
            fontWeight: 700,
            fontFamily: "inherit",
          }}
        >
          Logout
        </button>
      </div>

      <Navbar
        activePage={activePage}
        setActivePage={setActivePage}
        onHamburger={() => setSidebarOpen(true)}
      />

      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        addLog={addLog}
      />

      <div className="main-container">
        {activePage === "dashboard" && <Dashboard addLog={addLog} />}
        {activePage === "emergency" && <Emergency addLog={addLog} />}
        {activePage === "alerts"    && <Alerts    addLog={addLog} />}
        {activePage === "reports"   && <Reports />}
      </div>
    </>
  );
}