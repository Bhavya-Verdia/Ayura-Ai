# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Deployment
Production deploys run in **GitHub Actions on push to `main`** (`.github/workflows/deploy.yml`),
gated on CI. There is nothing to run locally.

```bash
gh run watch                                    # follow the deploy
gh run list --workflow="Ayura AI Deploy" -L 5   # recent deploys
gh workflow run "Ayura AI Deploy"               # deploy without a push
```

`./deploy.sh` is break-glass only and refuses to run without `--break-glass`. Do not use it
because it is faster: a local deploy and a push-triggered one both run `docker compose rm -fs`
then `up -d` on the same droplet, and the collision has taken production down — Docker renames
the loser's container, the next run hits "container name is already in use", and the site can
be left with nothing running. **Never accept a deploy script's own success line as evidence**;
verify by image timestamp and by fetching the served asset.

### Infrastructure
```bash
docker-compose up -d          # Start MongoDB, Redis, ChromaDB
```

### Backend
```bash
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000   # Dev server
arq worker.WorkerSettings                          # Background job worker (separate terminal)
python scripts/build_vectors.py                    # Seed ChromaDB knowledge base
```

### Frontend
```bash
cd client
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # Vite build; postbuild runs scripts/prerender.mjs (multi-route SEO) + check-bundle-size.mjs
npm run lint
npm run test:e2e  # Playwright E2E tests
npm run test:e2e:ui
```

### Backend Tests
```bash
cd server
pytest                            # All tests
pytest tests/test_auth.py         # Single test file
pytest tests/test_auth.py::test_register_user  # Single test
```

## Environment Variables

Copy `.env.example` to `.env` at the repo root. Settings are loaded by `server/config.py` (pydantic-settings), which reads both `server/.env` and the root `.env`.

Key variables:
- `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` — primary LLM (GPT-4o)
- `GEMINI_API_KEY` — fallback LLM (Gemini 2.0 Flash); app runs without Azure if only this is set
- `MONGO_URL` — full MongoDB URI, or set `MONGO_HOST`/`MONGO_PORT`/`MONGO_DB` individually
- `REDIS_URL` — required for ARQ background worker; rate limiting degrades gracefully without it
- `CHROMA_HOST` / `CHROMA_PORT` — if set, uses remote ChromaDB HTTP client; otherwise embedded PersistentClient at `server/data/chromadb/`
- `JWT_SECRET_KEY`, `SECRET_KEY` — must be changed from defaults in production
- `VITE_API_URL` — frontend API base; defaults to `/api` (proxied by Vite dev server to port 8000)

## Architecture

### Request Flow
The Vite dev server proxies `/api` and `/uploads` to `http://127.0.0.1:8000`. In production, nginx (see `client/nginx.conf`) handles this. All routes are mounted at `/api/<resource>` in `server/main.py`.

### Authentication
JWT tokens are stored exclusively in **HTTP-only cookies** (`ayura_access`, `ayura_refresh`) — never localStorage. The frontend axios client in `client/src/api/client.js` sends `withCredentials: true` and auto-refreshes on 401 via `/api/auth/refresh`. Google and GitHub OAuth are supported alongside email/password.

### AI Plan Generation Pipeline (engine-backed + LLM enrichment)
Each feature is produced by a **deterministic, KB-grounded engine**, then optionally enriched with LLM-generated narrative. There is no free-text LLM agent that authors plans (an earlier 4-agent LangGraph pipeline was removed because it ignored the KB and could hallucinate formulations/asanas).

1. **Tier 1 — Core rule engines** (`server/engine/`): BMI, calorie, dosha analysis, seasonal adjustments, condition filtering.
2. **Tier 2 — Per-feature engines** (`server/services/`): `gym_plan_engine`, `yoga_plan_engine`, `diet_plan_engine`, `panchakarma_engine`, `routine_engine`, `remedy_engine` (medicines + home remedies). Each builds a structured plan from the bundled JSON knowledge bases. Diet is **LLM-primary** (`diet_llm_generator`) with the rule engine as a fallback.
3. **Tier 3 — LLM enrichers** (`server/services/*_enricher.py`): add narrative/coaching on top of the deterministic plan via the shared `llm_client`. RAG (`server/ai/rag_pipeline.py`) provides ChromaDB semantic context.

