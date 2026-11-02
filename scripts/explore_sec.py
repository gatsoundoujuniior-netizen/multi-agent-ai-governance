# Affiche les colonnes et un aperçu de chaque fichier SEC
import pandas as pd

for f in ["sub", "num", "tag"]:
    df = pd.read_csv(f"data/raw/sec/{f}.txt", sep="\t", dtype=str,
                     nrows=5000, quoting=3, encoding_errors="replace")
    print(f"\n===== {f}.txt : {len(df.columns)} colonnes")
    print(list(df.columns))
    print(df.head(3).T)
