import { useEffect, useState } from "react";
import { useTraffic } from "../context/TrafficContext";

const DIRS = ["north", "south", "east", "west"];

function LaneLight({ dir, activeLane, phase, displayTimer }) {
  const isActive = activeLane === dir;

  let redOn = false, yellowOn = false, greenOn = false;
  if (isActive) {
    if (phase === "GREEN")  greenOn  = true;
    if (phase === "YELLOW") yellowOn = true;
    if (phase === "RED")    redOn    = true;
  } else {
    redOn = true;
  }

  const timerColor = phase === "GREEN" ? "#2e7d32" : phase === "YELLOW" ? "#f57f17" : "#c62828";

  return (
    <div className="signal-light">
      <div className="lane-name-label">
        {dir.charAt(0).toUpperCase() + dir.slice(1)} Lane
      </div>
      <div className="light-container">
        <div className={`light red    ${redOn    ? "on" : ""}`} />
        <div className={`light yellow ${yellowOn ? "on" : ""}`} />
        <div className={`light green  ${greenOn  ? "on" : ""}`} />
      </div>
      <div className="timer-box" style={{ color: isActive ? timerColor : "#94a3b8" }}>
        {isActive ? displayTimer : "—"}
      </div>
    </div>
  );
}

export default function SignalLights() {
  const { selectedSignal, selectedSignalId } = useTraffic();
  const [localTimer, setLocalTimer] = useState(0);

  // Sync local timer with backend value whenever it changes
  useEffect(() => {
    if (selectedSignal?.timer != null) {
      setLocalTimer(selectedSignal.timer);
    }
  }, [selectedSignal?.timer, selectedSignal?.active_lane]);

  // Tick down locally every second for smooth countdown
  useEffect(() => {
    const interval = setInterval(() => {
      setLocalTimer(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeLane = selectedSignal?.active_lane ?? null;
  const phase      = selectedSignal?.phase       ?? "RED";
  const name       = selectedSignal?.name        ?? selectedSignalId;

  return (
    <div className="dashboard-panel">
      <h3 className="panel-title">
        Signal Status &amp; Timers
        {name && (
          <span style={{ fontSize:"0.75rem", color:"#0288d1", marginLeft:8, fontWeight:600 }}>
            — {name}
          </span>
        )}
      </h3>

      {!selectedSignal ? (
        <p style={{ color:"#475569", textAlign:"center", padding:"2rem" }}>
          ⏳ Waiting for backend data…
        </p>
      ) : (
        <div className="signal-status-panel">
          {DIRS.map((dir) => (
            <LaneLight
              key={dir}
              dir={dir}
              activeLane={activeLane}
              phase={phase}
              displayTimer={localTimer}
            />
          ))}
        </div>
      )}
    </div>
  );
}