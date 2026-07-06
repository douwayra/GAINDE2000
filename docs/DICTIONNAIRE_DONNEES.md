# Dictionnaire de Données - GAINDE 2000 / ORBUS

Ce document sert de dictionnaire de données de référence pour le projet d'analyse douanière. Il décrit de manière exhaustive la structure, le type de données, les relations et la signification de chaque champ des trois tables consolidées de la base DuckDB (`gainde_douane.db`).

---

## 1. Table `articles`
Cette table contient le descriptif détaillé des marchandises ligne par ligne (niveau le plus fin de la déclaration). Elle compte **1 201 958 lignes** dans la base consolidée.

| Nom de la Colonne | Type SQL | Clé / Relation | Description | Exemples de Valeurs |
| :--- | :--- | :---: | :--- | :--- |
| **IDTPSFACTURE** | BIGINT | FK (factures) | Clé de jointure vers la facture d'origine. | `3042705`, `3483869` |
| **NUMEROTARIFDOUANE** | VARCHAR | - | Code SH (Système Harmonisé) ou TARIC à 10 chiffres identifiant la marchandise. | `9027800000` (Instruments) |
| **NUMERODOSSIERTPS** | BIGINT | FK (dossiers) | Clé de jointure vers le dossier administratif. | `3483869` |
| **DESIGNATIONCOMMERCIALE** | VARCHAR | - | Description en texte libre de l'article importé. | `"CONDUCTIVIMETRE"`, `"RICE"` |
| **PAYSPROVENANCE** | VARCHAR | - | Pays d'expédition intermédiaire de la cargaison. | `"Afrique du Sud"`, `"France"` |
| **PAYSORIGINE** | VARCHAR | - | Pays de fabrication ou production du produit. | `"Allemagne"`, `"Chine"` |
| **PAYSDESTINATION** | VARCHAR | - | Pays destinataire final de la marchandise. | `"Sénégal"` |
| **UNITEMESURE** | VARCHAR | - | Code de l'unité physique de mesure douanière. | `"SET"`, `"DOZ"`, `"KG"`, `"L"` |
| **QUANTITEMESURE** | DOUBLE | - | Quantité de marchandise dans l'unité spécifiée. | `1.0`, `1200.0` |
| **POIDSNET** | DOUBLE | - | Poids net de la marchandise (hors emballage) en kg. | `15.5`, `NaN` (90% manquants) |
| **POIDSBRUT** | DOUBLE | - | Poids brut de la marchandise (emballage compris) en kg. | `18.0`, `NaN` (90% manquants) |
| **VALEURUNITAIRECFA** | DOUBLE | - | Prix unitaire de l'article en CFA. | `1500.0` |
| **VALEURCFA** | DOUBLE | - | Valeur totale déclarée de l'article en CFA. | `4500000.0` |
| **VALEURUNITAIREDEVISE** | DOUBLE | - | Prix unitaire de l'article en devise d'origine. | `2.50` |
| **VALEURDEVISE** | DOUBLE | - | Valeur totale déclarée de l'article en devise. | `7500.0` |
| **VALEURUNITAIREFOBCFA** | DOUBLE | - | Prix unitaire FOB (Free On Board) en CFA. | `1400.0` |
| **VALEURFOBCFA** | DOUBLE | - | Valeur totale FOB de l'article en CFA. | `4200000.0` |
| **VALEURUNITAIREFOBDEVISE**| DOUBLE | - | Prix unitaire FOB en devise. | `2.30` |
| **VALEURFOBDEVISE** | DOUBLE | - | Valeur totale FOB de l'article en devise. | `6900.0` |
| **ORDRE** | DOUBLE | - | Index de la ligne de l'article dans la facture. | `1.0`, `2.0` |
| **ANOMALY_IF** | BOOLEAN | - | Indicateur d'anomalie par l'algorithme *Isolation Forest*. | `True`, `False` |

---

## 2. Table `factures`
Cette table représente le niveau transactionnel commercial du dédouanement. Elle compte **301 230 lignes** uniques.

