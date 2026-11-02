# Dataset `sec_financial_statements`

Fiche catalogue et dictionnaire de données du dataset Finance (membre Finance, TP1 étape 3).
Le dataset a deux sources : les dépôts SEC (fiche 1) et la liste officielle des tickers SEC (fiche 2).
La deuxième source sert au MDM Tiers et Structures (référentiel `master.company`).

## Fiche 1 : dépôts SEC (Financial Statement Data Sets)

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | États financiers annuels des sociétés cotées US |
| Métier | Description | Rapports annuels (10-K) déposés auprès de la SEC par les sociétés cotées aux États-Unis, avec leurs principaux montants financiers (chiffre d'affaires, résultat, actifs, dettes, capitaux propres, trésorerie). Il alimente le Finance Agent, qui répond aux questions sur la santé financière d'une entreprise, et le MDM Tiers et Structures. |
| Métier | Domaine | Finance |
| Technique | Tables | `data.sec_sub_raw`, `data.sec_num_raw`, `data.sec_tag_raw` |
| Technique | Format source | TXT séparé par tabulations, encodage UTF-8, tout chargé en texte |
| Opérationnelle | Source | SEC, Financial Statement Data Sets, trimestre 2026q1 |
| Opérationnelle | Fréquence de mise à jour | Trimestrielle (côté SEC) |
| Opérationnelle | Date de chargement | 2026-11-02, script `scripts/load_sec.py` |
| Opérationnelle | Volumétrie | 4 262 lignes (sub), 64 253 lignes (num), 27 lignes (tag) |
| Opérationnelle | Filtre appliqué | Formulaires 10-K, 8 tags us-gaap, USD, sans coreg ni segments |
| Opérationnelle | Lignes écartées | 2 lignes mal formées dans `num.txt` (11 champs au lieu de 10), hors périmètre du filtre |
| Gouvernance | Data Owner | Direction Finance |
| Gouvernance | Data Steward | Junior (membre Finance) |
| Gouvernance | Classification | Public |
| Gouvernance | Sensibilité | Low |
| Gouvernance | PII | Non (les noms, adresses et téléphones sont ceux d'entreprises, personnes morales) |

## Fiche 2 : liste officielle des tickers SEC

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Liste officielle des sociétés cotées US (CIK, ticker, nom) |
| Métier | Description | Correspondance tenue par la SEC entre l'identifiant d'une entreprise (CIK), son symbole boursier (ticker) et son nom actuel. Elle est la deuxième source du MDM Tiers et Structures : elle fournit le nom à jour et le ticker qui relie `master.company` au MDM Produits (membre Investment). |
| Métier | Domaine | Finance |
| Technique | Table | `data.sec_company_tickers_raw` |
| Technique | Format source | JSON, encodage UTF-8, tout chargé en texte |
| Opérationnelle | Source | SEC, https://www.sec.gov/files/company_tickers.json |
| Opérationnelle | Fréquence de mise à jour | En continu (côté SEC) |
| Opérationnelle | Date de chargement | 2026-11-02, script `scripts/load_sec.py` |
| Opérationnelle | Volumétrie | 10 423 lignes, 8 017 CIK distincts |
| Opérationnelle | Filtre appliqué | Aucun : le référentiel doit couvrir toutes les sociétés cotées (5 418 n'ont pas de 10-K en 2026q1, par exemple Apple) |
| Gouvernance | Data Owner | Direction Finance |
| Gouvernance | Data Steward | Junior (membre Finance) |
| Gouvernance | Classification | Public |
| Gouvernance | Sensibilité | Low |
| Gouvernance | PII | Non |

## Dictionnaire de données

### Table `data.sec_sub_raw` (un dépôt par ligne)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `adsh` | Numéro du dépôt | Numéro unique attribué par la SEC à chaque rapport déposé | Texte (20 caractères) | NOT NULL, unique | Format `0000000000-00-000000` | Doit relier chaque montant de `sec_num_raw` à son dépôt | Non |
| `cik` | Identifiant SEC de l'entreprise | Numéro unique attribué par la SEC à chaque entité qui dépose des rapports | Texte (10 chiffres) | NOT NULL | 10 chiffres, complété par des zéros à gauche (la source l'écrit sans les zéros : 4 à 7 chiffres) | Doit être unique par entreprise dans `master.company` | Non |
| `name` | Raison sociale au moment du dépôt | Nom légal de l'entreprise tel qu'inscrit dans le rapport déposé | Texte | NOT NULL | Texte libre, en majuscules dans la source | Doit céder la priorité au nom de la liste des tickers dans `master.company` | Non |
| `sic` | Code secteur d'activité | Code de la classification américaine des secteurs d'activité (Standard Industrial Classification) | Texte (4 chiffres) | Peut être vide | Codes de la liste SIC de la SEC (ex. 6798 = fonds immobiliers cotés) | Doit exister dans le référentiel `ref.sic` | Non |
| `countryba` | Pays de l'adresse professionnelle | Pays du siège où l'entreprise exerce son activité | Texte (2 lettres) | Peut être vide (96 dépôts sans pays) | Code pays ISO 3166 sur 2 lettres (US = 4 034 dépôts, CA, GB, BM...) | Doit exister dans le référentiel `ref.country` | Non |
| `form` | Type de formulaire | Nature du rapport déposé | Texte | NOT NULL | 10-K uniquement après filtre (10-K = rapport annuel) | Doit valoir 10-K dans ce dataset | Non |

### Table `data.sec_num_raw` (un montant par ligne)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `tag` | Poste financier | Étiquette XBRL standard qui dit ce que mesure le montant | Texte | NOT NULL | Les 8 tags retenus : Revenues, RevenueFromContractWithCustomerExcludingAssessedTax, NetIncomeLoss, OperatingIncomeLoss, Assets, Liabilities, StockholdersEquity, CashAndCashEquivalentsAtCarryingValue | Doit exister dans `sec_tag_raw` avec `custom = 0` | Non |
| `ddate` | Date de fin de période | Date à laquelle se termine la période couverte par le montant | Texte (AAAAMMJJ) | NOT NULL | Date au format AAAAMMJJ (de 20091231 à 20260131 dans le chargement) | Doit être convertie au format AAAA-MM-JJ dans les données nettoyées | Non |
| `qtrs` | Durée de la période | Nombre de trimestres couverts par le montant | Entier | NOT NULL | 0 = montant à une date (bilan), 1 à 4 = montant sur 1 à 4 trimestres (4 = un an), 94 = valeur atypique présente dans la source | Doit valoir 0 ou 4 pour les chiffres annuels utilisés par le Finance Agent | Non |
| `uom` | Unité de mesure | Unité dans laquelle le montant est exprimé | Texte | NOT NULL | USD uniquement après filtre | Doit valoir USD dans ce dataset | Non |
| `value` | Montant | Montant déclaré par l'entreprise pour un poste et une date | Décimal | Peut être vide | Nombre décimal, négatif possible (10 469 montants négatifs, par exemple une perte nette) | Doit être lu avec son `uom` et son `qtrs` pour être interprété | Non |

### Table `data.sec_company_tickers_raw` (une ligne par ticker)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `cik_str` | Identifiant SEC de l'entreprise | Même identifiant que `cik` dans `sec_sub_raw`, écrit sans les zéros de tête | Texte | NOT NULL | Chiffres, sans zéros de tête | Doit être complété à 10 chiffres avant le rapprochement avec `sec_sub_raw` | Non |
| `ticker` | Symbole boursier | Code court d'un titre en bourse | Texte | NOT NULL | Lettres majuscules, parfois un tiret (ex. BRK-B) | Doit servir de lien avec `master.security` (MDM Produits) | Non |
| `title` | Raison sociale actuelle | Nom actuel de l'entreprise, tenu à jour par la SEC | Texte | NOT NULL | Texte libre | Doit être le nom retenu dans `master.company` quand il existe | Non |

## Observations pour le MDM (étape 5)

| Constat | Chiffre | Conséquence pour le MDM |
|---|---|---|
| CIK écrit sur 4 à 7 chiffres dans les deux sources | 100 % des lignes | Standardiser sur 10 chiffres avant de rapprocher |
| Une entreprise a déposé deux 10-K dans le trimestre | 4 262 dépôts pour 4 261 CIK | Règle de priorité : le dépôt le plus récent gagne pour les attributs de `sub` |
| Un même CIK peut avoir plusieurs tickers | 10 423 tickers pour 8 017 CIK | Une entreprise peut émettre plusieurs titres : `master.company` reste une ligne par CIK |
| Nom différent entre les deux sources | 107 entreprises (ex. LendingClub devenue Happen) | Règle de priorité : le nom de la liste des tickers gagne, `sub` en secours |
| Pays absent | 96 dépôts | Mesurer la complétude (seuil commun : 95 %) |
