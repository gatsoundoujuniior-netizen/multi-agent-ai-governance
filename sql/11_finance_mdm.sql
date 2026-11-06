-- MDM Tiers et Structures (membre Finance)
-- Pre-requis : data.sec_sub_raw, data.sec_num_raw, data.sec_tag_raw,
--              data.sec_company_tickers_raw, data.sec_submissions_raw charges
-- Relancable sans danger.
--
-- Trois sources pour l'entite Company, rapprochees par le CIK :
--   1. data.sec_sub_raw              depots 10-K du trimestre (nom au depot, pays, secteur)
--   2. data.sec_company_tickers_raw  liste officielle SEC (nom actuel)
--   3. data.sec_submissions_raw      fiches EDGAR des entreprises sans 10-K (nom, pays, secteur)

-- 1. Reference Data ------------------------------------------------------
CREATE TABLE IF NOT EXISTS ref.currency (
  code  CHAR(3) PRIMARY KEY,
  label VARCHAR(50) NOT NULL);
INSERT INTO ref.currency VALUES
  ('USD','Dollar americain'), ('EUR','Euro'), ('MAD','Dirham marocain')
ON CONFLICT DO NOTHING;

-- Pays : codes ISO 3166 rencontres dans les trois sources
CREATE TABLE IF NOT EXISTS ref.country (
  code  CHAR(2) PRIMARY KEY,
  label VARCHAR(80) NOT NULL);
INSERT INTO ref.country VALUES
  ('US','Etats-Unis'), ('CA','Canada'), ('GB','Royaume-Uni'), ('IE','Irlande'),
  ('CH','Suisse'), ('NL','Pays-Bas'), ('IL','Israel'), ('CN','Chine'),
  ('BM','Bermudes'), ('KY','Iles Caimans'), ('JP','Japon'), ('MA','Maroc'),
  ('PR','Porto Rico'), ('HK','Hong Kong'), ('FR','France'), ('MY','Malaisie'),
  ('SG','Singapour'), ('ZA','Afrique du Sud'), ('BS','Bahamas'), ('CR','Costa Rica'),
  ('DE','Allemagne'), ('DK','Danemark'), ('GG','Guernesey'), ('JE','Jersey'),
  ('LU','Luxembourg'), ('TW','Taiwan'), ('UY','Uruguay'), ('AE','Emirats arabes unis'),
  ('AU','Australie'), ('BR','Bresil'), ('GR','Grece'), ('SE','Suede'), ('IT','Italie'),
  ('KR','Coree du Sud'), ('BE','Belgique'), ('ES','Espagne'), ('AR','Argentine'),
  ('VG','Iles Vierges britanniques'), ('IN','Inde'), ('CL','Chili'), ('NO','Norvege'),
  ('ID','Indonesie'), ('MC','Monaco'), ('PE','Perou'), ('NZ','Nouvelle-Zelande'),
  ('CY','Chypre'), ('CO','Colombie'), ('TR','Turquie'), ('PH','Philippines'),
  ('KZ','Kazakhstan'), ('VE','Venezuela'), ('TH','Thailande'), ('MO','Macao'),
  ('FI','Finlande'), ('JO','Jordanie'), ('PA','Panama'), ('PT','Portugal'),
  ('KE','Kenya'), ('DO','Republique dominicaine'), ('ME','Montenegro'),
  ('LT','Lituanie'), ('PL','Pologne'), ('AM','Armenie'), ('KH','Cambodge'),
  ('NG','Nigeria'), ('MN','Mongolie'), ('AT','Autriche'), ('MT','Malte'),
  ('MH','Iles Marshall'), ('GE','Georgie'), ('SK','Slovaquie'), ('CZ','Republique tcheque'),
  ('GI','Gibraltar'), ('IM','Ile de Man'), ('RO','Roumanie'), ('UZ','Ouzbekistan'),
  ('MX','Mexique')
ON CONFLICT DO NOTHING;

