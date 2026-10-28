# multi-agent-ai-governance

Plateforme de gouvernance des donnees pour agents IA : une Governance Engine FastAPI
(RBAC, ABAC, audit trail) controle l'acces des agents LangGraph aux donnees, avec un
catalogue OpenMetadata et un MDM Tiers et Structures. Projet HESTIM, cours Data Governance.

## Principe

Un agent n'accede jamais directement aux donnees. Il demande a la Governance Engine,
qui repond ALLOW ou DENY et ecrit chaque decision dans `gov.audit_log`.

## Lancer le projet

```powershell
copy .env.example .env
docker compose up -d                                         # PostgreSQL du projet (port 5433)
docker compose -f openmetadata/docker-compose.yml up --detach --wait   # OpenMetadata (port 8585)
```

- OpenMetadata : http://localhost:8585 (admin@open-metadata.org / admin, a changer au premier acces)
- PostgreSQL : localhost:5433, base `governance`

## Conventions communes (decisions d'equipe, valeurs par defaut)

| Sujet | Valeur |
|---|---|
| Schemas | `ref`, `master`, `data`, `gov` |
| Agents | `finance_agent`, `investment_agent`, `hr_agent` |
| Datasets | `sec_financial_statements`, `sp500_market_data`, `ibm_hr_analytics` |
| Purposes valides | `valuation`, `reporting`, `audit` |
| Seuil qualite | 95 % de completude |

## Arborescence

```
docker-compose.yml       PostgreSQL du projet
openmetadata/            quickstart OpenMetadata 2.0.1 (fichier officiel)
sql/                     scripts de creation des tables
scripts/                 chargement des datasets
policies/                regles d'acces en JSON
governance_engine/       API FastAPI (portier)
agents/                  agents LangGraph
dashboard/               Streamlit
tests/                   pytest
docs/                    dossier technique
```
