import { useState } from "react";
import { useTraffic } from "../context/TrafficContext";

const API = "http://127.0.0.1:8000";

export default function Sidebar({ open, onClose, addLog }) {
  const { trafficData, signalsByLocation, selectedSignalId, setSelectedSignalId } = useTraffic();
  const [filterArea, setFilterArea] = useState("all");

  const locations = Object.keys(signalsByLocation);

  const getStatusText = (sig) => {
    if (!sig?.cycle_ready) return "⏳ Initializing...";
    const lane  = sig.active_lane ?? "—";
    const timer = sig.timer ?? 0;
    const phase = sig.phase ?? "—";
    return `${lane.charAt(0).toUpperCase() + lane.slice(1)} ${phase} (${timer}s)`;
  };

  const allSignals = Object.entries(trafficData);
  const filtered   = filterArea === "all"
    ? allSignals
    : allSignals.filter(([, s]) => s?.location === filterArea);

  const handleSelect = (id) => {
    setSelectedSignalId(id);
    if (window.innerWidth <= 1024) onClose();
  };

  const post = async (url) => {
    try {
      await fetch(`${API}${url}`, { method: "POST" });
    } catch (e) {
      console.error(e);
    }
  };

  const handleResetAll = async () => {
    await post("/signals/reset-all");
    addLog("System", "All signals reset to automatic mode");
    alert("All signals reset.");
    onClose();
  };

  const handleOptimize = async () => {
    await post("/signals/optimize");
    addLog("System", "Traffic flow optimization triggered");
    alert("Optimization triggered — YOLO re-running on all signals.");
    onClose();
  };

  const handleCityEmergency = () => {
    addLog("City Emergency", "City-wide emergency activated");
    alert("City-wide emergency activated.");
    onClose();
  };

  return (
    <>
      <div className={`sidebar-backdrop ${open ? "active" : ""}`} onClick={onClose} />
      <div className={`sidebar-menu ${open ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>Traffic Signals</h3>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <select
          className="area-selector"
          value={filterArea}
          onChange={(e) => setFilterArea(e.target.value)}
        >
          <option value="all">All Areas</option>
          {locations.map((loc) => (
            <option key={loc} value={loc}>
              {loc.charAt(0).toUpperCase() + loc.slice(1)}
            </option>
          ))}
        </select>

        <div className="signal-list">
          {filtered.length === 0 && (
            <p style={{ color: "#475569", fontSize: "0.85rem", padding: "0.5rem" }}>
              {Object.keys(trafficData).length === 0 ? "⏳ Connecting to backend…" : "No signals here."}
            </p>
          )}
          {filtered.map(([id, sig]) => (
            <div
              key={id}
              className={`signal-item ${selectedSignalId === id ? "active" : ""}`}
              onClick={() => handleSelect(id)}
            >
              <div className="signal-name">
                🚥 {sig?.name ?? id}
                <span className="location-tag">
                  {sig?.location ? sig.location.charAt(0).toUpperCase() + sig.location.slice(1) : ""}
                </span>
              </div>
              <div className="signal-status-text">{getStatusText(sig)}</div>
            </div>
          ))}
        </div>

        <div className="quick-actions">
          <h3>Quick Actions</h3>
          <button className="action-btn emergency" onClick={handleCityEmergency}>
            🚨 City-Wide Emergency
          </button>
          <button className="action-btn" onClick={handleResetAll}>
            ↺ Reset All Signals
          </button>
          <button className="action-btn" onClick={handleOptimize}>
            ⚡ Optimize Traffic Flow
          </button>
        </div>
      </div>
    </>
  );
}