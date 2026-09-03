# TrustTest documentation gap analysis

**Docs:** `docs/trusttest` (72 MDX files, 64 in `docs.json` nav)
**Code:** `TrustTest/trusttest` (current package)
**Date:** 2026-09-03

This report compares the public TrustTest documentation against the current Python package. It covers missing features, incorrect APIs, stale pages, and structural issues.

---

## Executive summary

The docs cover the **happy path well**: install, connect an HTTP target, run `run_red_teaming()`, build catalog scenarios, generate functional/RAG tests, and evaluate with the main LLM judges and a few heuristics.

They have **fallen behind the catalog**. The largest gap is prompt injection: the package ships **39 single-turn catalog subcategories**; the docs list **18** and give dedicated pages to only **2**. Several recent attack families (MCP, multimodal/agent ingestion, memory poison, CoT forgery, kidnap-RAG) are invisible to readers.

The second gap is **accuracy**. Several documented class names and import paths do not exist (`CustomEvaluator`, `PostgresKnowledgeBase`, `trusttest.kb`, `trusttest.evaluation_context`). Copied examples will fail.

The third gap is **evaluator coverage**. Signature heuristics (`Virus`, `Spam`, `Phishing`, `XssAttackVector`) and `BiasComparisonEvaluator` exist in code and are used by unsafe-output / bias probes, but have no evaluate-result pages.

**Priority if you only do three things:**

1. Refresh the prompt-injection catalog (add the 22 missing single-turn probes; move payload splitting to multi-turn).
2. Fix broken APIs (`CustomEvaluator*` , knowledge-base class/import names, evaluation context module).
3. Document the Dataset vs Prompt probe pattern and `StaticDatasetProbe` (jailbreaks, model-focus, translation).

---

## What the docs already cover well

These areas match the code closely enough to keep as the baseline:

| Area | Status |
|------|--------|
| Install from private PyPI + most extras | Solid. Missing `language-detection` and `azure`. |
| `HttpTarget` (payload, token, retry, Azure OIDC YAML) | Strongest connect page. |
| Catalog scenario-builder pattern | Content bias, leaks, unsafe outputs, off-topic, agentic, system prompt. |
| `run_red_teaming()` | Tutorial matches `catalog.red_team` params. |
| Functional generation | `DatasetProbe`, `PromptDatasetProbe`, `RAGProbe`, question-type enums. |
| Core LLM judges | Completeness, Correctness, Tone, True/False, URL correctness, RAG poisoning. |
| Core heuristics | BLEU, Equals, Regex, language pair. |
| Custom probe authoring | Dataset / prompt / multi-turn patterns in `creating-custom-probes.mdx`. |
| Persistence | `trusttest.client()`, NeuralTrust + file-system save/load. |

Threat-category **overviews** (content bias, sensitive data leak, system prompt disclosure, input leakage, unsafe outputs, off-topic, agentic behavior) list the right subcategory names. They do not explain the Dataset vs Prompt implementation split (see below).

---

## 1. Critical feature gaps

Features that exist in code, are user-facing, and are missing or nearly missing from docs.

### 1.1 Single-turn prompt injections — 22 probes not in the catalog

Canonical catalog: `trusttest/catalog/prompt_injections/single_turn.py` (`SubCategory`, 39 values).

Documented in `create/threat-detection/prompt-injections/overview.mdx`: 18 class names. Dedicated pages: DAN and Best-of-N only.

**Documented (keep, but most need a real page):**

`AntiGPTProbe`, `DANJailbreakProbe`, `BestOfNJailbreakingProbe`, `RolePlayingExploitsProbe`, `SystemOverrideProbe`, `InstructionalInversionProbe`, `EncodedPayloadProbe`, `EncodingAndCapitalizationProbe`, `SymbolicEncodingProbe`, `ObfuscationAndTokenSmugglingProbe`, `TypoTricksProbe`, `ContextHijackingProbe`, `JsonInjectionProbe`, `AllowedAndDisallowedQuestionsProbe`, `MultiLanguageAttacksProbe`, `SynonymsProbe`, `MultimodalInjectionProbe`

**In the catalog, absent from docs:**

