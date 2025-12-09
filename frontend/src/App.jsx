import { useEffect, useState, useCallback } from "react";
import { LoginPage } from "./LoginPage";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authToken, setAuthToken] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [userId, setUserId] = useState(null);
  const [ownedVehicleId, setOwnedVehicleId] = useState(null);
  // Only keep fleet state for user role
  const [fleet, setFleet] = useState([]);
  // Removed mode state as we'll use userRole to determine the view
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
  const [upcomingBookings, setUpcomingBookings] = useState([]);
  const [mfgSummary, setMfgSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Handle login
  const handleLogin = (data) => {
    setIsLoggedIn(true);
    setAuthToken(data.token);
    setUserRole(data.role);
    setUserId(data.user_id);
    
    // Store in localStorage for persistence
    localStorage.setItem("aura_token", data.token);
    localStorage.setItem("aura_role", data.role);
    localStorage.setItem("aura_user_id", data.user_id);
    
    // Extract vehicle ID for car owners
    if (data.role === "user" && data.user_id.includes("v")) {
      const vehicleId = data.user_id.substring(data.user_id.length - 4).toUpperCase();
      setOwnedVehicleId(vehicleId);
      setVehicleId(vehicleId);
      localStorage.setItem("aura_vehicle_id", vehicleId);
    }
  };

  // Handle logout
  const handleLogout = useCallback(() => {
    console.log("Logging out...");
    setIsLoggedIn(false);
    setAuthToken(null);
    setUserRole(null);
    setUserId(null);
    setOwnedVehicleId(null);
    localStorage.removeItem("aura_token");
    localStorage.removeItem("aura_role");
    localStorage.removeItem("aura_user_id");
    localStorage.removeItem("aura_vehicle_id");
    console.log("Logged out Successfully");
  }, []);

  // Memoized fetchFleet to prevent infinite loops
  const fetchFleet = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const headers = authToken ? {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      } : {};

      // Only fetch what's needed based on user role
      const endpoints = [];
      
      // In the fetchFleet function, only fetch bookings for service center
      if (userRole === 'service') {
        endpoints.push(
          fetch(`${API_BASE}/bookings/upcoming`, { headers })
        );
      } 
      // Car owner only needs their own vehicle data
      else if (userRole === 'user' && ownedVehicleId) {
        endpoints.push(
          fetch(`${API_BASE}/vehicles/${ownedVehicleId}`, { headers })
        );
        // Set the vehicleId to the ownedVehicleId
        setVehicleId(ownedVehicleId);
      }
      // Manufacturing view needs the summary
      else if (userRole === 'mfg') {
        endpoints.push(
          fetch(`${API_BASE}/mfg/summary`, { headers })
        );
      }

      if (endpoints.length === 0) return;

      const responses = await Promise.all(endpoints);
      
      // Check for any 401 Unauthorized responses
      if (responses.some(res => res.status === 401)) {
        throw new Error("Session expired - please login again");
      }
      
      // Process responses based on role
      if (userRole === 'service') {
        const [bookingsRes] = responses;
        const bookingsJson = bookingsRes.ok ? await bookingsRes.json() : { bookings: [] };
        
        setUpcomingBookings(bookingsJson.bookings || []);
      } 
      else if (userRole === 'user' && ownedVehicleId) {
        const [vehicleRes] = responses;
        if (vehicleRes.ok) {
          const vehicleData = await vehicleRes.json();
          setFleet([vehicleData]); // Store as array for compatibility with existing code
        }
      }
      else if (userRole === 'mfg') {
        const [mfgRes] = responses;
        if (mfgRes.ok) {
          const mfgJson = await mfgRes.json();
          setMfgSummary(mfgJson);
        }
      }
    } catch (e) {
      console.error("Fetch error:", e);
      if (e.message.includes("Session expired") || e.message.includes("Unauthorized")) {
        handleLogout();
      } else {
        setError("Failed to load data. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  // Check for existing session on mount
  const validateToken = useCallback(async () => {
    const savedToken = localStorage.getItem("aura_token");
    const savedRole = localStorage.getItem("aura_role");
    const savedUserId = localStorage.getItem("aura_user_id");
    
    // If any auth data is missing, log out
    if (!savedToken || !savedRole || !savedUserId) {
      console.log("Missing auth data in localStorage");
      handleLogout();
      return;
    }

    try {
      console.log("Validating token...");
      const res = await fetch(`${API_BASE}/auth/validate?token=${savedToken}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${savedToken}`
        },
      });

      if (res.status === 422) {
        const errorData = await res.json();
        console.error("Validation error:", errorData);
        throw new Error(`Validation failed: ${JSON.stringify(errorData)}`);
      }

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      console.log("Token validation response:", data);

      if (!data.valid) {
        throw new Error("Invalid token");
      }

      // If we get here, token is valid - update state
      console.log("Token is valid, updating state...");
      setAuthToken(savedToken);
      setUserRole(savedRole);
      setUserId(savedUserId);
      setIsLoggedIn(true);
      
      // Set vehicle ID if it exists
      const savedVehicleId = localStorage.getItem("aura_vehicle_id");
      if (savedVehicleId) {
        setOwnedVehicleId(savedVehicleId);
        setVehicleId(savedVehicleId);
      }

    } catch (e) {
      console.error("Token validation error:", e);
      handleLogout();
    }
  }, []);

  // Validate token on mount and when logged in state changes
  useEffect(() => {
    if (isLoggedIn) {
      validateToken();
    }
  }, [isLoggedIn, validateToken]);

  useEffect(() => {
    validateToken();
  }, [validateToken]);

  // Fetch data when authenticated and authToken is ready
  useEffect(() => {
    if (isLoggedIn && authToken) {
      // Only fetch fleet data if user has permission
      const timer = setTimeout(() => {
        if (userRole === 'user' || userRole === 'service') {
          fetchFleet();
        }
      }, 100);
      
      // Set up polling only for service center view
      let interval;
      if (userRole === 'service') {
        interval = setInterval(() => {
          fetchFleet();
        }, 3000);
      }
      
      return () => {
        clearTimeout(timer);
        if (interval) clearInterval(interval);
      };
    }
  }, [isLoggedIn, authToken, fetchFleet, userRole]);

  const triggerEngagement = useCallback(async (id) => {
    try {
      setEngagementLoading(true);
      setEngagementError("");
      setEngagement(null);

      const headers = {
        "Content-Type": "application/json",
      };
      if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
      }

      const res = await fetch("http://127.0.0.1:8200/simulate_call", {
        method: "POST",
        headers,
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
  }, [authToken]);

  const triggerSchedule = useCallback(async (id) => {
    try {
      setScheduleLoading(true);
      setScheduleError("");
      setSchedule(null);

      const headers = {
        "Content-Type": "application/json",
      };
      if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
      }

      const res = await fetch("http://127.0.0.1:8300/propose_slots", {
        method: "POST",
        headers,
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
  }, [authToken]);

  const confirmBooking = useCallback(async (vehicleId, slotStart, slotEnd) => {
    try {
      const headers = {
        "Content-Type": "application/json",
      };
      if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
      }

      const res = await fetch(`${API_BASE}/bookings/confirm`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          vehicle_id: vehicleId,
          slot_start: slotStart,
          slot_end: slotEnd,
          center_id: "SVC_CENTER_001",
        }),
      });

      const json = await res.json();
      if (json.success) {
        alert(`✓ Booking confirmed for ${slotStart}`);
        triggerSchedule(vehicleId);
        fetchFleet();
      } else {
        alert(`✗ Failed to confirm booking: ${json.error}`);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to confirm booking");
    }
  }, [authToken, triggerSchedule, fetchFleet]);

  const fetchData = useCallback(async (id) => {
    try {
      setLoading(true);
      setError("");

      // Only car owners can view detailed health data
      if (userRole !== "user") {
        setError("Only vehicle owners can view detailed health data");
        setHealth(null);
        setHistory([]);
        setContactDecision(null);
        return;
      }

      const headers = authToken ? {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      } : {};

      const [healthRes, histRes, contactRes] = await Promise.all([
        fetch(`${API_BASE}/health/${id}`, { headers }),
        fetch(`${API_BASE}/history/${id}?limit=20`, { headers }),
        fetch(`${API_BASE}/contact_decision/${id}`, { headers }),
      ]);

      if (!healthRes.ok || !histRes.ok || !contactRes.ok) {
        if (healthRes.status === 403 || histRes.status === 403 || contactRes.status === 403) {
          throw new Error("Unauthorized access - wrong vehicle");
        }
        throw new Error(`HTTP ${healthRes.status}`);
      }

      const healthJson = await healthRes.json();
      const histJson = await histRes.json();
      const contactJson = await contactRes.json();

      setHealth(healthJson);
      setHistory(histJson.points || []);
      setContactDecision(contactJson);
    } catch (e) {
      console.error(e);
      setError(e.message || "Failed to load data from backend");
      if (e.message.includes("Unauthorized")) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  }, [authToken, userRole, handleLogout]);

  useEffect(() => {
    if (isLoggedIn && authToken && userRole === "user") {
      fetchData(vehicleId);
      const interval = setInterval(() => {
        fetchData(vehicleId);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [vehicleId, isLoggedIn, authToken, userRole, fetchData]);

  // Keep health parsing inside UserView so views remain self-contained

  // Show login page if not authenticated
  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div style={{ padding: "1.5rem 2rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem", color: "#e5e7eb" }}>
        AURA Prototype Dashboard
      </h1>
      <p style={{ marginBottom: "1rem", color: "#9ca3af" }}>
        Live vehicle health from Master Agent (V001–V010).
      </p>
      {/* Logout button in top right */}
      <div style={{ position: "absolute", top: "1.5rem", right: "2rem" }}>
        <button
          onClick={handleLogout}
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#ef4444",
            color: "#fff",
            border: "none",
            borderRadius: "0.375rem",
            cursor: "pointer",
            fontSize: "0.875rem",
            fontWeight: 500,
          }}
        >
          Logout
        </button>
      </div>
      {/* User info */}
      <div style={{ marginBottom: "1rem", padding: "0.75rem", backgroundColor: "#374151", borderRadius: "0.375rem", color: "#d1d5db", fontSize: "0.875rem" }}>
        Logged in as <strong>{userId}</strong> ({userRole === "user" ? "Car Owner" : userRole === "service" ? "Service Center" : "Manufacturing"})
      </div>

      {/* Show only the view for the current user's role */}
      {userRole === "user" ? (
        <UserView
          vehicleId={vehicleId}
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
      ) : userRole === "service" ? (
        <ServiceCenterView 
          upcomingBookings={upcomingBookings} 
        />
      ) : (
        <ManufacturingView summary={mfgSummary} />
      )}
    </div>
  );
}

function UserView(props) {
  const {
    vehicleId,
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
      {loading && (
        <div style={{ marginBottom: "0.5rem", color: "#e5e7eb" }}>Loading…</div>
      )}
      {error && (
        <div style={{ marginBottom: "0.5rem", color: "#f97373" }}>{error}</div>
      )}

      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>

        {/* Main column: current health, contact decision, engagement, schedule, history */}
        <div style={{ flex: "1 1 520px", minWidth: "320px" }}>
          {/* Current health card */}
          <div style={{ padding: "1rem", borderRadius: "0.75rem", background: current && current.anomaly_score > 0.5 ? "#7f1d1d" : current && current.anomaly_score > 0.25 ? "#78350f" : "#064e3b", minWidth: "260px" }}>
            <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Vehicle Health Status</h2>
            {current ? (
              <>
                <p style={{ marginBottom: "0.5rem" }}>
                  <strong style={{ color: "#fbbf24" }}>Overall Score:</strong> {current.anomaly_score?.toFixed(2) || "--"}
                </p>

                {/* Rule-based scoring section */}
                <div style={{ fontSize: "0.85rem", color: "#d1d5db", marginBottom: "0.5rem", paddingLeft: "0.5rem", borderLeft: "2px solid #3b82f6" }}>
                  <p style={{ margin: "0.15rem 0", fontWeight: 500 }}>Rule-Based (70%):</p>
                  <p style={{ margin: "0.1rem 0" }}>Score: <strong>{current.rule_anomaly_score?.toFixed(2) || "--"}</strong></p>
                  <p style={{ margin: "0.1rem 0" }}>Brakes: <strong>{current.subsystems?.brakes?.toFixed(2) || "--"}</strong></p>
                  <p style={{ margin: "0.1rem 0" }}>Engine: <strong>{current.subsystems?.engine?.toFixed(2) || "--"}</strong></p>
                  <p style={{ margin: "0.1rem 0" }}>Suspension: <strong>{current.subsystems?.suspension?.toFixed(2) || "--"}</strong></p>
                </div>

                {/* ML-based scoring section */}
                <div style={{ fontSize: "0.85rem", color: "#d1d5db", paddingLeft: "0.5rem", borderLeft: "2px solid #8b5cf6" }}>
                  <p style={{ margin: "0.15rem 0", fontWeight: 500 }}>ML-Based (30%) – Isolation Forest:</p>
                  <p style={{ margin: "0.1rem 0" }}>
                    Score: <strong>{current.ml_anomaly_score?.toFixed(2) || "--"}</strong>
                  </p>
                  <p style={{ margin: "0.1rem 0" }}>
                    Decision: <strong style={{ textTransform: "uppercase", color: current.ml_label === "anomaly" ? "#f87171" : "#86efac" }}>
                      {current.ml_label || "unknown"}
                    </strong>
                  </p>
                </div>
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
                  <p style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Cannot schedule now: {schedule.reason}{schedule.total_suggested && ` (${schedule.available}/${schedule.total_suggested} available)`}</p>
                ) : (
                  <div style={{ fontSize: "0.8rem" }}>
                    {schedule.total_suggested && (
                      <p style={{ fontSize: "0.75rem", color: "#d1fae5", marginBottom: "0.3rem" }}>
                        ✓ {schedule.available} of {schedule.total_suggested} slots available (others already booked)
                      </p>
                    )}
                    {schedule.options.map((opt, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem", paddingBottom: "0.3rem", borderBottom: "1px solid #1f2937" }}>
                        <span>{opt.label}</span>
                        <button
                          onClick={() => confirmBooking(vehicleId, opt.slot_start, opt.slot_end)}
                          style={{
                            padding: "0.2rem 0.5rem",
                            fontSize: "0.75rem",
                            borderRadius: "0.375rem",
                            border: "1px solid #4b5563",
                            background: "#065f46",
                            color: "#d1fae5",
                            cursor: "pointer",
                            fontWeight: 500,
                          }}
                        >
                          Confirm
                        </button>
                      </div>
                    ))}
                  </div>
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

function ServiceCenterView({ upcomingBookings }) {
  return (
    <div style={{ color: "#e5e7eb" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ padding: "1rem", borderRadius: "0.75rem", background: "#1e293b", border: "1px solid #334155" }}>
          <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Service Center Dashboard</h2>
          <p style={{ fontSize: "0.9rem", color: "#cbd5e1" }}>
            This view shows upcoming service appointments. Vehicle health data will be available 
            through the customer agent after a booking is confirmed.
          </p>
        </div>

        {/* Upcoming AURA Bookings */}
        <div style={{ padding: "1rem", borderRadius: "0.75rem", background: "#020617", border: "1px solid #1f2937" }}>
          <h2 style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Upcoming AURA Bookings</h2>
          {upcomingBookings.length === 0 ? (
            <p style={{ fontSize: "0.9rem", color: "#9ca3af" }}>No confirmed bookings yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1f2937" }}>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Vehicle</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Date / Time</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Service Center</th>
                  <th style={{ textAlign: "left", padding: "0.5rem" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {upcomingBookings.map((booking) => (
                  <tr key={booking.booking_id} style={{ borderBottom: "1px solid #020617" }}>
                    <td style={{ padding: "0.4rem 0.5rem", fontWeight: 500 }}>{booking.vehicle_id}</td>
                    <td style={{ padding: "0.4rem 0.5rem" }}>
                      {booking.slot_start
                        ? new Date(booking.slot_start).toLocaleString("en-IN", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "--"}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem" }}>{booking.center_id || "TBD"}</td>
                    <td style={{ padding: "0.4rem 0.5rem", textTransform: "capitalize", color: booking.status === "confirmed" ? "#86efac" : "#9ca3af" }}>
                      {booking.status}
                    </td>
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