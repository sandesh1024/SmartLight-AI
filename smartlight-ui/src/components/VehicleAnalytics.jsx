import { useEffect, useRef } from "react";
import { useTraffic } from "../context/TrafficContext";

const DIRS = ["north", "south", "east", "west"];

export default function VehicleAnalytics() {
  const { selectedSignal } = useTraffic();
  const counts = selectedSignal?.vehicle_counts ?? { north: 0, south: 0, east: 0, west: 0 };

  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  // Init chart once
  useEffect(() => {
    if (!chartRef.current) return;
    const ctx = chartRef.current.getContext("2d");

    // Load Chart.js from CDN dynamically
    if (!window.Chart) {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js";
      script.onload = () => initChart(ctx);
      document.head.appendChild(script);
    } else {
      initChart(ctx);
    }

    function initChart(ctx) {
      chartInstance.current = new window.Chart(ctx, {
        type: "line",
        data: {
          labels: [],
          datasets: [
            { label: "North Lane", data: [], borderColor: "#ef5350", backgroundColor: "rgba(239,83,80,0.15)", tension: 0.4 },
            { label: "South Lane", data: [], borderColor: "#26a69a", backgroundColor: "rgba(38,166,154,0.15)", tension: 0.4 },
            { label: "East Lane",  data: [], borderColor: "#ffa726", backgroundColor: "rgba(255,167,38,0.15)", tension: 0.4 },
            { label: "West Lane",  data: [], borderColor: "#5c6bc0", backgroundColor: "rgba(92,107,192,0.15)", tension: 0.4 },
          ],
        },
        options: {
          plugins: { legend: { labels: { color: "#1e293b" } } },
          scales: {
            x: { title: { display: true, text: "Time", color: "#0d47a1" }, ticks: { color: "#475569" }, grid: { color: "#bbdefb" } },
            y: { title: { display: true, text: "Vehicles", color: "#0d47a1" }, beginAtZero: true, ticks: { color: "#475569" }, grid: { color: "#bbdefb" } },
          },
          responsive: true,
          maintainAspectRatio: false,
        },
      });
    }

    return () => { chartInstance.current?.destroy(); };
  }, []);

  // Push data when counts change
  useEffect(() => {
    if (!chartInstance.current) return;
    const now = new Date();
    const label = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
    const chart = chartInstance.current;

    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(counts.north ?? 0);
    chart.data.datasets[1].data.push(counts.south ?? 0);
    chart.data.datasets[2].data.push(counts.east  ?? 0);
    chart.data.datasets[3].data.push(counts.west  ?? 0);

    // Keep last 30 points
    if (chart.data.labels.length > 30) {
      chart.data.labels.shift();
      chart.data.datasets.forEach((ds) => ds.data.shift());
    }
    chart.update("none");
  }, [counts.north, counts.south, counts.east, counts.west]);

  return (
    <div className="dashboard-panel">
      <h3 className="panel-title">Vehicle Counts &amp; Analytics</h3>
      <div className="vehicle-counts">
        {DIRS.map((dir) => (
          <div key={dir} className="lane-card">
            <div className="lane-name">{dir.charAt(0).toUpperCase() + dir.slice(1)} Lane</div>
            <div className={`vehicle-count ${(counts[dir] ?? 0) > 10 ? "pulsing" : ""}`}>
              {counts[dir] ?? 0}
            </div>
          </div>
        ))}
      </div>
      <div className="chart-container">
        <canvas ref={chartRef} />
      </div>
    </div>
  );
}