| Class | `SubCategory` slug | Why it matters |
|-------|--------------------|----------------|
| `GrandmaJailbreakProbe` | `grandma-jailbreak` | Common jailbreak family |
| `IndirectProbe` | `indirect` | Indirect / pretext injection |
| `RepeatedTokenDivergenceProbe` | `repeated-token-divergence` | Generation-stress jailbreak |
| `StructuredPayloadProbe` | `structured-payload` | Distinct from JSON injection |
| `TrainingDataReplayProbe` | `training-data-replay` | Training-data extraction |
| `CoTForgeryProbe` | `cot-forgery` | Forged chain-of-thought |
| `AdversarialPoetryProbe` | `adversarial-poetry` | Poetic framing |
| `AdversarialTalesProbe` | `adversarial-tales` | Narrative-frame overrides |
| `PolicyPuppetryProbe` | `policy-puppetry` | Fake policy documents |
| `ManyShotJailbreakProbe` | `many-shot-jailbreak` | Many-shot compliance |
| `MCPToolPoisoningProbe` | `mcp-tool-poisoning` | MCP tool metadata attacks |
| `MCPServerSideSamplingProbe` | `mcp-server-side-sampling` | MCP sampling override |
| `WebIDPICloakingProbe` | `web-idpi-cloaking` | Hidden agent-only page directives |
| `AgenticBrowserOCRInjectionProbe` | `agentic-browser-ocr-injection` | OCR / screenshot command injection |
| `ImageStegoInjectionProbe` | `image-stego-injection` | Hidden image payloads |
| `ConcurrentAudioInjectionProbe` | `concurrent-audio-injection` | Second-channel audio |
| `KidnapRAGProbe` | `kidnap-rag` | Staged malicious RAG docs |
| `PersistentMemoryPoisonProbe` | `persistent-memory-poison` | Standing memory rules |
| `AdaptiveMultiturnTranscriptProbe` | `adaptive-multiturn-transcript` | Multi-turn attack as pasted transcript |
| `CodingAgentConfigEscalationProbe` | `coding-agent-config-escalation` | Agent config self-rewrite |
| `ICOSemanticShiftProbe` | `ico-semantic-shift` | Semantic-shift jailbreak |
| `SNGuidedDiffusionDLLMProbe` | `sn-guided-diffusion-dllm` | Diffusion / dLLM jailbreak |

These are the highest-value missing pages. MCP, multimodal/agent ingestion, memory poison, and kidnap-RAG are the ones most likely to surprise customers who only read the docs.

### 1.2 Multi-turn: `PayloadSplittingProbe` is misplaced

Code (`catalog/prompt_injections/multi_turn.py`):

- `CrescendoAttackProbe`
- `EchoChamberAttackProbe`
- `MultiTurnManipulationProbe`
- `PayloadSplittingProbe` (`SubCategory.PAYLOAD_SPLITTING`) — requires `ConversationTarget`

Docs list payload splitting under **single-turn structural attacks** and omit it from the multi-turn section. The single-turn catalog does **not** include it.

### 1.3 Dataset vs Prompt probes (threat categories)

Almost every threat category ships **two implementations** per subcategory:

- `*DatasetProbe` — bundled YAML objectives (`trusttest/datasets/static_objectives/`)
- `*PromptProbe` — LLM-generated attacks

Example: `HateDatasetProbe` / `HatePromptProbe`, `DirectRequestDatasetProbe` / `DirectRequestPromptProbe`, `ToolMisuseSimulationDatasetProbe` / `ToolMisuseSimulationPromptProbe`.

Category pages show one `*ScenarioBuilder` example and never mention:

- That each subcategory has static + generated variants
- How the builder chooses between them
- When to instantiate a `*DatasetProbe` vs `*PromptProbe` directly
- Shared params: `num_test_cases`, `sampling`, `use_jailbreaks`, `translate_into_language`

Content bias is the only place that hints at this (objective builder vs dataset builder). Other category pages do not.

### 1.4 `StaticDatasetProbe`, jailbreaks, and model-focus

`trusttest.probes.static_dataset.StaticDatasetProbe` is the shared engine behind many catalog dataset probes. User-facing params:

- `categories`, `max_objectives_per_category`, `sampling`
- `use_jailbreaks`, `max_jailbreak_per_objective`
- `model_focus` (`ModelFocusCompany`: OpenAI, Anthropic, Google, Meta, …)
- `translate_into_language`

The package ships ~90 generic jailbreak YAMLs plus vendor-specific templates under `datasets/static_jailbreaks/model_focus/`.

**None of this is documented.** The “From Dataset” prompt-injection page talks about user YAML/JSON/Parquet via `DatasetProbe`, not the bundled static-objective + jailbreak wrapper system.

