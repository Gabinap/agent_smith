# Répartition du travail — Projet Agent Smith (v2, redécoupée)

_Groupe de 3. Ce document remplace le découpage calqué sur les sections du sujet (V.1 → VIII) par un découpage par **modules techniques**, avec pour chacun un **contrat d'interface** explicite._

---

## 0. Pourquoi redécouper

Le plan du sujet est une **spécification**, pas un plan de travail. Le suivre à la lettre produit quatre problèmes concrets :

| Problème dans le découpage v1 | Conséquence |
|---|---|
| V.3 (MBPP) et V.4 (SWE-bench) sont deux « parties » distinctes | On écrit deux fois un CLI, deux fois une boucle, deux fois l'écriture de `solution.json`. ~70 % de code commun dupliqué entre deux personnes. |
| Les modèles Pydantic (`StepMetrics`, `SolutionOutput`, `SandboxConfig`) apparaissent dans V.2, V.3 et V.4 | Personne n'en est propriétaire → trois versions divergentes, conflits de merge garantis en semaine 2. |
| V.1 et V.2 se partagent `final_answer`, les messages d'échec et le format d'observation | Zone grise entre deux personnes : chacun suppose que l'autre le fait. |
| Docker est un sous-point de V.4 | La brique la plus longue à fiabiliser démarre en semaine 2, alors qu'elle ne dépend de rien. |
| V.1 et V.2 sont marqués « bloquants » | Faux si on écrit des stubs. C'est un blocage organisationnel, pas technique. |

**Principe retenu** : un module = un répertoire, un propriétaire, une interface stable, des tests qui tournent sans les autres modules.

---

## 1. Le déblocage : contrats + doublures

La v1 impose un déroulement en phases parce que tout attend la boucle et le sandbox. On supprime cette contrainte avec **M0** (une demi-journée collective en J1) qui fige les types échangés, plus trois doublures triviales :

- `FakeLLM` — rejoue une liste de réponses scriptées depuis un JSON. Permet de tester la boucle, l'extraction et le budget sans consommer un seul token.
- `FakeSandbox` — `exec()` nu, sans sécurité. Permet de développer la boucle et les adaptateurs avant que le vrai sandbox existe.
- `LocalExecBackend` — exécute les outils sur un dépôt cloné en local plutôt que dans Docker. Permet d'écrire et de tester les 9 outils obligatoires sans Docker.

À partir de là, **plus aucun module n'est bloquant** : tout le monde code contre une interface, et le remplacement d'une doublure par la vraie implémentation est un changement d'une ligne d'injection.

---

## 2. Carte des modules

