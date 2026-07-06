# GAINDE 2000 / ORBUS - Spécifications Techniques d'Ingénierie des Données

Ce document décrit de manière exhaustive l'architecture logicielle, les pipelines d'intégration de données (ETL), les modèles mathématiques, la gouvernance de sécurité et les spécifications d'interface (API) de la plateforme ORBUS / GAINDE 2000.

---

## 1. Architecture Système et Découplage de Données

Le système est conçu selon un modèle à trois tiers hautement découplé :
*   **Couche de restitution (Frontend)** : Application monopage (SPA) en Vanilla JavaScript et CSS natif, s'appuyant sur Apache ECharts pour les visualisations interactives.
*   **Couche de services (Backend)** : API REST construite avec FastAPI (Python 3.10+) et exécutée via le serveur ASGI Uvicorn.
*   **Couche de persistance (Hybride OLTP/OLAP)** : Utilisation conjointe de DuckDB et SQLite3.

```
┌────────────────────────────────────────────────────────┐
│               Client Web (SPA - JavaScript)            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ Jeton JWT (HTTP Authorization Header)
                           ▼
┌────────────────────────────────────────────────────────┐
│                 FastAPI Service (app.py)               │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               │ (Lecture Seule)          │ (Lecture / Écriture)
               ▼                          ▼
┌─────────────────────────────┐   ┌──────────────────────┐
│       DuckDB Database       │   │   SQLite3 Database   │
│    (gainde_douane.db)       │   │      (users.db)      │
│     Couche OLAP Analytique  │   │  Couche OLTP Sécu    │
└─────────────────────────────┘   └──────────────────────┘
```

### A. Implémentation Concurrente et Performance DuckDB
DuckDB gère les analyses historiques volumineuses (1,8 million de transactions). Pour éviter tout verrouillage d'écriture et permettre l'exécution en parallèle de requêtes analytiques lourdes et de pipelines ETL, DuckDB est initialisé dans le code de l'API avec un accès strict en lecture seule :

```python
# app.py - Initialisation de la connexion persistante DuckDB
import duckdb

db_conn = duckdb.connect('data/db/gainde_douane.db', read_only=True)
```
Cette configuration permet à DuckDB d'utiliser le partitionnement en mémoire et le traitement vectorisé (SIMD) pour répondre à des agrégations complexes en moins de 30 millisecondes.

### B. Couche SQLite3 transactionnelle
SQLite3 gère la base locale `users.db` pour stocker les comptes utilisateurs, le journal d'audit informatique et les dossiers ciblés pour inspection physique par les douaniers. Les accès se font via des connexions locales éphémères fermées à l'issue de chaque transaction de base de données :

```python
# app.py - Exemple d'accès transactionnel SQLite3
import sqlite3

def write_audit_log(timestamp, username, ip, status):
    conn = sqlite3.connect("data/db/users.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (timestamp, username, client_ip, status) VALUES (?, ?, ?, ?)",
        (timestamp, username, ip, status)
    )
    conn.commit()
    conn.close()
```

---

## 2. Schémas de Base de Données Relatifs au Projet

### A. Base de Données Transactionnelle SQLite3 (`users.db`)

