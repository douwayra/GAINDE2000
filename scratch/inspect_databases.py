import pymssql

def inspect_db(db_name):
    server = '192.168.2.138'
    user = 'DataAnalyse'
    password = 'DataAnalyse@2026'
    
    try:
        conn = pymssql.connect(server=server, user=user, password=password, database=db_name, timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        return f"Error: {e}"

def main():
    databases = [
        "ORBUSANALYTICS",
        "FACTURATION_GAINDE2000",
        "MYORBUS_DB",
        "BD_GESTIONDOSSIERSFTP",
        "BDLOGISTIC",
        "bdOrbusV2",
        "BdPole",
        "BD_VERIFICATIONDOUANE"
    ]
    
    for db in databases:
        print(f"\n--- Tables in database: {db} ---")
        res = inspect_db(db)
        if isinstance(res, list):
            if not res:
                print("No tables found.")
            else:
                # Print tables, look for relevant ones
                relevant = [t for t in res if any(word in t.upper() for word in ["DOSSIER", "FACT", "ART", "DECLARATION"])]
                print(f"Total tables: {len(res)}")
                print(f"Relevant tables: {relevant[:10]}")
                print(f"Other tables sample: {res[:10]}")
        else:
            print(res)

if __name__ == "__main__":
    main()