| ID | Module | Durée | Dépend de | Type |
|---|---|---|---|---|
| M0 | Contrats & squelette repo | 0,5 j | — | 🤝 collectif J1 |
| M1 | LLM Gateway (providers, clés, usage) | 1,5 j | M0 | 🧩 |
| M2 | Extraction & normalisation multi-format | 1 j | M0 | 🧩 pure |
| M3 | Noyau sandbox (sécurité, isolation) | 2,5 j | M0 | 🔒 |
| M4 | Intégration MCP (client, wrappers, manuel) | 1,25 j | M0, M3 (point d'injection) | 🔒 |
| M5 | Serveurs MCP & 9 outils obligatoires | 1,75 j | M0 | 🧩 |
| M6 | Backend d'exécution Docker | 1,25 j | M0 | 🧩 |
| M7 | Orchestrateur (boucle, budget, métriques, logs) | 1,5 j | M0 | 🔒 |
| M8 | Adaptateurs benchmark + CLI agents | 1 j | M7, M5, M6 | 🧩 |
| M9 | Prompt engineering & itération | 2 j | M1..M8 | 🔁 continu |
| M10 | Benchmark & rapport | 2,5 j | M8, M9 | 🧩 |
| M11 | README, config, soumission | 1,25 j | — | 🔁 continu |
| | **Total** | **18 j** | | |

Légende : 🔒 indivisible · 🧩 divisible · 🔁 étalé dans le temps · 🤝 à faire ensemble

---

## 3. Fiches modules

### M0 — Contrats & squelette repo · 0,5 j · collectif, J1 matin

**Livrable** : le repo `uv` initialisé, l'arborescence de packages, et un module `core/contracts.py` contenant **tous** les types échangés entre modules.

```python
# Modèles imposés par le sujet
SandboxConfig, MBPPTaskInput, SWEBenchTaskInput, StepMetrics, SolutionOutput

# Types internes (les nôtres)
class LLMResponse:      text, input_tokens, output_tokens, request_time_ms,
                        api_url, model_name, retries
class ExtractedAction:  code: str, source_format: Literal["python","xml","json","react"],
                        warnings: list[str]
class ExecutionResult:  stdout, stderr, error, final_answer: str | None,
                        timed_out: bool, truncated: bool
class Observation:      text: str, kind: Literal["ok","no_code","malformed",
                        "timeout","truncated","syntax_error","tool_error"]
```

Plus les trois protocoles structurants :

```python
class ExecBackend(Protocol):        # implémenté par Local et Docker
    def run(cmd, workdir, timeout) -> CommandResult
    def read_file(path) -> str
    def write_file(path, content) -> None

class LLMClient(Protocol):
    def complete(system, messages, stop) -> LLMResponse

class BenchmarkAdapter(Protocol):   # implémenté par MBPP et SWEbench
    def load_task(path) -> TaskInput
    def build_user_prompt(task) -> str
    def mcp_spec(task) -> McpSpec
    def sandbox_config(task) -> SandboxConfig
    def finalize(final_answer_value) -> str   # code MBPP | patch git
```

**Fini quand** : `uv run pytest` passe sur un test bidon dans chaque package, et les trois doublures (`FakeLLM`, `FakeSandbox`, `LocalExecBackend`) sont commitées.

> Ne pas sauter cette étape et ne pas la déléguer. C'est le seul moment où les trois personnes doivent être d'accord sur la même chose, et c'est ce qui rend le reste parallélisable.

---

### M1 — LLM Gateway · 1,5 j · indépendant, démarre J1

**Périmètre** : abstraction multi-providers (OpenRouter, Groq, Gemini, Mistral…), pool de plusieurs clés par provider avec rotation sur rate limit / quota épuisé, fallback provider, politique de retry avec backoff, `stop_sequences`, comptage de tokens et de latence.

**Contrat** : implémente `LLMClient`. Un seul point d'entrée, aucune fuite du SDK provider au-delà de ce module.

**Points d'attention**
- Les clés viennent exclusivement de `.env` / variables d'environnement (`OPENROUTER_API_KEY`…). Toute clé en dur = échec sécurité à l'éval.
- Les `stop` sont fournis par l'appelant (le prompt décide de `<end_code>`), pas hardcodés ici.
- `retries` doit être remonté par appel : c'est un champ obligatoire de `StepMetrics`.
- Le choix du provider n'est pas noté ; la qualité de l'abstraction l'est. Critère : ajouter un provider = un nouveau fichier, zéro modification ailleurs.

**Fini quand** : un test coupe artificiellement la clé n°1 et la requête aboutit sur la clé n°2 sans exception remontée.

---

### M2 — Extraction & normalisation · 1 j · indépendant, démarre J1

**Périmètre** : `str` brut du LLM → `ExtractedAction`. Gère les 4 formats du sujet (bloc Python, XML façon Anthropic, JSON/Hermes, ReAct) et convertit les trois derniers en appels de fonctions Python équivalents. Détecte et signale les blocs malformés réparés (backticks manquants, `python` absent, bloc non fermé) via `warnings`.

**Pourquoi c'est un module séparé** : ce sont des **fonctions pures**. Aucune dépendance, testables par une table de ~30 cas d'entrée/sortie, développables en parallèle total. Les noyer dans « la boucle » est la principale raison pour laquelle la v1 rendait V.1 bloquant.

**Fini quand** : la table de cas passe, y compris les cas dégradés (aucun bloc, deux blocs, bloc vide, XML tronqué).

---

### M3 — Noyau sandbox · 2,5 j · 🔒 une seule personne

**Périmètre** : la frontière d'exécution. Choix de l'approche d'isolation (in-process vs sous-processus — à documenter et défendre), restriction des imports par allowlist, allowlist de répertoires, blocage réseau, timeout d'exécution, limite mémoire, builtins restreints, injection de `final_answer` dans le namespace, propagation correcte de `KeyboardInterrupt` / `SystemExit`.

**Contrat** : `Sandbox.execute(code: str) -> ExecutionResult`. Le namespace injectable est exposé via une méthode `register(name, callable)` — c'est le point d'accroche de M4.

**Contraintes du sujet**
- Stdlib et builtins uniquement, pas de `RestrictedPython`.
- Le timeout ne concerne **que** le code exécuté dans le sandbox, jamais les actions du serveur MCP.
- `KeyboardInterrupt` / `SystemExit` ne doivent jamais être avalés silencieusement.
- `final_answer` est un construct du sandbox, **pas** un outil MCP : il reste présent quel que soit le serveur connecté.

**Fini quand** : une suite de tests d'attaque passe — `import os`, `open("/etc/passwd")`, `socket.socket()`, `while True`, allocation de 2 Go, `__builtins__` reconstruit via `().__class__.__mro__`.

---

### M4 — Intégration MCP · 1,25 j · même personne que M3

**Périmètre** : client MCP en **stdio et HTTP streamable**, découverte dynamique des outils, génération automatique des wrappers Python injectés dans le namespace du sandbox, génération du **manuel** (noms, descriptions, types de paramètres) à partir des schémas du serveur.

**Contrat** : `McpSession.tools() -> list[ToolSpec]` et `McpSession.manual() -> str`. Le sandbox enveloppe le client MCP, jamais l'inverse.

**Point critique** : le système sera testé avec un **serveur MCP inconnu**. Zéro nom d'outil en dur, nulle part — ni dans le code, ni dans le prompt système (le manuel y est injecté à l'exécution).