-- Correspondance code de localisation EDGAR -> code pays ISO
-- EDGAR ecrit un Etat americain (CA = Californie) ou un code pays maison (M0 = Japon)
CREATE TABLE IF NOT EXISTS ref.edgar_location (
  code         VARCHAR(2) PRIMARY KEY,
  label        VARCHAR(80) NOT NULL,
  country_code CHAR(2) NOT NULL REFERENCES ref.country(code));
INSERT INTO ref.edgar_location (code, label, country_code)
SELECT s, 'Etat americain ' || s, 'US'
FROM unnest(ARRAY['AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL',
  'IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA',
  'WV','WI','WY']) AS s
ON CONFLICT DO NOTHING;
INSERT INTO ref.edgar_location (code, label, country_code) VALUES
  ('X1','United States','US'), ('PR','Puerto Rico','PR'),
  ('A0','Alberta, Canada','CA'), ('A1','British Columbia, Canada','CA'),
  ('A2','Manitoba, Canada','CA'), ('A3','New Brunswick, Canada','CA'),
  ('A4','Newfoundland, Canada','CA'), ('A5','Nova Scotia, Canada','CA'),
  ('A6','Ontario, Canada','CA'), ('A8','Quebec, Canada','CA'),
  ('A9','Saskatchewan, Canada','CA'), ('Z4','Canada (Federal Level)','CA'),
  ('F4','China','CN'), ('U0','Singapore','SG'), ('L3','Israel','IL'),
  ('K3','Hong Kong','HK'), ('X0','United Kingdom','GB'), ('M0','Japan','JP'),
  ('E9','Cayman Islands','KY'), ('C3','Australia','AU'), ('V8','Switzerland','CH'),
  ('D5','Brazil','BR'), ('J3','Greece','GR'), ('D0','Bermuda','BM'),
  ('2M','Germany','DE'), ('F5','Taiwan','TW'), ('N8','Malaysia','MY'),
  ('P7','Netherlands','NL'), ('I0','France','FR'), ('L2','Ireland','IE'),
  ('O5','Mexico','MX'), ('N4','Luxembourg','LU'), ('C0','United Arab Emirates','AE'),
  ('V7','Sweden','SE'), ('L6','Italy','IT'), ('M5','Korea, Republic of','KR'),
  ('C9','Belgium','BE'), ('U3','Spain','ES'), ('C1','Argentina','AR'),
  ('D8','Virgin Islands, British','VG'), ('G7','Denmark','DK'), ('K7','India','IN'),
  ('F3','Chile','CL'), ('T3','South Africa','ZA'), ('Q8','Norway','NO'),
  ('K8','Indonesia','ID'), ('O9','Monaco','MC'), ('R5','Peru','PE'),
  ('Q2','New Zealand','NZ'), ('G4','Cyprus','CY'), ('F8','Colombia','CO'),
  ('W8','Turkey','TR'), ('R6','Philippines','PH'), ('1P','Kazakhstan','KZ'),
  ('X5','Venezuela','VE'), ('W1','Thailand','TH'), ('N5','Macau','MO'),
  ('H9','Finland','FI'), ('X3','Uruguay','UY'), ('Y9','Jersey','JE'),
  ('Y7','Guernsey','GG'), ('M2','Jordan','JO'), ('R1','Panama','PA'),
  ('S1','Portugal','PT'), ('M3','Kenya','KE'), ('G8','Dominican Republic','DO'),
  ('Z5','Montenegro','ME'), ('1Q','Lithuania','LT'), ('R9','Poland','PL'),
  ('1B','Armenia','AM'), ('E3','Cambodia','KH'), ('Q5','Nigeria','NG'),
  ('C5','Bahamas','BS'), ('P0','Mongolia','MN'), ('C4','Austria','AT'),
  ('O1','Malta','MT'), ('1T','Marshall Islands','MH'), ('2Q','Georgia','GE'),
  ('2B','Slovakia','SK'), ('2N','Czech Republic','CZ'), ('J1','Gibraltar','GI'),
  ('Y8','Isle of Man','IM'), ('S5','Romania','RO'), ('2K','Uzbekistan','UZ')
