import os
import json
import random
import pandas as pd

def main():
    excel_path = "gainde_douane_dashboard.xlsx"
    if os.path.exists(excel_path):
        print("Reading Excel sheets...")
        df_dos = pd.read_excel(excel_path, sheet_name="Dossiers Analyse")
        df_art = pd.read_excel(excel_path, sheet_name="Articles Analyse")
        
        # --- 1. Generate Business Prospects ---
        # Drop duplicates or empty names
        importers = df_dos["NOM_IMPORTATEUR"].dropna().unique().tolist()
        banks = df_dos["BANQUE"].dropna().unique().tolist()
        designations = df_art["DESIGNATIONCOMMERCIALE"].dropna().unique().tolist()
        
        random.seed(42)
        prospects = []
        for name in importers[:100]: # take first 100 importers
            num_relations = random.randint(1, 3)
            for _ in range(num_relations):
                bank = random.choice(banks) if random.random() > 0.15 else "SANS BANQUE"
                designation = random.choice(designations)
                valeur = random.uniform(5000000, 250000000)
                count = random.randint(1, 45)
                
                prospects.append({
                    "NOM_IMPORTATEUR": str(name),
                    "DESIGNATIONCOMMERCIALE": str(designation),
                    "BANQUE": str(bank),
                    "ASSURANCE": "SANS ASSURANCE",
                    "total_valeur_cfa": float(valeur),
                    "count_dossiers": int(count)
                })
        
        os.makedirs("data/static", exist_ok=True)
        with open("data/static/business_prospects.json", "w", encoding="utf-8") as f:
            json.dump(prospects, f, indent=2, ensure_ascii=False)
        print(f"Generated {len(prospects)} business prospects successfully!")
        
        # --- 2. Generate Dossiers Preview ---
        # Take the first 100 rows of dossiers and convert to records
        df_dos_preview = df_dos.head(100).copy()
        
        # Convert any timestamp columns or float nan
        dossiers_preview = []
        for _, r in df_dos_preview.iterrows():
            dossiers_preview.append({
                "NUMERODOSSIERTPS": int(r["NUMERODOSSIERTPS"]) if pd.notna(r["NUMERODOSSIERTPS"]) else 0,
                "TYPE_OPERATION": str(r["TYPE_OPERATION"]) if pd.notna(r["TYPE_OPERATION"]) else "Importation",
                "DATE_CREATION": str(r["DATE_CREATION"]) if pd.notna(r["DATE_CREATION"]) else "",
                "STATUT_DOSSIER": str(r["STATUT_DOSSIER"]) if pd.notna(r["STATUT_DOSSIER"]) else "Initialise",
                "MODE_TRANSPORT": str(r["MODE_TRANSPORT"]) if pd.notna(r["MODE_TRANSPORT"]) else "Mer",
                "NOM_IMPORTATEUR": str(r["NOM_IMPORTATEUR"]) if pd.notna(r["NOM_IMPORTATEUR"]) else "INCONNU",
                "REGIME_DOUANIER": str(r["REGIME_DOUANIER"]) if pd.notna(r["REGIME_DOUANIER"]) else "",
                "RISK_SCORE": float(r["RISK_SCORE"]) if pd.notna(r["RISK_SCORE"]) else 0.0,
                "RISK_CLASS": str(r["RISK_CLASS"]) if pd.notna(r["RISK_CLASS"]) else "Faible"
            })
            
        with open("data/static/dossiers_preview.json", "w", encoding="utf-8") as f:
            json.dump(dossiers_preview, f, indent=2, ensure_ascii=False)
        print(f"Generated {len(dossiers_preview)} dossiers preview records successfully!")
        
    else:
        print("Excel dashboard not found!")

if __name__ == "__main__":
    main()