#### Gym library: authored, not imported
`data/knowledge_base/gym_exercises.json` is **generated** by
`scripts/build_gym_library.py` from the curated spec in `scripts/gym_library/`
(173 movements). Never hand-edit the JSON — `--check` and a test enforce that it
matches the spec. `scripts/seed_gym_exercises.py` is a retired stub that refuses
to run: it re-derived `category`, `level` and `mechanic` from substring matches
on exercise names, and 23% of its rows contradicted their own upstream source.

The library states what the engine used to infer from names — `role`, `mechanic`,
`family`, `load_class`, `impact`, `skill_floor`, `movement_pattern`, `bucket`,
`rep_style`, `canonical`, `coaching_cue`. `role` is the important one: only
`main`/`accessory` may fill a working slot, which is what stops a stretch being
prescribed as a set of eight. Upstream (`data/sources/free_exercise_db.json`) is
a **muscle-list source only**. All instruction prose is authored in
`scripts/gym_library/prose.py`: 89 of the 120 entries that reused upstream text
carried a defect, including a dumbbell exercise whose steps told you to pick up a
barbell and two that instructed holding your breath under load. Contraindications,
pregnancy and dosha are authored per movement in `scripts/gym_library/clinical.py`,
each with a stated mechanism — they differ from the old derived rules on 89 of 173.

#### Diet library: authored, not derived
`data/knowledge_base/diet_foods.json` is **generated** by
`scripts/build_diet_library.py` from the curated spec in `scripts/diet_library/`
(150 foods). Never hand-edit the JSON — `--check` and a test enforce that it
matches the spec. `scripts/seed_diet_foods.py` is a retired stub that refuses to
run: it produced the entire Ayurvedic layer from a ten-row table of category
defaults plus substring matches on the food's id, and its values differ from the
authored ones on 83 of 150 rows for rasa, 46 for vipaka, 42 for virya, 134 for
dosha effect, 128 for nutrition and all 150 for ritu.

What the generator could not express is why the spec exists: it emitted six rasa
combinations for 150 foods, `season_suitable: ["all"]` on every row (so the
Ritucharya scoring in `diet_plan_engine` had nothing to score against), no `guna`
axis at all — while `diet_llm_generator`'s prompt requires every meal to cite it,
so the model invented it — and **no sour vipaka at all**, which is unreachable in
its category table and wrong for every sour food. `prep_state` is part of a food's
identity, not a note: Ardraka and Shunthi are `ginger_fresh` and `ginger_dry`,
two rows with opposite virya, not one `ginger`. A row that departs from the rasa
rule must state a `prabhava` giving the reason, or `schema.validate` refuses it.

Rows are `reviewed: false` — authored, **not clinically reviewed**. They belong in
the Vaidya packet alongside the gym and Panchakarma flags.

#### Diet: the floor for diseases outside the vocabulary
`ahara_safety.classify_condition_apathya_llm` covers what the 38-condition vocabulary
does not. Run on six real rare diseases it returned **zero** entries: the whole batch
shared a 700-token budget, six conditions truncated the JSON mid-object, and the parse
failure zeroed all of them. Worse, the failure was cached as a negative — so one bad
request meant a permanent absence of a floor for every condition in that batch, for
the life of the process. A negative is now cached only when the model actually
answered; a transport or parse error is not evidence about a disease.

Classifier terms are held to the same rules as the authored tables: no behaviour words
(Apathya in the sources is a regimen, so the model returns "day sleep" when asked for
foods) and nothing contentless (`tea` is the form half of Ayurvedic medicine takes,
`water` is in every drink recipe, `oil` is in every tadka, `salt` is in every savoury
meal — `sugar` stays, because a recipe mentions salt by default and sugar only when it
is there). Staples are **not** rejected: `wheat` is the whole point of a celiac floor.

`conditions_without_food_floor` names what could not be covered, and `DietView` shows
a partial all-clear off it. Silence there read as "checked and clear", which is the
opposite of what had happened.

#### Diet arc: the four-week progression is chosen, not fixed
`services/diet_plan_arc.py` picks the sequence from the patient's Ama, Bala, Ojas and
build. It used to be four literals in the prompt — Ama Pachana, Agni Deepana,
Brimhana, Rasayana — for every patient the app has ever had, computed *after* the
profile and reading none of it.