ON CONFLICT DO NOTHING;

-- Codes secteur SIC : libelles fournis par la source EDGAR quand elle les a
CREATE TABLE IF NOT EXISTS ref.sic (
  code  VARCHAR(4) PRIMARY KEY,
  label VARCHAR(150));
INSERT INTO ref.sic (code)
SELECT DISTINCT sic FROM data.sec_sub_raw WHERE sic IS NOT NULL
UNION
SELECT DISTINCT sic FROM data.sec_submissions_raw WHERE sic IS NOT NULL AND sic <> ''
ON CONFLICT DO NOTHING;
UPDATE ref.sic r SET label = e.sic_description
FROM (SELECT DISTINCT ON (sic) sic, sic_description FROM data.sec_submissions_raw
      WHERE sic_description IS NOT NULL AND sic_description <> '' ORDER BY sic) e
WHERE r.code = e.sic AND r.label IS NULL;

-- 2. Golden Record Company ------------------------------------------------
-- Colonnes du contrat avec le membre Investment : company_id, cik, legal_name,
-- country, sic_code. Les colonnes *_source gardent la trace de la source gagnante.
CREATE TABLE IF NOT EXISTS master.company (
  company_id     SERIAL PRIMARY KEY,
  cik            VARCHAR(10) UNIQUE NOT NULL,
  legal_name     VARCHAR(200) NOT NULL,
  name_source    VARCHAR(20) NOT NULL,
  country        CHAR(2) REFERENCES ref.country(code),
  country_source VARCHAR(20),
  sic_code       VARCHAR(4) REFERENCES ref.sic(code),
  sic_source     VARCHAR(20),
  updated_at     TIMESTAMP DEFAULT now());

WITH
-- Source 1 : pour un meme CIK, le depot 10-K le plus recent gagne
depot AS (
  SELECT DISTINCT ON (LPAD(cik, 10, '0'))
         LPAD(cik, 10, '0') AS cik, TRIM(name) AS name,
         UPPER(TRIM(countryba)) AS country, sic
  FROM data.sec_sub_raw
  ORDER BY LPAD(cik, 10, '0'), filed DESC),
-- Source 2 : un CIK peut avoir plusieurs tickers, le nom est le meme
liste AS (
  SELECT DISTINCT ON (LPAD(cik_str, 10, '0'))
         LPAD(cik_str, 10, '0') AS cik, TRIM(title) AS name
  FROM data.sec_company_tickers_raw
  ORDER BY LPAD(cik_str, 10, '0'), ticker),
-- Source 3 : code de localisation EDGAR traduit en code pays ISO
edgar AS (
  SELECT LPAD(e.cik, 10, '0') AS cik, TRIM(e.name) AS name,
         l.country_code AS country, NULLIF(e.sic, '') AS sic
  FROM data.sec_submissions_raw e
  LEFT JOIN ref.edgar_location l
         ON l.code = COALESCE(NULLIF(e.business_state_or_country, ''),
                              e.business_country_code)),
ciks AS (
  SELECT cik FROM depot UNION SELECT cik FROM liste UNION SELECT cik FROM edgar)
INSERT INTO master.company (cik, legal_name, name_source, country, country_source,
                            sic_code, sic_source)
SELECT c.cik,
       -- Regle de priorite du nom : liste officielle (nom actuel), puis depot, puis EDGAR
       COALESCE(l.name, d.name, e.name),
       CASE WHEN l.name IS NOT NULL THEN 'TICKERS'
            WHEN d.name IS NOT NULL THEN 'DEPOT_10K' ELSE 'EDGAR' END,
       -- Pays et secteur : le depot 10-K, puis EDGAR. Un code hors referentiel -> NULL
       COALESCE(rc.code, e.country),
       CASE WHEN rc.code IS NOT NULL THEN 'DEPOT_10K'
            WHEN e.country IS NOT NULL THEN 'EDGAR' END,
       COALESCE(d.sic, e.sic),
       CASE WHEN d.sic IS NOT NULL THEN 'DEPOT_10K'
            WHEN e.sic IS NOT NULL THEN 'EDGAR' END
