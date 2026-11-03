# Enrichissement des tables RH dans OpenMetadata (TP3 etape 4).
# Reprend la fiche catalogue et le dictionnaire de docs/dictionnaire/ibm_hr_analytics.md.
# Pre-requis : scripts/setup_openmetadata.py execute (classifications, equipe, domaine,
# glossaire, ingestion du service gouv_postgres).
# Usage : python scripts/enrich_openmetadata_hr.py
import base64
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()
OM = os.getenv("OM_URL", "http://localhost:8585") + "/api/v1"
PREFIX = "gouv_postgres.governance.data."


def call(method, path, body=None, token=None, content_type="application/json"):
    req = urllib.request.Request(OM + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} : {e.read().decode()[:300]}")


def label(fqn, source="Classification"):
    return {"tagFQN": fqn, "source": source, "labelType": "Manual", "state": "Confirmed"}


password = os.getenv("OM_ADMIN_PASSWORD", "admin")
token = call("POST", "/users/login", {
    "email": os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org"),
    "password": base64.b64encode(password.encode()).decode()})["accessToken"]

team = call("GET", "/teams/name/Direction RH".replace(" ", "%20"), token=token)
domain = call("GET", "/domains/name/RH", token=token)

# 1. Glossaire : les termes metier du membre HR
TERMS = {
    "Employee": "Personne liee a l'entreprise par un contrat de travail. "
                "Regle de gestion : un employe = un matricule = une ligne dans master.employee.",
    "Attrition": "Depart d'un employe de l'entreprise, volontaire ou non. "
                 "Regle de gestion : ne doit etre communique qu'en taux agrege "
                 "(par departement, par poste), jamais pour une personne.",
    "Department": "Unite organisationnelle de rattachement d'un employe. "
                  "Regle de gestion : doit exister une seule fois dans master.department.",
    "Performance Rating": "Evaluation annuelle de la performance, de 1 (Low) a 4 (Outstanding). "
                          "Regle de gestion : doit exister dans ref.performance_rating.",
}
terms = {}
for name, description in TERMS.items():
    terms[name] = call("PUT", "/glossaryTerms", {
        "glossary": "Glossaire Projet", "name": name, "description": description,
        "owners": [{"id": team["id"], "type": "team"}]}, token)["fullyQualifiedName"]
    print("terme :", name)

# 2. Tables : description (fiche catalogue), owner, domaine, classification
TABLES = {
    "hr_employee_raw": (
        "Copie brute du dataset IBM HR Analytics (Kaggle, fictif, traite comme reel) : "
        "photo de 1 470 employes avec poste, departement, formation, remuneration, "
        "satisfaction, performance, anciennete et depart (attrition). Tout en texte, "
        "aucune correction. Contient des PII : ne jamais exposer une ligne individuelle "
        "hors Direction RH.",
        ["Confidentialite.Confidential", "Sensibilite.High"]),
}

# 3. Colonnes : description (dictionnaire), tag PII, terme de glossaire
# PII.Sensitive : identifiant direct, quasi-identifiant ou remuneration
# PII.NonSensitive : ne designe personne a lui seul
COLUMNS = {
    "hr_employee_raw": {
        "employee_number": ("Matricule : numero unique attribue a l'employe par l'entreprise. "
                            "Identifiant direct.", "PII.Sensitive", "Employee"),
        "age": ("Age de l'employe a la date de la photo (18 a 60 ans). Quasi-identifiant.",
                "PII.Sensitive", None),
        "gender": ("Genre declare de l'employe (Female, Male). Quasi-identifiant.",
                   "PII.Sensitive", None),
        "marital_status": ("Situation familiale (Single, Married, Divorced). Quasi-identifiant.",
                           "PII.Sensitive", None),
        "monthly_income": ("Remuneration brute mensuelle de l'employe, en USD. Ne doit jamais "
                           "etre communiquee individuellement hors Direction RH.",
                           "PII.Sensitive", None),
        "daily_rate": ("Cout journalier de l'employe pour l'entreprise, en USD.",
                       "PII.Sensitive", None),
        "hourly_rate": ("Cout horaire de l'employe pour l'entreprise, en USD.",
                        "PII.Sensitive", None),
        "monthly_rate": ("Cout mensuel de l'employe pour l'entreprise, en USD "
                         "(different du salaire mensuel).", "PII.Sensitive", None),
        "department": ("Unite de l'organisation a laquelle l'employe est rattache "
                       "(Sales, Research & Development, Human Resources).",
                       "PII.NonSensitive", "Department"),
        "job_role": ("Fonction occupee par l'employe (9 postes, Manager existe dans les "
                     "3 departements).", "PII.NonSensitive", None),
        "attrition": ("Indique si l'employe a quitte l'entreprise : Yes = a quitte, "
                      "No = toujours present. A communiquer en taux agrege seulement.",
                      "PII.NonSensitive", "Attrition"),
        "education": ("Niveau d'etudes : 1 = Below College, 2 = College, 3 = Bachelor, "
                      "4 = Master, 5 = Doctor.", None, None),
        "performance_rating": ("Evaluation annuelle : 1 = Low, 2 = Good, 3 = Excellent, "
                               "4 = Outstanding.", None, "Performance Rating"),
        "job_satisfaction": ("Satisfaction envers le poste : 1 = Low, 2 = Medium, 3 = High, "
                             "4 = Very High.", None, None),
        "work_life_balance": ("Equilibre vie pro / vie perso : 1 = Bad, 2 = Good, 3 = Better, "
                              "4 = Best.", None, None),
    },
}

for table, (description, table_tags) in TABLES.items():
    t = call("GET", f"/tables/name/{PREFIX}{table}?fields=columns,tags,owners,domains",
             token=token)
    ops = [
        {"op": "add", "path": "/description", "value": description},
        {"op": "add", "path": "/owners", "value": [{"id": team["id"], "type": "team"}]},
        {"op": "add", "path": "/domains", "value": [{"id": domain["id"], "type": "domain"}]},
        {"op": "add", "path": "/tags", "value": [label(fqn) for fqn in table_tags]},
    ]
    for i, col in enumerate(t["columns"]):
        if col["name"] in COLUMNS.get(table, {}):
            col_description, pii, term = COLUMNS[table][col["name"]]
            col_tags = [label(pii)] if pii else []
            if term:
                col_tags.append(label(terms[term], source="Glossary"))
            ops.append({"op": "add", "path": f"/columns/{i}/description",
                        "value": col_description})
            ops.append({"op": "add", "path": f"/columns/{i}/tags", "value": col_tags})
    call("PATCH", f"/tables/{t['id']}", ops, token, "application/json-patch+json")
    print("table enrichie :", table)
