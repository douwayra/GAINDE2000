#!/usr/bin/env python3
import sqlite3
import bcrypt

def main():
    db_path = "data/db/users.db"
    print(f"Initialisation de la base de données : {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Création de la table des utilisateurs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            bureau_douane TEXT
        )
    """)

    # Création de la table des dossiers inspectés
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marked_dossiers (
            dossier_num TEXT PRIMARY KEY,
            marked_by TEXT,
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Création de la table d'audit
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
    
    # Définition des utilisateurs de test
    test_users = [
        ("admin", "adminpassword", "admin", None),
        ("direction", "directionpassword", "direction", None),
        ("inspecteur_dkp", "inspecteurpassword", "inspecteur", "DKP"),
        ("inspecteur_aibd", "inspecteurpassword", "inspecteur", "AIBD"),
        ("transitaire_cargolink", "transitairepassword", "transitaire", "1234567"),
        ("banque_sgbs", "banquepassword", "partenaire", "SGBS"),
        ("assurance_axa", "assurancepassword", "partenaire", "AXA"),
        ("chercheur", "chercheurpassword", "statisticien", None),
        ("presse", "pressepassword", "journaliste", None)
    ]
    
    for username, raw_password, role, bureau in test_users:
        # Hachage sécurisé du mot de passe avec bcrypt en direct
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')
        
        # Insertion ou remplacement
        cursor.execute("""
            INSERT OR REPLACE INTO users (username, password_hash, role, bureau_douane)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, role, bureau))
        
        print(f"Utilisateur configuré : {username} (Rôle: {role}, Bureau: {bureau})")
        
    # Seeding audit logs
    cursor.execute("DELETE FROM audit_logs")
    default_logs = [
        ('2026-06-18 10:35:12', 'transitaire_cargolink', '197.224.23.104', '10.200.12.5', 'Dakar, Sénégal', 'Autorisé (Normal)'),
        ('2026-06-18 10:34:44', 'admin', '197.224.23.1', '10.200.12.5', 'Dakar, Sénégal', 'Autorisé (Normal)'),
        ('2026-06-18 10:30:15', 'hacker_bot', '185.220.101.42', '10.200.12.5', 'Frankfurt, Allemagne', 'Bloqué (Tor Node)'),
        ('2026-06-18 10:28:01', 'suspect_user', '82.102.23.15', '10.200.12.5', 'Paris, France', 'Tentative Force Brute')
    ]
    cursor.executemany("""
        INSERT INTO audit_logs (timestamp, username, client_ip, server_ip, location, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, default_logs)
    print("Logs d'audit initialisés !")
        
    conn.commit()
    conn.close()
    print("Initialisation terminée avec succès !")

if __name__ == "__main__":
    main()
