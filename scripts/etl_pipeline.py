#!/usr/bin/env python3
"""
PIPELINE ETL DOUANIÈRE - GAINDE 2000 / ORBUS
Ce script automatise la détection, le nettoyage, la fusion et la validation 
des données de douane (Dossiers, Factures, Articles) pour toutes les périodes (2020-2026).
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("etl_pipeline.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Noms des colonnes de référence pour la table Articles
ARTICLES_HEADERS = [
    'IDTPSFACTURE', 'NUMEROTARIFDOUANE', 'NUMERODOSSIERTPS', 'DESIGNATIONCOMMERCIALE',
    'PAYSPROVENANCE', 'PAYSORIGINE', 'PAYSDESTINATION', 'UNITEMESURE', 'QUANTITEMESURE',
    'POIDSNET', 'POIDSBRUT', 'VALEURUNITAIRECFA', 'VALEURCFA', 'VALEURUNITAIREDEVISE',
    'VALEURDEVISE', 'VALEURUNITAIREFOBCFA', 'VALEURFOBCFA', 'VALEURUNITAIREFOBDEVISE',
    'VALEURFOBDEVISE', 'ORDRE'
]

# Colonnes clés pour Facture
FACTURES_COLMAP = {
    0: 'IDTPSFACTURE', 1: 'NUMERODOSSIERTPS', 2: 'DEVISE', 3: 'TYPE_FACTURE',
    4: 'NUMERO_FACTURE', 5: 'DATE_FACTURE', 6: 'NOM_EXPORTATEUR', 7: 'ADRESSE_EXPORTATEUR',
    8: 'TEL_EXPORTATEUR', 9: 'FAX_EXPORTATEUR', 10: 'EMAIL_EXPORTATEUR', 11: 'VILLE_EXPORTATEUR',
    12: 'PAYS_EXPORTATEUR', 13: 'CP_EXPORTATEUR', 14: 'BP_EXPORTATEUR', 15: 'VALEUR_FOB_DEVISE',
    16: 'VALEUR_FOB_CFA', 17: 'FRAIS_FRET_DEVISE', 18: 'FRAIS_ASSURANCE_DEVISE',
    19: 'AUTRES_FRAIS_DEVISE', 20: 'VALEUR_TOTAL_DEVISE', 21: 'VALEUR_TOTAL_CFA',
    22: 'INCOTERM', 23: 'MODE_REGLEMENT', 25: 'PAYS_BANQUE', 26: 'PAYS_PROVENANCE',
    28: 'MODE_PAIEMENT', 29: 'INCOTERM_LIVRAISON', 30: 'VALEUR_FRET_CFA',
    32: 'VALEUR_ASSURANCE_CFA', 34: 'VALEUR_AUTRES_FRAIS_CFA',
    54: 'VALEUR_FACTURE_DEVISE_FINAL', 55: 'VALEUR_FACTURE_CFA_FINAL', 56: 'PAYS_DESTINATION'
}

# Colonnes clés pour Dossiers
DOSSIERS_COLMAP = {
    0: 'NUMERODOSSIERTPS', 1: 'ID_SEQUENCE_DOSSIER', 2: 'TYPE_OPERATION', 3: 'DATE_CREATION',
    4: 'STATUT_DOSSIER', 6: 'NOM_NAVIRE', 7: 'MODE_TRANSPORT', 8: 'PAYS_PROVENANCE',
    9: 'VILLE_PROVENANCE', 11: 'NOM_IMPORTATEUR', 14: 'ADRESSE_IMPORTATEUR',
    15: 'TEL_IMPORTATEUR', 16: 'FAX_IMPORTATEUR', 18: 'VILLE_IMPORTATEUR',
    19: 'PAYS_IMPORTATEUR', 20: 'NINEA_IMPORTATEUR', 24: 'REGIME_DOUANIER',
    27: 'BANQUE', 29: 'ASSURANCE', 35: 'TYPE_CONTENEUR', 41: 'TYPE_POLICE',
    44: 'STATUT_COMPLETUDE', 58: 'DATE_SOUMISSION', 60: 'IP_CLIENT', 61: 'IP_SERVEUR',
    69: 'SCRIPT_PAGE'
}

def detect_file_type(filepath):
    """
    Analyse un fichier CSV pour détecter automatiquement son type 
    selon le nombre de colonnes et son séparateur.
    """
    try:
        # Tenter de lire la première ligne
        with open(filepath, 'r', encoding='latin1') as f:
            first_line = f.readline()
        
        # Détecter le séparateur
        sep = ';' if ';' in first_line else ','
        
        # Compter le nombre de colonnes dans la première ligne
        cols = len(first_line.split(sep))
        
        if cols == 20:
            return 'ARTICLES', sep
        elif cols == 57:
            return 'FACTURES', sep
        elif cols == 73:
            return 'DOSSIERS', sep
        else:
            return 'INCONNU', sep
    except Exception as e:
        logging.error(f"Erreur lors de la détection du type de fichier {filepath} : {e}")
        return 'ERREUR', ';'

def clean_text_series(series):
    """Nettoie une série textuelle (strip, NaN conversion)."""
    return series.astype(str).str.strip().replace({'NULL': np.nan, 'null': np.nan, 'nan': np.nan, '': np.nan})

def convert_numeric_series(series):
    """Nettoie et convertit une série en numérique (gestion virgule décimale)."""
    clean_series = series.astype(str).str.replace(',', '.', regex=False)
    return pd.to_numeric(clean_series, errors='coerce')

def process_articles(filepaths, sep_map):
    """Nettoie et fusionne tous les fichiers d'articles détectés."""
    logging.info(f"Début du traitement des articles ({len(filepaths)} fichiers détectés)...")
    dfs = []
    
    for path in filepaths:
        sep = sep_map[path]
        logging.info(f"Lecture de l'article : {path}...")
        
        # Déterminer si le fichier a des en-têtes valides
        try:
            temp_df = pd.read_csv(path, sep=sep, nrows=2, encoding='utf-8-sig')
            has_header = 'IDTPSFACTURE' in [c.strip().replace('ï»¿', '') for c in temp_df.columns]
        except Exception:
            has_header = False
        
        try:
            if has_header:
                df = pd.read_csv(path, sep=sep, encoding='utf-8-sig', low_memory=False, dtype=str)
                df.columns = [c.strip().replace('ï»¿', '') for c in df.columns]
            else:
                df = pd.read_csv(path, sep=sep, header=None, encoding='latin1', low_memory=False, dtype=str)
                # S'assurer d'aligner le nombre de colonnes
                if df.shape[1] == len(ARTICLES_HEADERS):
                    df.columns = ARTICLES_HEADERS
                else:
                    logging.warning(f"Le fichier {path} a {df.shape[1]} colonnes au lieu de 20. Ignoré.")
                    continue
        except Exception as e:
            logging.error(f"Erreur de lecture du fichier d'articles {path} : {e}")
            continue
            
        dfs.append(df)
        
    if not dfs:
        return None
        
    all_art = pd.concat(dfs, ignore_index=True)
    logging.info(f"Articles fusionnés. Lignes initiales : {len(all_art):,}")
    
    # Nettoyage des chaînes et des ID
    for col in ARTICLES_HEADERS:
        if col in all_art.columns:
            all_art[col] = clean_text_series(all_art[col])
            
    # Conversion des numériques
    num_cols = [
        'QUANTITEMESURE', 'POIDSNET', 'POIDSBRUT', 'VALEURUNITAIRECFA', 'VALEURCFA',
        'VALEURUNITAIREDEVISE', 'VALEURDEVISE', 'VALEURUNITAIREFOBCFA', 'VALEURFOBCFA',
        'VALEURUNITAIREFOBDEVISE', 'VALEURFOBDEVISE', 'ORDRE'
    ]
    for col in num_cols:
        if col in all_art.columns:
            all_art[col] = convert_numeric_series(all_art[col])
            
    # Convertir clés en numérique
    all_art['IDTPSFACTURE'] = pd.to_numeric(all_art['IDTPSFACTURE'], errors='coerce')
    all_art['NUMERODOSSIERTPS'] = pd.to_numeric(all_art['NUMERODOSSIERTPS'], errors='coerce')
    
    # Élimination des doublons
    dups = all_art.duplicated().sum()
    if dups > 0:
        logging.info(f"Suppression de {dups:,} doublons exacts.")
        all_art = all_art.drop_duplicates()
        
    logging.info(f"Fin du traitement des articles. Lignes nettoyées : {len(all_art):,}")
    return all_art

