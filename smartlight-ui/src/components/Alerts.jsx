// smartlight-ui/src/components/Alerts.jsx
// Admin sends notifications → stored on backend → public app reads them

import { useState, useEffect } from "react";
import { useTraffic } from "../context/TrafficContext";

const API   = "http://127.0.0.1:8000";
const ICONS = { info: "📢", warning: "⚠️", alert: "🚨", emergency: "🔥" };

export default function Alerts({ addLog }) {
  const { trafficData, connected } = useTraffic();

  const [title,         setTitle]         = useState("");
  const [message,       setMsg]           = useState("");
  const [type,          setType]          = useState("info");
  const [area,          setArea]          = useState("all");
  const [sending,       setSending]       = useState(false);
  const [notifications, setNotifications] = useState([]);

  // Fetch existing notifications from backend on load
  useEffect(() => {
    fetch(`${API}/notifications`)
      .then(r => r.json())
      .then(data => setNotifications(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  // Auto alerts from live backend data
  const autoAlerts = [];
  if (!connected) {
    autoAlerts.push({ id: "ws", icon: "🔌", text: "Backend disconnected — no live data." });
  }
  Object.entries(trafficData).forEach(([id, sig]) => {
    if (!sig) return;
    const total = Object.values(sig.vehicle_counts ?? {}).reduce((s, v) => s + v, 0);
    if (total > 30) autoAlerts.push({ id: `hi-${id}`, icon: "🚗", text: `High traffic at ${sig.name} — ${total} vehicles` });
    if (sig.emergency) autoAlerts.push({ id: `em-${id}`, icon: "🚨", text: `Emergency active at ${sig.name}` });
  });

  async function sendNotification() {
    if (!title || !message) { alert("Please fill in title and message."); return; }
    setSending(true);
    try {
      const res = await fetch(`${API}/notifications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, message, type, area }),
      });
      const data = await res.json();
      if (data.notification) {
        setNotifications(prev => [data.notification, ...prev]);
        addLog("Notification", `Sent: ${title}`);
        setTitle(""); setMsg("");
        alert("✅ Notification sent — visible on public app.");
      }
    } catch {
      alert("❌ Failed to send. Is backend running?");
    } finally {
      setSending(false);
    }
  }

  const areas = ["all","bandra","worli","dadar","andheri","churchgate"];

  return (
    <div className="page-section active">
      {autoAlerts.length > 0 && (
        <div className="dashboard-panel">
          <h3 className="panel-title">⚡ Live System Alerts</h3>
          <div className="notifications-list" style={{ maxHeight: 150 }}>
            {autoAlerts.map(a => (
              <div key={a.id} className="notification-item">
                <div className="notification-title">{a.icon} {a.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="dashboard-panel" style={{ flex: 1 }}>
        <h3 className="panel-title">Send Public Notification</h3>
        <div className="notification-form">
          <input
            className="notification-input"
            placeholder="Notification Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <textarea
            className="notification-textarea"
            placeholder="Notification Message"
            value={message}
            onChange={e => setMsg(e.target.value)}
          />
          <select className="notification-input" value={type} onChange={e => setType(e.target.value)}>
            <option value="info">📢 Information</option>
            <option value="warning">⚠️ Warning</option>
            <option value="alert">🚨 Alert</option>
            <option value="emergency">🔥 Emergency</option>
          </select>
          <select className="notification-input" value={area} onChange={e => setArea(e.target.value)}>
            {areas.map(a => (
              <option key={a} value={a}>
                {a === "all" ? "All Areas" : a.charAt(0).toUpperCase() + a.slice(1)}
              </option>
            ))}
          </select>
          <button
            className="notification-btn"
            onClick={sendNotification}
            disabled={sending}
          >
            {sending ? "⏳ Sending..." : "📤 Send to Public App"}
          </button>
        </div>

        <h3 className="panel-title">Sent Notifications</h3>
        <div className="notifications-list">
          {notifications.length === 0 && (
            <p style={{ color: "#475569", fontSize: "0.85rem" }}>No notifications sent yet.</p>
          )}
          {notifications.slice(0, 20).map(n => (
            <div key={n.id} className="notification-item">
              <div className="notification-title">
                {ICONS[n.type] ?? "📢"} {n.title}
              </div>
              <div className="notification-meta">
                <span>{n.timestamp}</span>
                <span>
                  {n.area === "all" ? "All Areas" : n.area.charAt(0).toUpperCase() + n.area.slice(1)}
                </span>
              </div>
              <div style={{ fontSize: "0.85rem" }}>{n.message}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}