**Fini quand** : `uv run sandbox --mcp-stdio "<serveur de test écrit exprès, avec des outils bidons>"` expose ces outils bidons et un manuel correct sans toucher au code.

---

### M5 — Serveurs MCP & outils obligatoires · 1,75 j · indépendant, démarre J1

**Périmètre** : `mcp_tools_mbpp.py` et `mcp_tools_swebench.py` à la racine du repo, et les 9 outils.

| Sous-lot | Outils | Durée |
|---|---|---|
| M5.a Fichiers | `read_file`, `edit_file`, `list_files` | 0,5 j |
| M5.b Recherche | `search_code`, `search_function_or_class_definition_in_code`, `find_references` | 0,75 j |
| M5.c Exécution | `run_tests`, `get_patch`, `run_command` | 0,5 j |

**Contrat** : chaque outil est écrit **une seule fois**, contre `ExecBackend`. En local il tourne sur un clone du dépôt, en éval sur le backend Docker. C'est le gain principal du redécoupage : les outils ne connaissent pas Docker.

**Points d'attention** : les formats de sortie exacts sont notés — `<n>: <ligne>` façon `cat -n` pour `read_file`, `/chemin/absolu.py:<n> <ligne>` pour les trois outils de recherche. Ces outils sont testés **isolément** pendant l'éval, hors boucle d'agent.

**Fini quand** : un test compare la sortie de `search_code` à celle de `grep -rn` sur le même dépôt, et `read_file` à `cat -n`.

---

### M6 — Backend d'exécution Docker · 1,25 j · indépendant, démarre J1

