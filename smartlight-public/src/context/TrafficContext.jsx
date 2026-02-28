import { createContext, useContext, useEffect, useState, useRef, useCallback } from "react";

const TrafficContext = createContext();
const BACKEND_HOST = window.location.hostname;
const WS_URL  = `ws://${BACKEND_HOST}:8000/ws`;
const API_URL = `http://${BACKEND_HOST}:8000`;

export const getLevel = (total) => {
  if (total >= 50) return { label: "HIGH",   color: "#ef5350", bg: "rgba(239,83,80,0.12)",   emoji: "🔴", pulse: true  };
  if (total >= 30) return { label: "MEDIUM", color: "#ffa726", bg: "rgba(255,167,38,0.12)",  emoji: "🟡", pulse: false };
  return              { label: "LOW",    color: "#66bb6a", bg: "rgba(102,187,106,0.12)", emoji: "🟢", pulse: false };
};

export const TrafficProvider = ({ children }) => {
  const [trafficData,    setTrafficData]    = useState({});
  const [connected,      setConnected]      = useState(false);
  const [reconnecting,   setReconnecting]   = useState(false);
  const [notifications,  setNotifications]  = useState([]);

  const socketRef    = useRef(null);
  const reconnTimer  = useRef(null);
  const mountedRef   = useRef(true);
  const prevDataRef  = useRef({});

  // ── WebSocket ──────────────────────────────────────────
  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    try {
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        setReconnecting(false);
      };

      socket.onmessage = (e) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(e.data);
          setTrafficData(data);

          // Auto-generate notifications for high traffic / emergency
          const now = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
          Object.entries(data).forEach(([id, sig]) => {
            if (!sig?.vehicle_counts) return;
            const total     = Object.values(sig.vehicle_counts).reduce((s, v) => s + v, 0);
            const prev      = prevDataRef.current[id];
            const prevTotal = prev ? Object.values(prev.vehicle_counts ?? {}).reduce((s, v) => s + v, 0) : 0;

            if (total >= 50 && prevTotal < 50) {
              setNotifications(n => [{
                id:       Date.now() + id,
                type:     "high",
                title:    `Heavy Traffic — ${sig.name}`,
                message:  `${total} vehicles detected`,
                area:     sig.location,
                time:     now,
                source:   "auto",
              }, ...n].slice(0, 30));
            }

            if (sig.emergency && !prev?.emergency) {
              setNotifications(n => [{
                id:      Date.now() + id + "em",
                type:    "emergency",
                title:   `Emergency Active — ${sig.name}`,
                message: `${sig.active_lane?.toUpperCase()} lane on priority`,
                area:    sig.location,
                time:    now,
                source:  "auto",
              }, ...n].slice(0, 30));
            }
          });

          prevDataRef.current = data;
        } catch {}
      };

      socket.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        setReconnecting(true);
        reconnTimer.current = setTimeout(connect, 3000);
      };

      socket.onerror = () => socket.close();
    } catch {
      setReconnecting(true);
      reconnTimer.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnTimer.current);
      socketRef.current?.close();
    };
  }, [connect]);

  // ── Poll backend for admin-sent notifications every 5s ──
  useEffect(() => {
    const fetchNotifs = async () => {
      try {
        const res  = await fetch(`${API_URL}/notifications`);
        const data = await res.json();
        if (!Array.isArray(data)) return;

        // Merge admin notifications with auto-generated ones
        // Admin notifications have an "id" from backend
        setNotifications(prev => {
          const autoNotifs  = prev.filter(n => n.source === "auto");
          const adminNotifs = data.map(n => ({
            ...n,
            time:   n.timestamp ?? "",
            source: "admin",
          }));

          // Combine: admin first, then auto, deduplicated by id
          const all   = [...adminNotifs, ...autoNotifs];
          const seen  = new Set();
          return all.filter(n => {
            if (seen.has(String(n.id))) return false;
            seen.add(String(n.id));
            return true;
          }).slice(0, 40);
        });
      } catch {}
    };

    fetchNotifs(); // run immediately on mount
    const interval = setInterval(fetchNotifs, 5000); // then every 5s
    return () => clearInterval(interval);
  }, []);

  // ── Computed values ──────────────────────────────────────
  const signalsByLocation = Object.entries(trafficData).reduce((acc, [id, sig]) => {
    const loc = sig?.location ?? "unknown";
    if (!acc[loc]) acc[loc] = [];
    const total = Object.values(sig?.vehicle_counts ?? {}).reduce((s, v) => s + v, 0);
    acc[loc].push({ id, ...sig, total, level: getLevel(total) });
    return acc;
  }, {});

  const cityStats = Object.values(trafficData).reduce((acc, sig) => {
    const total = Object.values(sig?.vehicle_counts ?? {}).reduce((s, v) => s + v, 0);
    acc.totalVehicles += total;
    acc.totalSignals  += 1;
    if (total >= 50)             acc.highCount   += 1;
    if (total >= 30 && total < 50) acc.mediumCount += 1;
    if (total < 30)              acc.lowCount    += 1;
    return acc;
  }, { totalVehicles: 0, totalSignals: 0, highCount: 0, mediumCount: 0, lowCount: 0 });

  return (
    <TrafficContext.Provider value={{
      trafficData, connected, reconnecting,
      signalsByLocation, cityStats, notifications,
    }}>
      {children}
    </TrafficContext.Provider>
  );
};

export const useTraffic = () => useContext(TrafficContext);