import React, { useState, useEffect } from 'react';

export default function PaymentTab() {
  const [dossierNum, setFileNum] = useState('');
  const [bankCode, setBankCode] = useState('SGBS');
  const [amount, setAmount] = useState('');

  const [payments] = useState([
    { institution: 'SGBS', delay: '1.8 jour', volume: '48 404 files', performance: 'Excellent', perfClass: 'badge-success' },
    { institution: 'CBAO Attijariwafa', delay: '2.1 jours', volume: '40 099 files', performance: "Optimal", perfClass: 'badge-success' },
    { institution: 'BICIS', delay: '3.5 jours', volume: '35 817 files', performance: "Medium", perfClass: 'badge-warning' },
    { institution: 'AXA Assurance', delay: '1.2 jour', volume: '14 447 files', performance: "Very Fast", perfClass: 'badge-success' }
  ]);

  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const filteredPayments = payments.filter(item => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return true;
    return (
      item.institution.toLowerCase().includes(term) ||
      item.delay.toLowerCase().includes(term) ||
      item.volume.toLowerCase().includes(term) ||
      item.performance.toLowerCase().includes(term)
    );
  });

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.ceil(filteredPayments.length / ITEMS_PER_PAGE) || 1;
  const paginatedPayments = filteredPayments.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );
  
  const [statusText, setStatusText] = useState('Statut : Attente de Signature Électronique');
  const [statusStyle, setStatusStyle] = useState({
    background: '#e0f2fe',
    color: '#0369a1'
  });

  const handleSimulateSignature = () => {
    if (!dossierNum.trim()) {
      alert("Veuillez saisir un numéro de dossier.");
      return;
    }
    setStatusStyle({
      background: '#fef3c7',
      color: '#d97706'
    });
    setStatusText(`Statut : Dossier ${dossierNum.trim()} Signé Électriquement (En attente de paiement)`);
  };

  const handleSimulatePayment = () => {
    if (!dossierNum.trim() || !amount.trim()) {
      alert("Veuillez saisir le numéro de dossier et le montant.");
      return;
    }
    setStatusStyle({
      background: '#dcfce7',
      color: '#15803d'
    });
    setStatusText(`Statut : Paiement de ${amount.trim()} CFA validé par ${bankCode} pour le dossier ${dossierNum.trim()} !`);
  };

  return (
    <div className="dashboard-row">
      {/* Signature/Payment Simulator */}
      <div className="chart-card">
        <div className="chart-card-title">Validation Documentaire & Paiement (Orbus Pay)</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px' }}>
          Signez vos engagements douaniers électroniquement et réglez les frais de port.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
          <div className="login-input-group">
            <label htmlFor="pay-dossier-num">Numéro Dossier TPS</label>
            <input 
              type="text" 
              placeholder="ex: 3410294" 
              value={dossierNum}
              onChange={(e) => setFileNum(e.target.value)}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', color: 'var(--text-main)', background: 'var(--card-bg)' }}
            />
          </div>
          <div className="login-input-group">
            <label htmlFor="pay-bank-code">Banque de Règlement / Assureur</label>
            <select 
              value={bankCode}
              onChange={(e) => setBankCode(e.target.value)}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)' }}
            >
              <option value="SGBS">SGBS (Senegal)</option>
              <option value="CBAO">CBAO Groupe Attijariwafa Bank</option>
              <option value="BICIS">BICIS</option>
              <option value="AXA">AXA Assurance (Fret Maritime)</option>
            </select>
          </div>
          <div className="login-input-group">
            <label htmlFor="pay-amount">Montant à régler (CFA)</label>
            <input 
              type="text" 
              placeholder="ex: 15 000 000" 
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', color: 'var(--text-main)', background: 'var(--card-bg)' }}
            />
          </div>
          
          <div 
            style={{ 
              padding: '12px', 
              borderRadius: '8px', 
              fontSize: '0.85rem', 
              fontWeight: 600, 
              textAlign: 'center',
              ...statusStyle
            }}
          >
            {statusText}
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              className="login-btn" 
              onClick={handleSimulateSignature} 
              style={{ background: 'var(--primary)', flex: 1 }}
            >
              Signer le Dossier
            </button>
            <button 
              className="login-btn" 
              onClick={handleSimulatePayment} 
              style={{ background: 'var(--success)', flex: 1 }}
            >
              Payer les Taxes
            </button>
          </div>
        </div>
      </div>
      
      {/* Delays Table */}
      <div className="chart-card">
        <div className="chart-card-title">Délais Moyens de Financement & Couverture</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px' }}>
          Temps moyen de traitement pour la libération des fonds et la signature électronique des garanties.
        </p>

        <div className="table-controls">
          <input
            type="text"
            className="table-search-input"
            placeholder="Rechercher une institution..."
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
              Page {currentPage} / {totalPages} ({filteredPayments.length} institutions)
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
                <th>Institution</th>
                <th>Temps de Réponse Moyen</th>
                <th>Volume Traité</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              {paginatedPayments.length > 0 ? (
                paginatedPayments.map((item, idx) => (
                  <tr key={idx}>
                    <td><strong>{item.institution}</strong></td>
                    <td>{item.delay}</td>
                    <td>{item.volume}</td>
                    <td><span className={`badge ${item.perfClass}`}>{item.performance}</span></td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                    Aucune institution trouvée.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
