import { useState, useEffect } from "react";
import { TrafficProvider, useTraffic, getLevel } from "./context/TrafficContext";

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Baloo+2:wght@400;600;700;800&display=swap');
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Nunito', sans-serif; background: #f0f7ff; color: #1e293b; min-height: 100vh; }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-thumb { background: #90caf9; border-radius: 3px; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  @keyframes slideIn { from{transform:translateX(100%);opacity:0} to{transform:translateX(0);opacity:1} }
  @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
  .tab-btn {
    flex:1; padding:0.7rem; border:none; background:transparent;
    font-family:inherit; font-weight:700; font-size:0.85rem;
    color:#94a3b8; cursor:pointer; transition:all 0.25s;
    border-bottom:3px solid transparent; white-space:nowrap;
  }
  .tab-btn.active { color:#0288d1; border-color:#0288d1; }
  .signal-card {
    background:white; border-radius:16px; padding:1rem 1.2rem; margin-bottom:0.75rem;
    border:1.5px solid #e2e8f0; box-shadow:0 2px 8px rgba(0,0,0,0.06);
    transition:all 0.25s; animation:fadeUp 0.4s ease; cursor:pointer;
  }
  .signal-card:hover { transform:translateY(-2px); box-shadow:0 6px 18px rgba(0,123,255,0.12); }
  .signal-card.high   { border-color:rgba(239,83,80,0.4);   }
  .signal-card.medium { border-color:rgba(255,167,38,0.4);  }
  .signal-card.low    { border-color:rgba(102,187,106,0.4); }
  .level-badge {
    display:inline-flex; align-items:center; gap:4px;
    padding:3px 10px; border-radius:20px;
    font-size:0.72rem; font-weight:800; letter-spacing:0.5px;
  }
  .lane-bar-bg { background:#f1f5f9; border-radius:4px; height:6px; flex:1; }
  .lane-bar-fill { height:100%; border-radius:4px; transition:width 0.5s ease; }
  .notif-item {
    background:white; border-radius:12px; padding:1rem; margin-bottom:0.6rem;
    border-left:4px solid; box-shadow:0 2px 6px rgba(0,0,0,0.05);
    animation:slideIn 0.3s ease;
  }
  .stat-card {
    background:white; border-radius:16px; padding:1.2rem;
    text-align:center; flex:1; box-shadow:0 2px 8px rgba(0,0,0,0.06);
    border:1.5px solid #e2e8f0;
  }
`;

const TYPE_STYLE = {
  high:      { color: "#ef5350", border: "#ef5350", icon: "🔴" },
  emergency: { color: "#d90429", border: "#d90429", icon: "🚨" },
  warning:   { color: "#ffa726", border: "#ffa726", icon: "⚠️" },
  alert:     { color: "#ef5350", border: "#ef5350", icon: "🚨" },
  info:      { color: "#0288d1", border: "#0288d1", icon: "📢" },
  medium:    { color: "#ffa726", border: "#ffa726", icon: "🟡" },
};

function StatusBar() {
  const { connected, reconnecting } = useTraffic();
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ background:"linear-gradient(135deg,#0d47a1,#0288d1)", color:"white", padding:"1rem 1.2rem", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
      <div>
        <div style={{ fontSize:"1.2rem", fontWeight:900, fontFamily:"'Baloo 2'" }}>🚦 SmartLight</div>
        <div style={{ fontSize:"0.72rem", opacity:0.8 }}>Mumbai Traffic Live</div>
      </div>
      <div style={{ textAlign:"right" }}>
        <div style={{ display:"inline-flex", alignItems:"center", gap:6, background:"rgba(255,255,255,0.15)", padding:"4px 10px", borderRadius:"20px", fontSize:"0.75rem", fontWeight:700, marginBottom:"0.3rem" }}>
          <span style={{ width:8, height:8, borderRadius:"50%", background: connected ? "#00e676" : reconnecting ? "#ffb300" : "#ef5350", animation: connected ? "pulse 2s infinite" : "none", display:"inline-block" }} />
          {connected ? "LIVE" : reconnecting ? "Reconnecting..." : "Offline"}
        </div>
        <div style={{ fontSize:"0.7rem", opacity:0.7 }}>{time.toLocaleTimeString("en-IN")}</div>
      </div>
    </div>
  );
}

function CityStats() {
  const { cityStats } = useTraffic();
  const stats = [
    { label:"Total Vehicles", value:cityStats.totalVehicles, color:"#0288d1" },
    { label:"🔴 High",        value:cityStats.highCount,     color:"#ef5350" },
    { label:"🟡 Medium",      value:cityStats.mediumCount,   color:"#ffa726" },
    { label:"🟢 Low",         value:cityStats.lowCount,      color:"#66bb6a" },
  ];
  return (
    <div style={{ padding:"1rem", background:"white", borderBottom:"1px solid #e2e8f0" }}>
      <div style={{ fontSize:"0.75rem", color:"#64748b", fontWeight:700, marginBottom:"0.7rem" }}>CITY OVERVIEW</div>
      <div style={{ display:"flex", gap:"0.5rem" }}>
        {stats.map(s => (
          <div key={s.label} className="stat-card" style={{ padding:"0.7rem 0.4rem" }}>
            <div style={{ fontSize:"1.4rem", fontWeight:900, color:s.color }}>{s.value}</div>
            <div style={{ fontSize:"0.65rem", color:"#94a3b8", fontWeight:700, marginTop:2 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LaneBar({ dir, count, maxCount }) {
  const pct   = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
  const color = count >= 10 ? "#ef5350" : count >= 5 ? "#ffa726" : "#66bb6a";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:"0.5rem", marginBottom:4 }}>
      <span style={{ fontSize:"0.7rem", color:"#64748b", fontWeight:700, width:36 }}>
        {dir.charAt(0).toUpperCase() + dir.slice(1)}
      </span>
      <div className="lane-bar-bg">
        <div className="lane-bar-fill" style={{ width:`${pct}%`, background:color }} />
      </div>
      <span style={{ fontSize:"0.72rem", fontWeight:800, color, width:24, textAlign:"right" }}>{count}</span>
    </div>
  );
}

function SignalCard({ signal, onClick }) {
  const { level, vehicle_counts, name, active_lane, phase, timer, emergency } = signal;
  const counts   = vehicle_counts ?? {};
  const maxCount = Math.max(...Object.values(counts), 1);
  return (
    <div className={`signal-card ${level.label.toLowerCase()}`} onClick={onClick}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"0.7rem" }}>
        <div>
          <div style={{ fontWeight:800, fontSize:"0.95rem", color:"#1e293b" }}>{name}</div>
          <div style={{ fontSize:"0.72rem", color:"#94a3b8", marginTop:2 }}>
            {active_lane ? `${active_lane.toUpperCase()} ${phase} · ${timer}s` : "Initializing..."}
          </div>
        </div>
        <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:4 }}>
          <span className="level-badge" style={{ background:level.bg, color:level.color }}>
            {level.emoji} {level.label}
          </span>
          {emergency && (
            <span className="level-badge" style={{ background:"rgba(239,83,80,0.1)", color:"#ef5350", fontSize:"0.65rem" }}>
              🚨 EMERGENCY
            </span>
          )}
        </div>
      </div>
      <div>
        {["north","south","east","west"].map(dir => (
          <LaneBar key={dir} dir={dir} count={counts[dir] ?? 0} maxCount={maxCount} />
        ))}
      </div>
      <div style={{ marginTop:"0.6rem", textAlign:"right", fontSize:"0.72rem", color:"#94a3b8", fontWeight:600 }}>
        Total: <strong style={{ color:level.color }}>{signal.total} vehicles</strong>
      </div>
    </div>
  );
}

function SignalDetail({ signal, onClose }) {
  if (!signal) return null;
  const counts = signal.vehicle_counts ?? {};
  const level  = signal.level;
  return (
    <div style={{ position:"fixed", inset:0, zIndex:1000, background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)", display:"flex", alignItems:"flex-end" }} onClick={onClose}>
      <div style={{ background:"white", borderRadius:"24px 24px 0 0", padding:"1.5rem", width:"100%", maxHeight:"80vh", overflowY:"auto", animation:"slideIn 0.3s ease" }} onClick={e => e.stopPropagation()}>
        <div style={{ width:40, height:4, background:"#e2e8f0", borderRadius:2, margin:"0 auto 1.2rem" }} />
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1rem" }}>
          <div>
            <h2 style={{ fontSize:"1.2rem", fontWeight:900, color:"#0d47a1" }}>{signal.name}</h2>
            <p style={{ color:"#64748b", fontSize:"0.8rem", textTransform:"capitalize" }}>{signal.location}</p>
          </div>
          <span className="level-badge" style={{ background:level.bg, color:level.color, fontSize:"0.85rem" }}>
            {level.emoji} {level.label}
          </span>
        </div>
        <div style={{ background:"#f0f7ff", borderRadius:12, padding:"0.8rem 1rem", marginBottom:"1rem", display:"flex", justifyContent:"space-between" }}>
          {[
            { label:"Active Lane", value: signal.active_lane?.toUpperCase() ?? "—", color:"#0288d1" },
            { label:"Phase",       value: signal.phase ?? "—",                       color: signal.phase==="GREEN"?"#66bb6a":signal.phase==="YELLOW"?"#ffa726":"#ef5350" },
            { label:"Timer",       value: `${signal.timer ?? 0}s`,                   color:"#0d47a1" },
            { label:"Vehicles",    value: signal.total,                               color:level.color },
          ].map(item => (
            <div key={item.label} style={{ textAlign:"center" }}>
              <div style={{ fontSize:"1.4rem", fontWeight:900, color:item.color }}>{item.value}</div>
              <div style={{ fontSize:"0.7rem", color:"#64748b", fontWeight:700 }}>{item.label}</div>
            </div>
          ))}
        </div>
        <h3 style={{ fontSize:"0.85rem", fontWeight:800, color:"#0d47a1", marginBottom:"0.7rem" }}>Lane Breakdown</h3>
        {["north","south","east","west"].map(dir => {
          const count = counts[dir] ?? 0;
          const lvl   = getLevel(count * 3);
          return (
            <div key={dir} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0.7rem 1rem", background:lvl.bg, borderRadius:10, marginBottom:"0.5rem", border:`1px solid ${lvl.color}33` }}>
              <span style={{ fontWeight:700, textTransform:"capitalize", color:"#1e293b" }}>{dir}</span>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontWeight:800, fontSize:"1.1rem", color:lvl.color }}>{count}</span>
                <span>{lvl.emoji}</span>
              </div>
            </div>
          );
        })}
        {signal.lane_timings && Object.keys(signal.lane_timings).length > 0 && (
          <>
            <h3 style={{ fontSize:"0.85rem", fontWeight:800, color:"#0d47a1", margin:"1rem 0 0.7rem" }}>Planned Green Time</h3>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0.5rem" }}>
              {Object.entries(signal.lane_timings).map(([lane, secs]) => (
                <div key={lane} style={{ background:"#f0f7ff", borderRadius:10, padding:"0.6rem 0.8rem", display:"flex", justifyContent:"space-between" }}>
                  <span style={{ fontWeight:700, textTransform:"capitalize", fontSize:"0.85rem" }}>{lane}</span>
                  <span style={{ fontWeight:800, color:"#0288d1", fontSize:"0.85rem" }}>{secs}s</span>
                </div>
              ))}
            </div>
          </>
        )}
        <button onClick={onClose} style={{ width:"100%", marginTop:"1.2rem", padding:"0.9rem", background:"linear-gradient(45deg,#0288d1,#0d47a1)", color:"white", border:"none", borderRadius:12, fontWeight:800, fontSize:"1rem", fontFamily:"inherit", cursor:"pointer" }}>
          Close
        </button>
      </div>
    </div>
  );
}

function TrafficTab() {
  const { signalsByLocation, trafficData } = useTraffic();
  const [filter, setFilter]   = useState("all");
  const [selected, setSelected] = useState(null);
  const locations  = Object.keys(signalsByLocation);
  const allSignals = Object.values(signalsByLocation).flat();
  const displayed  = filter === "all"    ? allSignals
    : filter === "high"   ? allSignals.filter(s => s.level.label === "HIGH")
    : filter === "medium" ? allSignals.filter(s => s.level.label === "MEDIUM")
    : filter === "low"    ? allSignals.filter(s => s.level.label === "LOW")
    : (signalsByLocation[filter] ?? []);
  return (
    <>
      <div style={{ background:"white", borderBottom:"1px solid #e2e8f0", overflowX:"auto" }}>
        <div style={{ display:"flex", minWidth:"max-content", padding:"0 0.5rem" }}>
          {["all","high","medium","low",...locations].map(f => (
            <button key={f} className={`tab-btn ${filter===f?"active":""}`} onClick={() => setFilter(f)}>
              {f==="all"?"All":f==="high"?"🔴 High":f==="medium"?"🟡 Medium":f==="low"?"🟢 Low":f.charAt(0).toUpperCase()+f.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div style={{ padding:"1rem", overflowY:"auto", flex:1 }}>
        {displayed.length === 0 && (
  <div style={{ textAlign:"center", padding:"3rem 1rem", color:"#94a3b8" }}>
    <div style={{ fontSize:"2.5rem", marginBottom:"0.5rem" }}>
      {Object.keys(trafficData).length === 0 ? "⏳" : "🔍"}
    </div>
    <p style={{ fontWeight:700 }}>
      {Object.keys(trafficData).length === 0
        ? "Connecting to backend..."
        : "No signals in this category"}
    </p>
  </div>
)}
        {displayed.map(sig => (
          <SignalCard key={sig.id} signal={sig} onClick={() => setSelected(sig)} />
        ))}
      </div>
      {selected && <SignalDetail signal={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function AlertsTab() {
  const { notifications } = useTraffic();

  return (
    <div style={{ padding:"1rem", overflowY:"auto", flex:1 }}>
      {notifications.length === 0 && (
        <div style={{ textAlign:"center", padding:"3rem 1rem", color:"#94a3b8" }}>
          <div style={{ fontSize:"2.5rem", marginBottom:"0.5rem" }}>✅</div>
          <p style={{ fontWeight:700 }}>No alerts right now</p>
          <p style={{ fontSize:"0.8rem", marginTop:"0.3rem" }}>All signals operating normally</p>
        </div>
      )}
      {notifications.map(n => {
        const s = TYPE_STYLE[n.type] ?? TYPE_STYLE.info;

        // ✅ Handle both admin notifications (title+area) and auto notifications (signal+location)
        const heading  = n.title    ?? n.signal   ?? "System Alert";
        const location = n.area     ?? n.location ?? "";
        const time     = n.timestamp ?? n.time    ?? "";

        return (
          <div key={n.id} className="notif-item" style={{ borderColor: s.border }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"0.4rem" }}>
              <span style={{ fontWeight:800, color:s.color, fontSize:"0.88rem" }}>
                {s.icon} {heading}
              </span>
              <span style={{ fontSize:"0.7rem", color:"#94a3b8", whiteSpace:"nowrap", marginLeft:"0.5rem" }}>
                {time}
              </span>
            </div>
            <p style={{ fontSize:"0.82rem", color:"#475569", marginBottom:"0.3rem" }}>
              {n.message}
            </p>
            {location && (
              <p style={{ fontSize:"0.72rem", color:"#94a3b8", textTransform:"capitalize" }}>
                📍 {location === "all" ? "All Areas" : location}
              </p>
            )}
            {n.source === "admin" && (
              <span style={{ fontSize:"0.65rem", background:"rgba(2,136,209,0.1)", color:"#0288d1", padding:"2px 6px", borderRadius:"8px", fontWeight:700 }}>
                From Traffic Authority
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function AboutTab() {
  return (
    <div style={{ padding:"1.5rem", overflowY:"auto", flex:1 }}>
      <div style={{ textAlign:"center", marginBottom:"1.5rem" }}>
        <div style={{ fontSize:"4rem" }}>🚦</div>
        <h1 style={{ fontFamily:"'Baloo 2'", color:"#0d47a1", fontWeight:800 }}>SmartLight AI</h1>
        <p style={{ color:"#64748b", fontSize:"0.9rem" }}>AI-powered adaptive traffic control</p>
      </div>
      {[
        { icon:"🤖", title:"AI-Powered",      desc:"YOLOv8 computer vision counts vehicles in real time" },
        { icon:"⚡", title:"Adaptive Signals", desc:"Signal timings adjust every cycle based on live vehicle counts" },
        { icon:"🗺️", title:"20 Signals",       desc:"Covering Bandra, Worli, Dadar, Andheri & Churchgate" },
        { icon:"📱", title:"Public Access",    desc:"Live traffic levels accessible to everyone, no login needed" },
        { icon:"🚨", title:"Emergency Routes", desc:"Priority signal override for emergency vehicles" },
      ].map(item => (
        <div key={item.title} style={{ background:"white", borderRadius:14, padding:"1rem", marginBottom:"0.75rem", display:"flex", gap:"1rem", border:"1.5px solid #e2e8f0", boxShadow:"0 2px 6px rgba(0,0,0,0.05)" }}>
          <span style={{ fontSize:"1.8rem" }}>{item.icon}</span>
          <div>
            <div style={{ fontWeight:800, color:"#0d47a1", marginBottom:"0.2rem" }}>{item.title}</div>
            <div style={{ fontSize:"0.82rem", color:"#64748b" }}>{item.desc}</div>
          </div>
        </div>
      ))}
      <div style={{ background:"linear-gradient(135deg,#0d47a1,#0288d1)", borderRadius:14, padding:"1rem", color:"white", textAlign:"center", marginTop:"1rem" }}>
        <p style={{ fontWeight:700, fontSize:"0.85rem" }}>Traffic Authority?</p>
        <a href="http://localhost:5173" style={{ display:"inline-block", marginTop:"0.5rem", background:"rgba(255,255,255,0.2)", color:"white", padding:"0.4rem 1rem", borderRadius:"20px", fontSize:"0.8rem", fontWeight:700, textDecoration:"none" }}>
          Admin Login →
        </a>
      </div>
    </div>
  );
}

function PublicApp() {
  const [tab, setTab] = useState("traffic");
  const tabs = [
    { id:"traffic", label:"🚦 Traffic" },
    { id:"alerts",  label:"🔔 Alerts"  },
    { id:"about",   label:"ℹ️ About"   },
  ];
  return (
    <div style={{ maxWidth:480, margin:"0 auto", minHeight:"100vh", display:"flex", flexDirection:"column", background:"#f0f7ff", boxShadow:"0 0 40px rgba(0,0,0,0.1)" }}>
      <StatusBar />
      {tab === "traffic" && <CityStats />}
      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
        {tab === "traffic" && <TrafficTab />}
        {tab === "alerts"  && <AlertsTab  />}
        {tab === "about"   && <AboutTab   />}
      </div>
      <div style={{ background:"white", borderTop:"1px solid #e2e8f0", display:"flex", position:"sticky", bottom:0, paddingBottom:"env(safe-area-inset-bottom)" }}>
        {tabs.map(t => (
          <button key={t.id} className={`tab-btn ${tab===t.id?"active":""}`} onClick={() => setTab(t.id)} style={{ fontSize:"0.9rem", padding:"0.9rem 0" }}>
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <style>{css}</style>
      <TrafficProvider>
        <PublicApp />
      </TrafficProvider>
    </>
  );
}