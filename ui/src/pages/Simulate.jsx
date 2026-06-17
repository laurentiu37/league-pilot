import { useState } from "react";
import { api } from "../api/client";

const defaultTimeSlots = [
  "17:00","17:15","17:30","17:45",
  "18:00","18:15","18:30","18:45",
  "19:00","19:15","19:30","19:45",
  "20:00","20:15","20:30","20:45","21:00"
];

export default function Simulate() {
  const [seed, setSeed] = useState("");
  const [tvFeaturedPerRound, setTvFeaturedPerRound] = useState(1);
  const [tvRequestedTime, setTvRequestedTime] = useState("");
  const [timeSlots, setTimeSlots] = useState(defaultTimeSlots.join(","));
  const [tvAllowedTimes, setTvAllowedTimes] = useState(""); // optional

  const [pCovid, setPCovid] = useState(0.05);
  const [pVenueBlock, setPVenueBlock] = useState(0.03);
  const [pConcert, setPConcert] = useState(0.18);
  const [pInjury, setPInjury] = useState(0.06);
  const [pCallup, setPCallup] = useState(0.12);
  const [pCovidOutbreak, setPCovidOutbreak] = useState(0.04);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const parseCsvTimes = (s) =>
    s.split(",").map(x => x.trim()).filter(Boolean);

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setResult(null);
    setLoading(true);

    try {
      const body = {
        seed: seed.trim() ? Number(seed) : null,
        tv_featured_per_round: Number(tvFeaturedPerRound),
        time_slots: parseCsvTimes(timeSlots),
        tv_requested_time: tvRequestedTime.trim() ? tvRequestedTime.trim() : null,
        tv_allowed_times: tvAllowedTimes.trim() ? parseCsvTimes(tvAllowedTimes) : null,

        p_covid_per_round: Number(pCovid),
        p_venue_block_per_round: Number(pVenueBlock),
        p_concert_per_round: Number(pConcert),
        p_injury_per_round: Number(pInjury),
        p_callup_per_round: Number(pCallup),
        p_covid_player_outbreak_per_round: Number(pCovidOutbreak),
      };

      const res = await api.post("/simulate", body);
      setResult(res.data);
    } catch (e2) {
      const msg = e2?.response?.data?.detail || e2.message || "Unknown error";
      setErr(String(msg));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>Simulate season</h2>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 10 }}>
          <label>Seed (optional)</label>
          <input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="e.g. 123" />

          <label>TV featured per round</label>
          <input type="number" min="0" value={tvFeaturedPerRound} onChange={(e) => setTvFeaturedPerRound(e.target.value)} />

          <label>TV requested time (optional)</label>
          <input value={tvRequestedTime} onChange={(e) => setTvRequestedTime(e.target.value)} placeholder="HH:MM (e.g. 20:00)" />

          <label>Time slots (CSV)</label>
          <input value={timeSlots} onChange={(e) => setTimeSlots(e.target.value)} />

          <label>TV allowed times (CSV, optional)</label>
          <input value={tvAllowedTimes} onChange={(e) => setTvAllowedTimes(e.target.value)} placeholder="e.g. 19:30,20:00,20:30" />
        </div>

        <h3 style={{ marginTop: 10 }}>Dynamic events probabilities</h3>
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 10 }}>
          <label>p_covid_per_round</label>
          <input type="number" step="0.01" value={pCovid} onChange={(e) => setPCovid(e.target.value)} />
          <label>p_venue_block_per_round</label>
          <input type="number" step="0.01" value={pVenueBlock} onChange={(e) => setPVenueBlock(e.target.value)} />
          <label>p_concert_per_round</label>
          <input type="number" step="0.01" value={pConcert} onChange={(e) => setPConcert(e.target.value)} />
          <label>p_injury_per_round</label>
          <input type="number" step="0.01" value={pInjury} onChange={(e) => setPInjury(e.target.value)} />
          <label>p_callup_per_round</label>
          <input type="number" step="0.01" value={pCallup} onChange={(e) => setPCallup(e.target.value)} />
          <label>p_covid_player_outbreak_per_round</label>
          <input type="number" step="0.01" value={pCovidOutbreak} onChange={(e) => setPCovidOutbreak(e.target.value)} />
        </div>

        <button disabled={loading} style={{ width: 220, padding: 10 }}>
          {loading ? "Simulating..." : "Run simulation"}
        </button>
      </form>

      {err && <p style={{ color: "crimson", marginTop: 12 }}>Error: {err}</p>}

      {result && (
        <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
          <div><b>Run ID:</b> {result.run_id}</div>
          <div><b>Seed:</b> {result.seed}</div>
          <div style={{ marginTop: 8 }}>{result.message}</div>
        </div>
      )}
    </div>
  );
}