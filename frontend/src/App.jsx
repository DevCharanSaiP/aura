import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";
function App() {
  
  const [fleet, setFleet] = useState([]);
  const [mode, setMode] = useState("user"); // "user" | "service" | "mfg"
  const [vehicleId, setVehicleId] = useState("V001");
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [contactDecision, setContactDecision] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [engagementLoading, setEngagementLoading] = useState(false);
  const [engagementError, setEngagementError] = useState("");
  const [schedule, setSchedule] = useState(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState("");
  const [mfgSummary, setMfgSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchFleet() {
    try {
      const [fleetRes, mfgRes] = await Promise.all([
        fetch(`${API_BASE}/vehicles`),
        fetch(`${API_BASE}/mfg/summary`),
      ]);
      const fleetJson = await fleetRes.json();
      const mfgJson = await mfgRes.json();
      setFleet(fleetJson.vehicles || []);
      setMfgSummary(mfgJson);
    } catch (e) {
      console.error(e);
    }
  }

  async function triggerEngagement(id) {
    try {
      setEngagementLoading(true);
      setEngagementError("");
      setEngagement(null);

      const res = await fetch("http://127.0.0.1:8200/simulate_call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_id: id,
          owner_name: "Techathon User",
          phone: "+91XXXXXXXXXX",
        }),
      });

      const json = await res.json();
      setEngagement(json);
    } catch (e) {
      console.error(e);
      setEngagementError("Failed to contact Customer Agent");
    } finally {
      setEngagementLoading(false);
    }
  }

  async function triggerSchedule(id) {
    try {
      setScheduleLoading(true);
      setScheduleError("");
      setSchedule(null);

      const res = await fetch("http://127.0.0.1:8300/propose_slots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_id: id,
          owner_name: "Techathon User",
        }),
      });

      const json = await res.json();
      setSchedule(json);
    } catch (e) {
      console.error(e);
      setScheduleError("Failed to contact Scheduling Agent");
    } finally {
      setScheduleLoading(false);
    }
  }

  async function fetchData(id) {
    try {
      setLoading(true);
      setError("");
      const [healthRes, histRes, contactRes] = await Promise.all([
        fetch(`${API_BASE}/health/${id}`),
        fetch(`${API_BASE}/history/${id}?limit=20`),
        fetch(`${API_BASE}/contact_decision/${id}`),
      ]);

      const healthJson = await healthRes.json();
      const histJson = await histRes.json();
      const contactJson = await contactRes.json();

      setHealth(healthJson);
      setHistory(histJson.points || []);
      setContactDecision(contactJson);
    } catch (e) {
      console.error(e);
      setError("Failed to load data from backend");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData(vehicleId);
    fetchFleet();
    const interval = setInterval(() => {
      fetchData(vehicleId);
      fetchFleet();
  }, 3000);
    return () => clearInterval(interval);
  }, [vehicleId]);

  // Keep health parsing inside UserView so views remain self-contained

  return (
    <div style={{ padding: "1.5rem 2rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem", color: "#e5e7eb" }}>
        AURA Prototype Dashboard
      </h1>
      <p style={{ marginBottom: "1rem", color: "#9ca3af" }}>
        Live vehicle health from Master Agent (V001–V010).
      </p>
      {/* Role switcher */}
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
        {[
          { id: "user", label: "Car Owner" },
          { id: "service", label: "Service Center" },
          { id: "mfg", label: "Manufacturing" },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            style={{
              padding: "0.35rem 0.75rem",
              borderRadius: "999px",
              border: mode === m.id ? "2px solid #e5e7eb" : "1px solid #4b5563",
              background: mode === m.id ? "#111827" : "#020617",
              color: "#e5e7eb",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === "user" && (
        <UserView
          vehicleId={vehicleId}
          setVehicleId={setVehicleId}
          fleet={fleet}
          health={health}
          history={history}
          contactDecision={contactDecision}
          engagement={engagement}
          triggerEngagement={triggerEngagement}
          engagementLoading={engagementLoading}
          engagementError={engagementError}
          schedule={schedule}
          triggerSchedule={triggerSchedule}
          scheduleLoading={scheduleLoading}
          scheduleError={scheduleError}
          loading={loading}
          error={error}
        />
      )}

      {mode === "service" && <ServiceCenterView fleet={fleet} />}

      {mode === "mfg" && <ManufacturingView summary={mfgSummary} />}
    </div>
  );
}

function UserView(props) {
  const {
    vehicleId,
    setVehicleId,
    fleet,
    health,
    history,
    contactDecision,
    engagement,
    triggerEngagement,
    engagementLoading,
    engagementError,
    schedule,
    triggerSchedule,
    scheduleLoading,
    scheduleError,
    loading,
    error,
  } = props;

  const current = health && health.health ? JSON.parse(health.health) : null;

  return (
    <div>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Vehicle ID:&nbsp;
          <select
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
            style={{
              padding: "0.25rem 0.5rem",
              borderRadius: "0.375rem",
              border: "1px solid #4b5563",
              background: "#020617",
              color: "#e5e7eb",
            }}
          >
            {Array.from({ length: 10 }).map((_, i) => {
              const num = i + 1;
              const id = `V${num.toString().padStart(3, "0")}`;
              return (
                <option key={id} value={id}>
                  {id}
                </option>
              );
            })}
          </select>
        </label>
      </div>

      {loading && (
        <div style={{ marginBottom: "0.5rem", color: "#e5e7eb" }}>Loading…</div>
      )}
      {error && (
        <div style={{ marginBottom: "0.5rem", color: "#f97373" }}>{error}</div>
      )}

      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* Fleet overview */}
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "1rem",
            borderRadius: "0.75rem",
            background: "#020617",
            border: "1px solid #1f2937",
            minWidth: "220px",
          }}
        >
          <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Fleet Overview</h2>
          {fleet.length === 0 ? (
            <p style={{ fontSize: "0.9rem", color: "#9ca3af" }}>No vehicles yet.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "0.5rem" }}>
              {fleet.map((v) => {
                let bg = "#064e3b";
                if (v.status === "warning") bg = "#78350f";
                if (v.status === "critical") bg = "#7f1d1d";
                const selected = v.vehicle_id === vehicleId;
                return (
                  <button
                    key={v.vehicle_id}
                    onClick={() => setVehicleId(v.vehicle_id)}
                    style={{ textAlign: "left", padding: "0.5rem 0.6rem", borderRadius: "0.5rem", border: selected ? "2px solid #e5e7eb" : "1px solid #1f2937", background: bg, color: "#e5e7eb", cursor: "pointer", fontSize: "0.85rem" }}
                  >
                    <div style={{ fontWeight: 600 }}>{v.vehicle_id}</div>
                    <div style={{ fontSize: "0.8rem" }}>
                      Anom: {v.anomaly_score !== null && v.anomaly_score !== undefined ? v.anomaly_score.toFixed(2) : "--"}
                    </div>
                    <div style={{ fontSize: "0.75rem", textTransform: "capitalize", color: "#e5e7eb" }}>{v.status}</div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Main column: current health, contact decision, engagement, schedule, history */}
        <div style={{ flex: "1 1 520px", minWidth: "320px" }}>
          {/* Current health card */}
          <div style={{ padding: "1rem", borderRadius: "0.75rem", background: current && current.anomaly_score > 0.5 ? "#7f1d1d" : current && current.anomaly_score > 0.25 ? "#78350f" : "#064e3b", minWidth: "260px" }}>
            <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Current Health – {vehicleId}</h2>
            {current ? (
              <>
                <p style={{ marginBottom: "0.25rem" }}>Anomaly score: <strong>{current.anomaly_score.toFixed(2)}</strong></p>
                <p style={{ marginBottom: "0.25rem" }}>Brakes: <strong>{current.subsystems.brakes?.toFixed(2)}</strong></p>
                <p style={{ marginBottom: "0.25rem" }}>Engine: <strong>{current.subsystems.engine?.toFixed(2)}</strong></p>
                <p style={{ marginBottom: "0.25rem" }}>Suspension: <strong>{current.subsystems.suspension?.toFixed(2)}</strong></p>
              </>
            ) : (
              <p>No data yet.</p>
            )}
          </div>

          {/* Proactive contact decision */}
          <div style={{ marginTop: "0.75rem", padding: "0.75rem 1rem", borderRadius: "0.75rem", background: "#111827", minWidth: "260px" }}>
            <h3 style={{ fontWeight: 600, marginBottom: "0.35rem", fontSize: "0.95rem" }}>Proactive Contact Decision</h3>
            {!contactDecision ? (
              <p style={{ fontSize: "0.85rem", color: "#9ca3af" }}>No decision yet.</p>
            ) : (
              <>
                <p style={{ fontSize: "0.85rem", marginBottom: "0.25rem" }}>Should contact: <strong>{contactDecision.should_contact ? "Yes" : "No"}</strong></p>
                <p style={{ fontSize: "0.85rem", color: "#9ca3af" }}>Reason: {contactDecision.reason}</p>
                {contactDecision.severity && <p style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Severity: {contactDecision.severity}</p>}
              </>
            )}
          </div>

          {/* Engagement + Scheduling panels */}
          <div style={{ display: "flex", gap: "1rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 260px", minWidth: "260px" }}>
              {/* Customer Engagement Simulation (same as before) */}
              <div style={{ padding: "0.75rem 1rem", borderRadius: "0.75rem", background: "#020617", border: "1px solid #1f2937" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                  <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>Customer Engagement Script</h3>
                  <button onClick={() => triggerEngagement(vehicleId)} disabled={engagementLoading} style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", borderRadius: "0.375rem", border: "1px solid #4b5563", background: "#111827", color: "#e5e7eb", cursor: "pointer" }}>{engagementLoading ? "Generating…" : "Simulate Call"}</button>
                </div>
                {engagementError && <p style={{ fontSize: "0.8rem", color: "#f97373" }}>{engagementError}</p>}
                {!engagement ? (
                  <p style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Click "Simulate Call" to see what AURA would say.</p>
                ) : (
                  <>
                    <p style={{ fontSize: "0.8rem", marginBottom: "0.25rem" }}>Action: <strong>{engagement.action}</strong></p>
                    {engagement.decision && <p style={{ fontSize: "0.75rem", color: "#9ca3af" }}>Decision reason: {engagement.decision.reason}</p>}
                    {engagement.script && <p style={{ fontSize: "0.8rem", marginTop: "0.35rem", padding: "0.5rem", borderRadius: "0.5rem", background: "#0b1120" }}>&quot;{engagement.script}&quot;</p>}
                  </>
                )}
              </div>
            </div>

            <div style={{ flex: "1 1 260px", minWidth: "260px" }}>
              {/* Scheduling suggestions (same as before) */}
              <div style={{ padding: "0.75rem 1rem", borderRadius: "0.75rem", background: "#020617", border: "1px solid #1f2937" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                  <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>Suggested Appointment Slots</h3>
                  <button onClick={() => triggerSchedule(vehicleId)} disabled={scheduleLoading} style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", borderRadius: "0.375rem", border: "1px solid #4b5563", background: "#111827", color: "#e5e7eb", cursor: "pointer" }}>{scheduleLoading ? "Checking…" : "Propose Slots"}</button>
                </div>
                {scheduleError && <p style={{ fontSize: "0.8rem", color: "#f97373" }}>{scheduleError}</p>}
                {!schedule ? (
                  <p style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Click "Propose Slots" to see options based on risk.</p>
                ) : !schedule.can_schedule ? (
                  <p style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Cannot schedule now: {schedule.reason}</p>
                ) : (
                  <ul style={{ fontSize: "0.8rem", paddingLeft: "1rem" }}>{schedule.options.map((opt, idx) => (<li key={idx} style={{ marginBottom: "0.3rem" }}>{opt.label}</li>))}</ul>
                )}
              </div>
            </div>
          </div>

          {/* History list */}
          <div style={{ marginTop: "0.75rem", padding: "1rem", borderRadius: "0.75rem", background: "#0b1120" }}>
            <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Recent History (last {history.length} points)</h2>
            {history.length === 0 ? (
              <p>No history yet.</p>
            ) : (
              <ul style={{ maxHeight: "260px", overflowY: "auto", fontSize: "0.85rem", paddingLeft: "1rem" }}>{history.map((p, idx) => (<li key={idx} style={{ marginBottom: "0.35rem" }}><code>{p.timestamp}</code> &rarr; <strong>{p.anomaly_score.toFixed(2)}</strong> (B:{p.subsystems.brakes?.toFixed(2)} E:{p.subsystems.engine?.toFixed(2)} S:{p.subsystems.suspension?.toFixed(2)})</li>))}</ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ServiceCenterView({ fleet }) {
  const total = fleet.length;
  const warning = fleet.filter((v) => v.status === "warning").length;
  const critical = fleet.filter((v) => v.status === "critical").length;
  const ok = fleet.filter((v) => v.status === "ok").length;

  return (
    <div style={{ color: "#e5e7eb" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <SummaryCard label="Total vehicles" value={total} />
          <SummaryCard label="Critical risk" value={critical} color="#7f1d1d" />
          <SummaryCard label="Warning risk" value={warning} color="#78350f" />
          <SummaryCard label="Healthy" value={ok} color="#064e3b" />
        </div>

        <div style={{ padding: "1rem", borderRadius: "0.75rem", background: "#020617", border: "1px solid #1f2937" }}>
          <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Live Risk Board</h2>
          {fleet.length === 0 ? (
            <p style={{ fontSize: "0.9rem", color: "#9ca3af" }}>No vehicles loaded yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1f2937" }}>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Vehicle</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Anomaly</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {fleet.map((v) => (
                  <tr key={v.vehicle_id} style={{ borderBottom: "1px solid #020617" }}>
                    <td style={{ padding: "0.4rem 0.5rem" }}>{v.vehicle_id}</td>
                    <td style={{ padding: "0.4rem 0.5rem" }}>{v.anomaly_score != null ? v.anomaly_score.toFixed(2) : "--"}</td>
                    <td style={{ padding: "0.4rem 0.5rem", textTransform: "capitalize" }}>{v.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color = "#111827" }) {
  return (
    <div style={{ padding: "0.75rem 1rem", borderRadius: "0.75rem", background: color, minWidth: "160px" }}>
      <div style={{ fontSize: "0.8rem", color: "#d1d5db" }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function ManufacturingView({ summary }) {
  if (!summary) {
    return (
      <p style={{ fontSize: "0.9rem", color: "#9ca3af" }}>
        Loading manufacturing insights…
      </p>
    );
  }

  const { fleet_size, counts, top_risk } = summary;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <SummaryCard label="Fleet size" value={fleet_size} />
        <SummaryCard label="Critical risk" value={counts.critical || 0} color="#7f1d1d" />
        <SummaryCard label="Warning risk" value={counts.warning || 0} color="#78350f" />
        <SummaryCard label="Healthy" value={counts.ok || 0} color="#064e3b" />
      </div>

      <div style={{ padding: "1rem", borderRadius: "0.75rem", background: "#020617", border: "1px solid #1f2937" }}>
        <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Top Risky Vehicles (for RCA)</h2>
        {(!top_risk || top_risk.length === 0) ? (
          <p style={{ fontSize: "0.9rem", color: "#9ca3af" }}>No high-risk vehicles at the moment.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1f2937" }}>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Vehicle</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Anomaly</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Severity</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {top_risk.map((v) => (
                <tr key={v.vehicle_id} style={{ borderBottom: "1px solid #020617" }}>
                  <td style={{ padding: "0.4rem 0.5rem" }}>{v.vehicle_id}</td>
                  <td style={{ padding: "0.4rem 0.5rem" }}>{v.anomaly_score != null ? v.anomaly_score.toFixed(2) : "--"}</td>
                  <td style={{ padding: "0.4rem 0.5rem", textTransform: "capitalize" }}>{v.severity}</td>
                  <td style={{ padding: "0.4rem 0.5rem" }}>{v.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default App;