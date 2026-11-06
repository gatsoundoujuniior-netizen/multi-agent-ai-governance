# Enrichissement des tables Finance dans OpenMetadata (TP1 etapes 4.2, 4.3 et 5.6).
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

# 2. Tables : description (fiche catalogue), classification
# Les donnees de la SEC restent publiques. Un referentiel construit par nos regles est interne.
DEPOTS = ("Rapports annuels (10-K) deposes aupres de la SEC par les societes cotees aux "
          "Etats-Unis, trimestre 2026q1. Filtre : 10-K, 8 tags us-gaap, USD, sans ventilation.")
PUBLIC, INTERNAL = "Confidentialite.Public", "Confidentialite.Internal"
TABLES = {
    "data.sec_sub_raw": ("Copie brute des depots 10-K (une ligne par rapport depose). " + DEPOTS,
                         PUBLIC),
    "data.sec_num_raw": ("Copie brute des montants financiers (une ligne par montant). " + DEPOTS,
                         PUBLIC),
    "data.sec_tag_raw": ("Copie brute du plan de comptes XBRL, limite aux 8 tags retenus. " + DEPOTS,
                         PUBLIC),
    "data.sec_company_tickers_raw": ("Copie brute de la liste officielle SEC CIK / ticker / nom, "
                                     "sans filtre. Deuxieme source du MDM Tiers et Structures.",
                                     PUBLIC),
    "data.sec_submissions_raw": ("Copie brute des fiches EDGAR Submissions (une ligne par "
                                 "entreprise) pour les entreprises sans 10-K dans le trimestre. "
                                 "Troisieme source du MDM Tiers et Structures.", PUBLIC),
    "data.sec_financial_facts": ("Montants financiers (une ligne par montant), transactions "
                                 "reliees au Golden Record par company_id. Les montants vides "
                                 "de la source sont exclus.", PUBLIC),
    "master.company": ("Golden Record des entreprises : une ligne par CIK, 3 sources SEC. "
                       "Regle de priorite par attribut : nom = tickers puis 10-K puis EDGAR ; "
                       "pays et secteur = 10-K puis EDGAR. Les colonnes *_source gardent la "
                       "source gagnante.", INTERNAL),
    "master.xbrl_account": ("Plan de comptes : les 8 tags us-gaap retenus, avec leur categorie.",
                            INTERNAL),
    "ref.country": ("Codes pays ISO a 2 lettres et leurs libelles.", PUBLIC),
    "ref.currency": ("Codes devise et leurs libelles.", PUBLIC),
    "ref.sic": ("Codes secteur SIC de la SEC et leurs libelles.", PUBLIC),
    "ref.edgar_location": ("Traduction des codes de localisation EDGAR en codes pays ISO.", PUBLIC),
}
TABLE_TERMS = {"master.company": "Company"}

# 3. Colonnes : description (dictionnaire), PII.NonSensitive, terme de glossaire
COLUMNS = {
    "data.sec_sub_raw": {
        "adsh": ("Numero unique attribue par la SEC a chaque rapport depose.", None),
        "cik": ("Identifiant unique de l'entreprise a la SEC, ecrit sans les zeros de tete "
                "dans la source (a completer a 10 chiffres).", "CIK"),
        "name": ("Nom legal de l'entreprise tel qu'inscrit dans le rapport depose.", "Company"),
        "countryba": ("Pays du siege ou l'entreprise exerce son activite (code ISO 2 lettres).",
                      None),
    },
    "data.sec_num_raw": {
        "tag": ("Etiquette XBRL standard qui dit ce que mesure le montant.", "XBRL Tag"),
        "value": ("Montant declare par l'entreprise pour un poste et une date, "
                  "a lire avec uom et qtrs.", None),
        "qtrs": ("Nombre de trimestres couverts : 0 = montant a une date (bilan), "
                 "4 = montant sur un an.", None),
    },
    "data.sec_company_tickers_raw": {
        "cik_str": ("Identifiant SEC de l'entreprise, sans les zeros de tete.", "CIK"),
        "ticker": ("Symbole boursier, lien avec master.security (MDM Produits).", None),
        "title": ("Nom actuel de l'entreprise, tenu a jour par la SEC.", "Company"),
    },
    "data.sec_submissions_raw": {
        "cik": ("Identifiant SEC de l'entreprise, sans les zeros de tete.", "CIK"),
        "name": ("Nom de l'entreprise dans sa fiche EDGAR.", "Company"),
        "business_state_or_country": ("Code de localisation EDGAR du siege (Etat americain ou "
                                      "code maison, ex. M0 = Japon).", None),
    },
    "master.company": {
        "company_id": ("Cle technique du Golden Record, utilisee par les tables qui s'y relient.",
                       None),
        "cik": ("Cle metier : identifiant SEC sur 10 chiffres, sert au rapprochement des sources.",
                "CIK"),
        "legal_name": ("Nom retenu : tickers, puis 10-K, puis EDGAR.", "Company"),
        "name_source": ("Source gagnante du nom : TICKERS, DEPOT_10K ou EDGAR.", None),
        "country": ("Pays du siege en code ISO : 10-K, puis EDGAR. Vide si aucune source.", None),
        "country_source": ("Source gagnante du pays : DEPOT_10K ou EDGAR.", None),
        "sic_code": ("Code secteur SIC : 10-K, puis EDGAR. Vide si aucune source n'en donne.",
                     None),
        "sic_source": ("Source gagnante du secteur : DEPOT_10K ou EDGAR.", None),
    },
}

table_ids = {}
for table, (description, confidentiality) in TABLES.items():
    t = call("GET", f"/tables/name/{PREFIX}{table}?fields=columns,tags,owners,domains",
             token=token)
    table_ids[table] = t["id"]
    tags = [label(confidentiality), label("Sensibilite.Low")]
    if table in TABLE_TERMS:
        tags.append(label(terms[TABLE_TERMS[table]], source="Glossary"))
    ops = [
        {"op": "add", "path": "/description", "value": description},
        {"op": "add", "path": "/owners", "value": [{"id": team["id"], "type": "team"}]},
        {"op": "add", "path": "/domains", "value": [{"id": domain["id"], "type": "domain"}]},
        {"op": "add", "path": "/tags", "value": tags},
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

# 4. Lignage : de quelles tables chaque table est construite (sql/11_finance_mdm.sql)
LINEAGE = [
    ("data.sec_sub_raw", "master.company"),
    ("data.sec_company_tickers_raw", "master.company"),
    ("data.sec_submissions_raw", "master.company"),
    ("data.sec_tag_raw", "master.xbrl_account"),
    ("master.company", "data.sec_financial_facts"),
    ("master.xbrl_account", "data.sec_financial_facts"),
    ("data.sec_num_raw", "data.sec_financial_facts"),
]
for source, target in LINEAGE:
    call("PUT", "/lineage", {"edge": {
        "fromEntity": {"id": table_ids[source], "type": "table"},
        "toEntity": {"id": table_ids[target], "type": "table"}}}, token)
    print("lignage :", source, "->", target)
