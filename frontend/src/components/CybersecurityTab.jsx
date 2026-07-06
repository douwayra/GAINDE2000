import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../utils/api';

export default function CybersecurityTab({ role }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const filteredLogs = (logs || []).filter(log => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return true;
    return (
      String(log.timestamp || '').toLowerCase().includes(term) ||
      String(log.username || '').toLowerCase().includes(term) ||
      String(log.client_ip || '').toLowerCase().includes(term) ||
      String(log.server_ip || '').toLowerCase().includes(term) ||
      String(log.location || '').toLowerCase().includes(term) ||
      String(log.status || '').toLowerCase().includes(term)
    );
  });

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.ceil(filteredLogs.length / ITEMS_PER_PAGE) || 1;
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const response = await fetchWithAuth('/api/admin/audit-logs');
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (err) {
      console.error("Error loading audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const handleSimulateIncident = async (incidentType) => {
    try {
      const response = await fetchWithAuth('/api/admin/simulate-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_type: incidentType })
      });

      if (response.ok) {
        // Reload logs after simulation
        fetchAuditLogs();
      } else {
        alert("Erreur lors de la simulation d'incident.");
      }
    } catch (err) {
      console.error(err);
      alert("Erreur de connexion.");
    }
  };

  const isAdmin = role === 'admin';

  return (
    <>
      <div className="dashboard-row">
        {/* Server performance card */}
        <div className="chart-card" style={{ flex: 1 }}>
          <div className="chart-card-title">État et Performance des Serveurs ORBUS</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '15px', marginTop: '15px' }}>
            <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Latence scripts ASP</span>
              <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>42 ms</span>
            </div>
            <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Charge Serveur</span>
              <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>24%</span>
            </div>
            <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>DuckDB Memory</span>
              <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>124 Mo</span>
            </div>
            <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Appels API / min</span>
              <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--success)' }}>2 450</span>
            </div>
          </div>
        </div>

        {/* Admin Incident Simulator Card */}
        {isAdmin && (
          <div className="chart-card" style={{ flex: 1 }}>
            <div className="chart-card-title">Simulateur d\'Incidents de Cybersécurité</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px', marginTop: '-5px' }}>
              Injectez des anomalies réseau et de sécurité fictives pour tester les alertes en temps réel.
            </p>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button 
                className="login-btn" 
                onClick={() => handleSimulateIncident('brute_force')} 
                style={{ background: '#ef4444', flex: 1, minWidth: '130px', fontSize: '0.8rem', padding: '10px' }}
              >
                Attaque Force Brute
              </button>
              <button 
                className="login-btn" 
                onClick={() => handleSimulateIncident('tor_node')} 
                style={{ background: '#f59e0b', flex: 1, minWidth: '130px', fontSize: '0.8rem', padding: '10px' }}
              >
                Connexion Tor
              </button>
              <button 
                className="login-btn" 
                onClick={() => handleSimulateIncident('data_leak')} 
                style={{ background: '#3b82f6', flex: 1, minWidth: '130px', fontSize: '0.8rem', padding: '10px' }}
              >
                Fuite de Données
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Audit Logs Table */}
      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title">Journal d\'Accès Réseau & Détection d\'Intrusions</div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px' }}>
            Journal de connexion et détection des menaces par adresse IP.
          </p>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Rechercher un log..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                Précédent
              </button>
              <span className="pagination-info">
                Page {currentPage} / {totalPages} ({filteredLogs.length} logs)
              </span>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
              >
                Suivant
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Horodatage</th>
                  <th>Identifiant</th>
                  <th>Adresse IP Cliente</th>
                  <th>IP Serveur</th>
                  <th>Région / Ville</th>
                  <th>Status de Sécurité</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      Chargement des logs...
                    </td>
                  </tr>
                ) : paginatedLogs.length > 0 ? (
                  paginatedLogs.map((log, idx) => {
                    let badgeClass = 'badge';
                    const status = log.status;
                    if (status.includes('Normal') || status.includes('Authorized')) {
                      badgeClass += ' badge-success';
                    } else if (status.includes('Force Brute') || status.includes('Tentative')) {
                      badgeClass += ' badge-warning';
                    } else {
                      badgeClass += ' badge-danger';
                    }
                    return (
                      <tr key={idx}>
                        <td>{log.timestamp}</td>
                        <td><strong>{log.username}</strong></td>
                        <td>{log.client_ip}</td>
                        <td>{log.server_ip}</td>
                        <td>{log.location}</td>
                        <td><span className={badgeClass}>{status}</span></td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      Aucun journal d'audit disponible.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
