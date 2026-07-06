import React from 'react';

export default function FileTimelineModal({ dossier, onClose }) {
  if (!dossier) return null;

  const steps = [
    { id: 'initialise', label: "Soumission Administrative", desc: "Dossier créé et soumis dans le système" },
    { id: 'banque', label: "Validation Banque", desc: "Frais de dossier et garanties financières acquittés" },
    { id: 'encours', label: 'Ciblage & Analyse de Risque', desc: 'Évaluation automatique des risques douaniers' },
    { id: 'liquide', label: "BAE Douane (Liquidation)", desc: "Bon à Enlever (BAE) délivré par l'inspecteur" },
    { id: 'livraison', label: "Livraison Marchandise", desc: "Marchandise libérée et retirée" }
  ];

  let activeIndex = 0;
  const status = (dossier.STATUT_DOSSIER || '').toLowerCase();

  if (status.includes('initialise')) {
    activeIndex = 1;
  } else if (status.includes('paye') || status.includes('valide')) {
    activeIndex = 2;
  } else if (status.includes('encours')) {
    activeIndex = 3;
  } else if (status.includes('liquide')) {
    activeIndex = 4;
  } else if (status.includes('termine') || status.includes('livre')) {
    activeIndex = 5;
  } else {
    activeIndex = 2;
  }

  return (
    <div 
      className="login-overlay" 
      style={{ 
        position: 'fixed', 
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%', 
        background: 'rgba(15,23,42,0.6)', 
        backdropFilter: 'blur(8px)', 
        display: 'flex',
        justifyContent: 'center', 
        alignItems: 'center', 
        zIndex: 10000 
      }}
    >
      <div 
        className="chart-card" 
        style={{ 
          width: '500px', 
          maxWidth: '90%', 
          borderTop: '5px solid var(--primary)', 
          background: 'var(--card-bg)', 
          borderRadius: '20px', 
          padding: '25px', 
          boxShadow: '0 10px 30px rgba(0,0,0,0.15)', 
          position: 'relative',
          color: 'var(--text-main)'
        }}
      >
        <button 
          onClick={onClose} 
          style={{ 
            position: 'absolute', 
            top: '15px', 
            right: '15px', 
            background: 'none', 
            border: 'none', 
            fontSize: '1.5rem', 
            cursor: 'pointer', 
            color: 'var(--text-muted)', 
            fontFamily: 'inherit' 
          }}
        >
          &times;
        </button>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--text-main)', marginBottom: '5px' }}>
          Suivi de Dossier Douanier
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--primary)', fontWeight: 'bold', marginBottom: '20px' }}>
          N° Dossier : {dossier.NUMERODOSSIERTPS}
        </p>
        
        {/* Timeline elements */}
        <div 
          style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '20px', 
            marginBottom: '25px', 
            paddingLeft: '10px', 
            borderLeft: '3px solid var(--border)', 
            position: 'relative' 
          }}
        >
          {steps.map((step, idx) => {
            let stepClass = 'timeline-step';
            if (idx < activeIndex) {
              stepClass += ' completed';
            } else if (idx === activeIndex) {
              stepClass += ' active';
            }
            return (
              <div key={step.id} className={stepClass}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                   {step.label}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '5px' }}>
                   {step.desc}
                </div>
              </div>
            );
          })}
        </div>
        
        <div style={{ background: 'var(--bg-app)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 'bold', color: 'var(--text-main)', marginBottom: '5px' }}>
            Délais prévisionnels historiques
          </h4>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <span>Validation Banque : 2,1 jours</span>
            <span>BAE Douane : 1,4 jour</span>
          </div>
        </div>
      </div>
    </div>
  );
}
