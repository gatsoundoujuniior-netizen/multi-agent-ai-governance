# multi-agent-ai-governance

Plateforme de gouvernance des donnees pour agents IA : une Governance Engine FastAPI
(RBAC, ABAC, audit trail) controle l'acces des agents LangGraph aux donnees, avec un
catalogue OpenMetadata et un MDM Tiers et Structures. Projet HESTIM, cours Data Governance.

## Principe

Un agent n'accede jamais directement aux donnees. Il demande a la Governance Engine,
qui repond ALLOW ou DENY et ecrit chaque decision dans `gov.audit_log`.

## Les TP du projet (partie 1 : jusqu'au MDM)

| TP | Pour qui | Fichier |
|---|---|---|
| TP0 Fondations communes | Les 3 membres ensemble | [docs/tp/TP0_Commun_Fondations.md](docs/tp/TP0_Commun_Fondations.md) |
| TP1 Finance, MDM Tiers et Structures | Membre Finance | [docs/tp/TP1_Finance_MDM_Tiers_Structures.md](docs/tp/TP1_Finance_MDM_Tiers_Structures.md) |
| TP2 Investment, MDM Produits | Membre Investment | [docs/tp/TP2_Investment_MDM_Produits.md](docs/tp/TP2_Investment_MDM_Produits.md) |
| TP3 HR, MDM Ressources | Membre HR | [docs/tp/TP3_HR_MDM_Ressources.md](docs/tp/TP3_HR_MDM_Ressources.md) |

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
policies/                regles d'acces en JSON (partie 2)
governance_engine/       API FastAPI, le portier (partie 2)
agents/                  agents LangGraph (partie 2)
dashboard/               Streamlit (partie 2)
tests/                   pytest (partie 2)
```
