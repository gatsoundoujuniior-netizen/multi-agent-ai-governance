# Enrichissement des tables RH dans OpenMetadata (TP3 etapes 4 et 5.6).
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
PREFIX = "gouv_postgres.governance."


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

# 2. Tables : description (fiche catalogue), owner, domaine, classification, terme
# La classification se decide table par table : les personnes sont Confidential,
# l'organisation et les codes sont Internal
CONFIDENTIAL = ["Confidentialite.Confidential", "Sensibilite.High"]
INTERNAL = ["Confidentialite.Internal", "Sensibilite.Low"]
TABLES = {
    "data.hr_employee_raw": (
        "Copie brute du dataset IBM HR Analytics (Kaggle, fictif, traite comme reel) : "
        "photo de 1 470 employes avec poste, departement, formation, remuneration, "
        "satisfaction, performance, anciennete et depart (attrition). Tout en texte, "
        "aucune correction. Contient des PII : ne jamais exposer une ligne individuelle "
        "hors Direction RH.", CONFIDENTIAL, None),
    "data.hr_mobility_raw": (
        "Copie brute de la mobilite interne (donnees simulees) : changements de departement "
        "et de poste avec leur date d'effet. Deuxieme source du MDM Ressources humaines.",
        ["Confidentialite.Confidential", "Sensibilite.Medium"], None),
    "data.hr_office_raw": (
        "Copie brute des sites de l'entreprise (donnees simulees).", INTERNAL, None),
    "master.employee": (
        "Golden Record des employes : une ligne par matricule, attributs maitres seulement "
        "(genre, situation familiale, departement, poste, niveau, formation). Regle de "
        "priorite : pour le departement et le poste, la mobilite la plus recente gagne sur "
        "le fichier IBM HR. department_source et job_role_source indiquent la source "
        "gagnante. Contient des PII (genre, situation familiale).", CONFIDENTIAL, "Employee"),
    "data.hr_employee_facts": (
        "Faits RH par employe (age, remuneration, satisfaction, performance, anciennete, "
        "attrition), relies a master.employee par employee_id. Contient des PII (age, "
        "salaires) : seuls des agregats peuvent sortir de la Direction RH.",
        CONFIDENTIAL, None),
    "master.department": (
        "Referentiel des departements (3), chacun rattache a un site.", INTERNAL, "Department"),
    "master.job_role": (
        "Referentiel des postes (9), independant du departement : Manager existe dans les "
        "3 departements.", INTERNAL, None),
    "master.education_field": ("Referentiel des filieres d'etudes (6).", INTERNAL, None),
    "master.office": (
        "Referentiel des sites de l'entreprise. Donnees simulees (le dataset IBM HR ne "
        "contient aucun lieu).", INTERNAL, None),
    "ref.education_level": (
        "Signification officielle du code education : 1 = Below College a 5 = Doctor.",
        INTERNAL, None),
    "ref.satisfaction_level": (
        "Signification officielle des codes de satisfaction et d'implication : "
        "1 = Low a 4 = Very High.", INTERNAL, None),
    "ref.performance_rating": (
        "Signification officielle du code performance_rating : 1 = Low a 4 = Outstanding.",
        INTERNAL, "Performance Rating"),
    "ref.work_life_balance": (
        "Signification officielle du code work_life_balance : 1 = Bad a 4 = Best.",
        INTERNAL, None),
}

# 3. Colonnes : description (dictionnaire), tag PII, terme de glossaire
# PII.Sensitive : identifiant direct, quasi-identifiant ou remuneration
# PII.NonSensitive : ne designe personne a lui seul
COLUMNS = {
    "master.employee": {
        "employee_number": ("Matricule, cle metier du Golden Record. Identifiant direct.",
                            "PII.Sensitive", "Employee"),
        "gender": ("Genre declare de l'employe. Quasi-identifiant.", "PII.Sensitive", None),
        "marital_status": ("Situation familiale de l'employe. Quasi-identifiant.",
                           "PII.Sensitive", None),
        "department_source": ("Source gagnante pour le departement : IBM_HR ou MOBILITY.",
                              None, None),
        "job_role_source": ("Source gagnante pour le poste : IBM_HR ou MOBILITY.", None, None),
    },
    "data.hr_employee_facts": {
        "age": ("Age de l'employe a la date de la photo. Quasi-identifiant.",
                "PII.Sensitive", None),
        "monthly_income": ("Remuneration brute mensuelle, en USD. Ne doit jamais etre "
                           "communiquee individuellement hors Direction RH.",
                           "PII.Sensitive", None),
        "daily_rate": ("Cout journalier de l'employe, en USD.", "PII.Sensitive", None),
        "hourly_rate": ("Cout horaire de l'employe, en USD.", "PII.Sensitive", None),
        "monthly_rate": ("Cout mensuel de l'employe, en USD.", "PII.Sensitive", None),
        "attrition": ("Vrai si l'employe a quitte l'entreprise. A communiquer en taux "
                      "agrege seulement.", "PII.NonSensitive", "Attrition"),
    },
    "data.hr_mobility_raw": {
        "employee_number": ("Matricule de l'employe qui change de poste.",
                            "PII.Sensitive", "Employee"),
    },
    "data.hr_employee_raw": {
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

table_ids = {}
for table, (description, table_tags, table_term) in TABLES.items():
    t = call("GET", f"/tables/name/{PREFIX}{table}?fields=columns,tags,owners,domains",
             token=token)
    table_ids[table] = t["id"]
    tags = [label(fqn) for fqn in table_tags]
    if table_term:
        tags.append(label(terms[table_term], source="Glossary"))
    ops = [
        {"op": "add", "path": "/description", "value": description},
        {"op": "add", "path": "/owners", "value": [{"id": team["id"], "type": "team"}]},
        {"op": "add", "path": "/domains", "value": [{"id": domain["id"], "type": "domain"}]},
        {"op": "add", "path": "/tags", "value": tags},
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

# 4. Lignage : de quelles tables chaque table est construite (sql/31_hr_mdm.sql)
LINEAGE = [
    ("data.hr_employee_raw", "master.department"),
    ("data.hr_employee_raw", "master.job_role"),
    ("data.hr_employee_raw", "master.education_field"),
    ("data.hr_office_raw", "master.office"),
    ("data.hr_employee_raw", "master.employee"),
    ("data.hr_mobility_raw", "master.employee"),
    ("master.employee", "data.hr_employee_facts"),
    ("data.hr_employee_raw", "data.hr_employee_facts"),
]
for source, target in LINEAGE:
    call("PUT", "/lineage", {"edge": {
        "fromEntity": {"id": table_ids[source], "type": "table"},
        "toEntity": {"id": table_ids[target], "type": "table"}}}, token)
    print("lignage :", source, "->", target)
