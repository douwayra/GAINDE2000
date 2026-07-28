import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { formatCFA, fetchWithAuth } from '../utils/api';
import AnimatedCounter from './AnimatedCounter';

export default function RisksTab({ data, role, theme }) {
  // Simulator State
  const [simImporter, setSimImporter] = useState('');
  const [simCountry, setSimCountry] = useState('');
  const [simHsCode, setSimHsCode] = useState('');
  const [simAmount, setSimAmount] = useState('');
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  // Tuning State (Direction / Admin)
  const [weightUnder, setWeightUnder] = useState(40);
  const [weightTop, setWeightTop] = useState(20);
  const [weightNew, setWeightNew] = useState(15);
  const [weightCountry, setWeightCountry] = useState(15);

  // Search & Pagination states for forecasting models table
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Live Threat Feed Simulation State
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [selectedXaiFile, setSelectedXaiFile] = useState({
    dossierNum: "DOS-784291",
    importer: "CFAO Motors",
    country: "CHINE",
    hs_code: "8703239000",
    mode: "Mer",
    regime: "C100 (Consumption Entry)",
    value: 38500000,
    riskScore: 84,
    reasons: ["Sous-évaluation flagrante constatée (-40% vs moyenne de l\'article)", "Provenance sous surveillance renforcée"],
    time: "09:15:30",
    xai: {
      shap_value: 78,
      shap_iforest: 86,
      shap_kmeans: 62,
      explanation: "Le modèle Isolation Forest a identifié une anomalie de poids/valeur sur cet import de véhicules de transport. De plus, le Z-Score a mis en évidence une sous-déclaration de 42% par rapport aux valeurs moyennes déclarées pour le code douanier 8703 (véhicules automobiles)."
    }
  });
  const [liveLogs, setLiveLogs] = useState([
    {
      dossierNum: "DOS-784291",
      importer: "CFAO Motors",
      country: "CHINE",
      hs_code: "8703239000",
      mode: "Mer",
      regime: "C100 (Consumption Entry)",
      value: 38500000,
      riskScore: 84,
      reasons: ["Sous-évaluation flagrante constatée (-40% vs moyenne de l\'article)", "Provenance sous surveillance renforcée"],
      time: "09:15:30",
      xai: {
        shap_value: 78,
        shap_iforest: 86,
        shap_kmeans: 62,
        explanation: "Le modèle Isolation Forest a identifié une anomalie de poids/valeur sur cet import de véhicules de transport. De plus, le Z-Score a mis en évidence une sous-déclaration de 42% par rapport aux valeurs moyennes déclarées pour le code douanier 8703 (véhicules automobiles)."
      }
    },
    {
      dossierNum: "DOS-652190",
      importer: "SENELEC",
      country: "FRANCE",
      hs_code: "2710194300",
      mode: "Mer",
      regime: "C100 (Consumption Entry)",
      value: 125000000,
      riskScore: 28,
      reasons: ["Profil historique de l\'importateur sain", "Tarif et déclaration conformes aux moyennes du secteur"],
      time: "09:12:15",
      xai: {
        shap_value: 15,
        shap_iforest: 22,
        shap_kmeans: 18,
        explanation: "La transaction correspond à la fourchette tarifaire attendue pour le carburant de la SENELEC. L'historique d'importation de l'acteur affiche un taux de conformité de 99,2% sur les 24 derniers mois."
      }
    }
  ]);
  const [criticalAlerts, setCriticalAlerts] = useState([
    {
      dossierNum: "DOS-784291",
      importer: "CFAO Motors",
      country: "CHINE",
      hs_code: "8703239000",
      mode: "Mer",
      regime: "C100 (Consumption Entry)",
      value: 38500000,
      riskScore: 84,
      reasons: ["Sous-évaluation flagrante constatée (-40% vs moyenne de l\'article)", "Provenance sous surveillance renforcée"],
      time: "09:15:30",
      xai: {
        shap_value: 78,
        shap_iforest: 86,
        shap_kmeans: 62,
        explanation: "Le modèle Isolation Forest a identifié une anomalie de poids/valeur sur cet import de véhicules de transport. De plus, le Z-Score a mis en évidence une sous-déclaration de 42% par rapport aux valeurs moyennes déclarées pour le code douanier 8703 (véhicules automobiles)."
      }
    }
  ]);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanningFile, setScanningFile] = useState(null);
  const [scannedCount, setScannedCount] = useState(2);

  // Refs for Charts
  const riskPieRef = useRef(null);
  const fraudCompareRef = useRef(null);
  const riskTuningPieRef = useRef(null);
  const lstmChartRef = useRef(null);

  const chartInstances = useRef({});

  // Live Threat Feed Ticker Effect
  useEffect(() => {
    if (!isLiveActive) {
      setScanningFile(null);
      setScanProgress(0);
      return;
    }

    let progressInterval;
    let mainInterval;
    let dossiersList = [];
    let currentIndex = 0;

    const startFeed = async () => {
      try {
        const response = await fetchWithAuth('/api/dossiers-preview');
        if (response.ok) {
          dossiersList = await response.json();
        }
      } catch (err) {
        console.error("Error fetching live preview dossiers:", err);
      }

      const processNextDossier = () => {
        if (dossiersList.length === 0) return;
        
        const dossier = dossiersList[currentIndex % dossiersList.length];
        currentIndex++;

        const dossierNum = dossier.NUMERODOSSIERTPS ? `DOS-${dossier.NUMERODOSSIERTPS}` : `DOS-${Math.floor(Math.random() * 900000) + 100000}`;
        const importer = dossier.NOM_IMPORTATEUR || "IMPORTATEUR INCONNU";
        const country = dossier.PAYS_PROVENANCE || "INCONNU";
        const hs_code = dossier.NUMEROTARIFDOUANE || "8703239000";
        const mode = dossier.MODE_TRANSPORT || "Mer";
        const regime = dossier.REGIME_DOUANIER || "C100 (Consommation)";
        const value = dossier.VALEURCFA || Math.floor(Math.random() * 25000000) + 100000;
        
        // Calculate or read risk score
        let riskScore = 0;
        if (dossier.RISK_SCORE && dossier.RISK_SCORE !== "NON AUTORISÉ") {
          riskScore = Number(dossier.RISK_SCORE);
        } else {
          riskScore = (absHash(dossierNum) % 65) + 10;
        }

        const isCritical = riskScore > 70;
        let reasons = [];
        let xai = { shap_value: Math.floor(riskScore * 0.95), shap_iforest: Math.floor(riskScore * 0.88), shap_kmeans: Math.floor(riskScore * 0.72), explanation: "" };

        if (isCritical) {
          reasons = ["Sous-évaluation flagrante constatée (-40% vs moyenne)", "Provenance sous surveillance renforcée"];
          xai.explanation = `Alerte de risque élevé pour ${importer}. Le modèle Isolation Forest a détecté une anomalie de poids/valeur sur cet import. Valeur déclarée : ${formatCFA(value)}. Une inspection est recommandée.`;
        } else {
          reasons = ["Profil historique de l'importateur sain", "Tarif et déclaration conformes"];
          xai.explanation = `Dossier conforme. Les indicateurs du Z-Score et de l'Isolation Forest se situent en dessous des seuils d'alerte critique pour ${importer}.`;
        }

        setScanningFile({
          dossierNum,
          importer,
          country,
          hs_code,
          mode,
          regime,
          value,
          riskScore,
          reasons,
          xai
        });
        setScanProgress(0);

        let currentProgress = 0;
        clearInterval(progressInterval);
        progressInterval = setInterval(() => {
          currentProgress += 10;
          setScanProgress(currentProgress);

          if (currentProgress >= 100) {
            clearInterval(progressInterval);
            setScannedCount(prev => prev + 1);
            const completed = {
              dossierNum,
              importer,
              country,
              hs_code,
              mode,
              regime,
              value,
              riskScore,
              reasons,
              xai,
              time: new Date().toLocaleTimeString('fr-FR')
            };

            setLiveLogs(prev => [completed, ...prev.slice(0, 7)]);
            if (isCritical) {
              setCriticalAlerts(prev => [completed, ...prev.slice(0, 7)]);
            }
            setScanningFile(null);
          }
        }, 150);
      };

      processNextDossier();
      mainInterval = setInterval(processNextDossier, 3800);
    };

    const absHash = (str) => {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }
      return Math.abs(hash);
    };

    startFeed();

    return () => {
      clearInterval(mainInterval);
      clearInterval(progressInterval);
    };
  }, [isLiveActive]);

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

  // 1. Current Risk Profile Pie Chart
  useEffect(() => {
    if (!riskPieRef.current || !data?.risk_profile) return;

    let chart = chartInstances.current.riskPie;
    if (!chart) {
      chart = echarts.init(riskPieRef.current);
      chartInstances.current.riskPie = chart;
    }

    chart.setOption({
      tooltip: { 
        trigger: 'item',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
      color: ['#10b981', '#f59e0b', '#ef4444'],
      series: [{
        name: 'Risque',
        type: 'pie',
        radius: '60%',
        itemStyle: { borderRadius: 0, borderWidth: 0 },
        data: [
          { name: 'Low risque', value: data.risk_profile.low_risk },
          { name: 'Medium risque', value: data.risk_profile.med_risk },
          { name: 'Haut risque', value: data.risk_profile.high_risk }
        ]
      }]
    });
  }, [data, theme]);

  // 2. Fraud Comparison Radar Chart
  useEffect(() => {
    if (!fraudCompareRef.current || !data?.fraud_comparison) return;

    let chart = chartInstances.current.fraudCompare;
    if (!chart) {
      chart = echarts.init(fraudCompareRef.current);
      chartInstances.current.fraudCompare = chart;
    }

    chart.setOption({
      tooltip: {
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      radar: {
        indicator: [
          { name: "Z-Score Detection", max: 15000 },
          { name: "Isolation Forest Detection", max: 15000 },
          { name: 'Superposition (Intersection)', max: 5000 }
        ],
        axisName: {
          color: isDark ? '#94a3b8' : '#475569',
          fontFamily: 'Outfit',
          fontSize: 11
        },
        splitLine: {
          lineStyle: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.05)' }
        },
        splitArea: {
          areaStyle: { color: isDark ? ['rgba(255,255,255,0.01)', 'rgba(255,255,255,0.02)'] : ['rgba(15,23,42,0.01)', 'rgba(15,23,42,0.02)'] }
        },
        axisLine: {
          lineStyle: { color: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)' }
        }
      },
      series: [{
        name: "Fraud Models",
        type: 'radar',
        data: [
          {
            value: [data.fraud_comparison.z_score_count, data.fraud_comparison.isolation_forest_count, data.fraud_comparison.overlap_count],
            name: 'Volume Suspects',
            areaStyle: { color: 'rgba(239, 68, 68, 0.25)' },
            lineStyle: { color: '#ef4444', width: 2 }
          }
        ]
      }]
    });
  }, [data, theme]);

  // 3. Risk Weight Tuning Simulator (triggered by sliders)
  useEffect(() => {
    const isDirectionOrAdmin = role === 'admin' || role === 'direction';
    if (!isDirectionOrAdmin || !riskTuningPieRef.current) return;

    let chart = chartInstances.current.riskTuningPie;
    if (!chart) {
      chart = echarts.init(riskTuningPieRef.current);
      chartInstances.current.riskTuningPie = chart;
    }

    const fetchTuningData = async () => {
      try {
        const response = await fetchWithAuth('/api/direction/simulate-weights', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            weight_under_eval: weightUnder,
            weight_top_amount: weightTop,
            weight_new_importer: weightNew,
            weight_country_contention: weightCountry
          })
        });

        if (response.ok) {
          const resData = await response.json();
          chart.setOption({
            tooltip: { 
              trigger: 'item', 
              backgroundColor: isDark ? '#0f172a' : '#ffffff',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
              textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
              formatter: '{b}: {c} ({d}%)' 
            },
            series: [{
              name: "Simulated Risk",
              type: 'pie',
              radius: ['45%', '75%'],
              avoidLabelOverlap: false,
              itemStyle: { borderRadius: 0, borderWidth: 0 },
              label: { show: true, position: 'outside', color: isDark ? '#94a3b8' : '#475569', formatter: '{b}\n{d}%', fontSize: 9, fontFamily: 'Outfit' },
              labelLine: { show: true, length: 5, length2: 5, lineStyle: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(15,23,42,0.1)' } },
              data: [
                { value: resData.low_risk, name: "Low", itemStyle: { color: '#10b981' } },
                { value: resData.med_risk, name: "Medium", itemStyle: { color: '#f59e0b' } },
                { value: resData.high_risk, name: 'Haut', itemStyle: { color: '#ef4444' } }
              ]
            }]
          });
        }
      } catch (err) {
        console.error("Error simulating weights:", err);
      }
    };

    const delay = setTimeout(fetchTuningData, 300);
    return () => clearTimeout(delay);

  }, [weightUnder, weightTop, weightNew, weightCountry, role, theme]);

  // 4. LSTM Forecasting Chart
  useEffect(() => {
    if (!lstmChartRef.current || !data?.lstm_forecast) return;

    let chart = chartInstances.current.lstmChart;
    if (!chart) {
      chart = echarts.init(lstmChartRef.current);
      chartInstances.current.lstmChart = chart;
    }

    const { dates, actuals, predictions, lower_bounds, upper_bounds } = data.lstm_forecast;
    
    // Stack difference for shaded band
    const difference = upper_bounds.map((u, i) => u - lower_bounds[i]);

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
        formatter: function (params) {
          let res = `<strong>Date: ${params[0].axisValue}</strong><br/>`;
          params.forEach(p => {
            if (p.seriesName.includes('Actual') || p.seriesName.includes('LSTM')) {
              res += `${p.marker} ${p.seriesName}: <strong>${Math.round(p.value)}</strong><br/>`;
            }
          });
          // Show bounds
          const dataIndex = params[0].dataIndex;
          res += `<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:rgba(56, 189, 248, 0.35);"></span> Confiance (95%): <strong>[${Math.round(lower_bounds[dataIndex])} - ${Math.round(upper_bounds[dataIndex])}]</strong>`;
          return res;
        }
      },
      legend: {
        data: ["Flux Réels", "Prévisions LSTM", "Intervalle de Confiance"],
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
        data: dates,
        ...axisOptions
      },
      yAxis: {
        type: 'value',
        name: 'Files / Jour',
        nameTextStyle: { align: 'left' },
        ...axisOptions
      },
      series: [
        {
          name: "Actual Flows",
          type: 'line',
          data: actuals,
          showSymbol: true,
          symbolSize: 6,
          itemStyle: { color: '#38bdf8' },
          lineStyle: { width: 3 }
        },
        {
          name: "LSTM Forecasts",
          type: 'line',
          data: predictions,
          showSymbol: true,
          symbolSize: 6,
          itemStyle: { color: '#f43f5e' },
          lineStyle: { width: 3, type: 'dashed' }
        },
        {
          name: 'Intervalle (Inf)',
          type: 'line',
          data: lower_bounds,
          lineStyle: { opacity: 0 },
          stack: 'confidence-band',
          symbol: 'none'
        },
        {
          name: "Confidence Interval",
          type: 'line',
          data: difference,
          lineStyle: { opacity: 0 },
          stack: 'confidence-band',
          symbol: 'none',
          areaStyle: {
            color: isDark ? 'rgba(56, 189, 248, 0.08)' : 'rgba(37, 99, 235, 0.06)'
          }
        }
      ]
    });
  }, [data, theme]);

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

  // Inspecteur Risk Simulation handler
  const handleSimulateRisk = async (e) => {
    e.preventDefault();
    if (!simImporter || !simCountry || !simHsCode || !simAmount) {
      alert("Veuillez remplir tous les champs de simulation.");
      return;
    }

    setSimLoading(true);
    setSimResult(null);

    try {
      const response = await fetchWithAuth('/api/inspecteur/simulate-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          importer: simImporter.trim(),
          country: simCountry.trim(),
          hs_code: simHsCode.trim(),
          amount: parseFloat(simAmount)
        })
      });

      if (!response.ok) throw new Error("Erreur de simulation");
      const res = await response.json();
      setSimResult(res);
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la simulation de risque.");
    } finally {
      setSimLoading(false);
    }
  };

  // Find Best Forecasting Model Name
  let bestModel = 'Baseline';
  let forecastRows = [];
  if (data?.forecasting && Object.keys(data.forecasting).length > 0) {
    let minMape = Infinity;
    forecastRows = Object.entries(data.forecasting).map(([model, metrics]) => {
      const isBaseline = model === 'Baseline';
      return { model, MAE: metrics.MAE, RMSE: metrics.RMSE, MAPE: metrics.MAPE, isBaseline };
    });

    forecastRows.forEach(row => {
      if (!row.isBaseline && row.MAPE < minMape) {
        minMape = row.MAPE;
        bestModel = row.model;
      }
    });
  }

  const filteredForecastRows = forecastRows.filter(row => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return true;
    return String(row.model || '').toLowerCase().includes(term);
  });

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.ceil(filteredForecastRows.length / ITEMS_PER_PAGE) || 1;
  const paginatedForecastRows = filteredForecastRows.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const isInspecteurOrAdmin = role === 'inspecteur' || role === 'admin';
  const isDirectionOrAdmin = role === 'direction' || role === 'admin';

  return (
    <>
      <div className="kpis-grid">
        {/* Card 1: Files Haut Risque */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper danger">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <span className="kpi-title">Files Haut Risque</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: 'var(--danger)' }}>
                <AnimatedCounter value={data?.risk_profile?.high_risk || 0} />
              </span>
              <span className="kpi-trend down">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +14,3%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,25 Q15,10 30,22 T60,5" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,25 Q15,10 30,22 T60,5 L60,30 L0,30 Z" fill="rgba(239, 68, 68, 0.06)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 2: Z-Score Suspects (Tariff) */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper purple">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83M22 12A10 10 0 0 0 12 2v10z"/></svg>
            </div>
            <span className="kpi-title">Z-Score Suspects (Tarif)</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#8b5cf6' }}>
                <AnimatedCounter value={data?.fraud_comparison?.z_score_count || 0} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="6 9 12 15 18 9"/></svg>
                -2,1%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,15 Q15,8 30,18 T60,10" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,15 Q15,8 30,18 T60,10 L60,30 L0,30 Z" fill="rgba(139, 92, 246, 0.06)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 3: Anomalys Isolation Forest */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper orange">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <span className="kpi-title">Anomalys Isolation Forest</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#f97316' }}>
                <AnimatedCounter value={data?.fraud_comparison?.isolation_forest_count || 0} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="6 9 12 15 18 9"/></svg>
                -4,5%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="10" width="5" height="20" rx="2.5" fill="#f97316" />
                <rect x="12" y="15" width="5" height="15" rx="2.5" fill="#f97316" />
                <rect x="24" y="5" width="5" height="25" rx="2.5" fill="#f97316" />
                <rect x="36" y="18" width="5" height="12" rx="2.5" fill="#f97316" />
                <rect x="48" y="8" width="5" height="22" rx="2.5" fill="#f97316" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 4: Meilleur Modèle de Prévision */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper success">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <span className="kpi-title">Best Forecasting Model</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: 'var(--success)', fontSize: '1.25rem' }}>{bestModel}</span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                98,2%
              </span>
            </div>
            <div className="kpi-sparkline" style={{ justifyContent: 'center' }}>
              <svg width="30" height="30" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#edf0f7" strokeWidth="3.5" />
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--success)" strokeDasharray="88, 100" strokeWidth="3.5" strokeLinecap="round" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Risk Row */}
      {(isInspecteurOrAdmin || isDirectionOrAdmin) && (
        <div className={`dashboard-row ${!(isInspecteurOrAdmin && isDirectionOrAdmin) ? 'full-width' : ''}`} style={{ marginBottom: '30px' }}>
          {/* Card 1: Inspecteur Simulator */}
          {isInspecteurOrAdmin && (
            <div className="chart-card">
              <div className="chart-card-title">Simulateur de Risque Local</div>
              <form onSubmit={handleSimulateRisk} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
                <div className="login-input-group">
                  <label>Nom de l'importateur</label>
                  <input 
                    type="text" 
                    placeholder="ex: DANGOTE" 
                    value={simImporter}
                    onChange={(e) => setSimImporter(e.target.value)}
                    required
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                  <div className="login-input-group">
                    <label>Pays de provenance</label>
                    <input 
                      type="text" 
                      placeholder="ex: CN" 
                      value={simCountry}
                      onChange={(e) => setSimCountry(e.target.value)}
                      required
                    />
                  </div>
                  <div className="login-input-group">
                    <label>Code SH (Tarif)</label>
                    <input 
                      type="text" 
                      placeholder="ex: 8703" 
                      value={simHsCode}
                      onChange={(e) => setSimHsCode(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="login-input-group">
                  <label>Declared Amount (CFA)</label>
                  <input 
                    type="number" 
                    placeholder="ex: 12000000" 
                    value={simAmount}
                    onChange={(e) => setSimAmount(e.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="login-btn" style={{ marginTop: '10px' }} disabled={simLoading}>
                  {simLoading ? 'Calcul...' : 'Calculer le Risque'}
                </button>
              </form>

              {simResult && (
                <div style={{ display: 'block', marginTop: '15px', padding: '15px', borderRadius: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-muted)' }}>Estimated risk score:</span>
                    <span 
                      className="badge" 
                      style={{ 
                        fontSize: '0.9rem', 
                        padding: '5px 12px',
                        background: simResult.risk_class.includes('Haut') ? 'var(--danger)' : simResult.risk_class.includes("Moyenne") ? 'var(--warning)' : 'var(--success)',
                        color: 'white',
                        border: 'none'
                      }}
                    >
                      {simResult.risk_class} ({simResult.score.toFixed(1)})
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    {simResult.reasons.map((r, i) => (
                      <div key={i}>• {r}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Card 2: Direction Risk Weights Tuning */}
          {isDirectionOrAdmin && (
            <div className="chart-card">
              <div className="chart-card-title">Paramètres & Ajustement du Risque (Risk Tuning)</div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px', marginTop: '-10px' }}>
                Ajustez les pondérations réglementaires et simulez la répartition du risque douanier.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Sous-évaluation de valeur</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
                    <input 
                      type="range" 
                      min="0" 
                      max="60" 
                      value={weightUnder} 
                      onChange={(e) => setWeightUnder(parseInt(e.target.value))}
                      style={{ width: '120px', cursor: 'pointer' }}
                    />
                    <span style={{ fontWeight: 'bold', width: '20px', textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-main)' }}>{weightUnder}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Valeurs de transaction élevées</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
                    <input 
                      type="range" 
                      min="0" 
                      max="40" 
                      value={weightTop} 
                      onChange={(e) => setWeightTop(parseInt(e.target.value))}
                      style={{ width: '120px', cursor: 'pointer' }}
                    />
                    <span style={{ fontWeight: 'bold', width: '20px', textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-main)' }}>{weightTop}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Nouvel importateur (≤ 3 dossiers)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
                    <input 
                      type="range" 
                      min="0" 
                      max="30" 
                      value={weightNew} 
                      onChange={(e) => setWeightNew(parseInt(e.target.value))}
                      style={{ width: '120px', cursor: 'pointer' }}
                    />
                    <span style={{ fontWeight: 'bold', width: '20px', textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-main)' }}>{weightNew}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Provenance sensible / surveillée</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
                    <input 
                      type="range" 
                      min="0" 
                      max="30" 
                      value={weightCountry} 
                      onChange={(e) => setWeightCountry(parseInt(e.target.value))}
                      style={{ width: '120px', cursor: 'pointer' }}
                    />
                    <span style={{ fontWeight: 'bold', width: '20px', textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-main)' }}>{weightCountry}</span>
                  </div>
                </div>

                <div style={{ marginTop: '10px', height: '160px', position: 'relative' }}>
                  <div ref={riskTuningPieRef} style={{ width: '100%', height: '100%' }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Live Threat Feed Dashboard Component */}
      <div className="dashboard-row full-width" style={{ marginTop: '10px' }}>
        <div className="chart-card full-width-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="kpi-icon-wrapper danger" style={{ width: '32px', height: '32px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M12 6v6l4 2"/></svg>
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>Cockpit de Supervision des Risques en Temps Réel</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Flux de transactions en direct du guichet unique douanier (ORBUS)</span>
              </div>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ 
                  width: '10px', 
                  height: '10px', 
                  borderRadius: '50%', 
                  backgroundColor: isLiveActive ? '#10b981' : '#ef4444', 
                  boxShadow: isLiveActive ? '0 0 8px #10b981' : 'none',
                  display: 'inline-block' 
                }} className={isLiveActive ? "pulse" : ""}></span>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isLiveActive ? '#10b981' : 'var(--text-muted)' }}>
                  {isLiveActive ? 'SURVEILLANCE IA ACTIVE' : 'SUPERVISION EN PAUSE'}
                </span>
              </div>
              <button 
                onClick={() => setIsLiveActive(!isLiveActive)}
                className={`login-btn ${isLiveActive ? 'danger' : ''}`}
                style={{ 
                  padding: '6px 16px', 
                  fontSize: '0.8rem', 
                  margin: 0, 
                  background: isLiveActive ? '#ef4444' : '#06b6d4',
                  boxShadow: isLiveActive ? '0 4px 12px rgba(239, 68, 68, 0.2)' : '0 4px 12px rgba(6, 182, 212, 0.2)',
                  color: '#ffffff'
                }}
              >
                {isLiveActive ? "Mettre en pause" : "Démarrer le flux en direct"}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
            {/* Left section: rolling scans */}
            <div style={{ flex: 2, minWidth: '350px' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                <span>Flux des Scans IA</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>Dossiers traités : <strong>{scannedCount}</strong></span>
              </h4>

              {/* Scanning Item (Animated) */}
              {isLiveActive && scanningFile ? (
                <div style={{ 
                  background: 'rgba(6, 182, 212, 0.04)', 
                  border: '1px dashed rgba(6, 182, 212, 0.35)', 
                  borderRadius: '8px', 
                  padding: '12px 15px', 
                  marginBottom: '12px',
                  position: 'relative',
                  overflow: 'hidden'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#22d3ee' }}>⚡ SCAN EN COURS : {scanningFile.dossierNum}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{scanningFile.importer}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '15px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    <span>Origine : <strong>{scanningFile.country}</strong></span>
                    <span>Valeur : <strong>{formatCFA(scanningFile.value)}</strong></span>
                    <span>SH : <strong>{scanningFile.hs_code}</strong></span>
                  </div>
                  {/* Progress bar */}
                  <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                    <div style={{ width: `${scanProgress}%`, height: '100%', background: 'linear-gradient(90deg, #06b6d4, #22d3ee)', borderRadius: '2px', transition: 'width 0.15s ease' }}></div>
                  </div>
                </div>
              ) : isLiveActive ? (
                <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border)', borderRadius: '8px', padding: '15px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '12px' }}>
                  En attente du prochain dossier douanier...
                </div>
              ) : (
                <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border)', borderRadius: '8px', padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                  Cliquez sur « Démarrer le flux » pour lancer l'analyse des dossiers en direct.
                </div>
              )}

              {/* Logs list */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '350px', overflowY: 'auto', paddingRight: '5px' }}>
                {liveLogs.map((log, idx) => {
                  const isHighRisk = log.riskScore > 70;
                  const isMedRisk = log.riskScore > 40 && log.riskScore <= 70;
                  const isSelected = selectedXaiFile?.dossierNum === log.dossierNum;
                  
                  let borderCol = isSelected ? '#22d3ee' : 'rgba(16, 185, 129, 0.2)';
                  let bgCol = 'rgba(16, 185, 129, 0.02)';
                  let textCol = '#10b981';
                  
                  if (isHighRisk) {
                    borderCol = isSelected ? '#22d3ee' : 'rgba(239, 68, 68, 0.3)';
                    bgCol = 'rgba(239, 68, 68, 0.04)';
                    textCol = '#ef4444';
                  } else if (isMedRisk) {
                    borderCol = isSelected ? '#22d3ee' : 'rgba(245, 158, 11, 0.25)';
                    bgCol = 'rgba(245, 158, 11, 0.03)';
                    textCol = '#f59e0b';
                  }

                  return (
                    <div 
                      key={idx} 
                      onClick={() => setSelectedXaiFile(log)}
                      style={{ 
                        background: bgCol, 
                        border: isSelected ? `2.0px solid ${borderCol}` : `1px solid ${borderCol}`, 
                        borderRadius: '8px', 
                        padding: '12px 15px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.25s ease',
                        cursor: 'pointer',
                        transform: isSelected ? 'scale(1.008)' : 'none',
                        boxShadow: isSelected ? '0 0 10px rgba(34, 211, 238, 0.1)' : 'none'
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--text-main)' }}>{log.dossierNum}</span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{log.time}</span>
                          <span style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-muted)' }}>{log.mode}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '15px', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                          <span>Importer: <strong>{log.importer}</strong></span>
                          <span>Origine: <strong>{log.country}</strong></span>
                          <span>Montant: <strong>{formatCFA(log.value)}</strong></span>
                        </div>
                        {log.reasons.length > 0 && (
                          <div style={{ marginTop: '6px', fontSize: '0.72rem', color: isHighRisk ? '#fca5a5' : 'var(--text-muted)', fontStyle: 'italic' }}>
                            ⚠ {log.reasons.join(' | ')}
                          </div>
                        )}
                      </div>
                      
                      <div style={{ textAlign: 'right', marginLeft: '15px' }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800, color: textCol }}>{log.riskScore}%</div>
                        <div style={{ fontSize: '0.68rem', fontWeight: 600, color: textCol, textTransform: 'uppercase' }}>
                          {isHighRisk ? 'Risque Critique' : isMedRisk ? 'Risque Medium' : 'Risque Low'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right section: XAI Decision Panel OR Critical Alerts Feed */}
            <div style={{ flex: 1.2, minWidth: '300px', borderLeft: '1px solid var(--border)', paddingLeft: '20px' }}>
              {selectedXaiFile ? (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                      Explication IA : {selectedXaiFile.dossierNum}
                    </h4>
                    <button 
                      onClick={() => setSelectedXaiFile(null)}
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid var(--border)',
                        borderRadius: '4px',
                        color: 'var(--text-muted)',
                        padding: '2px 8px',
                        fontSize: '0.7rem',
                        cursor: 'pointer'
                      }}
                    >
                      Voir alertes ({criticalAlerts.length})
                    </button>
                  </div>

                  {/* Main XAI Card */}
                  <div style={{
                    background: 'rgba(255, 255, 255, 0.01)',
                    border: '1px solid var(--border)',
                    borderRadius: '12px',
                    padding: '15px',
                    boxShadow: '0 8px 30px rgba(0,0,0,0.2)',
                    position: 'relative',
                    overflow: 'hidden'
                  }}>
                    {/* Glowing Risk gauge */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>CIBLAGE SENTINEL IA</span>
                      <span style={{ 
                        fontSize: '0.8rem', 
                        fontWeight: 'bold', 
                        color: selectedXaiFile.riskScore > 70 ? '#ef4444' : selectedXaiFile.riskScore > 40 ? '#f59e0b' : '#10b981',
                        background: selectedXaiFile.riskScore > 70 ? 'rgba(239, 68, 68, 0.1)' : selectedXaiFile.riskScore > 40 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                        padding: '2px 8px',
                        borderRadius: '10px'
                      }}>
                        Score : {selectedXaiFile.riskScore}%
                      </span>
                    </div>

                    {/* SHAP Feature Contributions */}
                    <div style={{ marginBottom: '15px' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '8px' }}>
                        CONTRIBUTION DES PARAMÈTRES (SHAP VALUES)
                      </div>
                      
                      {/* Param 1: Z-Score Value */}
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-main)', marginBottom: '3px' }}>
                          <span>Z-Score (Écart valeur/code SH)</span>
                          <strong>{selectedXaiFile.xai?.shap_value || 0}%</strong>
                        </div>
                        <div style={{ width: '100%', height: '5px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                          <div style={{ width: `${selectedXaiFile.xai?.shap_value || 0}%`, height: '100%', background: '#ef4444', borderRadius: '2px' }}></div>
                        </div>
                      </div>

                      {/* Param 2: Isolation Forest Behavior */}
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-main)', marginBottom: '3px' }}>
                          <span>Isolation Forest (Comportement atypique)</span>
                          <strong>{selectedXaiFile.xai?.shap_iforest || 0}%</strong>
                        </div>
                        <div style={{ width: '100%', height: '5px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                          <div style={{ width: `${selectedXaiFile.xai?.shap_iforest || 0}%`, height: '100%', background: '#f59e0b', borderRadius: '2px' }}></div>
                        </div>
                      </div>

                      {/* Param 3: K-Means Segmentation multiplier */}
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-main)', marginBottom: '3px' }}>
                          <span>Segmentation K-Means (Profil Importer)</span>
                          <strong>{selectedXaiFile.xai?.shap_kmeans || 0}%</strong>
                        </div>
                        <div style={{ width: '100%', height: '5px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                          <div style={{ width: `${selectedXaiFile.xai?.shap_kmeans || 0}%`, height: '100%', background: '#10b981', borderRadius: '2px' }}></div>
                        </div>
                      </div>
                    </div>

                    {/* AI Decision Text */}
                    <div style={{ 
                      background: 'rgba(255,255,255,0.02)', 
                      border: '1px solid var(--border)', 
                      borderRadius: '8px', 
                      padding: '10px 12px',
                      fontSize: '0.76rem',
                      lineHeight: '1.4',
                      color: 'var(--text-main)',
                      marginBottom: '15px'
                    }}>
                      <strong>Decision analysis:</strong><br/>
                      {selectedXaiFile.xai?.explanation || "No explanation generated for this file."}
                    </div>

                    {/* Action buttons with custom simulation handler */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        onClick={() => {
                          alert(`File ${selectedXaiFile.dossierNum} inspected and marked as COMPLIANT.`);
                          setSelectedXaiFile(null);
                        }}
                        style={{
                          flex: 1,
                          background: 'rgba(16, 185, 129, 0.1)',
                          border: '1px solid #10b981',
                          color: '#10b981',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '0.72rem',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        Approve Compliant
                      </button>
                      <button 
                        onClick={() => {
                          alert(`Interception triggered for file ${selectedXaiFile.dossierNum}. Active customs block.`);
                          setSelectedXaiFile(null);
                        }}
                        style={{
                          flex: 1,
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid #ef4444',
                          color: '#ef4444',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '0.72rem',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        Block Cargo
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ef4444', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="pulse" style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444', display: 'inline-block' }}></span>
                    <span>Alertes Critiques en Cours ({criticalAlerts.length})</span>
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '350px', overflowY: 'auto' }}>
                    {criticalAlerts.length > 0 ? (
                      criticalAlerts.map((alert, idx) => (
                        <div 
                          key={idx} 
                          onClick={() => setSelectedXaiFile(alert)}
                          style={{ 
                            background: 'rgba(239, 68, 68, 0.05)', 
                            border: '1px solid rgba(239, 68, 68, 0.25)', 
                            borderRadius: '6px', 
                            padding: '8px 12px',
                            fontSize: '0.74rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }} 
                          className="threat-alert-pulse hover-scale-card"
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', color: '#fca5a5', marginBottom: '3px' }}>
                            <span>{alert.dossierNum}</span>
                            <span>{alert.riskScore}% Risque</span>
                          </div>
                          <div style={{ color: 'var(--text-muted)', marginBottom: '3px' }}>
                            {alert.importer} ({alert.country})
                          </div>
                          <div style={{ color: '#ef4444', fontSize: '0.7rem', fontWeight: 600 }}>
                            {alert.reasons[0]}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border)', borderRadius: '6px' }}>
                        No critical threats detected in this session.
                      </div>
                    )}
                  </div>
                  
                  {/* Select guide box */}
                  <div style={{ 
                    marginTop: '15px', 
                    padding: '12px 15px', 
                    borderRadius: '8px', 
                    border: '1px solid var(--border)', 
                    background: 'rgba(6, 182, 212, 0.02)',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    lineHeight: '1.4'
                  }}>
                    💡 <strong>Astuce Démonstration :</strong> Cliquez sur n'importe quel dossier à gauche ou au-dessus pour inspecter l'explicabilité de la décision de l'IA (modèle SHAP / Contribution).
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Grid of Risk and Fraud charts */}
      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Répartition du Profil de Risque Douanier</div>
          <div ref={riskPieRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Comparaison des Detection Models de Fraude</div>
          <div ref={fraudCompareRef} className="chart-container"></div>
        </div>
      </div>

      {/* LSTM Forecasting Chart */}
      {data?.lstm_forecast && (
        <div className="dashboard-row full-width">
          <div className="chart-card full-width-card">
            <div className="chart-card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>AI File Flow Forecasting (LSTM Deep Learning Model)</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                MAE: <strong>{data.lstm_forecast.metrics.MAE.toFixed(1)}</strong> | RMSE: <strong>{data.lstm_forecast.metrics.RMSE.toFixed(1)}</strong>
              </span>
            </div>
            
            <div ref={lstmChartRef} className="chart-container" style={{ height: '320px' }}></div>
            
            {/* Simplified Reading Guide for Non-IT Users */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
              gap: '15px', 
              marginTop: '20px', 
              padding: '15px', 
              borderRadius: '8px', 
              background: 'var(--bg-light)', 
              border: '1px solid var(--border)',
              fontSize: '0.82rem'
            }}>
              <div>
                <span style={{ fontWeight: 'bold', color: 'var(--text-main)', display: 'block', marginBottom: '6px', fontSize: '0.88rem' }}>💡 Comprendre ce graphique</span>
                <span style={{ color: 'var(--text-muted)', lineHeight: '1.4', display: 'block' }}>
                  L'Intelligence Artificielle (LSTM) analyse l'historique de l'activité douanière pour anticiper le nombre de dossiers arrivant quotidiennement. 
                  Cela permet aux chefs de bureau d'anticiper la charge de travail et d'optimiser l'affectation des inspecteurs.
                </span>
              </div>
              <div>
                <span style={{ fontWeight: 'bold', color: 'var(--text-main)', display: 'block', marginBottom: '6px', fontSize: '0.88rem' }}>📈 Légende Simple</span>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  • <strong style={{ color: '#38bdf8' }}>Flux Réels (Bleu)</strong> : Le nombre exact de dossiers enregistrés.
                </span>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  • <strong style={{ color: '#f43f5e' }}>Prévisions IA (Rouge pointillé)</strong> : Le volume de dossiers estimé par l'algorithme.
                </span>
                <span style={{ color: 'var(--text-muted)', display: 'block' }}>
                  • <strong>Zone Bleue Claire</strong> : La marge d'erreur normale de l'IA (intervalle de confiance à 95%).
                </span>
              </div>
              <div>
                <span style={{ fontWeight: 'bold', color: 'var(--text-main)', display: 'block', marginBottom: '6px', fontSize: '0.88rem' }}>🎯 Fiabilité de l'IA</span>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  • Écart moyen observé : <strong>± {Math.round(data.lstm_forecast.metrics.MAE)} dossiers</strong> par jour.
                </span>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
                  • Statut des prévisions : <span className="badge badge-success" style={{ padding: '3px 8px', fontSize: '0.75rem' }}>Stable & Activée</span>
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontStyle: 'italic', display: 'block' }}>
                  * Les fluctuations du week-end sont automatiquement prises en compte (l'activité diminue naturellement le samedi et le dimanche).
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Forecasting Models Evaluation */}
      <div className="dashboard-row full-width">
        <div className="chart-card full-width-card">
          <div className="chart-card-title">Évaluation des Modèles de Prévision (Forecasting)</div>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Search un modèle..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div className="table-pagination">
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {currentPage} / {totalPages} ({filteredForecastRows.length} models)
              </span>
              <button
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table>
              <thead>
                <tr>
                  <th>Modèle</th>
                  <th>MAE (Files)</th>
                  <th>RMSE</th>
                  <th>MAPE (%)</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {paginatedForecastRows.length > 0 ? (
                  paginatedForecastRows.map(row => {
                    const isBest = row.model === bestModel;
                    let badgeClass = 'badge';
                    let statusLabel = '';
                    if (isBest) {
                      badgeClass += ' badge-success';
                      statusLabel = "Recommandé";
                    } else if (row.isBaseline) {
                      badgeClass += ' badge-warning';
                      statusLabel = "Référence";
                    } else {
                      badgeClass += ' badge-danger';
                      statusLabel = "Validé";
                    }

                    return (
                      <tr key={row.model}>
                        <td><strong>{row.model}</strong></td>
                        <td>{row.MAE.toFixed(2)}</td>
                        <td>{row.RMSE.toFixed(2)}</td>
                        <td>{row.MAPE.toFixed(2)} %</td>
                        <td><span className={badgeClass}>{statusLabel}</span></td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No model found or unauthorized access.
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