def process_factures(filepaths, sep_map):
    """Nettoie et fusionne tous les fichiers de factures détectés."""
    logging.info(f"Début du traitement des factures ({len(filepaths)} fichiers détectés)...")
    dfs = []
    
    for path in filepaths:
        sep = sep_map[path]
        logging.info(f"Lecture des factures : {path}...")
        try:
            df = pd.read_csv(path, sep=sep, header=None, encoding='latin1', low_memory=False, dtype=str)
        except Exception as e:
            logging.error(f"Erreur de lecture du fichier factures {path} : {e}")
            continue
            
        # Assigner les colonnes selon la map
        new_cols = [FACTURES_COLMAP[i] if i in FACTURES_COLMAP else f'col_{i}' for i in range(df.shape[1])]
        df.columns = new_cols
        dfs.append(df)
        
    if not dfs:
        return None
        
    all_fac = pd.concat(dfs, ignore_index=True)
    logging.info(f"Factures fusionnées. Lignes initiales : {len(all_fac):,}")
    
    # Supprimer les BOM si présents en Col 0
    all_fac['IDTPSFACTURE'] = all_fac['IDTPSFACTURE'].astype(str).str.replace('ï»¿', '', regex=False)
    
    # Nettoyage des textes
    for col in all_fac.columns:
        all_fac[col] = clean_text_series(all_fac[col])
        
    # Conversion des valeurs numériques
    num_cols = [
        'VALEUR_FOB_DEVISE', 'VALEUR_FOB_CFA', 'FRAIS_FRET_DEVISE', 'FRAIS_ASSURANCE_DEVISE',
        'AUTRES_FRAIS_DEVISE', 'VALEUR_TOTAL_DEVISE', 'VALEUR_TOTAL_CFA', 'VALEUR_FRET_CFA',
        'VALEUR_ASSURANCE_CFA', 'VALEUR_AUTRES_FRAIS_CFA', 'VALEUR_FACTURE_DEVISE_FINAL',
        'VALEUR_FACTURE_CFA_FINAL'
    ]
    for col in num_cols:
        if col in all_fac.columns:
            all_fac[col] = convert_numeric_series(all_fac[col])
            
    all_fac['IDTPSFACTURE'] = pd.to_numeric(all_fac['IDTPSFACTURE'], errors='coerce')
    all_fac['NUMERODOSSIERTPS'] = pd.to_numeric(all_fac['NUMERODOSSIERTPS'], errors='coerce')
    
    # Supprimer doublons
    dups = all_fac.duplicated().sum()
    if dups > 0:
        logging.info(f"Suppression de {dups:,} doublons factures.")
        all_fac = all_fac.drop_duplicates()
        
    logging.info(f"Fin du traitement des factures. Lignes nettoyées : {len(all_fac):,}")
    return all_fac

