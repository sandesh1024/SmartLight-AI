import { useState } from "react";
import { useTraffic } from "../context/TrafficContext";

const DIRS = ["north", "south", "east", "west"];
const API  = "http://127.0.0.1:8000";

export default function ManualControls({ addLog }) {
  const { selectedSignal, selectedSignalId } = useTraffic();
  const [loading, setLoading] = useState(null);

  const post = async (url, body = {}) => {
    const res = await fetch(`${API}${url}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.ok;
  };

  const handleControl = async (lane, color) => {
    const key  = `${lane}-${color}`;
    const name = selectedSignal?.name ?? selectedSignalId;
    setLoading(key);
    try {
      await post(`/signals/${selectedSignalId}/override`, {
        lane, color, duration: color === "green" ? 15 : 10,
      });
      addLog("Manual Override", `${name}: ${lane.toUpperCase()} → ${color.toUpperCase()}`);
    } catch {
      addLog("Manual Override", `${name}: ${lane.toUpperCase()} → ${color.toUpperCase()} (failed)`);
    } finally {
      setLoading(null);
    }
  };

  const handleEmergency = async (lane) => {
    const key  = `${lane}-em`;
    const name = selectedSignal?.name ?? selectedSignalId;
    setLoading(key);
    try {
      await post(`/signals/${selectedSignalId}/emergency`, { lane, duration: 30 });
      addLog("Emergency", `${name}: ${lane.toUpperCase()} emergency GREEN 30s`);
    } catch {
      addLog("Emergency", `${name}: ${lane.toUpperCase()} failed`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="dashboard-panel">
      <h3 className="panel-title">Manual Controls</h3>
      <div className="control-grid">
        {DIRS.map((lane) => (
          <div key={lane} className="control-group">
            <h4>{lane.charAt(0).toUpperCase() + lane.slice(1)} Lane</h4>
            <div className="control-buttons">
              <button className="control-btn red"    disabled={!!loading} onClick={() => handleControl(lane, "red")}>
                {loading === `${lane}-red` ? "..." : "Red"}
              </button>
              <button className="control-btn yellow" disabled={!!loading} onClick={() => handleControl(lane, "yellow")}>
                {loading === `${lane}-yellow` ? "..." : "Yellow"}
              </button>
              <button className="control-btn green"  disabled={!!loading} onClick={() => handleControl(lane, "green")}>
                {loading === `${lane}-green` ? "..." : "Green"}
              </button>
            </div>
            <button className="control-btn emergency" disabled={!!loading} onClick={() => handleEmergency(lane)}>
              {loading === `${lane}-em` ? "⏳ Sending..." : "🚨 Emergency"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}