import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { formatCFA, fetchWithAuth } from '../utils/api';

export default function LogisticsTab({ data, role, theme }) {
  const [sankeyMode, setSankeyMode] = useState('imports');
  const [ninea, setNinea] = useState('');
  const [solvencyResult, setSolvencyResult] = useState(null);
  const [solvencyLoading, setSolvencyLoading] = useState(false);
  const [crisisScenario, setCrisisScenario] = useState('none');

  // Table 1 (Segmentation) states
  const [searchTermSeg, setSearchTermSeg] = useState('');
  const [currentPageSeg, setCurrentPageSeg] = useState(1);

  // Table 2 (Doc Delays) states
  const [docDelays] = useState([
    { docType: "Déclaration Préalable d'Importation (DPI)", delay: '1,1 jour', volume: '280 450 dossiers', performance: "Très Rapide", badgeClass: 'badge-success' },
    { docType: "Bon à Enlever (BAE Douane)", delay: '1,4 jour', volume: '350 791 dossiers', performance: "Optimal", badgeClass: 'badge-success' },
    { docType: "Engagement Financier (Banques)", delay: '2,1 jours', volume: '301 230 dossiers', performance: "Moyen", badgeClass: 'badge-warning' },
    { docType: "Certificat d'Assurance (Fret)", delay: '1,2 jour', volume: '120 195 dossiers', performance: "Très Rapide", badgeClass: 'badge-success' },
    { docType: "Autorisations Techniques (Ministères)", delay: '3,5 jours', volume: '45 812 dossiers', performance: "À Améliorer", badgeClass: 'badge-danger' },
    { docType: "Déclaration en Détail (Transitaires)", delay: '1,8 jour', volume: '350 791 dossiers', performance: "Fluide", badgeClass: 'badge-success' }
  ]);
  const [searchTermDocs, setSearchTermDocs] = useState('');
  const [currentPageDocs, setCurrentPageDocs] = useState(1);

  // Reset pages on search term change
  useEffect(() => {
    setCurrentPageSeg(1);
  }, [searchTermSeg]);

  useEffect(() => {
    setCurrentPageDocs(1);
  }, [searchTermDocs]);

  const filteredSeg = (data?.segmentation || []).filter(row => {
    const term = searchTermSeg.toLowerCase().trim();
    if (!term) return true;
    return String(row.segment || '').toLowerCase().includes(term);
  });

  const ITEMS_PER_PAGE = 5;
  const totalPagesSeg = Math.ceil(filteredSeg.length / ITEMS_PER_PAGE) || 1;
  const paginatedSeg = filteredSeg.slice(
    (currentPageSeg - 1) * ITEMS_PER_PAGE,
    currentPageSeg * ITEMS_PER_PAGE
  );

  const filteredDocs = docDelays.filter(item => {
    const term = searchTermDocs.toLowerCase().trim();
    if (!term) return true;
    return (
      item.docType.toLowerCase().includes(term) ||
      item.delay.toLowerCase().includes(term) ||
      item.volume.toLowerCase().includes(term) ||
      item.performance.toLowerCase().includes(term)
    );
  });

  const totalPagesDocs = Math.ceil(filteredDocs.length / ITEMS_PER_PAGE) || 1;
  const paginatedDocs = filteredDocs.slice(
    (currentPageDocs - 1) * ITEMS_PER_PAGE,
    currentPageDocs * ITEMS_PER_PAGE
  );

  const kmeansRef = useRef(null);
  const transportRef = useRef(null);
  const sankeyRef = useRef(null);
  const crisisChartRef = useRef(null);

  const chartInstances = useRef({});

  const isDark = theme !== 'light';
  const axisOptions = {
    axisLabel: { color: isDark ? '#94a3b8' : '#475569', fontFamily: 'Outfit', fontSize: 11 },
    axisLine: { lineStyle: { color: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)' } },
    splitLine: { lineStyle: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.05)' } },
    nameTextStyle: { color: isDark ? '#94a3b8' : '#475569', fontFamily: 'Outfit' }
  };

  useEffect(() => {
    return () => {
      Object.values(chartInstances.current).forEach(chart => {
        if (chart) chart.dispose();
      });
      chartInstances.current = {};
    };
  }, []);

  // 1. K-Means Cluster Size bar chart
  useEffect(() => {
    if (!kmeansRef.current || !data?.segmentation) return;

    let chart = chartInstances.current.kmeans;
    if (!chart) {
      chart = echarts.init(kmeansRef.current);
      chartInstances.current.kmeans = chart;
    }

    chart.setOption({
      tooltip: { 
        trigger: 'axis',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      xAxis: { type: 'category', data: data.segmentation.map(d => d.segment), ...axisOptions },
      yAxis: { type: 'value', name: "Importers", ...axisOptions },
      series: [{
        data: data.segmentation.map(d => d.count),
        type: 'bar',
        itemStyle: { color: '#2075db' }
      }]
    });
  }, [data, theme]);

  // 2. Mode of Transport Pie Chart
  useEffect(() => {
    if (!transportRef.current || !data?.logistics?.mode_split) return;

    let chart = chartInstances.current.transport;
    if (!chart) {
      chart = echarts.init(transportRef.current);
      chartInstances.current.transport = chart;
    }

    const transData = Object.entries(data.logistics.mode_split).map(([k, v]) => ({ name: k, value: v }));
    chart.setOption({
      tooltip: { 
        trigger: 'item',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
      color: ['#3b82f6', '#10b981', '#f59e0b'],
      series: [{
        name: "Transport",
        type: 'pie',
        radius: ['30%', '60%'],
        itemStyle: { borderRadius: 0, borderWidth: 0 },
        data: transData
      }]
    });
  }, [data, theme]);

  // 3. Sankey Diagram
  useEffect(() => {
    if (!sankeyRef.current) return;

    let chart = chartInstances.current.sankey;
    if (!chart) {
      chart = echarts.init(sankeyRef.current);
      chartInstances.current.sankey = chart;
    }

    let nodes = [];
    let links = [];

    if (sankeyMode === 'imports') {
      nodes = [
        { name: 'Chine', itemStyle: { color: '#f87171' } },
        { name: 'Inde', itemStyle: { color: '#fb923c' } },
        { name: 'France', itemStyle: { color: '#60a5fa' } },
        { name: 'Other countries', itemStyle: { color: '#94a3b8' } },
        { name: 'Maritime (Port)', itemStyle: { color: '#2563eb' } },
        { name: 'Air (AIBD)', itemStyle: { color: '#34d399' } },
        { name: 'Road (Borders)', itemStyle: { color: '#fbbf24' } },
        { name: 'Senegal (Cons. Entry)', itemStyle: { color: '#64748b' } },
        { name: 'Senegal (Transit)', itemStyle: { color: '#475569' } }
      ];

      links = [
        { source: 'Chine', target: 'Maritime (Port)', value: 65000 },
        { source: 'Inde', target: 'Maritime (Port)', value: 30000 },
        { source: 'France', target: 'Maritime (Port)', value: 30000 },
        { source: 'France', target: 'Air (AIBD)', value: 15000 },
        { source: 'Other countries', target: 'Road (Borders)', value: 20000 },
        { source: 'Maritime (Port)', target: 'Senegal (Cons. Entry)', value: 125000 },
        { source: 'Air (AIBD)', target: 'Senegal (Cons. Entry)', value: 15000 },
        { source: 'Road (Borders)', target: 'Senegal (Transit)', value: 20000 }
      ];
    } else {
      nodes = [
        { name: 'Senegal (Source)', itemStyle: { color: '#4ade80' } },
        { name: 'Maritime (Port)', itemStyle: { color: '#2563eb' } },
        { name: 'Air (AIBD)', itemStyle: { color: '#34d399' } },
        { name: 'Road (Borders)', itemStyle: { color: '#fbbf24' } },
        { name: 'France (Dest)', itemStyle: { color: '#60a5fa' } },
        { name: 'Chine (Dest)', itemStyle: { color: '#f87171' } },
        { name: 'Afrique de l\'Est (Dest)', itemStyle: { color: '#fb923c' } }
      ];

      links = [
        { source: 'Senegal (Source)', target: 'Maritime (Port)', value: 40000 },
        { source: 'Senegal (Source)', target: 'Air (AIBD)', value: 20000 },
        { source: 'Senegal (Source)', target: 'Road (Borders)', value: 10000 },
        { source: 'Maritime (Port)', target: 'France (Dest)', value: 15000 },
        { source: 'Maritime (Port)', target: 'Chine (Dest)', value: 25000 },
        { source: 'Air (AIBD)', target: 'France (Dest)', value: 10000 },
        { source: 'Air (AIBD)', target: 'Afrique de l\'Est (Dest)', value: 10000 },
        { source: 'Road (Borders)', target: 'Afrique de l\'Est (Dest)', value: 10000 }
      ];
    }

    chart.setOption({
      tooltip: { 
        trigger: 'item', 
        triggerOn: 'mousemove',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      series: [{
        type: 'sankey',
        data: nodes,
        links: links,
        emphasis: { focus: 'adjacency' },
        lineStyle: { color: 'gradient', curveness: 0.5 },
        label: {
          color: isDark ? '#f1f5f9' : '#0f172a',
          fontFamily: 'Outfit',
          fontSize: 11,
          fontWeight: '600'
        }
      }]
    }, true);

  }, [sankeyMode, theme]);

  // 4. Crisis Simulator Stress Test Chart
  useEffect(() => {
    if (!crisisChartRef.current) return;

    let chart = chartInstances.current.crisisChart;
    if (!chart) {
      chart = echarts.init(crisisChartRef.current);
      chartInstances.current.crisisChart = chart;
    }

    const standardShare = [63, 18, 19];
    let simulatedShare = [63, 18, 19];

    if (crisisScenario === 'port_blocked') {
      simulatedShare = [10, 45, 45];
    } else if (crisisScenario === 'fuel_crisis') {
      simulatedShare = [65, 25, 10];
    } else if (crisisScenario === 'air_closed') {
      simulatedShare = [78, 2, 20];
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      legend: {
        data: ["Volume de Référence (%)", "Volume Sous Crise (%)"],
        textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' },
        bottom: '0%'
      },
      grid: {
        top: '12%',
        bottom: '15%',
        left: '5%',
        right: '5%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: ["Fret Maritime (Mer)", "Fret Aérien (Air)", "Fret Terrestre (Route)"],
        ...axisOptions
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: '{value} %' },
        ...axisOptions
      },
      series: [
        {
          name: "Reference Volume (%)",
          type: 'bar',
          data: standardShare,
          itemStyle: { color: isDark ? '#1e40af' : '#3b82f6', borderRadius: [4, 4, 0, 0] },
          barWidth: '22%'
        },
        {
          name: "Volume Under Crisis (%)",
          type: 'bar',
          data: simulatedShare,
          itemStyle: { color: '#ef4444', borderRadius: [4, 4, 0, 0] },
          barWidth: '22%'
        }
      ]
    });
  }, [crisisScenario, theme]);

  // Resize Charts handler
  useEffect(() => {
    const handleResize = () => {
      Object.values(chartInstances.current).forEach(chart => {
        if (chart) chart.resize();
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Partner Solvency Checker
  const handleCheckSolvency = async (e) => {
    e.preventDefault();
    if (!ninea.trim()) {
      alert("Veuillez saisir un code PPM.");
      return;
    }

    setSolvencyLoading(true);
    setSolvencyResult(null);

    try {
      const response = await fetchWithAuth(`/api/partenaire/importer-reliability?ninea=${encodeURIComponent(ninea.trim())}`);
      if (!response.ok) throw new Error("Solvency check error");
      const res = await response.json();
      setSolvencyResult(res);
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la récupération des informations de solvabilité.");
    } finally {
      setSolvencyLoading(false);
    }
  };

  const isPartenaireOrAdmin = role === 'partenaire' || role === 'admin';

  // Crisis Simulation Impacts
  let delayImpactText = "0 jour";
  let volumeImpactText = "0%";
  let budgetImpactText = "0%";
  let contingencyText = "No logistics disruptions in progress. The national supply chain is operating normally.";
  let badgeSeverityClass = "badge-success";
  
  if (crisisScenario === 'port_blocked') {
    delayImpactText = "+ 4.2 jours";
    volumeImpactText = "- 35% de flux";
    budgetImpactText = "- 45% recettes";
    contingencyText = "Urgence Maritime : Redirection prioritaire du fret conteneurisé vers le Port de Kaolack et de Banjul. Activation des corridors de secours routiers terrestres.";
    badgeSeverityClass = "badge-danger";
  } else if (crisisScenario === 'fuel_crisis') {
    delayImpactText = "+ 5.8 jours";
    volumeImpactText = "- 15% de flux";
    budgetImpactText = "- 10% recettes";
    contingencyText = "Pénurie Carburant : Priorisation du carburant pour les transports de denrées alimentaires et médicales. Activation de la ligne de chemin de fer Dakar-Bamako.";
    badgeSeverityClass = "badge-danger";
  } else if (crisisScenario === 'air_closed') {
    delayImpactText = "+ 2.5 jours";
    volumeImpactText = "- 10% de flux";
    budgetImpactText = "- 12% recettes";
    contingencyText = "Fermeture Espace Aérien : Report du fret express aérien sur les porte-conteneurs rapides (Europe-Dakar). Dédouanement prioritaire (couloir vert) pour ces marchandises.";
    badgeSeverityClass = "badge-warning";
  }

  return (
    <>
      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Segmentation des Importers (K-Means)</div>
          <div ref={kmeansRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Distribution by Transport Mode</div>
          <div ref={transportRef} className="chart-container"></div>
        </div>
      </div>

      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <span>Flux Logistiques et Operationnels (Diagramme de Sankey)</span>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className={`btn ${sankeyMode === 'imports' ? 'active' : ''}`} 
                onClick={() => setSankeyMode('imports')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid var(--primary-light)',
                  backgroundColor: sankeyMode === 'imports' ? 'var(--primary)' : 'transparent',
                  color: sankeyMode === 'imports' ? 'white' : 'var(--text-main)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  transition: 'all 0.2s'
                }}
              >
                Imports (to Senegal)
              </button>
              <button 
                className={`btn ${sankeyMode === 'exports' ? 'active' : ''}`} 
                onClick={() => setSankeyMode('exports')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid var(--success)',
                  backgroundColor: sankeyMode === 'exports' ? 'var(--success)' : 'transparent',
                  color: sankeyMode === 'exports' ? 'white' : 'var(--text-main)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  transition: 'all 0.2s'
                }}
              >
                Exports (from Senegal)
              </button>
            </div>
          </div>
          <div ref={sankeyRef} className="chart-container" style={{ height: '380px' }}></div>
        </div>
      </div>

      {/* Crisis Stress Test Simulator Card */}
      <div className="dashboard-row">
        <div className="chart-card full-width-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="kpi-icon-wrapper warning" style={{ width: '32px', height: '32px', color: '#f59e0b' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>Simulateur de Crise & Stress-Test Logistique</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Simuler des incidents majeurs pour évaluer la résilience des flux douaniers nationaux</span>
              </div>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>Scénario d\'Incident :</label>
              <select 
                value={crisisScenario} 
                onChange={(e) => setCrisisScenario(e.target.value)}
                style={{ padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
              >
                <option value="none">Aucun incident (Normal)</option>
                <option value="port_blocked">Fermeture / Blocage du Port de Dakar</option>
                <option value="fuel_crisis">Pénurie de Carburant (Transit ralenti)</option>
                <option value="air_closed">Fermeture de l\'Espace Aérien Cargo</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
            {/* Left side: simulated stress metrics */}
            <div style={{ flex: 1, minWidth: '280px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '15px' }}>
                  Customs Disruption Indicators
                </h4>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: '8px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>Allongement des Délais :</span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 'bold', color: crisisScenario === 'none' ? '#10b981' : '#f59e0b' }}>
                      {delayImpactText}
                    </span>
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: '8px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>Impact sur le Volume :</span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 'bold', color: crisisScenario === 'none' ? '#10b981' : '#ef4444' }}>
                      {volumeImpactText}
                    </span>
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: '8px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>Pertes Recettes (Est.) :</span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 'bold', color: crisisScenario === 'none' ? '#10b981' : '#ef4444' }}>
                      {budgetImpactText}
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ 
                marginTop: '15px', 
                padding: '12px 15px', 
                borderRadius: '8px', 
                background: 'rgba(6, 182, 212, 0.04)', 
                border: '1px solid rgba(6, 182, 212, 0.25)' 
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <span className={`badge ${badgeSeverityClass}`} style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                    {crisisScenario === 'none' ? 'SITUATION NOMINALE' : 'PLAN D\'URGENCE ACTIVÉ'}
                  </span>
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', margin: 0, lineHeight: '1.4' }}>
                  {contingencyText}
                </p>
              </div>
            </div>

            {/* Right side: comparison ECharts chart */}
            <div style={{ flex: 1.5, minWidth: '320px' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '5px', textAlign: 'center' }}>
                Transport Volume Distribution (Before vs Crisis)
              </h4>
              <div ref={crisisChartRef} style={{ width: '100%', height: '240px' }}></div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Détail de la Segmentation Métier des Importateurs</div>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Rechercher un segment..."
              value={searchTermSeg}
              onChange={(e) => setSearchTermSeg(e.target.value)}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setCurrentPageSeg(prev => Math.max(prev - 1, 1))}
                disabled={currentPageSeg === 1}
              >
                Précédent
              </button>
              <span className="pagination-info">
                Page {currentPageSeg} / {totalPagesSeg}
              </span>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPageSeg(prev => Math.min(prev + 1, totalPagesSeg))}
                disabled={currentPageSeg === totalPagesSeg}
              >
                Suivant
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Segment Importer</th>
                  <th>Nombre de Comptes</th>
                  <th>Valeur Moyenne (CFA)</th>
                  <th>Dossiers Moyens</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSeg && paginatedSeg.length > 0 ? (
                  paginatedSeg.map(row => (
                    <tr key={row.segment}>
                      <td><strong>{row.segment}</strong></td>
                      <td>{row.count.toLocaleString('fr-FR')}</td>
                      <td>{formatCFA(row.avg_value)}</td>
                      <td>{(row.avg_dossiers !== undefined ? row.avg_dossiers : row.avg_files).toFixed(1)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No segment found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Délais Moyens de Délivrance des Documents</div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px' }}>
            Temps de traitement moyen pour la délivrance des documents de douane requis.
          </p>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Rechercher un document..."
              value={searchTermDocs}
              onChange={(e) => setSearchTermDocs(e.target.value)}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setCurrentPageDocs(prev => Math.max(prev - 1, 1))}
                disabled={currentPageDocs === 1}
              >
                Précédent
              </button>
              <span className="pagination-info">
                Page {currentPageDocs} / {totalPagesDocs}
              </span>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPageDocs(prev => Math.min(prev + 1, totalPagesDocs))}
                disabled={currentPageDocs === totalPagesDocs}
              >
                Suivant
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Type de Document</th>
                  <th>Délai Moyen</th>
                  <th>Volume Traité</th>
                  <th>Performance</th>
                </tr>
              </thead>
              <tbody>
                {paginatedDocs.length > 0 ? (
                  paginatedDocs.map((item, idx) => (
                    <tr key={idx}>
                      <td><strong>{item.docType}</strong></td>
                      <td>{item.delay}</td>
                      <td>{item.volume}</td>
                      <td><span className={`badge ${item.badgeClass}`}>{item.performance}</span></td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      Aucun document trouvé.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Partenaire Solvency Card */}
      {isPartenaireOrAdmin && (
        <div className="dashboard-row" style={{ marginTop: '30px' }}>
          <div className="chart-card full-width-card">
            <div className="chart-card-title">Indice de Solvabilité & Analyse Financière Client</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px', marginTop: '-10px' }}>
              Recherchez le profil d'un importateur par son code PPM pour obtenir son score de solvabilité et son taux de conformité.
            </p>
            <form onSubmit={handleCheckSolvency} style={{ display: 'flex', gap: '15px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '20px' }}>
              <div className="login-input-group" style={{ flex: 1, minWidth: '250px' }}>
                <label>Code PPM de l'importateur</label>
                <input 
                  type="text" 
                  placeholder="ex: 0013920" 
                  value={ninea}
                  onChange={(e) => setNinea(e.target.value)}
                  style={{ background: 'var(--bg-app)', color: 'var(--text-main)', border: '1px solid var(--border)' }}
                  required
                />
              </div>
              <button type="submit" className="login-btn" style={{ marginTop: '22px' }} disabled={solvencyLoading}>
                {solvencyLoading ? 'Analyse...' : 'Analyser la Solvabilité'}
              </button>
            </form>

            {solvencyResult && (
              <div style={{ padding: '20px', borderRadius: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '20px' }}>
                  <div style={{ textAlign: 'center', borderRight: '1px solid var(--border)', paddingRight: '10px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Score de Fiabilité</span>
                    <span style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--primary-light)' }}>{solvencyResult.score} / 100</span>
                  </div>
                  <div style={{ textAlign: 'center', borderRight: '1px solid var(--border)', paddingRight: '10px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Classe de Crédit</span>
                    <span 
                      style={{ 
                        fontSize: '1.3rem', 
                        fontWeight: 'bold', 
                        color: solvencyResult.score >= 90 ? 'var(--success)' : solvencyResult.score >= 80 ? 'var(--primary-light)' : solvencyResult.score >= 70 ? 'var(--warning)' : 'var(--danger)', 
                        display: 'block', 
                        marginTop: '10px' 
                      }}
                    >
                      {solvencyResult.class}
                    </span>
                  </div>
                  <div style={{ textAlign: 'center', borderRight: '1px solid var(--border)', paddingRight: '10px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Total Dossiers Financés</span>
                    <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-main)', display: 'block', marginTop: '8px' }}>{solvencyResult.total_dossiers} dossiers</span>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Dossiers En Cours / Initialisés</span>
                    <span style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginTop: '10px' }}>{solvencyResult.active_dossiers} / {solvencyResult.pending_dossiers}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
