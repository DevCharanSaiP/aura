import { useState } from "react";

export function LoginPage({ onLogin }) {
  const [role, setRole] = useState("user"); // "user" | "service" | "manufacturing"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role }),
      });

      const data = await res.json();
      if (data.success) {
        // Save token and user info to localStorage
        localStorage.setItem("aura_token", data.token);
        localStorage.setItem("aura_role", data.role);
        localStorage.setItem("aura_user_id", data.user_id);
        if (data.role === "user") {
          localStorage.setItem("aura_vehicle_id", data.user_id.split("_")[1].toUpperCase());
        }
        onLogin(data);
      } else {
        setError(data.message || "Login failed");
      }
    } catch (e) {
      setError("Network error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const demoCredentials = {
    user: { username: "owner_v001", password: "pass123", vehicle: "V001" },
    service: { username: "service_center", password: "service123" },
    manufacturing: { username: "manufacturing", password: "mfg123" },
  };

  const demoUser = demoCredentials[role];

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        color: "#e5e7eb",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          padding: "2rem",
          borderRadius: "1rem",
          background: "#0f172a",
          border: "1px solid #334155",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "0.5rem" }}>AURA</h1>
          <p style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            Predictive Vehicle Health & Maintenance Platform
          </p>
        </div>

        {/* Role Selection */}
        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 500 }}>
            Login As:
          </label>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {[
              { value: "user", label: "🚗 Car Owner" },
              { value: "service", label: "🔧 Service Center" },
              { value: "manufacturing", label: "🏭 Manufacturing" },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setRole(opt.value);
                  setUsername(demoCredentials[opt.value].username);
                  setPassword(demoCredentials[opt.value].password);
                  setError("");
                }}
                style={{
                  flex: 1,
                  padding: "0.5rem",
                  borderRadius: "0.5rem",
                  border: role === opt.value ? "2px solid #3b82f6" : "1px solid #475569",
                  background: role === opt.value ? "#1e40af" : "#1e293b",
                  color: "#e5e7eb",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  transition: "all 0.2s",
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} style={{ marginBottom: "1rem" }}>
          {/* Username */}
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.35rem", fontWeight: 500 }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              style={{
                width: "100%",
                padding: "0.75rem",
                borderRadius: "0.5rem",
                border: "1px solid #475569",
                background: "#1e293b",
                color: "#e5e7eb",
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.35rem", fontWeight: 500 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              style={{
                width: "100%",
                padding: "0.75rem",
                borderRadius: "0.5rem",
                border: "1px solid #475569",
                background: "#1e293b",
                color: "#e5e7eb",
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div
              style={{
                padding: "0.75rem",
                borderRadius: "0.5rem",
                background: "#7f1d1d",
                color: "#fecaca",
                fontSize: "0.85rem",
                marginBottom: "1rem",
                border: "1px solid #991b1b",
              }}
            >
              {error}
            </div>
          )}

          {/* Login Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: "0.5rem",
              border: "none",
              background: loading ? "#475569" : "#3b82f6",
              color: "#e5e7eb",
              fontSize: "0.95rem",
              fontWeight: 600,
              cursor: loading ? "default" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        {/* Demo Credentials Info */}
        <div
          style={{
            padding: "1rem",
            borderRadius: "0.5rem",
            background: "#1e3a5f",
            border: "1px solid #1e40af",
            fontSize: "0.75rem",
            color: "#bfdbfe",
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: "0.35rem" }}>📝 Demo Credentials:</p>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Car Owner:</strong> owner_v001 / pass123 (Access V001 data only)
          </p>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Service Center:</strong> service_center / service123 (View bookings, no sensor data)
          </p>
          <p style={{ margin: "0.2rem 0" }}>
            <strong>Manufacturing:</strong> manufacturing / mfg123 (Fleet summary only)
          </p>
        </div>
      </div>
    </div>
  );
}