Two ways that was wrong rather than merely unpersonalised. Charaka Sutrasthana 23
names Prameha, Medoroga and Kushtha as the diseases of over-nourishment, and week 3
handed exactly those patients a Brimhana week of ghee, nuts and root vegetables. And
week 1 handed a depleted patient a clearing week — the model noticed and wrote it into
the plan: *"Although Ama is reported as absent, this first week keeps meals light…"*.

Five arcs: Garbhini Paricharya (pregnancy, nourishing throughout),
Brimhana-pradhana (depleted), Langhana-pradhana (Santarpana-caused disease or heavy
build), Deepana-pradhana (depleted **and** Ama-laden — the Ama is burned by kindling
Agni, not by reducing a patient with no Bala to spend), and Samatva. Rasayana is only
scheduled where the weeks before it can clear what was there at the start, since
Rasayana on an Ama-laden Srotas feeds the Ama.

**Low Ojas is not depletion in a heavy patient.** Ojas Kshaya is ordinary in Medoroga
— the Srotas are obstructed, not empty — and reading it as depletion sent an obese
diabetic down the Brimhana arc, which is the error this module exists to prevent.

`withheld` names a phase the patient must *not* be given, with its reason, so the
absence is legible in the prompt and in `DietView` rather than looking like an
oversight. Phase labels on the returned plan are stamped from the arc: the arc is the
app's prescription, not the model's echo.

Related: nothing checked that the model returned four weeks — only that the `weeks`
key existed — and it drops one now and then, shipping a one-week "4-week plan" into a
UI that renders four tabs. A short or misnumbered response is now a failed generation
and falls back to the rule engine.

#### Diet conditions: every recognised disease has a rule, and one table names it
`engine/condition_vocab` accepts 38 canonical conditions. **21 had no dietary rule of
any kind** — no `PATHYA_APATHYA_HINTS` entry, no `_CONDITION_APATHYA_TERMS` entry, no
library claim — so the brief said "use your classical Ayurvedic knowledge" and the
deterministic floor was whatever `classify_condition_apathya_llm` invented. Gout and
kidney stones were among them. All 21 are now authored in both tables and carried in
`data/golden/vaidya_diet_condition_protocols.csv` (packet tier 7) — authored, **not
clinically reviewed**, like the library rows.

Scan terms hold only concrete food words. The Apathya prose beside them names
behaviours ("sleeping during the day", "holding the urge to urinate") and deriving
terms from that phrasing is how a scan ends up searching meals for `sitting`. Terms
broad enough to match a prescribed food are out for the same reason: `salt` is in
every meal and `tea` is the form half these conditions' medicines take, so the
entries say `extra salt` and `black tea`. Two conditions have no classical Nidana and
say so via `modern_extrapolated` rather than citing a chapter that does not describe
them. Hyperthyroidism is authored as the **mirror** of hypothyroidism, not a copy —
the brassicas restricted in one are Pathya in the other — and hypotension is the one
entry here that does not restrict salt.

**There is one canonical-condition table**, `ahara_safety._COND_CANON`;
`diet_brief_builder.COND_ALIASES` and `normalize_condition_key` delegate to it. There
were two, disagreeing on 22 inputs, and that was not cosmetic: `uncurated_conditions()`
skips the LLM classifier whenever the *brief* recognises a condition, so anything the
brief canonicalised and the scan did not got the curated floor from neither table and
the classifier from neither path — `piles`, `iron_deficiency`, `ulcerative_colitis`,
`rheumatoid` and five others sat there. It is the same hole PR #62 closed between
these two tables, reopened by a second alias map nobody thought of as one. Chains
resolve inside the table so one lookup is always enough.

#### Diet conditions: the library's claims gate the primary path
`services/diet_condition_foods.py` turns `diet_foods.json`'s 370 authored
(condition, food) Apathya claims and 338 Pathya claims into two things the
LLM-primary path can use — named foods in the brief, and scan terms in
`apply_condition_food_safety`. Before it, `apathya_for` gated only
`diet_plan_engine` (the **fallback**) and `pathya_for` gated nothing: 333 of the 370
exclusions were unenforced on the path every user gets, so **the fallback was
clinically stricter than the primary path**. An acidity patient could be served green
tea, lemon water, curd and dry ginger, all authored Apathya for acidity.

The curated `_CONDITION_APATHYA_TERMS` is **not** replaced — the two tables were
authored separately and each names foods the other does not, so the floor is their
union.

