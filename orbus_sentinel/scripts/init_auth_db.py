#!/usr/bin/env python3
import sqlite3
import bcrypt

def main():
    db_path = "data/db/users.db"
    print(f"Initialisation de la base de données : {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            bureau_douane TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marked_dossiers (
            dossier_num TEXT PRIMARY KEY,
            marked_by TEXT,
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            client_ip TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    test_users = [
        ("admin", "adminpassword", "admin", None),
        ("manager", "P@sser1234", "direction", None),
        ("direction", "directionpassword", "direction", None),
        ("inspecteur_dkp", "inspecteurpassword", "inspecteur", "DKP"),
        ("inspecteur_aibd", "inspecteurpassword", "inspecteur", "AIBD"),
        ("transitaire_cargolink", "transitairepassword", "transitaire", "1234567"),
        ("banque_sgbs", "partenairepassword", "partenaire", "SGBS"),
        ("assurance_axa", "partenairepassword", "partenaire", "AXA"),
        ("chercheur", "statisticienpassword", "statisticien", None),
        ("presse", "journalistepassword", "journaliste", None)
    ]
    
    for username, raw_password, role, bureau in test_users:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')
        cursor.execute("INSERT OR REPLACE INTO users (username, password_hash, role, bureau_douane) VALUES (?, ?, ?, ?)",
                       (username, hashed, role, bureau))
        print(f"Utilisateur configuré : {username} (Rôle: {role}, Bureau: {bureau})")
        
    conn.commit()
    conn.close()
    print("Initialisation terminée avec succès !")

if __name__ == "__main__":
    main()
