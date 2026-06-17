import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export default function RunDetails() {
  const { runId } = useParams();

  const [tab, setTab] = useState("games");
  const [summary, setSummary] = useState(null);

  const [games, setGames] = useState([]);
  const [players, setPlayers] = useState([]);
  const [events, setEvents] = useState("");

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const tabs = useMemo(
    () => [
      { id: "games", label: "Games" },
      { id: "players", label: "Players avg" },
      { id: "events", label: "Events" },
    ],
    []
  );

  // Summary
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setErr("");
      try {
        const res = await api.get(`/runs/${runId}/summary`);
        if (!cancelled) setSummary(res.data);
      } catch (e) {
        if (!cancelled) setErr(String(e?.response?.data?.detail || e.message));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Tab data
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setErr("");
      setLoading(true);
      try {
        if (tab === "games") {
          const res = await api.get(`/runs/${runId}/games`);
          if (!cancelled) setGames(res.data.rows || []);
        } else if (tab === "players") {
          const res = await api.get(`/runs/${runId}/players-avg`);
          if (!cancelled) setPlayers(res.data.rows || []);
        } else if (tab === "events") {
          const res = await api.get(`/runs/${runId}/events`);
          if (!cancelled) setEvents(res.data.log || "");
        }
      } catch (e) {
        if (!cancelled) setErr(String(e?.response?.data?.detail || e.message));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId, tab]);

  return (
    <div>
      <h2>Run #{runId}</h2>

      {err && <p style={{ color: "crimson" }}>Error: {err}</p>}

      {summary && (
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 10, marginBottom: 12 }}>
          <div><b>Seed:</b> {summary.seed}</div>
          <div><b>Created:</b> {summary.created_at}</div>
          <div><b>Champion:</b> {summary.champion} | <b>Vice:</b> {summary.vice}</div>
          <div><b>Cup:</b> {summary.cup_winner} | <b>Supercup:</b> {summary.supercup_winner}</div>
          <div><b>Games count:</b> {summary.games_count}</div>
        </div>
      )}

            {/* EXPORT DOWNLOADS */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <a
          href={`${API_BASE}/runs/${runId}/export/games.csv`}
          target="_blank"
          rel="noreferrer"
        >
          Download games.csv
        </a>

        <a
          href={`${API_BASE}/runs/${runId}/export/players_avg.csv`}
          target="_blank"
          rel="noreferrer"
        >
          Download players_avg.csv
        </a>

        <a
          href={`${API_BASE}/runs/${runId}/export/events.txt`}
          target="_blank"
          rel="noreferrer"
        >
          Download events.txt
        </a>

        <a href={`${API_BASE}/runs/${runId}/export/regular_standings.csv`} target="_blank" rel="noreferrer">
          Download regular_standings.csv
        </a>

        <a href={`${API_BASE}/runs/${runId}/export/final_order.csv`} target="_blank" rel="noreferrer">
          Download final_order.csv
        </a>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #ddd",
              background: tab === t.id ? "#eee" : "white",
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div style={{ opacity: 0.8 }}>Loading...</div>}

      {tab === "games" && (
        <div style={{ display: "grid", gap: 8 }}>
          {games.map((g, idx) => (
            <div key={idx} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 10 }}>
              <div style={{ fontWeight: 700 }}>
                {g.stage} — {g.label}
              </div>
              <div style={{ fontSize: 14, marginTop: 4 }}>
                {g.date} {g.time} • {g.home} {g.home_score}-{g.away_score} {g.away} • {g.venue}
              </div>
              <div style={{ fontSize: 13, marginTop: 6, opacity: 0.85 }}>
                TV: {String(g.tv_featured)} | requested: {g.tv_requested_time ?? "-"} | confirmed: {String(g.tv_confirmed)}
              </div>
              {g.notes && (
                <div style={{ marginTop: 6, fontSize: 13 }}>
                  <b>Notes:</b> {g.notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "players" && (
        <div style={{ display: "grid", gap: 8 }}>
          {players.map((p, idx) => (
            <div key={idx} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 10 }}>
              <div style={{ fontWeight: 700 }}>
                {p.player_name} ({p.position}) — {p.team}
              </div>
              <div style={{ fontSize: 13, opacity: 0.85 }}>
                Competition: {p.competition} | GP: {p.games_played}
              </div>
              <div style={{ marginTop: 6 }}>
                PTS {p.pts_avg} • REB {p.reb_avg} • AST {p.ast_avg} • MIN {p.min_avg}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "events" && (
        <pre style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
          {events || "(no events)"}
        </pre>
      )}
    </div>
  );
}