### 1.5 Evaluators missing from Evaluate results

**Heuristics in code, not in docs:**

| Class | Used by | Notes |
|-------|---------|-------|
| `BiasComparisonEvaluator` | Cognitive / stereotypical bias probes | Paired Q&A consistency |
| `VirusEvaluator` | `VirusProbe` | EICAR signature in output |
| `SpamEvaluator` | `SpamProbe` | GTUBE signature |
| `PhishingEvaluator` | `PhishingProbe` | GTphish signature |
| `XssAttackVectorEvaluator` | `XssAttackVectorProbe` | XSS / exfil patterns |

Unsafe-output docs describe Phishing / Spam / Virus / XSS as probes that “test if the model generates” those things. They do not say evaluation is **signature-based**, not an LLM judge.

**LLM judges:**

| Class | Docs status |
|-------|-------------|
| `AnswerRelevanceEvaluator` | Used in RAG examples; **no evaluate-result page**; missing from LLM-judge overview |
| `RAGPoisoningEvaluator` | Has a page; **missing from LLM-judge overview list** |
| `CustomEvaluatorExpected` | Not documented (see §2) |
| `CustomEvaluatorObjective` | Not documented (see §2) |

### 1.6 Config, providers, and install extras

**Config (`trusttest.config`):**

| Feature | Docs |
|---------|------|
| `set_config({evaluator, question_generator, embeddings, topic_summarizer})` | Documented |
| `translation` task (used by `StaticDatasetProbe` translation) | **Missing** |
| Auto-load `.trusttest_config.json` / `trusttest_config.json` from CWD | **Missing** |
| `load_config()`, `get_config()`, `TrustTestConfigError` | **Missing** |
| `retry_config` / `extra_args` on LLM config | **Missing** |
| Default models (`gpt-4o-mini`, `text-embedding-3-small`) | **Missing** |

**LLM providers in `get_llm_client`:** `openai`, `azure`, `google`, `anthropic`, `ollama`, `vllm`, `groq`, `deepseek`, `http`.

Docs omit **`groq`** and **`http`** (`HTTPClient` — judge/generator against an arbitrary HTTP endpoint, with `url`, `payload_config`, `concatenate_field`).

**Embeddings:** Azure is supported (`get_embeddings_model(provider="azure")`) but missing from the embeddings provider list in `connect/llms.mdx`.

**Install extras in `pyproject.toml` not in installation docs:**

- `trusttest[language-detection]` — FastText detector (language evaluators default to this)
- `trusttest[azure]` — Azure identity / OpenAI Azure client (separate from `rag-azure`)

### 1.7 Persistence client features

Documented: save/load scenario, test set, run, evaluator.

**Not documented** (`NeuralTrustClient`):

- `run_evaluation_scenario` / `run_evaluation_scenario_test_case` (remote execution)
- `get_evaluation_scenario_run_metrics`, `get_evaluation_run_status`, `get_evaluation_test_set_status`
- `get_target_total_metrics`

**Not documented** (`FileSystemClient`):

- `get_overview()` → `RedTeamingOverview` (local red-team rollup by language / category / framework)

### 1.8 Compliance frameworks on catalog scenarios

Each catalog builder attaches framework metadata (EU AI Act, OWASP AITG / LLM Top 10, MITRE ATLAS, ISO/IEC 42001). This is how `run_scenarios` / `FileSystemClient.get_overview()` group results.

Docs never mention framework tags. The “compliance” tutorial only runs unsafe outputs + DAN — it does not explain the mapping.

### 1.9 Other user-facing APIs with little or no coverage

| Feature | Location | Docs |
|---------|----------|------|
| `RagContextBuilder` | `dataset_builder` | Missing — generates gold `expected_response` from retrieved docs |
| `HarmbenchDatasetProbe` | `probes/harmbench.py` | Missing (implemented; not in `probes.__all__` or catalog) |
| `ConversationTarget` / `create_conversation_context` | `targets` | Custom-target page only; multi-turn pages assume `HttpTarget` |
| Language detection API | `language_detection` | Language evaluator page cites `langdetect`; code uses `LanguageDetector` + FastText |
| Per-task LLM client injection | probe / evaluator `llm_client=` | Mentioned on a few probe pages; not as a global pattern |
| `FailCriteriaType.percentage_fail` | `evaluator_suite` | Named; no threshold example |

`MaliciousCodeDatasetProbe` exists with YAML but is **not exported** from `trusttest.probes` or the unsafe-outputs catalog. Do not document as public until it is exported.

