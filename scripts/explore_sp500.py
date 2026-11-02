# Affiche les colonnes et un apercu des deux fichiers S&P 500
# Le fichier des cours est le plus gros CSV de data/raw/sp500 (hors constituents.csv)
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/sp500")
cours = sorted((f for f in RAW.glob("*.csv") if f.name != "constituents.csv"),
               key=lambda f: f.stat().st_size)
if not cours:
    raise SystemExit("Aucun fichier de cours dans data/raw/sp500 : telechargez le dataset Kaggle")
prices = cours[-1]

for f in [prices, RAW / "constituents.csv"]:
    df = pd.read_csv(f, nrows=5000, dtype=str)
    print(f"\n===== {f.name} : {len(df.columns)} colonnes")
    print(list(df.columns))
    print(df.head(3).T)

# Nombre total de lignes du gros fichier, sans tout charger en memoire
with open(prices, encoding="utf-8") as fichier:
    print(f"\nLignes de {prices.name} :", sum(1 for _ in fichier) - 1)

# Question 4 du TP : comment s'ecrit Berkshire Hathaway dans chaque fichier ?
const = pd.read_csv(RAW / "constituents.csv", dtype=str)
print("\nBerkshire dans constituents :", list(const.loc[const["Symbol"].str.startswith("BRK"), "Symbol"]))
symboles = set()
for chunk in pd.read_csv(prices, dtype=str, chunksize=500_000):
    col = next(c for c in chunk.columns if c.lower() in ("symbol", "ticker", "name"))
    symboles |= set(chunk[col].dropna())
print(f"Berkshire dans {prices.name} :", sorted(s for s in symboles if s.upper().startswith("BRK")))
print("Tickers distincts dans les cours :", len(symboles))
