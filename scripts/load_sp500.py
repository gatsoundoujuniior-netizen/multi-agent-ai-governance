# Charge les fichiers S&P 500 bruts dans PostgreSQL (schema data, tables *_raw)
# Copie fidele, tout en texte. Seuls les noms de colonnes sont harmonises.
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@localhost:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
RAW = Path("data/raw/sp500")
DATE_MIN = None   # ex. "2019-01-01" si le chargement est trop long (a documenter !)
COLONNES_ATTENDUES = {"date", "symbol", "open", "high", "low", "close", "volume"}


def nettoyer_noms(df):
    # "Adj Close" -> "adj_close" : noms de colonnes en snake_case
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    # Selon le dataset Kaggle, le ticker s'appelle Symbol, Ticker ou Name
    if "symbol" not in df.columns:
        for alias in ("ticker", "name"):
            if alias in df.columns:
                return df.rename(columns={alias: "symbol"})
    return df


# 1. Liste des membres du S&P 500 (petit fichier, source prioritaire du MDM)
const = nettoyer_noms(pd.read_csv(RAW / "constituents.csv", dtype=str))
const.to_sql("sp500_constituents_raw", engine, schema="data", if_exists="replace", index=False)
print("sp500_constituents_raw :", len(const))

# 2. Historique des cours : le plus gros CSV du dossier, lu et charge par morceaux
cours = sorted((f for f in RAW.glob("*.csv") if f.name != "constituents.csv"),
               key=lambda f: f.stat().st_size)
if not cours:
    raise SystemExit("Aucun fichier de cours dans data/raw/sp500 : telechargez le dataset Kaggle")
print("Fichier des cours :", cours[-1].name)

total = 0
for i, chunk in enumerate(pd.read_csv(cours[-1], dtype=str, chunksize=200_000)):
    chunk = nettoyer_noms(chunk)
    if i == 0:
        manquantes = COLONNES_ATTENDUES - set(chunk.columns)
        if manquantes:
            raise SystemExit(f"Colonnes absentes : {manquantes}. Colonnes lues : {list(chunk.columns)}")
    if DATE_MIN:
        chunk = chunk[chunk["date"] >= DATE_MIN]
    chunk.to_sql("sp500_prices_raw", engine, schema="data",
                 if_exists="replace" if i == 0 else "append", index=False, chunksize=10_000)
    total += len(chunk)
    print("lignes chargees :", total)