---

## 2. Incorrect or stale documentation

These will break copy-paste or teach the wrong mental model.

### 2.1 Custom evaluator class does not exist

| Docs say | Code has |
|----------|----------|
| `from trusttest.evaluators import CustomEvaluator` | `CustomEvaluatorExpected`, `CustomEvaluatorObjective` |

Affected: `getting-started/tutorials/custom-llm-judge.mdx` (the canonical custom-judge guide). `evaluate-result/llm-as-a-judge/custom.mdx` is an empty stub and is **not in the nav**.

### 2.2 Knowledge-base class and import drift

| Page | Documented | Actual |
|------|------------|--------|
| `knowledge-base/overview.mdx` | `PostgresKnowledgeBase` | `PgVectorKnowledgeBase` |
| `connectors/postgres.mdx` | `from trusttest.kb import PostgresKnowledgeBase` | `from trusttest.knowledge_base.pgvector import PgVectorKnowledgeBase` — there is no `trusttest.kb` |
| `connectors/postgres.mdx` | `EmbeddingsOpenAi(api="openai", …)` + `POSTGRES_*` host/user/db fields | Constructor is `connection_string`, `table_name`, `fields_mapping`; embeddings via `get_embeddings_model` or `EmbeddingsOpenAi` from `trusttest.embeddings` |
| `functional/from-rag.mdx` | `from trusttest.knowledge_base import AzureSearchKnowledgeBase` | Class is `AzureKnowledgeBase`; **not** re-exported from `knowledge_base.__init__` |
| `functional/from-rag.mdx` | `from trusttest.knowledge_base import PgVectorKnowledgeBase` | Class name is correct; import must be `trusttest.knowledge_base.pgvector` |
| `connectors/azure.mdx` | `AzureKnowledgeBase(..., key=...)` | Constructor takes `credentials: TokenCredential \| AzureKeyCredential`, not `key=` |
| `knowledge-base/overview.mdx` | Lists Azure, Neo4j, Postgres, InMemory | **Omits Upstash** (page exists under connectors) |

`knowledge_base.__init__` only exports `KnowledgeBase`, `InMemoryKnowledgeBase`, `Document`. Connector pages should use submodule imports.

### 2.3 Evaluation context module name

`evaluate-result/evaluation-strategy.mdx` imports `trusttest.evaluation_context` (singular). The module is `trusttest.evaluation_contexts` (plural). Other pages already use the correct name.

The page also omits `BiasComparisonContext`, which bias probes require.

### 2.4 Language detection

`evaluate-result/heuristics/language.mdx` says evaluators use **`langdetect`**. Implementation defaults to `FastTextLanguageDetector` (`trusttest[language-detection]`). Parameter is `expected_languages` (plural), not a single `expected_language`.

### 2.5 HTTP placeholder inconsistency

| Page | Placeholder |
|------|-------------|
| `connect/http.mdx` basic example | `{{ message }}` |
| Same page, later + most create pages | `{{ test }}` (this is the real default `message_regex`) |
| `getting-started/tutorials/http-model.mdx` | `{{ message }}` |

Pick one canonical placeholder (`{{ test }}`) and use it everywhere.

### 2.6 Payload splitting taxonomy

See §1.2. Listing it as a single-turn probe is wrong.

### 2.7 Iterate / Capture-the-Flag naming

`getting-started/tutorials/iterate.mdx` and orphan `create/iterate.mdx` title a **Crescendo** run as “Capture the Flag” / “Iterate Scenario”. There is no `iterate` module. This confuses Crescendo with a separate product feature.

### 2.8 Azure / pgvector extra names in code vs docs

Docs extras (`rag-azure`, `rag-postgres`) match `pyproject.toml`. Some library `ImportError` strings still say `trusttest[azure]` / `trusttest[rag-pgvector]`. Docs are right; worth aligning the code messages so users are not sent to a non-existent extra.

### 2.9 Small copy / example bugs

- `getting-started/tutorials/local-llm.mdx`: `target_target` typo.
- `getting-started/tutorials/http-model.mdx`: `ErrorHandelingConfig` typo (code: `ErrorHandlingConfig` / `error_config`).
- `core-concepts/overview.mdx`: “EvaluatorScenarios” (should be `EvaluationScenario` + `EvaluatorSuite`).
- LLM client install snippets in `connect/llms.mdx` are wrapped in ` ```python ` instead of ` ```shell `.

---