def process_dossiers(filepaths, sep_map):
    """Nettoie et fusionne tous les fichiers de dossiers détectés."""
    logging.info(f"Début du traitement des dossiers ({len(filepaths)} fichiers détectés)...")
    dfs = []
    
    for path in filepaths:
        sep = sep_map[path]
        logging.info(f"Lecture des dossiers : {path}...")
        try:
            df = pd.read_csv(path, sep=sep, header=None, encoding='latin1', low_memory=False, dtype=str)
        except Exception as e:
            logging.error(f"Erreur de lecture du fichier dossiers {path} : {e}")
            continue
            
        new_cols = [DOSSIERS_COLMAP[i] if i in DOSSIERS_COLMAP else f'col_{i}' for i in range(df.shape[1])]
        df.columns = new_cols
        dfs.append(df)
        
    if not dfs:
        return None
        
    all_dos = pd.concat(dfs, ignore_index=True)
    logging.info(f"Dossiers fusionnés. Lignes initiales : {len(all_dos):,}")
    
    # Nettoyage
    all_dos['NUMERODOSSIERTPS'] = all_dos['NUMERODOSSIERTPS'].astype(str).str.replace('ï»¿', '', regex=False)
    for col in all_dos.columns:
        all_dos[col] = clean_text_series(all_dos[col])
        
    all_dos['NUMERODOSSIERTPS'] = pd.to_numeric(all_dos['NUMERODOSSIERTPS'], errors='coerce')
    
    # Supprimer doublons
    dups = all_dos.duplicated().sum()
    if dups > 0:
        logging.info(f"Suppression de {dups:,} doublons dossiers.")
        all_dos = all_dos.drop_duplicates()
        
    logging.info(f"Fin du traitement des dossiers. Lignes nettoyées : {len(all_dos):,}")
    return all_dos

