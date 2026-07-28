import os
import pymssql

server = os.getenv("MSSQL_SERVER", "192.168.2.138")
user = os.getenv("MSSQL_USER", "DataAnalyse")
password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")

conn = pymssql.connect(server=server, user=user, password=password, database=database)
cur = conn.cursor()

print("--- Sample DATEDOSSIERTPS from DOSSIERTPS ---")
cur.execute("SELECT TOP 20 DATEDOSSIERTPS FROM DOSSIERTPS ORDER BY DATEDOSSIERTPS DESC")
for row in cur.fetchall():
    print(f"DATEDOSSIERTPS: {row[0]}")

print("\n--- Count by year using different methods ---")
cur.execute("""
    SELECT 
        YEAR(DATEDOSSIERTPS) as y,
        COUNT(*) as total,
        SUM(CASE WHEN DATEDOSSIERTPS IS NULL THEN 1 ELSE 0 END) as null_dates
    FROM DOSSIERTPS 
    GROUP BY YEAR(DATEDOSSIERTPS)
    ORDER BY y
""")
for row in cur.fetchall():
    print(f"Year {row[0]}: {row[1]} total (null dates: {row[2]})")

cur.close()
conn.close()
