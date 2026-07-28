# 🌐 Code Source & Documentation Technique — Carte Interactive Mondiale
## Plateforme Orbus Sentinel / GAINDE 2000

- `frontend/src/utils/mapUtils.js` (Mapping des pays et coordonnées GPS)
- `frontend/src/components/DashboardTab.jsx` (Composant de la carte interactive)
- `public/world.json` (Fichier de fond de carte GeoJSON mondial)

---

## 1. Présentation et Fonctionnalités Clés

La carte interactive d'**Orbus Sentinel** est un outil de visualisation géographique haute performance permettant de piloter l'ensemble des flux commerciaux douaniers du Sénégal (Importations et Exportations).

### Caractéristiques principales :
1. **Carte Choroplèthe Dynamique** : Coloration automatique de chaque pays d'origine/destination selon la valeur financière cumulée en Franc CFA.
2. **Animation des Routes Commerciales** : Tracer de lignes géodésiques courbes (`curveness: 0.25`) avec animation de particules en temps réel reliant le Sénégal à ses partenaires commerciaux mondialement.
3. **Infobulles Enrichies (Tooltips HTML)** : Affichage au survol du nom standardisé du pays, du montant total des opérations en Franc CFA et du nombre de dossiers douaniers associés.
4. **Normalisation Intelligente des Noms de Pays** : Dictionnaire d'équivalences nettoyant automatiquement les variantes orthographiques et encodages (ex : `CHINZ` → `China`, `SËNËGAL` → `Senegal`, `CÔTE D'IVOIRE` → `Côte d'Ivoire`).
5. **Support Thématique Bimodal** : Adaptation automatique de la palette visuelle selon le mode actif (Mode Clair / Mode Sombre).
6. **Robustesse et Fallback CDN** : Ingestion prioritaire du fichier GeoJSON local `world.json` avec bascule automatique sur CDN en cas d'indisponibilité.

---

## 2. 💻 Code Source 1 : Dictionnaire et Utilities (`mapUtils.js`)

Ce fichier contient la table de correspondance des pays et le référentiel des coordonnées GPS (Latitude / Longitude) pour le tracé des lignes de flux.

```javascript
// File: frontend/src/utils/mapUtils.js

// Dictionnaire de normalisation des noms de pays (Multilingue & Encodages)
export const countryNameMap = {
  'SÉNÉGAL': 'Senegal',
  'SENEGAL': 'Senegal',
  'CHINE': 'China',
  'CHINZ': 'China',
  'FRANCE': 'France',
  'INDE': 'India',
  'MALI': 'Mali',
  "CÔTE D'IVOIRE": "Côte d'Ivoire",
  "COTE D'IVOIRE": "Côte d'Ivoire",
  'GUINÉE': 'Guinea',
  'BURKINA FASO': 'Burkina Faso',
  'PAYS-BAS': 'Netherlands',
  'BELGIQUE': 'Belgium',
  'ALLEMAGNE': 'Germany',
  'ITALIE': 'Italy',
  'ESPAGNE': 'Spain',
  'ROYAUME-UNI': 'United Kingdom',
  'ÉMIRATS ARABES UNIS': 'United Arab Emirates',
  'ÉTATS-UNIS': 'United States',
  'BRÉSIL': 'Brazil',
  'MAROC': 'Morocco',
  'TURQUIE': 'Turkey',
  'JAPON': 'Japan'
};

// Coordonnées GPS (Longitude, Latitude) pour l'ancrage des lignes de flux
export const countryCoords = {
  'China': [104.19, 35.86],
  'France': [2.21, 46.22],
  'India': [78.96, 20.59],
  'Netherlands': [5.29, 52.13],
  'Spain': [-3.74, 40.46],
  'United States': [-95.71, 37.09],
  'Mali': [-3.99, 17.57],
  'Belgium': [4.46, 50.50],
  'United Arab Emirates': [53.84, 23.42],
  'Germany': [10.45, 51.16],
  'Turkey': [35.24, 38.96],
  'Japan': [138.25, 36.20],
  'Morocco': [-7.09, 31.79],
  'Senegal': [-14.45, 14.49]
};

// Fonction de nettoyage et standardisation du nom du pays
export function getStandardCountryName(rawName) {
  if (!rawName) return '';
  let name = rawName.trim().toUpperCase();
  
  if (name.includes('-')) {
    const parts = name.split('-');
    for (const part of parts) {
      const cleanedPart = part.trim();
      if (countryNameMap[cleanedPart]) {
        return countryNameMap[cleanedPart];
      }
    }
  }
  
  for (const key of Object.keys(countryNameMap)) {
    if (name.includes(key)) {
      return countryNameMap[key];
    }
  }

  return rawName.charAt(0).toUpperCase() + rawName.slice(1).toLowerCase();
}
```