| Nom de la Colonne | Type SQL | Clé / Relation | Description | Exemples de Valeurs |
| :--- | :--- | :---: | :--- | :--- |
| **IDTPSFACTURE** | BIGINT | PK | Identifiant technique unique de la facture. | `3042705` |
| **NUMERODOSSIERTPS** | BIGINT | FK (dossiers) | Clé de liaison vers le dossier de dédouanement (1:1). | `3483869` |
| **DEVISE** | VARCHAR | - | Code de devise normalisé (ISO 4217). | `"EUR"`, `"USD"`, `"XOF"` |
| **TYPE_FACTURE** | VARCHAR | - | Type de facturation (normalisé). | `"Proforma"`, `"Définitive"` |
| **NUMERO_FACTURE** | VARCHAR | - | Numéro de la facture émise par l'exportateur. | `"FAC-2021-0098"` |
| **DATE_FACTURE** | VARCHAR | - | Date de facturation commerciale. | `"2021-09-20"` |
| **NOM_EXPORTATEUR** | VARCHAR | - | Raison sociale du vendeur ou fournisseur étranger. | `"SCHNEIDER ELECTRIC"` |
| **ADRESSE_EXPORTATEUR** | VARCHAR | - | Adresse physique de l'exportateur. | `"12 Rue de Paris, France"` |
| **PAYS_EXPORTATEUR** | VARCHAR | - | Pays d'établissement de l'exportateur. | `"France"`, `"Chine"` |
| **VALEUR_FOB_DEVISE** | DOUBLE | - | Valeur FOB totale facturée en devise. | `50000.0` |
| **VALEUR_FOB_CFA** | DOUBLE | - | Valeur FOB totale en CFA. | `32795700.0` |
| **FRAIS_FRET_DEVISE** | DOUBLE | - | Frais de transport international en devise. | `1200.0` |
| **FRAIS_ASSURANCE_DEVISE** | DOUBLE | - | Frais d'assurance transport en devise. | `350.0` |
| **VALEUR_TOTAL_DEVISE** | DOUBLE | - | Montant total facturé (FOB+Fret+Assur) en devise. | `51550.0` |
| **VALEUR_TOTAL_CFA** | DOUBLE | - | Montant total de la facture en CFA. | `33811900.0` |
| **INCOTERM** | VARCHAR | - | Règle d'Incoterm régissant la livraison. | `"FOB"`, `"CIF"`, `"EXW"`, `"CFR"` |
| **MODE_REGLEMENT** | VARCHAR | - | Moyen de paiement financier. | `"VIREMENT"`, `"LETTRE DE CREDIT"` |
| **PAYS_BANQUE** | VARCHAR | - | Pays de la banque assurant le transfert de fonds. | `"Sénégal"`, `"France"` |
| **VALEUR_FRET_CFA** | DOUBLE | - | Montant du fret converti en CFA. | `787000.0` |
| **VALEUR_ASSURANCE_CFA** | DOUBLE | - | Montant de l'assurance converti en CFA. | `229000.0` |
| **VALEUR_FACTURE_CFA_FINAL**| DOUBLE | - | Valeur totale finale après ajustement douanier. | `33811900.0` |
| **PAYS_DESTINATION** | VARCHAR | - | Pays destinataire final déclaré de la facture. | `"Sénégal"` |

---

## 3. Table `dossiers`
Cette table correspond au niveau administratif supérieur (le dossier déposé en douane). Elle compte **350 791 lignes** uniques.

| Nom de la Colonne | Type SQL | Clé / Relation | Description | Exemples de Valeurs |
| :--- | :--- | :---: | :--- | :--- |
| **NUMERODOSSIERTPS** | BIGINT | PK | Identifiant unique du dossier douanier. | `3483869` |
| **ID_SEQUENCE_DOSSIER** | VARCHAR | - | Numéro de séquence du dossier ORBUS. | `"SEQ-2020-0012"` |
| **TYPE_OPERATION** | VARCHAR | - | Libellé normalisé du type d'opération douanière. | `"Importation"`, `"Exportation"` |
| **DATE_CREATION** | VARCHAR | - | Date et heure de création du dossier. | `"2020-01-28 10:22:10"` |
| **STATUT_DOSSIER** | VARCHAR | - | Statut du dossier dans le système ORBUS. | `"SOUMIS"`, `"VALIDE"`, `"REJETE"` |
| **NOM_NAVIRE** | VARCHAR | - | Nom du navire transporteur de la marchandise. | `"MAERSK MC-KINNEY"` |
| **MODE_TRANSPORT** | VARCHAR | - | Mode logistique principal (normalisé). | `"Mer"`, `"Air"`, `"Route"`, `"Fer"` |
| **NOM_IMPORTATEUR** | VARCHAR | - | Nom ou raison sociale de l'importateur. | `"SENELEC"`, `"TOTAL SENEGAL"` |
| **PAYS_IMPORTATEUR** | VARCHAR | - | Pays d'établissement de l'importateur. | `"Sénégal"` |
| **NINEA_IMPORTATEUR** | VARCHAR | - | Identifiant fiscal NINEA de l'importateur. | `"0012345G2"` |
| **REGIME_DOUANIER** | VARCHAR | - | Régime douanier appliqué à la marchandise. | `"C100"` (Mise à la consommation) |
| **BANQUE** | VARCHAR | - | Banque émettrice de la caution financière. | `"CBAO"`, `"SGBS"`, `"ECOBANK"` |
| **ASSURANCE** | VARCHAR | - | Compagnie d'assurance garante. | `"AXA"`, `"ALLIANZ"`, `"CNART"` |
| **TYPE_CONTENEUR** | VARCHAR | - | Format de conteneur utilisé (normalisé). | `"FCL - Conteneur personnalisé"` |
| **IMPORTATEUR_SEGMENT** | VARCHAR | - | Segment K-Means de l'importateur. | `"Grands comptes"`, `"Réguliers"` |
| **RISK_SCORE** | INT | - | Score global de risque calculé de 0 à 100. | `85`, `15` |
| **RISK_CLASS** | VARCHAR | - | Classification du niveau de risque douanier. | `"Faible risque"`, `"Haut risque"` |
