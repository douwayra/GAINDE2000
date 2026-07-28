# 🚀 Plan d'Anticipation Technique — Infinity Sentinel (IPMD V2)
**Projet** : Port Autonome de Dakar (PAD) x Guichet Unique GAINDE 2000  
**Auteur** : Yahya Elimane KANE — Data Science Lead  
**Date** : 28 Juillet 2026  

---

## 1. 🎯 Objectif du Plan d'Anticipation

En attendant la livraison des flux de données réels du Port Autonome de Dakar (IPMD), ce document formalise **l'ensemble des algorithmes, schémas de BDD et pipelines de traitement** préparés à l'avance. 

Dès réception des fichiers CSV / BDD du Port par Modou et Moustapha SECK, **le déploiement sera instantané et sans aucun délai d'adaptation**.

---

## 2. 🛠️ Les 4 Travaux Préparés & Disponibles

### A. Algorithme de Cross-Matching Douane x Port (`scripts/cross_match_gainde_pad.py`)
- **Principe** : Rapprochement automatique entre les déclarations douanières (GAINDE 2000) et les manifests portuaires (PAD) sur la clé pivot `NUMERO_MANIFESTE` + `NUMERO_BL`.
- **Règles de détection d'anomalies** :
  1. *Écart de format conteneur* : Détection des déclarations 20ft en Douane vs 40ft High Cube manifestés au Port.
  2. *Sous-déclaration de tonnage* : Alerte automatique en cas d'écart > 15% entre la déclaration de poids net douanière et la pesée portuaire.
  3. *Calcul d'évasion fiscale présumée* en Franc CFA.
- **Fichier de sortie** : `data/static/cross_matching_results.json`.

### B. Modèle ML Prédictif de Congestion Portuaire (`scripts/predict_congestion.py`)
- **Principe** : Modèle de régression XGBoost prédisant le temps de séjour d'un navire à quai (*Dwell Time*) et calculant le risque de surstaries au Môle 8 (Terminal à Conteneurs).
- **Features d'entrée** : Pavillon, TEU 20ft, FEU 40ft, type de navire, mois/saison.
- **Fichier de sortie** : `data/static/congestion_predictions.json`.

### C. Référentiel des SLAs & Délais Réglementaires
- Suivi des durées moyennes d'exécution par formalité :
  - **BAE / APE Douane** : Seuil réglementaire 24h / Objectif managérial 12h.
  - **BAD Compagnie** : Seuil réglementaire 48h / Objectif managérial 24h.
  - **DO Consignataire** : Seuil réglementaire 24h / Objectif managérial 8h.
  - **VISA PAD** : Seuil réglementaire 12h / Objectif managérial 4h.
  - **Quitus de Sortie** : Seuil réglementaire 12h / Objectif managérial 3h.

### D. Matrice de Mapping des Données
- Le dictionnaire de jointure des champs Douane (GAINDE) ↔ Port (IPMD) est configuré et prêt pour l'ETL.

---

## 3. 🏁 Procédure de Mise en Production lors de la Réception des Données

1. Placer le dump CSV ou l'accès BDD direct du Port dans `data/csv/` ou la variable `.env`.
2. Exécuter le script de croisement :  
   `python scripts/cross_match_gainde_pad.py`
3. Exécuter le modèle prédictif :  
   `python scripts/predict_congestion.py`
4. Lancer le tableau de bord pour visualiser immédiatement les résultats.

---

*Document préparé par Yahya Elimane KANE pour le Groupe GAINDE 2000*
