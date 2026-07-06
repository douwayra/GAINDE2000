#!/usr/bin/env python3
"""
⚡ PIPELINE ETL HAUTE PERFORMANCE (POLARS + DUCKDB)
Ce script utilise Polars (moteur Rust multi-threadé) et DuckDB (BD analytique)
pour nettoyer et stocker plus de 1.8M de lignes en quelques secondes.
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv

load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

try:
    import polars as pl
    import duckdb
except ImportError:
    logging.error("Les packages requis (polars, duckdb, pyarrow) ne sont pas installés.")
    logging.info("Veuillez installer la stack haute performance via : pip3 install polars duckdb pyarrow")
    sys.exit(1)

ARTICLES_HEADERS = [
    'IDTPSFACTURE', 'NUMEROTARIFDOUANE', 'NUMERODOSSIERTPS', 'DESIGNATIONCOMMERCIALE',
    'PAYSPROVENANCE', 'PAYSORIGINE', 'PAYSDESTINATION', 'UNITEMESURE', 'QUANTITEMESURE',
    'POIDSNET', 'POIDSBRUT', 'VALEURUNITAIRECFA', 'VALEURCFA', 'VALEURUNITAIREDEVISE',
    'VALEURDEVISE', 'VALEURUNITAIREFOBCFA', 'VALEURFOBCFA', 'VALEURUNITAIREFOBDEVISE',
    'VALEURFOBDEVISE', 'ORDRE'
]

FACTURES_COLUMNS = [
    'IDTPSFACTURE', 'NUMERODOSSIERTPS', 'DEVISE', 'TYPE_FACTURE', 'NUMERO_FACTURE',
    'DATE_FACTURE', 'NOM_EXPORTATEUR', 'ADRESSE_EXPORTATEUR', 'TEL_EXPORTATEUR', 'FAX_EXPORTATEUR',
    'EMAIL_EXPORTATEUR', 'VILLE_EXPORTATEUR', 'PAYS_EXPORTATEUR', 'CP_EXPORTATEUR', 'BP_EXPORTATEUR',
    'VALEUR_FOB_DEVISE', 'VALEUR_FOB_CFA', 'FRAIS_FRET_DEVISE', 'FRAIS_ASSURANCE_DEVISE',
    'AUTRES_FRAIS_DEVISE', 'VALEUR_TOTAL_DEVISE', 'VALEUR_TOTAL_CFA', 'INCOTERM', 'MODE_REGLEMENT',
    'col_24', 'PAYS_BANQUE', 'PAYS_PROVENANCE', 'col_27', 'MODE_PAIEMENT', 'INCOTERM_LIVRAISON',
    'VALEUR_FRET_CFA', 'col_31', 'VALEUR_ASSURANCE_CFA', 'col_33', 'VALEUR_AUTRES_FRAIS_CFA'
] + [f'col_{i}' for i in range(35, 54)] + [
    'VALEUR_FACTURE_DEVISE_FINAL', 'VALEUR_FACTURE_CFA_FINAL', 'PAYS_DESTINATION'
]

DOSSIERS_COLUMNS = [
    'NUMERODOSSIERTPS', 'ID_SEQUENCE_DOSSIER', 'TYPE_OPERATION', 'DATE_CREATION',
    'STATUT_DOSSIER', 'col_5', 'NOM_NAVIRE', 'MODE_TRANSPORT', 'PAYS_PROVENANCE',
    'VILLE_PROVENANCE', 'col_10', 'NOM_IMPORTATEUR', 'col_12', 'col_13', 'ADRESSE_IMPORTATEUR',
    'TEL_IMPORTATEUR', 'FAX_IMPORTATEUR', 'col_17', 'VILLE_IMPORTATEUR', 'PAYS_IMPORTATEUR',
    'NINEA_IMPORTATEUR'
] + [f'col_{i}' for i in range(21, 24)] + ['REGIME_DOUANIER', 'col_25', 'col_26', 'BANQUE', 'col_28', 'ASSURANCE'] + \
[f'col_{i}' for i in range(30, 35)] + ['TYPE_CONTENEUR'] + [f'col_{i}' for i in range(36, 41)] + \
['TYPE_POLICE'] + [f'col_{i}' for i in range(42, 44)] + ['STATUT_COMPLETUDE'] + [f'col_{i}' for i in range(45, 58)] + \
['DATE_SOUMISSION', 'col_59', 'IP_CLIENT', 'IP_SERVEUR'] + [f'col_{i}' for i in range(62, 69)] + ['SCRIPT_PAGE'] + \
[f'col_{i}' for i in range(70, 73)]

def detect_file_type(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
    sep = ';' if ';' in first_line else ','
    cols = len(first_line.split(sep))
    if cols == 20:
        return 'ARTICLES', sep
    elif cols == 57:
        return 'FACTURES', sep
    elif cols == 73:
        return 'DOSSIERS', sep
    return 'INCONNU', sep

def clean_dataframe(df, text_cols, numeric_cols, key_cols):
    import html
    # Remplacement des textes NULL par de vrais nulls, nettoyage des espaces, normalisation de DEVISE et MODE_TRANSPORT
    for col in text_cols:
        if col in df.columns:
            # 1. Nettoyage des espaces et nulls
            df = df.with_columns(
                pl.col(col).str.strip_chars().replace(["NULL", "null", "nan", ""], None)
            )
            # 2. Unescape des entités HTML (ex: &eacute; ou &#233;)
            df = df.with_columns(
                pl.col(col).map_elements(html.unescape, return_dtype=pl.String, skip_nulls=True)
            )
            # 3. Normalisation des écritures corrompues (Sénégal et types de conteneurs)
            cleanup_map = {
                "Sï¿½nï¿½gal": "Sénégal",
                "S¨¦n¨¦gal": "Sénégal",
                "S¡§¦n¡§¦gal": "Sénégal",
                "S¡§&brvbar;n¡§&brvbar;gal": "Sénégal",
                "Senegal": "Sénégal",
                "Sénéga": "Sénégal",
                "SÃ©nÃ©gal": "Sénégal",
                "FCL - Conteneur personnalisï¿½": "FCL - Conteneur personnalisé",
                "FCL - Conteneur personnalis„1¤7": "FCL - Conteneur personnalisé",
                "FCL - Conteneur personnalis&eacute;": "FCL - Conteneur personnalisé",
                "FCL-Conteneur personnalise": "FCL - Conteneur personnalisé",
                "FCL - conteneur personalisé": "FCL - Conteneur personnalisé",
                "FCL- conteneur personalisé": "FCL - Conteneur personnalisé",
                "FCL conteneur personnalisé": "FCL - Conteneur personnalisé"
            }
            df = df.with_columns(
                pl.col(col).replace(cleanup_map, default=pl.col(col))
            )
            
            # 4. Normalisation des colonnes spécifiques
            if col == 'DEVISE':
                df = df.with_columns(
                    pl.col(col).str.to_uppercase()
                    .replace({"NULL": None, "null": None, "nan": None, "": None, "EURO": "EUR"})
                )
            elif col == 'MODE_TRANSPORT':
                # Map categories: Air, Mer, Route, Fer, Contener-Mer, Contener-Route, Contener-Air, Autres
                # First clean, strip, and upper
                df = df.with_columns(
                    pl.col(col).str.to_uppercase()
                )
                transport_map = {
                    'MER': 'Mer', 'MARITIME': 'Mer', 'BATEAU': 'Mer', 'M': 'Mer',
                    'AIR': 'Air', 'AVION': 'Air', 'AERIEN': 'Air', 'AI': 'Air',
                    'ROUTE': 'Route', 'ROUTIER': 'Route',
                    'FER': 'Fer', 'CHEMIN DE FER': 'Fer',
                    'CONTENER-MER': 'Contener-Mer', 'CONTENER - MER': 'Contener-Mer',
                    'CONTENER-ROUTE': 'Contener-Route', 'CONTENER - ROUTE': 'Contener-Route',
                    'CONTENER-AIR': 'Contener-Air', 'CONTENER - AIR': 'Contener-Air',
                    'AUTRES': 'Autres', 'AUTRE': 'Autres'
                }
                df = df.with_columns(
                    pl.col(col).replace_strict(transport_map, default=pl.col(col).str.to_titlecase())
                    .replace({"NULL": None, "null": None, "nan": None, "": None})
                )
            elif col == 'TYPE_OPERATION':
                # Map operation codes: I -> Importation, E -> Exportation, R -> Réexportation, S -> Transit
                df = df.with_columns(
                    pl.col(col).str.to_uppercase()
                )
                op_map = {
                    'I': 'Importation',
                    'E': 'Exportation',
                    'R': 'Réexportation',
                    'S': 'Transit'
                }
                df = df.with_columns(
                    pl.col(col).replace(op_map, default=pl.col(col))
                    .replace({"NULL": None, "null": None, "nan": None, "": None})
                )
            elif col == 'TYPE_FACTURE':
                # Map invoice types and fix typos
                df = df.with_columns(
                    pl.col(col).str.to_titlecase()
                )
                facture_map = {
                    'Proformau': 'Proforma',
                    'Proformam': 'Proforma',
                    'Definitive': 'Définitive'
                }
                df = df.with_columns(
                    pl.col(col).replace(facture_map, default=pl.col(col))
                    .replace({"NULL": None, "null": None, "nan": None, "": None})
                )
            
    # Conversion des décimales (virgule -> point) et cast en Float64
    for col in numeric_cols:
        if col in df.columns:
            df = df.with_columns(
                pl.col(col).str.replace(",", ".", literal=True).cast(pl.Float64, strict=False)
            )
            
    # Cast des clés d'identification
    for col in key_cols:
        if col in df.columns:
            df = df.with_columns(
                pl.col(col).cast(pl.Int64, strict=False)
            )
            
    return df

def validate_data_quality(df, table_name):
    if df is None or df.shape[0] == 0:
        return df, None
        
    rejected_conditions = []
    
    if table_name == "ARTICLES":
        rejected_conditions.append(
            (pl.col("VALEURCFA") <= 0) | 
            (pl.col("POIDSNET") <= 0) | 
            (pl.col("QUANTITEMESURE") <= 0) |
            (pl.col("NUMEROTARIFDOUANE").is_null()) |
            (pl.col("NUMEROTARIFDOUANE").str.len_chars() < 4)
        )
    elif table_name == "FACTURES":
        rejected_conditions.append(
            (pl.col("VALEUR_TOTAL_CFA") <= 0) |
            (pl.col("IDTPSFACTURE").is_null())
        )
    elif table_name == "DOSSIERS":
        rejected_conditions.append(
            (pl.col("NINEA_IMPORTATEUR").is_null()) |
            (pl.col("NUMERODOSSIERTPS").is_null())
        )
        
    if not rejected_conditions:
        return df, None
        
    rej_expr = rejected_conditions[0]
    for cond in rejected_conditions[1:]:
        rej_expr = rej_expr | cond
        
    clean_df = df.filter(~rej_expr)
    rejected_df = df.filter(rej_expr)
    
    return clean_df, rejected_df

def main():
    start_time = time.time()
    logging.info("=== INITIALISATION ETL HAUTE PERFORMANCE (POLARS + DUCKDB) ===")
    
    search_dir = 'data/csv' if os.path.isdir('data/csv') else '.'
    csv_files = [os.path.join(search_dir, f) for f in os.listdir(search_dir) if f.endswith('.csv') and f not in ['articles_clean_all.csv', 'factures_clean.csv', 'entete_dossier_clean.csv']]
    classified = {'ARTICLES': [], 'FACTURES': [], 'DOSSIERS': []}
    sep_map = {}
    df_art_rej = None
    df_fac_rej = None
    df_dos_rej = None
    
    for f in csv_files:
        ftype, sep = detect_file_type(f)
        sep_map[f] = sep
        if ftype in classified:
            classified[ftype].append(f)
            logging.info(f"Fichier : {f} ➔ Détecté : {ftype} (séparateur: '{sep}')")
            
    # 1. Traitement des ARTICLES
    df_art = None
    if classified['ARTICLES']:
        logging.info("Traitement de la table Articles en cours...")
        dfs = []
        for path in classified['ARTICLES']:
            sep = sep_map[path]
            # Lire en mode String avec Polars
            df = pl.read_csv(path, separator=sep, has_header=True, infer_schema_length=0, encoding='utf-8-sig')
            
            # Si pas de header détecté, recharger sans header
            if 'IDTPSFACTURE' not in [c.replace('ï»¿', '') for c in df.columns]:
                df = pl.read_csv(path, separator=sep, has_header=False, infer_schema_length=0, encoding='utf-8-sig')
                if df.shape[1] == 20:
                    df.columns = ARTICLES_HEADERS
            else:
                df.columns = [c.replace('ï»¿', '') for c in df.columns]
                
            dfs.append(df)
            
        df_art = pl.concat(dfs)
        df_art = df_art.with_columns(pl.col(df_art.columns[0]).str.replace('ï»¿', ''))
        
        # Nettoyage
        num_cols = [
            'QUANTITEMESURE', 'POIDSNET', 'POIDSBRUT', 'VALEURUNITAIRECFA', 'VALEURCFA',
            'VALEURUNITAIREDEVISE', 'VALEURDEVISE', 'VALEURUNITAIREFOBCFA', 'VALEURFOBCFA',
            'VALEURUNITAIREFOBDEVISE', 'VALEURFOBDEVISE', 'ORDRE'
        ]
        df_art = clean_dataframe(df_art, ARTICLES_HEADERS, num_cols, ['IDTPSFACTURE', 'NUMERODOSSIERTPS'])
        df_art = df_art.unique()
        df_art, df_art_rej = validate_data_quality(df_art, "ARTICLES")
        logging.info(f"Articles traités : {df_art.shape[0]:,} lignes. Rejetés : {df_art_rej.shape[0] if df_art_rej is not None else 0} lignes.")

    # 2. Traitement des FACTURES
    df_fac = None
    df_fac_rej = None
    if classified['FACTURES']:
        logging.info("Traitement de la table Factures en cours...")
        dfs = []
        for path in classified['FACTURES']:
            sep = sep_map[path]
            df = pl.read_csv(path, separator=sep, has_header=False, infer_schema_length=0, encoding='utf-8-sig')
            if df.shape[1] == 57:
                df.columns = FACTURES_COLUMNS
                dfs.append(df)
        df_fac = pl.concat(dfs)
        df_fac = df_fac.with_columns(pl.col(df_fac.columns[0]).str.replace('ï»¿', ''))
        
        num_cols = [
            'VALEUR_FOB_DEVISE', 'VALEUR_FOB_CFA', 'FRAIS_FRET_DEVISE', 'FRAIS_ASSURANCE_DEVISE',
            'AUTRES_FRAIS_DEVISE', 'VALEUR_TOTAL_DEVISE', 'VALEUR_TOTAL_CFA', 'VALEUR_FRET_CFA',
            'VALEUR_ASSURANCE_CFA', 'VALEUR_AUTRES_FRAIS_CFA', 'VALEUR_FACTURE_DEVISE_FINAL',
            'VALEUR_FACTURE_CFA_FINAL'
        ]
        df_fac = clean_dataframe(df_fac, FACTURES_COLUMNS, num_cols, ['IDTPSFACTURE', 'NUMERODOSSIERTPS'])
        df_fac = df_fac.unique()
        df_fac, df_fac_rej = validate_data_quality(df_fac, "FACTURES")
        logging.info(f"Factures traitées : {df_fac.shape[0]:,} lignes. Rejetés : {df_fac_rej.shape[0] if df_fac_rej is not None else 0} lignes.")

    # 3. Traitement des DOSSIERS
    df_dos = None
    df_dos_rej = None
    if classified['DOSSIERS']:
        logging.info("Traitement de la table Dossiers en cours...")
        dfs = []
        for path in classified['DOSSIERS']:
            sep = sep_map[path]
            df = pl.read_csv(path, separator=sep, has_header=False, infer_schema_length=0, encoding='utf-8-sig')
            if df.shape[1] == 73:
                df.columns = DOSSIERS_COLUMNS
                dfs.append(df)
        df_dos = pl.concat(dfs)
        df_dos = df_dos.with_columns(pl.col(df_dos.columns[0]).str.replace('ï»¿', ''))
        df_dos = clean_dataframe(df_dos, DOSSIERS_COLUMNS, [], ['NUMERODOSSIERTPS'])
        df_dos = df_dos.unique()
        df_dos, df_dos_rej = validate_data_quality(df_dos, "DOSSIERS")
        logging.info(f"Dossiers traités : {df_dos.shape[0]:,} lignes. Rejetés : {df_dos_rej.shape[0] if df_dos_rej is not None else 0} lignes.")

    # 4. Stockage dans DUCKDB
    db_path = os.getenv('DB_DOUANE_PATH', 'data/db/gainde_douane.db')
    logging.info(f"Création et écriture dans la base DuckDB : {db_path}...")
    if os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = duckdb.connect(db_path)
    
    if df_art is not None:
        conn.execute("CREATE OR REPLACE TABLE articles AS SELECT * FROM df_art")
        art_path = os.path.join(search_dir, 'articles_clean_all.csv') if search_dir != '.' else 'articles_clean_all.csv'
        df_art.write_csv(art_path)
        logging.info(f"Sauvegardé : {art_path}")
    if df_art_rej is not None and df_art_rej.shape[0] > 0:
        conn.execute("CREATE OR REPLACE TABLE rejected_articles AS SELECT * FROM df_art_rej")
        logging.info(f"Sauvegardé : rejected_articles ({df_art_rej.shape[0]} lignes)")
        
    if df_fac is not None:
        conn.execute("CREATE OR REPLACE TABLE factures AS SELECT * FROM df_fac")
        fac_path = os.path.join(search_dir, 'factures_clean.csv') if search_dir != '.' else 'factures_clean.csv'
        df_fac.write_csv(fac_path)
        logging.info(f"Sauvegardé : {fac_path}")
    if df_fac_rej is not None and df_fac_rej.shape[0] > 0:
        conn.execute("CREATE OR REPLACE TABLE rejected_factures AS SELECT * FROM df_fac_rej")
        logging.info(f"Sauvegardé : rejected_factures ({df_fac_rej.shape[0]} lignes)")
        
    if df_dos is not None:
        conn.execute("CREATE OR REPLACE TABLE dossiers AS SELECT * FROM df_dos")
        dos_path = os.path.join(search_dir, 'entete_dossier_clean.csv') if search_dir != '.' else 'entete_dossier_clean.csv'
        df_dos.write_csv(dos_path)
        logging.info(f"Sauvegardé : {dos_path}")
    if df_dos_rej is not None and df_dos_rej.shape[0] > 0:
        conn.execute("CREATE OR REPLACE TABLE rejected_dossiers AS SELECT * FROM df_dos_rej")
        logging.info(f"Sauvegardé : rejected_dossiers ({df_dos_rej.shape[0]} lignes)")
        
    logging.info("Données insérées avec succès dans DuckDB.")
    
    # 5. Validation croisée ultra-rapide avec SQL dans DuckDB
    logging.info("Exécution des requêtes de cohérence SQL...")
    
    match_fac = conn.execute("""
        SELECT (SELECT COUNT(DISTINCT IDTPSFACTURE) FROM articles WHERE IDTPSFACTURE IN (SELECT IDTPSFACTURE FROM factures)) * 100.0 / COUNT(DISTINCT IDTPSFACTURE) 
        FROM articles
    """).fetchone()[0]
    logging.info(f"Taux de correspondance Articles ➔ Factures (SQL) : {match_fac:.2f}%")
    
    match_dos = conn.execute("""
        SELECT (SELECT COUNT(DISTINCT NUMERODOSSIERTPS) FROM factures WHERE NUMERODOSSIERTPS IN (SELECT NUMERODOSSIERTPS FROM dossiers)) * 100.0 / COUNT(DISTINCT NUMERODOSSIERTPS) 
        FROM factures
    """).fetchone()[0]
    logging.info(f"Taux de correspondance Factures ➔ Dossiers (SQL) : {match_dos:.2f}%")
    
    conn.close()
    
    duration = time.time() - start_time
    logging.info(f"=== PIPELINE HAUTE PERFORMANCE DUCKDB TERMINÉE EN {duration:.2f} SECONDES ===")

if __name__ == "__main__":
    main()
