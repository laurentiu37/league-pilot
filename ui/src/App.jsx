import { Routes, Route, Navigate } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import Simulate from "./pages/Simulate.jsx";
import Runs from "./pages/Runs.jsx";
import RunDetails from "./pages/RunDetails.jsx";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <Nav />
      <Routes>
        <Route path="/" element={<Navigate to="/simulate" replace />} />
        <Route path="/simulate" element={<Simulate />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/runs/:runId" element={<RunDetails />} />
      </Routes>
    </div>
  );
}