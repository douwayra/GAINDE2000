import os
import pymssql

server = os.getenv("MSSQL_SERVER", "192.168.2.138")
user = os.getenv("MSSQL_USER", "DataAnalyse")
password = os.getenv("MSSQL_PASSWORD", "DataAnalyse@2026")
database = os.getenv("MSSQL_DATABASE", "APPLICATIONS")

conn = pymssql.connect(server=server, user=user, password=password, database=database)
cur = conn.cursor()

print("--- Tables in APPLICATIONS Database ---")
cur.execute("""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_NAME
""")
for row in cur.fetchall():
    print(f"- {row[0]}")

cur.close()
conn.close()
