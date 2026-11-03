-- MDM Ressources humaines (membre HR)
-- Pre-requis : data.hr_employee_raw charge (scripts/load_hr.py)
-- Relancable sans danger.
--
-- Deux sources pour l'entite Employee, rapprochees par le matricule (employee_number) :
--   1. data.hr_employee_raw   fichier IBM HR (identite, departement, poste, formation)
--   2. data.hr_mobility_raw   mobilite interne simulee (nouveau departement, nouveau poste)
-- Regle de priorite : pour le departement et le poste, la mobilite la plus recente gagne.

-- 0. Sources simulees : copie brute dans data.*_raw, tout en texte -------
DROP TABLE IF EXISTS data.hr_office_raw, data.hr_mobility_raw;
CREATE TABLE data.hr_office_raw (code TEXT, city TEXT, country TEXT);
CREATE TABLE data.hr_mobility_raw (
  employee_number TEXT, department TEXT, job_role TEXT, effective_date TEXT);
COPY data.hr_office_raw FROM '/seed/office.csv' WITH (FORMAT csv, HEADER true);
COPY data.hr_mobility_raw FROM '/seed/hr_mobility.csv' WITH (FORMAT csv, HEADER true);

-- 1. Reference Data : la signification officielle des codes ---------------
CREATE TABLE IF NOT EXISTS ref.education_level (
  level SMALLINT PRIMARY KEY, label VARCHAR(30) NOT NULL);
INSERT INTO ref.education_level VALUES
  (1,'Below College'), (2,'College'), (3,'Bachelor'), (4,'Master'), (5,'Doctor')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS ref.satisfaction_level (
  level SMALLINT PRIMARY KEY, label VARCHAR(30) NOT NULL);
INSERT INTO ref.satisfaction_level VALUES
  (1,'Low'), (2,'Medium'), (3,'High'), (4,'Very High')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS ref.performance_rating (
  level SMALLINT PRIMARY KEY, label VARCHAR(30) NOT NULL);
INSERT INTO ref.performance_rating VALUES
  (1,'Low'), (2,'Good'), (3,'Excellent'), (4,'Outstanding')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS ref.work_life_balance (
  level SMALLINT PRIMARY KEY, label VARCHAR(30) NOT NULL);
INSERT INTO ref.work_life_balance VALUES
  (1,'Bad'), (2,'Good'), (3,'Better'), (4,'Best')
ON CONFLICT DO NOTHING;

-- 2. Referentiels de l'organisation --------------------------------------
-- Sites (simules). country : code ISO de ref.country (referentiel du membre Finance),
-- verifie par sql/32_hr_quality.sql
CREATE TABLE IF NOT EXISTS master.office (
  office_id SERIAL PRIMARY KEY,
  code      VARCHAR(10) UNIQUE NOT NULL,
  city      VARCHAR(60) NOT NULL,
  country   CHAR(2));
INSERT INTO master.office (code, city, country)
SELECT UPPER(TRIM(code)), TRIM(city), UPPER(TRIM(country)) FROM data.hr_office_raw
ON CONFLICT (code) DO UPDATE SET city = EXCLUDED.city, country = EXCLUDED.country;

CREATE TABLE IF NOT EXISTS master.department (
  department_id SERIAL PRIMARY KEY,
  label         VARCHAR(60) UNIQUE NOT NULL,
  office_id     INT REFERENCES master.office(office_id));
INSERT INTO master.department (label)
SELECT DISTINCT TRIM(department) FROM data.hr_employee_raw
ON CONFLICT DO NOTHING;
-- Rattachement simule des departements aux sites
UPDATE master.department d SET office_id = o.office_id
FROM master.office o
WHERE (d.label = 'Sales' AND o.code = 'OFF-CAS')
   OR (d.label = 'Research & Development' AND o.code = 'OFF-RAB')
   OR (d.label = 'Human Resources' AND o.code = 'OFF-CAS');

-- Le poste est independant du departement : Manager existe dans les 3
CREATE TABLE IF NOT EXISTS master.job_role (
  job_role_id SERIAL PRIMARY KEY,
  label       VARCHAR(60) UNIQUE NOT NULL);
INSERT INTO master.job_role (label)
SELECT DISTINCT TRIM(job_role) FROM data.hr_employee_raw
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS master.education_field (
  education_field_id SERIAL PRIMARY KEY,
  label              VARCHAR(60) UNIQUE NOT NULL);
INSERT INTO master.education_field (label)
SELECT DISTINCT TRIM(education_field) FROM data.hr_employee_raw
ON CONFLICT DO NOTHING;

-- 3. Golden Record Employee (attributs maitres seulement) -----------------
CREATE TABLE IF NOT EXISTS master.employee (
  employee_id        SERIAL PRIMARY KEY,
  employee_number    INT UNIQUE NOT NULL,
  gender             VARCHAR(10),
  marital_status     VARCHAR(10),
  department_id      INT REFERENCES master.department(department_id),
  job_role_id        INT REFERENCES master.job_role(job_role_id),
  job_level          SMALLINT,
  education_level    SMALLINT REFERENCES ref.education_level(level),
  education_field_id INT REFERENCES master.education_field(education_field_id),
  department_source  VARCHAR(20) NOT NULL,   -- IBM_HR ou MOBILITY : la source gagnante
  job_role_source    VARCHAR(20) NOT NULL,
  mobility_date      DATE,                     -- date d'effet de la mobilite retenue
  updated_at         TIMESTAMP DEFAULT now());