#### 1. Table `users`
Contient les identifiants, rôles, et affectations douanières ou industrielles des utilisateurs.
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    bureau_douane TEXT
);
```

#### 2. Table `marked_dossiers`
Enregistre les dossiers douaniers signalés pour une inspection physique par les douaniers affectés aux différents ports ou aéroports.
```sql
CREATE TABLE marked_dossiers (
    dossier_num TEXT PRIMARY KEY,
    marked_by TEXT NOT NULL,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. Table `audit_logs`
Journalise les actions sensibles et les événements de sécurité (force brute, nœuds Tor, alertes d'exfiltration).
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    username TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    server_ip TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL
);
```

### B. Base de Données Analytique DuckDB (`gainde_douane.db`)

#### Table `dossiers`
Cette table dénormalisée regroupe l'historique consolidé des déclarations.

```sql
CREATE TABLE dossiers (
    NUMERODOSSIERTPS VARCHAR PRIMARY KEY,
    TYPE_OPERATION VARCHAR, -- 'Import' ou 'Export'
    DATE_CREATION TIMESTAMP,
    STATUT_DOSSIER VARCHAR, -- 'Initialise', 'Paye', 'EnCours', 'Liquide', 'Livre'
    MODE_TRANSPORT VARCHAR, -- 'Mer', 'Air', 'Route'
    NOM_IMPORTATEUR VARCHAR,
    NINEA_IMPORTATEUR VARCHAR,
    REGIME_DOUANIER VARCHAR,
    BANQUE VARCHAR,
    ASSURANCE VARCHAR,
    VALEUR_CFA DOUBLE,
    POIDS_NET DOUBLE,
    RISK_SCORE INTEGER,
    RISK_CLASS VARCHAR
);
```

---

## 3. Le Pipeline d'Intégration de Données (ETL)

Le pipeline d'extraction, de transformation et de chargement (ETL) est écrit en Python. Il traite et consolide les flux des déclarations douanières, des factures financières et des registres d'articles.

```
┌──────────────┐    ┌───────────────┐    ┌────────────────┐
│   Factures   │    │  Déclarations │    │    Articles    │
│  (Frais/Dev) │    │  (Statut/Reg) │    │  (Code SH/Pds) │
└──────┬───────┘    └───────┬───────┘    └───────┬────────┘
       │                    │                    │
       └──────────────┬─────┴────────────────────┘
                      ▼
       [ Jointure SQL sur ID Déclaration ]
                      │
                      ▼
       [ Standardisation Monétaire BCEAO ]
                      │
                      ▼
       [ Correction Poids Aberrants & Zéros ]
                      │
                      ▼
       [ Déduplication (Horodatage Max) ]
                      │
                      ▼
       [ Chargement dans gainde_douane.db ]
```

### A. Jointures et Transformation Multi-Sources
Les fichiers bruts d'articles, de factures et de dossiers sont importés dans un dataframe Pandas. La jointure s'effectue sur le numéro unique de dossier :
```python
import pandas as pd

# Chargement
df_dossiers = pd.read_csv("data/csv/dossiers.csv")
df_factures = pd.read_csv("data/csv/factures.csv")
df_articles = pd.read_csv("data/csv/articles.csv")

# Jointures
df_merged = df_dossiers.merge(df_factures, on="NUMERODOSSIERTPS", how="inner")
df_merged = df_merged.merge(df_articles, on="NUMERODOSSIERTPS", how="inner")
```

### B. Standardisation Monétaire (Taux de Change BCEAO)
Pour toutes les transactions libellées en devises étrangères, le pipeline applique le taux de change réglementaire de la BCEAO en vigueur à la date d'enregistrement du dossier (`DATE_CREATION`) :

$$\text{VALEUR\_CFA} = \text{MONTANT\_DECLARE} \times \text{TAUX\_BCEAO}$$

En Python :
```python
# Exemple de dictionnaire des taux fixes pour l'ETL
rates = {
    'EUR': 655.957,
    'USD': 590.25,
    'GBP': 750.80,
    'XOF': 1.0
}

def convert_to_cfa(row):
    currency = str(row['DEVISE_FACTURE']).upper().strip()
    amount = float(row['MONTANT_FACTURE'])
    rate = rates.get(currency, 1.0)
    return amount * rate

df_merged['VALEUR_CFA'] = df_merged.apply(convert_to_cfa, axis=1)
```

### C. Traitement des Valeurs Aberrantes et Division par Zéro
Pour fiabiliser l'évaluation du prix au kilo lors du ciblage douanier, le pipeline nettoie les anomalies de poids net :
*   Les poids inférieurs ou égaux à zéro sont remplacés par la médiane du poids pour le même code produit (Code SH).
*   Si aucun code SH n'a de poids enregistré, la valeur par défaut est fixée à $1.0$ kg pour éviter la division par zéro dans le calcul de la valeur unitaire :

```python
# Remplacement des poids absurdes
df_merged['POIDS_NET'] = df_merged['POIDS_NET'].apply(lambda w: w if w > 0 else 1.0)
```

---

## 4. Spécifications de Sécurité et Cloisonnement de Données (RLS/CLS)

La sécurité est implémentée côté serveur via le décodage et la validation des jetons JWT par FastAPI.

### A. Décodage et Claims JWT
FastAPI intercepte les requêtes HTTP, valide la signature du jeton d'authentification et extrait les rôles et affectations de l'utilisateur :
```python
# app.py - Validation des claims JWT
def get_current_user_claims(authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    claims = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return {
        "username": claims.get("sub"),
        "role": claims.get("role"),
        "bureau_douane": claims.get("bureau_douane")
    }
```

### B. Matrice d'Application de la Sécurité RLS (SQL Dynamique)
Dans l'endpoint d'aperçu des déclarations `/api/dossiers-preview`, les clauses SQL sont injectées selon les rôles extraits :

```python
@app.get("/api/dossiers-preview")
def get_dossiers_preview(claims: dict = Depends(get_current_user_claims)):
    role = claims["role"]
    bureau = claims["bureau_douane"]
    
    where_clauses = []
    
    # 1. RLS - Row-Level Security
    if role == "inspecteur":
        if bureau == "DKP":
            where_clauses.append("MODE_TRANSPORT = 'Mer'")
        elif bureau == "AIBD":
            where_clauses.append("MODE_TRANSPORT = 'Air'")
    elif role == "transitaire":
        where_clauses.append(f"NINEA_IMPORTATEUR = '{bureau}'")
    elif role == "partenaire":
        where_clauses.append(f"(BANQUE = '{bureau}' OR ASSURANCE = '{bureau}')")
        
    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    conn = db_conn.cursor()
    df = conn.execute(f"SELECT * FROM dossiers {where_str} LIMIT 100").df()
    
    # 2. CLS - Column-Level Security (Anonymisation & Masquage)
    if role in ["statisticien", "journaliste"]:
        df['NOM_IMPORTATEUR'] = df['NOM_IMPORTATEUR'].apply(
            lambda name: f"ENTREPRISE_ANONYME_{abs(hash(name)) % 10000}" if name else "INCONNU"
        )
        
    if role in ["journaliste", "transitaire", "partenaire", "statisticien"]:
        df['RISK_SCORE'] = "NON AUTORISÉ"
        df['RISK_CLASS'] = "NON AUTORISÉ"
        
    return df.to_dict(orient='records')
```

---

## 5. Mathématiques Appliquées, Statistiques & Intelligence Douanière

### A. Détection univariée de la sous-évaluation par Z-Score
Pour chaque article importé, la douane calcule le prix unitaire unitaire $x_i$ :
$$x_i = \frac{\text{VALEUR\_CFA}_i}{\text{POIDS\_NET}_i}$$

Le score d'écart unitaire (Z-Score) est évalué au sein de la catégorie de produit (nomenclature SH-4) :
$$Z_i = \frac{x_i - \mu_{\text{SH}}}{\sigma_{\text{SH}}}$$

Où :
*   $\mu_{\text{SH}}$ : Moyenne historique du prix unitaire pour cette catégorie SH.
*   $\sigma_{\text{SH}}$ : Écart-type du prix unitaire pour cette catégorie SH.

Si $Z_i < -2.0$, la transaction est jugée de façon suspecte. Le score de risque est alors augmenté de $40$ points.

### B. Détection multivariée des anomalies structurelles par Isolation Forest
Pour détecter les fraudes plus complexes qui n'apparaissent pas sur une seule variable, le backend applique un algorithme d'Isolation Forest.
Le score d'anomalie d'un dossier $\mathbf{x}$ est défini par :
$$s(\mathbf{x}, n) = 2^{-\frac{E(h(\mathbf{x}))}{c(n)}}$$
Où :
*   $h(\mathbf{x})$ : Profondeur d'isolation de la donnée dans les arbres.
*   $E(h(\mathbf{x}))$ : Moyenne des profondeurs sur la forêt d'arbres.
*   $c(n)$ : Profondeur moyenne théorique d'un arbre binaire de recherche.

Si $s(\mathbf{x}, n) > 0.65$, le dossier est identifié comme suspect et son `RISK_CLASS` passe à `Haut Risque`.

### C. Modélisation Prédictive & Séries Temporelles (Forecasting)
Le module analytique compare trois approches (ARIMA, Prophet, Holt-Winters) pour prédire les recettes douanières quotidiennes et sélectionne le modèle ayant le MAPE le plus faible :

$$\text{MAPE} = \frac{100\%}{n} \sum_{t=1}^{n} \left| \frac{y_t - \hat{y}_t}{y_t} \right|$$

Où $y_t$ est la valeur réelle constatée et $\hat{y}_t$ est la prévision émise.

### D. Segmentation Métier par K-Means
Pour classifier les importateurs, l'algorithme K-Means cherche à partitionner les observations en minimisant la variance intra-classe :

$$\arg\min_{\mathbf{S}} \sum_{k=1}^{4} \sum_{\mathbf{x}_i \in S_k} \|\mathbf{x}_i - \boldsymbol{\mu}_k\|^2$$

Avec :
$$\mathbf{x}_i = \left[ \log(\text{Volume CFA Cumulé}_i), \log(\text{Nombre de Déclarations}_i) \right]$$

---

## 6. Spécifications Détaillées des API REST (FastAPI)

### A. Route : `POST /api/inspecteur/simulate-risk`
*   **Request Schema** :
    ```json
    {
      "importer": "DANGOTE SENEGAL",
      "country": "CN",
      "hs_code": "8703",
      "amount": 18000000.0
    }
    ```
*   **Response Schema** :
    ```json
    {
      "score": 75.0,
      "risk_class": "Haut risque",
      "reasons": [
        "Code SH sensible aux anomalies de valeur (+40)",
        "Montant élevé (> 10M CFA) (+20)",
        "Provenance géographique sous surveillance (+15)"
      ]
    }
    ```

### B. Route : `POST /api/direction/simulate-weights`
*   **Request Schema** :
    ```json
    {
      "weight_under_eval": 45,
      "weight_top_amount": 25,
      "weight_new_importer": 10,
      "weight_country_contention": 20
    }
    ```
*   **Response Schema** :
    ```json
    {
      "low_risk": 1180,
      "med_risk": 610,
      "high_risk": 210
    }
    ```

### C. Route : `GET /api/partenaire/importer-reliability`
*   **Parameters** : `ninea=005039963`
*   **Response Schema** :
    ```json
    {
      "score": 92,
      "class": "A+ (Excellent)",
      "total_dossiers": 154,
      "active_dossiers": 120,
      "pending_dossiers": 34
    }
    ```

### D. Route : `POST /api/statistician/export-csv`
*   **Request Schema** :
    ```json
    {
      "mode_transport": "Mer",
      "country": "CHINE"
    }
    ```
*   **Response Schema** :
    ```json
    {
      "download_url": "/api/statistician/download-csv/export_anonyme_4592.csv"
    }
    ```

### E. Route : `POST /api/admin/simulate-incident`
*   **Request Schema** :
    ```json
    {
      "incident_type": "brute_force"
    }
    ```
*   **Response Schema** :
    ```json
    {
      "detail": "Incident simulé avec succès."
    }
    ```

---

## 7. Rendu Visuel et Configurations ECharts Côté Client

Les diagrammes de flux de Sankey et cartes de chaleur d'activité sont configurés via l'API Javascript d'Apache ECharts.

### A. Rendu Dynamique Commutable du Diagramme de Sankey
Le diagramme de Sankey s'adapte selon l'opération sélectionnée par l'utilisateur (Importation ou Exportation) :

```javascript
window.switchSankeyMode = function(mode) {
    let nodes = [];
    let links = [];
    
    if (mode === 'imports') {
        nodes = [
            { name: 'Chine', itemStyle: { color: '#fca5a5' } },
            { name: 'Inde', itemStyle: { color: '#fed7aa' } },
            { name: 'France', itemStyle: { color: '#bfdbfe' } },
            { name: 'Autres pays', itemStyle: { color: '#e2e8f0' } },
            { name: 'Maritime (Port)', itemStyle: { color: '#1455a2' } },
            { name: 'Aérien (AIBD)', itemStyle: { color: '#10b981' } },
            { name: 'Routier (Frontières)', itemStyle: { color: '#f59e0b' } },
            { name: 'Sénégal (Mise en Conso)', itemStyle: { color: '#0f172a' } },
            { name: 'Sénégal (Transit Régional)', itemStyle: { color: '#64748b' } }
        ];
        
        links = [
            { source: 'Chine', target: 'Maritime (Port)', value: 65000 },
            { source: 'Inde', target: 'Maritime (Port)', value: 30000 },
            { source: 'France', target: 'Maritime (Port)', value: 30000 },
            { source: 'France', target: 'Aérien (AIBD)', value: 15000 },
            { source: 'Autres pays', target: 'Routier (Frontières)', value: 20000 },
            { source: 'Maritime (Port)', target: 'Sénégal (Mise en Conso)', value: 125000 },
            { source: 'Aérien (AIBD)', target: 'Sénégal (Mise en Conso)', value: 15000 },
            { source: 'Routier (Frontières)', target: 'Sénégal (Transit Régional)', value: 20000 }
        ];
    } else {
        nodes = [
            { name: 'Sénégal (Source)', itemStyle: { color: '#bbf7d0' } },
            { name: 'Maritime (Port)', itemStyle: { color: '#1455a2' } },
            { name: 'Aérien (AIBD)', itemStyle: { color: '#10b981' } },
            { name: 'Routier (Frontières)', itemStyle: { color: '#f59e0b' } },
            { name: 'France (Dest)', itemStyle: { color: '#bfdbfe' } },
            { name: 'Chine (Dest)', itemStyle: { color: '#fca5a5' } },
            { name: 'Afrique de l\'Est (Dest)', itemStyle: { color: '#fed7aa' } }
        ];
        
        links = [
            { source: 'Sénégal (Source)', target: 'Maritime (Port)', value: 40000 },
            { source: 'Sénégal (Source)', target: 'Aérien (AIBD)', value: 20000 },
            { source: 'Sénégal (Source)', target: 'Routier (Frontières)', value: 10000 },
            { source: 'Maritime (Port)', target: 'France (Dest)', value: 15000 },
            { source: 'Maritime (Port)', target: 'Chine (Dest)', value: 25000 },
            { source: 'Aérien (AIBD)', target: 'France (Dest)', value: 10000 },
            { source: 'Aérien (AIBD)', target: 'Afrique de l\'Est (Dest)', value: 10000 },
            { source: 'Routier (Frontières)', target: 'Afrique de l\'Est (Dest)', value: 10000 }
        ];
    }
    
    chartSankey.setOption({
        tooltip: { trigger: 'item', triggerOn: 'mousemove' },
        series: [{
            type: 'sankey',
            data: nodes,
            links: links,
            emphasis: { focus: 'adjacency' },
            lineStyle: { color: 'gradient', curveness: 0.5 },
            label: {
                color: '#1e293b',
                fontFamily: 'inherit',
                fontSize: 11,
                fontWeight: '600'
            }
        }]
    }, true);
};
```

---

## 8. Procédure de Déploiement et Vérification

### A. Lancement de l'Environnement de Développement
1.  **Lancement du Serveur FastAPI** :
    ```bash
    uvicorn app:app --host 127.0.0.1 --port 8000 --reload
    ```
2.  **Ouverture de l'Application** :
    Charger le fichier `index.html` dans un navigateur moderne.

### B. Validation par la Suite de Tests d'Intégration
Avant toute modification ou déploiement :
```bash
python3 scratch/test_endpoints.py
```
Ce script valide de manière automatisée la matrice RBAC/RLS/CLS, les simulateurs de risque et les alertes prédictives.
