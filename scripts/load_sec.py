# Charge les fichiers SEC bruts dans PostgreSQL (schema data, tables *_raw)
import json
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@localhost:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
RAW = "data/raw/sec"
OPTIONS = dict(sep="\t", dtype=str, quoting=3, encoding_errors="replace")

# Les postes financiers que l'on garde (notre plan de comptes simplifie)
TAGS = [
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss", "OperatingIncomeLoss",
    "Assets", "Liabilities", "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
]

# 1. Depots : uniquement les rapports annuels
sub = pd.read_csv(f"{RAW}/sub.txt", **OPTIONS)
sub = sub[sub["form"] == "10-K"]
sub.to_sql("sec_sub_raw", engine, schema="data", if_exists="replace", index=False)
print("sec_sub_raw :", len(sub))

# 2. Plan de comptes : uniquement nos tags standards
tag = pd.read_csv(f"{RAW}/tag.txt", **OPTIONS)
tag = tag[tag["tag"].isin(TAGS) & (tag["custom"] == "0")]
tag.to_sql("sec_tag_raw", engine, schema="data", if_exists="replace", index=False)
print("sec_tag_raw :", len(tag))

# 3. Montants : lus par morceaux car le fichier est gros
# on_bad_lines="warn" : une ligne mal formee de la source est ecartee et signalee
adsh_10k = set(sub["adsh"])
morceaux = []
for chunk in pd.read_csv(f"{RAW}/num.txt", chunksize=500_000,
                         on_bad_lines="warn", **OPTIONS):
    chunk = chunk[
        chunk["tag"].isin(TAGS)
        & (chunk["uom"] == "USD")
        & chunk["adsh"].isin(adsh_10k)
        & chunk["version"].str.startswith("us-gaap", na=False)
    ]
    # On garde le total de l'entreprise, pas les ventilations
    for col in ["coreg", "segments"]:
        if col in chunk.columns:
            chunk = chunk[chunk[col].isna()]
    morceaux.append(chunk)
num = pd.concat(morceaux)
num.to_sql("sec_num_raw", engine, schema="data", if_exists="replace",
           index=False, chunksize=10_000)
print("sec_num_raw :", len(num))

# 4. Deuxieme source du MDM : la liste officielle CIK / ticker / nom de la SEC
# Copie fidele, sans filtre : le CIK reste tel quel (mise sur 10 chiffres dans le MDM)
with open(f"{RAW}/company_tickers.json", encoding="utf-8") as f:
    tickers = pd.DataFrame(json.load(f).values()).astype(str)
tickers.to_sql("sec_company_tickers_raw", engine, schema="data",
               if_exists="replace", index=False)
print("sec_company_tickers_raw :", len(tickers))
