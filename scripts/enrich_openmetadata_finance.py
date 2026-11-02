# Enrichissement des tables Finance dans OpenMetadata (TP1 etape 4.2 et 4.3).
# Reprend la fiche catalogue et le dictionnaire de docs/dictionnaire/sec_financial_statements.md.
# Pre-requis : scripts/setup_openmetadata.py execute (classifications, equipe, domaine,
# glossaire, ingestion du service gouv_postgres).
# Usage : python scripts/enrich_openmetadata_finance.py
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

team = call("GET", "/teams/name/Direction Finance".replace(" ", "%20"), token=token)
domain = call("GET", "/domains/name/Finance", token=token)

# 1. Glossaire : les termes metier du membre Finance
TERMS = {
    "Company": "Entite juridique cotee qui depose des rapports a la SEC. "
               "Regle de gestion : une entreprise = un CIK = une ligne dans master.company.",
    "CIK": "Identifiant unique d'une entreprise a la SEC (Central Index Key). "
           "Regle de gestion : doit etre ecrit sur 10 chiffres, completes par des zeros a gauche.",
    "Revenue": "Chiffre d'affaires : total des ventes de la periode. "
               "Regle de gestion : correspond aux tags XBRL Revenues et "
               "RevenueFromContractWithCustomerExcludingAssessedTax.",
    "XBRL Tag": "Etiquette standard d'un poste financier dans les rapports deposes a la SEC. "
                "Regle de gestion : seuls les tags us-gaap standards (custom = 0) sont utilises.",
}
terms = {}
for name, description in TERMS.items():
    terms[name] = call("PUT", "/glossaryTerms", {
        "glossary": "Glossaire Projet", "name": name, "description": description,
        "owners": [{"id": team["id"], "type": "team"}]}, token)["fullyQualifiedName"]
    print("terme :", name)

# 2. Tables : description (fiche catalogue), owner, domaine, classification
DEPOTS = ("Rapports annuels (10-K) deposes aupres de la SEC par les societes cotees aux "
          "Etats-Unis, trimestre 2026q1. Filtre : 10-K, 8 tags us-gaap, USD, sans ventilation.")
TABLES = {
    "sec_sub_raw": "Copie brute des depots 10-K (une ligne par rapport depose). " + DEPOTS,
    "sec_num_raw": "Copie brute des montants financiers (une ligne par montant). " + DEPOTS,
    "sec_tag_raw": "Copie brute du plan de comptes XBRL, limite aux 8 tags retenus. " + DEPOTS,
    "sec_company_tickers_raw": "Copie brute de la liste officielle SEC CIK / ticker / nom, "
                               "sans filtre. Deuxieme source du MDM Tiers et Structures.",
}

# 3. Colonnes : description (dictionnaire), PII.NonSensitive, terme de glossaire
COLUMNS = {
    "sec_sub_raw": {
        "adsh": ("Numero unique attribue par la SEC a chaque rapport depose.", None),
        "cik": ("Identifiant unique de l'entreprise a la SEC, ecrit sans les zeros de tete "
                "dans la source (a completer a 10 chiffres).", "CIK"),
        "name": ("Nom legal de l'entreprise tel qu'inscrit dans le rapport depose.", "Company"),
        "countryba": ("Pays du siege ou l'entreprise exerce son activite (code ISO 2 lettres).",
                      None),
    },
    "sec_num_raw": {
        "tag": ("Etiquette XBRL standard qui dit ce que mesure le montant.", "XBRL Tag"),
        "value": ("Montant declare par l'entreprise pour un poste et une date, "
                  "a lire avec uom et qtrs.", None),
        "qtrs": ("Nombre de trimestres couverts : 0 = montant a une date (bilan), "
                 "4 = montant sur un an.", None),
    },
    "sec_company_tickers_raw": {
        "cik_str": ("Identifiant SEC de l'entreprise, sans les zeros de tete.", "CIK"),
        "ticker": ("Symbole boursier, lien avec master.security (MDM Produits).", None),
        "title": ("Nom actuel de l'entreprise, tenu a jour par la SEC.", "Company"),
    },
}

for table, description in TABLES.items():
    t = call("GET", f"/tables/name/{PREFIX}{table}?fields=columns,tags,owners,domains",
             token=token)
    ops = [
        {"op": "add", "path": "/description", "value": description},
        {"op": "add", "path": "/owners", "value": [{"id": team["id"], "type": "team"}]},
        {"op": "add", "path": "/domains", "value": [{"id": domain["id"], "type": "domain"}]},
        {"op": "add", "path": "/tags", "value": [label("Confidentialite.Public"),
                                                 label("Sensibilite.Low")]},
    ]
    for i, col in enumerate(t["columns"]):
        if col["name"] in COLUMNS.get(table, {}):
            col_description, term = COLUMNS[table][col["name"]]
            col_tags = [label("PII.NonSensitive")]
            if term:
                col_tags.append(label(terms[term], source="Glossary"))
            ops.append({"op": "add", "path": f"/columns/{i}/description",
                        "value": col_description})
            ops.append({"op": "add", "path": f"/columns/{i}/tags", "value": col_tags})
    call("PATCH", f"/tables/{t['id']}", ops, token, "application/json-patch+json")
    print("table enrichie :", table)