FROM ciks c
LEFT JOIN depot d ON d.cik = c.cik
LEFT JOIN liste l ON l.cik = c.cik
LEFT JOIN edgar e ON e.cik = c.cik
LEFT JOIN ref.country rc ON rc.code = d.country
ON CONFLICT (cik) DO UPDATE
  SET legal_name     = EXCLUDED.legal_name,
      name_source    = EXCLUDED.name_source,
      country        = EXCLUDED.country,
      country_source = EXCLUDED.country_source,
      sic_code       = EXCLUDED.sic_code,
      sic_source     = EXCLUDED.sic_source,
      updated_at     = now();

-- 3. Plan de comptes XBRL (Structures) -------------------------------------
CREATE TABLE IF NOT EXISTS master.xbrl_account (
  tag      VARCHAR(120) PRIMARY KEY,
  label    VARCHAR(300),
  balance  VARCHAR(6),     -- debit / credit
  category VARCHAR(20) CHECK (category IN
           ('Asset','Liability','Equity','Revenue','Expense','Income')));

-- Si un tag existe dans plusieurs versions de taxonomie, la plus recente gagne
INSERT INTO master.xbrl_account (tag, label, balance, category)
SELECT DISTINCT ON (tag)
       tag, tlabel, crdr,
       CASE
         WHEN tag IN ('Assets','CashAndCashEquivalentsAtCarryingValue') THEN 'Asset'
         WHEN tag = 'Liabilities' THEN 'Liability'
         WHEN tag = 'StockholdersEquity' THEN 'Equity'
         WHEN tag LIKE 'Revenue%' THEN 'Revenue'
         ELSE 'Income'
       END
FROM data.sec_tag_raw
ORDER BY tag, version DESC
ON CONFLICT (tag) DO NOTHING;

-- 4. Faits financiers (donnees metier qui pointent vers le MDM) ------------
CREATE TABLE IF NOT EXISTS data.sec_financial_facts (
  fact_id    BIGSERIAL PRIMARY KEY,
  company_id INT NOT NULL REFERENCES master.company(company_id),
  tag        VARCHAR(120) NOT NULL REFERENCES master.xbrl_account(tag),
  period_end DATE NOT NULL,
  qtrs       SMALLINT,
  value      NUMERIC(24,2),
  currency   CHAR(3) REFERENCES ref.currency(code),
  adsh       VARCHAR(25));

TRUNCATE data.sec_financial_facts;
INSERT INTO data.sec_financial_facts (company_id, tag, period_end, qtrs, value, currency, adsh)
SELECT c.company_id, n.tag, TO_DATE(n.ddate, 'YYYYMMDD'),
       n.qtrs::SMALLINT, n.value::NUMERIC, n.uom, n.adsh
FROM data.sec_num_raw n
JOIN data.sec_sub_raw s ON s.adsh = n.adsh
JOIN master.company c   ON c.cik = LPAD(s.cik, 10, '0')
JOIN master.xbrl_account x ON x.tag = n.tag
WHERE n.value IS NOT NULL;

-- 5. Libelles des 10 codes SIC les plus frequents sans libelle (controle Q6) -----
UPDATE ref.sic r SET label = v.label
FROM (VALUES
  ('6111', 'Federal & Federally-Sponsored Credit Agencies'),
  ('4213', 'Trucking (No Local)'),
  ('6324', 'Hospital & Medical Service Plans'),
  ('6351', 'Surety Insurance'),
  ('3561', 'Pumps & Pumping Equipment'),
  ('6162', 'Mortgage Bankers & Loan Correspondents'),
  ('8062', 'Services-General Medical & Surgical Hospitals, NEC'),
  ('1221', 'Bituminous Coal & Lignite Mining'),
  ('3460', 'Metal Forgings & Stampings'),
  ('7320', 'Services-Consumer Credit Reporting, Collection Agencies')) AS v(code, label)
WHERE r.code = v.code AND r.label IS NULL;