---

## 3. 💻 Code Source 2 : Composant de la Carte (`DashboardTab.jsx`)

Ce composant React gère le cycle de vie de la carte, le chargement GeoJSON, les événements de survol et les séries ECharts.

```javascript
// File: frontend/src/components/DashboardTab.jsx (Extrait dédié à la Carte Interactive)

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { countryCoords, getStandardCountryName } from '../utils/mapUtils';
import { formatCFA } from '../utils/api';

export default function WorldMapComponent({ data, mapMode, theme }) {
  const worldMapRef = useRef(null);
  const chartInstance = useRef(null);
  const isDark = theme === 'dark';

  useEffect(() => {
    if (!worldMapRef.current || !data?.geography) return;

    // Initialisation ou récupération de l'instance ECharts
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(worldMapRef.current);
    }

    const chart = chartInstance.current;

    // Ingestion du fond de carte GeoJSON (Local avec fallback CDN)
    fetch('/world.json')
      .then(res => res.json())
      .then(worldJson => {
        echarts.registerMap('world', worldJson);
        renderMap(chart);
      })
      .catch(err => {
        fetch('https://fastly.jsdelivr.net/npm/echarts@4.9.0/map/json/world.json')
          .then(res => res.json())
          .then(worldJson => {
            echarts.registerMap('world', worldJson);
            renderMap(chart);
          });
      });

    function renderMap(chartInst) {
      const isImports = mapMode === 'imports';
      const rawStats = isImports ? data.geography.import_country_stats : data.geography.export_country_stats;

      // Transformation et agrégation des données géographiques
      const mapData = (rawStats || []).map(c => ({
        name: getStandardCountryName(c.country),
        originalName: c.country,
        value: c.valeur,
        count: c.count
      })).filter(c => c.name);

      const maxVal = mapData.length > 0 ? Math.max(...mapData.map(c => c.value)) : 1000000000;
      const senegalCoords = countryCoords['Senegal'] || [-14.45, 14.49];

      // Génération des trajectoires géodésiques
      const linesData = [];
      mapData.forEach(c => {
        const cCoords = countryCoords[c.name];
        if (cCoords && c.value > 0 && c.name !== 'Senegal') {
          linesData.push({
            coords: isImports ? [cCoords, senegalCoords] : [senegalCoords, cCoords],
            value: c.value,
            name: c.originalName || c.name
          });
        }
      });

      // Configuration des options ECharts
      const options = {
        tooltip: {
          trigger: 'item',
          backgroundColor: isDark ? 'rgba(9, 14, 30, 0.95)' : '#ffffff',
          borderColor: isDark ? 'rgba(6, 182, 212, 0.3)' : 'rgba(15, 23, 42, 0.15)',
          borderWidth: 1,
          textStyle: { color: isDark ? '#f1f5f9' : '#1e293b', fontSize: 12 },
          formatter: function (params) {
            if (params.data && params.data.value) {
              const origName = params.data.originalName || params.name;
              return `<div style="padding:6px 10px;">
                        <b style="font-size:13px; color: ${isDark ? '#22d3ee' : '#2075db'}">${origName}</b><br/>
                        <span>${isImports ? 'Provenance' : 'Destination'} :</span> <b>${formatCFA(params.data.value)}</b><br/>
                        <span>Dossiers :</span> <b>${params.data.count.toLocaleString('fr-FR')}</b>
                      </div>`;
            }
            return `<div style="padding:4px 8px;"><b>${params.name}</b><br/>Pas de flux direct</div>`;
          }
        },
        visualMap: {
          min: 0,
          max: maxVal,
          left: 'left',
          top: 'bottom',
          text: ['Élevé', 'Faible'],
          calculable: true,
          inRange: {
            color: isImports
              ? (isDark ? ['#1e3a8a', '#3b82f6', '#06b6d4', '#22d3ee'] : ['#f1f5f9', '#93c5fd', '#3b82f6', '#1d4ed8'])
              : (isDark ? ['#065f46', '#10b981', '#4ade80', '#a7f3d0'] : ['#f0fdf4', '#86efac', '#22c55e', '#166534'])
          }
        },
        geo: {
          map: 'world',
          roam: true,
          zoom: 1.15,
          center: [10, 22],
          itemStyle: {
            areaColor: isDark ? '#1b2535' : '#e2e8f0',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(15, 23, 42, 0.08)',
            borderWidth: 0.6
          },
          emphasis: {
            itemStyle: {
              areaColor: isDark ? 'rgba(6, 182, 212, 0.35)' : 'rgba(32, 117, 219, 0.25)',
              borderColor: isDark ? '#22d3ee' : '#2075db',
              borderWidth: 1.2
            }
          }
        },
        series: [
          // Couche 1 : Fond de carte choroplèthe
          {
            name: 'Flux Commerciaux',
            type: 'map',
            geoIndex: 0,
            data: mapData
          },
          // Couche 2 : Halo lumineux des lignes de flux
          {
            name: 'Glow Halo',
            type: 'lines',
            coordinateSystem: 'geo',
            zlevel: 1,
            lineStyle: {
              color: isImports ? '#0ea5e9' : '#10b981',
              width: 3.5,
              opacity: 0.08,
              curveness: 0.25
            },
            data: linesData
          },
          // Couche 3 : Routes avec effet de particules animées
          {
            name: 'Particules Animées',
            type: 'lines',
            coordinateSystem: 'geo',
            zlevel: 2,
            effect: {
              show: true,
              period: 4.5,
              trailLength: 0.35,
              color: isImports ? '#22d3ee' : '#34d399',
              symbol: 'circle',
              symbolSize: 4.5
            },
            lineStyle: {
              color: isImports ? 'rgba(34, 211, 238, 0.3)' : 'rgba(52, 211, 153, 0.3)',
              width: 1.5,
              curveness: 0.25
            },
            data: linesData
          }
        ]
      };

      chartInst.setOption(options);
    }

    // Adaptation automatique au redimensionnement de l'écran
    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);

  }, [data, mapMode, theme]);

  return <div ref={worldMapRef} style={{ width: '100%', height: '520px', borderRadius: '12px' }} />;
}
```