## 3. Incomplete coverage (listed, not explained)

These appear in tables but a reader cannot actually use them from the docs alone.

### Prompt injections

Only DAN and Best-of-N have constructor params, objectives, and a full example. The other 16 listed single-turn probes are name-only. Multimodal injection is listed with no image / technique params (`injection_techniques` exists on the class).

Echo Chamber’s `SteeringObjective` / `steering_keywords` appear on the orphan `create/echo-chamber.mdx`, not on the canonical multi-turn page.

### Threat-category pages

Each page has purpose + subcategory table + one builder snippet. Missing:

- Dataset vs Prompt split
- Default evaluator (`TrueFalseEvaluator` for most catalog runs)
- `language`, `objectives`, `max_turns` (multi-turn)
- How `run_scenarios()` differs from `builder.get_scenario()`
- Framework tags

### RAG / automatic generation

`create/automatic-test-generation.mdx` is the best question-type reference (`BenignQuestion`, `MaliciousQuestion`). Still missing:

- `RagContextBuilder`
- Topic clustering params (UMAP / HDBSCAN) as user-tunable (overview describes the pipeline as Azure-only)
- Language detection on ingested documents
- That vector KBs need `set_config` embeddings + `topic_summarizer`

### Connect

- Custom target page is adequate for `Target` / `ConversationTarget`.
- No guide for using `HTTPClient` as the **judge/generator** (distinct from `HttpTarget` as the SUT).
- No Azure OpenAI embeddings walkthrough.

---

## 4. Information architecture

### Orphan MDX (on disk, not in `docs.json`)

Likely still reachable by URL; several contradict the canonical pages.

| File | Problem |
|------|---------|
| `create/overview.mdx` | Legacy stub; superseded by `threat-detection/overview.mdx` |
| `create/prompt-injections.mdx` | Shorter duplicate of the PI overview |
| `create/crescendo.mdx` | Uses `MultiTurnScenarioBuilder`; canonical is `…/multi-turn/crescendo.mdx` |
| `create/echo-chamber.mdx` | Has `SteeringObjective` detail missing from the canonical page |
| `create/iterate.mdx` | Duplicate of the iterate tutorial; CTF misnomer |
| `create/prompt-dataset.mdx` | Duplicate of `functional/from-prompt.mdx` |
| `create/dataset.mdx` | Duplicate of `functional/from-dataset.mdx` |
| `evaluate-result/llm-as-a-judge/custom.mdx` | Empty stub |

**Action:** delete or redirect orphans; harvest Echo Chamber `SteeringObjective` into the canonical page first.

### Stubs and thin pages

- `evaluate-result/llm-as-a-judge/custom.mdx` — empty
- `core-concepts/overview.mdx` — glossary only; typos
- KB connector pages (in-memory, azure, neo4j, upstash) — no frontmatter title/description
- `evaluate-result/overview.mdx` — does not list current evaluator inventory

### No API reference

Unlike TrustGate, TrustTest has no symbol index. With 100+ probe classes and submodule-only imports (`trusttest.__init__` exports only `client` and `set_config`), a compact “import cheat sheet” would remove a lot of guesswork.

---

## 5. Recommended doc work (ordered)

### P0 — correctness (broken examples)

1. Replace `CustomEvaluator` with `CustomEvaluatorExpected` / `CustomEvaluatorObjective`; add the custom judge page to the nav (or fold the tutorial into it).
2. Fix KB names and imports (`PgVectorKnowledgeBase`, `AzureKnowledgeBase`, no `trusttest.kb`).
3. Fix `trusttest.evaluation_contexts` imports; add `BiasComparisonContext`.
4. Standardize `HttpTarget` placeholder to `{{ test }}`.
5. Move payload splitting to multi-turn; remove it from the single-turn table.

### P1 — catalog completeness (the real product gap)

6. Expand the single-turn overview table to all **39** `SubCategory` values with class names.
7. Add short pages (or one grouped page per family) for the 22 missing probes, starting with:
   - MCP (`MCPToolPoisoning`, `MCPServerSideSampling`)
   - Agentic ingestion (`AgenticBrowserOCRInjection`, `ImageStegoInjection`, `ConcurrentAudioInjection`, `WebIDPICloaking`)
   - Memory / RAG (`PersistentMemoryPoison`, `KidnapRAG`, `AdaptiveMultiturnTranscript`)
   - Modern jailbreaks (`CoTForgery`, `PolicyPuppetry`, `ManyShotJailbreak`, `AdversarialPoetry` / `AdversarialTales`)
