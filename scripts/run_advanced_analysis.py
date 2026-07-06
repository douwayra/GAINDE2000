#!/usr/bin/env python3
import os
import json
import logging
import duckdb
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import joblib
import torch
import torch.nn as nn
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    # Avoid division by zero
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def main():
    logging.info("=== STARTING ADVANCED ANALYSIS & MODELING PIPELINE ===")
    
    db_path = os.getenv('DB_DOUANE_PATH', 'data/db/gainde_douane.db')
    conn = duckdb.connect(db_path)
    
    # 1. Load Data
    logging.info("Loading tables from DuckDB database...")
    df_dossiers = conn.execute("SELECT * FROM dossiers").df()
    df_factures = conn.execute("SELECT * FROM factures").df()
    df_articles = conn.execute("SELECT * FROM articles").df()
    
    logging.info(f"Loaded {len(df_dossiers):,} dossiers, {len(df_factures):,} factures, {len(df_articles):,} articles.")
    
    # Pre-parse dates
    df_dossiers['DATE_DT'] = pd.to_datetime(df_dossiers['DATE_CREATION'], errors='coerce')
    
    # ==========================================
    # 2. CORE CUSTOMS & FINANCIAL KPIS
    # ==========================================
    logging.info("Computing Core KPIs...")
    total_dossiers = len(df_dossiers['NUMERODOSSIERTPS'].dropna().unique())
    total_factures = len(df_factures['IDTPSFACTURE'].dropna().unique())
    total_articles = len(df_articles)
    
    total_val_cfa = df_articles['VALEURCFA'].sum()
    total_poids_net = df_articles['POIDSNET'].sum()
    total_qty = df_articles['QUANTITEMESURE'].sum()
    
    avg_val_dossier = total_val_cfa / max(total_dossiers, 1)
    avg_val_facture = total_val_cfa / max(total_factures, 1)
    avg_val_article = total_val_cfa / max(total_articles, 1)
    
    # Helper to retrieve the most common commercial designation for a given tariff code
    def get_most_common_designation(df, code):
        sub = df[df['NUMEROTARIFDOUANE'] == code]['DESIGNATIONCOMMERCIALE'].dropna()
        if len(sub) > 0:
            desc = str(sub.value_counts().index[0])
            if len(desc) > 35:
                return desc[:32] + "..."
            return desc
        return "PRODUIT INCONNU"

    # Top products by imported value
    top_products_val = df_articles.groupby('NUMEROTARIFDOUANE')['VALEURCFA'].sum().reset_index()
    top_products_val = top_products_val.sort_values(by='VALEURCFA', ascending=False).head(10)
    top_products_val['DESIGNATION'] = top_products_val['NUMEROTARIFDOUANE'].apply(lambda c: get_most_common_designation(df_articles, c))
    top_products_val_list = [{"NUMEROTARIFDOUANE": str(r["NUMEROTARIFDOUANE"]), "DESIGNATION": str(r["DESIGNATION"]), "VALEURCFA": float(r["VALEURCFA"])} for _, r in top_products_val.iterrows()]
    
    # Top most expensive products (by unit value)
    df_articles['P_UNITAIRE'] = df_articles['VALEURCFA'] / df_articles['QUANTITEMESURE']
    top_products_expensive = df_articles.groupby('NUMEROTARIFDOUANE')['P_UNITAIRE'].median().reset_index()
    top_products_expensive = top_products_expensive.sort_values(by='P_UNITAIRE', ascending=False).head(10)
    top_products_expensive['DESIGNATION'] = top_products_expensive['NUMEROTARIFDOUANE'].apply(lambda c: get_most_common_designation(df_articles, c))
    top_products_expensive_list = [{"NUMEROTARIFDOUANE": str(r["NUMEROTARIFDOUANE"]), "DESIGNATION": str(r["DESIGNATION"]), "P_UNITAIRE": float(r["P_UNITAIRE"])} for _, r in top_products_expensive.iterrows()]
    
    # ==========================================
    # 3. GEOGRAPHICAL REGIONS SPLIT
    # ==========================================
    logging.info("Analyzing Geographical Regions...")
    cedeao_countries = {
        "Sénégal", "Mali", "Côte d'Ivoire", "Guinée", "Burkina Faso", "Niger", 
        "Bénin", "Togo", "Ghana", "Nigeria", "Gambie", "Cap-Vert", "Guinée-Bissau", 
        "Liberia", "Sierra Leone"
    }
    
    europe_countries = {
        "France", "Pays-Bas", "Belgique", "Allemagne", "Italie", "Espagne", 
        "Royaume-Uni", "Suisse", "Portugal", "Suède", "Pologne", "Autriche", 
        "Danemark", "Finlande", "Irlande", "Grèce", "Norvège", "Hongrie", "Roumanie"
    }
    
    asie_countries = {
        "Chine", "Inde", "Turquie", "Japon", "Émirats Arabes Unis", "Arabie Saoudite", 
        "Indonésie", "Corée du Sud", "Thaïlande", "Vietnam", "Malaisie", "Singapour", 
        "Pakistan", "Bangladesh", "Iran", "Irak", "Liban", "Koweït"
    }
    
    def get_region(country):
        if not country or pd.isna(country):
            return "Inconnu"
        c = str(country).strip()
        if c in cedeao_countries:
            return "CEDEAO"
        elif c in europe_countries:
            return "Europe"
        elif c in asie_countries:
            return "Asie"
        else:
            return "Autres"
            
    df_articles['REGION_ORIGINE'] = df_articles['PAYSORIGINE'].apply(get_region)
    region_val_split = df_articles.groupby('REGION_ORIGINE')['VALEURCFA'].sum().to_dict()
    region_shares = {k: v / total_val_cfa * 100 for k, v in region_val_split.items()}

    # Country-level mapping for world map
    country_mapping = {
        "Sénégal": "Senegal",
        "France": "France",
        "Pays-Bas": "Netherlands",
        "Chine": "China",
        "Inde": "India",
        "Cote d Ivoire": "Ivory Coast",
        "Cote d'Ivoire": "Ivory Coast",
        "Côte d'Ivoire": "Ivory Coast",
        "Maroc": "Morocco",
        "Belgique": "Belgium",
        "Ghana": "Ghana",
        "Turquie": "Turkey",
        "Espagne": "Spain",
        "Nigéria": "Nigeria",
        "Nigeria": "Nigeria",
        "Brésil": "Brazil",
        "Russie": "Russia",
        "Allemagne": "Germany",
        "Togo": "Togo",
        "Etats-Unis": "United States",
        "United States": "United States",
        "Suisse": "Switzerland",
        "Dubaï": "United Arab Emirates",
        "Émirats arabes unis": "United Arab Emirates",
        "Emirats Arabes Unis": "United Arab Emirates",
        "Mali": "Mali",
        "Royaume-Uni": "United Kingdom",
        "Italie": "Italy",
        "Japon": "Japan",
        "Canada": "Canada",
        "Mauritanie": "Mauritania",
        "Arabie Saoudite": "Saudi Arabia",
        "Afrique du Sud": "South Africa",
        "Égypte": "Egypt",
        "Egypte": "Egypt",
        "Algérie": "Algeria",
        "Algerie": "Algeria",
        "Tunisie": "Tunisia",
        "Bénin": "Benin",
        "Cameroun": "Cameroon",
        "Guinée": "Guinea",
        "Niger": "Niger",
        "Burkina Faso": "Burkina Faso",
        "Gabon": "Gabon",
        "Liban": "Lebanon",
        "Portugal": "Portugal",
        "Suède": "Sweden",
        "Danemark": "Denmark",
        "Pologne": "Poland",
        "Autriche": "Austria",
        "Grèce": "Greece",
        "Irlande": "Ireland",
        "Roumanie": "Romania",
        "Norvège": "Norway",
        "Finlande": "Finland",
        "Ukraine": "Ukraine",
        "République Populaire de Chine": "China",
        "Hong Kong": "Hong Kong",
        "Taïwan": "Taiwan",
        "Singapour": "Singapore",
        "Malaisie": "Malaysia",
        "Thaïlande": "Thailand",
        "Viêt Nam": "Vietnam",
        "Vietnam": "Vietnam",
        "Indonésie": "Indonesia",
        "Pakistan": "Pakistan",
        "Argentine": "Argentina",
        "Mexique": "Mexico",
        "Colombie": "Colombia",
        "Chili": "Chile",
        "Pérou": "Peru",
        "Venezuela": "Venezuela",
        "Cuba": "Cuba",
        "Australie": "Australia",
        "Nouvelle-Zélande": "New Zealand",
        "Madagascar": "Madagascar",
        "Maurice": "Mauritius",
        "Kenya": "Kenya",
        "Angola": "Angola"
    }

    # ==========================================
    # 4. LOGISTICS & OPERATIONS SPLIT
    # ==========================================
    logging.info("Analyzing Logistics & Operations...")
    logistics_split = df_dossiers.groupby('MODE_TRANSPORT').size().to_dict()
    
    # We join articles with dossiers to analyze value and quantity per transport mode
    df_art_dos = df_articles.merge(df_dossiers[['NUMERODOSSIERTPS', 'MODE_TRANSPORT', 'TYPE_OPERATION', 'NOM_IMPORTATEUR', 'DATE_DT']], on='NUMERODOSSIERTPS', how='left')
    
    transport_stats = df_art_dos.groupby('MODE_TRANSPORT').agg(
        valeur_moyenne=('VALEURCFA', 'mean'),
        quantite_moyenne=('QUANTITEMESURE', 'mean'),
        total_valeur=('VALEURCFA', 'sum')
    ).reset_index().to_dict(orient='records')
    
    operation_stats = df_art_dos.groupby('TYPE_OPERATION').agg(
        total_valeur=('VALEURCFA', 'sum'),
        count=('NUMERODOSSIERTPS', 'count')
    ).reset_index().to_dict(orient='records')

    # Distinguish Imports and Exports Country Stats
    # For Imports: Group by PAYSORIGINE where TYPE_OPERATION == 'Importation'
    df_imports = df_art_dos[df_art_dos['TYPE_OPERATION'] == 'Importation']
    country_imports = df_imports.groupby('PAYSORIGINE').agg(
        total_valeur=('VALEURCFA', 'sum'),
        count=('IDTPSFACTURE', 'count')
    ).reset_index()
    country_imports = country_imports[country_imports['PAYSORIGINE'].notna() & (country_imports['PAYSORIGINE'] != '')]
    import_stats_list = []
    for idx, row in country_imports.iterrows():
        c_orig = str(row['PAYSORIGINE']).strip()
        c_mapped = country_mapping.get(c_orig, c_orig)
        import_stats_list.append({
            'country': c_mapped,
            'valeur': float(row['total_valeur']),
            'count': int(row['count'])
        })
        
    # For Exports: Group by PAYSDESTINATION where TYPE_OPERATION == 'Exportation'
    df_exports = df_art_dos[df_art_dos['TYPE_OPERATION'] == 'Exportation']
    country_exports = df_exports.groupby('PAYSDESTINATION').agg(
        total_valeur=('VALEURCFA', 'sum'),
        count=('IDTPSFACTURE', 'count')
    ).reset_index()
    country_exports = country_exports[country_exports['PAYSDESTINATION'].notna() & (country_exports['PAYSDESTINATION'] != '') & (country_exports['PAYSDESTINATION'] != 'Inconnu')]
    export_stats_list = []
    for idx, row in country_exports.iterrows():
        c_dest = str(row['PAYSDESTINATION']).strip()
        c_mapped = country_mapping.get(c_dest, c_dest)
        export_stats_list.append({
            'country': c_mapped,
            'valeur': float(row['total_valeur']),
            'count': int(row['count'])
        })

    # === COMPUTE SEPARATE IMPORT/EXPORT SECTIONS ===
    # A. Imports Data
    df_art_dos_imports = df_art_dos[df_art_dos['TYPE_OPERATION'] == 'Importation']
    df_dos_imports = df_dossiers[df_dossiers['TYPE_OPERATION'] == 'Importation'].copy()
    df_dos_imports['MONTH'] = df_dos_imports['DATE_DT'].dt.month_name()
    
    import_dossiers_cnt = len(df_art_dos_imports['NUMERODOSSIERTPS'].dropna().unique())
    import_val = float(df_art_dos_imports['VALEURCFA'].sum())
    import_weight = float(df_art_dos_imports['POIDSNET'].sum())
    import_qty = float(df_art_dos_imports['QUANTITEMESURE'].sum())
    
    import_region_split = df_art_dos_imports.groupby('REGION_ORIGINE')['VALEURCFA'].sum().to_dict()
    import_region_shares = {k: float(v / max(import_val, 1) * 100) for k, v in import_region_split.items()}
    import_mode_split = df_dos_imports.groupby('MODE_TRANSPORT').size().to_dict()
    import_month_counts = df_dos_imports.groupby('MONTH').size().to_dict()
    
    import_top_prod = df_art_dos_imports.groupby('NUMEROTARIFDOUANE')['VALEURCFA'].sum().reset_index()
    import_top_prod = import_top_prod.sort_values(by='VALEURCFA', ascending=False).head(10)
    import_top_prod['DESIGNATION'] = import_top_prod['NUMEROTARIFDOUANE'].apply(lambda c: get_most_common_designation(df_articles, c))
    import_top_prod_list = [{"NUMEROTARIFDOUANE": str(r["NUMEROTARIFDOUANE"]), "DESIGNATION": str(r["DESIGNATION"]), "VALEURCFA": float(r["VALEURCFA"])} for _, r in import_top_prod.iterrows()]
    
    # B. Exports Data
    df_art_dos_exports = df_art_dos[df_art_dos['TYPE_OPERATION'] == 'Exportation']
    df_dos_exports = df_dossiers[df_dossiers['TYPE_OPERATION'] == 'Exportation'].copy()
    df_dos_exports['MONTH'] = df_dos_exports['DATE_DT'].dt.month_name()
    
    export_dossiers_cnt = len(df_art_dos_exports['NUMERODOSSIERTPS'].dropna().unique())
    export_val = float(df_art_dos_exports['VALEURCFA'].sum())
    export_weight = float(df_art_dos_exports['POIDSNET'].sum())
    export_qty = float(df_art_dos_exports['QUANTITEMESURE'].sum())
    
    df_art_dos_exports = df_art_dos_exports.copy()
    df_art_dos_exports['REGION_DESTINATION'] = df_art_dos_exports['PAYSDESTINATION'].apply(get_region)
    export_region_split = df_art_dos_exports.groupby('REGION_DESTINATION')['VALEURCFA'].sum().to_dict()
    export_region_shares = {k: float(v / max(export_val, 1) * 100) for k, v in export_region_split.items()}
    
    export_mode_split = df_dos_exports.groupby('MODE_TRANSPORT').size().to_dict()
    export_month_counts = df_dos_exports.groupby('MONTH').size().to_dict()
    
    export_top_prod = df_art_dos_exports.groupby('NUMEROTARIFDOUANE')['VALEURCFA'].sum().reset_index()
    export_top_prod = export_top_prod.sort_values(by='VALEURCFA', ascending=False).head(10)
    export_top_prod['DESIGNATION'] = export_top_prod['NUMEROTARIFDOUANE'].apply(lambda c: get_most_common_designation(df_articles, c))
    export_top_prod_list = [{"NUMEROTARIFDOUANE": str(r["NUMEROTARIFDOUANE"]), "DESIGNATION": str(r["DESIGNATION"]), "VALEURCFA": float(r["VALEURCFA"])} for _, r in export_top_prod.iterrows()]
    
    # ==========================================
    # 5. PARETO 80/20 ANALYSIS
    # ==========================================
    logging.info("Running Pareto 80/20 Analysis...")
    # Importers Pareto
    importer_vals = df_art_dos.groupby('NOM_IMPORTATEUR')['VALEURCFA'].sum().sort_values(ascending=False)
    cum_importer_val = importer_vals.cumsum() / importer_vals.sum()
    top_20pct_count = int(np.ceil(0.20 * len(importer_vals)))
    importer_pareto_val = cum_importer_val.iloc[min(top_20pct_count, len(cum_importer_val)-1)] * 100
    
    # Products Pareto
    product_vals = df_articles.groupby('NUMEROTARIFDOUANE')['VALEURCFA'].sum().sort_values(ascending=False)
    cum_product_val = product_vals.cumsum() / product_vals.sum()
    top_20pct_prod_count = int(np.ceil(0.20 * len(product_vals)))
    product_pareto_val = cum_product_val.iloc[min(top_20pct_prod_count, len(cum_product_val)-1)] * 100
    
    # ==========================================
    # 6. TIME DECOMPOSITION
    # ==========================================
    logging.info("Decomposing Time Seasonalities...")
    df_dossiers['DAY_OF_WEEK'] = df_dossiers['DATE_DT'].dt.day_name()
    df_dossiers['MONTH'] = df_dossiers['DATE_DT'].dt.month_name()
    df_dossiers['QUARTER'] = df_dossiers['DATE_DT'].dt.to_period('Q').astype(str)
    
    dow_counts = df_dossiers.groupby('DAY_OF_WEEK').size().to_dict()
    month_counts = df_dossiers.groupby('MONTH').size().to_dict()
    quarter_counts = df_dossiers.groupby('QUARTER').size().to_dict()
    
    # Heatmap data (Day of week x Month)
    heatmap_df = df_dossiers.groupby(['DAY_OF_WEEK', 'MONTH']).size().reset_index(name='count')
    heatmap_data = heatmap_df.to_dict(orient='records')
    
    # ==========================================
    # 7. IMPORTER SEGMENTATION (K-MEANS)
    # ==========================================
    logging.info("Running Importer K-Means Clustering...")
    importer_features = df_art_dos.groupby('NOM_IMPORTATEUR').agg(
        dossier_count=('NUMERODOSSIERTPS', 'nunique'),
        total_value=('VALEURCFA', 'sum'),
        total_qty=('QUANTITEMESURE', 'sum'),
        active_weeks=('DATE_DT', lambda x: x.dt.isocalendar().week.nunique() if not x.isna().all() else 1)
    ).reset_index()
    
    # Filter out empty importers
    importer_features = importer_features.dropna()
    
    # Scale features with log transform to handle outliers robustness
    importer_features['log_dossier_count'] = np.log1p(importer_features['dossier_count'])
    importer_features['log_total_value'] = np.log1p(importer_features['total_value'])
    importer_features['log_total_qty'] = np.log1p(importer_features['total_qty'])
    importer_features['log_active_weeks'] = np.log1p(importer_features['active_weeks'])
    
    scaler = StandardScaler()
    scaled_feats = scaler.fit_transform(importer_features[['log_dossier_count', 'log_total_value', 'log_total_qty', 'log_active_weeks']])
    
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    importer_features['cluster'] = kmeans.fit_predict(scaled_feats) # Fit and relabel
    
    # Relabel based on median value
    cluster_means = importer_features.groupby('cluster')['total_value'].median().sort_values().index
    cluster_labels = {
        cluster_means[0]: 'Petits importateurs occasionnels',
        cluster_means[1]: 'Importateurs réguliers',
        cluster_means[2]: 'Grands comptes',
        cluster_means[3]: 'Très gros importateurs stratégiques'
    }
    importer_features['segment'] = importer_features['cluster'].map(cluster_labels)
    
    # Create segment mapping dictionary for dossiers join
    segment_map = dict(zip(importer_features['NOM_IMPORTATEUR'], importer_features['segment']))
    df_dossiers['IMPORTATEUR_SEGMENT'] = df_dossiers['NOM_IMPORTATEUR'].map(segment_map).fillna('Petits importateurs occasionnels')
    
    # Save segmentation stats
    segment_stats = importer_features.groupby('segment').agg(
        count=('NOM_IMPORTATEUR', 'count'),
        avg_value=('total_value', 'mean'),
        avg_dossiers=('dossier_count', 'mean')
    ).reset_index().to_dict(orient='records')
    
    # ==========================================
    # 8. ADVANCED FRAUD DETECTION (ISOLATION FOREST vs Z-SCORE)
    # ==========================================
    logging.info("Running Fraud Detection Models...")
    
    # A. Z-score Suspect Detection (Recomputed for alignment)
    tarifs_stats = df_articles.groupby('NUMEROTARIFDOUANE')['P_UNITAIRE'].agg(['median', 'std', 'count']).reset_index()
    df_articles_stats = df_articles.merge(tarifs_stats, on='NUMEROTARIFDOUANE', how='left')
    
    # Calculate Z-score
    df_articles_stats['Z_SCORE'] = (df_articles_stats['P_UNITAIRE'] - df_articles_stats['median']) / df_articles_stats['std']
    df_articles_stats['SUSPECT_Z'] = (df_articles_stats['Z_SCORE'] < -1.5) & (df_articles_stats['count'] >= 10) & (df_articles_stats['std'] > 0)
    df_articles_stats['SUSPECT_Z'] = df_articles_stats['SUSPECT_Z'].fillna(False)
    
    # Save Z-score suspect ids
    suspect_z_ids = set(df_articles_stats[df_articles_stats['SUSPECT_Z']]['IDTPSFACTURE'].dropna().unique())
    
    # B. Isolation Forest Anomaly Detection
    features_if = df_articles[['VALEURCFA', 'QUANTITEMESURE', 'POIDSNET', 'POIDSBRUT']].copy()
    features_if = features_if.fillna(features_if.median())
    
    iforest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    df_articles_stats['ANOMALY_IF'] = iforest.fit_predict(features_if) == -1
    
    suspect_if_ids = set(df_articles_stats[df_articles_stats['ANOMALY_IF']]['IDTPSFACTURE'].dropna().unique())
    
    # Save models to disk
    os.makedirs('data/models', exist_ok=True)
    joblib.dump(scaler, 'data/models/scaler_kmeans.pkl')
    joblib.dump(kmeans, 'data/models/kmeans_model.pkl')
    joblib.dump(iforest, 'data/models/iforest_model.pkl')
    logging.info("Serialized K-Means, Scaler, and Isolation Forest models saved to data/models/")
    
    # Compare methods
    intersection_ids = suspect_z_ids.intersection(suspect_if_ids)
    logging.info(f"Z-Score Suspects: {len(suspect_z_ids):,}")
    logging.info(f"Isolation Forest Suspects: {len(suspect_if_ids):,}")
    logging.info(f"Overlap between Z-Score and Isolation Forest: {len(intersection_ids):,}")
    
    # ==========================================
    # 9. CUSTOMS RISK SCORING MODEL (ON 100)
    # ==========================================
    logging.info("Computing Customs Risk Scores...")
    
    # Identify suspect countries (countries with under-valuation rate in top 20%)
    country_fraud = df_articles_stats.groupby('PAYSORIGINE').agg(
        suspects=('SUSPECT_Z', 'sum'),
        total=('SUSPECT_Z', 'count')
    ).reset_index()
    country_fraud = country_fraud[country_fraud['total'] >= 50]
    country_fraud['rate'] = country_fraud['suspects'] / country_fraud['total']
    risk_countries = set(country_fraud.sort_values(by='rate', ascending=False).head(int(np.ceil(0.20 * len(country_fraud))))['PAYSORIGINE'])
    
    # Identify unusual quantity (top 5% per tariff code)
    qty_q95 = df_articles.groupby('NUMEROTARIFDOUANE')['QUANTITEMESURE'].quantile(0.95).reset_index(name='q95')
    df_articles_qty = df_articles.merge(qty_q95, on='NUMEROTARIFDOUANE', how='left')
    df_articles_qty['UNUSUAL_QTY'] = df_articles_qty['QUANTITEMESURE'] > df_articles_qty['q95']
    unusual_qty_dossiers = set(df_articles_qty[df_articles_qty['UNUSUAL_QTY']]['NUMERODOSSIERTPS'])
    
    # Importer dossiers count for new declarant detection
    importer_counts = df_dossiers.groupby('NOM_IMPORTATEUR').size().to_dict()
    
    # Mapping of under-valuation per dossier
    dossier_suspect_z = set(df_articles_stats[df_articles_stats['SUSPECT_Z']]['NUMERODOSSIERTPS'])
    
    # Dossier total values for atypical value detection (top 10% value)
    dossier_values = df_art_dos.groupby('NUMERODOSSIERTPS')['VALEURCFA'].sum().to_dict()
    q90_dossier_val = pd.Series(list(dossier_values.values())).quantile(0.90)
    
    # Vectorized computation of risk scores for speed
    score_under = df_dossiers['NUMERODOSSIERTPS'].isin(dossier_suspect_z).astype(int) * 40
    dos_vals = df_dossiers['NUMERODOSSIERTPS'].map(dossier_values).fillna(0)
    score_val = (dos_vals > q90_dossier_val).astype(int) * 20
    imp_counts = df_dossiers['NOM_IMPORTATEUR'].map(importer_counts).fillna(0)
    score_new = (imp_counts <= 3).astype(int) * 15
    score_country = df_dossiers['PAYS_PROVENANCE'].isin(risk_countries).astype(int) * 15
    score_qty = df_dossiers['NUMERODOSSIERTPS'].isin(unusual_qty_dossiers).astype(int) * 10
    
    df_dossiers['RISK_SCORE'] = (score_under + score_val + score_new + score_country + score_qty).clip(upper=100)
    
    def get_risk_class(score):
        if score < 30:
            return "Faible risque"
        elif score < 60:
            return "Moyen risque"
        else:
            return "Haut risque"
            
    df_dossiers['RISK_CLASS'] = df_dossiers['RISK_SCORE'].apply(get_risk_class)
    
    risk_class_counts = df_dossiers['RISK_CLASS'].value_counts().to_dict()
    
    # ==========================================
    # 10. FLUX FORECASTING MODELS
    # ==========================================
    logging.info("Modeling Flux Forecasting (Daily Dossiers count)...")
    daily_series = df_dossiers.groupby(df_dossiers['DATE_DT'].dt.date).size().reset_index(name='y')
    daily_series.columns = ['ds', 'y']
    daily_series = daily_series.sort_values(by='ds')
    
    # Generate lag features
    for lag in [1, 2, 7, 14]:
        daily_series[f'LAG_{lag}'] = daily_series['y'].shift(lag)
    daily_series['MOYENNE_MOBILE_7J'] = daily_series['y'].shift(1).rolling(7).mean()
    
    daily_series = daily_series.dropna().reset_index(drop=True)
    
    # Train-test split (last 30 days as test)
    train_df = daily_series.iloc[:-30]
    test_df = daily_series.iloc[-30:]
    
    features = ['LAG_1', 'LAG_2', 'LAG_7', 'LAG_14', 'MOYENNE_MOBILE_7J']
    
    X_train, y_train = train_df[features], train_df['y']
    X_test, y_test = test_df[features], test_df['y']
    
    # Models training
    # 1. Baseline: 7-day Moving Average (which is MOYENNE_MOBILE_7J)
    baseline_preds = X_test['MOYENNE_MOBILE_7J']
    
    # 2. Linear Regression
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_preds = lr.predict(X_test)
    
    # 3. Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    
    # 4. XGBoost (Gradient Boosting Regressor de fallback)
    xgb = GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
    xgb.fit(X_train, y_train)
    xgb_preds = xgb.predict(X_test)
    
    # Metrics
    models_metrics = {}
    for name, preds in [('Baseline', baseline_preds), ('LinearRegression', lr_preds), ('RandomForest', rf_preds), ('XGBoost', xgb_preds)]:
        mae = np.mean(np.abs(y_test - preds))
        rmse = np.sqrt(np.mean((y_test - preds) ** 2))
        mape = calculate_mape(y_test, preds)
        models_metrics[name] = {'MAE': mae, 'RMSE': rmse, 'MAPE': mape}
        logging.info(f"{name} -> MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2f}%")

    # 5. LSTM Deep Learning Model
    logging.info("Training PyTorch LSTM model...")
    seq_len = 14
    
    # Scale variables using standard scaling
    scaler = StandardScaler()
    scaled_y_train = scaler.fit_transform(y_train.values.reshape(-1, 1)).flatten()
    
    def create_lstm_sequences(data, seq_length):
        xs, ys = [], []
        for i in range(len(data) - seq_length):
            x = data[i:(i + seq_length)]
            y = data[i + seq_length]
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)
        
    train_seq_x, train_seq_y = create_lstm_sequences(scaled_y_train, seq_len)
    
    X_train_tensor = torch.tensor(train_seq_x, dtype=torch.float32).unsqueeze(-1)
    y_train_tensor = torch.tensor(train_seq_y, dtype=torch.float32).unsqueeze(-1)
    
    class LSTMModel(nn.Module):
        def __init__(self, input_dim=1, hidden_dim=32, num_layers=1, output_dim=1):
            super().__init__()
            self.hidden_dim = hidden_dim
            self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
            self.linear = nn.Linear(hidden_dim, output_dim)
            
        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            out = self.linear(lstm_out[:, -1, :])
            return out
            
    lstm_net = LSTMModel(input_dim=1, hidden_dim=32, num_layers=1, output_dim=1)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(lstm_net.parameters(), lr=0.01)
    
    # Train
    epochs = 120
    lstm_net.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        preds_tensor = lstm_net(X_train_tensor)
        loss = criterion(preds_tensor, y_train_tensor)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 30 == 0:
            logging.info(f"LSTM Epoch {epoch+1}/{epochs} - Loss: {loss.item():.4f}")
            
    # Evaluation (Autoregressive 30-step forecast)
    lstm_net.eval()
    lstm_preds = []
    current_seq = list(scaled_y_train[-seq_len:])
    
    with torch.no_grad():
        for i in range(30):
            seq_tensor = torch.tensor(current_seq[-seq_len:], dtype=torch.float32).view(1, seq_len, 1)
            pred = lstm_net(seq_tensor).item()
            lstm_preds.append(pred)
            current_seq.append(pred)
            
    lstm_preds_orig = scaler.inverse_transform(np.array(lstm_preds).reshape(-1, 1)).flatten()
    lstm_preds_orig = np.clip(lstm_preds_orig, a_min=0, a_max=None)
    
    # Calculate training residuals standard deviation for confidence interval
    with torch.no_grad():
        train_preds_scaled = np.array(lstm_net(X_train_tensor).detach().tolist()).flatten()
    train_preds_orig = scaler.inverse_transform(train_preds_scaled.reshape(-1, 1)).flatten()
    y_train_aligned = y_train.values[seq_len:]
    residuals = y_train_aligned - train_preds_orig
    std_residuals = np.std(residuals)
    logging.info(f"LSTM Train residuals standard deviation: {std_residuals:.2f}")
    
    # Compute expanding confidence interval (uncertainty grows by sqrt(h))
    lower_bounds = []
    upper_bounds = []
    for h in range(1, 31):
        uncertainty = 1.96 * std_residuals * np.sqrt(h)
        pred_val = lstm_preds_orig[h - 1]
        lower_bounds.append(max(0.0, float(pred_val - uncertainty)))
        upper_bounds.append(float(pred_val + uncertainty))
        
    lstm_mae = np.mean(np.abs(y_test - lstm_preds_orig))
    lstm_rmse = np.sqrt(np.mean((y_test - lstm_preds_orig) ** 2))
    lstm_mape = calculate_mape(y_test, lstm_preds_orig)
    
    models_metrics['LSTM'] = {'MAE': float(lstm_mae), 'RMSE': float(lstm_rmse), 'MAPE': float(lstm_mape)}
    logging.info(f"LSTM -> MAE: {lstm_mae:.2f}, RMSE: {lstm_rmse:.2f}, MAPE: {lstm_mape:.2f}%")
    
    # Extract dates for test plot
    test_dates = [d.strftime('%Y-%m-%d') for d in test_df['ds']]
    
    lstm_forecast_data = {
        'dates': test_dates,
        'actuals': [int(val) for val in y_test.values],
        'predictions': [float(val) for val in lstm_preds_orig],
        'lower_bounds': [float(val) for val in lower_bounds],
        'upper_bounds': [float(val) for val in upper_bounds],
        'metrics': {
            'MAE': float(lstm_mae),
            'RMSE': float(lstm_rmse),
            'MAPE': float(lstm_mape)
        }
    }
        
    # ==========================================
    # 11. PERSIST DATA & UPDATE DATABASE
    # ==========================================
    logging.info("Updating DuckDB Database Tables...")
    
    # A. Write columns back to database
    # Write Segment and Risk columns to dossiers
    conn.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS IMPORTATEUR_SEGMENT VARCHAR")
    conn.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS RISK_SCORE INT")
    conn.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS RISK_CLASS VARCHAR")
    
    # Clean tables and write back using temporary views
    temp_dos = df_dossiers[['NUMERODOSSIERTPS', 'IMPORTATEUR_SEGMENT', 'RISK_SCORE', 'RISK_CLASS']]
    conn.execute("CREATE OR REPLACE TEMPORARY VIEW temp_dossiers_view AS SELECT * FROM temp_dos")
    conn.execute("""
        UPDATE dossiers
        SET IMPORTATEUR_SEGMENT = temp_dossiers_view.IMPORTATEUR_SEGMENT,
            RISK_SCORE = temp_dossiers_view.RISK_SCORE,
            RISK_CLASS = temp_dossiers_view.RISK_CLASS
        FROM temp_dossiers_view
        WHERE dossiers.NUMERODOSSIERTPS = temp_dossiers_view.NUMERODOSSIERTPS
    """)
    
    # Add anomaly column to articles
    conn.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS ANOMALY_IF BOOLEAN")
    temp_art = df_articles_stats[['IDTPSFACTURE', 'ORDRE', 'ANOMALY_IF']]
    conn.execute("CREATE OR REPLACE TEMPORARY VIEW temp_articles_view AS SELECT * FROM temp_art")
    conn.execute("""
        UPDATE articles
        SET ANOMALY_IF = temp_articles_view.ANOMALY_IF
        FROM temp_articles_view
        WHERE articles.IDTPSFACTURE = temp_articles_view.IDTPSFACTURE 
          AND articles.ORDRE = temp_articles_view.ORDRE
    """)
    
    # Re-save cleaned CSVs with updated columns
    csv_dir = 'data/csv' if os.path.isdir('data/csv') else '.'
    df_dossiers.to_csv(os.path.join(csv_dir, 'entete_dossier_clean.csv'), index=False, encoding='utf-8')
    df_articles_stats.to_csv(os.path.join(csv_dir, 'articles_clean_all.csv'), index=False, encoding='utf-8')
    
    # Write output stats JSON for the Web/Jupyter Dashboards
    dashboard_data = {
        'kpis': {
            'total_dossiers': int(total_dossiers),
            'total_factures': int(total_factures),
            'total_articles': int(total_articles),
            'total_val_cfa': float(total_val_cfa),
            'total_poids_net': float(total_poids_net),
            'total_qty': float(total_qty),
            'avg_val_dossier': float(avg_val_dossier),
            'avg_val_facture': float(avg_val_facture),
            'avg_val_article': float(avg_val_article)
        },
        'geography': {
            'region_val_split': {k: float(v) for k, v in region_val_split.items()},
            'region_shares': {k: float(v) for k, v in region_shares.items()},
            'import_country_stats': import_stats_list,
            'export_country_stats': export_stats_list
        },
        'logistics': {
            'mode_split': {str(k): int(v) for k, v in logistics_split.items()},
            'transport_stats': transport_stats,
            'operation_stats': operation_stats
        },
        'pareto': {
            'importer_pareto_val': float(importer_pareto_val),
            'product_pareto_val': float(product_pareto_val)
        },
        'time_decomposition': {
            'day_of_week': {str(k): int(v) for k, v in dow_counts.items()},
            'month': {str(k): int(v) for k, v in month_counts.items()},
            'quarter': {str(k): int(v) for k, v in quarter_counts.items()},
            'heatmap': heatmap_data
        },
        'segmentation': segment_stats,
        'fraud_comparison': {
            'z_score_count': int(len(suspect_z_ids)),
            'isolation_forest_count': int(len(suspect_if_ids)),
            'overlap_count': int(len(intersection_ids))
        },
        'risk_profile': {
            'low_risk': int(risk_class_counts.get('Faible risque', 0)),
            'med_risk': int(risk_class_counts.get('Moyen risque', 0)),
            'high_risk': int(risk_class_counts.get('Haut risque', 0))
        },
        'forecasting': models_metrics,
        'lstm_forecast': lstm_forecast_data,
        'top_products': {
            'by_value': top_products_val_list,
            'expensive': top_products_expensive_list
        },
        'imports_data': {
            'kpis': {
                'total_dossiers': int(import_dossiers_cnt),
                'total_val_cfa': float(import_val),
                'total_poids_net': float(import_weight),
                'total_qty': float(import_qty),
                'avg_val_dossier': float(import_val / max(import_dossiers_cnt, 1))
            },
            'geography': {
                'region_val_split': {k: float(v) for k, v in import_region_split.items()},
                'region_shares': import_region_shares,
                'country_stats': import_stats_list
            },
            'logistics': {
                'mode_split': {str(k): int(v) for k, v in import_mode_split.items()}
            },
            'time_decomposition': {
                'month': {str(k): int(v) for k, v in import_month_counts.items()}
            },
            'top_products': import_top_prod_list
        },
        'exports_data': {
            'kpis': {
                'total_dossiers': int(export_dossiers_cnt),
                'total_val_cfa': float(export_val),
                'total_poids_net': float(export_weight),
                'total_qty': float(export_qty),
                'avg_val_dossier': float(export_val / max(export_dossiers_cnt, 1))
            },
            'geography': {
                'region_val_split': {k: float(v) for k, v in export_region_split.items()},
                'region_shares': export_region_shares,
                'country_stats': export_stats_list
            },
            'logistics': {
                'mode_split': {str(k): int(v) for k, v in export_mode_split.items()}
            },
            'time_decomposition': {
                'month': {str(k): int(v) for k, v in export_month_counts.items()}
            },
            'top_products': export_top_prod_list
        }
    }
    
    static_dir = 'data/static' if os.path.isdir('data/static') else '.'
    json_path = os.path.join(static_dir, 'dashboard_data.json')
    js_path = os.path.join(static_dir, 'data.js')
    
    with open(json_path, 'w', encoding='utf-8') as json_f:
        json.dump(dashboard_data, json_f, indent=4, ensure_ascii=False)

    with open(js_path, 'w', encoding='utf-8') as js_f:
        js_f.write("window.dashboardData = " + json.dumps(dashboard_data, indent=4, ensure_ascii=False) + ";")
        
    conn.close()
    logging.info("=== ADVANCED ANALYSIS & MODELING COMPLETE. JSON STATS SAVED TO dashboard_data.json AND data.js ===")

if __name__ == "__main__":
    main()
