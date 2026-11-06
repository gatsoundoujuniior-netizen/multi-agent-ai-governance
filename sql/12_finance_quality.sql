-- Controles qualite du MDM Tiers et Structures (membre Finance)
-- Pre-requis : sql/11_finance_mdm.sql execute
-- Seuils communs : 95 % de completude minimum, 1 % de doublons maximum

-- Q1. Unicite : un CIK n'apparait jamais deux fois (attendu : 0 ligne)
SELECT cik, COUNT(*) FROM master.company GROUP BY cik HAVING COUNT(*) > 1;

-- Q2. Pourquoi une regle de priorite ? Entreprises dont le nom differe entre le depot et la liste
SELECT COUNT(DISTINCT s.cik) AS nb_entreprises_noms_differents
FROM data.sec_sub_raw s
JOIN data.sec_company_tickers_raw t ON LPAD(t.cik_str, 10, '0') = LPAD(s.cik, 10, '0')
WHERE UPPER(TRIM(s.name)) <> UPPER(TRIM(t.title));

-- Q3. Completude des attributs du Golden Record (seuil : 95 %)
SELECT COUNT(*) AS nb_companies,
       ROUND(100.0 * COUNT(legal_name) / COUNT(*), 2) AS pct_name,
       ROUND(100.0 * COUNT(country)    / COUNT(*), 2) AS pct_country,
       ROUND(100.0 * COUNT(sic_code)   / COUNT(*), 2) AS pct_sic
FROM master.company;

-- Q4. Validite : codes pays des depots absents du referentiel
SELECT UPPER(TRIM(countryba)) AS code, COUNT(*) AS nb_depots
FROM data.sec_sub_raw
WHERE NULLIF(TRIM(countryba), '') IS NOT NULL
  AND UPPER(TRIM(countryba)) NOT IN (SELECT code FROM ref.country)
GROUP BY 1 ORDER BY 2 DESC;

-- Q5. Doublons de faits (meme entreprise, meme poste, meme periode ; seuil : 1 %)
-- Resultat : 5 lignes d'une seule entreprise, deposees dans 2 rapports avec la meme valeur
SELECT SUM(n) AS nb_faits,
       COALESCE(SUM(n - 1), 0) AS nb_doublons,
       ROUND(100.0 * COALESCE(SUM(n - 1), 0) / NULLIF(SUM(n), 0), 2) AS pct_doublons
FROM (SELECT COUNT(*) AS n FROM data.sec_financial_facts
      GROUP BY company_id, tag, period_end, qtrs) f;

-- Q6. Libelles SIC encore manquants (les 10 plus frequents sont completes dans 11_finance_mdm.sql)
-- 0000 ne designe aucun secteur : 11 entreprises recues ainsi d'EDGAR (point ouvert)
SELECT c.sic_code, COUNT(*) FROM master.company c
JOIN ref.sic s ON s.code = c.sic_code
WHERE s.label IS NULL GROUP BY c.sic_code ORDER BY 2 DESC LIMIT 10;

-- Q7. Qui sont les entreprises sans secteur ? (point ouvert du Golden Record)
SELECT COALESCE(e.entity_type, 'hors EDGAR') AS entity_type, COUNT(*) AS nb_sans_sic
FROM master.company c
LEFT JOIN data.sec_submissions_raw e ON LPAD(e.cik, 10, '0') = c.cik
WHERE c.sic_code IS NULL
GROUP BY 1 ORDER BY 2 DESC;

-- Q8. Quelle source a gagne, attribut par attribut ? (la regle de priorite en chiffres)
SELECT 'nom' AS attribut, name_source AS source, COUNT(*) AS nb FROM master.company GROUP BY 2
UNION ALL
SELECT 'pays', country_source, COUNT(*) FROM master.company GROUP BY 2
UNION ALL
SELECT 'secteur', sic_source, COUNT(*) FROM master.company GROUP BY 2
ORDER BY 1, 3 DESC;

-- Q9. Tous les faits pointent vers une entreprise, tous les depots y sont (attendu : 0 et 0)
SELECT (SELECT COUNT(*) FROM data.sec_financial_facts f
        LEFT JOIN master.company c ON c.company_id = f.company_id
        WHERE c.company_id IS NULL) AS faits_orphelins,
       (SELECT COUNT(DISTINCT s.cik) FROM data.sec_sub_raw s
        LEFT JOIN master.company c ON c.cik = LPAD(s.cik, 10, '0')
        WHERE c.cik IS NULL) AS depots_sans_entreprise;
