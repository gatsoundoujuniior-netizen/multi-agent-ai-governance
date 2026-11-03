# Dataset `ibm_hr_analytics`

Fiche catalogue et dictionnaire de données du dataset RH (membre HR, TP3 étape 3).
Le MDM Ressources humaines a trois sources : le fichier IBM HR (fiche 1), la mobilité interne simulée (fiche 2), qui est la deuxième source de l'employé, et les sites simulés (fiche 3).

## Fiche 1 : dossiers employés IBM HR

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Dossiers employés : attrition et performance |
| Métier | Description | Photo des 1 470 employés d'une entreprise à une date donnée : poste, département, formation, rémunération, satisfaction, performance, ancienneté, et départ ou non de l'entreprise (attrition). Il alimente le HR Agent, qui répond à des questions agrégées comme « quel département a le plus fort taux d'attrition ? », et le MDM Ressources humaines. |
| Métier | Domaine | RH |
| Technique | Table | `data.hr_employee_raw` |
| Technique | Format source | CSV, séparateur virgule, encodage UTF-8, 35 colonnes, tout chargé en texte |
| Opérationnelle | Source | Kaggle, « IBM HR Analytics Employee Attrition & Performance », fichier `WA_Fn-UseC_-HR-Employee-Attrition.csv` (dataset fictif créé par IBM, traité comme réel) |
| Opérationnelle | Fréquence de mise à jour | Aucune (photo unique) |
| Opérationnelle | Date de chargement | 2026-11-03, script `scripts/load_hr.py` |
| Opérationnelle | Volumétrie | 1 470 lignes, 1 470 matricules distincts, aucune valeur manquante, aucun doublon |
| Opérationnelle | Filtre appliqué | Aucun. Seuls les noms de colonnes passent en snake_case |
| Gouvernance | Data Owner | Direction RH |
| Gouvernance | Data Steward | Mohamed Traoré (membre HR) |
| Gouvernance | Classification | Confidential |
| Gouvernance | Sensibilité | High |
| Gouvernance | PII | Oui : `employee_number`, `age`, `gender`, `marital_status`, `monthly_income`, `daily_rate`, `hourly_rate`, `monthly_rate` (voir l'analyse PII) |

## Fiche 2 : mobilité interne (source simulée)

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Changements de poste validés par la mobilité interne |
| Métier | Description | Liste des employés qui ont changé de département ou de poste, avec la date d'effet. Elle est la deuxième source du MDM Ressources humaines : plus récente que le fichier IBM HR, elle gagne pour le département et le poste de l'employé. |
| Métier | Domaine | RH |
| Technique | Table | `data.hr_mobility_raw` (créée par `sql/31_hr_mdm.sql`) |
| Technique | Format source | CSV `data/seed/hr_mobility.csv`, séparateur virgule, tout chargé en texte |
| Opérationnelle | Source | Données **simulées** pour le projet (logiciel de mobilité interne fictif) |
| Opérationnelle | Fréquence de mise à jour | À chaque mobilité (événementielle) |
| Opérationnelle | Volumétrie | 3 lignes (employés 1, 2 et 4) |
| Gouvernance | Data Owner | Direction RH |
| Gouvernance | Data Steward | Mohamed Traoré (membre HR) |
| Gouvernance | Classification | Confidential |
| Gouvernance | Sensibilité | Medium (pas de salaire ni de donnée démographique, mais une décision individuelle sur une personne) |
| Gouvernance | PII | Oui : `employee_number` |

## Fiche 3 : sites de l'entreprise (source simulée)

| Type | Attribut | Valeur |
|---|---|---|
| Métier | Nom métier | Sites de l'entreprise |
| Métier | Description | Liste des bureaux où sont rattachés les départements. Le dataset IBM HR ne contient aucun lieu : cette petite table illustre le type de MDM Ressources (les sites). |
| Métier | Domaine | RH |
| Technique | Table | `data.hr_office_raw` (créée par `sql/31_hr_mdm.sql`) |
| Technique | Format source | CSV `data/seed/office.csv`, séparateur virgule, tout chargé en texte |
| Opérationnelle | Source | Données **simulées** pour le projet |
| Opérationnelle | Volumétrie | 3 lignes (Casablanca, Rabat, Tanger) |
| Gouvernance | Data Owner | Direction RH |
| Gouvernance | Data Steward | Mohamed Traoré (membre HR) |
| Gouvernance | Classification | Internal |
| Gouvernance | Sensibilité | Low |
| Gouvernance | PII | Non (aucune personne) |

## Analyse PII : pourquoi ce dataset contient des données personnelles sans contenir de nom

Une PII est une information qui permet d'identifier une personne **seule ou combinée** avec d'autres. Aucune colonne ne contient de nom, mais plusieurs colonnes, combinées, désignent une seule personne. Mesures faites sur `data.hr_employee_raw` le 2026-11-03 :

| Combinaison de colonnes | Employés seuls dans leur groupe (donc reconnaissables) |
|---|---|
| âge + genre + situation familiale + département | 136 sur 1 470 (9,3 %) |
| âge + genre + situation familiale + département + poste | 483 sur 1 470 (32,9 %) |
| salaire mensuel seul | 1 349 valeurs différentes pour 1 470 employés |
| poste Manager dans le département Human Resources | 11 personnes seulement (4 femmes, 7 hommes) |

| Colonne | Classement | Justification |
|---|---|---|
| `employee_number` | PII.Sensitive | Identifiant direct : dans l'entreprise, le matricule désigne une seule personne |
| `age`, `gender`, `marital_status` | PII.Sensitive | Quasi-identifiants : combinés au département ou au poste, ils désignent une personne (tableau ci-dessus) |
| `monthly_income`, `daily_rate`, `hourly_rate`, `monthly_rate` | PII.Sensitive | Rémunération : presque unique par personne, et sa divulgation cause un tort direct à l'employé |
| `department`, `job_role`, `attrition` | PII.NonSensitive | Seuls, ils ne désignent personne (63 à 961 employés par département). Ils restent des quasi-identifiants : l'agrégat par département est autorisé, pas le croisement avec l'âge ou le genre |

**Règle prévue pour la partie 2 :** le HR Agent peut obtenir un agrégat (taux d'attrition par département), où aucune personne n'est visible. Une demande portant sur une colonne `PII.Sensitive` d'un employé précis est refusée.

## Dictionnaire de données

### Table `data.hr_employee_raw` (un employé par ligne)

Toutes les colonnes sont stockées en texte dans la table brute. La colonne « Type » donne le type métier, appliqué dans le MDM.

#### Identité et organisation (attributs maîtres, vont dans `master.employee`)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `employee_number` | Matricule | Numéro unique attribué à l'employé par l'entreprise | Entier | NOT NULL, unique | Entier positif, de 1 à 2 068 (les numéros ne se suivent pas : 599 numéros non utilisés) | Doit identifier un seul employé dans `master.employee` et ne jamais être réattribué | **Oui** |
| `gender` | Genre | Genre déclaré de l'employé | Texte | NOT NULL | `Female`, `Male` | Ne doit jamais être croisé avec l'âge et le département dans une réponse hors Direction RH | **Oui** |
| `marital_status` | Situation familiale | Situation matrimoniale déclarée de l'employé | Texte | NOT NULL | `Single` (célibataire), `Married` (marié), `Divorced` (divorcé) | Ne doit jamais être communiquée individuellement hors Direction RH | **Oui** |
| `department` | Département | Unité de l'organisation à laquelle l'employé est rattaché | Texte | NOT NULL | `Sales` (446), `Research & Development` (961), `Human Resources` (63) | Doit exister dans le référentiel `master.department` | Non |
| `job_role` | Poste | Fonction occupée par l'employé | Texte | NOT NULL | 9 postes : Sales Executive, Sales Representative, Research Scientist, Laboratory Technician, Manufacturing Director, Healthcare Representative, Research Director, Manager, Human Resources | Doit exister dans `master.job_role`. Un même poste peut exister dans plusieurs départements (Manager est dans les 3) | Non |
| `job_level` | Niveau hiérarchique | Échelon de l'employé dans la grille de l'entreprise | Entier | NOT NULL | 1 à 5, du plus bas au plus haut. **Aucun libellé officiel** dans la source | Doit être compris entre 1 et 5. Libellés à demander à la Direction RH | Non |
| `education` | Niveau d'études | Plus haut diplôme obtenu par l'employé | Entier (code) | NOT NULL | 1 = Below College, 2 = College, 3 = Bachelor, 4 = Master, 5 = Doctor | Doit exister dans `ref.education_level` | Non |
| `education_field` | Filière d'études | Domaine du diplôme de l'employé | Texte | NOT NULL | Life Sciences, Medical, Marketing, Technical Degree, Human Resources, Other | Doit exister dans `master.education_field` | Non |

#### Rémunération (faits, vont dans `data.hr_employee_facts`)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `monthly_income` | Salaire mensuel | Rémunération brute mensuelle de l'employé | Entier (USD) | NOT NULL | Nombre strictement positif (de 1 009 à 19 999) | Ne doit jamais être communiqué individuellement hors Direction RH | **Oui** |
| `daily_rate` | Taux journalier | Coût journalier de l'employé pour l'entreprise | Entier (USD) | NOT NULL | Nombre strictement positif (de 102 à 1 499) | Ne doit jamais être communiqué individuellement hors Direction RH | **Oui** |
| `hourly_rate` | Taux horaire | Coût horaire de l'employé pour l'entreprise | Entier (USD) | NOT NULL | Nombre strictement positif (de 30 à 100) | Ne doit jamais être communiqué individuellement hors Direction RH | **Oui** |
| `monthly_rate` | Taux mensuel | Coût mensuel de l'employé pour l'entreprise (différent du salaire mensuel) | Entier (USD) | NOT NULL | Nombre strictement positif (de 2 094 à 26 999) | Ne doit jamais être communiqué individuellement hors Direction RH | **Oui** |
| `percent_salary_hike` | Augmentation de salaire | Pourcentage d'augmentation obtenu lors de la dernière révision | Entier (%) | NOT NULL | De 11 à 25 | Doit être compris entre 0 et 100 | Non |
| `stock_option_level` | Niveau de stock-options | Niveau d'attribution d'actions de l'entreprise | Entier | NOT NULL | 0 à 3 (0 = aucune). **Aucun libellé officiel** dans la source | Doit être compris entre 0 et 3 | Non |

#### Situation et satisfaction (faits, vont dans `data.hr_employee_facts`)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `age` | Âge | Âge de l'employé à la date de la photo | Entier (années) | NOT NULL | De 18 à 60 | Doit être d'au moins 18 ans. Ne doit jamais être croisé avec le genre et le département hors Direction RH | **Oui** |
| `attrition` | Départ de l'employé | Indique si l'employé a quitté l'entreprise | Texte | NOT NULL | `Yes` = a quitté (237), `No` = toujours présent (1 233) | Doit être converti en booléen dans le MDM. Ne doit être communiqué qu'en taux agrégé (par département, par poste) | Non |
| `over_time` | Heures supplémentaires | Indique si l'employé fait des heures supplémentaires | Texte | NOT NULL | `Yes`, `No` | Doit être converti en booléen dans le MDM | Non |
| `business_travel` | Fréquence des déplacements | Fréquence des voyages professionnels de l'employé | Texte | NOT NULL | `Non-Travel` (jamais), `Travel_Rarely` (rarement), `Travel_Frequently` (souvent) | Doit prendre une des 3 valeurs admises | Non |
| `distance_from_home` | Distance domicile-travail | Distance entre le domicile de l'employé et son lieu de travail | Entier | NOT NULL | De 1 à 29 (unité non précisée par la source) | Doit être positive | Non |
| `environment_satisfaction` | Satisfaction envers l'environnement de travail | Note donnée par l'employé à son environnement de travail | Entier (code) | NOT NULL | 1 = Low, 2 = Medium, 3 = High, 4 = Very High | Doit exister dans `ref.satisfaction_level` | Non |
| `job_satisfaction` | Satisfaction envers le poste | Note donnée par l'employé à son poste | Entier (code) | NOT NULL | 1 = Low, 2 = Medium, 3 = High, 4 = Very High | Doit exister dans `ref.satisfaction_level` | Non |
| `relationship_satisfaction` | Satisfaction envers les relations de travail | Note donnée par l'employé à ses relations avec ses collègues | Entier (code) | NOT NULL | 1 = Low, 2 = Medium, 3 = High, 4 = Very High | Doit exister dans `ref.satisfaction_level` | Non |
| `job_involvement` | Implication dans le poste | Niveau d'implication de l'employé dans son travail | Entier (code) | NOT NULL | 1 = Low, 2 = Medium, 3 = High, 4 = Very High | Doit exister dans `ref.satisfaction_level` | Non |
| `work_life_balance` | Équilibre vie pro / vie perso | Note donnée par l'employé à l'équilibre entre travail et vie personnelle | Entier (code) | NOT NULL | 1 = Bad, 2 = Good, 3 = Better, 4 = Best | Doit exister dans `ref.work_life_balance` | Non |
| `performance_rating` | Évaluation de la performance | Note annuelle de performance donnée par le manager | Entier (code) | NOT NULL | 1 = Low, 2 = Good, 3 = Excellent, 4 = Outstanding (seuls 3 et 4 sont présents : 1 244 et 226) | Doit exister dans `ref.performance_rating` | Non |
| `years_at_company` | Ancienneté | Nombre d'années passées dans l'entreprise | Entier (années) | NOT NULL | De 0 à 40 | Doit être inférieure ou égale à `total_working_years` | Non |

Les autres colonnes de durée (`total_working_years`, `years_in_current_role`, `years_since_last_promotion`, `years_with_curr_manager`, `num_companies_worked`, `training_times_last_year`) sont des entiers positifs, non personnels, repris tels quels dans `data.hr_employee_facts`.

### Table `data.hr_mobility_raw` (un changement de poste par ligne)

| Nom physique | Nom métier | Définition | Type | Contraintes | Valeurs admises | Règle de gestion | PII |
|---|---|---|---|---|---|---|---|
| `employee_number` | Matricule | Matricule de l'employé qui change de poste | Entier | NOT NULL | Doit exister dans `data.hr_employee_raw` | Doit être rapproché du Golden Record par le matricule | **Oui** |
| `department` | Nouveau département | Département de l'employé après la mobilité | Texte | NOT NULL | Un des 3 départements de `master.department` | Doit gagner sur le département du fichier IBM HR | Non |
| `job_role` | Nouveau poste | Poste de l'employé après la mobilité | Texte | NOT NULL | Un des 9 postes de `master.job_role` | Doit gagner sur le poste du fichier IBM HR | Non |
| `effective_date` | Date d'effet | Date à laquelle le changement de poste prend effet | Date (AAAA-MM-JJ) | NOT NULL | Date valide | Doit servir à choisir la mobilité la plus récente si un employé en a plusieurs | Non |

## Colonnes constantes

| Colonne | Valeur unique | Décision | Justification |
|---|---|---|---|
| `employee_count` | 1 | Gardée dans la table brute, non reprise dans le MDM | Même valeur pour les 1 470 employés : elle ne distingue personne et n'apporte aucune information |
| `over18` | Y | Idem | Tous les employés sont majeurs. L'âge (18 à 60) donne déjà cette information |
| `standard_hours` | 80 | Idem | Même durée de travail de référence pour tous |

## Observations pour le MDM (étape 5)

| Constat | Chiffre | Conséquence pour le MDM |
|---|---|---|
| Le matricule est unique et stable | 1 470 matricules pour 1 470 lignes | Clé métier de `master.employee` |
| Le poste Manager existe dans les 3 départements | 9 postes, 3 départements | `master.job_role` est un référentiel indépendant du département |
| 9 colonnes sont des codes chiffrés | education, 4 satisfactions, work_life_balance, performance_rating, job_level, stock_option_level | Tables `ref.*` pour donner un sens officiel aux codes. `job_level` et `stock_option_level` n'ont pas de libellé : point ouvert avec la Direction RH |
| La mobilité change le département ou le poste de 3 employés | employés 1, 2 et 4 | Règle de priorité : la mobilité, plus récente, gagne pour le département et le poste. Colonnes `department_source` et `job_role_source` |
| Âge, salaire, satisfaction et attrition changent dans le temps | toutes les lignes | Ce sont des faits : `data.hr_employee_facts`, qui pointe vers `master.employee` |
| `attrition` et `over_time` valent `Yes` / `No` | toutes les lignes | Conversion en booléen dans le MDM |
