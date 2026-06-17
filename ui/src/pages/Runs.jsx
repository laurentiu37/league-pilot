import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function Runs() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/runs");
        if (!cancelled) setRows(res.data.rows || []);
      } catch (e) {
        if (!cancelled) setErr(String(e?.response?.data?.detail || e.message));
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <h2>Runs</h2>
      {err && <p style={{ color: "crimson" }}>Error: {err}</p>}

      <div style={{ display: "grid", gap: 8 }}>
        {rows.map(r => (
          <div key={r.run_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <div>
                <div><b>Run #{r.run_id}</b> — seed: {r.seed}</div>
                <div style={{ fontSize: 13, opacity: 0.8 }}>created_at: {r.created_at}</div>
              </div>
              <div>
                <Link to={`/runs/${r.run_id}`}>Open</Link>
              </div>
            </div>
            <div style={{ marginTop: 8, fontSize: 14 }}>
              <div>Champion: <b>{r.champion}</b> | Vice: <b>{r.vice}</b></div>
              <div>Cup: <b>{r.cup_winner}</b> | Supercup: <b>{r.supercup_winner}</b></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}