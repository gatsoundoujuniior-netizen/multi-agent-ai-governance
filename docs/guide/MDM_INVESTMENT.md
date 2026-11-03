# MDM Produits (membre Investment) : choix et justifications

Ce document résume comment le MDM Produits est construit (`sql/21_investment_mdm.sql`) et pourquoi. Il suit le format du [guide MDM](GUIDE_MDM.md) : pour chaque décision, le problème, les options, le choix et la raison.

## Entités et 5 tests

| Entité | Nature | Volatilité faible | Réutilisation | Partage | Criticité | Master Data ? |
|---|---|---|---|---|---|---|
| Security (ticker) | Oui, un objet identifiable | Oui, le ticker ne change presque jamais | Oui, des milliers de cours par titre | Oui, avec Finance (lien CIK) | Oui, sans lui aucun cours n'est exploitable | **Oui** |
| Sector GICS | Oui, une catégorie | Oui, 11 secteurs officiels | Oui, chaque titre | Oui, contrat commun `ref.sector` | Moyenne | **Oui, Reference Data** (`ref`) |
| Un cours du jour | Non, un événement daté | Non, une nouvelle valeur chaque jour | Non | Non | Moyenne | **Non, donnée transactionnelle** (`data.market_prices`) |
| Product (fonds, mandat) | Oui | Oui | Oui | Oui | Oui | **Oui** (simulé) |
| Investor | Oui, un client | Oui, l'identité ne change pas | Oui | Oui | Oui, le profil de risque décide des produits autorisés | **Oui** (simulé) |

## Les golden records

```
 sp500_constituents_raw   sp500_prices_raw   sec_company_tickers_raw (Finance)
          \                      |                    /
           \____ rapprochement par le ticker standardisé ____/
                                 |
   ref.sector ---------- master.security ---------- master.company (Finance, par le CIK)
                                 |
                       data.market_prices (un cours = une ligne)

 investor_crm_raw   investor_questionnaire_raw
          \                /
       rapprochement par le code investisseur
                  |
           master.investor
```

### `master.security` : une ligne par ticker

| Attribut | Règle de priorité | Raison |
|---|---|---|
| Fiche (ticker) | liste S&P 500, puis historique des cours | La liste est officielle. Les cours ne font que révéler les titres sortis de l'indice |
| Nom | liste S&P 500, puis liste des tickers SEC | La liste S&P 500 donne le nom usuel avec la classe d'action |
| CIK | liste S&P 500, puis liste des tickers SEC | Idem. La SEC complète les titres sortis de l'indice |
| Secteur | liste S&P 500 uniquement | Seule source qui donne le secteur GICS |
| `in_index` | recalculé à chaque exécution | Un titre peut sortir de l'indice |

Les colonnes `source`, `name_source` et `cik_source` indiquent la source gagnante.

### `master.investor` : une ligne par investisseur

| Attribut | Règle de priorité | Raison |
|---|---|---|
| Identité (nom, type, pays) | CRM | Seule source qui la contient |
| Profil de risque | questionnaire le plus récent, puis CRM | Le questionnaire est rempli et daté par le client : c'est lui qui a une valeur réglementaire. Le CRM n'est qu'une déclaration du commercial |

Les colonnes `risk_profile_source` et `risk_profile_date` indiquent d'où vient le profil et de quand il date.

## Décisions par étape

Dataset retenu : Kaggle « S&P 500 Stocks: 25 Years of Data (Updated Daily) » (darkmatternet), fichier `sp500_stocks.csv`, chargé le 2026-11-03.

