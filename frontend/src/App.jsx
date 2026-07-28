import React, { useState, useEffect } from 'react';
import { fetchWithAuth, performLogout } from './utils/api';
import { 
  LayoutDashboard, 
  TrendingUp, 
  TrendingDown, 
  ShieldAlert, 
  Layers, 
  Search as SearchIcon, 
  Cpu, 
  Users,
  BarChart3
} from 'lucide-react';

// Components
import Login from './components/Login';
import DashboardTab from './components/DashboardTab';
import ImportsTab from './components/ImportsTab';
import ExportsTab from './components/ExportsTab';
import RisksTab from './components/RisksTab';
import LogisticsTab from './components/LogisticsTab';
import BusinessTab from './components/BusinessTab';
import FinanceTab from './components/FinanceTab';
import CybersecurityTab from './components/CybersecurityTab';
import AdminUsersTab from './components/AdminUsersTab';
import Chatbot from './components/Chatbot';
import DossierTimelineModal from './components/DossierTimelineModal';

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('');
  const [bureau, setBureau] = useState('');
  
  // Navigation & Tabs
  const [activeTab, setActiveTab] = useState('executive');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Theme Toggle State
  const [theme, setTheme] = useState(localStorage.getItem('orbus_theme') || 'light');

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    const root = document.documentElement;
    if (newTheme === 'dark') {
      root.classList.remove('light-theme');
      root.classList.add('dark-theme');
    } else {
      root.classList.remove('dark-theme');
      root.classList.add('light-theme');
    }
    localStorage.setItem('orbus_theme', newTheme);
  };

  useEffect(() => {
    const root = document.documentElement;
    const storedTheme = localStorage.getItem('orbus_theme') || 'light';
    if (storedTheme === 'dark') {
      root.classList.remove('light-theme');
      root.classList.add('dark-theme');
      setTheme('dark');
    } else {
      root.classList.remove('dark-theme');
      root.classList.add('light-theme');
      setTheme('light');
    }
  }, []);
  
  // Data
  const [dashboardData, setDashboardData] = useState(null);
  const [dossiers, setDossiers] = useState([]);
  const [budgetAlert, setBudgetAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  
  // PDF Multi-Report selection states
  const [showReportModal, setShowReportModal] = useState(false);
  const [selectedReportType, setSelectedReportType] = useState('executive');
  const [anonymizeData, setAnonymizeData] = useState(false);
  const [reportMonth, setReportMonth] = useState('07');
  const [reportYear, setReportYear] = useState('2026');

  // Smart Command Console States
  const [lang, setLang] = useState('fr');
  const [commandText, setCommandText] = useState("");
  const [showCommandSuggestions, setShowCommandSuggestions] = useState(false);

  const handleExecuteCommand = (cmd) => {
    const cleanCmd = cmd.trim().toLowerCase();
    if (!cleanCmd) return;

    if (cleanCmd.includes("fraude") || cleanCmd.includes("risque") || cleanCmd === "risks") {
      setActiveTab("risks");
    } else if (cleanCmd.includes("logistique") || cleanCmd === "logistics") {
      setActiveTab("logistics");
    } else if (cleanCmd.includes("export")) {
      setActiveTab("exports");
    } else if (cleanCmd.includes("import")) {
      setActiveTab("imports");

    } else if (cleanCmd.includes("finance") || cleanCmd.includes("affaire") || cleanCmd.includes("prev") || cleanCmd === "finance") {
      setActiveTab("finance");
    } else if (cleanCmd.includes("securite") || cleanCmd === "cybersecurity") {
      setActiveTab("cybersecurity");
    } else if (cleanCmd.includes("user") || cleanCmd.includes("utilis")) {
      setActiveTab("admin-users");
    } else if (cleanCmd === "executive" || cleanCmd.includes("board") || cleanCmd.includes("pilotage")) {
      setActiveTab("executive");
    } else if (cleanCmd.includes("pdf") || cleanCmd.includes("report") || cleanCmd.includes("rapport")) {
      setShowReportModal(true);
    } else if (cleanCmd.includes("theme") || cleanCmd.includes("sombre") || cleanCmd.includes("clair")) {
      toggleTheme();
    } else if (cleanCmd.includes("aide") || cleanCmd.includes("help")) {
      alert("Commandes disponibles : 'fraude', 'logistique', 'finance', 'imports', 'exports', 'pdf', 'theme', 'pilotage'");
    } else {
      alert(`Commande '${cmd}' non reconnue. Tapez 'help' pour la liste.`);
    }
    setCommandText("");
    setShowCommandSuggestions(false);
  };


  // Global Filters
  const [filterYear, setFilterYear] = useState('2021');
  const [filterCountry, setFilterCountry] = useState('');
  const [filterBank, setFilterBank] = useState('');
  const [filterOptions, setFilterOptions] = useState({ years: [], countries: [], banks: [] });

  // Selected Dossier for Timeline Modal
  const [selectedDossier, setSelectedDossier] = useState(null);

  // Load Auth State
  const checkAuth = () => {
    const token = localStorage.getItem('orbus_token');
    const storedUsername = localStorage.getItem('orbus_username');
    const storedRole = localStorage.getItem('orbus_role');
    const storedBureau = localStorage.getItem('orbus_bureau');

    if (token && storedUsername && storedRole) {
      setAuthenticated(true);
      setUsername(storedUsername);
      setRole(storedRole);
      setBureau(storedBureau || '');
      return true;
    } else {
      setAuthenticated(false);
      setLoading(false);
      return false;
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const fetchFilterOptions = async () => {
    try {
      const res = await fetchWithAuth('/api/filter-options');
      if (res.ok) {
        const data = await res.json();
        setFilterOptions(data);
      }
    } catch (e) {
      console.error("Error loading filter options:", e);
    }
  };

  useEffect(() => {
    if (authenticated) {
      fetchFilterOptions();
    }
  }, [authenticated]);

  // Fetch Dashboard Data & Dossiers Preview & Budget Alerts
  const fetchData = async () => {
    if (!authenticated) return;
    setLoading(true);
    try {
      // Build filters query
      let query = '';
      if (filterYear) query += `year=${encodeURIComponent(filterYear)}&`;
      if (filterCountry) query += `country=${encodeURIComponent(filterCountry)}&`;
      if (filterBank) query += `bank=${encodeURIComponent(filterBank)}&`;

      // Fetch Dashboard stats
      const statsPromise = fetchWithAuth(`/api/dashboard-data?${query}`).then(async res => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Erreur de chargement des statistiques.");
        }
        return res.json();
      });
      const filtersQuery = [
        filterYear ? `year=${encodeURIComponent(filterYear)}` : null,
        filterCountry ? `country=${encodeURIComponent(filterCountry)}` : null,
        filterBank ? `bank=${encodeURIComponent(filterBank)}` : null,
      ].filter(Boolean).join('&');

      // Fetch Dossiers preview
      const dossiersPromise = fetchWithAuth(`/api/dossiers-preview${filtersQuery ? `?${filtersQuery}` : ''}`).then(async res => {
        if (!res.ok) throw new Error("Erreur de chargement des dossiers.");
        return res.json();
      }).catch(() => []);
      
      const [statsData, previewDossiers] = await Promise.all([statsPromise, dossiersPromise]);
      setDashboardData(statsData);
      setDossiers(previewDossiers);

      // Fetch Budget alerts for admin / direction
      if (role === 'admin' || role === 'direction') {
        const alertResp = await fetchWithAuth('/api/direction/budget-alerts');
        if (alertResp.ok) {
          const alertData = await alertResp.json();
          if (alertData.alert) {
            setBudgetAlert(alertData.message);
          } else {
            setBudgetAlert(null);
          }
        }
      }
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      setDashboardData({ error: err.message || "Erreur de connexion au serveur." });
    } finally {
      setLoading(false);
    }
  };

  // Handle PDF report generation & authenticated download
  const handleGeneratePDF = async () => {
    setPdfLoading(true);
    try {
      const response = await fetchWithAuth(`/api/direction/generate-pdf-report?type=${selectedReportType}&anonymize=${anonymizeData}&year=${filterYear}&country=${filterCountry}&bank=${filterBank}&reportMonth=${reportMonth}&reportYear=${reportYear}`);
      if (!response.ok) {
        throw new Error("Impossible de générer le rapport. Veuillez vérifier que les statistiques de modélisation ont été générées.");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Rapport_${selectedReportType}_Sentinel.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setShowReportModal(false);
    } catch (err) {
      console.error(err);
      alert(err.message || "Erreur lors de la génération du rapport PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) {
      fetchData();
    }
  }, [authenticated, filterYear, filterCountry, filterBank]);

  // Target/Cibler action inside Dossiers Preview
  const handleCiblerDossier = async (dossierNum) => {
    try {
      const response = await fetchWithAuth('/api/inspecteur/mark-inspection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dossier_num: String(dossierNum) })
      });
      if (response.ok) {
        // Refresh preview list
        fetchData();
      } else {
        alert("Erreur lors du ciblage du dossier.");
      }
    } catch (err) {
      console.error(err);
      alert("Erreur de connexion.");
    }
  };

  if (!authenticated) {
    return <Login onLoginSuccess={() => checkAuth()} />;
  }

  // RBAC Tab visibility logic
  const isTabVisible = (tabId) => {
    if (role === 'admin') {
      return true; // Admin sees all tabs
    }
    
    if (tabId === 'executive') return true;

    if (role === 'direction') {
      return ['imports', 'exports', 'logistics', 'business', 'finance'].includes(tabId);
    }
    if (role === 'inspecteur') {
      return ['imports', 'exports', 'risks'].includes(tabId);
    }
    if (role === 'transitaire') {
      return ['imports', 'exports'].includes(tabId);
    }
    if (role === 'partenaire') {
      return ['logistics'].includes(tabId);
    }
    if (role === 'statisticien' || role === 'journaliste') {
      return ['imports', 'exports', 'logistics', 'finance'].includes(tabId);
    }
    return false;
  };

  // Human role label
  let roleLabel = role;
  if (role === 'admin') roleLabel = "Administrateur";
  else if (role === 'direction') roleLabel = "Direction Générale";
  else if (role === 'inspecteur') roleLabel = `Inspecteur Bureau (${bureau || 'Tous'})`;
  else if (role === 'transitaire') roleLabel = `Transitaire (PPM: ${bureau || 'N/A'})`;
  else if (role === 'partenaire') roleLabel = `Partenaire Financier (${bureau || 'N/A'})`;
  else if (role === 'statisticien') roleLabel = "Statisticien / Chercheur";
  else if (role === 'journaliste') roleLabel = "Journaliste / Presse";

  // Tab Details for Page Header
  const tabDetails = {
    executive: {
      label: "Dashboard Exécutif",
      desc: "Vue d'ensemble de l'activité commerciale, KPIs macro et cartographie.",
      icon: LayoutDashboard
    },
    imports: {
      label: "Analyses Importations",
      desc: "Provenance, évolution et répartition logistique des importations.",
      icon: TrendingUp
    },
    exports: {
      label: "Analyses Exportations",
      desc: "Destinations, volumes et valeur commerciale des exportations.",
      icon: TrendingDown
    },
    risks: {
      label: "Analyse des Risques",
      desc: "Détection d'anomalies, prévisions de ciblage et simulateurs IA.",
      icon: ShieldAlert
    },
    logistics: {
      label: "Segmentation & Logistique",
      desc: "Flux opérationnels, K-Means et indice de solvabilité importateurs.",
      icon: Layers
    },
    business: {
      label: "Prospection Business",
      desc: "Opportunités de prospection commerciale et ciblage bancaire.",
      icon: SearchIcon
    },

    finance: {
      label: "Finances & Prévisions",
      desc: "Chiffres d'affaires, classement des gros importateurs et projections financières.",
      icon: BarChart3
    },
    cybersecurity: {
      label: "Audit IT & Cybersécurité  ",
      desc: "Suivi d'accès réseau, audit de sécurité et détection d'intrusions.",
      icon: Cpu
    },
    'admin-users': {
      label: "Gestion Utilisateurs",
      desc: "Administration des comptes et droits d'accès SQLite.",
      icon: Users
    }
  };

  const showFiltersBar = role === 'admin' || role === 'direction' || role === 'inspecteur';
  const activeTabInfo = tabDetails[activeTab] || tabDetails.executive;

  return (
    <div className={`app-container ${mobileMenuOpen ? 'sidebar-open' : ''}`}>
      {/* Decorative Network Overlay for Command Center Atmosphere */}
      <div className="network-overlay"></div>
      
      {/* Mobile Navigation Header */}
      <div className="mobile-navbar">
        <button className="hamburger-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} aria-label="Toggle Navigation">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {mobileMenuOpen ? (
              <line x1="18" y1="6" x2="6" y2="18"></line>
            ) : (
              <>
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </>
            )}
          </svg>
        </button>
        <div className="mobile-logo">
          <img src="assets/gainde_logo_transparent.png" alt="Orbus Logo" style={{ height: '32px', objectFit: 'contain' }} />
          <span>Orbus Sentinel</span>
        </div>
        <div className="mobile-profile-avatar" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {username.slice(0, 2).toUpperCase()}
        </div>
      </div>

      {/* Drawer Overlay Backdrop */}
      {mobileMenuOpen && <div className="sidebar-backdrop" onClick={() => setMobileMenuOpen(false)}></div>}

      {/* Left Sidebar Menu */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <img src="assets/gainde_logo_transparent.png" alt="Orbus Sentinel Logo" />
          <div className="sidebar-logo-text">
            <h1>Orbus Sentinel</h1>
            {/* <p>saaytu business</p> */}
          </div>
        </div>
        <nav className="sidebar-menu">
          {Object.entries(tabDetails).map(([tabId, info]) => {
            if (!isTabVisible(tabId)) return null;
            const IconComp = info.icon;
            return (
              <button
                key={tabId}
                className={`sidebar-item ${activeTab === tabId ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(tabId);
                  setMobileMenuOpen(false);
                }}
              >
                <IconComp size={18} />
                <span>{info.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Command Center Status and Silhouettes */}
        <div className="sidebar-deco">
          <div className="sidebar-deco-header">
            <span>SECURE STREAM</span>
            <span className="pulse-dot"></span>
          </div>
          <div className="sidebar-deco-icons">
            {/* Cargo ship */}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="deco-svg"><path d="M2 17h20l-2 4H4l-2-4ZM5 17V9h3v8M16 17V7h3v10M10 17v-5h4v5"/></svg>
            {/* Airplane */}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="deco-svg"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5Z"/></svg>
            {/* Truck */}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="deco-svg"><rect x="1" y="3" width="15" height="13" rx="2"/><path d="M16 8h4l3 3v5h-7V8ZM1 18h22M5 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM19 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/></svg>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-info">
            <div className="user-avatar">{username.slice(0, 2).toUpperCase()}</div>
            <div className="user-details">
              <span className="user-name">{username}</span>
              <span className="user-role">{roleLabel}</span>
            </div>
          </div>
          <button className="logout-btn" onClick={performLogout}>Se Déconnecter</button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Top Header Bar inside Workspace */}
        <div className="main-header">
          <div className="search-bar-container" style={{ position: 'relative' }}>
            <SearchIcon size={16} style={{ color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="Assistant intelligent... (ex: 'fraude', 'pdf', 'theme')" 
              className="search-input" 
              value={commandText}
              onChange={(e) => {
                setCommandText(e.target.value);
                setShowCommandSuggestions(true);
              }}
              onFocus={() => setShowCommandSuggestions(true)}
              onBlur={() => setTimeout(() => setShowCommandSuggestions(false), 250)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleExecuteCommand(commandText);
                }
              }}
            />
            {showCommandSuggestions && (
              <div className="smart-console-suggestions">
                <div className="smart-suggestion-header">Pilotage Sentinel IA</div>
                <div className="smart-suggestion-item" onMouseDown={() => handleExecuteCommand("risks")}>
                  🎯 Supervision des Risques ('fraude')
                </div>
                <div className="smart-suggestion-item" onMouseDown={() => handleExecuteCommand("logistics")}>
                  🚢 Stress-Test Logistique ('logistique')
                </div>
                <div className="smart-suggestion-item" onMouseDown={() => handleExecuteCommand("pdf")}>
                  ⚡ Générer Rapport  ('pdf')
                </div>
                <div className="smart-suggestion-item" onMouseDown={() => handleExecuteCommand("theme")}>
                  🌓 Basculer Thème ('theme')
                </div>
                <div className="smart-suggestion-item" onMouseDown={() => handleExecuteCommand("executive")}>
                  📊 Tableau de bord ('pilotage')
                </div>
              </div>
            )}
          </div>
          
          <div className="header-actions">
            {(role === 'admin' || role === 'direction' || role === 'statisticien' || role === 'inspecteur') && (
              <button 
                className="premium-pdf-btn" 
                title="Générer Rapport Décisionnel (PDF)" 
                onClick={() => setShowReportModal(true)}
                disabled={pdfLoading}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 12 15 15"/></svg>
                <span>{pdfLoading ? 'Génération...' : 'Générateur de Rapport'}</span>
              </button>
            )}
            


            <button className="header-action-btn alert-badge-container" title="Notifications">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
              <span className="alert-badge-dot">10</span>
            </button>
            
            <button className="header-action-btn" title="Changer de thème (Clair/Sombre)" onClick={toggleTheme}>
              {theme === 'light' ? (
                // Moon icon for switching to dark theme
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              ) : (
                // Sun icon for switching to light theme
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
              )}
            </button>
            
            <div className="header-profile">
              <div className="user-avatar-small">{username.slice(0, 2).toUpperCase()}</div>
              <span className="header-username">{username}</span>
            </div>
          </div>
        </div>
        
        {/* Content Header Title */}
        <div className="content-header">
          <div className="page-title">
            <h2>{activeTabInfo.label}</h2>
            <p>{activeTabInfo.desc}</p>
          </div>
        </div>

        {/* Budget Alerts Banner */}
        {budgetAlert && (
          <div id="budget-alert-banner" style={{ display: 'flex', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.25)', padding: '15px 20px', borderRadius: '12px', color: '#fca5a5', fontWeight: '500', fontSize: '0.9rem', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#ef4444' }}><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>{budgetAlert}</span>
            </div>
            <button onClick={() => setBudgetAlert(null)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', fontWeight: 'bold', color: '#fca5a5', cursor: 'pointer' }}>&times;</button>
          </div>
        )}

        {/* Global Filters Bar */}
        {showFiltersBar && (
          <div className="filters-container">
            <div style={{ fontWeight: 'bold', color: 'var(--primary-light)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
              Filtres Globaux Dynamiques :
            </div>
            
            <div className="filter-group">
              <label>Année :</label>
              <select 
                value={filterYear} 
                onChange={(e) => setFilterYear(e.target.value)}
              >
                <option value="">Toutes</option>
                {filterOptions.years.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <label>Pays :</label>
              <select 
                value={filterCountry} 
                onChange={(e) => setFilterCountry(e.target.value)}
                style={{ minWidth: '150px', maxWidth: '200px' }}
              >
                <option value="">Tous les pays</option>
                {filterOptions.countries.map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1).toLowerCase()}</option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <label>Banque :</label>
              <select 
                value={filterBank} 
                onChange={(e) => setFilterBank(e.target.value)}
                style={{ minWidth: '150px', maxWidth: '200px' }}
              >
                <option value="">Toutes les banques</option>
                {filterOptions.banks.map(b => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <button 
              onClick={() => { setFilterYear(''); setFilterCountry(''); setFilterBank(''); }} 
              style={{ padding: '8px 15px', borderRadius: '8px', border: '1px solid var(--border)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-muted)', fontFamily: 'inherit', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s', marginLeft: 'auto' }}
            >
              Réinitialiser
            </button>
          </div>
        )}

        {/* Tab Content Rendering */}
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
            <div className="loader"></div>
          </div>
        ) : (
          <div className="tab-content active">
            {activeTab === 'executive' && (
              <DashboardTab 
                data={dashboardData} 
                files={dossiers} 
                role={role} 
                onFileClick={(row) => setSelectedDossier(row)}
                onTargetFile={handleCiblerDossier}
                theme={theme}
                lang={lang}
                filterOptions={filterOptions}
              />
            )}
            {activeTab === 'imports' && <ImportsTab data={dashboardData} theme={theme} lang={lang} />}
            {activeTab === 'exports' && <ExportsTab data={dashboardData} theme={theme} lang={lang} />}
            {activeTab === 'risks' && <RisksTab data={dashboardData} role={role} theme={theme} lang={lang} />}
            {activeTab === 'logistics' && <LogisticsTab data={dashboardData} role={role} theme={theme} lang={lang} />}
            {activeTab === 'business' && (
              <BusinessTab 
                filters={{ year: filterYear, country: filterCountry, bank: filterBank }} 
                lang={lang}
              />
            )}

            {activeTab === 'finance' && <FinanceTab theme={theme} filters={{ year: filterYear, country: filterCountry, bank: filterBank }} />}
            {activeTab === 'cybersecurity' && <CybersecurityTab role={role} lang={lang} />}
            {activeTab === 'admin-users' && <AdminUsersTab lang={lang} />}
          </div>
        )}
      </div>

      {/* Floating Chatbot */}
      <Chatbot />

      {/* Timeline Modal */}
      {selectedDossier && (
        <DossierTimelineModal 
          dossier={selectedDossier} 
          onClose={() => setSelectedDossier(null)} 
        />
      )}


      {/* Premium Multi-Report Selection Modal */}
      {showReportModal && (
        <div 
          className="report-modal-overlay"
          onClick={() => setShowReportModal(false)}
        >
          <div 
            className="report-modal-container"
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '15px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                  Générateur de Rapports Douaniers IA
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Générer des synthèses d'activité douanière formatées officiellement</span>
              </div>
              <button 
                onClick={() => setShowReportModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem', transition: 'color 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', borderRadius: '50%' }}
                onMouseEnter={(e) => e.target.style.color = '#ef4444'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-muted)'}
              >
                ✕
              </button>
            </div>

            {/* Grid of Report Options */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px', marginBottom: '20px' }}>
              {[
                { 
                  id: 'executive', 
                  name: 'Rapport Décisionnel', 
                  desc: 'Synthèse globale d\'activité pour la Direction Générale (KPIs, Profil de Risque, Prévisions).',
                  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/></svg>
                },
                { 
                  id: 'fraud', 
                  name: 'Audit des Fraudes', 
                  desc: 'Détail des ciblages Z-Score, Isolation Forest et directives opérationnelles d\'inspection.',
                  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                },
                { 
                  id: 'logistics', 
                  name: 'Stress-Test Logistique', 
                  desc: 'Répartition des transports, retards des documents administratifs et simulation d\'incidents.',
                  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
                },
                { 
                  id: 'partners', 
                  name: 'Fiabilité Importateurs', 
                  desc: 'Segmentation K-Means des comptes, niveaux de conformité et audit de solvabilité financière.',
                  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                },
                { 
                  id: 'exploitation', 
                  name: 'Exploitation Mensuelle', 
                  desc: 'Durées réelles et délais de traitement des 60 pôles (conformément au rapport d\'activité).',
                  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                }
              ].map(opt => {
                const isSelected = selectedReportType === opt.id;
                return (
                  <div 
                    key={opt.id}
                    onClick={() => setSelectedReportType(opt.id)}
                    className={`report-card-option ${isSelected ? 'selected' : ''}`}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isSelected ? '#22d3ee' : 'var(--text-main)', transition: 'color 0.2s' }}>
                        {opt.icon}
                        <strong style={{ fontSize: '0.86rem' }}>{opt.name}</strong>
                      </div>
                      <span className="report-radio-indicator"></span>
                    </div>
                    <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: 0, lineHeight: '1.4' }}>{opt.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Dynamic Month/Year Selector for Exploitation Report */}
            {selectedReportType === 'exploitation' && (
              <div style={{ display: 'flex', gap: '15px', background: 'rgba(6, 182, 212, 0.05)', padding: '12px 15px', borderRadius: '12px', border: '1px solid rgba(6, 182, 212, 0.15)', marginBottom: '15px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>Mois d'exploitation</label>
                  <select 
                    value={reportMonth} 
                    onChange={(e) => setReportMonth(e.target.value)}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border)', borderRadius: '8px', padding: '6px 10px', color: 'white', fontSize: '0.8rem' }}
                  >
                    <option value="01">Janvier</option>
                    <option value="02">Février</option>
                    <option value="03">Mars</option>
                    <option value="04">Avril</option>
                    <option value="05">Mai</option>
                    <option value="06">Juin</option>
                    <option value="07">Juillet</option>
                    <option value="08">Août</option>
                    <option value="09">Septembre</option>
                    <option value="10">Octobre</option>
                    <option value="11">Novembre</option>
                    <option value="12">Décembre</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>Année d'exploitation</label>
                  <select 
                    value={reportYear} 
                    onChange={(e) => setReportYear(e.target.value)}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border)', borderRadius: '8px', padding: '6px 10px', color: 'white', fontSize: '0.8rem' }}
                  >
                    {filterOptions.years.map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Anonymize Option */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.02)', padding: '12px 15px', borderRadius: '12px', border: '1px solid var(--border)', marginBottom: '25px', transition: 'all 0.2s' }}>
              <input 
                type="checkbox" 
                id="anonymize-pdf" 
                checked={anonymizeData}
                onChange={(e) => setAnonymizeData(e.target.checked)}
                style={{ cursor: 'pointer', width: '16px', height: '16px', accentColor: '#06b6d4' }}
              />
              <label htmlFor="anonymize-pdf" style={{ fontSize: '0.8rem', color: 'var(--text-main)', cursor: 'pointer', fontWeight: 500, userSelect: 'none' }}>
                Anonymiser les noms d'importateurs et d'utilisateurs (Recherche & Statistiques)
              </label>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button 
                onClick={() => setShowReportModal(false)}
                className="login-btn"
                style={{ margin: 0, padding: '8px 20px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: '10px' }}
              >
                Annuler
              </button>
              <button 
                onClick={handleGeneratePDF}
                disabled={pdfLoading}
                className="login-btn"
                style={{ 
                  margin: 0, 
                  padding: '8px 25px', 
                  background: 'linear-gradient(135deg, #06b6d4, #0891b2)', 
                  border: 'none', 
                  boxShadow: '0 4px 15px rgba(6, 182, 212, 0.25)',
                  color: 'white',
                  fontWeight: 'bold',
                  borderRadius: '10px'
                }}
              >
                {pdfLoading ? 'Génération du PDF...' : 'Télécharger le Rapport'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
