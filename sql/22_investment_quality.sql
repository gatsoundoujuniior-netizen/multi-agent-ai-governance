-- Controles qualite du MDM Produits (membre Investment)
-- Seuils communs : 95 % de completude, 1 % de doublons maximum

-- Q1. Unicite : un ticker n'apparait jamais deux fois (attendu : 0 ligne)
SELECT ticker, COUNT(*) FROM master.security GROUP BY ticker HAVING COUNT(*) > 1;

-- Q2. Pourquoi standardiser ? Tickers bruts qui ne different que par '.', '-' ou la casse
SELECT REPLACE(UPPER(TRIM(symbol)), '.', '-') AS ticker_std,
       ARRAY_AGG(DISTINCT symbol) AS variantes
FROM (SELECT symbol FROM data.sp500_prices_raw
      UNION SELECT symbol FROM data.sp500_constituents_raw) s
GROUP BY 1 HAVING COUNT(DISTINCT symbol) > 1;

-- Q3. Completude du Golden Record, par source qui a cree la fiche (seuil : 95 %)
SELECT source, COUNT(*) AS nb,
       ROUND(100.0 * COUNT(name)      / COUNT(*), 2) AS pct_name,
       ROUND(100.0 * COUNT(sector_id) / COUNT(*), 2) AS pct_sector,
       ROUND(100.0 * COUNT(cik)       / COUNT(*), 2) AS pct_cik
FROM master.security GROUP BY source;

-- Q3 bis. Source gagnante pour le nom et le CIK
SELECT name_source, cik_source, COUNT(*) FROM master.security GROUP BY 1, 2 ORDER BY 3 DESC;

-- Q4. Lien inter-referentiels : part des titres de l'indice relies a une entreprise Finance
SELECT ROUND(100.0 * COUNT(company_id) / COUNT(*), 2) AS pct_lie_company
FROM master.security WHERE in_index;

-- Q4 bis. Relation 1-N : entreprises qui emettent plusieurs titres (ex. Alphabet)
SELECT cik, ARRAY_AGG(ticker ORDER BY ticker) AS tickers
FROM master.security WHERE in_index AND cik IS NOT NULL
GROUP BY cik HAVING COUNT(*) > 1;

-- Q5. Doublons de cours (meme titre, meme jour)
SELECT security_id, trade_date, COUNT(*) FROM data.market_prices
GROUP BY 1, 2 HAVING COUNT(*) > 1 LIMIT 10;

-- Q6. Validite des cours : prix negatifs ou incoherents
SELECT COUNT(*) FILTER (WHERE close <= 0)   AS close_negatif,
       COUNT(*) FILTER (WHERE high < low)   AS high_inf_low,
       COUNT(*) FILTER (WHERE close > high OR close < low) AS close_hors_bornes,
       COUNT(*) FILTER (WHERE close IS NULL) AS close_vide
FROM data.market_prices;

-- Q7. Investor : chaque fiche a un profil de risque, et d'ou vient-il ?
SELECT risk_profile_source, COUNT(*) AS nb,
       ROUND(100.0 * COUNT(risk_profile) / COUNT(*), 2) AS pct_risk_profile
FROM master.investor GROUP BY 1;

-- Q8. Investor : desaccords entre les deux sources (le questionnaire a gagne)
SELECT i.code, i.name, INITCAP(TRIM(c.risk_profile)) AS profil_crm, i.risk_profile AS profil_retenu
FROM master.investor i
JOIN data.investor_crm_raw c ON UPPER(TRIM(c.code)) = i.code
WHERE INITCAP(TRIM(c.risk_profile)) <> i.risk_profile;

-- Q9. Investor : profil de plus de 2 ans, questionnaire a renouveler
SELECT code, name, risk_profile, risk_profile_source, risk_profile_date
FROM master.investor
WHERE risk_profile_date < CURRENT_DATE - INTERVAL '2 years';
