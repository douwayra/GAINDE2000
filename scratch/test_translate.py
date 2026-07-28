import re

def translate_query(query):
    # 1. Extract and translate LIMIT to TOP
    limit_match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
    if limit_match:
        limit_val = limit_match.group(1)
        query = re.sub(r'LIMIT\s+\d+', '', query, flags=re.IGNORECASE)
        # Insert TOP limit_val after SELECT (and SELECT DISTINCT)
        query = re.sub(r'SELECT\s+(DISTINCT\s+)?', f'SELECT \\1TOP {limit_val} ', query, flags=re.IGNORECASE)
        
    # 2. Table mappings
    query = re.sub(r'\barticles\b', 'CONTENIR', query, flags=re.IGNORECASE)
    query = re.sub(r'\bfactures\b', 'FACTURE', query, flags=re.IGNORECASE)
    query = re.sub(r'\bdossiers\b', 'DOSSIERTPS', query, flags=re.IGNORECASE)
    
    # 3. Column mappings
    col_mappings = {
        'DATE_CREATION': 'DATEDOSSIERTPS',
        'TYPE_OPERATION': 'IMPORTATIONOUEXPORTATION',
        'STATUT_DOSSIER': 'NIVEAUEXECUTIONDOSSIERTPS',
        'MODE_TRANSPORT': 'MODETRANSPORT',
        'NOM_IMPORTATEUR': 'NOMOURAISONSOCIALEBENEFICIAIRE',
        'NINEA_IMPORTATEUR': 'NUMERONINEA',
        'REGIME_DOUANIER': 'RegimeDouanier',
        'BANQUE': 'BANQUEDOMICILIATION',
        'ASSURANCE': 'ASSUREUR',
        'PAYS_PROVENANCE': 'PaysDeProvenance',
        'PAYS_IMPORTATEUR': 'PAYSBENEFICIAIRE',
        'VALEUR_TOTAL_CFA': 'VALEURTOTALECFA',
        'VALEUR_FOB_CFA': 'VALEURFOBTOTALECFA',
        'IP_CLIENT': 'IPCLIENT',
        'IP_SERVEUR': 'IPCLIENT',
        'DATE_SOUMISSION': 'DATEDOSSIERTPS',
        'SCRIPT_PAGE': 'NULL',
        'TYPE_CONTENEUR': 'NULL',
        'TYPE_POLICE': 'NULL',
        'STATUT_COMPLETUDE': 'NULL',
        'ANOMALY_IF': '0',
        'RISK_SCORE': '0.0',
        'RISK_CLASS': "'Faible'"
    }
    
    for old_col, new_col in sorted(col_mappings.items(), key=lambda x: len(x[0]), reverse=True):
        query = re.sub(rf'\b{old_col}\b', new_col, query)
        
    # 4. Function mappings
    query = re.sub(
        r'dayname\s*\(\s*CAST\s*\(\s*substring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*10\s*\)\s*AS\s*DATE\s*\)\s*\)',
        r'DATENAME(weekday, CAST(SUBSTRING(\1, 1, 10) AS DATE))',
        query,
        flags=re.IGNORECASE
    )
    query = re.sub(
        r'monthname\s*\(\s*CAST\s*\(\s*substring\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*1\s*,\s*10\s*\)\s*AS\s*DATE\s*\)\s*\)',
        r'DATENAME(month, CAST(SUBSTRING(\1, 1, 10) AS DATE))',
        query,
        flags=re.IGNORECASE
    )
    
    # 5. Parameter replacements
    query = query.replace('?', '%s')
    
    return query

def main():
    q1 = """
        SELECT 
            COUNT(DISTINCT d.NUMERODOSSIERTPS) AS total_dossiers,
            COUNT(DISTINCT f.IDTPSFACTURE) AS total_factures,
            COUNT(*) AS total_articles,
            SUM(a.VALEURCFA) AS total_val_cfa,
            SUM(a.POIDSNET) AS total_poids_net,
            SUM(a.QUANTITEMESURE) AS total_qty
        FROM articles a
        JOIN factures f ON a.IDTPSFACTURE = f.IDTPSFACTURE
        JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
    """
    
    q2 = """
        SELECT 
            d.PAYS_PROVENANCE, 
            d.TYPE_OPERATION, 
            SUM(a.VALEURCFA) AS val, 
            COUNT(DISTINCT d.NUMERODOSSIERTPS) AS cnt
        FROM articles a
        JOIN factures f ON a.IDTPSFACTURE = f.IDTPSFACTURE
        JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
        WHERE d.PAYS_PROVENANCE = ?
        GROUP BY d.PAYS_PROVENANCE, d.TYPE_OPERATION
    """
    
    q3 = """
        SELECT 
            dayname(CAST(substring(DATE_CREATION, 1, 10) AS DATE)) AS day,
            monthname(CAST(substring(DATE_CREATION, 1, 10) AS DATE)) AS month,
            COUNT(*) AS cnt
        FROM dossiers
    """
    
    q4 = """
        SELECT a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE, SUM(a.VALEURCFA) as val
        FROM articles a
        JOIN factures f ON a.IDTPSFACTURE = f.IDTPSFACTURE
        JOIN dossiers d ON f.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS
        GROUP BY a.NUMEROTARIFDOUANE, a.DESIGNATIONCOMMERCIALE
        ORDER BY val DESC
        LIMIT 15
    """

    print("Q1 translated:\n", translate_query(q1))
    print("\nQ2 translated:\n", translate_query(q2))
    print("\nQ3 translated:\n", translate_query(q3))
    print("\nQ4 translated:\n", translate_query(q4))

if __name__ == "__main__":
    main()