8. Document `StaticDatasetProbe`: bundled objectives, `use_jailbreaks`, `model_focus`, translation.
9. On every threat-category page, explain Dataset vs Prompt probes.

### P2 — evaluators and config

10. Pages (or one “signature evaluators” page) for Virus / Spam / Phishing / XSS heuristics.
11. Page for `BiasComparisonEvaluator`.
12. Page for `AnswerRelevanceEvaluator`; add it and RAG poisoning to the LLM-judge overview.
13. Document `translation`, config-file auto-discovery, `groq` + `http` LLM providers, Azure embeddings, `language-detection` extra.

### P3 — cleanup and depth

14. Remove or redirect the 8 orphan files.
15. Rename iterate/CTF tutorial to Crescendo / multi-turn red teaming.
16. Document NeuralTrust remote run + metrics APIs and `FileSystemClient.get_overview()`.
17. Document catalog framework tags (EU AI Act, OWASP, MITRE ATLAS).
18. Add an import / public-API cheat sheet (root exports only `client` and `set_config`).
19. Document `RagContextBuilder` next to RAG generation.
20. Fix typos (`target_target`, `ErrorHandelingConfig`, `EvaluatorScenarios`).

---

## 6. Side-by-side inventory

### Prompt injection catalog

| | Docs | Code |
|--|------|------|
| Single-turn subcategories | 18 listed | **39** |
| Dedicated single-turn pages | 2 (DAN, Best-of-N) | — |
| Multi-turn probes | 3 | **4** (adds payload splitting) |

### Evaluators

| Family | Docs pages | Public classes |
|--------|------------|----------------|
| LLM judges | 6 + stub custom | 9 (`AnswerRelevance`, two Custom* types) |
| Heuristics | 4 | 10 (adds BiasComparison + 4 signatures) |

### Knowledge bases

| Docs name | Code class | Import |
|-----------|------------|--------|
| `InMemoryKnowledgeBase` | same | `trusttest.knowledge_base` |
| `AzureKnowledgeBase` / `AzureSearchKnowledgeBase` | `AzureKnowledgeBase` | `trusttest.knowledge_base.azure_search` |
| `Neo4jKnowledgeBase` | same | `trusttest.knowledge_base.neo4j` |
| `PostgresKnowledgeBase` | `PgVectorKnowledgeBase` | `trusttest.knowledge_base.pgvector` |
| `UpstashKnowledgeBase` | same | `trusttest.knowledge_base.upstash` |

### Install extras

Documented: `google`, `openai`, `deepseek`, `anthropic`, `ollama`, `vllm`, `rag-azure`, `rag-upstash`, `rag-neo4j`, `rag-postgres`.

Missing: `language-detection`, `azure`.

### Root package exports

Only `trusttest.client` and `trusttest.set_config`. Everything else is a submodule import. Docs mix styles (`from trusttest.probes import DatasetProbe` vs `from trusttest.probes.dataset import DatasetProbe`) without stating the rule.

---

## 7. Out of scope / do not document yet

- `MaliciousCodeDatasetProbe` — present on disk, not in `probes.__all__` or the unsafe-outputs catalog.
- Internal helpers (`timezone`, logger internals, probe-private prompt generators except as RAG question types).
- There is **no CLI** (`pyproject.toml` has no `[project.scripts]`). Do not invent one.

`HarmbenchDatasetProbe` is usable via submodule import but is not catalog-registered. Document only if product intends it as public.

---

## Appendix — suggested new nav (P1 slice)

Under Prompt Injections → Single Turn, add groups rather than 22 more top-level pages:

- Jailbreaking (existing + Grandma, Indirect, Many-shot, Policy puppetry, CoT forgery, ICO, SN-guided)
- Encoding & obfuscation (existing)
- Structural (JSON, structured payload, context hijack, allowed/disallowed; **drop payload splitting**)
- Language (existing + training-data replay, repeated-token)
- Multimodal & agent surfaces (multimodal, OCR, image stego, audio, web cloaking)
- MCP & agent config (tool poisoning, server-side sampling, coding-agent escalation)
- Memory & RAG (persistent memory, kidnap-RAG, adaptive transcript)

Under Multi Turn, add **Payload splitting**.

Under Heuristic, add **Signature evaluators** and **Bias comparison**.

Under LLM as judge, add **Answer relevance** and replace the custom stub with the real two-class API.
