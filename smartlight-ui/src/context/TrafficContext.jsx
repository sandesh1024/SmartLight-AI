import { createContext, useContext, useEffect, useState, useRef, useCallback } from "react";

const TrafficContext = createContext();
const WS_URL = "ws://127.0.0.1:8000/ws";

export const TrafficProvider = ({ children }) => {
  const [trafficData,      setTrafficData]      = useState({});
  const [selectedSignalId, setSelectedSignalId] = useState("bandra_1");
  const [connected,        setConnected]        = useState(false);
  const [reconnecting,     setReconnecting]     = useState(false);
  const [logs,             setLogs]             = useState([]);

  const socketRef   = useRef(null);
  const reconnTimer = useRef(null);
  const mountedRef  = useRef(true);

  const addLog = useCallback((type, message) => {
    const time = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setLogs(prev => [{
      id: Date.now(),
      time, type, message,
    }, ...prev].slice(0, 60));
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!mountedRef.current) return;
        console.log("✅ WebSocket Connected");
        setConnected(true);
        setReconnecting(false);
        addLog("System", "Connected to backend");
      };

      socket.onmessage = (e) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(e.data);
          if (data && typeof data === "object" && Object.keys(data).length > 0) {
            setTrafficData(data);
          }
        } catch (err) {
          console.error("WS parse error:", err);
        }
      };

      socket.onclose = () => {
        if (!mountedRef.current) return;
        console.log("❌ WebSocket Disconnected");
        setConnected(false);
        setReconnecting(true);
        reconnTimer.current = setTimeout(connect, 3000);
      };

      socket.onerror = (err) => {
        console.error("WS error:", err);
        socket.close();
      };

    } catch (err) {
      console.error("WS connect error:", err);
      setReconnecting(true);
      reconnTimer.current = setTimeout(connect, 3000);
    }
  }, [addLog]);

  useEffect(() => {
    mountedRef.current = true;
    // Small delay to ensure backend is ready
    const timer = setTimeout(connect, 500);
    return () => {
      mountedRef.current = false;
      clearTimeout(timer);
      clearTimeout(reconnTimer.current);
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
    };
  }, [connect]);

  // Derived values
  const selectedSignal = trafficData[selectedSignalId] ?? null;

  const signalsByLocation = Object.entries(trafficData).reduce((acc, [id, sig]) => {
    const loc = sig?.location ?? "unknown";
    if (!acc[loc]) acc[loc] = [];
    acc[loc].push({ id, ...sig });
    return acc;
  }, {});

  const cityStats = Object.values(trafficData).reduce((acc, sig) => {
    const total = Object.values(sig?.vehicle_counts ?? {}).reduce((s, v) => s + v, 0);
    acc.totalVehicles += total;
    acc.activeSignals += sig?.cycle_ready ? 1 : 0;
    return acc;
  }, { totalVehicles: 0, activeSignals: 0 });

  const totalSignals  = Object.keys(trafficData).length;
  const lastUpdated   = new Date();

  return (
    <TrafficContext.Provider value={{
      trafficData,
      selectedSignalId,
      setSelectedSignalId,
      selectedSignal,
      signalsByLocation,
      cityStats,
      totalSignals,
      lastUpdated,
      connected,
      reconnecting,
      logs,
      addLog,
    }}>
      {children}
    </TrafficContext.Provider>
  );
};

export const useTraffic = () => useContext(TrafficContext);