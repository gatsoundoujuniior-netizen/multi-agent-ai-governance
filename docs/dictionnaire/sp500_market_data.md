# Dataset `sp500_market_data`

Fiche catalogue et dictionnaire de données du dataset Investment (membre Investment, TP2 étape 3).
Le dataset a deux sources : l'historique des cours (fiche 1) et la liste officielle des membres du S&P 500 (fiche 2).
Le MDM Produits utilise aussi deux sources simulées pour les investisseurs (fiche 3).

Les valeurs `...` sont à compléter après le chargement de l'historique des cours (`scripts/load_sp500.py`).

## Fiche 1 : historique des cours

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Historique des cours des actions du S&P 500 |
| Métier | Description | Cours quotidiens (ouverture, plus haut, plus bas, clôture, volume) des actions qui font ou ont fait partie de l'indice S&P 500. Il alimente l'Investment Agent, qui répond aux questions sur l'évolution et la volatilité d'un titre. |
| Métier | Domaine | Investissement |
| Technique | Table | `data.sp500_prices_raw` |
| Technique | Format source | CSV, séparateur virgule, tout chargé en texte |
| Opérationnelle | Source | Kaggle, dataset « S&P 500 Historical Market Data » : ... (nom exact du fichier) |
| Opérationnelle | Période couverte | du ... au ... |
| Opérationnelle | Date de chargement | ..., script `scripts/load_sp500.py` |
| Opérationnelle | Volumétrie | ... lignes, ... tickers distincts |
| Opérationnelle | Filtre appliqué | aucun / à partir du ... (si `DATE_MIN` utilisé) |
| Gouvernance | Data Owner | Direction Investissement |
| Gouvernance | Data Steward | Ivan (membre Investment) |
| Gouvernance | Classification | Internal |
| Gouvernance | Sensibilité | Medium |
| Gouvernance | PII | Non |

## Fiche 2 : liste officielle des membres du S&P 500

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Composition actuelle de l'indice S&P 500 |
| Métier | Description | Liste des sociétés qui composent aujourd'hui l'indice S&P 500, avec leur nom, leur secteur GICS et leur identifiant SEC (CIK). C'est la source prioritaire du MDM Produits : elle fournit le nom, le secteur et le CIK qui relie chaque titre au référentiel `master.company` du membre Finance. |
| Métier | Domaine | Investissement |
| Technique | Table | `data.sp500_constituents_raw` |
| Technique | Format source | CSV, séparateur virgule, encodage UTF-8, tout chargé en texte |
| Opérationnelle | Source | datahub.io, https://datahub.io/core/s-and-p-500-companies |
| Opérationnelle | Fréquence de mise à jour | À chaque changement de composition de l'indice (côté source) |
| Opérationnelle | Date de chargement | ..., script `scripts/load_sp500.py` |
| Opérationnelle | Volumétrie | 503 lignes, 503 tickers, 500 CIK distincts, 11 secteurs GICS |
| Opérationnelle | Filtre appliqué | Aucun |
| Gouvernance | Data Owner | Direction Investissement |
| Gouvernance | Data Steward | Ivan (membre Investment) |
| Gouvernance | Classification | Internal |
| Gouvernance | Sensibilité | Medium |
| Gouvernance | PII | Non |

## Fiche 3 : sources simulées des investisseurs

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Clients investisseurs institutionnels |
| Métier | Description | Données **simulées**. Deux sources décrivent les mêmes investisseurs : le CRM commercial (identité et profil de risque déclaré par le commercial) et le questionnaire de risque réglementaire (profil de risque rempli et daté par le client). Elles alimentent le golden record `master.investor`. |
| Métier | Domaine | Investissement |
| Technique | Tables | `data.investor_crm_raw`, `data.investor_questionnaire_raw` |
| Technique | Format source | CSV dans `data/seed/` (`investor_crm.csv`, `investor_risk_questionnaire.csv`) |
| Opérationnelle | Volumétrie | 6 investisseurs dans le CRM, 6 questionnaires pour 5 investisseurs |
| Gouvernance | Data Owner | Direction Investissement |
| Gouvernance | Data Steward | Ivan (membre Investment) |
| Gouvernance | Classification | Internal |
| Gouvernance | Sensibilité | Medium |
| Gouvernance | PII | Non (investisseurs institutionnels : des personnes morales) |

## Dictionnaire de données

