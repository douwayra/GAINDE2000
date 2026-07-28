# 🎓 RAPPORT DE CLÔTURE DE STAGE & TRANSMISSION DE PROJET
## Plateformes Orbus Sentinel & Infinity Sentinel-2 (IPMD V2)

**Stagiaire Data Science & Analytics** : Yahya Elimane KANE  
**Organisme d'accueil** : Groupe GAINDE 2000 / Orbus Infinity  
**Superviseurs & Destinataires** : M. Moustapha SECK, Modou & Équipe Technique  
**Période du projet** : 2024 - 2026  
**Date de transmission** : 28 Juillet 2026  

---

## 1. 📑 Synthèse Exécutive du Stage

Durant ce stage au sein du groupe **GAINDE 2000**, la mission a porté sur la conception, le développement et le déploiement de **deux plateformes analytiques majeures** d'aide à la décision et de supervision pour le commerce extérieur du Sénégal :

1. **Orbus Sentinel** : Cockpit de supervision douanière (GAINDE 2000), détection de fraudes et de sous-évaluation fiscale par Machine Learning (*Isolation Forest, Z-Score*), scoring de risque 0-100, et assistant IA conversationnel en langage naturel (SQL-NL).
2. **Infinity Sentinel-2 (Évolution IPMD V2)** : Plateforme de supervision des formalités logistiques et maritimes du Port Autonome de Dakar (PAD), suivi des navires en temps réel (*Liveview AIS*), scoring de performance des consignataires/manutentionnaires et algorithmes de cross-matching Douane x Port.

---

## 2. 🚀 Bilan des Livrables Produits

### A. Code Source & Applications
- **Backend API REST (Python / FastAPI / Uvicorn)** : `app.py` (2 400+ lignes de code), 27+ endpoints sécurisés par JWT et RBAC 7 rôles, journalisation des audits ISO8601, rate-limiting et gestion d'erreurs.
- **Frontend SPA Moderne (React 19 / Vite 6 / ECharts)** : Interface bimodal (Theme Clair/Sombre), 10 onglets de visualisation, carte interactive mondiale avec animations géodésiques, timeline de dossiers, filtres croisés et exportations.
- **Suite IPMD V1 & Sentinel-2 (`IpmdSuiteTab.jsx`)** : Reprise intégrale des 9 dashboards du Port de Dakar (Formalités, Navires, AIS, Acteurs, SLAs) et module IA de croisement.
- **Générateur de Rapports PDF (`pdf_generator.py`)** : Module ReportLab (1 122 lignes) générant 4 types de rapports officiels institutionnels avec graphiques et logo Orbus Sentinel.

### B. Modèles de Machine Learning & Données
- `data/models/iforest_model.pkl` : Modèle Isolation Forest d'isolation des anomalies fiscales multidimensionnelles.
- `data/models/kmeans_model.pkl` & `scaler_kmeans.pkl` : Segmentation des importateurs en 4 clusters comportementaux.
- `data/db/gainde_douane.db` (DuckDB) & `data/db/users.db` (SQLite) : Bases analytiques et d'authentification.
- `data/static/ipmd_data.json` & `dashboard_data.json` : Caches de données haute performance.

---

## 3. 📂 Structuration Modulaire du Projet

Le projet a été découpé de manière modulaire et propre pour faciliter la maintenance future par l'équipe :

```
GAINDE2000/
│
├── 🔵 frontend/src/components/orbus_sentinel/   <-- MODULE DOUANES (GAINDE 2000)
│   ├── DashboardTab.jsx      (Vue Globale & Carte Interactive Mondiale)
│   ├── ImportsTab.jsx        (Analyses Importations)
│   ├── ExportsTab.jsx        (Analyses Exportations)
│   ├── RisksTab.jsx          (Score de Risque Douanier & Fraud AI)
│   ├── LogisticsTab.jsx      (Segmentation K-Means & Corridors)
│   ├── BusinessTab.jsx       (Prospection Commerciale)
│   ├── FinanceTab.jsx        (Finances & Alertes Budget)
│   ├── CybersecurityTab.jsx  (Audit IT & Intrusions)
│   └── AdminUsersTab.jsx     (Gestion des Comptes Utilisateurs)
│
├── 🟢 frontend/src/components/infinity_sentinel/ <-- MODULE PORT (PAD & IPMD V2)
│   └── IpmdSuiteTab.jsx      (Formalités BAE/BAD/DO/VISA/Quitus, AIS Liveview, SLAs)
│
├── 🔵 scripts/orbus_sentinel/                    <-- SCRIPTS ML & ETL DOUANES
│   ├── etl_pipeline.py
│   ├── etl_pipeline_duckdb.py
│   └── run_advanced_analysis.py
│
├── 🟢 scripts/infinity_sentinel/                 <-- SCRIPTS INGESTION PORT
│   └── generate_ipmd_data.py
│
├── app.py                                       <-- Serveur Backend FastAPI principal
├── pdf_generator.py                             <-- Générateur de rapports PDF
└── fiche_deploiement_preprod.md                 <-- Fiche d'infrastructure pour l'équipe Infra
```

---

## 4. 🛠️ Guide Démarrage et Maintenance Rapide

### A. Démarrage du Backend (FastAPI)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\uvicorn.exe app:app --host 127.0.0.1 --port 8000 --reload
```

### B. Démarrage du Frontend (React / Vite)
```powershell
cd frontend
npm run dev
# Application accessible sur http://localhost:5173/
```

### C. Comptes de Test & Rôles
- **Administrateur** : `admin` / `adminpassword`
- **Direction Générale** : `direction` / `directionpassword`
- **Inspecteur Douane** : `inspecteur_dkp` / `inspecteurpassword`
- **Transitaire** : `transitaire_cargolink` / `transitairepassword`

---

## 5. 🤝 Procédure de Réception pour l'Équipe Successeure

1. **Intégration des Données IPMD Réelles** :
   À la livraison des tables du Port par l'équipe IPMD, exécuter le script de jointure sur les clés pivots `NUMEROMANIFESTE` + `NUMERO_BL`.
2. **Changement des Clés de Sécurité** :
   Modifier la variable `SECRET_KEY` dans le fichier `.env` sur le serveur de production.
3. **Build de Production Frontend** :
   Exécuter `npm run build` dans le dossier `frontend/` pour générer le dossier `dist/` qui sera servi par NGINX.

---

*Transmission effectuée par Yahya Elimane KANE à l'équipe GAINDE 2000 — 28 Juillet 2026*