WITH ibm AS (
  SELECT r.employee_number::INT AS employee_number, TRIM(r.gender) AS gender,
         TRIM(r.marital_status) AS marital_status, d.department_id, j.job_role_id,
         r.job_level::SMALLINT AS job_level, r.education::SMALLINT AS education_level,
         f.education_field_id
  FROM data.hr_employee_raw r
  JOIN master.department d      ON d.label = TRIM(r.department)
  JOIN master.job_role j        ON j.label = TRIM(r.job_role)
  JOIN master.education_field f ON f.label = TRIM(r.education_field)),
-- Plusieurs mobilites pour un meme employe : la plus recente gagne.
-- Standardisation : TRIM et comparaison sans tenir compte des majuscules.
mobility AS (
  SELECT DISTINCT ON (TRIM(m.employee_number)::INT)
         TRIM(m.employee_number)::INT AS employee_number, d.department_id, j.job_role_id,
         TRIM(m.effective_date)::DATE AS effective_date
  FROM data.hr_mobility_raw m
  JOIN master.department d ON UPPER(d.label) = UPPER(TRIM(m.department))
  JOIN master.job_role j   ON UPPER(j.label) = UPPER(TRIM(m.job_role))
  ORDER BY TRIM(m.employee_number)::INT, TRIM(m.effective_date)::DATE DESC)
-- Le Golden Record part du fichier IBM HR : une mobilite sur un matricule inconnu
-- ne cree pas d'employe (signalee par le controle Q8)
INSERT INTO master.employee (employee_number, gender, marital_status, department_id,
                             job_role_id, job_level, education_level, education_field_id,
                             department_source, job_role_source, mobility_date)
SELECT i.employee_number, i.gender, i.marital_status,
       COALESCE(m.department_id, i.department_id),
       COALESCE(m.job_role_id, i.job_role_id),
       i.job_level, i.education_level, i.education_field_id,
       CASE WHEN m.department_id IS NOT NULL THEN 'MOBILITY' ELSE 'IBM_HR' END,
       CASE WHEN m.job_role_id IS NOT NULL THEN 'MOBILITY' ELSE 'IBM_HR' END,
       m.effective_date
FROM ibm i
LEFT JOIN mobility m ON m.employee_number = i.employee_number
ON CONFLICT (employee_number) DO UPDATE SET
  gender = EXCLUDED.gender, marital_status = EXCLUDED.marital_status,
  department_id = EXCLUDED.department_id, job_role_id = EXCLUDED.job_role_id,
  job_level = EXCLUDED.job_level, education_level = EXCLUDED.education_level,
  education_field_id = EXCLUDED.education_field_id,
  department_source = EXCLUDED.department_source, job_role_source = EXCLUDED.job_role_source,
  mobility_date = EXCLUDED.mobility_date, updated_at = now();

-- 4. Faits RH (donnees metier qui pointent vers le Golden Record) ----------
CREATE TABLE IF NOT EXISTS data.hr_employee_facts (
  employee_id                INT PRIMARY KEY REFERENCES master.employee(employee_id),
  age                        SMALLINT,
  monthly_income             INT,
  daily_rate                 INT,
  hourly_rate                INT,
  monthly_rate               INT,
  attrition                  BOOLEAN,
  over_time                  BOOLEAN,
  business_travel            VARCHAR(30),
  distance_from_home         SMALLINT,
  environment_satisfaction   SMALLINT REFERENCES ref.satisfaction_level(level),
  job_satisfaction           SMALLINT REFERENCES ref.satisfaction_level(level),
  relationship_satisfaction  SMALLINT REFERENCES ref.satisfaction_level(level),
  job_involvement            SMALLINT REFERENCES ref.satisfaction_level(level),
  work_life_balance          SMALLINT REFERENCES ref.work_life_balance(level),
  performance_rating         SMALLINT REFERENCES ref.performance_rating(level),
  percent_salary_hike        SMALLINT,
  stock_option_level         SMALLINT,
  num_companies_worked       SMALLINT,
  total_working_years        SMALLINT,
  training_times_last_year   SMALLINT,
  years_at_company           SMALLINT,
  years_in_current_role      SMALLINT,
  years_since_last_promotion SMALLINT,
  years_with_curr_manager    SMALLINT);

TRUNCATE data.hr_employee_facts;
INSERT INTO data.hr_employee_facts
SELECT e.employee_id, r.age::SMALLINT, r.monthly_income::INT, r.daily_rate::INT,
       r.hourly_rate::INT, r.monthly_rate::INT, r.attrition = 'Yes', r.over_time = 'Yes',
       TRIM(r.business_travel), r.distance_from_home::SMALLINT,
       r.environment_satisfaction::SMALLINT, r.job_satisfaction::SMALLINT,
       r.relationship_satisfaction::SMALLINT, r.job_involvement::SMALLINT,
       r.work_life_balance::SMALLINT, r.performance_rating::SMALLINT,
       r.percent_salary_hike::SMALLINT, r.stock_option_level::SMALLINT,
       r.num_companies_worked::SMALLINT, r.total_working_years::SMALLINT,
       r.training_times_last_year::SMALLINT, r.years_at_company::SMALLINT,
       r.years_in_current_role::SMALLINT, r.years_since_last_promotion::SMALLINT,
       r.years_with_curr_manager::SMALLINT
FROM data.hr_employee_raw r
JOIN master.employee e ON e.employee_number = r.employee_number::INT;
-- employee_count, over18, standard_hours : constantes, non reprises (voir dictionnaire)
