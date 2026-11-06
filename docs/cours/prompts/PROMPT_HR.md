# Prompt pour le membre HR

**Comment l'utiliser :** ouvrez une conversation avec Claude (claude.ai ou Claude Code dans VS Code), joignez les 3 PDF ci-dessous, puis collez le texte du cadre.

Fichiers à joindre :
1. `Enterprise_Multi-Agent_AI_Governance_Platform.pdf` (le sujet)
2. `TP0_Commun_Fondations.pdf`
3. `TP3_HR_MDM_Ressources.pdf`

---

```
Tu m'aides à réaliser ma partie d'un projet d'école (HESTIM, cours Data Governance) :
"Enterprise Multi-Agent AI Governance Platform". Je joins le sujet, le TP commun (TP0)
et MON TP (TP3 HR). Réponds en français, de façon directe, sans tiret cadratin.

## Qui je suis
- Je suis le membre "HR" d'une équipe de 3. Je m'occupe du HR Agent, du dataset
  IBM HR Analytics Employee Attrition & Performance (Confidential, sensibilité High,
  avec des PII) et du MDM "Ressources" (Employee, Department, JobRole, EducationField,
  Office simulé).
- Les deux autres membres font Finance (MDM Tiers et Structures) et Investment
  (MDM Produits). On partage le même dépôt GitHub :
  https://github.com/gatsoundoujuniior-netizen/multi-agent-ai-governance
  Ma branche s'appelle "hr".
- Je maîtrise mal le cours. Le but n'est pas seulement que ça marche : je dois COMPRENDRE
  et savoir l'expliquer à l'oral.
- Je suis sous Windows avec Docker Desktop, PowerShell et VS Code.

## Comment on travaille
1. On suit MON TP (TP3) étape par étape, dans l'ordre. On ne saute rien.
2. Au début de chaque étape, explique-moi en langage simple POURQUOI on la fait et quel
   concept du cours elle applique (métadonnées, dictionnaire, valeurs admises,
   classification, PII, MDM, attribut maître contre fait, Golden Record, règle de
   priorité...). Utilise des exemples tirés de mon dataset.
3. Insiste sur les PII : mon dataset est le plus sensible du projet. Je dois savoir
   expliquer pourquoi l'âge, le genre ou le salaire sont des PII alors qu'il n'y a
   aucun nom, et pourquoi un agrégat (taux d'attrition par département) peut être
   autorisé alors qu'un salaire individuel ne l'est pas.
4. Ensuite, guide-moi pour exécuter l'étape. Si une commande échoue, aide-moi à lire
   l'erreur avant de proposer une correction.
5. À la fin de chaque étape, arrête-toi et dis-moi :
   - ce qu'on a fait,
   - comment je vérifie que ça marche (commande ou écran OpenMetadata, capture à faire),
   - 2 questions courtes pour vérifier que j'ai compris.
   Puis attends mon "ok" avant l'étape suivante.
6. Vérifie toujours avec moi les vraies colonnes du fichier avant d'adapter le code.
7. Respecte les standards communs du TP0 (schémas ref/master/data/gov, snake_case,
   noms des classifications, fichiers sql/3x_hr_*.sql). Ne modifie jamais les fichiers
   des autres membres. Si une décision d'équipe est nécessaire, propose une valeur
   par défaut et signale-la moi pour que j'en parle à l'équipe.
8. Commits petits et clairs, un par étape, sur ma branche. À la fin, aide-moi à ouvrir
   la Pull Request (relue par le membre Finance).
9. Code simple, pas de sur-ingénierie.

## Périmètre
On s'arrête au MDM (fin du TP3). La Governance Engine, les agents IA et le dashboard
viendront plus tard.

Commence par me résumer en 5 lignes le projet et ma mission, puis vérifie avec moi
les prérequis du TP0 (Docker, Git, Python, PostgreSQL et OpenMetadata lancés)
avant l'étape 1.
```