**Périmètre** : implémentation Docker de `ExecBackend`. Pull d'image, création du conteneur, montage éventuel de `${TESTBED_PATH}`, exécution de commandes, récupération du diff via `git -c core.fileMode=false diff`, exécution de l'`eval_script`, et **nettoyage garanti** des conteneurs.

**Pourquoi séparé de M5** : c'est de la plomberie d'infrastructure, sans rapport avec la sémantique des outils, et c'est ce qui casse le plus souvent. En faire un module indépendant permet de le fiabiliser dès la semaine 1 au lieu de le découvrir en semaine 2.

**Point d'attention** : le nettoyage doit survivre à un crash et à un Ctrl-C — context manager plus filet de sécurité (`atexit` ou label + purge au démarrage). Un conteneur orphelin après l'éval est une pénalité.

**Fini quand** : un script pull `sympy__sympy-14711`, lit un fichier, applique une édition, produit un diff non vide, lance `run_tests`, et ne laisse aucun conteneur ni volume derrière lui même si on l'interrompt au milieu.

---

### M7 — Orchestrateur · 1,5 j · 🔒 une seule personne

**Périmètre** : la boucle Thought → Code → Observation, **générique sur le benchmark**. Compteur d'itérations (`max_iterations` configurable), budget cumulé de tokens en entrée/sortie, timeout global, arrêt sur `final_answer`, formatage des `Observation` renvoyées au LLM, collecte des `StepMetrics`, écriture de `SolutionOutput` et de l'arborescence `./evaluations/EVAL_TYPE/YYYY-MM-DD_HH-MM-SS/task_id/`.

**Contrat** : `AgentLoop(llm, sandbox, adapter, config).run(task) -> SolutionOutput`.

**Ce qui remonte ici depuis la v1** : la structure de logs (ex-VI.5) n'est pas une tâche à recoller « à la personne qui fait V.3 ou V.4 » — c'est une responsabilité transverse de l'orchestrateur, donc 20 minutes ici au lieu d'une tâche isolée.

**Feedback explicite** — l'orchestrateur doit produire une `Observation` non ambiguë dans les 5 cas du sujet : aucun bloc de code trouvé, bloc malformé mais interprété (en expliquant comment), timeout avec sortie partielle, sortie tronquée par la limite de taille, édition ayant introduit une erreur de syntaxe. Le LLM ne doit jamais avoir à deviner.

**Budget** : couper **avant** le dépassement, pas après. Si l'appel suivant ferait franchir la limite de tokens, la boucle s'arrête et écrit `success: false` proprement — un dépassement fait échouer la tâche, un arrêt propre laisse une chance sur les autres.

**Fini quand** : la boucle résout une tâche MBPP de bout en bout avec `FakeLLM` et `FakeSandbox`, et le `solution.json` produit valide contre le schéma.

---

### M8 — Adaptateurs benchmark & CLI · 1 j

Parce que M7 est générique, il ne reste ici que le spécifique :

- **M8.a — MBPP · 0,25 j** : chargement de `MBPPTaskInput`, prompt de tâche, `finalize` renvoyant le code, serveur MCP `run_tests`, entrée `python -m agent_mbpp`. Limites : 10 itérations, 6 000 tokens in, 1 500 out, 120 s.
- **M8.b — SWE-bench · 0,75 j** : chargement de `SWEBenchTaskInput`, prompt d'issue, choix sandbox-dans-le-conteneur vs sandbox-hôte-avec-pont, `finalize` renvoyant `get_patch()`, entrée `python -m agent_swebench`. Limites : 30 itérations, 300 k in, 10 k out, 900 s.
- **M8.c — CLI sandbox interactif · inclus** : `uv run sandbox` en mode REPL, avec ou sans `--mcp-stdio` / `--mcp-server`, sortie propre sur `exit` et EOF.

