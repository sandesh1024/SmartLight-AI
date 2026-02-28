import { useState } from "react";
import { useTraffic } from "../context/TrafficContext";

const DIRS   = ["north", "south", "east", "west"];
const ARROWS = { north: "↑", south: "↓", east: "→", west: "←" };
const VIDEO_BASE = "http://127.0.0.1:8000/videos";

function CamFeed({ dir, count, isActive, videoId }) {
  const [videoError, setVideoError] = useState(false);

  // videoId is like "lane3" → file is "video3.mp4"
  const videoFile = videoId
    ? `video${videoId.replace("lane", "")}.mp4`
    : null;
  const videoUrl = videoFile ? `${VIDEO_BASE}/${videoFile}` : null;

  const stripes = [0,1,2,3,4,5].map((i) => ({
    animationDuration: `${1.3 + i * 0.15}s`,
    animationDelay:    `${i * 0.28}s`,
  }));

  return (
    <div className={`camera-feed ${isActive ? "active-lane" : ""}`}>

      {/* Real video if available, animated placeholder as fallback */}
      {videoUrl && !videoError ? (
        <video
          key={videoUrl}
          autoPlay muted loop playsInline
          onError={() => setVideoError(true)}
          style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: 8 }}
        >
          <source src={videoUrl} type="video/mp4" />
        </video>
      ) : (
        <div className="camera-placeholder">
          <div className="cam-road">
            {stripes.map((s, i) => (
              <div
                key={i}
                className="cam-stripe"
                style={{
                  height: "14%",
                  animationDuration: s.animationDuration,
                  animationDelay:    s.animationDelay,
                }}
              />
            ))}
          </div>
          <div className="cam-dir-arrow">{ARROWS[dir]}</div>
        </div>
      )}

      {/* Overlays */}
      <div className="cam-live">
        <span style={{
          width: 7, height: 7, borderRadius: "50%",
          background: "#00e676", display: "inline-block",
          animation: "pulse 1.5s infinite",
        }} />
        LIVE
      </div>
      <div className="cam-count">{count} VEH</div>
      <div className="cam-label">{dir.toUpperCase()} LANE</div>
      {isActive && <div className="cam-active-badge">● ACTIVE</div>}
    </div>
  );
}

export default function CameraGrid() {
  const { selectedSignal } = useTraffic();

  const counts       = selectedSignal?.vehicle_counts ?? {};
  const activeLane   = selectedSignal?.active_lane    ?? null;
  const videoMapping = selectedSignal?.video_mapping  ?? {};

  return (
    <div className="dashboard-panel" style={{ flex: "1.1" }}>
      <h3 className="panel-title">Live Camera Feeds</h3>
      <div className="camera-grid">
        {DIRS.map((dir) => (
          <CamFeed
            key={dir}
            dir={dir}
            count={counts[dir] ?? 0}
            isActive={activeLane === dir}
            videoId={videoMapping[dir] ?? null}
          />
        ))}
      </div>
    </div>
  );
}