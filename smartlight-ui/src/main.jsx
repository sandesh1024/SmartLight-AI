import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { TrafficProvider } from "./context/TrafficContext";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <TrafficProvider>
        <App />
      </TrafficProvider>
    </AuthProvider>
  </React.StrictMode>
);