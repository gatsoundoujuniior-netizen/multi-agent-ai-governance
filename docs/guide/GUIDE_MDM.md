# Guide : réaliser son MDM, étape par étape

Ce guide décrit comment le membre Finance a construit son MDM (TP1), pour qu'Ivan (Investment, TP2) et Mohammed (HR, TP3) construisent le leur de la même façon. Chaque étape donne : le concept du cours, ce qu'il faut faire, l'exemple Finance, puis un tableau des problèmes rencontrés et des choix faits. Remplacez l'exemple Finance par votre dataset.

Résultat obtenu côté Finance : un golden record `master.company` de 8 485 entreprises, construit à partir de **3 sources** rapprochées par le CIK, avec un pays renseigné à 98,8 % (49 % avec une seule source).

## Sommaire

1. [Ce que la prof attend](#1-ce-que-la-prof-attend)
2. [Standards communs et contrats entre membres](#2-standards-communs-et-contrats-entre-membres)
3. [Étape 0 : préparer sa machine](#3-étape-0--préparer-sa-machine)
4. [Étape 1 : découvrir le dataset](#4-étape-1--découvrir-le-dataset)
5. [Étape 2 : charger les données brutes](#5-étape-2--charger-les-données-brutes)
6. [Étape 3 : documenter (fiche catalogue et dictionnaire)](#6-étape-3--documenter-fiche-catalogue-et-dictionnaire)
7. [Étape 4 : cataloguer dans OpenMetadata](#7-étape-4--cataloguer-dans-openmetadata)
8. [Étape 5 : construire le MDM](#8-étape-5--construire-le-mdm)
9. [Problèmes techniques rencontrés](#9-problèmes-techniques-rencontrés)
10. [Ce qui change pour Ivan et pour Mohammed](#10-ce-qui-change-pour-ivan-et-pour-mohammed)
11. [Check-list par membre](#11-check-list-par-membre)

---

## 1. Ce que la prof attend

| Exigence | Ce que cela veut dire concrètement |
|---|---|
| 3 MDM, un par membre | Finance : Tiers et Structures. Investment : Produits. HR : Ressources humaines |
| Plusieurs sources par MDM | La même entité doit venir d'**au moins 2 sources**. Sans 2 sources, il n'y a rien à rapprocher ni de règle de priorité à appliquer |
| Attributs stables et partagés | On garde ce qui décrit l'entité (nom, pays, profil de risque), pas les transactions (montants, cours, salaires) |
| Justifier chaque choix | Pour chaque décision : le problème, les options, le choix, la raison. C'est le rôle des tableaux de ce guide |

Les notions du cours sont expliquées dans le document d'équipe *Comprendre nos 3 MDM* (lien partagé sur le groupe).

## 2. Standards communs et contrats entre membres

### Standards (décidés au TP0, à respecter par tous)

| Sujet | Standard |
|---|---|
| Schémas PostgreSQL | `ref` (codes de référence), `master` (golden records), `data` (brut et transactionnel), `gov` (gouvernance, partie 2) |
| Tables brutes | `data.<source>_raw`, copie fidèle, tout en texte, aucune correction |
| Nommage | minuscules, `snake_case`, clé primaire `<entite>_id` |
| Dates | `YYYY-MM-DD` dans les données nettoyées |
| Classification | `Confidentialite` : Public, Internal, Confidential, Restricted. `Sensibilite` : Low, Medium, High. PII : `PII.Sensitive`, `PII.NonSensitive` |
| Qualité | 95 % de complétude minimum, 1 % de doublons maximum |
| Fichiers | `scripts/load_<dataset>.py`, `sql/1x_finance_*.sql`, `sql/2x_investment_*.sql`, `sql/3x_hr_*.sql`, `docs/dictionnaire/<dataset>.md` |
| Data Owner | toujours une direction métier (équipe OpenMetadata de type **Group**), jamais l'IT |
| Branches | `finance`, `investment`, `hr`, PR vers `main` relue par un autre membre |

### Contrats entre membres

| Table | Propriétaire | Utilisée par | Colonnes stables |
|---|---|---|---|
| `master.company` | Finance | Investment | `company_id`, `cik` (texte, **10 chiffres**), `legal_name`, `country` (ISO 2 lettres), `sic_code` |
| `data.sec_company_tickers_raw` | Finance | Investment | `cik_str`, `ticker`, `title` : la correspondance ticker → CIK |
| `ref.country`, `ref.currency` | Finance | Tous | `code`, `label` |
| `ref.sector` (GICS) | Investment | Tous | `sector_id`, `label` |

Une colonne du contrat ne change jamais sans prévenir l'autre membre. Ajouter une colonne est permis (Finance a ajouté `name_source`, `country_source`, `sic_source`).

## 3. Étape 0 : préparer sa machine

```powershell
copy .env.example .env                       # puis mettre son mot de passe PostgreSQL
docker compose up -d --wait                  # PostgreSQL du projet, port 5433
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

OpenMetadata (quickstart 2.0.1) se lance avec `docker compose -f openmetadata/docker-compose.yml up --detach --wait`. Le premier démarrage prend 5 à 15 minutes. Ensuite, **une seule commande** crée la configuration commune, identique sur les 3 machines :

```powershell
.\.venv\Scripts\python.exe scripts/setup_openmetadata.py
```

Elle crée les classifications `Confidentialite` et `Sensibilite`, les équipes Direction Finance, Investissement et RH, les domaines, le `Glossaire Projet`, le service `gouv_postgres`, et lance l'ingestion des schémas `data`, `master` et `ref`. Elle peut être relancée sans danger, par exemple après le chargement de nouvelles tables.

**Si OpenMetadata ne marche pas sur votre machine** (la prof a confirmé que ce n'est pas bloquant) : gardez la fiche catalogue et le dictionnaire en Markdown dans `docs/dictionnaire/`, et ajoutez les descriptions dans PostgreSQL avec `COMMENT ON TABLE data.xxx IS '...'` et `COMMENT ON COLUMN ...`. Les mêmes notions (métadonnées métier, gouvernance) restent démontrées.

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Refaire la configuration du TP0 sur 3 machines sans faute de frappe | a) à la main dans l'interface, b) par script | b) `setup_openmetadata.py` | Le TP0 exige des catalogues identiques au caractère près. Un script donne exactement le même résultat partout, en une minute |
| OpenMetadata refuse une équipe *Department* comme owner | a) garder Department et ne pas mettre d'owner, b) passer les équipes en *Group* | b) | Dans OpenMetadata, seule une équipe *Group* peut posséder un actif. Le TP0 disait Department : c'est corrigé dans le script |

## 4. Étape 1 : découvrir le dataset

**Concept.** On inspecte les vraies données avant de construire quoi que ce soit. Regarder les colonnes, c'est déjà produire des métadonnées techniques et opérationnelles.

**À faire.** Télécharger le dataset dans `data/raw/` (ignoré par Git), écrire un script qui affiche les colonnes et un échantillon (`scripts/explore_sec.py` côté Finance), noter les colonnes de liaison et la clé de l'entité.

**Exemple Finance.** 4 fichiers SEC : `sub.txt` (6 169 dépôts), `num.txt` (3,7 millions de montants, 560 Mo), `tag.txt` (plan de comptes), `pre.txt` (non utilisé).

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Quel trimestre SEC prendre ? | un trimestre récent au hasard, ou celui qui contient le plus de rapports annuels | 2026q1 | La plupart des entreprises déposent leur rapport annuel au premier trimestre : 4 262 10-K sur 6 169 dépôts |
| `num.txt` fait 560 Mo | l'ouvrir en entier, ou lire un échantillon | échantillon (`nrows=5000`) | Les colonnes suffisent pour comprendre la structure. On ne traite en entier que ce dont on a besoin |
| Comment relier un montant à son entreprise ? | par le nom, ou par une colonne commune | `adsh` | Numéro unique du dépôt, présent dans `num` et `sub` |
| Quelle clé pour l'entreprise ? | le nom, ou le CIK | le CIK | Le nom change (Enerpac s'appelait Actuant), le CIK jamais |

**Pour vous.** Trouvez votre clé métier : Ivan, le ticker. Mohammed, le matricule `EmployeeNumber`. Vérifiez qu'elle ne change pas dans le temps.

## 5. Étape 2 : charger les données brutes

**Concept.** On charge une copie **brute** (`data.<source>_raw`) : mêmes colonnes, tout en texte, aucune correction. Les corrections viennent dans le MDM. La copie brute sert à tracer la provenance (lineage), à rejouer le MDM après une erreur et à auditer.

**À faire.** Un script `scripts/load_<dataset>.py` qui filtre les lignes utiles et écrit les tables dans le schéma `data`. Vérifier avec `SELECT COUNT(*)` : ces nombres sont des métadonnées opérationnelles.

**Exemple Finance.**

| Table brute | Source | Filtre | Lignes |
|---|---|---|---|
| `data.sec_sub_raw` | `sub.txt` | 10-K | 4 262 |
| `data.sec_num_raw` | `num.txt` | 8 tags us-gaap, USD, sans ventilation | 64 253 |
| `data.sec_tag_raw` | `tag.txt` | 8 tags, `custom = 0` | 27 |
| `data.sec_company_tickers_raw` | `company_tickers.json` (SEC) | aucun | 10 423 |
| `data.sec_submissions_raw` | API EDGAR Submissions (SEC) | entreprises sans 10-K | 4 224 |

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Garder une version non corrigée ? | corriger directement au chargement, ou garder du brut | brut | Traçabilité, possibilité de rejouer le MDM et d'auditer chaque valeur |
| Quels rapports garder ? | tous, 10-K, 10-Q | 10-K | Chiffres annuels comparables. 10-Q = 3 mois, 20-F = normes étrangères |
| Quels montants garder ? | tous, nos tags, nos tags + USD + total | nos tags + USD + total | Pas de devises mélangées, pas de double comptage des ventilations (`segments`) |
| Où ranger les tables brutes ? | `master` ou `data` | `data` | `master` signifie « validé ». Le brut contient des doublons et des formats non standardisés |
| 2 lignes mal formées dans `num.txt` (11 colonnes au lieu de 10) | arrêter le chargement, ou écarter en signalant | écarter et signaler (`on_bad_lines="warn"`) | 2 lignes sur 3,7 millions, hors périmètre. On trace au lieu de bloquer |
| Filtrer la liste des tickers comme `sub.txt` ? | filtrer, ou tout garder | tout garder | Le référentiel doit être complet : Apple et 5 417 autres n'ont pas de 10-K ce trimestre |

## 6. Étape 3 : documenter (fiche catalogue et dictionnaire)

**Concept.** Les 4 types de métadonnées, avec une question pour chacun :

| Type | Question | Exemple Finance |
|---|---|---|
| Technique | Comment c'est rangé ? | `value` est un nombre décimal |
| Métier | Qu'est-ce que ça veut dire ? | « Montant déclaré par l'entreprise pour un poste et une date » |
| Opérationnelle | D'où ça vient, combien, quand ? | Source SEC 2026q1, 64 253 lignes, chargé le 2026-11-02 |
| Gouvernance | Qui décide, quelles règles ? | Owner Direction Finance, Public, PII Non |

La **fiche catalogue** décrit le dataset entier. Le **dictionnaire** décrit chaque colonne. Les 4 règles de rédaction : définition en phrase complète sans jargon, règle de gestion qui commence par un verbe et se vérifie, valeurs admises exhaustives, propriétaire = une direction métier.

**À faire.** `docs/dictionnaire/<dataset>.md`. Modèle à copier : [docs/dictionnaire/sec_financial_statements.md](../dictionnaire/sec_financial_statements.md) (2 fiches, 14 colonnes, observations pour le MDM).

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Le dataset SEC contient noms, adresses, téléphones : PII ? | Oui ou Non | Non | Ce sont des **entreprises** (personnes morales). On juge colonne par colonne : le téléphone d'un dirigeant serait une PII |
| Documenter une 2ᵉ source ajoutée après coup ? | même fiche, fiche séparée, ne pas documenter | une fiche par source, dans le même fichier | Mêmes owner et classification, mais format, fréquence et filtre différents |

**Pour vous.** Mohammed : c'est l'étape la plus importante pour vous. Âge, genre, situation familiale et salaire sont des PII même sans nom, parce que combinés ils identifient une personne.

## 7. Étape 4 : cataloguer dans OpenMetadata

**Concept.** L'ingestion remplit seule le technique et l'opérationnel. Le Data Steward ajoute le métier (descriptions, glossaire) et la gouvernance (owner, domaine, tags).

**À faire.** Relancer `setup_openmetadata.py` pour ingérer vos nouvelles tables, puis enrichir vos tables. Côté Finance, un script reprend la fiche et le dictionnaire : `scripts/enrich_openmetadata_finance.py`. Copiez-le en `enrich_openmetadata_<votre_domaine>.py` et changez les textes.

**Exemple Finance.** Les 4 tables brutes ont : description, owner Direction Finance, domaine Finance, tags `Confidentialite.Public` et `Sensibilite.Low`. Des colonnes clés ont leur description, `PII.NonSensitive`, et un terme du glossaire (Company, CIK, Revenue, XBRL Tag).

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| Quels schémas ingérer ? | tous, ou `data`, `master`, `ref` | `data`, `master`, `ref` | `gov` contiendra les règles d'accès et l'audit : les afficher dans un catalogue ouvert à tous aiderait à contourner la sécurité |

## 8. Étape 5 : construire le MDM

**Concept.** Un MDM rapproche la même entité venue de plusieurs sources et publie **une seule version qui fait autorité** : le golden record. Cinq étapes :

1. **Charger** l'entité depuis au moins 2 sources.
2. **Standardiser** les formats (clé, codes pays, majuscules pour comparer).
3. **Rapprocher et dédoublonner** grâce à la clé métier : une ligne par entité.
4. **Appliquer les règles de priorité**, attribut par attribut, et garder la trace de la source gagnante.
5. **Publier** : les données transactionnelles pointent vers le golden record.

**Choisir les entités avec les 5 tests** (nature, volatilité, réutilisation, partage, criticité). Une entreprise passe les 5 tests : Master Data. Un montant est un événement daté : donnée transactionnelle, qui va dans `data.sec_financial_facts` et pointe vers `master.company`.

**Clé métier ou attribut.** La clé (le CIK) sert à **reconnaître** l'entité et ne change jamais. Les attributs (nom, pays) **décrivent** l'entité et peuvent changer : c'est sur eux que portent les règles de priorité.

**Master Data ou Reference Data.** `master` contient des entités construites par nos règles (`master.company`). `ref` contient des listes de codes officielles importées telles quelles (`ref.country` ISO, `ref.sic`, `ref.edgar_location`).

### Exemple Finance : `sql/11_finance_mdm.sql`

```
 sec_sub_raw (10-K)   sec_company_tickers_raw   sec_submissions_raw (EDGAR)
        \                      |                        /
         \__________ rapprochement par le CIK (10 chiffres) __/
                               |
                        master.company   (1 ligne par CIK, 8 485 entreprises)
                         /           \
     ref.country, ref.sic             data.sec_financial_facts (63 937 montants)
```

| Attribut | Règle de priorité | Raison |
|---|---|---|
| Nom | liste des tickers, puis dépôt 10-K, puis EDGAR | `sub.txt` garde le nom au moment du dépôt. 107 entreprises ont changé de nom depuis (LendingClub est devenue Happen) |
| Pays | dépôt 10-K, puis EDGAR (code traduit en ISO) | La liste des tickers n'a pas de pays |
| Secteur (SIC) | dépôt 10-K, puis EDGAR | Idem |
| Pour un même CIK dans `sub` | le dépôt le plus récent gagne | Une entreprise a déposé deux 10-K dans le trimestre |

Les colonnes `name_source`, `country_source` et `sic_source` indiquent la source gagnante pour chaque valeur. Exemple : Apple a `name_source = TICKERS` et `country_source = EDGAR`.

| Problème rencontré | Options | Choix | Justification |
|---|---|---|---|
| CIK écrit sur 4 à 7 chiffres selon la source | comparer tel quel, ou standardiser | standardiser sur 10 chiffres (`LPAD`) | Sinon `14846` et `0000014846` donnent deux entreprises |
| Le MDM n'avait qu'une source | rester à 1 source, ajouter une 2ᵉ | 2ᵉ source : `company_tickers.json` | Officielle, autre système que les dépôts, CIK commun, ticker utile à Investment. GLEIF écarté : pas de CIK, rapprochement par le nom impossible |
| Une entreprise a plusieurs tickers (GOOGL, GOOG) | une ligne par ticker, ou par CIK | une ligne par CIK | Le golden record représente l'entreprise. Les titres vont dans `master.security` (Investment) : relation 1-N |
| Écriture du nom | tout en majuscules, ou écriture officielle | écriture officielle de la source gagnante | On ne déforme pas un nom officiel. On standardise pour comparer, pas pour afficher |
| Pays renseigné pour 49 % des entreprises seulement (standard : 95 %) | retirer les entreprises sans pays, mesurer à part, ajouter une 3ᵉ source | 3ᵉ source : API EDGAR Submissions | On règle le problème à la source au lieu de le cacher. Résultat : 98,8 % |
| EDGAR écrit `CA` (Californie) ou `M0` (Japon), pas des codes ISO | ignorer le pays EDGAR, ou traduire | table `ref.edgar_location` (code EDGAR vers ISO) | Une table de Reference Data donne un sens officiel aux codes |
| Classification de `master.company` | Public comme les sources, ou Internal | Internal | Le référentiel est le résultat de nos règles : un actif interne. La classification s'applique à chaque table |

### Résultat

| Mesure | Valeur |
|---|---|
| Entreprises dans `master.company` | 8 485 |
| Pays renseigné | 98,8 % (49 % avec une seule source) |
| Secteur renseigné | 85,7 % (point ouvert, voir ci-dessous) |
| Comptes du plan XBRL (`master.xbrl_account`) | 8 |
| Montants reliés au golden record | 63 937 |

**Points ouverts côté Finance** : les entreprises sans code SIC sont surtout des fonds, des trusts et des ADR, à qui la SEC n'attribue pas de secteur (décision à prendre) ; contrôles qualité `sql/12_finance_quality.sql` ; documentation de `master.company` dans OpenMetadata.

## 9. Problèmes techniques rencontrés

| Problème | Cause | Solution |
|---|---|---|
| OpenMetadata redémarre en boucle | La migration de la base interne n'avait jamais tourné (conteneurs manquants) | Relancer `docker compose up --detach --wait`, puis redémarrer `openmetadata_server` une fois la migration terminée |
| Mot de passe admin OpenMetadata perdu | Changé puis oublié | Catalogue vide : réinitialisation complète (supprimer la base interne et l'index Elasticsearch, relancer). Noter le mot de passe hors de Git |
| `docker` ne répond plus | Moteur Docker Desktop bloqué après plusieurs jours | Quitter Docker Desktop, `wsl --shutdown`, relancer Docker Desktop. Relancer ensuite `gouv_postgres` (`docker compose up -d --wait`) et la pile OpenMetadata |
| Elasticsearch trop lent au démarrage | `--wait` abandonne avant qu'il soit prêt | Relancer `docker compose up --detach --wait` une deuxième fois |
| L'ingestion ne se déclenche pas juste après sa création | Airflow n'a pas encore lu le pipeline déployé | Attendre 15 secondes avant de déclencher (fait dans le script) |
| Téléchargement EDGAR coupé (serveur ou changement de connexion) | Coupure réseau | Le script réessaie 5 fois et ne retélécharge que les fichiers manquants |
| Accès aux API de la SEC | La SEC exige que chaque programme s'identifie | Variable `SEC_USER_AGENT` dans `.env` |

## 10. Ce qui change pour Ivan et pour Mohammed

### Ivan (Investment, MDM Produits)

- Entité principale : `master.security`, clé : le ticker (standardisé : `BRK.B` et `BRK-B` sont le même titre).
- Vos 2 sources pour Security : la liste officielle du S&P 500 (prioritaire) et les tickers vus dans l'historique des cours.
- Lien avec Finance : chaque titre pointe vers `master.company` par le CIK sur 10 chiffres. La table `data.sec_company_tickers_raw` donne la correspondance ticker → CIK pour les titres absents de votre liste.
- Point à traiter : `master.investor` (profil de risque, l'exemple de la prof) n'a qu'une source simulée. Prévoir une 2ᵉ source et une règle de priorité sur `risk_profile`.
- Classification : Internal, Medium, pas de PII (investisseurs institutionnels).

### Mohammed (HR, MDM Ressources humaines)

- Entité principale : `master.employee`, clé : le matricule.
- Vos 2 sources : le fichier IBM HR et la mobilité interne simulée (`hr_mobility.csv`), qui gagne pour le département et le poste car elle est plus récente.
- Attribut maître contre fait : département et poste vont dans le MDM, salaire, âge, satisfaction et attrition vont dans `data.hr_employee_facts`.
- Nom du MDM : dans le cours, le type « Ressources » désigne les équipements et les sites. À l'oral, présentez « MDM Ressources humaines » comme un référentiel de **type Tiers** (domaine Parties), les sites (Office) relevant du type Ressources.
- Classification : Confidential, High, PII sur l'âge, le genre, la situation familiale et le salaire.

## 11. Check-list par membre

- [ ] Dataset téléchargé dans `data/raw/`, exploré, clé métier identifiée
- [ ] Tables brutes `data.<source>_raw` chargées, volumétrie notée
- [ ] Au moins 2 sources pour l'entité principale du MDM
- [ ] `docs/dictionnaire/<dataset>.md` : fiche catalogue (une par source) et dictionnaire (8 colonnes minimum)
- [ ] `setup_openmetadata.py` lancé, tables enrichies (description, owner, domaine, tags, glossaire), ou plan B Markdown
- [ ] 5 tests appliqués et écrits dans le compte rendu
- [ ] Script MDM `sql/<n>x_<domaine>_mdm.sql` : standardisation, rapprochement, règles de priorité, colonnes de source
- [ ] Contrôles qualité : unicité, complétude (95 %), validité
- [ ] Un tableau problème / options / choix / justification pour chaque étape
- [ ] Commit sur sa branche, PR vers `main` relue par un autre membre