### Étape 1 : découvrir le dataset

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Quel dataset Kaggle prendre ? | indice seul (^GSPC), un fichier par entreprise, un fichier unique par titre et par jour | « S&P 500 Stocks: 25 Years of Data » : un fichier unique, 2 948 439 lignes, 502 tickers, 2000-01-03 au 2026-10-30 | L'indice seul n'a pas de ticker : impossible de construire `master.security`. Un fichier unique se charge en une fois. 25 ans d'historique, mis à jour chaque jour |
| Quelle 2ᵉ source pour décrire les titres ? | la liste du dataset Kaggle (`sp500_companies.csv`), Wikipédia, la liste datahub.io | `constituents.csv` de datahub.io | La liste Kaggle n'a pas de CIK. Celle de datahub.io contient le CIK, la clé du lien avec `master.company` de Finance. Format CSV ouvert et stable |
| Quelle clé métier pour un titre ? | le nom, le CIK, le ticker | le ticker | Le CIK identifie l'entreprise, pas le titre : GOOGL et GOOG ont le même CIK. Le nom change, le ticker très rarement |
| `BRK.B` dans la liste, `BRK-B` dans les cours (idem `BF.B` et `BF-B`) | comparer tel quel, standardiser | standardiser au MDM | Mesuré par `explore_sp500.py`. Voir étape 5 |

### Étape 2 : charger les données brutes

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Typer les colonnes au chargement ? | laisser pandas deviner, tout en texte | tout en texte (`dtype=str`) | Copie fidèle de la source. Une date ou un prix mal formé n'est pas perdu sans bruit : on le compte au MDM |
| Le fichier des cours fait plusieurs millions de lignes | tout charger en mémoire, lire par morceaux | morceaux de 200 000 lignes | Évite de saturer la mémoire d'un PC portable |
| Les noms de colonnes changent d'un dataset Kaggle à l'autre (`Symbol`, `Ticker`, `Name`, `Adj Close`) | adapter le SQL à chaque fois, harmoniser les noms | harmoniser les **noms** (snake_case, ticker → `symbol`), jamais les **valeurs** | Le MDM reste le même quel que soit le dataset. La règle « aucune correction » porte sur les valeurs |
| Filtrer les dates pour aller plus vite ? | tout charger, `DATE_MIN` | tout charger | 2,9 millions de lignes se chargent en quelques minutes. La volatilité demande un historique long |
| Les sources simulées (produits, investisseurs) | les charger directement dans `master`, passer par `data.*_raw` | `data.*_raw` | Même règle pour toutes les sources : garder la version d'origine pour tracer et rejouer le MDM |

### Étape 3 : documenter

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Le dataset contient-il des PII ? | Oui, Non | Non | Des cours de bourse et des noms de sociétés cotées. Les investisseurs sont des institutions (personnes morales) |
| Documenter 3 sources | une fiche commune, une fiche par source | une fiche par source, dans le même fichier | Même owner et même classification, mais origine, fréquence et volumétrie différentes (même choix que Finance) |
| `adj_close` absent de certains datasets | ne pas la documenter, la documenter comme facultative | la documenter, « peut être vide » | C'est la colonne utile pour calculer la volatilité en partie 2 |

### Étape 4 : cataloguer dans OpenMetadata

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Configurer OpenMetadata comme les autres membres | à la main, avec le script commun | `scripts/setup_openmetadata.py` du membre Finance | Catalogue identique sur les 3 machines |
| Quels schémas ingérer ? | tous, `data`, `master`, `ref` | `data`, `master`, `ref` | `gov` contiendra les règles d'accès : il ne doit pas être visible de tous (même choix que Finance) |
| Classification de `master.security` | Medium comme le dataset, Low comme le propose le TP | *à décider en équipe* | La classification s'applique table par table. Un référentiel de tickers publics est moins sensible que l'historique complet |

