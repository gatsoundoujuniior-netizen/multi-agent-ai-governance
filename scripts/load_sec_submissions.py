# Troisieme source du MDM Tiers et Structures : les fiches EDGAR Submissions de la SEC.
# Pour les entreprises de la liste des tickers sans 10-K dans le trimestre, elle fournit
# le pays, le secteur et l'adresse que sub.txt ne donne pas.
# Les fichiers JSON bruts sont gardes dans data/raw/sec/submissions/ : un relancement
# ne retelecharge que ceux qui manquent.
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@localhost:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
RAW = "data/raw/sec/submissions"
USER_AGENT = os.getenv("SEC_USER_AGENT", "multi-agent-ai-governance student-project")
os.makedirs(RAW, exist_ok=True)

# Les entreprises de la liste des tickers absentes des depots 10-K du trimestre
with engine.connect() as conn:
    ciks = [row[0] for row in conn.execute(text("""
        SELECT DISTINCT LPAD(t.cik_str, 10, '0')
        FROM data.sec_company_tickers_raw t
        WHERE LPAD(t.cik_str, 10, '0') NOT IN
              (SELECT LPAD(cik, 10, '0') FROM data.sec_sub_raw)
        ORDER BY 1"""))]
print("fiches a recuperer :", len(ciks))

# Telechargement : la SEC limite a 10 requetes par seconde, on reste en dessous
missing = 0
for i, cik in enumerate(ciks, 1):
    path = f"{RAW}/CIK{cik}.json"
    if os.path.exists(path):
        continue
    req = urllib.request.Request(f"https://data.sec.gov/submissions/CIK{cik}.json",
                                 headers={"User-Agent": USER_AGENT})
    # Une coupure reseau ou un refus temporaire de la SEC : on reessaie en attendant plus
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            with open(path, "wb") as f:
                f.write(content)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                missing += 1
                break
            if e.code not in (429, 500, 502, 503) or attempt == 4:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 4:
                raise
        time.sleep(5 * (attempt + 1))
    time.sleep(0.15)
    if i % 500 == 0:
        print(f"  {i} / {len(ciks)}")
print("fiches introuvables a la SEC :", missing)

# Copie brute : une ligne par entreprise, tout en texte, codes EDGAR tels quels
fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
rows = []
for cik in ciks:
    path = f"{RAW}/CIK{cik}.json"
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    business = (s.get("addresses") or {}).get("business") or {}
    rows.append({
        "cik": s.get("cik"),
        "name": s.get("name"),
        "entity_type": s.get("entityType"),
        "sic": s.get("sic"),
        "sic_description": s.get("sicDescription"),
        "state_of_incorporation": s.get("stateOfIncorporation"),
        "business_state_or_country": business.get("stateOrCountry"),
        "business_state_or_country_description": business.get("stateOrCountryDescription"),
        "business_country": business.get("country"),
        "business_country_code": business.get("countryCode"),
        "business_city": business.get("city"),
        "fetched_at": fetched_at,
    })
sub = pd.DataFrame(rows).astype("string")
sub.to_sql("sec_submissions_raw", engine, schema="data", if_exists="replace", index=False)
print("sec_submissions_raw :", len(sub))