> En v1, V.3 valait 1,5 j et V.4 4,25 j, en grande partie parce que chacun réimplémentait la boucle, le CLI et les métriques. Ici ces 5,75 j deviennent 1,5 j (M7) + 1 j (M8) + le temps d'itération, qui est isolé dans M9 où il est visible.

**Fini quand** : les trois commandes du sujet (dump → run → validate) passent pour les deux benchmarks.

---

### M9 — Prompt engineering & itération · 2 j · continu, réparti

**Ce n'est pas une tâche avec un livrable, c'est une boucle de réglage.** C'est pour ça qu'elle est sortie de V.1 et de V.4, où elle était invisible et sous-estimée.

**Périmètre** : rédaction du prompt système (doc des outils issue du manuel dynamique, slots de réponse `Thought` / `Code` / `Observation`, exemples de raisonnement, méthodologie de debug pas-à-pas), puis itération sur les 3 tâches de rodage (`sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`).

**Méthode**
1. Résoudre soi-même une tâche à la main, avec uniquement les outils dont dispose l'agent. Le raisonnement suivi **est** la méthodologie à écrire dans le prompt.
2. Lire systématiquement les 3 à 5 premières itérations de chaque run raté. Les erreurs y sont presque toujours dans le prompt ou les outils, pas dans le modèle.
3. Travailler d'abord sans limites de tokens ni d'itérations. Si ça ne passe pas sans contraintes, les contraintes n'arrangeront rien.

**Répartition** : une tâche de rodage par personne pendant la phase d'itération, avec une mise en commun quotidienne du prompt (un seul fichier, un seul propriétaire du merge, pour éviter trois prompts divergents).

**Bonus gratuit** : garder les `solution.json` avant/après un changement de prompt → c'est l'étude d'ablation exigée par M10, obtenue sans travail supplémentaire.

---

### M10 — Benchmark & rapport · 2,5 j

**Périmètre** : `BENCHMARK_REPORT.md` à la racine, ≥ 5 modèles × ≥ 3 tâches SWE-bench communes. Setup et justification du choix des tâches ; tableau pass/fail, itérations, tokens in/out, temps ; fiabilité des providers (latence moyenne, retries, disponibilité) ; ≥ 2 métriques intermédiaires ; ≥ 1 étude d'ablation ; conclusions argumentées sur les données.

**Répartition** : les runs sont parallélisables (1 à 2 modèles par personne, mêmes 3 tâches), la rédaction ne l'est pas → un pilote rédige, les deux autres relisent.

**Points d'attention**
- Étaler les runs dans le temps : 5 modèles × 3 tâches × plusieurs essais épuise vite les quotas gratuits.
- Les métriques intermédiaires se mesurent **à la main** en lisant les `solution.json` — pas d'outillage à écrire, c'est l'analyse qui est notée.
- Les `solution.json` doivent rester dans le repo comme preuve.
- Démarrer dès qu'**une** tâche SWE-bench passe, sans attendre les trois.

---

### M11 — README, config, soumission · 1,25 j · continu

**Périmètre** : `README.md` en anglais, première ligne en italique (`This project has been created as part of the 42 curriculum by <login1>, <login2>, <login3>.`), sections Description / Instructions / Resources (dont l'usage détaillé de l'IA), plus les sections imposées : architecture système, explication de la boucle, design du sandbox, détails d'implémentation des outils, résultats et analyse du benchmark. Fichiers de configuration sandbox et modèles. Vérification finale du repo.

**Règle** : chacun rédige la section de son module **au moment où il le termine**, pas à la fin. Le module M0 crée les 5 sections vides dès J1.

**Soumission** : ensemble, la veille de la deadline. Vérifier la taille du repo, le `.gitignore`, l'absence d'images Docker, de poids de modèles, d'outputs générés — et l'absence de clé d'API dans l'historique git, pas seulement dans le HEAD.

---

## 4. Répartition par domaine

