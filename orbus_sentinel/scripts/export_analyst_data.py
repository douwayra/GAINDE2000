import os
import pymssql
import csv

# MSSQL Database configurations
server = os.getenv("MSSQL_SERVER", "192.168.2.138")
user = os.getenv("MSSQL_USER", "DataAnalyse")
password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")

print("Connexion à la base SQL Server...")
conn = pymssql.connect(server=server, user=user, password=password, database=database)
cur = conn.cursor()

# Query to fetch joined dossiers and articles for years 2022 to 2026
query = """
    SELECT 
        d.NUMERODOSSIERTPS,
        d.DATEDOSSIERTPS,
        d.NOMOURAISONSOCIALEBENEFICIAIRE,
        d.NUMERONINEA,
        d.RegimeDouanier,
        d.MODETRANSPORT,
        d.PaysDeProvenance,
        d.BANQUEDOMICILIATION,
        d.ASSUREUR,
        d.NIVEAUEXECUTIONDOSSIERTPS,
        a.DESIGNATIONCOMMERCIALE,
        a.VALEURCFA,
        a.POIDSNET,
        a.QUANTITEMESURE
    FROM DOSSIERTPS d
    LEFT JOIN CONTENIR a ON d.NUMERODOSSIERTPS = a.NUMERODOSSIERTPS
    WHERE YEAR(d.DATEDOSSIERTPS) BETWEEN 2022 AND 2026
    ORDER BY d.DATEDOSSIERTPS DESC
"""

output_path = "export_dossiers_2022_2026.csv"
print("Extraction des données en cours...")

cur.execute(query)

# Write to CSV file with semicolon delimiter (convenient for Excel)
with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    writer.writerow([
        "NUMERODOSSIER", 
        "DATE_CREATION", 
        "NOM_IMPORTATEUR", 
        "NINEA", 
        "REGIME", 
        "MODE_TRANSPORT", 
        "PAYS_PROVENANCE", 
        "BANQUE", 
        "ASSURANCE", 
        "STATUT", 
        "DESIGNATION_ARTICLE", 
        "VALEUR_CFA", 
        "POIDS_NET", 
        "QUANTITE"
    ])
    
    row_count = 0
    for r in cur:
        # Clean and harmonize fields
        num_dos = r[0] or ""
        date_c = str(r[1]) if r[1] else ""
        nom_imp = (r[2] or "INCONNU").strip().upper()
        ninea = (r[3] or "INCONNU").strip()
        regime = (r[4] or "INCONNU").strip()
        mode_t = (r[5] or "INCONNU").strip()
        pays_p = (r[6] or "INCONNU").strip().upper()
        banque = (r[7] or "SANS BANQUE").strip()
        assurance = (r[8] or "SANS ASSURANCE").strip()
        statut = (r[9] or "INCONNU").strip()
        desig = (r[10] or "MARCHANDISES DIVERSES").strip()
        valeur = float(r[11] or 0.0)
        poids = float(r[12] or 0.0)
        qty = float(r[13] or 0.0)
        
        writer.writerow([
            num_dos, date_c, nom_imp, ninea, regime, mode_t, 
            pays_p, banque, assurance, statut, desig, valeur, poids, qty
        ])
        row_count += 1

cur.close()
conn.close()

print(f"Export terminé avec succès ! Fichier écrit : {output_path} ({row_count} lignes exportées).")
