import os
import pymssql

server = os.getenv("MSSQL_SERVER", "192.168.2.138")
user = os.getenv("MSSQL_USER", "DataAnalyse")
password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")

conn = pymssql.connect(server=server, user=user, password=password, database=database)
cur = conn.cursor()

print("--- Year Breakdown in DOSSIERTPS ---")
cur.execute("SELECT YEAR(DATEDOSSIERTPS), COUNT(*) FROM DOSSIERTPS GROUP BY YEAR(DATEDOSSIERTPS) ORDER BY 1")
for row in cur.fetchall():
    print(f"Year {row[0]}: {row[1]} dossiers")

print("\n--- Year Breakdown in CONTENIR (articles) via DATEDOSSIERTPS ---")
cur.execute("""
    SELECT YEAR(d.DATEDOSSIERTPS), COUNT(DISTINCT d.NUMERODOSSIERTPS), COUNT(*) 
    FROM CONTENIR a 
    JOIN DOSSIERTPS d ON a.NUMERODOSSIERTPS = d.NUMERODOSSIERTPS 
    GROUP BY YEAR(d.DATEDOSSIERTPS) 
    ORDER BY 1
""")
for row in cur.fetchall():
    print(f"Year {row[0]}: {row[1]} unique dossiers, {row[2]} articles")

cur.close()
conn.close()
