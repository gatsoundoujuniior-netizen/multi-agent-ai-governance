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

## Décisions

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| `BRK.B` (liste S&P 500) et `BRK-B` (autres sources) désignent le même titre | comparer tel quel, ou standardiser | standardiser : majuscules, sans espaces, `.` remplacé par `-` | Sinon Berkshire Hathaway existerait deux fois. On standardise la clé pour comparer |
| Une entreprise émet plusieurs titres (Alphabet : GOOGL et GOOG) | une ligne par entreprise, ou par titre | une ligne par titre, reliée à `master.company` par le CIK | L'entreprise est le golden record de Finance. Nous gérons le titre : relation 1-N |
| Les titres sortis de l'indice n'ont ni nom ni CIK | les supprimer, les garder vides, chercher une 3ᵉ source | 3ᵉ source : la liste des tickers SEC chargée par Finance | On complète à la source sans créer de nouveau téléchargement, et on garde la trace (`SEC_TICKERS`) |
| Un ticker abandonné peut être réattribué à une autre société | ignorer, ou signaler | signaler (point ouvert) | Le nom venu de la SEC pour un ancien titre peut être celui du nouveau propriétaire du ticker |
| `master.investor` n'avait qu'une source | rester à 1 source, ajouter une 2ᵉ | 2ᵉ source simulée : le questionnaire de risque | Sans 2 sources, pas de rapprochement ni de règle de priorité. Le profil de risque est l'exemple donné par la prof |
| Un investisseur a rempli deux questionnaires | le premier, le plus récent | le plus récent | Le profil de risque d'un client évolue : seul le dernier compte |
| Codes et valeurs mal écrits (`inv-002 `, `low`) | rejeter la ligne, ou standardiser | standardiser (`UPPER`, `TRIM`, `INITCAP`) | La valeur est juste, seule l'écriture diffère |
| Questionnaire de plus de 2 ans (INV-005) | l'utiliser quand même, ou l'ignorer | l'utiliser et le signaler (contrôle Q9) | C'est la meilleure information disponible. Le Steward demande son renouvellement |
| Classification des investisseurs | Confidential avec PII, ou Internal | Internal, pas de PII | Ce sont des institutions (personnes morales). On ne collecte pas de clients particuliers : on ne garde que ce dont on a besoin |

## Contrôles qualité (`sql/22_investment_quality.sql`)

| Contrôle | Ce qu'il vérifie |
|---|---|
| Q1 | Un ticker n'apparaît qu'une fois |
| Q2 | Les variantes d'écriture fusionnées par la standardisation |
| Q3 | Complétude du nom, du secteur et du CIK (seuil 95 %), par source |
| Q4 | Part des titres de l'indice reliés à une entreprise Finance, et relations 1-N |
| Q5, Q6 | Doublons et cours incohérents (prix négatif, plus haut inférieur au plus bas) |
| Q7 à Q9 | Profil de risque des investisseurs : complétude, désaccords entre sources, ancienneté |
