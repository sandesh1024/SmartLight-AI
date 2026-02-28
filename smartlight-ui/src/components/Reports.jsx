import { useTraffic } from "../context/TrafficContext";

export default function Reports() {
  const { trafficData, cityStats, totalSignals, lastUpdated, logs } = useTraffic();
  const allSignals = Object.entries(trafficData);

  return (
    <div className="page-section active">
      <div className="dashboard-panel" style={{ flex: 1 }}>
        <h3 className="panel-title">System &amp; Traffic Reports</h3>

        <div className="report-center">
          <p>📊 Live Traffic Data — {totalSignals} signals active</p>
          <p className="sub">
            {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString("en-IN")}` : "Waiting for backend…"}
          </p>
          <p className="sub" style={{ marginTop: 8 }}>
            City-wide: <strong>{cityStats.totalVehicles}</strong> vehicles &nbsp;|&nbsp;
            Active signals: <strong>{cityStats.activeSignals}</strong>
          </p>
          <div className="report-btns">
            <button className="report-btn" onClick={() => alert("Generating 24-hour summary report…")}>Generate Daily Summary</button>
            <button className="report-btn" onClick={() => alert("Exporting historical data…")}>Export CSV Data</button>
          </div>
        </div>

        {/* Live signal table */}
        {allSignals.length > 0 && (
          <div style={{ marginTop: "1.5rem", overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ background: "rgba(79,195,247,0.2)", color: "#0d47a1" }}>
                  {["Signal","Location","Active Lane","Phase","Timer","N","S","E","W"].map((h) => (
                    <th key={h} style={{ padding: "8px 10px", textAlign: "left", borderBottom: "1px solid #bbdefb", fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allSignals.map(([id, sig], i) => {
                  const vc = sig?.vehicle_counts ?? {};
                  return (
                    <tr key={id} style={{ background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.3)" }}>
                      <td style={{ padding: "7px 10px", color: "#0d47a1", fontWeight: 700 }}>{sig?.name ?? id}</td>
                      <td style={{ padding: "7px 10px", textTransform: "capitalize", color: "#475569" }}>{sig?.location ?? "—"}</td>
                      <td style={{ padding: "7px 10px", color: "#2e7d32", fontWeight: 700, textTransform: "uppercase" }}>{sig?.active_lane ?? "—"}</td>
                      <td style={{ padding: "7px 10px", color: sig?.phase === "GREEN" ? "#2e7d32" : sig?.phase === "YELLOW" ? "#f57f17" : "#c62828", fontWeight: 700 }}>{sig?.phase ?? "—"}</td>
                      <td style={{ padding: "7px 10px", fontWeight: 700 }}>{sig?.timer ?? 0}s</td>
                      <td style={{ padding: "7px 10px", color: "#0288d1" }}>{vc.north ?? 0}</td>
                      <td style={{ padding: "7px 10px", color: "#0288d1" }}>{vc.south ?? 0}</td>
                      <td style={{ padding: "7px 10px", color: "#0288d1" }}>{vc.east  ?? 0}</td>
                      <td style={{ padding: "7px 10px", color: "#0288d1" }}>{vc.west  ?? 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="dashboard-panel">
        <h3 className="panel-title">Recent System Log</h3>
        <div className="traffic-log">
          {logs.length === 0 && <p style={{ color: "#475569", fontSize: "0.85rem" }}>Log initialized…</p>}
          {logs.map((e) => (
            <div key={e.id} className="log-entry">
              <span className="log-time">{e.time}</span>
              <span className="log-type">[{e.type}]</span>
              <span style={{ flex: 1 }}>{e.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}