# 📋 Fiche Explicative du Fichier Articles1.csv

## 🎯 Vue d'ensemble
Ce fichier contient **31 523 enregistrements** de **marchandises import/export** (factures commerciales/douanières).
Chaque ligne = **1 article dans 1 facture** avec ses caractéristiques (quantité, poids, valeur, pays, unité).

---

## 📍 Structure du fichier

### **A. Identification & Provenance**
| Colonne | Signification | Exemple | Utilité |
|---------|-------------|---------|---------|
| **IDTPSFACTURE** | ID unique de la facture | 3042705 | Regrouper articles de même facture |
| **NUMERODOSSIERTPS** | Numéro de dossier douanier | 3483869 | Suivre un dossier administratif |
| **NUMEROTARIFDOUANE** | Code HS/TARIC (classification douanière) | 9027800000 | Identifier type de marchandise, appliquer droits |
| **DESIGNATIONCOMMERCIALE** | Description commerciale | "CONDUCTIVIMETRE" | Comprendre le produit |
| **PAYSPROVENANCE** | Pays expéditeur (intermédiaire) | "Afrique du Sud" | Identifier flux logistique |
| **PAYSORIGINE** | Pays producteur | "Allemagne" | Déterminer tarif douanier |
| **PAYSDESTINATION** | Pays destinataire | "Sénégal" | Destination finale |
| **ORDRE** | Numéro ligne | 1, 2, 3... | Ordre dans facture |

### **B. Caractéristiques Physiques**
| Colonne | Signification | Unité | Données manquantes | Note |
|---------|-------------|-------|-------------------|------|
| **UNITEMESURE** | Unité de mesure | Texte | Rares | SET, PI-S, DOZ, m, L, KG... |
| **QUANTITEMESURE** | Quantité en l'unité | Nombre | Très rares | Peut être 0 |
| **POIDSNET** | Poids sans emballage | kg | **90% manquant** ⚠️ | ~3070 / 31523 présents |
| **POIDSBRUT** | Poids avec emballage | kg | **90% manquant** ⚠️ | ~3102 / 31523 présents |

### **C. Valeurs Commerciales (2 devises)**

#### **En Franc CFA (Monnaie locale)**
| Colonne | Signification | Note |
|---------|-------------|------|
| **VALEURCFA** | Valeur TOTALE de l'article | Valeur déclarée par importateur |
| **VALEURUNITAIRECFA** | Valeur UNITAIRE | = VALEURCFA / QUANTITEMESURE |
| **VALEURFOBCFA** | Valeur FOB* (port origine) | Coûts transport/assurance EXCLUS |
| **VALEURUNITAIREFOBCFA** | Valeur FOB unitaire | Pour comparaison entre articles |

#### **En Devise Étrangère (USD, EUR, etc.)**
| Colonne | Signification | Note |
|---------|-------------|------|
| **VALEURDEVISE** | Valeur TOTALE en devise orig. | Facture d'import peut être en USD |
| **VALEURUNITAIREDEVISE** | Valeur UNITAIRE en devise | Même ratio que CFA |
| **VALEURFOBDEVISE** | FOB en devise | Équivalent FOB |
| **VALEURUNITAIREFOBDEVISE** | FOB unitaire en devise | Pour prix comparatifs |

*FOB = "Free On Board" = prix sans frais transport/assurance

---

## ⚠️ Points d'Attention

### **Données Manquantes**
```
POIDSNET/POIDSBRUT   : 90% manquants → probablement pas pesés
VALEURUNITAIRECFA    : 47% manquants → articles légers/peu chers?
PAYSPROVENANCE/DEST  : <1% manquants → donné presque toujours
```

### **Qualité des Données**
- **Colonnes avec "NULL" texte** → remplacées par NaN ✓
- **Séparateur décimal = virgule** → nécessite conversion (,→.)
- **Unités mixtes** → SET vs PI-S vs L vs m → normaliser avant agrégations
- **BOM en en-tête** → caractère `ï»¿` au début première colonne (géré en lecture)

### **Particularités**
- Même article peut avoir plusieurs lignes = **factures multiproduits**
- Certaines valeurs FOB = 0 → problème administratif ou données incomplètes
- Mix de conventions : parfois poids = 0, parfois NULL, parfois absent

---

## 🔍 Exemples d'Utilisation

### **1. Analyser les flux par pays**
```python
# Total des imports par destination
df.groupby('PAYSDESTINATION')['VALEURFOBCFA'].sum().sort_values(ascending=False)
# → Quels pays reçoivent le plus de marchandises (en valeur)?
```

### **2. Comprendre les unités**
```python
# Répartition des unités de mesure
df['UNITEMESURE'].value_counts()
# → Quel type d'articles dominent? (sets, pièces, litres, etc.)
```

### **3. Détecter anomalies**
```python
# Articles sans poids
df[df['POIDSNET'].isna()].shape[0]
# → 90% des articles : normal pour produits légers/assemblés

# Valeurs FOB = 0 (suspectes)
df[df['VALEURFOBCFA'] == 0].shape[0]
```

### **4. Comparaison prix unitaire**
```python
# Prix moyen par pays d'origine
df.groupby('PAYSORIGINE')['VALEURUNITAIRECFA'].mean()
# → Quel pays exporte produits plus chers?
```

---

## 📊 Statistiques Clés
- **31 523 lignes** = articles différents (certaines factures multi-articles)
- **20 colonnes** = identifiants + caractéristiques + valeurs
- **~250 pays/régions** mentionnés (PAYSPROVENANCE, PAYSORIGINE, PAYSDESTINATION)
- **~100 codes TARIC différents** (NUMEROTARIFDOUANE)
- **~50 unités de mesure** différentes (à normaliser)

---

## ✅ Actions Recommandées (dans le notebook)
1. ✓ Charger CSV avec gestion BOM
2. ✓ Remplacer NULL → NaN
3. ✓ Convertir virgules → points (colonnes numériques)
4. ✓ Normaliser UNITEMESURE (minuscules, espaces)
5. ✓ Créer indicateurs manquants (ex: POIDS_ABSENT)
6. ✓ Supprimer doublons exacts
7. ✓ Exporter CSV nettoyé → Articles1_cleaned.csv
8. → Analyse graphiques + pivot tables par pays/unité

---

## 🎓 Vocabulaire Clé

| Terme | Définition |
|-------|-----------|
| **FOB** | Free On Board = prix coûts d'expédition non inclus |
| **CFA** | Franc CFA = monnaie locale (Sénégal, Afrique de l'Ouest) |
| **Code TARIC/HS** | Classification internationale des marchandises (douane) |
| **TPS** | Télédéclaration des Passages en Douane |
| **Facture** | Document commercial liée à une importation/exportation |
| **Devise** | Monnaie étrangère (USD, EUR, etc.) |

---

**Créé le 15/06/2026 - À partir de Articles1.csv (31 523 enregistrements)**