def run_validations(articles, factures, dossiers):
    """Valide les liaisons et la cohérence des bases de données."""
    logging.info("Exécution des contrôles de cohérence croisés...")
    
    art_ids = set(articles['IDTPSFACTURE'].dropna().astype(int))
    fac_ids = set(factures['IDTPSFACTURE'].dropna().astype(int))
    matching_invoices = art_ids.intersection(fac_ids)
    
    logging.info(f"Factures uniques dans les Articles : {len(art_ids):,}")
    logging.info(f"Factures uniques dans la table Factures : {len(fac_ids):,}")
    logging.info(f"Taux de correspondance Factures : {len(matching_invoices)/max(len(art_ids), 1)*100:.2f}%")
    
    fac_dos = set(factures['NUMERODOSSIERTPS'].dropna().astype(int))
    dos_dos = set(dossiers['NUMERODOSSIERTPS'].dropna().astype(int))
    matching_dossiers = fac_dos.intersection(dos_dos)
    
    logging.info(f"Dossiers uniques dans les Factures : {len(fac_dos):,}")
    logging.info(f"Dossiers uniques dans la table Dossiers : {len(dos_dos):,}")
    logging.info(f"Taux de correspondance Dossiers : {len(matching_dossiers)/max(len(fac_dos), 1)*100:.2f}%")

def main():
    start_time = datetime.now()
    logging.info("=== DÉMARRAGE DE LA PIPELINE ETL ===")
    
    # Créer le répertoire de destination
    output_dir = 'cleaned_data'
    os.makedirs(output_dir, exist_ok=True)
    
    # Scan des fichiers dans le répertoire actuel
    all_files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.csv') and f != 'articles_clean_all.csv']
    logging.info(f"Fichiers CSV détectés dans le dossier racine : {all_files}")
    
    classified_files = {'ARTICLES': [], 'FACTURES': [], 'DOSSIERS': []}
    sep_map = {}
    
    for f in all_files:
        ftype, sep = detect_file_type(f)
        sep_map[f] = sep
        if ftype in classified_files:
            classified_files[ftype].append(f)
            logging.info(f"Fichier : {f} ➔ Détecté comme : {ftype} (Séparateur: '{sep}')")
        else:
            logging.warning(f"Fichier : {f} ➔ Non reconnu ou ignoré.")
            
    # Traitement séquentiel
    articles_df = None
    factures_df = None
    dossiers_df = None
    
    if classified_files['ARTICLES']:
        articles_df = process_articles(classified_files['ARTICLES'], sep_map)
        if articles_df is not None:
            articles_df.to_csv(os.path.join(output_dir, 'articles_clean.csv'), index=False, encoding='utf-8')
            logging.info(f"Sauvegardé : {os.path.join(output_dir, 'articles_clean.csv')}")
            
    if classified_files['FACTURES']:
        factures_df = process_factures(classified_files['FACTURES'], sep_map)
        if factures_df is not None:
            factures_df.to_csv(os.path.join(output_dir, 'factures_clean.csv'), index=False, encoding='utf-8')
            logging.info(f"Sauvegardé : {os.path.join(output_dir, 'factures_clean.csv')}")
            
    if classified_files['DOSSIERS']:
        dossiers_df = process_dossiers(classified_files['DOSSIERS'], sep_map)
        if dossiers_df is not None:
            dossiers_df.to_csv(os.path.join(output_dir, 'dossiers_clean.csv'), index=False, encoding='utf-8')
            logging.info(f"Sauvegardé : {os.path.join(output_dir, 'dossiers_clean.csv')}")
            
    # Valider si toutes les tables sont prêtes
    if articles_df is not None and factures_df is not None and dossiers_df is not None:
        run_validations(articles_df, factures_df, dossiers_df)
    else:
        logging.warning("Certaines tables manquent pour exécuter la validation croisée complète.")
        
    duration = datetime.now() - start_time
    logging.info(f"=== PIPELINE ETL TERMINÉE EN {duration.total_seconds():.2f} SECONDES ===")

if __name__ == "__main__":
    main()
