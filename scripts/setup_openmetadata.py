# Configuration commune d'OpenMetadata (TP0 etape 5), identique sur les 3 machines.
# Relancable sans danger : chaque appel PUT cree l'objet ou le met a jour.
# Usage : python scripts/setup_openmetadata.py
import base64
import json
import os
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()
OM = os.getenv("OM_URL", "http://localhost:8585") + "/api/v1"


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


def login():
    password = os.getenv("OM_ADMIN_PASSWORD", "admin")
    body = {"email": os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org"),
            "password": base64.b64encode(password.encode()).decode()}
    return call("POST", "/users/login", body)["accessToken"]


token = login()

# 1. Classifications et tags (les memes noms sur les 3 machines)
CLASSIFICATIONS = {
    "Confidentialite": ("Niveau de confidentialite d'une donnee", {
        "Public": "Diffusable sans restriction",
        "Internal": "Reserve aux employes de l'entreprise",
        "Confidential": "Reserve aux personnes habilitees",
        "Restricted": "Acces tres limite, donnees critiques",
    }),
    "Sensibilite": ("Criticite d'une donnee en cas d'erreur ou de fuite", {
        "Low": "Impact faible",
        "Medium": "Impact moyen",
        "High": "Impact fort (financier, reglementaire ou personnel)",
    }),
}
for name, (description, tags) in CLASSIFICATIONS.items():
    call("PUT", "/classifications", {"name": name, "description": description,
                                     "mutuallyExclusive": True}, token)
    for tag, tag_description in tags.items():
        call("PUT", "/tags", {"name": tag, "description": tag_description,
                              "classification": name}, token)
    print("classification :", name, list(tags))

# 2. Equipes : les Data Owners sont des directions metier, jamais l'IT
# Type Group : dans OpenMetadata, seule une equipe Group peut etre owner d'un actif
for team in ["Direction Finance", "Direction Investissement", "Direction RH"]:
    call("PUT", "/teams", {"name": team, "displayName": team, "teamType": "Group",
                           "description": f"Data Owner : {team}"}, token)
    print("equipe :", team)

# 3. Domaines metier
DOMAINS = {
    "Finance": "Etats financiers et referentiel des entreprises (MDM Tiers et Structures)",
    "Investissement": "Marches, titres boursiers et produits d'investissement (MDM Produits)",
    "RH": "Employes et organisation (MDM Ressources humaines)",
}
for name, description in DOMAINS.items():
    call("PUT", "/domains", {"name": name, "description": description,
                             "domainType": "Source-aligned"}, token)
    print("domaine :", name)

# 4. Glossaire commun : chaque membre y ajoute ses termes
call("PUT", "/glossaries", {"name": "Glossaire Projet", "displayName": "Glossaire Projet",
                            "description": "Vocabulaire metier commun du projet"}, token)
print("glossaire : Glossaire Projet")

# 5. Service PostgreSQL du projet
# host.docker.internal = le PC vu depuis l'interieur du conteneur OpenMetadata
service = call("PUT", "/services/databaseServices", {
    "name": "gouv_postgres",
    "serviceType": "Postgres",
    "description": "PostgreSQL du projet (schemas ref, master, data, gov)",
    "connection": {"config": {
        "type": "Postgres",
        "username": os.getenv("POSTGRES_USER"),
        "authType": {"password": os.getenv("POSTGRES_PASSWORD")},
        "hostPort": f"host.docker.internal:{os.getenv('POSTGRES_PORT')}",
        "database": os.getenv("POSTGRES_DB"),
    }},
}, token)
print("service : gouv_postgres")

# 6. Ingestion des metadonnees : schemas data, master, ref (pas gov ni public)
pipeline = call("PUT", "/services/ingestionPipelines", {
    "name": "gouv_postgres_metadata",
    "displayName": "gouv_postgres_metadata",
    "pipelineType": "metadata",
    "service": {"id": service["id"], "type": "databaseService"},
    "sourceConfig": {"config": {
        "type": "DatabaseMetadata",
        "schemaFilterPattern": {"includes": ["^data$", "^master$", "^ref$"]},
    }},
    "airflowConfig": {},
}, token)
call("POST", f"/services/ingestionPipelines/deploy/{pipeline['id']}", token=token)
# Airflow met quelques secondes a lire un pipeline tout juste deploye
time.sleep(15)
call("POST", f"/services/ingestionPipelines/trigger/{pipeline['id']}", token=token)
print("ingestion lancee, attente du resultat...")

for _ in range(60):
    time.sleep(10)
    statuses = call("GET", f"/services/ingestionPipelines/{pipeline['id']}?fields=pipelineStatuses",
                    token=token).get("pipelineStatuses") or {}
    if isinstance(statuses, list):
        statuses = statuses[-1] if statuses else {}
    state = statuses.get("pipelineState")
    if state in ("success", "partialSuccess", "failed"):
        print("ingestion :", state)
        break
else:
    print("ingestion : toujours en cours, verifier dans l'interface")
