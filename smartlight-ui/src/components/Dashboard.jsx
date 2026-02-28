import CameraGrid from "./CameraGrid";
import SignalLights from "./SignalLights";
import VehicleAnalytics from "./VehicleAnalytics";
import ManualControls from "./ManualControls";
import TrafficLog from "./TrafficLog";

export default function Dashboard({ addLog }) {
  return (
    <div className="page-section active">

      {/* Row 1 — Camera feeds + Signal lights */}
      <div className="dashboard-row">
        <CameraGrid />
        <SignalLights />
      </div>

      {/* Row 2 — Analytics + Manual controls */}
      <div className="dashboard-row">
        <VehicleAnalytics />
        <ManualControls addLog={addLog} />
      </div>

      {/* Row 3 — Traffic log */}
      <div className="dashboard-row">
        <TrafficLog />
      </div>

    </div>
  );
}