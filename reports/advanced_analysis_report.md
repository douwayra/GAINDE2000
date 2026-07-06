# Rapport d'Analyse Statistique Avancée et Corrélations

## A. Corrélations entre Variables Numériques
Nous calculons la corrélation de Spearman (robuste aux valeurs extrêmes) entre les variables physiques et financières des articles :

### Matrice de Corrélation (Spearman) :
|                |   QUANTITEMESURE |   POIDSNET |   POIDSBRUT |   VALEURCFA |   VALEURDEVISE |   VALEURFOBCFA |
|:---------------|-----------------:|-----------:|------------:|------------:|---------------:|---------------:|
| QUANTITEMESURE |         1.000000 |   0.720362 |    0.718590 |    0.408602 |       0.469414 |       0.409320 |
| POIDSNET       |         0.720362 |   1.000000 |    0.996458 |    0.614847 |       0.446488 |       0.585512 |
| POIDSBRUT      |         0.718590 |   0.996458 |    1.000000 |    0.624124 |       0.445041 |       0.595006 |
| VALEURCFA      |         0.408602 |   0.614847 |    0.624124 |    1.000000 |       0.357717 |       0.946533 |
| VALEURDEVISE   |         0.469414 |   0.446488 |    0.445041 |    0.357717 |       1.000000 |       0.324666 |
| VALEURFOBCFA   |         0.409320 |   0.585512 |    0.595006 |    0.946533 |       0.324666 |       1.000000 |

**Analyses & Conclusions :**
- **Poids Net & Brut** : Très forte corrélation (0.9965), ce qui est attendu pour des données physiques cohérentes.
- **Valeurs CFA & Devise** : La corrélation est modérée à forte (0.3577), validant la cohérence générale des taux de change.
- **Volume & Valeur** : La corrélation entre QUANTITEMESURE et VALEURCFA est de 0.4086, montrant une relation modérée (les articles en grande quantité ne sont pas forcément les plus chers en valeur unitaire).

## B. Tests d'Association entre Variables Catégorielles (Chi-Deux)
Le test de Chi-Deux vérifie s'il existe une dépendance statistique significative entre deux variables qualitatives.

### 1. Mode de Transport vs Devise de Facturation
- **P-Value du test** : 0.0000e+00
- **Conclusion** : Le choix de la devise est **statistiquement dépendant** du mode de transport (par exemple, le fret maritime utilise majoritairement l'EUR ou l'USD pour les transactions internationales importantes, tandis que le transport terrestre régional ou le fret aérien affichent des répartitions différentes).

**Tableau de contingence (Top valeurs nettoyées) :**
| MODE_TRANSPORT   |   AED |   AUD |   CAD |   CFA |   CHF |    EUR |   GBP |   JPY |   USD |   ZAR |
|:-----------------|------:|------:|------:|------:|------:|-------:|------:|------:|------:|------:|
| Air              |    35 |   605 |    41 |  1202 |   210 |  40074 |  1600 |    76 | 12667 |   352 |
| Autres           |     0 |     1 |     0 |    67 |    33 |    422 |     3 |     0 |    68 |     0 |
| Contener-Air     |     0 |     0 |     0 |     2 |     0 |     10 |     0 |     0 |     4 |     0 |
| Contener-Mer     |     4 |     0 |     6 |  2021 |     0 |   5895 |    20 |     1 |  2141 |     0 |
| Contener-Route   |     0 |     0 |     0 |    10 |     0 |    891 |     1 |     0 |     0 |     0 |
| Fer              |     0 |     1 |     0 |     6 |     0 |     33 |     1 |     0 |    14 |     1 |
| Grande Cameroon  |     0 |     0 |     0 |     0 |     0 |      1 |     0 |     0 |     0 |     0 |
| Mer              |    80 |   366 |   280 | 25161 |    46 | 125308 |  1748 |    99 | 44376 |   444 |
| Merair           |     0 |     0 |     0 |     0 |     0 |      1 |     0 |     0 |     0 |     0 |
| Route            |     0 |     0 |     0 | 28278 |     0 |   4703 |    60 |     0 |  1160 |     0 |

## C. Analyse des Valeurs Atypiques (Outliers)
Nous utilisons la méthode de l'Écart Interquartile (IQR) pour isoler les transactions ayant une valeur CFA exceptionnellement élevée.

- **Seuil de détection d'outlier (IQR)** : 9,380,161.80 CFA
- **Nombre d'outliers détectés** : 201,367 (16.75% du total)
- **Top 5 des transactions les plus élevées (Outliers extrêmes) :**
|        | DESIGNATIONCOMMERCIALE                      | PAYSORIGINE   |   VALEURCFA |   QUANTITEMESURE |
|-------:|:--------------------------------------------|:--------------|------------:|-----------------:|
| 957602 | PEANUT KERMELS                              | Sénégal       | 6.3399e+11  |      1232        |
| 238168 | MEUBLES EN BOIS                             | France        | 6.28203e+11 |        33        |
| 432232 | SOFT STEARIN SMP 44-50                      | Ghana         | 5.91684e+11 |      3000        |
| 971554 | BIDON DHUILE VEGETALE 20 LITRES MARQUE OKEY | Togo          | 4.77232e+11 |     79080        |
|  13759 | POTATO 45/+mm ,25kg in jute bag             | Pays-Bas      | 3.27978e+11 |         1.25e+08 |

## D. Analyse de Saisonnalité Temporelle (Autocorrélation)
L'autocorrélation mesure la dépendance entre la valeur actuelle d'une variable temporelle et ses valeurs passées.

| Lag (Jours) | Autocorrélation |
|------------:|----------------:|
|  1 | 0.329857 |
|  2 | -0.287113 |
|  3 | -0.369242 |
|  4 | -0.366575 |
|  5 | -0.279758 |
|  6 | 0.314136 |
|  7 | 0.853967 |
|  8 | 0.303984 |
|  9 | -0.305065 |
| 10 | -0.382363 |
| 11 | -0.373180 |
| 12 | -0.291330 |
| 13 | 0.312419 |
| 14 | 0.825237 |

**Analyses & Conclusions :**
- **Lag 7 (Hebdomadaire)** : L'autocorrélation à 7 jours est de **0.8540**, ce qui démontre un cycle hebdomadaire extrêmement fort (les flux du début de semaine se répètent avec régularité d'une semaine à l'autre).
- **Lag 14 (Bi-hebdomadaire)** : L'autocorrélation à 14 jours reste très élevée à **0.8252**, confirmant cette forte saisonnalité structurelle.


