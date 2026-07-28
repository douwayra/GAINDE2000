import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { formatCFA, formatWeight } from '../utils/api';
import { getStandardCountryName, countryCoords } from '../utils/mapUtils';
import AnimatedCounter from './AnimatedCounter';

export default function ExportsTab({ data, theme }) {
  const worldMapRef = useRef(null);
  const geoRef = useRef(null);
  const evolutionRef = useRef(null);
  const topGoodsRef = useRef(null);
  const transportRef = useRef(null);

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

  useEffect(() => {
    if (!data?.exports_data) return;
    const expData = data.exports_data;

    // 1. World Map
    if (worldMapRef.current && expData.geography?.country_stats) {
      let mapChart = chartInstances.current.worldMap;
      if (!mapChart) {
        mapChart = echarts.init(worldMapRef.current);
        chartInstances.current.worldMap = mapChart;
      }

      const getMapOption = (countryStats) => {
        const mapData = (countryStats || []).map(c => {
          const stdName = getStandardCountryName(c.country);
          return {
            name: stdName,
            originalName: c.country,
            value: c.valeur,
            count: c.count
          };
        }).filter(c => c.name);

        const linesData = [];
        const senegalCoords = countryCoords['Senegal'] || [-14.45, 14.49];
        
        mapData.forEach(c => {
          const cCoords = countryCoords[c.name];
          if (cCoords && c.value > 0 && c.name !== 'Senegal') {
            linesData.push({
              coords: [senegalCoords, cCoords],
              value: c.value,
              name: c.originalName || c.name
            });
          }
        });

        const maxVal = mapData.length > 0 ? Math.max(...mapData.map(c => c.value)) : 40000000000;
        const colorGradient = isDark ? ['#065f46', '#10b981', '#34d399', '#4ade80', '#a7f3d0'] : ['#f0fdf4', '#86efac', '#22c55e', '#166534'];

        return {
          title: {
            show: false,
            text: "Destination of Customs Exports from Senegal",
            left: 'center',
            textStyle: { fontSize: 13, color: isDark ? '#f1f5f9' : '#0f172a', fontFamily: 'Outfit', fontWeight: 600 }
          },
          tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(9, 14, 30, 0.95)',
            borderColor: isDark ? 'rgba(6, 182, 212, 0.3)' : 'rgba(15, 23, 42, 0.15)',
            borderWidth: 1,
            textStyle: { color: isDark ? '#f1f5f9' : '#0f172a', fontFamily: 'Outfit', fontSize: 12 },
            formatter: function (params) {
              if (params.seriesType === 'map' || params.componentSubType === 'map') {
                if (params.data && params.data.value) {
                  const origName = params.data.originalName || params.name;
                  return `<div style="padding:4px 8px;">
                            <b style="font-size:13px; color: ${isDark ? '#22c55e' : '#16a34a'}">${origName}</b><br/>
                            <span style="color:${isDark ? '#94a3b8' : '#64748b'}">Destination :</span> <b>${formatCFA(params.data.value)}</b><br/>
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
                borderColor: isDark ? '#22c55e' : '#16a34a',
                borderWidth: 1.2
              },
              label: { show: false }
            }
          },
          series: [
            {
              name: "Exports (CFA)",
              type: 'map',
              geoIndex: 0,
              data: mapData
            },
            {
              name: 'Routes Commerciales',
              type: 'lines',
              coordinateSystem: 'geo',
              zlevel: 2,
              effect: {
                show: true,
                period: 5,
                trailLength: 0.4,
                color: '#22c55e',
                symbol: 'circle',
                symbolSize: 3.5
              },
              lineStyle: {
                color: 'rgba(34, 197, 94, 0.25)',
                width: 1.2,
                curveness: 0.25
              },
              data: linesData
            }
          ]
        };
      };

      fetch('/world.json')
        .then(res => res.json())
        .then(worldJson => {
          echarts.registerMap('world', worldJson);
          mapChart.setOption(getMapOption(expData.geography.country_stats));
          setTimeout(() => {
            if (mapChart) mapChart.resize();
          }, 50);
        })
        .catch(err => {
          console.warn("Impossible de charger la carte du monde en local, tentative CDN...");
          fetch('https://fastly.jsdelivr.net/npm/echarts@4.9.0/map/json/world.json')
            .then(res => res.json())
            .then(worldJson => {
              echarts.registerMap('world', worldJson);
              mapChart.setOption(getMapOption(expData.geography.country_stats));
              setTimeout(() => {
                if (mapChart) mapChart.resize();
              }, 50);
            })
            .catch(cdnErr => {
              console.error("Map load failed", cdnErr);
              if (worldMapRef.current) {
                worldMapRef.current.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted);">Carte non disponible</div>';
              }
            });
        });
    }

    // 2. Region Pie
    if (geoRef.current && expData.geography?.region_val_split) {
      let geoChart = chartInstances.current.geo;
      if (!geoChart) {
        geoChart = echarts.init(geoRef.current);
        chartInstances.current.geo = geoChart;
      }
      const geoData = Object.entries(expData.geography.region_val_split).map(([k, v]) => ({ name: k, value: v }));
        geoChart.setOption({
          tooltip: { 
            trigger: 'item', 
            backgroundColor: isDark ? '#0f172a' : '#ffffff',
            borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
            textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
            formatter: params => `${params.name}: ${formatCFA(params.value)} (${params.percent}%)` 
          },
          legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
          color: ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4'],
        series: [{
          name: "Export Regions",
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 0, borderWidth: 0 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', color: '#ffffff' } },
          data: geoData
        }]
      });
    }

    // 3. Evolution Line
    if (evolutionRef.current && expData.time_decomposition?.month) {
      let evChart = chartInstances.current.evolution;
      if (!evChart) {
        evChart = echarts.init(evolutionRef.current);
        chartInstances.current.evolution = evChart;
      }
      const timeKeys = Object.keys(expData.time_decomposition.month);
      const timeVals = Object.values(expData.time_decomposition.month);
      evChart.setOption({
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
          lineStyle: { width: 3, color: '#6db51a' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(109, 181, 26, 0.4)' },
              { offset: 1, color: 'rgba(109, 181, 26, 0.01)' }
            ])
          }
        }]
      });
    }

    // 4. Top Goods Bar
    if (topGoodsRef.current && expData.top_products) {
      let goodsChart = chartInstances.current.topGoods;
      if (!goodsChart) {
        goodsChart = echarts.init(topGoodsRef.current);
        chartInstances.current.topGoods = goodsChart;
      }
      const goodsData = expData.top_products.slice(0, 10);
      goodsChart.setOption({
        grid: { left: '3%', right: '12%', bottom: '3%', containLabel: true },
        tooltip: { 
          trigger: 'axis', 
          axisPointer: { type: 'shadow' },
          backgroundColor: isDark ? '#0f172a' : '#ffffff',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
          textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' },
          formatter: function(params) {
            const idx = params[0].dataIndex;
            const originalItem = goodsData[goodsData.length - 1 - idx];
            return `<b>${originalItem.DESIGNATION}</b><br/>Code SH : ${originalItem.NUMEROTARIFDOUANE}<br/>Value : ${formatCFA(originalItem.VALEURCFA)}`;
          }
        },
        xAxis: { type: 'value', name: "Value", ...axisOptions },
        yAxis: { type: 'category', data: goodsData.map(d => d.DESIGNATION.slice(0, 18) + '...').reverse(), ...axisOptions },
        series: [{
          type: 'bar',
          data: goodsData.map(d => d.VALEURCFA).reverse(),
          itemStyle: { color: '#6db51a', borderRadius: [0, 5, 5, 0] }
        }]
      });
    }

    // 5. Transport Pie
    if (transportRef.current && expData.logistics?.mode_split) {
      let transChart = chartInstances.current.transport;
      if (!transChart) {
        transChart = echarts.init(transportRef.current);
        chartInstances.current.transport = transChart;
      }
      const transData = Object.entries(expData.logistics.mode_split).map(([k, v]) => ({ name: k, value: v }));
      transChart.setOption({
        tooltip: { 
          trigger: 'item',
          backgroundColor: isDark ? '#0f172a' : '#ffffff',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15, 23, 42, 0.08)',
          textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontFamily: 'Outfit' }
        },
        legend: { bottom: '0%', textStyle: { color: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'Outfit' } },
        color: ['#10b981', '#3b82f6', '#f59e0b'],
        series: [{
          name: 'Transport Export',
          type: 'pie',
          radius: ['30%', '60%'],
          itemStyle: { borderRadius: 0, borderWidth: 0 },
          data: transData
        }]
      });
    }

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

  if (!data?.exports_data) return <div style={{ textAlign: 'center', padding: '50px' }}><div className="loader"></div></div>;

  const exp = data.exports_data;

  return (
    <>
      <div className="kpis-grid">
        {/* Card 1: Files d'Exportation */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            </div>
            <span className="kpi-title">Dossiers d'Exportation</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value">
                <AnimatedCounter value={exp.kpis.total_dossiers} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +2,4%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="12" width="5" height="18" rx="2.5" fill="var(--primary)" />
                <rect x="12" y="8" width="5" height="22" rx="2.5" fill="var(--primary)" />
                <rect x="24" y="15" width="5" height="15" rx="2.5" fill="var(--primary)" />
                <rect x="36" y="5" width="5" height="25" rx="2.5" fill="var(--primary)" />
                <rect x="48" y="10" width="5" height="20" rx="2.5" fill="var(--primary)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 2: Value Exportée CFA */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper cyan">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
            <span className="kpi-title">Valeur Exportée CFA</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#0ea5e9' }}>
                <AnimatedCounter value={exp.kpis.total_val_cfa} formatter={formatCFA} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +3,8%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,20 Q15,4 30,15 T60,2" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,20 Q15,4 30,15 T60,2 L60,30 L0,30 Z" fill="rgba(14, 165, 233, 0.06)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 3: Total Exported Weight */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper orange">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 7H2M12 2v20M5 7l2 10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l2-10"/></svg>
            </div>
            <span className="kpi-title">Poids Total Exporté</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value" style={{ color: '#f97316' }}>
                <AnimatedCounter value={exp.kpis.total_poids_net} formatter={formatWeight} />
              </span>
              <span className="kpi-trend up">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="18 15 12 9 6 15"/></svg>
                +0,9%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <path d="M0,15 Q15,8 30,18 T60,10" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" />
                <path d="M0,15 Q15,8 30,18 T60,10 L60,30 L0,30 Z" fill="rgba(249, 115, 22, 0.06)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 4: Medium par Exportation */}
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-icon-wrapper purple">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83M22 12A10 10 0 0 0 12 2v10z"/></svg>
            </div>
            <span className="kpi-title">Medium par Exportation</span>
          </div>
          <div className="kpi-body">
            <div className="kpi-info-col">
              <span className="kpi-value">
                <AnimatedCounter value={exp.kpis.avg_val_dossier} formatter={formatCFA} />
              </span>
              <span className="kpi-trend down">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="6 9 12 15 18 9"/></svg>
                -1,2%
              </span>
            </div>
            <div className="kpi-sparkline">
              <svg width="60" height="30" viewBox="0 0 60 30" style={{ overflow: 'visible' }}>
                <rect x="0" y="15" width="5" height="15" rx="2.5" fill="#8b5cf6" />
                <rect x="12" y="10" width="5" height="20" rx="2.5" fill="#8b5cf6" />
                <rect x="24" y="6" width="5" height="24" rx="2.5" fill="#8b5cf6" />
                <rect x="36" y="12" width="5" height="18" rx="2.5" fill="#8b5cf6" />
                <rect x="48" y="4" width="5" height="26" rx="2.5" fill="#8b5cf6" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-row full-width">
        <div className="chart-card">
          <div className="chart-card-title">Destination Géographique des Exportations (Carte du Monde)</div>
          <div ref={worldMapRef} style={{ height: '500px', width: '100%' }}></div>
        </div>
      </div>

      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Échanges Export par Zone Économique</div>
          <div ref={geoRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Évolution Mensuelle des Exports</div>
          <div ref={evolutionRef} className="chart-container"></div>
        </div>
      </div>

      <div className="dashboard-row">
        <div className="chart-card">
          <div className="chart-card-title">Top 10 Marchandises les Plus Exportées (Valeur CFA)</div>
          <div ref={topGoodsRef} className="chart-container"></div>
        </div>
        <div className="chart-card">
          <div className="chart-card-title">Logistique Export par Transport Mode</div>
          <div ref={transportRef} className="chart-container"></div>
        </div>
      </div>
    </>
  );
}
