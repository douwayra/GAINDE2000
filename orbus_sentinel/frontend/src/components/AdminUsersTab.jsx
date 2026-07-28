import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../utils/api';

export default function AdminUsersTab() {
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(true);
  
  // Search and Pagination for Users list
  const [userSearch, setUserSearch] = useState('');
  const [userPage, setUserPage] = useState(1);
  const USERS_PER_PAGE = 5;

  // Search and Pagination for Audit Logs
  const [logSearch, setLogSearch] = useState('');
  const [logPage, setLogPage] = useState(1);
  const LOGS_PER_PAGE = 10;

  // Form States
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('direction');
  const [newBureau, setNewBureau] = useState('');

  // Password Modification States
  const [modUsername, setModUsername] = useState('');
  const [modPassword, setModPassword] = useState('');
  const [modSuccess, setModSuccess] = useState('');
  const [modError, setModError] = useState('');
  const [modLoading, setModLoading] = useState(false);

  // Status Messages for User Creation
  const [createSuccess, setCreateSuccess] = useState('');
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  // Fetch users from API
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await fetchWithAuth('/api/admin/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
        if (data.length > 0 && !modUsername) {
          setModUsername(data[0].username);
        }
      }
    } catch (err) {
      console.error("Error loading users:", err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch connection audit logs from API
  const fetchAuditLogs = async () => {
    setLogsLoading(true);
    try {
      const response = await fetchWithAuth('/api/admin/audit-logs');
      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data);
      }
    } catch (err) {
      console.error("Error loading audit logs:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchAuditLogs();
  }, []);

  // Filtered lists
  const filteredUsers = (users || []).filter(u => {
    const term = userSearch.toLowerCase().trim();
    if (!term) return true;
    return (
      String(u.username || '').toLowerCase().includes(term) ||
      String(u.role || '').toLowerCase().includes(term) ||
      String(u.bureau_douane || '').toLowerCase().includes(term)
    );
  });

  const filteredLogs = (auditLogs || []).filter(l => {
    const term = logSearch.toLowerCase().trim();
    if (!term) return true;
    return (
      String(l.username || '').toLowerCase().includes(term) ||
      String(l.client_ip || '').toLowerCase().includes(term) ||
      String(l.location || '').toLowerCase().includes(term) ||
      String(l.status || '').toLowerCase().includes(term)
    );
  });

  // Paginated users
  const totalUserPages = Math.ceil(filteredUsers.length / USERS_PER_PAGE) || 1;
  const paginatedUsers = filteredUsers.slice(
    (userPage - 1) * USERS_PER_PAGE,
    userPage * USERS_PER_PAGE
  );

  // Paginated logs
  const totalLogPages = Math.ceil(filteredLogs.length / LOGS_PER_PAGE) || 1;
  const paginatedLogs = filteredLogs.slice(
    (logPage - 1) * LOGS_PER_PAGE,
    logPage * LOGS_PER_PAGE
  );

  // Handle User Creation
  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreateError('');
    setCreateSuccess('');

    if (!newUsername.trim() || !newPassword) {
      setCreateError("Veuillez remplir tous les champs obligatoires.");
      return;
    }

    setCreateLoading(true);
    try {
      const response = await fetchWithAuth('/api/admin/create-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          role: newRole,
          bureau_douane: newBureau.trim() || null
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erreur de création");
      }

      setCreateSuccess(`User "${newUsername.trim()}" created successfully!`);
      setNewUsername('');
      setNewPassword('');
      setNewBureau('');
      
      // Reload lists
      fetchUsers();
      fetchAuditLogs();
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  // Handle Password Modification
  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    setModError('');
    setModSuccess('');

    if (!modUsername || !modPassword) {
      setModError("Veuillez choisir un utilisateur et saisir un mot de passe.");
      return;
    }

    setModLoading(true);
    try {
      const response = await fetchWithAuth('/api/admin/update-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: modUsername,
          password: modPassword
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erreur de mise à jour");
      }

      setModSuccess(`Password de "${modUsername}" updated successfully!`);
      setModPassword('');
      fetchAuditLogs();
    } catch (err) {
      setModError(err.message);
    } finally {
      setModLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '30px', width: '100%' }}>
      
      {/* ROW 1: Create user & Update password forms */}
      <div className="dashboard-row">
        
        {/* Box 1: Create User */}
        <div className="chart-card">
          <div className="chart-card-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
              <span>Créer un Nouvel Utilisateur</span>
            </div>
          </div>
          
          <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
            <div className="login-input-group">
              <label>Identifiant</label>
              <input 
                type="text" 
                placeholder="ex: moussa_customs" 
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                required 
              />
            </div>
            
            <div className="login-input-group">
              <label>Mot de passe</label>
              <input 
                type="password" 
                placeholder="Saisir le mot de passe initial" 
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required 
              />
            </div>
            
            <div className="login-input-group">
              <label>Rôle et Profil d\'Accès</label>
              <select 
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', fontSize: '0.9rem', outline: 'none', color: 'var(--text-main)', background: 'var(--card-bg)' }}
              >
                <option value="direction">Direction Générale (Décisionnel)</option>
                <option value="inspecteur">Inspecteur Bureau (Douane)</option>
                <option value="transitaire">Transitaire / Déclarant</option>
                <option value="partenaire">Partenaire Financier / Assureur</option>
                <option value="statisticien">Statisticien / Chercheur (Anonymisé)</option>
                <option value="journaliste">Journaliste / Presse</option>
                <option value="admin">Administrateur Système</option>
              </select>
            </div>
            
            <div className="login-input-group">
              <label>Bureau de Douane / Entité (ex: DKP, AIBD, Port, AXA)</label>
              <input 
                type="text" 
                placeholder="ex: DKP, ou laisser vide pour National" 
                value={newBureau}
                onChange={(e) => setNewBureau(e.target.value)}
              />
            </div>
            
            {createError && <div className="login-error">{createError}</div>}
            {createSuccess && (
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', fontSize: '0.82rem', fontWeight: '600', padding: '10px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                ✓ {createSuccess}
              </div>
            )}
            
            <button type="submit" className="premium-pdf-btn" style={{ width: '100%', justifyContent: 'center' }} disabled={createLoading}>
              {createLoading ? 'Ajout...' : "Ajouter l'utilisateur"}
            </button>
          </form>
        </div>

        {/* Box 2: Update Password */}
        <div className="chart-card">
          <div className="chart-card-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <span>Modifier un Mot de Passe</span>
            </div>
          </div>
          
          <form onSubmit={handleUpdatePassword} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
            <div className="login-input-group">
              <label>Sélectionner l\'Utilisateur</label>
              <select 
                value={modUsername}
                onChange={(e) => setModUsername(e.target.value)}
                style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', fontSize: '0.9rem', outline: 'none', color: 'var(--text-main)', background: 'var(--card-bg)' }}
              >
                {users.map(u => (
                  <option key={u.username} value={u.username}>{u.username} ({u.role})</option>
                ))}
              </select>
            </div>
            
            <div className="login-input-group">
              <label>Nouveau Mot de passe</label>
              <input 
                type="password" 
                placeholder="Entrer le nouveau mot de passe" 
                value={modPassword}
                onChange={(e) => setModPassword(e.target.value)}
                required 
              />
            </div>

            <div style={{ flexGrow: 1 }}></div>
            
            {modError && <div className="login-error">{modError}</div>}
            {modSuccess && (
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', fontSize: '0.82rem', fontWeight: '600', padding: '10px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                ✓ {modSuccess}
              </div>
            )}
            
            <button type="submit" className="premium-pdf-btn" style={{ width: '100%', justifyContent: 'center', marginTop: '45px' }} disabled={modLoading}>
              {modLoading ? 'Modification...' : "Mettre à jour le mot de passe"}
            </button>
          </form>
        </div>
      </div>

      {/* ROW 2: Existing Accounts List */}
      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title">Comptes Utilisateurs Enregistrés</div>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Rechercher un compte..."
              value={userSearch}
              onChange={(e) => {
                setUserSearch(e.target.value);
                setUserPage(1);
              }}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setUserPage(prev => Math.max(prev - 1, 1))}
                disabled={userPage === 1}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {userPage} / {totalUserPages} ({filteredUsers.length} utilisateurs)
              </span>
              <button
                className="pagination-btn"
                onClick={() => setUserPage(prev => Math.min(prev + 1, totalUserPages))}
                disabled={userPage === totalUserPages}
              >
                Next
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Identifiant</th>
                  <th>Rôle</th>
                  <th>Bureau de douane / Entité</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      Chargement des comptes...
                    </td>
                  </tr>
                ) : paginatedUsers.length > 0 ? (
                  paginatedUsers.map(u => (
                    <tr key={u.username}>
                      <td><strong>{u.username}</strong></td>
                      <td>
                        <span className="badge" style={{ background: 'var(--primary-glow)', color: 'var(--primary-light)', fontWeight: 'bold', textTransform: 'uppercase', border: '1px solid var(--border)' }}>
                          {u.role}
                        </span>
                      </td>
                      <td>{u.bureau_douane || 'All (National)'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No user found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ROW 3: User Connection logs (Audit logs) */}
      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title">
            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Journal d\'Audit & Connexions des Utilisateurs</span>
              </div>
              <button 
                onClick={fetchAuditLogs}
                style={{
                  background: 'var(--primary-glow)',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  color: 'var(--primary-light)',
                  padding: '4px 10px',
                  fontSize: '0.72rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Filtrer par identifiant, IP ou statut..."
              value={logSearch}
              onChange={(e) => {
                setLogSearch(e.target.value);
                setLogPage(1);
              }}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setLogPage(prev => Math.max(prev - 1, 1))}
                disabled={logPage === 1}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {logPage} / {totalLogPages} ({filteredLogs.length} logs)
              </span>
              <button
                className="pagination-btn"
                onClick={() => setLogPage(prev => Math.min(prev + 1, totalLogPages))}
                disabled={logPage === totalLogPages}
              >
                Next
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Horodatage</th>
                  <th>Utilisateur</th>
                  <th>IP Client</th>
                  <th>Géolocalisation</th>
                  <th>Statut Accès</th>
                </tr>
              </thead>
              <tbody>
                {logsLoading ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      Chargement du journal d'audit...
                    </td>
                  </tr>
                ) : paginatedLogs.length > 0 ? (
                  paginatedLogs.map((log, idx) => {
                    const isSuccess = log.status?.toUpperCase() === 'SUCCESS';
                    return (
                      <tr key={idx}>
                        <td style={{ color: 'var(--text-muted)' }}>{log.timestamp}</td>
                        <td><strong>{log.username}</strong></td>
                        <td style={{ fontFamily: 'monospace' }}>{log.client_ip}</td>
                        <td>{log.location || 'Inconnue'}</td>
                        <td>
                          <span 
                            className="badge" 
                            style={{ 
                              background: isSuccess ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)', 
                              color: isSuccess ? '#10b981' : '#ef4444', 
                              fontWeight: 'bold',
                              border: isSuccess ? '1px solid rgba(16, 185, 129, 0.2)' : '1px solid rgba(239, 68, 68, 0.2)'
                            }}
                          >
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No connection logs recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
    </div>
  );
}
