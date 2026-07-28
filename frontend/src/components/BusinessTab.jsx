import React, { useState, useEffect } from 'react';
import { formatCFA, fetchWithAuth } from '../utils/api';

export default function BusinessTab({ filters }) {
  const [prospects, setProspects] = useState([]);
  const [filteredProspects, setFilteredProspects] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when searchQuery or prospects change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, prospects]);

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.ceil(filteredProspects.length / ITEMS_PER_PAGE) || 1;
  const paginatedProspects = filteredProspects.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  useEffect(() => {
    const fetchBusinessProspects = async () => {
      setLoading(true);
      setErrorMsg('');
      try {
        const { year, country, bank } = filters;
        let url = '/api/business-prospects?';
        if (year) url += `year=${encodeURIComponent(year)}&`;
        if (country) url += `country=${encodeURIComponent(country)}&`;
        if (bank) url += `bank=${encodeURIComponent(bank)}&`;

        const response = await fetchWithAuth(url);
        if (!response.ok) throw new Error("Erreur de chargement");
        const data = await response.json();
        setProspects(data);
        setFilteredProspects(data);
      } catch (err) {
        console.error(err);
        setErrorMsg("Erreur de chargement des prospects douaniers.");
      } finally {
        setLoading(false);
      }
    };

    fetchBusinessProspects();
  }, [filters]);

  useEffect(() => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) {
      setFilteredProspects(prospects);
      return;
    }

    const filtered = prospects.filter(p => 
      (p.NOM_IMPORTATEUR || '').toLowerCase().includes(query) ||
      (p.DESIGNATIONCOMMERCIALE || '').toLowerCase().includes(query) ||
      (p.BANQUE || '').toLowerCase().includes(query) ||
      (p.ASSURANCE || '').toLowerCase().includes(query)
    );
    setFilteredProspects(filtered);
  }, [searchQuery, prospects]);

  return (
    <div className="dashboard-row full-width">
      <div className="chart-card">
        <div className="chart-card-title" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '15px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Prospection Business & Ciblage Commercial</span>
          <span style={{ fontSize: '0.8rem', background: 'var(--primary-light)', color: 'white', padding: '4px 10px', borderRadius: '12px', fontWeight: '600' }}>
            Accès Directeur / Admin
          </span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.5', marginBottom: '20px' }}>
          Identifiez de nouveaux prospects en analysant quels importateurs sénégalais traitent quelles marchandises, quelles sont leurs banques de financement et compagnies d'assurance actuelles, ainsi que les volumes de transactions associés. 
          <strong> Utilisez les filtres globaux ci-dessus pour affiner la prospection par Année, Pays de provenance ou Banque partenaire.</strong>
        </p>
         <div style={{ display: 'flex', gap: '15px', marginBottom: '15px', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'space-between' }}>
          <div style={{ position: 'relative', width: '350px' }}>
            <input 
              type="text" 
              placeholder="Rechercher par importateur, marchandise, banque..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '10px 15px', paddingLeft: '35px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', fontSize: '0.9rem', outline: 'none', transition: 'border-color 0.2s', background: 'var(--bg-app)', color: 'var(--text-main)' }}
            />
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
            </svg>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '600' }}>
              {loading ? 'Chargement...' : `${filteredProspects.length} prospects`}
            </div>
            {!loading && (
              <div className="table-pagination" style={{ margin: 0 }}>
                <button
                  className="pagination-btn"
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                >
                  Précédent
                </button>
                <span className="pagination-info">
                  Page {currentPage} / {totalPages}
                </span>
                <button
                  className="pagination-btn"
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                >
                  Suivant
                </button>
              </div>
            )}
          </div>
        </div>
        
        <div className="data-table-container" style={{ maxHeight: '500px', overflowY: 'auto' }}>
          <table>
            <thead style={{ position: 'sticky', top: 0, background: 'var(--card-bg)', zIndex: 10 }}>
              <tr>
                <th>Nom Importateur</th>
                <th>Désignation Marchandise</th>
                <th>Banque Garante</th>
                <th>Compagnie d'Assurance</th>
                <th style={{ textAlign: 'right' }}>Valeur Cumulée (CFA)</th>
                <th style={{ textAlign: 'center' }}>Opérations</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', justifyContent: 'center' }}>
                       <div className="loader"></div>
                      <span>Chargement des données de prospection en cours (analyse DuckDB)...</span>
                    </div>
                  </td>
                </tr>
              ) : errorMsg ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', color: 'var(--danger)', fontWeight: '600', padding: '20px' }}>
                    {errorMsg}
                  </td>
                </tr>
              ) : filteredProspects.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px' }}>
                    Aucun prospect ne correspond aux critères de recherche.
                  </td>
                </tr>
              ) : (
                paginatedProspects.map((p, idx) => (
                  <tr key={idx}>
                    <td><strong>{p.NOM_IMPORTATEUR}</strong></td>
                    <td><span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{p.DESIGNATIONCOMMERCIALE}</span></td>
                    <td><span className="badge" style={{ background: 'rgba(20, 85, 162, 0.1)', color: 'var(--primary)', fontWeight: '600' }}>{p.BANQUE}</span></td>
                    <td><span className="badge" style={{ background: 'rgba(109, 181, 26, 0.1)', color: 'var(--success)', fontWeight: '600' }}>{p.ASSURANCE}</span></td>
                    <td style={{ textAlign: 'right', fontWeight: 'bold', color: 'var(--text-main)' }}>{formatCFA(p.total_valeur_cfa)}</td>
                    <td style={{ textAlign: 'center' }}><span style={{ fontWeight: '600', color: 'var(--text-muted)' }}>{p.count_dossiers || 0}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
