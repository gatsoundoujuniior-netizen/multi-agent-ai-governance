# Exploration du dataset IBM HR : colonnes, valeurs, cle metier, codes, constantes
# Usage : python scripts/explore_hr.py
import pandas as pd

df = pd.read_csv("data/raw/hr/hr_attrition.csv", encoding="utf-8-sig")
print("Dimensions (lignes, colonnes) :", df.shape)
print(df.dtypes.to_string())
print("\nValeurs manquantes :", df.isna().sum().sum())
print("Lignes en double :", df.duplicated().sum())

# Cle metier : le matricule doit etre unique
print("\nEmployeeNumber unique ?", df["EmployeeNumber"].is_unique,
      "| min", df["EmployeeNumber"].min(), "| max", df["EmployeeNumber"].max())

# Colonnes texte : quelles valeurs ?
for col in df.select_dtypes(exclude="number").columns:
    print(f"\n{col} :", df[col].unique())

# Colonnes qui ont toujours la meme valeur
print("\nColonnes constantes :",
      {c: df[c].iloc[0] for c in df.columns if df[c].nunique() == 1})

# Colonnes chiffrees a peu de valeurs : des codes dont le sens n'est pas dans le fichier
print("\nColonnes codees (5 valeurs ou moins) :")
for col in df.select_dtypes("number").columns:
    if 1 < df[col].nunique() <= 5:
        print(f"  {col} : {sorted(df[col].unique())}")

# Un poste appartient-il a un seul departement ?
print("\nDepartements par poste :")
print(df.groupby("JobRole")["Department"].unique().to_string())
