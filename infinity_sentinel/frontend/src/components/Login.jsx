import React, { useState } from 'react';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMsg('Veuillez remplir tous les champs.');
      return;
    }

    setLoading(true);
    setErrorMsg('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Identifiant ou mot de passe incorrect');
      }

      const data = await response.json();
      
      // Store token and role info
      localStorage.setItem('orbus_token', data.access_token);
      localStorage.setItem('orbus_role', data.role);
      localStorage.setItem('orbus_username', data.username);
      if (data.bureau_douane) {
        localStorage.setItem('orbus_bureau', data.bureau_douane);
      } else {
        localStorage.removeItem('orbus_bureau');
      }

      onLoginSuccess();
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-overlay">
      <video autoPlay muted loop playsInline preload="auto" className="login-video-bg">
        <source src="/assets/port1.mp4" type="video/mp4" />
      </video>
      <div className="login-video-overlay"></div>

      <div className="login-card" style={{ borderTop: '5px solid #63a0e8' }}>
        <div style={{ display: 'flex', justifyContent: 'center', width: '100%', marginBottom: '5px' }}>
          <img src="/assets/infinity_logo.png" alt="Infinity Sentinel Logo" style={{ height: '65px', objectFit: 'contain' }} />
        </div>
        <h2>Infinity Sentinel-2</h2>
        <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', textAlign: 'center', marginTop: '-10px' }}>
          Port Autonome de Dakar & Supervision IPMD V2
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="login-input-group">
            <label htmlFor="username">Identifiant</label>
            <input
              type="text"
              id="username"
              placeholder="Saisissez votre identifiant"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="login-input-group">
            <label htmlFor="password">Mot de passe</label>
            <input
              type="password"
              id="password"
              placeholder="Saisissez votre mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {errorMsg && <div className="login-error">{errorMsg}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? "Connexion en cours..." : "Se Connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
