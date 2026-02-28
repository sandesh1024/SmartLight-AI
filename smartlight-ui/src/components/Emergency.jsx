import { useEffect, useRef, useState } from "react";
import { useTraffic } from "../context/TrafficContext";

const API = "http://127.0.0.1:8000";

const AREA_COORDS = {
  bandra:     [19.0559, 72.8405],
  worli:      [19.0069, 72.8188],
  dadar:      [19.0210, 72.8450],
  andheri:    [19.1170, 72.8580],
  churchgate: [18.9310, 72.8250],
};
const AREA_COLORS = {
  bandra: "#ef5350", worli: "#26a69a", dadar: "#ffa726",
  andheri: "#5c6bc0", churchgate: "#42a5f5",
};

// Signal coords per index offset
const SIG_OFFSETS = [
  [0, 0], [0.003, 0.003], [-0.003, 0.003], [0, -0.004],
];

export default function Emergency({ addLog }) {
  const { trafficData } = useTraffic();
  const mapRef      = useRef(null);
  const mapInstance = useRef(null);
  const routingRef  = useRef(null);
  const markersRef  = useRef({});

  const [startArea, setStartArea] = useState("");
  const [endArea,   setEndArea]   = useState("");
  const [emergency, setEmergency] = useState({
    active: false, name: null, affectedSignals: [], directionLane: null,
  });

  // Load Leaflet + plugins dynamically
  useEffect(() => {
    if (window.L && window.L.Routing && window.turf) { initMap(); return; }

    const addLink = (href) => {
      const l = document.createElement("link");
      l.rel = "stylesheet"; l.href = href;
      document.head.appendChild(l);
    };
    const addScript = (src, cb) => {
      const s = document.createElement("script");
      s.src = src; s.onload = cb;
      document.head.appendChild(s);
    };

    addLink("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
    addLink("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css");

    addScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", () =>
      addScript("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js", () =>
        addScript("https://cdn.jsdelivr.net/npm/@turf/turf@6/turf.min.js", initMap)
      )
    );

    return () => { mapInstance.current?.remove(); mapInstance.current = null; };
  }, []);

  // Add/update markers from live backend data
  useEffect(() => {
    if (!mapInstance.current || !window.L) return;
    const L = window.L;

    Object.entries(trafficData).forEach(([id, sig]) => {
      if (!sig?.location) return;
      const area   = sig.location;
      const color  = AREA_COLORS[area] ?? "#4fc3f7";
      const sigNum = parseInt(id.split("_")[1] ?? 1) - 1;
      const base   = AREA_COORDS[area] ?? [19.076, 72.877];
      const [lo, ln] = SIG_OFFSETS[sigNum] ?? [0, 0];
      const coords = [base[0] + lo, base[1] + ln];

      if (markersRef.current[id]) {
        markersRef.current[id].setLatLng(coords);
      } else {
        markersRef.current[id] = L.marker(coords)
          .addTo(mapInstance.current)
          .bindPopup(`<b style="color:#0d47a1">${sig.name}</b><br>${area}<br>Active: ${sig.active_lane ?? "—"} | ${sig.timer ?? 0}s`)
          .setIcon(L.divIcon({
            className: "",
            html: `<div id="sig-icon-${id}" style="background:${color};width:18px;height:18px;border-radius:50%;border:3px solid white;box-shadow:0 0 8px ${color};"></div>`,
            iconSize: [18, 18], iconAnchor: [9, 9],
          }));
      }
    });
  }, [trafficData]);

  function initMap() {
    if (!mapRef.current || mapInstance.current) return;
    const L = window.L;
    mapInstance.current = L.map(mapRef.current).setView([19.076, 72.877], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
    }).addTo(mapInstance.current);
  }

  // POST override to backend for all affected signals
  async function applyEmergencyToBackend(affectedIds, directionLane) {
    for (const id of affectedIds) {
      try {
        await fetch(`${API}/signals/${id}/emergency`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lane: directionLane, duration: 300 }), // 5 min emergency
        });
      } catch (e) {
        console.error(`Failed to override ${id}:`, e);
      }
    }
  }

  // Clear emergency overrides on backend
  async function clearEmergencyFromBackend(affectedIds) {
    for (const id of affectedIds) {
      try {
        await fetch(`${API}/signals/${id}/reset`, { method: "POST" });
      } catch (e) {
        console.error(`Failed to reset ${id}:`, e);
      }
    }
  }

  function activateRoute() {
    if (!startArea || !endArea || startArea === endArea) {
      alert("Please select different start and end areas."); return;
    }
    if (!window.L?.Routing) {
      alert("Map still loading, please try again."); return;
    }
    const L   = window.L;
    const map = mapInstance.current;
    if (!map) return;

    if (routingRef.current) { map.removeControl(routingRef.current); routingRef.current = null; }

    const [sLat, sLng] = AREA_COORDS[startArea];
    const [eLat, eLng] = AREA_COORDS[endArea];

    routingRef.current = L.Routing.control({
      waypoints: [L.latLng(sLat, sLng), L.latLng(eLat, eLng)],
      routeWhileDragging: false,
      router: L.Routing.osrmv1({ serviceUrl: "https://router.project-osrm.org/route/v1" }),
      lineOptions: { styles: [{ color: "#ef5350", weight: 6, opacity: 0.9 }] },
      createMarker: (i, wp) => L.marker(wp.latLng, {
        icon: L.divIcon({
          className: "",
          html: `<div style="background:${i === 0 ? "#ef5350" : "#66bb6a"};width:14px;height:14px;border-radius:50%;border:3px solid white;"></div>`,
          iconSize: [14, 14], iconAnchor: [7, 7],
        }),
      }),
    }).addTo(map);

    setTimeout(() => {
      document.querySelectorAll(".leaflet-routing-container").forEach(el => el.style.display = "none");
    }, 600);

    routingRef.current.on("routesfound", async (e) => {
      const route      = e.routes[0];
      const routeCoords = route.coordinates;
      const routeName  = `${startArea.charAt(0).toUpperCase() + startArea.slice(1)} → ${endArea.charAt(0).toUpperCase() + endArea.slice(1)}`;
      const affected   = [];

      // Find signals near the route using turf
      if (window.turf) {
        const turfLine = window.turf.lineString(routeCoords.map(c => [c.lng, c.lat]));
        Object.entries(trafficData).forEach(([id, sig]) => {
          const area   = sig?.location;
          if (!area) return;
          const base   = AREA_COORDS[area] ?? [19.076, 72.877];
          const sigNum = parseInt(id.split("_")[1] ?? 1) - 1;
          const [lo, ln] = SIG_OFFSETS[sigNum] ?? [0, 0];
          const pt     = window.turf.point([base[1] + ln, base[0] + lo]);
          const dist   = window.turf.pointToLineDistance(pt, turfLine, { units: "kilometers" });
          if (dist < 0.4) affected.push(id);
        });
      }

      // Determine direction from route geometry
      const latDiff = routeCoords[routeCoords.length - 1].lat - routeCoords[0].lat;
      const lngDiff = routeCoords[routeCoords.length - 1].lng - routeCoords[0].lng;
      const dirLane = Math.abs(latDiff) > Math.abs(lngDiff)
        ? (latDiff > 0 ? "north" : "south")
        : (lngDiff > 0 ? "east" : "west");

      // Highlight affected markers red
      affected.forEach(id => {
        const el = document.getElementById(`sig-icon-${id}`);
        if (el) { el.style.background = "#ef5350"; el.style.boxShadow = "0 0 15px #ef5350"; }
      });

      map.fitBounds(window.L.polyline(routeCoords).getBounds(), { padding: [50, 50] });

      setEmergency({ active: true, name: routeName, affectedSignals: affected, directionLane: dirLane });

      // ✅ Actually override the signals on the backend
      await applyEmergencyToBackend(affected, dirLane);

      addLog("Emergency Route", `${routeName} activated. ${dirLane.toUpperCase()} → GREEN on ${affected.length} signals`);
    });
  }

  async function deactivateRoute() {
    // ✅ Reset all affected signals on backend
    if (emergency.affectedSignals.length > 0) {
      await clearEmergencyFromBackend(emergency.affectedSignals);
      addLog("Emergency Route", "Emergency cleared — signals returning to auto mode");
    }

    if (routingRef.current && mapInstance.current) {
      mapInstance.current.removeControl(routingRef.current);
      routingRef.current = null;
    }

    // Reset marker colors
    emergency.affectedSignals.forEach(id => {
      const sig = trafficData[id];
      if (!sig) return;
      const color = AREA_COLORS[sig.location] ?? "#4fc3f7";
      const el    = document.getElementById(`sig-icon-${id}`);
      if (el) { el.style.background = color; el.style.boxShadow = `0 0 8px ${color}`; }
    });

    setEmergency({ active: false, name: null, affectedSignals: [], directionLane: null });
  }

  const areas = Object.keys(AREA_COORDS);

  return (
    <div className="page-section active emergency-page">
      <div className="dashboard-panel" style={{ flex: 2 }}>
        <h3 className="panel-title">Emergency Route Management</h3>
        <div id="mapContainer" ref={mapRef} />
        <div className="emergency-controls">
          <select className="emergency-input" value={startArea} onChange={e => setStartArea(e.target.value)}>
            <option value="">Select Starting Point</option>
            {areas.map(a => <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>)}
          </select>
          <select className="emergency-input" value={endArea} onChange={e => setEndArea(e.target.value)}>
            <option value="">Select Destination</option>
            {areas.map(a => <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>)}
          </select>
          <button className="emergency-btn" onClick={activateRoute}>Activate Emergency Route</button>
        </div>
      </div>

      <div className="dashboard-panel">
        <h3 className="panel-title">🚨 ACTIVE EMERGENCY ALERT 🚨</h3>
        <div className={`alert-message-box ${emergency.active ? "blinking" : ""}`}>
          <h2>{emergency.active ? "⚠️ Emergency Mode Activated" : "No Active Emergency"}</h2>
          <p style={{ fontSize: "1rem", marginTop: "0.4rem" }}>
            {emergency.active
              ? `Route: ${emergency.name}. ${emergency.directionLane?.toUpperCase()} lane is GREEN on all affected signals.`
              : "Select a route above to activate Emergency Mode."}
          </p>
          <button className="deactivate-btn" onClick={deactivateRoute}>Deactivate Emergency Mode</button>
        </div>

        <h3 className="panel-title" style={{ marginTop: "1rem" }}>Affected Traffic Signals</h3>
        <div className="affected-signals-list">
          {!emergency.active && <p style={{ color: "#475569" }}>No emergency route active.</p>}
          {emergency.active && emergency.affectedSignals.length === 0 && (
            <p style={{ color: "#475569" }}>No signals detected along route corridor.</p>
          )}
          {emergency.active && emergency.affectedSignals.length > 0 && (
            <>
              <h4>Affected Signals ({emergency.affectedSignals.length} signals overridden):</h4>
              {emergency.affectedSignals.map(id => {
                const sig = trafficData[id];
                return (
                  <div key={id} className="affected-item">
                    <strong>{sig?.name ?? id}</strong>
                    {sig?.location && ` (${sig.location.charAt(0).toUpperCase() + sig.location.slice(1)})`}
                    {" — "}
                    <span style={{ color: "#2e7d32", fontWeight: 700 }}>
                      {emergency.directionLane?.toUpperCase()} → GREEN (backend overridden)
                    </span>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