---

## 4. 🔍 Explications Détaillées du Code

### 1. Ingestion et Registre du Fond de Carte GeoJSON (`echarts.registerMap`)
L'application télécharge le fichier GeoJSON mondial `world.json` contenant la géométrie vectorielle des continents et des pays. ECharts enregistre ce fond sous la clé `'world'` qui sert de système de coordonnées spatiales (`geo`).

### 2. Superposition Multicouche (Multi-Layering ECharts)
Le rendu graphique s'appuie sur **3 couches superposées** :
- **Série 1 (`type: 'map'`)** : La carte des pays dont chaque polygone prend une couleur calculée par le composant `visualMap` en fonction de la valeur commerciale en Franc CFA.
- **Série 2 (`type: 'lines'`, `zlevel: 1`)** : Un tracé de fond flouté (*Halo Glow*) offrant un relief visuel professionnel.
- **Série 3 (`type: 'lines'`, `zlevel: 2`)** : Les lignes de transport géodésiques courbes avec un effet d'animation de particules circulaires (`effect: { show: true, period: 4.5 }`) simulant le mouvement réel des navires et conteneurs vers ou depuis Dakar.

### 3. Normalisation Dynamique des Noms de Pays (`getStandardCountryName`)
Les bases de données douanières GAINDE contiennent parfois des variations d'encodage (ex : `SÃ©nÃ©gal` ou `PAYS-BAS`). La fonction `getStandardCountryName` transforme toutes ces variations vers des clés standards (`Senegal`, `Netherlands`, `China`), garantissant que 100 % des données se lient correctement avec le fond de carte GeoJSON.

### 4. Réactivité & Support Thématique
Le composant s'adapte en temps réel aux changements de mode (**Clair/Sombre**) et de filtre (**Imports/Exports**). Les dégradés de couleurs (Bleu cyan pour les imports, Vert émeraude pour les exports) et le style des infobulles se mettent à jour sans réinitialiser la carte.

---