**Deriving a scan term from a food name is where this goes wrong.** A term is used
for a condition only when every library food it matches agrees about that condition.
That is what keeps `banana`/`raw_banana` and `ginger_fresh`/`ginger_dry` apart, and
what stops the same-food-entered-twice rows (`kidney_beans`/`rajma`,
`chana_dal`/`chhole`, `lentils_brown`/`masoor_dal` — all disagreeing clinically)
speaking for a condition their own rows cannot agree on. A parenthetical is usually
the English translation, but `Tofu (Firm)` is a variant, so modifier-only surfaces
are dropped — "firm" fired on a hypothyroid patient for a word describing texture.

Where the *curated* table is prep-state blind, the fix is an `exempt` list on the
entry, not a narrowed term: a meal that just says "banana" is usually the ripe one,
so the term still fires and the permitted sibling is let through by name.

As with energy, the lever that works is the **brief** — naming the Apathya foods
before generation took a 3-condition plan from 20 post-hoc alerts to 8, and an
acidity+piles plan (65 Apathya foods) to 2, with variety holding at 28/28 distinct
meals.

#### Diet energy: the target is computed, and the plan is checked against it
`services/diet_energy.py` is the diet path's nutrition arithmetic, and
`services/diet_portion_reconciler.py` verifies the generated plan delivers it. Before
these, `target_calories` was `1800 if female else 2000` nudged by BMI category and
goal — it read neither height, weight nor activity level — and nothing compared the
stated target with what came back: measured plans ran at 585-720 kcal against a stated
1200, and 1240-1410 against a stated 2400 for an *underweight* patient.
`engine/calorie_calculator.py`, a documented Tier-1 engine, was called only by its own
unit test and is now the BMR/TDEE source.

A deficit is floored at the larger of the sex floor and the patient's own BMR;
underweight and pregnancy override a stated weight-loss goal; the combined surplus is
bounded. The brief carries a **per-meal** kcal budget, which is what actually moved
delivery into band — the reconciler is the backstop, scaling `macros_approx` **and the
portion text together** (raising one without the other produces a plan that lies to
the person cooking it). Fasting days are exempt: Upavasa is the therapy, not a miss.

#### Diet inputs: one list per declaration, built in one place
Two helpers in `diet_brief_builder` are the only way the diet path builds a list of
what the patient declared, and the brief, the RAG query, the arc, the rule engine and
every scan take it from them:

* `diet_conditions(profile, prefs)` — `medical_history` **plus the diet form's own
  `gut_health_issue`**. Its four values are diseases, and three of them (acidity,
  constipation, ibs) were already canonical keys with a hint block, a scan floor and
  authored library claims. None of it reached them: the answer was rendered as the
  line `GUT HEALTH: Acidity` and went nowhere else. Same patient, same disease —
  declared on the diet form, brief 1,812 chars and 0 Apathya foods named; declared in
  `medical_history`, 3,789 and 50. `bloating` (Adhmana) is authored in both tables
  rather than aliased onto IBS or constipation: Vata obstructed by Ama in the
  Pakvashaya takes the Vatala foods, not IBS's sour-and-raw list. `rajma` and `chana`
  are named individually because moong is this condition's Pathya.
* `diet_allergies(profile, prefs)` — the diet form's `food_allergies` **union**
  `profile["allergies"]`. An allergy is the one declaration where asking twice and
  honouring one answer is not acceptable.

`profile["allergies"]` was `null` for every user in production and no screen collected
it, while `condition_filter.filter_by_allergies`, the chat agent's system prompt and
the Vaidya PDF export all read it. It is collected in onboarding now, in the same
vocabulary as the diet form, and `filter_by_allergies` expands each key through
`ALLERGEN_TERMS` — its substring matching could not see through a canonical key at
all (`"nuts_tree" in "tree nuts"` is False in both directions), so a declared tree-nut
allergy matched an almond by no route.

**Counting trap:** `{"allergies": {"$ne": []}}` matches nulls, and said 11 of 12 users
had declared one. With `$size` it is zero.

#### Diet: the advisory prose is held to the same floor as the meals
The three scans read five consumed slots. A plan also ships six free-text surfaces
that recommend food *by name* and `DietView` renders all of them —
`pathya_apathya.pathya` under the heading "Pathya — Recommended" above the rest. For
an acidity patient, `curd` in a meal raised an alert and set `condition_food_safe =
False`; the same word in the card passed untouched, beside green tea and lemon water.