### Étape 5 : construire le MDM

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| `BRK.B` (liste S&P 500) et `BRK-B` (autres sources) désignent le même titre | comparer tel quel, ou standardiser | standardiser : majuscules, sans espaces, `.` remplacé par `-` | Sinon Berkshire Hathaway existerait deux fois. On standardise la clé pour comparer |
| Une entreprise émet plusieurs titres (Alphabet : GOOGL et GOOG) | une ligne par entreprise, ou par titre | une ligne par titre, reliée à `master.company` par le CIK | L'entreprise est le golden record de Finance. Nous gérons le titre : relation 1-N |
| Les titres sortis de l'indice n'ont ni nom ni CIK | les supprimer, les garder vides, chercher une 3ᵉ source | 3ᵉ source : la liste des tickers SEC chargée par Finance | On complète à la source sans créer de nouveau téléchargement, et on garde la trace (`SEC_TICKERS`) |
| Un ticker abandonné peut être réattribué à une autre société | ignorer, ou signaler | signaler (point ouvert) | Le nom venu de la SEC pour un ancien titre peut être celui du nouveau propriétaire du ticker |
| Le dataset Kaggle ne contient que les membres actuels (biais du survivant) : la source 2 n'ajoute aucune fiche | changer de dataset, garder la règle et signaler | garder la règle et signaler | La règle de priorité reste juste et servira avec un dataset qui contient les anciens membres. L'Investment Agent doit savoir que l'historique ignore les sociétés disparues |
| `master.investor` n'avait qu'une source | rester à 1 source, ajouter une 2ᵉ | 2ᵉ source simulée : le questionnaire de risque | Sans 2 sources, pas de rapprochement ni de règle de priorité. Le profil de risque est l'exemple donné par la prof |
| Un investisseur a rempli deux questionnaires | le premier, le plus récent | le plus récent | Le profil de risque d'un client évolue : seul le dernier compte |
| Codes et valeurs mal écrits (`inv-002 `, `low`) | rejeter la ligne, ou standardiser | standardiser (`UPPER`, `TRIM`, `INITCAP`) | La valeur est juste, seule l'écriture diffère |
| Questionnaire de plus de 2 ans (INV-005) | l'utiliser quand même, ou l'ignorer | l'utiliser et le signaler (contrôle Q9) | C'est la meilleure information disponible. Le Steward demande son renouvellement |
| Pays `SN` (Sénégal, INV-006) absent de `ref.country` | le corriger soi-même, mettre le pays à NULL, signaler | signaler (contrôle Q10) et demander au membre Finance d'ajouter `SN` | `ref.country` appartient à Finance (contrat) : on ne modifie pas le référentiel d'un autre membre, et on ne perd pas une valeur juste |
| Classification des investisseurs | Confidential avec PII, ou Internal | Internal, pas de PII | Ce sont des institutions (personnes morales). On ne collecte pas de clients particuliers : on ne garde que ce dont on a besoin |

## Résultats (chargement du 2026-11-03)

| Mesure | Valeur |
|---|---|
| Cours chargés (`data.sp500_prices_raw`) | 2 948 439 lignes, 502 tickers, du 2000-01-03 au 2026-10-30 |
| Titres dans `master.security` | 503 (tous issus de la liste officielle) |
| Variantes fusionnées par la standardisation | 2 : `BRK.B`/`BRK-B`, `BF.B`/`BF-B` |
| Doublons de ticker | 0 |
| Complétude nom, secteur, CIK | 100 % |
| Cours reliés au golden record (`data.market_prices`) | 2 948 439 (100 %) |
| Doublons de cours, prix incohérents, clôtures vides | 0 |
| Titre de la liste sans aucun cours | 1 : FactSet (`FDS`) |
| Entreprises émettant 2 titres | 3 : Alphabet, News Corp, Fox |
| Investisseurs : profil venu du questionnaire / du CRM | 5 / 1 |
| Désaccords CRM / questionnaire | 3 (INV-002, INV-003, INV-004) |
| Questionnaires à renouveler (plus de 2 ans) | 1 (INV-005) |
| Titres reliés à `master.company` (Finance, par le CIK) | 503 sur 503 (100 %), avec les 8 477 entreprises du MDM Finance |

## Contrôles qualité (`sql/22_investment_quality.sql`)

| Contrôle | Ce qu'il vérifie |
|---|---|
| Q1 | Un ticker n'apparaît qu'une fois |
| Q2 | Les variantes d'écriture fusionnées par la standardisation |
| Q3 | Complétude du nom, du secteur et du CIK (seuil 95 %), par source |
| Q4 | Part des titres de l'indice reliés à une entreprise Finance, et relations 1-N |
| Q5, Q6 | Doublons et cours incohérents (prix négatif, plus haut inférieur au plus bas) |
| Q7 à Q9 | Profil de risque des investisseurs : complétude, désaccords entre sources, ancienneté |
| Q10 | Pays des investisseurs présent dans `ref.country` (référentiel commun) |
