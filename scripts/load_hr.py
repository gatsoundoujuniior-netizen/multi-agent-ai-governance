# Charge le dataset IBM HR brut dans PostgreSQL (data.hr_employee_raw)
# Copie fidele, tout en texte. Seuls les noms de colonnes passent en snake_case.
# Les sources simulees (mobilite, sites) sont chargees en data.*_raw par sql/31_hr_mdm.sql
import os
import re
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@localhost:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

df = pd.read_csv("data/raw/hr/hr_attrition.csv", dtype=str, encoding="utf-8-sig")
# MonthlyIncome -> monthly_income (standard commun de nommage)
df.columns = [re.sub(r"(?<!^)(?=[A-Z])", "_", c).lower() for c in df.columns]

df.to_sql("hr_employee_raw", engine, schema="data", if_exists="replace", index=False)
print("hr_employee_raw :", len(df), "lignes,", len(df.columns), "colonnes")
print(list(df.columns))