Chacun garde **un domaine stable** du début à la fin, plutôt que de changer de sujet à chaque phase. Cela réduit le coût de contexte et rend les revues croisées plus utiles.

| | **A — Exécution** | **B — Outillage & environnements** | **C — Modèle & boucle** |
|---|---|---|---|
| Modules | M3 (2,5 j) + M4 (1,25 j) | M5 (1,75 j) + M6 (1,25 j) + M8.b (0,75 j) | M1 (1,5 j) + M2 (1 j) + M7 (1,5 j) + M8.a (0,25 j) |
| Sous-total | 3,75 j | 3,75 j | 4,25 j |
| M0 collectif | 0,17 j | 0,17 j | 0,17 j |
| M9 réparti | 0,67 j | 0,67 j | 0,67 j |
| M10 réparti | 0,83 j | 0,83 j | 0,83 j |
| M11 réparti | 0,4 j | 0,4 j | 0,4 j |
| **Total** | **≈ 5,8 j** | **≈ 5,8 j** | **≈ 6,3 j** |

**Revues croisées** : A relit les outils de B (frontière sandbox/MCP), B relit la boucle de C (consommation des outils), C relit le sandbox de A (contrat d'exécution). Chaque frontière est ainsi relue par ses deux côtés.

---

## 5. Déroulement

**Semaine 1 — parallèle total, aucun blocage**

- J1 matin : M0 ensemble.
- J1 → J4 : A sur M3, B sur M5 puis M6, C sur M1 puis M2 puis M7.
- Fin de semaine : A branche M4 sur M3, C branche M7 sur les vrais M1/M2, B branche M5 sur M6. Trois intégrations indépendantes, pas un big bang.

**Semaine 2 — intégration et itération**

- Début de semaine : M8.a (MBPP bout en bout — c'est le test d'intégration réel du système : LLM → extraction → sandbox → MCP → observation), puis M8.b.
- Reste de la semaine : M9, une tâche de rodage par personne, mise en commun quotidienne du prompt.

**Semaine 3 — mesure et finalisation**

- M10 : runs répartis dès qu'une tâche passe, puis rédaction.
- M11 : assemblage du README (les sections sont déjà écrites), vérification du repo.
- Réserve : garder 2 jours de marge. La partie qui déborde est presque toujours M9.

**Calendrier réaliste : 2,5 à 3 semaines.**

---

## 6. Chemin critique et risques

**Chemin critique** : M0 → M7 → M8.b → M9 → M10. Environ 7,25 j incompressibles, plus le temps d'itération. Ce n'est plus le sandbox (M3) qui est critique, contrairement à la v1 : `FakeSandbox` le sort du chemin critique, ce qui laisse à A le temps de bien faire la sécurité — la partie sur laquelle l'éval est binaire.

| Risque | Signal d'alerte | Parade |
|---|---|---|
| M9 déborde (le plus probable) | Aucune tâche SWE-bench passée à la fin de la semaine 2 | Réduire à une seule tâche cible, avec le modèle le plus capable, sans limites — prouver que ça marche avant d'optimiser |
| Quotas gratuits épuisés pendant M10 | Retries en hausse, 429 en série | Multiplier les clés dès M1, étaler les runs, commencer le benchmark tôt |
| Conteneurs orphelins | `docker ps -a` qui gonfle | Traité dans M6 dès la semaine 1, pas à la fin |
| Serveur MCP inconnu à l'éval | Un nom d'outil en dur trouvé en relecture | `grep -r` sur les noms des 9 outils hors de M5 : zéro occurrence attendue |
| Modèles Pydantic divergents | Conflits de merge sur les schémas | M0 en fige la propriété : `core/contracts.py` ne se modifie qu'en accord à trois |
| Incapacité à défendre le code en soutenance | Une personne ne sait pas expliquer un module | Les revues croisées de la section 4, et un passage où chacun présente son domaine aux deux autres |
