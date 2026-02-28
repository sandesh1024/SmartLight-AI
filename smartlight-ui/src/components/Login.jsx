import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, error, setError } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    await new Promise(r => setTimeout(r, 600)); // small delay for UX
    login(username, password);
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #e0f7fa, #b3e5fc, #81d4fa)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'Nunito', 'Segoe UI', sans-serif",
      padding: "1rem",
    }}>
      {/* Background decoration */}
      <div style={{ position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{
            position: "absolute",
            borderRadius: "50%",
            background: "rgba(79,195,247,0.08)",
            width: `${200 + i * 80}px`,
            height: `${200 + i * 80}px`,
            top: `${10 + i * 12}%`,
            left: `${5 + i * 15}%`,
            animation: `float ${4 + i}s ease-in-out infinite alternate`,
          }} />
        ))}
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
        @keyframes float { from{transform:translateY(0)} to{transform:translateY(-20px)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .login-input {
          width: 100%; padding: 0.85rem 1rem;
          border: 1.5px solid #90caf9; border-radius: 12px;
          background: rgba(255,255,255,0.9); color: #1e293b;
          font-size: 1rem; font-family: inherit; outline: none;
          transition: all 0.3s;
        }
        .login-input:focus { border-color: #0288d1; box-shadow: 0 0 0 3px rgba(2,136,209,0.15); }
        .login-btn {
          width: 100%; padding: 0.9rem;
          background: linear-gradient(45deg, #0288d1, #0d47a1);
          color: white; border: none; border-radius: 12px;
          font-size: 1.1rem; font-weight: 800; font-family: inherit;
          cursor: pointer; transition: all 0.3s;
          box-shadow: 0 4px 15px rgba(2,136,209,0.4);
        }
        .login-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(2,136,209,0.5); }
        .login-btn:disabled { opacity: 0.7; cursor: not-allowed; }
      `}</style>

      <div style={{
        background: "rgba(255,255,255,0.75)",
        backdropFilter: "blur(20px)",
        borderRadius: "24px",
        border: "1px solid rgba(0,123,255,0.25)",
        boxShadow: "0 20px 60px rgba(0,123,255,0.15)",
        padding: "2.5rem",
        width: "100%",
        maxWidth: "420px",
        animation: "fadeIn 0.5s ease",
        position: "relative",
        zIndex: 1,
      }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🚦</div>
          <h1 style={{ color: "#0d47a1", fontSize: "1.8rem", fontWeight: 900, margin: 0 }}>
            SmartLight AI
          </h1>
          <p style={{ color: "#0288d1", fontSize: "0.9rem", marginTop: "0.3rem", fontWeight: 600 }}>
            Traffic Authority Portal
          </p>
          <div style={{
            marginTop: "1rem", padding: "0.4rem 1rem",
            background: "rgba(2,136,209,0.1)", borderRadius: "20px",
            display: "inline-block", fontSize: "0.8rem", color: "#0288d1", fontWeight: 700,
          }}>
            🔒 Authorized Personnel Only
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          <div>
            <label style={{ display: "block", color: "#0d47a1", fontWeight: 700, marginBottom: "0.4rem", fontSize: "0.9rem" }}>
              Username
            </label>
            <input
              className="login-input"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label style={{ display: "block", color: "#0d47a1", fontWeight: 700, marginBottom: "0.4rem", fontSize: "0.9rem" }}>
              Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                className="login-input"
                type={showPass ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={{ paddingRight: "3rem" }}
              />
              <button
                type="button"
                onClick={() => setShowPass(p => !p)}
                style={{
                  position: "absolute", right: "0.75rem", top: "50%",
                  transform: "translateY(-50%)", background: "none",
                  border: "none", cursor: "pointer", fontSize: "1.1rem", color: "#0288d1",
                }}
              >
                {showPass ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {error && (
            <div style={{
              background: "rgba(239,83,80,0.1)", border: "1px solid rgba(239,83,80,0.3)",
              borderRadius: "8px", padding: "0.7rem 1rem",
              color: "#c62828", fontSize: "0.85rem", fontWeight: 600,
            }}>
              ⚠️ {error}
            </div>
          )}

          <button className="login-btn" type="submit" disabled={loading}>
            {loading ? "⏳ Signing in..." : "Sign In →"}
          </button>
        </form>

        <div style={{
          marginTop: "1.5rem", padding: "1rem",
          background: "rgba(224,247,250,0.6)", borderRadius: "12px",
          border: "1px solid #bbdefb",
        }}>
          <p style={{ color: "#0288d1", fontSize: "0.78rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            Demo Credentials:
          </p>
          <p style={{ color: "#475569", fontSize: "0.75rem", lineHeight: 1.8 }}>
            admin / smartlight123<br />
            officer / officer456<br />
            super / super789
          </p>
        </div>

        <p style={{ textAlign: "center", marginTop: "1.2rem", fontSize: "0.78rem", color: "#64748b" }}>
          Public traffic view? {" "}
          <a href="http://localhost:5174" style={{ color: "#0288d1", fontWeight: 700 }}>
            Open Public App →
          </a>
        </p>
      </div>
    </div>
  );
}