`apply_advisory_safety` closes it, with two different remedies because the surfaces
differ. A `pathya` entry is a recommendation by construction, so a contradicted one is
**withheld** into `withheld_recommendations` and shown as withheld. Free prose is
mixed — "avoid curd and sour fruit" is correct advice for exactly the patient whose
terms match it — so it is flagged, and only where the food is not already governed by
an avoid-word **in its own clause**. Flagging correct advice is how a safety badge
gets trained out of a reader. `pathya_apathya.apathya` is never scanned: it exists to
name these foods.

The clause, not the prefix, is the unit: scanning only the text *before* the mention
made the answer depend on where the word fell, clearing "curd is best avoided" and
flagging "fresh curd is best avoided". What keeps that from clearing a genuine
recommendation is the splitter — a comma before an avoid-word is a clause boundary,
so "curd is excellent, avoid pickles" is two clauses.

`_active_condition_protocols` is shared by the meal scan and the prose scan rather
than copied. A second copy of that assembly is how the curated and library tables came
to disagree, and how the daily drink came to be in none of the three scans.

#### Diet: vegetarian and vegan only, because that is what the library holds
All 150 authored rows of `diet_foods.json` are vegetarian — no egg, fish or meat. The
form offered five dietary types. For the three with no data behind them the 708
authored (condition, food) claims said nothing, so a non-vegetarian patient's meals
were screened against the curated table alone; the rule engine answered a
`non_vegetarian` + `muscle_support` patient with black beans and edamame; and
`_DIET_TYPE_FORBIDDEN` had no `non_vegetarian` entry, so the scan reported
`dietary_type_safe = True`.

`DIETARY_TYPES` is `{vegetarian, vegan}`. The three withdrawn values are **coerced,
never rejected** — a stored preference that 422s is a user who cannot regenerate their
plan — and an unrecognised value now takes the vegetarian floor rather than an
all-clear, because it no longer means "nothing to check". `test_the_library_holds_no_
animal_food` fails if an animal row is ever authored, so reopening those types is a
decision someone makes on purpose.

#### Diet energy: `activity_level` is asked, not assumed
`Onboarding.jsx` sent `activity_level: 'moderate'` as a literal for every user it ever
created, and 9 of 12 in production had no value at all — while it is the largest
single lever in the plan: same body, same goal, **2040 kcal** at `sedentary` and
**3220** at `very_active`. The hardcoded value was the middle one, so the error was
silent in both directions. Onboarding asks for it now ("how active", which is a
different question from `fitness_level`, which it already asked and the diet path does
not read), and `test_onboarding_collects_every_activity_level_the_engine_scores`
parses the JSX to hold the offered answers and `ACTIVITY_MULTIPLIERS` in step — the
same front/back gap `test_dosha_instrument` exists to close.

`services.diet_llm_generator.build_diet_plan` is the single diet entry point — LLM
primary, rule engine fallback, same safety and energy layers on both. It exists
because the per-feature route and the holistic worker each held a copy of that
sequence and had drifted: the holistic fallback ran only `apply_ahara_safety`, so
which endpoint a user came through decided how much of the safety model applied.

`routes/plans._generate_feature_via_engine` is the single entry point both the holistic and per-feature paths use — it runs the engine + enricher and applies pregnancy/safety gating. The per-feature endpoints (`POST /api/plans/{gym,yoga,diet,routine,panchakarma,remedies,medicines}`) return the plan **synchronously**. The holistic `POST /api/plans/generate` is offloaded to an **ARQ background worker** (`server/worker.py`) via Redis and returns a `job_id` to poll at `/api/plans/job/{jobId}`; if Redis/ARQ is unavailable it falls back to running the job in-process via FastAPI `BackgroundTasks`.

### Prakriti instrument
The live quiz is **`client/src/pages/DoshaQuiz.jsx`** — 21 constitutional traits, a
`temperature_check` consistency probe, a Manas Prakriti block and a Vikriti symptom
list. `engine/dosha_analyzer._TRAIT_WEIGHTS` weights all 21 (0.7-2.0) and
`_PHYSICAL_TRAITS`/`_MENTAL_TRAITS` split them for body-versus-mind dominance.

The question set and the weights live on opposite sides of the front/back boundary
with no shared schema, so `tests/test_dosha_instrument.py` parses the JSX and holds
them in step: a trait the quiz stops asking contributes nothing silently, and
`_TRAIT_WEIGHTS.get(trait, 1.0)` gives an unweighted one the default. The structural
fix is to serve the instrument from the backend; until then that test is the only
place the two can be compared.

