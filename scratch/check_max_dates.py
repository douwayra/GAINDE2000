import os
import pymssql

server = os.getenv("MSSQL_SERVER", "192.168.2.138")
user = os.getenv("MSSQL_USER", "DataAnalyse")
password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")

conn = pymssql.connect(server=server, user=user, password=password, database=database)
cur = conn.cursor()

print("--- Last records details by year ---")
for y in [2022, 2023, 2024, 2025]:
    cur.execute(f"SELECT MIN(DATEDOSSIERTPS), MAX(DATEDOSSIERTPS), COUNT(*) FROM DOSSIERTPS WHERE YEAR(DATEDOSSIERTPS) = {y}")
    row = cur.fetchone()
    print(f"Year {y}: Min Date: {row[0]}, Max Date: {row[1]}, Total: {row[2]} dossiers")

cur.close()
conn.close()
