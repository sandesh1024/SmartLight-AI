import { useEffect, useState } from "react";
import { useTraffic } from "../context/TrafficContext";

export default function Navbar({ activePage, setActivePage, onHamburger }) {
  const { connected, reconnecting, connectionAttempts, totalSignals } = useTraffic();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const wsClass = connected ? "ok" : reconnecting ? "warn" : "err";
  const wsLabel = connected
    ? `🟢 LIVE · ${totalSignals} signals`
    : reconnecting
    ? `⏳ Reconnecting (${connectionAttempts})`
    : "🔴 Offline";

  const pages = [
    { id: "dashboard", label: "Dashboard" },
    { id: "emergency", label: "Emergency Route" },
    { id: "alerts",    label: "Public Alerts" },
    { id: "reports",   label: "Reports" },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="logo-group">
          <button className="hamburger" onClick={onHamburger}>☰</button>
          <div className="logo">🚦 Smart Light AI</div>
          <span className={`ws-badge ${wsClass}`}>
            <span className="ws-dot" />
            {wsLabel}
          </span>
        </div>
        <div className="nav-buttons">
          {pages.map((p) => (
            <button
              key={p.id}
              className={`nav-btn ${activePage === p.id ? "active" : ""}`}
              onClick={() => setActivePage(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}