`dosha_profiles.json` used to carry a superseded 20-item set under
`doshaQuizQuestions`, seeded into a `dosha_quiz_questions` collection nothing read.
Its ids differed from the live ones (`skin_type` for `skin`, `body_temperature` for
`temperature`, `learning` for `memory`), so comparing that copy against
`_TRAIT_WEIGHTS` showed 15 weighted axes never asked and 14 asked axes unweighted —
a convincing false positive, entirely an artefact of reading the dead file. It is
removed and the test fails if it returns.

**No public dataset can validate this instrument.** The Prakriti datasets label
records with their own rule-based scoring, not a practitioner's assessment — the
largest says its scoring "may differ from clinical evaluations made by expert
practitioners". Comparing our scorer against theirs compares two rule engines over
two different questionnaires. Clinical accuracy needs a blind Vaidya study, specified
as Part 7 of `data/golden/vaidya_reviewer_packet.md`.

### Chat Agent (`server/ai/agents/health_agent.py`)
The conversational chatbot (`POST /api/chat`, mounted in `main.py`) **is** a LangGraph ReAct agent (`create_react_agent`) with a small tool set (`get_plan_detail`, `set_reminder`, `check_my_medicine_interactions`, `adapt_plan`, `get_health_trend`). This is the *only* place LangGraph is used — the removed 4-agent pipeline noted above was for **plan authoring**, which is now purely engine-backed. Chat may read/adapt plans and trigger side effects but never authors them from free text. LangSmith tracing is enabled when a key is configured.

### LLM Client (`server/ai/llm_client.py`)
Singleton `llm_client` wraps Azure OpenAI (primary) and Google Gemini (fallback) with automatic failover and tenacity retry. Both `generate()` (batch) and `generate_stream()` (SSE) are supported. Metrics are recorded via `core/metrics.py`.

### Frontend State
- **Auth state**: `client/src/providers/AuthContext` — wraps the app, exposes `user` and `loading`
- **Server state**: TanStack Query (React Query v5) with IDB-backed persistence
- **Routing**: React Router v7, lazy-loaded pages, route guards (`PrivateRoute`, `AdminRoute`, `OnboardingRoute`, `PublicRoute`) in `client/src/App.jsx`
- **i18n**: `i18next` + `react-i18next`, config in `client/src/i18n.js`
- **PWA**: `vite-plugin-pwa` with `registerType: 'prompt'`

### Backend Structure
- `server/routes/` — FastAPI routers, one file per domain
- `server/schemas/` — Pydantic v2 request/response models
- `server/services/` — business logic called by routes
- `server/core/` — cross-cutting concerns: rate limiting, daily usage quotas, caching, KB cache, metrics, WebSocket manager, admin token auth

### Abuse & Cost Controls
Two independent layers, because they stop different things:
- **Per-minute rate limiting** (`core/rate_limit.py`, middleware) caps burst. Authenticated requests key on **user id** (decoded from the access cookie); auth routes and anonymous requests key on **IP**. The client IP is read from the *right* of `X-Forwarded-For`, `TRUSTED_PROXY_HOPS` entries in — reading from the left let callers spoof a fresh bucket per request. `client/nginx.conf` must therefore **overwrite** `X-Forwarded-For` with `$remote_addr`, not append to it.
- **Per-user daily quotas** (`core/quota.py`) cap sustained spend, since every plan generation and chat turn is a billed LLM call. Counted in `usage_quota` (MongoDB, TTL-reaped) so they hold across processes. Charged on cache *misses* only, after any non-LLM short-circuit; holistic generation bills `HOLISTIC_QUOTA_COST`. Admins are exempt, and the check fails open if Mongo is unreachable.
- Login has a **per-account lockout** (`LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`) — IP limits alone don't bound a distributed guessing attack on one password.
- `server/database/` — Motor (async MongoDB) and ChromaDB clients
- `server/data/` — JSON knowledge base files ingested into ChromaDB

### Production Notes
`config.py` enforces non-default `SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_TOKEN` when `APP_ENV=production`. `COOKIE_SECURE` and `COOKIE_SAMESITE=strict` are auto-forced in production. The `validate_production_secrets()` method is called at startup.
