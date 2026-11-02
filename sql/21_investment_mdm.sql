-- MDM Produits (membre Investment)
-- Pre-requis : data.sp500_prices_raw, data.sp500_constituents_raw charges (scripts/load_sp500.py)
-- Optionnel  : data.sec_company_tickers_raw et master.company du membre Finance
--              (sinon le CIK des titres sortis de l'indice et company_id restent NULL)
-- Le script peut etre relance sans danger.

-- 1. Reference Data : secteurs GICS ------------------------------------
CREATE TABLE IF NOT EXISTS ref.sector (
  sector_id SERIAL PRIMARY KEY,
  label     VARCHAR(80) UNIQUE NOT NULL);
INSERT INTO ref.sector (label)
SELECT DISTINCT TRIM(gics_sector) FROM data.sp500_constituents_raw
WHERE gics_sector IS NOT NULL
ON CONFLICT DO NOTHING;

-- 2. Golden Record Security ---------------------------------------------
-- Cle metier : le ticker standardise. Les colonnes *_source gardent la trace
-- de la source gagnante pour chaque attribut.
CREATE TABLE IF NOT EXISTS master.security (
  security_id SERIAL PRIMARY KEY,
  ticker      VARCHAR(12) UNIQUE NOT NULL,
  name        VARCHAR(200),
  name_source VARCHAR(20),
  sector_id   INT REFERENCES ref.sector(sector_id),
  cik         VARCHAR(10),
  cik_source  VARCHAR(20),
  company_id  INT,                  -- lien vers master.company (Finance)
  in_index    BOOLEAN NOT NULL,     -- membre actuel du S&P 500 ?
  source      VARCHAR(20) NOT NULL, -- source qui a cree la fiche
  updated_at  TIMESTAMP DEFAULT now());

-- Standardisation du ticker : majuscules, sans espaces, '.' remplace par '-'
-- (BRK.B et BRK-B sont le MEME titre)

-- Un titre peut sortir de l'indice : on recalcule in_index a chaque execution
UPDATE master.security SET in_index = FALSE;

-- Source 1 (prioritaire) : la liste officielle du S&P 500
INSERT INTO master.security (ticker, name, name_source, sector_id, cik, cik_source, in_index, source)
SELECT REPLACE(UPPER(TRIM(c.symbol)), '.', '-'),
       TRIM(c.security), 'CONSTITUENTS',
       s.sector_id,
       LPAD(c.cik, 10, '0'), 'CONSTITUENTS',
       TRUE,
       'CONSTITUENTS'
FROM data.sp500_constituents_raw c
LEFT JOIN ref.sector s ON s.label = TRIM(c.gics_sector)
ON CONFLICT (ticker) DO UPDATE
  SET name = EXCLUDED.name, name_source = EXCLUDED.name_source,
      sector_id = EXCLUDED.sector_id,
      cik = EXCLUDED.cik, cik_source = EXCLUDED.cik_source,
      in_index = TRUE, source = 'CONSTITUENTS',
      updated_at = now();

-- Source 2 (secondaire) : tickers vus dans les cours mais absents de la liste
-- (titres sortis de l'indice). Regle de priorite : on ne cree que ce qui manque.
INSERT INTO master.security (ticker, in_index, source)
SELECT DISTINCT REPLACE(UPPER(TRIM(symbol)), '.', '-'), FALSE, 'PRICES'
FROM data.sp500_prices_raw
WHERE symbol IS NOT NULL
ON CONFLICT (ticker) DO NOTHING;

-- Source 3 (completement) : la liste officielle ticker -> CIK de la SEC, chargee
-- par le membre Finance. Elle ne remplit que les nom et CIK encore vides.
DO $$
BEGIN
  IF to_regclass('data.sec_company_tickers_raw') IS NOT NULL THEN
    UPDATE master.security sec
    SET name        = COALESCE(sec.name, t.name),
        name_source = COALESCE(sec.name_source, 'SEC_TICKERS'),
        cik         = t.cik,
        cik_source  = 'SEC_TICKERS',
        updated_at  = now()
    FROM (SELECT DISTINCT ON (REPLACE(UPPER(TRIM(ticker)), '.', '-'))
                 REPLACE(UPPER(TRIM(ticker)), '.', '-') AS ticker,
                 LPAD(cik_str, 10, '0') AS cik, TRIM(title) AS name
          FROM data.sec_company_tickers_raw
          ORDER BY REPLACE(UPPER(TRIM(ticker)), '.', '-'), cik_str) t
    WHERE t.ticker = sec.ticker AND sec.cik IS NULL;
  END IF;
END $$;

-- Lien vers le referentiel Finance, par le CIK (seulement si master.company existe)
DO $$
BEGIN
  IF to_regclass('master.company') IS NOT NULL THEN
    UPDATE master.security sec
    SET company_id = c.company_id
    FROM master.company c
    WHERE c.cik = sec.cik;
  END IF;
END $$;

-- 3. Cours (donnees metier qui pointent vers le MDM) -----------------------
CREATE TABLE IF NOT EXISTS data.market_prices (
  price_id    BIGSERIAL PRIMARY KEY,
  security_id INT NOT NULL REFERENCES master.security(security_id),
  trade_date  DATE NOT NULL,
  open        NUMERIC(14,4),
  high        NUMERIC(14,4),
  low         NUMERIC(14,4),
  close       NUMERIC(14,4),
  volume      BIGINT);

TRUNCATE data.market_prices;
-- LEFT(date, 10) : certains datasets ecrivent "2020-01-02 00:00:00-05:00"
INSERT INTO data.market_prices (security_id, trade_date, open, high, low, close, volume)
SELECT sec.security_id, LEFT(TRIM(p.date), 10)::DATE,
       NULLIF(p.open,'')::NUMERIC, NULLIF(p.high,'')::NUMERIC,
       NULLIF(p.low,'')::NUMERIC,  NULLIF(p.close,'')::NUMERIC,
       NULLIF(p.volume,'')::NUMERIC::BIGINT
FROM data.sp500_prices_raw p
JOIN master.security sec ON sec.ticker = REPLACE(UPPER(TRIM(p.symbol)), '.', '-');

CREATE INDEX IF NOT EXISTS market_prices_security_date
  ON data.market_prices (security_id, trade_date);

-- 4. Product (simule, une source) -----------------------------------------
CREATE TABLE IF NOT EXISTS master.product (
  product_id SERIAL PRIMARY KEY,
  code       VARCHAR(20) UNIQUE NOT NULL,
  label      VARCHAR(100) NOT NULL,
  category   VARCHAR(40),
  risk_level VARCHAR(8) CHECK (risk_level IN ('Low','Medium','High')));

-- Copie brute dans data.product_raw, tout en texte, comme les autres sources
DROP TABLE IF EXISTS data.product_raw;
CREATE TABLE data.product_raw (code TEXT, label TEXT, category TEXT, risk_level TEXT);
COPY data.product_raw FROM '/seed/product.csv' WITH (FORMAT csv, HEADER true);
INSERT INTO master.product (code, label, category, risk_level)
SELECT UPPER(TRIM(code)), TRIM(label), TRIM(category), INITCAP(TRIM(risk_level))
FROM data.product_raw
ON CONFLICT (code) DO UPDATE
  SET label = EXCLUDED.label, category = EXCLUDED.category, risk_level = EXCLUDED.risk_level;

-- 5. Golden Record Investor (simule, deux sources) --------------------------
-- Source 1 : le CRM commercial (identite + profil de risque declare par le commercial)
-- Source 2 : le questionnaire de risque reglementaire, rempli et date par le client
-- Copie brute dans data.*_raw, tout en texte, comme les autres sources.
DROP TABLE IF EXISTS data.investor_crm_raw, data.investor_questionnaire_raw;
CREATE TABLE data.investor_crm_raw (
  code TEXT, name TEXT, investor_type TEXT, country TEXT, risk_profile TEXT, updated_on TEXT);
CREATE TABLE data.investor_questionnaire_raw (
  investor_code TEXT, risk_profile TEXT, questionnaire_date TEXT, completed_by TEXT);
COPY data.investor_crm_raw FROM '/seed/investor_crm.csv' WITH (FORMAT csv, HEADER true);
COPY data.investor_questionnaire_raw FROM '/seed/investor_risk_questionnaire.csv'
  WITH (FORMAT csv, HEADER true);

CREATE TABLE IF NOT EXISTS master.investor (
  investor_id         SERIAL PRIMARY KEY,
  code                VARCHAR(20) UNIQUE NOT NULL,
  name                VARCHAR(150) NOT NULL,
  investor_type       VARCHAR(40),
  country             CHAR(2),
  risk_profile        VARCHAR(8) CHECK (risk_profile IN ('Low','Medium','High')),
  risk_profile_source VARCHAR(20),
  risk_profile_date   DATE,
  updated_at          TIMESTAMP DEFAULT now());

WITH
crm AS (
  SELECT UPPER(TRIM(code)) AS code, TRIM(name) AS name, TRIM(investor_type) AS investor_type,
         UPPER(TRIM(country)) AS country, INITCAP(TRIM(risk_profile)) AS risk_profile,
         updated_on::DATE AS updated_on
  FROM data.investor_crm_raw),
-- Plusieurs questionnaires pour un meme investisseur : le plus recent gagne
questionnaire AS (
  SELECT DISTINCT ON (UPPER(TRIM(investor_code)))
         UPPER(TRIM(investor_code)) AS code, INITCAP(TRIM(risk_profile)) AS risk_profile,
         questionnaire_date::DATE AS questionnaire_date
  FROM data.investor_questionnaire_raw
  ORDER BY UPPER(TRIM(investor_code)), questionnaire_date::DATE DESC)
INSERT INTO master.investor (code, name, investor_type, country,
                             risk_profile, risk_profile_source, risk_profile_date)
SELECT c.code, c.name, c.investor_type, c.country,
       -- Regle de priorite du profil de risque : le questionnaire (valeur reglementaire),
       -- puis le CRM s'il n'y a pas de questionnaire
       COALESCE(q.risk_profile, c.risk_profile),
       CASE WHEN q.risk_profile IS NOT NULL THEN 'QUESTIONNAIRE' ELSE 'CRM' END,
       COALESCE(q.questionnaire_date, c.updated_on)
FROM crm c
LEFT JOIN questionnaire q ON q.code = c.code
ON CONFLICT (code) DO UPDATE
  SET name = EXCLUDED.name, investor_type = EXCLUDED.investor_type,
      country = EXCLUDED.country, risk_profile = EXCLUDED.risk_profile,
      risk_profile_source = EXCLUDED.risk_profile_source,
      risk_profile_date = EXCLUDED.risk_profile_date, updated_at = now();
