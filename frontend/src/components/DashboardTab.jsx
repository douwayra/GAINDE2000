import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { formatCFA, formatWeight, fetchWithAuth } from '../utils/api';
import { getStandardCountryName, countryCoords } from '../utils/mapUtils';
import AnimatedCounter from './AnimatedCounter';

export default function DashboardTab({ data, files, role, onFileClick, onTargetFile, theme, filterOptions }) {
  const [mapMode, setMapMode] = useState('imports');
  const [exportTransport, setExportTransport] = useState('');
  const [exportCountry, setExportCountry] = useState('');
  const [exportTypeOperation, setExportTypeOperation] = useState('');
  const [exportRegimeDouanier, setExportRegimeDouanier] = useState('');
  const [exportStatusFile, setExportStatusFile] = useState('');
  const [exportAnnee, setExportAnnee] = useState('');
  const [exportResult, setExportResult] = useState('');
  const [exportLoading, setExportLoading] = useState(false);

  // Search & Pagination states for files table
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const filteredFiles = (files || []).filter(row => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return true;
    return (
      String(row.NUMERODOSSIERTPS || '').toLowerCase().includes(term) ||
      String(row.TYPE_OPERATION || '').toLowerCase().includes(term) ||
      String(row.DATE_CREATION || '').toLowerCase().includes(term) ||
      String(row.STATUT_DOSSIER || '').toLowerCase().includes(term) ||
      String(row.MODE_TRANSPORT || '').toLowerCase().includes(term) ||
      String(row.NOM_IMPORTATEUR || '').toLowerCase().includes(term) ||
      String(row.REGIME_DOUANIER || '').toLowerCase().includes(term) ||
      String(row.RISK_CLASS || '').toLowerCase().includes(term) ||
      String(row.RISK_SCORE || '').toLowerCase().includes(term)
    );
  });

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.ceil(filteredFiles.length / ITEMS_PER_PAGE) || 1;
  const paginatedFiles = filteredFiles.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Chart Container Refs
  const worldMapRef = useRef(null);
  const geoRef = useRef(null);
  const evolutionRef = useRef(null);
  const topGoodsRef = useRef(null);
  const heatmapRef = useRef(null);
  const opVolRef = useRef(null);
  const opValRef = useRef(null);

  // Chart Instances
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

  // 1. World Map Chart
  useEffect(() => {
    if (!worldMapRef.current || !data?.geography) return;

    let chart = chartInstances.current.worldMap;
    if (!chart) {
      chart = echarts.init(worldMapRef.current);
      chartInstances.current.worldMap = chart;
    }

    fetch('/world.json')
      .then(res => res.json())
      .then(worldJson => {
        echarts.registerMap('world', worldJson);
        updateWorldMap(chart);
      })
      .catch(err => {
        console.warn("Impossible de charger la carte du monde en local, tentative CDN...");
        fetch('https://fastly.jsdelivr.net/npm/echarts@4.9.0/map/json/world.json')
          .then(res => res.json())
          .then(worldJson => {
            echarts.registerMap('world', worldJson);
            updateWorldMap(chart);
          })
          .catch(cdnErr => {
            console.error("Impossible de charger la carte du monde :", cdnErr);
            if (worldMapRef.current) {
              worldMapRef.current.innerHTML = `
                <div style="padding: 40px; text-align: center; color: var(--text-muted); height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                  <p style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">Carte indisponible</p>
                  <p style="font-size: 0.85rem;">Impossible de charger le fond de carte mondial.</p>
                </div>
              `;
            }
          });
      });

    function updateWorldMap(chartInst) {
      let mapData = [];
      let titleText = '';
      let seriesName = '';
      let maxVal = 1000000000;
      let colorGradient = [];

      if (mapMode === 'imports') {
        mapData = (data.geography.import_country_stats || []).map(c => {
          const stdName = getStandardCountryName(c.country);
          return {
            name: stdName,
            originalName: c.country,
            value: c.valeur,
            count: c.count
          };
        }).filter(c => c.name);
        titleText = "Provenance des Importations Douanières vers le Sénégal";
        seriesName = "Importations (CFA)";
        maxVal = mapData.length > 0 ? Math.max(...mapData.map(c => c.value)) : 1000000000;
        colorGradient = isDark ? ['#1e3a8a', '#3b82f6', '#0ea5e9', '#06b6d4', '#22d3ee'] : ['#f1f5f9', '#93c5fd', '#3b82f6', '#1d4ed8'];
      } else {
        mapData = (data.geography.export_country_stats || []).map(c => {
          const stdName = getStandardCountryName(c.country);
          return {
            name: stdName,
            originalName: c.country,
            value: c.valeur,
            count: c.count
          };
        }).filter(c => c.name);
        titleText = "Destination des Exportations Douanières depuis le Sénégal";
        seriesName = "Exportations (CFA)";
        maxVal = mapData.length > 0 ? Math.max(...mapData.map(c => c.value)) : 40000000000;
        colorGradient = isDark ? ['#065f46', '#10b981', '#34d399', '#4ade80', '#a7f3d0'] : ['#f0fdf4', '#86efac', '#22c55e', '#166534'];
      }

      // Generate lines data from/to Senegal
      const linesData = [];
      const senegalCoords = countryCoords['Senegal'] || [-14.45, 14.49];
      
      mapData.forEach(c => {
        const cCoords = countryCoords[c.name];
        if (cCoords && c.value > 0 && c.name !== 'Senegal') {
          linesData.push({
            coords: mapMode === 'imports' ? [cCoords, senegalCoords] : [senegalCoords, cCoords],
            value: c.value,
            name: c.originalName || c.name
          });
        }
      });

      chartInst.setOption({
        title: {
          show: false,
          text: titleText,
          left: 'center',
          textStyle: { fontSize: 13, color: isDark ? '#f1f5f9' : '#0f172a', fontFamily: 'Outfit', fontWeight: 600 }
        },
        tooltip: {
          trigger: 'item',
          backgroundColor: isDark ? 'rgba(9, 14, 30, 0.95)' : '#ffffff',
          borderColor: isDark ? 'rgba(6, 182, 212, 0.3)' : 'rgba(15, 23, 42, 0.15)',
          borderWidth: 1,
          textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit', fontSize: 12 },
          formatter: function (params) {
            if (params.seriesType === 'map' || params.componentSubType === 'map') {
              if (params.data && params.data.value) {
                const origName = params.data.originalName || params.name;
                return `<div style="padding:4px 8px;">
                          <b style="font-size:13px; color: ${isDark ? '#22d3ee' : '#2075db'}">${origName}</b><br/>
                          <span style="color:${isDark ? '#94a3b8' : '#64748b'}">${mapMode === 'imports' ? 'Provenance' : 'Destination'} :</span> <b>${formatCFA(params.data.value)}</b><br/>
                          <span style="color:${isDark ? '#94a3b8' : '#64748b'}">Dossiers :</span> <b>${params.data.count.toLocaleString('fr-FR')}</b>
                        </div>`;
              }
              return `<div style="padding:4px 8px;"><b style="color:${isDark ? '#94a3b8' : '#64748b'}">${params.name}</b><br/>Pas de flux direct enregistré</div>`;
            }
            return null;
          }
        },
        visualMap: {
          min: 0,
          max: maxVal,
          left: 'left',
          top: 'bottom',
          text: ['Haut', 'Bas'],
          textStyle: { color: isDark ? '#94a3b8' : '#475569', fontFamily: 'Outfit' },
          calculable: true,
          inRange: {
            color: colorGradient
          }
        },
        geo: {
          map: 'world',
          roam: true,
          zoom: 1.1,
          center: [10, 25],
          label: { show: false },
          itemStyle: {
            areaColor: isDark ? '#1b2535' : '#e2e8f0',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(15, 23, 42, 0.08)',
            borderWidth: 0.6
          },
          emphasis: {
            itemStyle: {
              areaColor: isDark ? 'rgba(6, 182, 212, 0.35)' : 'rgba(32, 117, 219, 0.25)',
              borderColor: isDark ? '#22d3ee' : '#2075db',
              borderWidth: 1.2
            },
            label: { show: false }
          }
        },
        series: [
          {
            name: seriesName,
            type: 'map',
            geoIndex: 0,
            data: mapData
          },
          {
            name: 'Glow Halo',
            type: 'lines',
            coordinateSystem: 'geo',
            zlevel: 1,
            lineStyle: {
              color: mapMode === 'imports' ? '#0ea5e9' : '#10b981',
              width: 3.5,
              opacity: 0.08,
              curveness: 0.25,
              shadowBlur: 8,
              shadowColor: mapMode === 'imports' ? '#0ea5e9' : '#10b981'
            },
            data: linesData
          },
          {
            name: 'Routes Commerciales',
            type: 'lines',
            coordinateSystem: 'geo',
            zlevel: 2,
            effect: {
              show: true,
              period: 4.5,
              trailLength: 0.35,
              color: mapMode === 'imports' ? '#22d3ee' : '#34d399',
              symbol: 'circle',
              symbolSize: 4.5,
              shadowBlur: 5,
              shadowColor: mapMode === 'imports' ? '#22d3ee' : '#34d399'
            },
            lineStyle: {
              color: mapMode === 'imports' ? 'rgba(34, 211, 238, 0.3)' : 'rgba(52, 211, 153, 0.3)',
              width: 1.5,
              curveness: 0.25
            },
            data: linesData
          }
        ]
      });

      // Force instant resize to calculate sizes correctly on mount
      setTimeout(() => {
        if (chartInst) chartInst.resize();
      }, 50);
    }
  }, [data, mapMode, theme]);

  // 2. Zone Eco Pie Chart
  useEffect(() => {
    if (!geoRef.current || !data?.geography?.region_val_split) return;

    let chart = chartInstances.current.geo;
    if (!chart) {
      chart = echarts.init(geoRef.current);
      chartInstances.current.geo = chart;
    }

    const geoData = Object.entries(data.geography.region_val_split).map(([k, v]) => ({ name: k, value: v }));
    chart.setOption({
      tooltip: { 
        trigger: 'item', 
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
        formatter: params => `${params.name}: ${formatCFA(params.value)} (${params.percent}%)` 
      },
      legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
      color: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#f43f5e'],
      series: [{
        name: "Regions",
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 0, borderWidth: 0 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#ffffff' } },
        labelLine: { show: false },
        data: geoData
      }]
    });
  }, [data, theme]);

  // 3. Monthly Evolution Time Series
  useEffect(() => {
    if (!evolutionRef.current || !data?.time_decomposition?.month) return;

    let chart = chartInstances.current.evolution;
    if (!chart) {
      chart = echarts.init(evolutionRef.current);
      chartInstances.current.evolution = chart;
    }

    const timeKeys = Object.keys(data.time_decomposition.month);
    const timeVals = Object.values(data.time_decomposition.month);
    chart.setOption({
      tooltip: { 
        trigger: 'axis',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      xAxis: { type: 'category', data: timeKeys, ...axisOptions },
      yAxis: { type: 'value', name: 'Volume', ...axisOptions },
      series: [{
        data: timeVals,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3, color: '#38bdf8' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.4)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.01)' }
          ])
        }
      }]
    });
  }, [data, theme]);

  // 4. Top Goods Bar Chart
  useEffect(() => {
    if (!topGoodsRef.current || !data?.top_products?.by_value) return;

    let chart = chartInstances.current.topGoods;
    if (!chart) {
      chart = echarts.init(topGoodsRef.current);
      chartInstances.current.topGoods = chart;
    }

    const goodsData = data.top_products.by_value.slice(0, 5);
    chart.setOption({
      grid: {
        left: '3%',
        right: '12%',
        bottom: '3%',
        containLabel: true
      },
      tooltip: { 
        trigger: 'axis', 
        axisPointer: { type: 'shadow' },
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
        formatter: function(params) {
          const idx = params[0].dataIndex;
          const originalItem = goodsData[goodsData.length - 1 - idx];
          return `<b>${originalItem.DESIGNATION}</b><br/>Code Tarif : ${originalItem.NUMEROTARIFDOUANE}<br/>Value : ${formatCFA(originalItem.VALEURCFA)}`;
        }
      },
      xAxis: { type: 'value', name: "Value", ...axisOptions },
      yAxis: { type: 'category', data: goodsData.map(d => d.DESIGNATION.slice(0, 18) + '...').reverse(), ...axisOptions },
      series: [{
        type: 'bar',
        data: goodsData.map(d => d.VALEURCFA).reverse(),
        itemStyle: { color: '#38bdf8', borderRadius: [0, 5, 5, 0] }
      }]
    });
  }, [data, theme]);

  // 5. Heatmap Jour de semaine x Mois
  useEffect(() => {
    if (!heatmapRef.current || !data?.time_decomposition?.heatmap) return;

    let chart = chartInstances.current.heatmap;
    if (!chart) {
      chart = echarts.init(heatmapRef.current);
      chartInstances.current.heatmap = chart;
    }

    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    const heatCells = [];
    data.time_decomposition.heatmap.forEach(item => {
      const dIdx = days.indexOf(item.DAY_OF_WEEK);
      const mIdx = months.indexOf(item.MONTH);
      if (dIdx !== -1 && mIdx !== -1) {
        heatCells.push([dIdx, mIdx, item.count]);
      }
    });

    chart.setOption({
      tooltip: { 
        position: 'top',
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      grid: { height: '70%', top: '8%', bottom: '15%' },
      xAxis: { type: 'category', data: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], splitArea: { show: true }, ...axisOptions },
      yAxis: { type: 'category', data: ['Jan', "Fév", 'Mar', "Avr", "Mai", "Jui", 'Jul', "Aoû", 'Sep', 'Oct', 'Nov', "Déc"], splitArea: { show: true }, ...axisOptions },
      visualMap: { 
        min: 0, 
        max: 8000, 
        calculate: true, 
        orient: 'horizontal', 
        left: 'center', 
        bottom: '0%', 
        textStyle: { color: isDark ? '#94a3b8' : '#475569', fontFamily: 'Outfit' },
        inRange: { color: isDark ? ['#0f1c3f', '#2075db', '#38bdf8'] : ['#eff6ff', '#3b82f6', '#1d4ed8'] } 
      },
      series: [{
        name: "Activity",
        type: 'heatmap',
        data: heatCells,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    });
  }, [data, theme]);

  // 6. Operation Volume Pie Chart
  useEffect(() => {
    if (!opVolRef.current || !data?.logistics?.operation_stats) return;

    let chart = chartInstances.current.opVol;
    if (!chart) {
      chart = echarts.init(opVolRef.current);
      chartInstances.current.opVol = chart;
    }

    const opVolData = data.logistics.operation_stats.map(row => ({ name: row.TYPE_OPERATION, value: row.count }));
    chart.setOption({
      tooltip: { 
        trigger: 'item', 
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
        formatter: params => `${params.name}: ${params.value.toLocaleString('fr-FR')} files (${params.percent}%)` 
      },
      legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
      color: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
      series: [{
        name: "Operations (Volume)",
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 0, borderWidth: 0 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#ffffff' } },
        data: opVolData
      }]
    });
  }, [data, theme]);

  // 7. Operation Value Bar Chart
  useEffect(() => {
    if (!opValRef.current || !data?.logistics?.operation_stats) return;

    let chart = chartInstances.current.opVal;
    if (!chart) {
      chart = echarts.init(opValRef.current);
      chartInstances.current.opVal = chart;
    }

    const opValData = data.logistics.operation_stats;
    chart.setOption({
      tooltip: { 
        trigger: 'axis', 
        axisPointer: { type: 'shadow' },
        backgroundColor: isDark ? '#0f172a' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
        textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
      },
      xAxis: { type: 'category', data: opValData.map(d => d.TYPE_OPERATION), ...axisOptions },
      yAxis: { type: 'value', name: 'Trillions', ...axisOptions },
      series: [{
        type: 'bar',
        data: opValData.map(d => d.total_valeur / 1e12),
        itemStyle: { color: '#2075db', borderRadius: [5, 5, 0, 0] },
        label: { show: true, position: 'top', color: isDark ? '#38bdf8' : '#0284c7', formatter: params => `${params.value.toFixed(2)} T` }
      }]
    });
  }, [data, theme]);

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      Object.values(chartInstances.current).forEach(chart => {
        if (chart) chart.resize();
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Handle Statistician Export
  const generateAnonymizedExport = async () => {
    setExportLoading(true);
    setExportResult('');
    try {
      const response = await fetchWithAuth('/api/statistician/export-csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode_transport: exportTransport || null,
          country: exportCountry || null,
          type_operation: exportTypeOperation || null,
          regime_douanier: exportRegimeDouanier || null,
          statut_dossier: exportStatusFile || null,
          annee: exportAnnee || null
        })
      });

      if (!response.ok) throw new Error("Erreur de génération");
      const resData = await response.json();
      setExportResult(resData.download_url);
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la génération de l\'export.");
    } finally {
      setExportLoading(false);
    }
  };

  const handleDownloadCSV = async (e) => {
    e.preventDefault();
    if (!exportResult) return;
    try {
      const response = await fetchWithAuth(exportResult);
      if (!response.ok) throw new Error("Erreur de téléchargement");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = exportResult.split('/').pop() || 'export_anonyme.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Erreur lors du téléchargement. Veuillez vérifier votre connexion.");
    }
  };

  if (!data || data.error || !data.kpis) {
    if (data && data.error) {
      return (
        <div style={{ textAlign: 'center', padding: '50px', color: '#ef4444', fontFamily: 'Outfit' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '10px' }}>Erreur de chargement</h3>
          <p>{data.error}</p>
        </div>
      );
    }
    return <div style={{ textAlign: 'center', padding: '50px' }}><div className="loader"></div></div>;
  }

  return (
    <>
      {/* KPIs Grid */}
      <div className="kpis-grid">
        {/* Card 1: Files Douaniers */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
            </div>
            <span className="kpi-title">Dossiers Traités</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value">
                <AnimatedCounter value={data.kpis.total_dossiers} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +4,2%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="12" width="5" height="18" rx="2.5" fill="var(--primary)" />
                <rect x="12" y="8" width="5" height="22" rx="2.5" fill="var(--primary)" />
                <rect x="24" y="15" width="5" height="15" rx="2.5" fill="var(--primary)" />
                <rect x="36" y="5" width="5" height="25" rx="2.5" fill="var(--primary)" />
                <rect x="48" y="2" width="5" height="28" rx="2.5" fill="var(--primary)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 2: Factures Commerciales */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper success">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="16" y1="21" x2="16" y2="19"/><line x1="8" y1="21" x2="8" y2="19"/><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 17h.01"/><path d="M12 17h.01"/><path d="M16 17h.01"/></svg>
            </div>
            <span className="kpi-title">Factures Commerciales</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value">
                <AnimatedCounter value={data.kpis.total_factures} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +2,8%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="15" width="5" height="15" rx="2.5" fill="var(--success)" />
                <rect x="12" y="10" width="5" height="20" rx="2.5" fill="var(--success)" />
                <rect x="24" y="6" width="5" height="24" rx="2.5" fill="var(--success)" />
                <rect x="36" y="12" width="5" height="18" rx="2.5" fill="var(--success)" />
                <rect x="48" y="4" width="5" height="26" rx="2.5" fill="var(--success)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 3: Nombre d'Articles */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper purple">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
            </div>
            <span className="kpi-title">Nombre d'Articles</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value">
                <AnimatedCounter value={data.kpis.total_articles} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +1,5%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="15" width="5" height="15" rx="2.5" fill="#8b5cf6" />
                <rect x="12" y="10" width="5" height="20" rx="2.5" fill="#8b5cf6" />
                <rect x="24" y="18" width="5" height="12" rx="2.5" fill="#8b5cf6" />
                <rect x="36" y="8" width="5" height="22" rx="2.5" fill="#8b5cf6" />
                <rect x="48" y="5" width="5" height="25" rx="2.5" fill="#8b5cf6" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 4: Value Globale */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper cyan">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
            <span className="kpi-title">Valeur Globale Déclarée</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#0ea5e9' }}>
                <AnimatedCounter value={data.kpis.total_val_cfa} formatter={formatCFA} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +5,4%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,22 Q15,5 30,17 T60,2" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,22 Q15,5 30,17 T60,2 L60,30 L0,30 Z" fill="rgba(14, 165, 233, 0.06)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 5: Total Volume */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper orange">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 7H2M12 2v20M5 7l2 10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l2-10"/></svg>
            </div>
            <span className="kpi-title">Volume Total</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#f97316' }}>
                <AnimatedCounter value={data.kpis.total_poids_net} formatter={formatWeight} />
              </span>
              <span className="kpi-trend warning">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                Stagnant
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,15 Q15,10 30,15 T60,12" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,15 Q15,10 30,15 T60,12 L60,30 L0,30 Z" fill="rgba(249, 115, 22, 0.06)" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* World Map */}
      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
            <span>Flux Commerciaux Mondiaux (Référentiel : Sénégal)</span>
            <div className="map-toggle-container" style={{ display: 'flex', gap: '10px', marginTop: '5px' }}>
              <button 
                className={`btn ${mapMode === 'imports' ? 'active' : ''}`} 
                onClick={() => setMapMode('imports')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid var(--primary-light)',
                  backgroundColor: mapMode === 'imports' ? 'var(--primary)' : 'transparent',
                  color: mapMode === 'imports' ? 'white' : 'var(--text-main)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  transition: 'all 0.2s'
                }}
              >
                Imports (to Senegal)
              </button>
              <button 
                className={`btn ${mapMode === 'exports' ? 'active' : ''}`} 
                onClick={() => setMapMode('exports')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid var(--success)',
                  backgroundColor: mapMode === 'exports' ? 'var(--success)' : 'transparent',
                  color: mapMode === 'exports' ? 'white' : 'var(--text-main)',
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
          <div ref={worldMapRef} style={{ height: '500px', width: '100%' }}></div>
        </div>
      </div>

      {/* Grid Row 2 */}
      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Échanges par Zone Économique</div>
          <div ref={geoRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Évolution de l\'Activité (Séries Temporelles)</div>
          <div ref={evolutionRef} className="chart-container"></div>
        </div>
      </div>

      {/* Grid Row 3 */}
      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Top 5 Marchandises en Valeur (CFA)</div>
          <div ref={topGoodsRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Heatmap d\'Activité (Jour × Mois)</div>
          <div ref={heatmapRef} className="chart-container"></div>
        </div>
      </div>

      {/* Grid Row 4 */}
      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Répartition des Opérations (Volume)</div>
          <div ref={opVolRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Valeur Financière par Opération (Trillions CFA)</div>
          <div ref={opValRef} className="chart-container"></div>
        </div>
      </div>

      {/* Preview Table */}
      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Aperçu des Dossiers Douaniers (Row & Column Level Security)</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Données filtrées selon privilèges</span>
          </div>

          <div className="table-controls">
            <input
              type="text"
              className="table-search-input"
              placeholder="Rechercher un dossier..."
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
                Page {currentPage} / {totalPages} ({filteredFiles.length} dossiers)
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
                  <th>N° Dossier</th>
                  <th>Opération</th>
                  <th>Date Création</th>
                  <th>Statut</th>
                  <th>Transport</th>
                  <th>Importateur / Client</th>
                  <th>Régime</th>
                  <th>Score Risque</th>
                  <th>Classe Risque</th>
                  {(role === 'inspecteur' || role === 'admin') && <th>Action (Ciblage)</th>}
                </tr>
              </thead>
              <tbody>
                {paginatedFiles && paginatedFiles.length > 0 ? (
                  paginatedFiles.map(row => {
                    let riskBadge = '';
                    const rClass = row.RISK_CLASS;
                    if (rClass === 'Haut Risque' || rClass === 'Haut') {
                      riskBadge = 'badge badge-danger';
                    } else if (rClass === 'Medium Risque' || rClass === "Moyenne") {
                      riskBadge = 'badge badge-warning';
                    } else if (rClass === 'Low Risque' || rClass === "Faible") {
                      riskBadge = 'badge badge-success';
                    } else if (rClass === 'NON AUTORISÉ') {
                      riskBadge = 'badge badge-danger';
                    } else {
                      riskBadge = 'badge';
                    }

                    const formattedDate = row.DATE_CREATION && row.DATE_CREATION.includes('T') 
                      ? row.DATE_CREATION.split('T')[0] 
                      : row.DATE_CREATION;

                    return (
                      <tr key={row.NUMERODOSSIERTPS} onClick={() => onFileClick(row)} style={{ cursor: 'pointer' }}>
                        <td><strong>{row.NUMERODOSSIERTPS}</strong></td>
                        <td>{row.TYPE_OPERATION}</td>
                        <td>{formattedDate}</td>
                        <td>{row.STATUT_DOSSIER}</td>
                        <td><span style={{ fontWeight: 600 }}>{row.MODE_TRANSPORT}</span></td>
                        <td>{row.NOM_IMPORTATEUR}</td>
                        <td>{row.REGIME_DOUANIER || 'N/A'}</td>
                        <td>
                          <span style={{ fontWeight: 'bold', color: row.RISK_SCORE === 'NON AUTORISÉ' ? '#ef4444' : '#38bdf8' }}>
                            {row.RISK_SCORE}
                          </span>
                        </td>
                        <td>
                          <span className={riskBadge} style={rClass === 'NON AUTORISÉ' ? { background: 'var(--danger-bg)', color: '#ef4444', fontWeight: 'bold' } : {}}>
                            {rClass || 'N/A'}
                          </span>
                        </td>
                        {(role === 'inspecteur' || role === 'admin') && (
                          <td>
                            {row.IS_MARKED ? (
                              <span className="badge" style={{ background: 'var(--danger-bg)', color: '#ef4444', fontWeight: 'bold', padding: '5px 10px' }}>
                                Ciblé
                              </span>
                            ) : (
                              <button 
                                className="login-btn" 
                                onClick={(e) => { e.stopPropagation(); onTargetFile(row.NUMERODOSSIERTPS); }} 
                                style={{ padding: '4px 8px', fontSize: '0.75rem', margin: 0, background: '#dc2626', borderRadius: '4px' }}
                              >
                                Cibler
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      No files found or access error.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Statistician Export Card */}
      {(role === 'statisticien' || role === 'admin') && (
        <div className="dashboard-row" style={{ marginTop: '10px' }}>
          <div className="chart-card full-width-card">
            <div className="chart-card-title">Extracteur de Données Anonymisées pour la Recherche</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '15px', marginTop: '-10px' }}>
              Générez et téléchargez un fichier de données transactionnelles anonymisées (noms commerciaux et codes PPM masqués) selon vos critères de recherche.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '15px' }}>
              <div className="login-input-group">
                <label>Mode de Transport</label>
                <select 
                  value={exportTransport} 
                  onChange={(e) => setExportTransport(e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                >
                  <option value="">Tous</option>
                  <option value="Mer">Mer (Maritime)</option>
                  <option value="Air">Aérien (Air)</option>
                  <option value="Route">Routier (Terrestre)</option>
                </select>
              </div>
              <div className="login-input-group">
                <label>Pays de Provenance</label>
                <input 
                  type="text" 
                  value={exportCountry} 
                  onChange={(e) => setExportCountry(e.target.value)}
                  placeholder="Ex: FRANCE, CHINE..." 
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                />
              </div>
              <div className="login-input-group">
                <label>Type d\'Opération</label>
                <select 
                  value={exportTypeOperation} 
                  onChange={(e) => setExportTypeOperation(e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                >
                  <option value="">Tous</option>
                  <option value="Import">Import</option>
                  <option value="Export">Export</option>
                </select>
              </div>
              <div className="login-input-group">
                <label>Régime Douanier</label>
                <input 
                  type="text" 
                  value={exportRegimeDouanier} 
                  onChange={(e) => setExportRegimeDouanier(e.target.value)}
                  placeholder="Ex: C100, S500..." 
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                />
              </div>
              <div className="login-input-group">
                <label>Statut Dossier</label>
                <select 
                  value={exportStatusFile} 
                  onChange={(e) => setExportStatusFile(e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                >
                  <option value="">All</option>
                  <option value="En cours">En cours</option>
                  <option value="Validé">Validé</option>
                  <option value="Initié">Initié</option>
                </select>
              </div>
              <div className="login-input-group">
                <label>Année de Création</label>
                <select 
                  value={exportAnnee} 
                  onChange={(e) => setExportAnnee(e.target.value)}
                  style={{ padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontFamily: 'inherit', background: 'var(--card-bg)', color: 'var(--text-main)', width: '100%' }}
                >
                  <option value="">Toutes les années</option>
                  {(filterOptions?.years || ["2020", "2021", "2022"]).map(y => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
              <button className="login-btn" onClick={generateAnonymizedExport} disabled={exportLoading} style={{ padding: '10px 24px' }}>
                {exportLoading ? 'Génération...' : 'Générer l\'export CSV'}
              </button>
            </div>
            {exportResult && (
              <div style={{ display: 'block', marginTop: '15px', padding: '15px', borderRadius: '8px', background: 'var(--success-bg)', color: '#a7f3d0', fontSize: '0.9rem', fontWeight: 600, textAlign: 'center', border: '1px solid rgba(109, 181, 26, 0.25)' }}>
                Export prêt ! <a href="#" onClick={handleDownloadCSV} style={{ color: '#34d399', textDecoration: 'underline', marginLeft: '10px' }}>Télécharger le fichier CSV</a>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
