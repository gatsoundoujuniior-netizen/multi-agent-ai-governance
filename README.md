# multi-agent-ai-governance

Plateforme de gouvernance des donnees pour agents IA : une Governance Engine FastAPI
(RBAC, ABAC, audit trail) controle l'acces des agents LangGraph aux donnees, avec un
catalogue OpenMetadata et un MDM Tiers et Structures. Projet HESTIM, cours Data Governance.

## Principe

Un agent n'accede jamais directement aux donnees. Il demande a la Governance Engine,
qui repond ALLOW ou DENY et ecrit chaque decision dans `gov.audit_log`.

Pour realiser ou comprendre un MDM, commencer par le guide d'equipe :
[docs/guide/GUIDE_MDM.md](docs/guide/GUIDE_MDM.md).

## Avancement (partie 1)

| Domaine | Membre | Branche | Etat |
|---|---|---|---|
| Finance, MDM Tiers et Structures | Junior | `finance` | MDM, controles qualite et catalogue faits, PR a ouvrir |
| Investment, MDM Produits | Ivan | `investment` | Travail pousse sur la branche, PR a ouvrir |
| HR, MDM Ressources humaines | Mohammed | `hr` | Travail pousse sur la branche, PR a ouvrir |

### Resultats du MDM Finance (`master.company`)

| Mesure | Resultat | Seuil |
|---|---|---|
| Entreprises | 8 485, une ligne par CIK, 0 doublon | |
| Sources rapprochees sur le CIK | 3 : depots 10-K, liste des tickers, API EDGAR Submissions | au moins 2 |
| Nom renseigne | 100 % | 95 % |
| Pays renseigne | 98,81 % (49 % sans EDGAR) | 95 % |
| Secteur SIC renseigne | 85,69 % : **sous le seuil**, point ouvert | 95 % |
| Montants relies a une entreprise | 63 937 sur 64 253 lignes brutes (316 sans montant), 0 orphelin | |
| Doublons de montants | 5, soit 0,01 % | 1 % |

Regles de priorite, attribut par attribut : nom = tickers, puis 10-K, puis EDGAR ;
pays et secteur = 10-K, puis EDGAR. Les colonnes `*_source` gardent la source gagnante.

### Points ouverts cote Finance

- Secteur sous le seuil : 1 214 entreprises sans code SIC, dont 1 035 de type `other` a la SEC.
  Decision a prendre.
- Code `0000` recu d'EDGAR pour 11 entreprises : il ne designe aucun secteur et compte
  pour l'instant comme renseigne.
- Libelles SIC : 47 codes restent sans libelle (104 entreprises).

## Les TP du projet (partie 1 : jusqu'au MDM)

| TP | Pour qui | Fichier |
|---|---|---|
| TP0 Fondations communes | Junior, Ivan et Mohammed ensemble | [docs/tp/TP0_Commun_Fondations.md](docs/tp/TP0_Commun_Fondations.md) |
| TP1 Finance, MDM Tiers et Structures | Junior (branche `finance`) | [docs/tp/TP1_Finance_MDM_Tiers_Structures.md](docs/tp/TP1_Finance_MDM_Tiers_Structures.md) |
| TP2 Investment, MDM Produits | Ivan (branche `investment`) | [docs/tp/TP2_Investment_MDM_Produits.md](docs/tp/TP2_Investment_MDM_Produits.md) |
| TP3 HR, MDM Ressources | Mohammed (branche `hr`) | [docs/tp/TP3_HR_MDM_Ressources.md](docs/tp/TP3_HR_MDM_Ressources.md) |

Les versions PDF sont dans `docs/tp/pdf/`. Les prompts pour se faire guider par Claude sont dans `docs/tp/prompts/`.

## Lancer le projet

```powershell
copy .env.example .env
docker compose up -d --wait                                            # PostgreSQL du projet (port 5433)
docker compose -f openmetadata/docker-compose.yml up --detach --wait   # OpenMetadata (port 8585)
```

- OpenMetadata : http://localhost:8585 (admin@open-metadata.org / admin, a changer au premier acces)
- PostgreSQL : localhost:5433, base `governance`

Executer un script SQL du projet :

```powershell
docker exec gouv_postgres psql -U gouv -d governance -v ON_ERROR_STOP=1 -f /sql/<fichier>.sql
```

Reconstruire le MDM Finance, dans cet ordre (les datasets SEC doivent etre dans `data/raw/sec/`) :

```powershell
python scripts/load_sec.py                # depots 10-K, montants, plan de comptes, tickers
python scripts/load_sec_submissions.py    # fiches EDGAR (telechargement, puis reprise possible)
docker exec gouv_postgres psql -U gouv -d governance -v ON_ERROR_STOP=1 -f /sql/11_finance_mdm.sql
docker exec gouv_postgres psql -U gouv -d governance -f /sql/12_finance_quality.sql
python scripts/setup_openmetadata.py      # configuration commune et ingestion
python scripts/enrich_openmetadata_finance.py   # catalogue, dictionnaire, glossaire, lignage
```

## Conventions communes (decisions d'equipe, valeurs par defaut)

| Sujet | Valeur |
|---|---|
| Schemas | `ref`, `master`, `data`, `gov` |
| Tables brutes | `data.<dataset>_raw` |
| Agents | `finance_agent`, `investment_agent`, `hr_agent` |
| Datasets | `sec_financial_statements`, `sp500_market_data`, `ibm_hr_analytics` |
| Classification | `Public`, `Internal`, `Confidential`, `Restricted` |
| Sensibilite | `Low`, `Medium`, `High` |
| Purposes valides | `valuation`, `reporting`, `audit` |
| Seuil qualite | 95 % de completude, 1 % de doublons maximum |
| Branches | `finance`, `investment`, `hr` (PR relue par un autre membre) |

## Contrats entre membres

| Table | Proprietaire | Utilisee par | Colonnes stables |
|---|---|---|---|
| `master.company` | Finance | Investment (lien ticker vers entreprise) | `company_id`, `cik` (10 chiffres), `legal_name`, `country`, `sic_code` |
| `ref.currency`, `ref.country` | Finance | Tous | `code`, `label` |
| `ref.sector` (GICS) | Investment | Tous | `sector_id`, `label` |

`master.company` contient une ligne par CIK. `country` et `sic_code` peuvent etre vides.
Les colonnes `name_source`, `country_source`, `sic_source` et `updated_at` servent a la
tracabilite et ne font pas partie du contrat. `ref.sic` et `ref.edgar_location` sont
internes au MDM Finance.

## Arborescence

```
docker-compose.yml       PostgreSQL du projet
openmetadata/            quickstart OpenMetadata 2.0.1 (fichier officiel)
sql/init/                execute une seule fois a la creation de la base
sql/                     scripts par membre : 1x finance, 2x investment, 3x hr
scripts/                 exploration et chargement des datasets
data/raw/                datasets telecharges (jamais dans Git)
data/seed/               petites tables simulees (dans Git)
docs/tp/                 les TP du projet, PDF et prompts
docs/dictionnaire/       fiches catalogue et dictionnaires de donnees
docs/guide/              guide d'equipe pour realiser son MDM
policies/                regles d'acces en JSON (partie 2)
governance_engine/       API FastAPI, le portier (partie 2)
agents/                  agents LangGraph (partie 2)
dashboard/               Streamlit (partie 2)
tests/                   pytest (partie 2)
```
