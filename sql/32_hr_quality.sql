-- Controles qualite du MDM Ressources humaines (membre HR)
-- Pre-requis : sql/31_hr_mdm.sql execute
-- Seuils communs : 95 % de completude minimum, 1 % de doublons maximum

-- Q1. Unicite : un matricule n'apparait jamais deux fois (attendu : 0 ligne)
SELECT employee_number, COUNT(*) FROM master.employee
GROUP BY employee_number HAVING COUNT(*) > 1;

-- Q2. Exhaustivite : tous les employes de la source sont dans le Golden Record
SELECT (SELECT COUNT(*) FROM data.hr_employee_raw)   AS nb_source,
       (SELECT COUNT(*) FROM master.employee)        AS nb_master,
       (SELECT COUNT(*) FROM data.hr_employee_facts) AS nb_faits;

-- Q3. Completude des attributs maitres (seuil : 95 %)
SELECT ROUND(100.0 * COUNT(department_id)      / COUNT(*), 2) AS pct_department,
       ROUND(100.0 * COUNT(job_role_id)        / COUNT(*), 2) AS pct_job_role,
       ROUND(100.0 * COUNT(education_level)    / COUNT(*), 2) AS pct_education,
       ROUND(100.0 * COUNT(education_field_id) / COUNT(*), 2) AS pct_education_field
FROM master.employee;

-- Q4. La regle de priorite a-t-elle ete appliquee ? (source gagnante par employe)
SELECT e.employee_number, r.department AS department_ibm, d.label AS department_retenu,
       r.job_role AS job_role_ibm, j.label AS job_role_retenu,
       e.department_source, e.job_role_source, e.mobility_date
FROM master.employee e
JOIN data.hr_employee_raw r ON r.employee_number::INT = e.employee_number
JOIN master.department d    ON d.department_id = e.department_id
JOIN master.job_role j      ON j.job_role_id = e.job_role_id
WHERE e.department_source = 'MOBILITY' OR e.job_role_source = 'MOBILITY'
ORDER BY e.employee_number;

-- Q5. Un poste dans plusieurs departements ?
SELECT j.label, ARRAY_AGG(DISTINCT d.label) AS departements
FROM master.employee e
JOIN master.job_role j   ON j.job_role_id = e.job_role_id
JOIN master.department d ON d.department_id = e.department_id
GROUP BY j.label HAVING COUNT(DISTINCT d.label) > 1;

-- Q6. Apercu de ce que le HR Agent pourra donner (un AGREGAT, sans personne visible)
SELECT d.label AS department,
       COUNT(*) AS nb_employes,
       ROUND(100.0 * AVG(f.attrition::INT), 1) AS taux_attrition_pct
FROM data.hr_employee_facts f
JOIN master.employee e   ON e.employee_id = f.employee_id
JOIN master.department d ON d.department_id = e.department_id
GROUP BY d.label ORDER BY taux_attrition_pct DESC;

-- Q7. Validite : les codes de la source existent-ils dans les referentiels ? (attendu : 0)
SELECT COUNT(*) FILTER (WHERE education NOT IN (SELECT level::TEXT FROM ref.education_level))
         AS education_invalide,
       COUNT(*) FILTER (WHERE performance_rating NOT IN
                        (SELECT level::TEXT FROM ref.performance_rating))
         AS performance_invalide,
       COUNT(*) FILTER (WHERE work_life_balance NOT IN
                        (SELECT level::TEXT FROM ref.work_life_balance))
         AS work_life_balance_invalide,
       COUNT(*) FILTER (WHERE job_level::INT NOT BETWEEN 1 AND 5) AS job_level_hors_plage,
       COUNT(*) FILTER (WHERE age::INT < 18) AS mineurs
FROM data.hr_employee_raw;

-- Q8. Mobilite : lignes non appliquees (matricule inconnu, libelle inconnu, ou mobilite
-- plus ancienne qu'une autre pour le meme employe). Chaque ligne est expliquee.
SELECT m.employee_number, m.department, m.job_role, m.effective_date,
       CASE
         WHEN e.employee_id IS NULL THEN 'matricule absent du fichier IBM HR'
         WHEN d.department_id IS NULL THEN 'departement inconnu de master.department'
         WHEN j.job_role_id IS NULL THEN 'poste inconnu de master.job_role'
         ELSE 'mobilite plus ancienne : remplacee par celle du ' || e.mobility_date
       END AS raison
FROM data.hr_mobility_raw m
LEFT JOIN master.employee e   ON e.employee_number = TRIM(m.employee_number)::INT
LEFT JOIN master.department d ON UPPER(d.label) = UPPER(TRIM(m.department))
LEFT JOIN master.job_role j   ON UPPER(j.label) = UPPER(TRIM(m.job_role))
WHERE e.employee_id IS NULL OR d.department_id IS NULL OR j.job_role_id IS NULL
   OR e.mobility_date IS DISTINCT FROM TRIM(m.effective_date)::DATE;

-- Q9. Office : le pays doit exister dans ref.country (referentiel commun du membre Finance)
-- Chaque code inconnu est signale par un NOTICE. Rien n'est verifie si ref.country n'existe pas.
DO $$
DECLARE
  r RECORD;
BEGIN
  IF to_regclass('ref.country') IS NULL THEN
    RAISE NOTICE 'Q9 : ref.country absent, rejouer sql/11_finance_mdm.sql du membre Finance';
    RETURN;
  END IF;
  FOR r IN SELECT o.code, o.country FROM master.office o
           LEFT JOIN ref.country c ON c.code = o.country
           WHERE o.country IS NOT NULL AND c.code IS NULL LOOP
    RAISE NOTICE 'Q9 : site % : pays % absent de ref.country', r.code, r.country;
  END LOOP;
  RAISE NOTICE 'Q9 : controle des pays termine';
END $$;
