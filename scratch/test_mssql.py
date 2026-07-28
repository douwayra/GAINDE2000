import pymssql

def main():
    server = '192.168.2.138'
    user = 'DataAnalyse'
    password = 'DataAnalyse@2026'
    
    print(f"Connecting to MSSQL server at {server}...")
    try:
        conn = pymssql.connect(server=server, user=user, password=password, timeout=10)
        cursor = conn.cursor()
        print("Connected successfully!")
        
        # Get databases
        cursor.execute("SELECT name FROM sys.databases")
        databases = cursor.fetchall()
        print("\nAvailable Databases:")
        for db in databases:
            print(f"- {db[0]}")
            
        conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    main()
