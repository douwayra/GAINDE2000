import React, { useState, useEffect } from 'react';
import { 
  Ship, 
  Anchor, 
  FileText, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp, 
  Layers, 
  Activity, 
  Search, 
  Filter, 
  Download, 
  UserCheck, 
  BarChart2, 
  Navigation, 
  ShieldAlert, 
  ArrowUpRight,
  Database,
  Building,
  Calendar,
  ChevronRight,
  Eye,
  ShieldCheck,
  Zap
} from 'lucide-react';
import AnimatedCounter from './AnimatedCounter';

export default function IpmdSuiteTab({ role, theme, lang }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('ALL');

  useEffect(() => {
    fetch('/api/dashboard-data')
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error("Erreur chargement IPMD data:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="card-glass" style={{ padding: '60px', textAlign: 'center' }}>
        <div className="spinner" style={{ margin: '0 auto 20px' }}></div>
        <h3>Chargement de la Suite Infinity Sentinel-2 (IPMD)...</h3>
        <p style={{ color: 'var(--text-muted)' }}>Initialisation du flux maritime et des formalités du Port de Dakar...</p>
      </div>
    );
  }

  // KPIs Portuaires Synthétiques
  const kpiData = [
    { label: "Navires en Escale (PAD)", value: 42, subtext: "14 en Rade Nord, 28 à Quai", icon: Ship, color: "#3b82f6" },
    { label: "Volume Conteneurs (TEU)", value: "18,450", subtext: "+12% vs mois dernier", icon: Anchor, color: "#10b981" },
    { label: "Délai Moyen Formalités", value: "18.4 h", subtext: "Objectif Réglementaire < 24h", icon: Clock, color: "#f59e0b" },
    { label: "Taux Conformité Consignataires", value: "94.2%", subtext: "32 Acteurs Évalués", icon: ShieldCheck, color: "#8b5cf6" }
  ];

  // Liste des formalités portuaires
  const formalitesList = [
    { code: "BAE-2026-9041", navire: "CMA CGM ANTOINE DE SAINT EXUPERY", bl: "BL-CMA-99412", formalite: "BAE Douanes", delai: "14.2h", statut: "VALIDE", acteur: "CMA CGM SENEGAL" },
    { code: "BAD-2026-8812", navire: "MAERSK MC-KINNEY MOLLER", bl: "BL-MSK-44120", formalite: "BAD Armateur", delai: "22.5h", statut: "VALIDE", acteur: "MAERSK SENEGAL" },
    { code: "DO-2026-7741", navire: "MSC OSCAR", bl: "BL-MSC-77811", formalite: "Ordre de Livraison (DO)", delai: "08.1h", statut: "EN_COURS", acteur: "MSC SENEGAL" },
    { code: "VISA-2026-6623", navire: "GRIMALDI GRANDE NIGERIA", bl: "BL-GRM-11204", formalite: "VISA PAD Portail", delai: "04.5h", statut: "VALIDE", acteur: "GRIMALDI SENEGAL" },
    { code: "QUITUS-2026-5510", navire: "HAPAG LLOYD EXPRESS", bl: "BL-HPL-33901", formalite: "Quitus Sortie Port", delai: "02.8h", statut: "VALIDE", acteur: "HAPAG LLOYD SENEGAL" }
  ];

  // Cross matching anomalies Douane x Port
  const crossMatchAnomalies = [
    { id: "CROSS-001", manifeste: "MAN-2026-08912", bl: "BL-CMA-99412", ecart: "Conteneur 20ft (Douane) vs 40ft High Cube (Port)", risque: "CRITIQUE", perte_estimee: "145 000 000 CFA" },
    { id: "CROSS-002", manifeste: "MAN-2026-08945", bl: "BL-MSK-44120", ecart: "Pesée Douane 12.5T vs Pesée Port 28.4T (+127%)", risque: "ÉLEVÉ", perte_estimee: "68 000 000 CFA" },
    { id: "CROSS-003", manifeste: "MAN-2026-08990", bl: "BL-GRM-11204", ecart: "BAE Douane accordé mais VISA PAD non visé", risque: "MOYEN", perte_estimee: "18 500 000 CFA" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
      
      {/* Header Banner */}
      <div className="card-glass" style={{ 
        padding: '24px 30px', 
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 58, 138, 0.9) 100%)',
        borderLeft: '6px solid #3b82f6',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderRadius: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <img src="/assets/infinity_logo.png" alt="Infinity Sentinel Logo" style={{ height: '38px', objectFit: 'contain' }} />
            <h2 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#ffffff', margin: 0 }}>
              Infinity Sentinel-2 — Port Autonome de Dakar (IPMD)
            </h2>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0 }}>
            Supervision intelligente du Guichet Unique Maritimes, suivi des navires AIS, détection d'anomalies Douane x Port et SLAs.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn-glass"
            onClick={() => alert("Génération du rapport portuaire IPMD PDF...")}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', background: '#3b82f6', color: '#ffffff', fontWeight: '600', borderRadius: '8px' }}
          >
            <Download size={16} /> Rapport Portuaire PDF
          </button>
        </div>
      </div>

      {/* KPIs Section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '18px' }}>
        {kpiData.map((kpi, idx) => {
          const IconComp = kpi.icon;
          return (
            <div key={idx} className="card-glass" style={{ padding: '20px', borderRadius: '14px', borderTop: `4px solid ${kpi.color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '600' }}>{kpi.label}</span>
                <div style={{ padding: '8px', borderRadius: '10px', background: `${kpi.color}15`, color: kpi.color }}>
                  <IconComp size={20} />
                </div>
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--text-primary)', marginBottom: '4px' }}>
                {kpi.value}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: '500' }}>
                {kpi.subtext}
              </div>
            </div>
          );
        })}
      </div>

      {/* Sub-Navigation Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', overflowX: 'auto' }}>
        {[
          { id: 'overview', label: 'Vue Globale Port', icon: LayoutDashboard },
          { id: 'formalites', label: 'Formalités (BAE/BAD/DO/VISA)', icon: FileText },
          { id: 'navires', label: 'Navires & Escale AIS', icon: Ship },
          { id: 'crossmatch', label: 'Cross-Matching Douane x Port', icon: ShieldAlert },
          { id: 'slas', label: 'Performance SLAs Consignataires', icon: BarChart2 }
        ].map(tab => {
          const IconC = tab.icon;
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                borderRadius: '10px',
                border: 'none',
                background: isActive ? '#3b82f6' : 'transparent',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: isActive ? '600' : '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <IconC size={16} /> {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content: Overview & Crossmatching */}
      {activeSubTab === 'crossmatch' ? (
        <div className="card-glass" style={{ padding: '24px', borderRadius: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldAlert color="#ef4444" size={22} /> Détections de Cross-Matching Intelligent Douane x Port (GAINDE 2000 x PAD)
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
                Rapprochement en temps réel des manifests maritimes et des déclarations douanières pour détecter les fraudes de tonnage et d'évaluation.
              </p>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px' }}>ID Anomalie</th>
                <th style={{ padding: '12px' }}>N° Manifeste</th>
                <th style={{ padding: '12px' }}>N° BL</th>
                <th style={{ padding: '12px' }}>Écart Constaté</th>
                <th style={{ padding: '12px' }}>Severité</th>
                <th style={{ padding: '12px' }}>Perte Présumée CFA</th>
              </tr>
            </thead>
            <tbody>
              {crossMatchAnomalies.map((ano, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '12px', fontWeight: '700', color: '#3b82f6' }}>{ano.id}</td>
                  <td style={{ padding: '12px' }}>{ano.manifeste}</td>
                  <td style={{ padding: '12px' }}>{ano.bl}</td>
                  <td style={{ padding: '12px', color: 'var(--text-primary)' }}>{ano.ecart}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      padding: '4px 10px', 
                      borderRadius: '6px', 
                      fontSize: '0.75rem', 
                      fontWeight: '700',
                      background: ano.risque === 'CRITIQUE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: ano.risque === 'CRITIQUE' ? '#ef4444' : '#f59e0b'
                    }}>
                      {ano.risque}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontWeight: '700', color: '#ef4444' }}>{ano.perte_estimee}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card-glass" style={{ padding: '24px', borderRadius: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '700', margin: 0 }}>
              Suivi Temps Réel des Formalités Portuaires (BAE, BAD, DO, VISA PAD)
            </h3>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px' }}>Code Dossier</th>
                <th style={{ padding: '12px' }}>Navire</th>
                <th style={{ padding: '12px' }}>N° BL</th>
                <th style={{ padding: '12px' }}>Formalité</th>
                <th style={{ padding: '12px' }}>Délai Traitement</th>
                <th style={{ padding: '12px' }}>Consignataire</th>
                <th style={{ padding: '12px' }}>Statut</th>
              </tr>
            </thead>
            <tbody>
              {formalitesList.map((f, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '12px', fontWeight: '700', color: '#3b82f6' }}>{f.code}</td>
                  <td style={{ padding: '12px' }}>{f.navire}</td>
                  <td style={{ padding: '12px' }}>{f.bl}</td>
                  <td style={{ padding: '12px', fontWeight: '600' }}>{f.formalite}</td>
                  <td style={{ padding: '12px' }}>{f.delai}</td>
                  <td style={{ padding: '12px' }}>{f.acteur}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      padding: '4px 10px', 
                      borderRadius: '6px', 
                      fontSize: '0.75rem', 
                      fontWeight: '700',
                      background: f.statut === 'VALIDE' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                      color: f.statut === 'VALIDE' ? '#10b981' : '#3b82f6'
                    }}>
                      {f.statut}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}
