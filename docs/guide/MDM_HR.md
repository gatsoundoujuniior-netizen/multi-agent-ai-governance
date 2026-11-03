# MDM Ressources humaines (membre HR) : choix et justifications

Ce document résume comment le MDM Ressources humaines est construit (`sql/31_hr_mdm.sql`) et pourquoi. Il suit le format du [guide MDM](GUIDE_MDM.md) : pour chaque décision, le problème, les options, le choix et la raison.

**Type de MDM.** Le référentiel des employés est de **type Tiers** (domaine Parties : des personnes). Seuls les sites (`master.office`) relèvent du type **Ressources**. Les codes (niveau d'études, satisfaction, performance) sont de la **Reference Data**.

## Entités et 5 tests

| Entité | Nature | Volatilité faible | Réutilisation | Partage | Criticité | Master Data ? |
|---|---|---|---|---|---|---|
| Employee (matricule, genre, département, poste) | Oui, une personne | Oui, le matricule ne change jamais, le poste rarement | Oui, chaque fait RH le référence | Oui : RH, paie, mobilité, comptes utilisateurs en partie 2 | Oui, un mauvais rattachement fausse toutes les statistiques | **Oui** |
| Department | Oui, une unité de l'organisation | Oui, 3 départements | Oui, 1 470 employés | Oui | Oui, base des agrégats du HR Agent | **Oui** |
| JobRole | Oui, une fonction | Oui, 9 postes | Oui | Oui | Oui | **Oui** |
| Office | Oui, un lieu | Oui | Oui, les départements y sont rattachés | Oui | Moyenne | **Oui** (simulé, type Ressources) |
| Code `education` (1 à 5) | Oui, un code et son sens | Oui, liste officielle | Oui | Oui | Oui, sans lui le code est illisible | **Oui, Reference Data** (`ref`) |
| MonthlyIncome | Non, une valeur à un instant | Non, change à chaque augmentation | | | | **Non, fait** (`data.hr_employee_facts`) |
| Attrition | Non, un événement (un départ) | Non | | | | **Non, fait** |
| Age | Non, une valeur | Non, change chaque année | | | | **Non, fait** |

## Les golden records

```
 data.hr_employee_raw (IBM HR)        data.hr_mobility_raw (mobilité, simulée)
              \                                 /
               \__ rapprochement par employee_number __/
                                  |
   master.department ─ master.office (simulé)
   master.job_role ────── master.employee ────── ref.education_level
   master.education_field  (1 ligne par matricule)
                                  |
                       data.hr_employee_facts ── ref.satisfaction_level
           (âge, salaires, satisfaction, attrition)  ref.performance_rating
                                                     ref.work_life_balance
```

### `master.employee` : une ligne par matricule

| Attribut | Règle de priorité | Raison |
|---|---|---|
| Fiche (matricule) | fichier IBM HR uniquement | C'est le registre du personnel. Une mobilité sur un matricule inconnu ne crée pas d'employé : elle est signalée (Q8) |
| Département | mobilité la plus récente, puis IBM HR | La mobilité est le système qui gère les changements de poste, et elle est datée après la photo IBM |
| Poste | mobilité la plus récente, puis IBM HR | Idem |
| Genre, situation familiale, niveau, formation | IBM HR uniquement | Seule source qui les contient |

Les colonnes `department_source` et `job_role_source` indiquent la source gagnante (`IBM_HR` ou `MOBILITY`), et `mobility_date` la date d'effet de la mobilité retenue.

## Décisions par étape

### Étape 1 : découvrir le dataset

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Quelle clé métier pour un employé ? | le numéro de ligne, une combinaison âge + département + poste, `EmployeeNumber` | `EmployeeNumber` | Unique (1 470 valeurs pour 1 470 lignes) et stable. Le numéro de ligne change si on trie, et une combinaison n'est pas unique |
| Les matricules ne se suivent pas (1 à 2 068) | les renuméroter, les garder | les garder | Un matricule n'est pas un compteur : les numéros des anciens employés ne sont pas réattribués |
| Colonnes constantes (`EmployeeCount`, `Over18`, `StandardHours`) | les supprimer partout, les garder dans le brut | brut seulement, exclues du MDM | Le brut est une copie fidèle. Elles ne distinguent personne |
| `PerformanceRating` ne contient que 3 et 4 | documenter 3 et 4, les 4 niveaux | les 4 niveaux | Les valeurs admises sont exhaustives, même absentes de cette photo |

### Étape 2 : charger les données brutes

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Typer les colonnes au chargement ? | laisser pandas deviner (TP3), tout en texte (guide) | tout en texte (`dtype=str`) | Copie fidèle : une valeur mal formée n'est pas perdue sans bruit, on la détecte au MDM |
| Noms de colonnes `MonthlyIncome` | les garder, snake_case | snake_case | Standard commun. On harmonise les noms, jamais les valeurs |
| Où charger les sources simulées ? | script Python, script SQL du MDM | `sql/31_hr_mdm.sql`, en `data.hr_mobility_raw` et `data.hr_office_raw` | Même règle que les autres sources (une copie brute), même choix qu'Ivan et Junior |

### Étape 3 : documenter

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Aucun nom dans le fichier : PII ? | Non, Oui | **Oui** | Âge + genre + situation familiale + département + poste : 483 employés sur 1 470 (32,9 %) sont seuls dans leur groupe, donc reconnaissables |
| `employee_number` est-il une PII ? | Non, Oui | Oui | Dans l'entreprise, le matricule désigne directement une personne |
| `department`, `job_role` | PII.Sensitive, PII.NonSensitive | NonSensitive | Seuls, ils regroupent 63 à 961 personnes. C'est leur croisement avec l'âge ou le genre qui est interdit |
| `job_level`, `stock_option_level` sans libellé | inventer un sens, documenter l'absence | documenter l'absence | Le Steward n'invente pas un sens métier : point ouvert avec la Direction RH |
| Documenter 3 sources | une fiche commune, une fiche par source | une fiche par source | Origine, volumétrie et classification différentes (même choix que Finance) |

### Étape 4 : cataloguer dans OpenMetadata

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Configurer et enrichir OpenMetadata | à la main, par script | `setup_openmetadata.py` (commun) et `enrich_openmetadata_hr.py` | Catalogue identique sur les 3 machines, rejouable après une réinitialisation |
| Quels textes dans le catalogue ? | les réécrire, reprendre le dictionnaire | reprendre le dictionnaire | Une seule source de vérité |
| L'ingestion échoue (`ReadTimeout` dans Airflow) | réessayer, libérer de la mémoire | arrêter les conteneurs d'un autre projet (SonarQube, Jenkins), relancer | La machine était saturée (4 cœurs, 7,7 Go). Ce n'était pas une erreur de configuration |

### Étape 5 : construire le MDM

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Une seule source réelle pour l'employé | rester à 1 source, ajouter une 2ᵉ | 2ᵉ source simulée : la mobilité interne | Sans 2 sources, il n'y a ni rapprochement ni règle de priorité (exigence de la prof) |
| IBM HR et mobilité se contredisent sur le département et le poste | IBM gagne, mobilité gagne | la mobilité gagne | Elle est plus récente et c'est le système qui gère les changements de poste |
| Un employé a deux mobilités (n° 2 : mars et octobre 2026) | la première, la plus récente | la plus récente | Seule la dernière décision de mobilité est en vigueur. L'ancienne est signalée par Q8 |
| Libellé mal écrit dans la mobilité (` research & development `) | rejeter la ligne, standardiser | standardiser (`TRIM`, comparaison en majuscules) | La valeur est juste, seule l'écriture diffère. L'affichage garde l'écriture officielle du référentiel |
| Mobilité sur un matricule absent d'IBM HR (n° 3) | créer l'employé, l'ignorer en silence, le signaler | ne pas le créer, le signaler (Q8) | Le registre du personnel est IBM HR. Un employé sans genre, formation ni salaire ne serait pas un Golden Record fiable |
| Garder la trace de la source gagnante | une colonne `source` (TP3), une par attribut | une par attribut (`department_source`, `job_role_source`) et `mobility_date` | La règle porte attribut par attribut : on doit savoir d'où vient chaque valeur (même choix que Finance) |
| Le poste Manager existe dans les 3 départements | poste rattaché au département, référentiel indépendant | référentiel indépendant (`master.job_role`) | Sinon « Manager » existerait 3 fois |
| Âge, salaire, attrition dans le Golden Record ? | oui, non | non : `data.hr_employee_facts` | Ce sont des faits qui changent ou des événements. Le Golden Record doit rester stable |
| Rejouer le script | `DO NOTHING` puis `UPDATE` (TP3), `INSERT ... ON CONFLICT DO UPDATE` | `ON CONFLICT DO UPDATE` en une seule requête | Si la mobilité change ou disparaît, le Golden Record revient à la bonne valeur. Avec le TP3, un ancien `MOBILITY` restait |
| Pays des sites (`MA`) : `ref.country` appartient à Finance | créer `ref.country` soi-même, clé étrangère, contrôle | contrôle Q9, sans clé étrangère | On ne modifie pas le référentiel d'un autre membre (contrat). Sans les données SEC, `ref.country` n'existe pas sur cette machine : Q9 le signale |
| Classification des nouvelles tables | Confidential partout, table par table | table par table | `master.employee` et les faits contiennent des PII : Confidential, High. Départements, postes, sites et codes : Internal, Low |

## Contrôles qualité (`sql/32_hr_quality.sql`)

| Contrôle | Ce qu'il vérifie | Résultat (2026-11-04) |
|---|---|---|
| Q1 | Un matricule n'apparaît qu'une fois | 0 doublon |
| Q2 | Exhaustivité : source, Golden Record et faits | 1 470 / 1 470 / 1 470 |
| Q3 | Complétude des attributs maîtres (seuil 95 %) | 100 % partout |
| Q4 | Règle de priorité appliquée, avec la source gagnante | 4 employés (1, 2, 4, 5) en `MOBILITY` |
| Q5 | Postes présents dans plusieurs départements | Manager (3 départements) |
| Q6 | Agrégat que le HR Agent pourra donner | Attrition : Sales 20,4 %, Human Resources 20,3 %, R&D 13,9 % |
| Q7 | Validité des codes par rapport aux référentiels | 0 code invalide, 0 mineur |
| Q8 | Lignes de mobilité non appliquées, avec la raison | n° 3 (matricule inconnu), n° 2 de mars (remplacée par octobre) |
| Q9 | Pays des sites dans `ref.country` (Finance) | Non vérifié : `ref.country` absent sur cette machine |

## Points ouverts

- `job_level` (1 à 5) et `stock_option_level` (0 à 3) n'ont pas de libellé officiel : à demander à la Direction RH avant de créer des tables `ref`.
- Q9 : rejouer après `sql/11_finance_mdm.sql` (membre Finance) pour vérifier le pays `MA`.
- Q6 calcule l'attrition avec le département **actuel** (après mobilité), alors que l'attrition vient de la photo IBM. Avec 4 employés concernés l'effet est négligeable, mais en partie 2 il faudra choisir : département au moment du départ, ou département actuel.
- La mobilité de l'employé 5 confirme son département (R&D) et change seulement son poste : `department_source = MOBILITY` signifie « confirmé par la mobilité », même si la valeur ne change pas.
