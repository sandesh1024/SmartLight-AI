import { useTraffic } from "../context/TrafficContext";

export default function TrafficLog() {
  const { logs } = useTraffic();

  return (
    <div className="dashboard-panel">
      <h3 className="panel-title">Traffic Log</h3>
      <div className="traffic-log">
        {logs.length === 0 && (
          <div className="log-entry">
            <span className="log-time">--:--</span>
            <span>[System] Log initialized…</span>
          </div>
        )}
        {logs.map((entry) => (
          <div key={entry.id} className="log-entry">
            <span className="log-time">{entry.time}</span>
            <span className="log-type">[{entry.type}]</span>
            <span style={{ flex: 1 }}>{entry.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}