### Table `data.sp500_prices_raw` (un titre et un jour par ligne)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `date` | Date de séance | Jour de bourse auquel se rapportent les cours de la ligne | Date | NOT NULL | Jours ouvrés de la bourse de New York, format `YYYY-MM-DD` | Doit être unique pour un même titre | Non |
| `symbol` | Ticker | Code court qui identifie un titre en bourse | Texte | NOT NULL | Lettres majuscules, un point ou un tiret pour les classes d'action (`BRK.B`, `BRK-B`) | Doit exister dans `master.security` après standardisation | Non |
| `open` | Cours d'ouverture | Premier prix auquel le titre s'est échangé pendant la séance | Décimal (4 décimales) | Peut être vide | Nombre strictement positif, en USD | Doit être compris entre `low` et `high` du même jour | Non |
| `high` | Plus haut du jour | Prix le plus élevé atteint par le titre pendant la séance | Décimal (4 décimales) | Peut être vide | Nombre strictement positif, en USD | Doit être supérieur ou égal à `low` | Non |
| `low` | Plus bas du jour | Prix le plus bas atteint par le titre pendant la séance | Décimal (4 décimales) | Peut être vide | Nombre strictement positif, en USD | Doit être inférieur ou égal à `high` | Non |
| `close` | Cours de clôture | Dernier prix auquel le titre s'est échangé pendant la séance | Décimal (4 décimales) | NOT NULL | Nombre strictement positif, en USD | Doit être compris entre `low` et `high` du même jour | Non |
| `adj_close` | Cours de clôture ajusté | Cours de clôture corrigé des dividendes et des divisions d'actions, pour comparer des prix d'époques différentes | Décimal (4 décimales) | Peut être vide (absente de certains datasets) | Nombre strictement positif, en USD | Doit servir au calcul des rendements et de la volatilité | Non |
| `volume` | Volume échangé | Nombre d'actions échangées pendant la séance | Entier | Peut être vide | Entier positif ou nul | Doit être un nombre entier d'actions | Non |

### Table `data.sp500_constituents_raw` (une société de l'indice par ligne)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `symbol` | Ticker | Code court qui identifie un titre en bourse | Texte | NOT NULL, unique | Lettres majuscules, un point pour les classes d'action (2 cas : `BRK.B`, `BF.B`) | Doit être standardisé (point remplacé par un tiret) avant d'entrer dans `master.security` | Non |
| `security` | Nom du titre | Nom usuel de la société, avec la classe d'action quand elle en a plusieurs | Texte | NOT NULL | Texte libre (ex. « Alphabet Inc. (Class A) ») | Doit être le nom retenu dans `master.security` (source prioritaire) | Non |
| `gics_sector` | Secteur GICS | Grand secteur d'activité selon la classification internationale GICS | Texte | NOT NULL | 11 valeurs : Industrials, Financials, Information Technology, Health Care, Consumer Discretionary, Consumer Staples, Utilities, Real Estate, Materials, Communication Services, Energy | Doit exister dans le référentiel `ref.sector` | Non |
| `cik` | Identifiant SEC de l'entreprise | Numéro unique attribué par la SEC à l'entreprise qui émet le titre | Texte (10 chiffres) | NOT NULL | 10 chiffres, complété par des zéros à gauche (la source l'écrit sur 4 à 7 chiffres) | Doit relier le titre à `master.company` (contrat avec le membre Finance) | Non |
| `date_added` | Date d'entrée dans l'indice | Date à laquelle le titre a rejoint le S&P 500 | Date | NOT NULL | Format `YYYY-MM-DD`, de 1957-03-04 à aujourd'hui | Doit être antérieure ou égale à la date de chargement | Non |

## Observations pour le MDM

- **Clé métier** : le ticker, après standardisation (majuscules, sans espaces, `.` remplacé par `-`). Sans cela, `BRK.B` et `BRK-B` créeraient deux fiches pour Berkshire Hathaway.
- **Relation 1-N avec Finance** : 503 tickers pour 500 CIK. Trois entreprises émettent deux titres : Alphabet (`GOOGL`, `GOOG`), News Corp (`NWSA`, `NWS`), Fox (`FOXA`, `FOX`). Le golden record `master.security` a donc une ligne par titre, et plusieurs titres pointent vers la même ligne de `master.company`.
- **Titres sortis de l'indice** : ils sont dans l'historique des cours, mais pas dans la liste actuelle. Ils n'ont ni nom ni secteur dans nos deux sources. La liste des tickers de la SEC (chargée par Finance) leur apporte un nom et un CIK quand le ticker existe encore.
- **Point ouvert** : un ticker abandonné peut être réattribué à une autre société. Le nom et le CIK venus de la SEC pour un ancien titre sont donc à vérifier (colonne `name_source = SEC_TICKERS`).
