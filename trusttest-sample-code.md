# TrustTest Sample Code Index

This document catalogs all TrustTest code snippets found in the docs/trusttest documentation, with their source file locations. The documentation uses an older TrustTest API (e.g., `RagPoisoningScenario`, old probe classes, `Scenario`, etc.).

## Corrections Index

| Section | Invalid Sample | Correction |
|---------|----------------|------------|
| upstash.mdx | RagPoisoningScenario | Use RAGProbe + EvaluationScenario + RAGPoisoningEvaluator |
| automatic-test-generation.mdx | RagFunctionalScenario, RagPoisoningScenario | Use RAGProbe + EvaluationScenario |
| tutorials/rag.mdx | RagFunctionalScenario, RagPoisoningScenario | Use RAGProbe + EvaluationScenario |
| quickstart.mdx | Dataset([...]) structure | Use Dataset([[item] for item in items]) for single-turn |
| connect/custom.mdx | trusttest.Scenario | Use EvaluationScenario + DatasetProbe |
| create/functional/from-dataset.mdx | dataset_builder.base, evaluators.llm_judges | Use trusttest.dataset_builder, trusttest.evaluators |
| create/functional/from-prompt.mdx | dataset_builder.single_prompt | Use trusttest.dataset_builder |
| create/dataset.mdx | Dataset([...]) | Use List[List[DatasetItem]] structure |
| create/unsafe-outputs.mdx | UnsafeOutputScenario | Use UnsafeOutputsScenarioBuilder |
| create/knowledge-base/neo4j.mdx | RagFunctionalScenario | Use RAGProbe + EvaluationScenario |
| create/system-prompt-disclosure.mdx | SystemPromptDisclosureScenario | Use SystemPromptDisclosureScenarioBuilder |
| create/echo-chamber.mdx | EchoChamberScenario | Use MultiTurnScenarioBuilder |
| create/agentic-behavior.mdx | AgenticBehaviorScenario | Use AgenticBehaviorLimitsScenarioBuilder |
| create/sensitive-data-leak.mdx | SensitiveDataLeakScenario | Use SensitiveDataLeakScenarioBuilder |
| create/input-leakage.mdx | InputLeakageScenario | Use InputLeakageScenarioBuilder |
| create/content-bias.mdx | ContentBiasScenario | Use ContentBiasObjectiveScenarioBuilder / ContentBiasDatasetScenarioBuilder |
| create/crescendo.mdx | CrescendoScenario | Use MultiTurnScenarioBuilder |
| create/off-topic.mdx | OffTopicScenario | Use OffTopicScenarioBuilder |
| create/prompt-injections.mdx | PromptInjectionScenario | Use SingleTurnScenarioBuilder |
| create/iterate.mdx | CaptureTheFlagScenario | Use MultiTurnScenarioBuilder or probe + EvaluationScenario |
| create/threat-detection/from-dataset.mdx | PromptInjectionScenario | Use SingleTurnScenarioBuilder or DatasetProbe |
| create/functional/from-rag.mdx | (imports OK) | Add test_set = probe.get_test_set() before evaluate |
| create/functional/overview.mdx | FunctionalScenario | Use RAGProbe + EvaluationScenario |
| tutorials/compliance.mdx | ComplianceScenario | No direct equivalent; use combination of scenario builders |

## Current API Quick Reference

**ScenarioBuilder pattern:**
```python
from trusttest.catalog.off_topic import OffTopicScenarioBuilder
from trusttest.catalog.off_topic import SubCategory  # or import from builder module

builder = OffTopicScenarioBuilder(target=target, num_test_cases=20)
scenario = builder.get_scenario(SubCategory.COMPETITORS_CHECK)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
results.display_summary()
```

**RAG testing:**
```python
from trusttest.probes.rag import RAGProbe
from trusttest.probes.rag import BenignQuestion, MaliciousQuestion
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluators import AnswerRelevanceEvaluator, RAGPoisoningEvaluator

probe = RAGProbe(target=target, knowledge_base=kb, num_questions=10, question_types=[BenignQuestion.SIMPLE])
scenario = EvaluationScenario(name="...", evaluator_suite=EvaluatorSuite(evaluators=[...], criteria="any_fail"))
test_set = probe.get_test_set()
results = scenario.evaluate(test_set)
```

**Client:**
```python
import trusttest
client = trusttest.client(type="file-system")  # or type="neuraltrust", token="...")
client.save_evaluation_scenario(scenario)
```

**Dataset structure:** `Dataset` expects `List[List[DatasetItem]]`; each inner list is one test case.

---

## trusttest/create/knowledge-base/connectors/upstash.mdx

```python
import os

from dotenv import load_dotenv

from trusttest.catalog import RagPoisoningScenario
from trusttest.knowledge_base.upstash import UpstashKnowledgeBase
from trusttest.targets.testing import DummyTarget
from trusttest.probes.rag import MaliciousQuestion

load_dotenv(override=True)

# Initialize the knowledge base with your Upstash Vector credentials
knowledge_base = UpstashKnowledgeBase(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
)

# Create and run an adversarial RAG test scenario
rag_test = RagPoisoningScenario(
    model=DummyTarget(),
    knowledge_base=knowledge_base,
    num_questions=10,
    question_types=[MaliciousQuestion.SPECIAL_TOKEN, MaliciousQuestion.HYPOTHETICAL],
)

test_set = rag_test.probe.get_test_set()
results = rag_test.eval.evaluate(test_set)
results.display_summary()
```

**Correction (current API):** `RagPoisoningScenario` does not exist. Use `RAGProbe` + `EvaluationScenario`:
```python
import os
from dotenv import load_dotenv
from trusttest.knowledge_base.upstash import UpstashKnowledgeBase
from trusttest.probes.rag import RAGProbe, MaliciousQuestion
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluators import RAGPoisoningEvaluator
from trusttest.targets.testing import DummyTarget

load_dotenv(override=True)
knowledge_base = UpstashKnowledgeBase(url=os.getenv("UPSTASH_VECTOR_REST_URL"), token=os.getenv("UPSTASH_VECTOR_REST_TOKEN"))
probe = RAGProbe(target=DummyTarget(), knowledge_base=knowledge_base, num_questions=10, question_types=[MaliciousQuestion.SPECIAL_TOKEN, MaliciousQuestion.HYPOTHETICAL])
scenario = EvaluationScenario(name="RAG Poisoning", evaluator_suite=EvaluatorSuite(evaluators=[RAGPoisoningEvaluator()], criteria="any_fail"))
test_set = probe.get_test_set()
results = scenario.evaluate(test_set)
results.display_summary()
```

---

## trusttest/create/automatic-test-generation.mdx

**Functional Testing:**
```python
from trusttest.catalog import RagFunctionalScenario
from trusttest.knowledge_base import Document, InMemoryKnowledgeBase
from trusttest.probes.rag import BenignQuestion

# Configure knowledge base
documents = [
    Document(
        id="1",
        content="Your document content here",
        topic="Your topic here"
    )
]
knowledge_base = InMemoryKnowledgeBase(documents=documents)

# Functional testing with different question types
functional_scenario = RagFunctionalScenario(
    model=your_model,
    knowledge_base=knowledge_base,
    num_questions=10,
    question_types=[
        BenignQuestion.SIMPLE,
        BenignQuestion.COMPLEX,
        BenignQuestion.REALLY_COMPLEX,
        BenignQuestion.CONVERSATIONAL,
        BenignQuestion.DISTRACTING,
        BenignQuestion.DOUBLE,
        BenignQuestion.OOS
    ]
)

# Run evaluation
test_set = functional_scenario.probe.get_test_set()
results = functional_scenario.eval.evaluate(test_set)
results.display()
```

**Correction (current API):** `RagFunctionalScenario` does not exist. Use `RAGProbe` + `EvaluationScenario` + `AnswerRelevanceEvaluator`. Replace `model` with `target`. Import `from trusttest.probes.rag import RAGProbe, BenignQuestion` and build scenario with `EvaluatorSuite(evaluators=[AnswerRelevanceEvaluator()], criteria="any_fail")`.

**Adversarial Testing:**
```python
from trusttest.catalog import RagPoisoningScenario
from trusttest.knowledge_base import Document, InMemoryKnowledgeBase
from trusttest.probes.rag import MaliciousQuestion

# Configure knowledge base
documents = [
    Document(
        id="1",
        content="Your document content here",
        topic="Your topic here"
    )
]
knowledge_base = InMemoryKnowledgeBase(documents=documents)

# Adversarial testing with different attack types
adversarial_scenario = RagPoisoningScenario(
    model=your_model,
    knowledge_base=knowledge_base,
    num_questions=10,
    question_types=[
        MaliciousQuestion.INSTRUCTION_MANIPULATION,
        MaliciousQuestion.ROLE_PLAY,
        MaliciousQuestion.HYPOTHETICAL,
        MaliciousQuestion.STORYTELLING,
        MaliciousQuestion.OBFUSCATION,
        MaliciousQuestion.PAYLOAD_SPLITTING,
        MaliciousQuestion.LIST_BASED,
        MaliciousQuestion.SPECIAL_TOKEN,
        MaliciousQuestion.OFF_TONE
    ]
)

# Run evaluation
test_set = adversarial_scenario.probe.get_test_set()
results = adversarial_scenario.eval.evaluate(test_set)
results.display()
```

**Correction (current API):** `RagPoisoningScenario` does not exist. Use `RAGProbe` + `EvaluationScenario` + `RAGPoisoningEvaluator` (same pattern as upstash correction above).

---

## trusttest/getting-started/tutorials/rag.mdx

**Configure Knowledge Base:**
```python
from trusttest.knowledge_base import Document, InMemoryKnowledgeBase

documents = [
    Document(
        id="1",
        content="...",
        topic="City origins",
    ),
    Document(
        id="2",
        content="...",
        topic="City location",
    ),
]

knowledge_base = InMemoryKnowledgeBase(documents=documents)
```

**Generate Functional Questions:**
```python
from trusttest.catalog import RagFunctionalScenario

knowledge_base = InMemoryKnowledgeBase(documents=documents)

rag_scenario = RagFunctionalScenario(
    target=DummyTarget(),
    knowledge_base=knowledge_base,
    num_questions=2,
    question_types=[BenignQuestion.SIMPLE]
)
```

**Correction (current API):** Replace with `RAGProbe` from `trusttest.probes.rag` + `EvaluationScenario` + `AnswerRelevanceEvaluator`.

**Generate RAG Poisoning Tests:**
```python
rag_scenario = RagPoisoningScenario(
    target=DummyTarget(),
    knowledge_base=knowledge_base,
    num_questions=2,
    question_types=[MaliciousQuestion.SPECIAL_TOKEN]
)
```

**Correction (current API):** Replace with `RAGProbe` + `EvaluationScenario` + `RAGPoisoningEvaluator`.

**Functional tests (complete):**
```python
from dotenv import load_dotenv

from trusttest.catalog import RagFunctionalScenario
from trusttest.knowledge_base import Document, InMemoryKnowledgeBase
from trusttest.targets.testing import DummyTarget
from trusttest.probes.rag import BenignQuestion

load_dotenv(override=True)

# ... documents and knowledge_base ...

rag_test = RagFunctionalScenario(
    target=DummyTarget(),
    knowledge_base=knowledge_base,
    num_questions=2,
    question_types=[BenignQuestion.SIMPLE]
)

test_set = rag_test.probe.get_test_set()
results = rag_test.eval.evaluate(test_set)
results.display()
```

**Correction (current API):** Same as above – use `RAGProbe` + `EvaluationScenario` + `AnswerRelevanceEvaluator` for functional; `RAGPoisoningEvaluator` for adversarial.

**Adversarial tests (complete):**
```python
from trusttest.catalog import RagPoisoningScenario
# ... RagPoisoningScenario, MaliciousQuestion.SPECIAL_TOKEN ...
rag_test = RagPoisoningScenario(...)
test_set = rag_test.probe.get_test_set()
results = rag_test.eval.evaluate(test_set)
results.display()
```

---

## trusttest/getting-started/quickstart.mdx

**Step 1 - Evaluation Target:**
```python
from trusttest.targets.testing import DummyTarget

target = DummyTarget()
response = target.respond("Hello, how are you?")
print(response)
```

**Step 2 - Probe:**
```python
from trusttest.dataset_builder import Dataset, DatasetItem
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.targets.testing import DummyTarget
from trusttest.probes.dataset import DatasetProbe

target = DummyTarget()
probe = DatasetProbe(
    target=target,
    dataset=Dataset([...]),
)
test_set = probe.get_test_set()
```

**Correction (current API):** `Dataset` expects `List[List[DatasetItem]]` – each inner list is one test case. Use `Dataset([[item] for item in items])` for single-turn tests, or `Dataset.from_yaml("path.yaml")`.

**Step 3 - Evaluation Scenario:**
```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluators import BleuEvaluator, ExpectedLanguageEvaluator

scenario = EvaluationScenario(
    name="Quickstart Functional Test",
    description="Functional test example.",
    evaluator_suite=EvaluatorSuite(
        evaluators=[
            BleuEvaluator(threshold=0.3),
            ExpectedLanguageEvaluator(expected_language="en"),
        ],
        criteria="any_fail",
    ),
)
```

**Complete Example:**
```python
from trusttest.dataset_builder import Dataset, DatasetItem
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluators import BleuEvaluator, ExpectedLanguageEvaluator
from trusttest.targets.testing import DummyTarget
from trusttest.probes.dataset import DatasetProbe

target = DummyTarget()
probe = DatasetProbe(...)
test_set = probe.get_test_set()
scenario = EvaluationScenario(...)
results = scenario.evaluate(test_set)
results.display()
results.display_summary()
```

**Correction (current API):** `scenario.evaluate(test_set)` – pass `test_set` from `probe.get_test_set()`. Ensure `EvaluationScenario` has `evaluator_suite` with `EvaluatorSuite(evaluators=[...], criteria="any_fail")`.

---

## trusttest/connect/custom.mdx

**Basic Implementation (uses old `Scenario`):**
```python
from trusttest.targets.base import Target

class DummyTarget(Target):
    async def async_respond(self, message: str) -> Optional[str]:
        return "This is a dummy response to: " + message
```

```python
from trusttest import Scenario

target = DummyTarget()
scenario = Scenario(
    target=target,
    # Add your scenario configuration here
)
results = scenario.run()
```

**Correction (current API):** `Scenario` from `trusttest` does not exist. Use `EvaluationScenario` + `DatasetProbe` (or other probe). Flow: `probe = DatasetProbe(target=target, dataset=dataset)`, `test_set = probe.get_test_set()`, `scenario = EvaluationScenario(evaluator_suite=suite)`, `results = scenario.evaluate(test_set)`.

**Conversation Target:**
```python
from trusttest.targets.base import ConversationTarget

class DummyConversationTarget(ConversationTarget):
    async def async_respond_conversation(
        self, conversation: List[str], **kwargs
    ) -> Optional[str]:
        return f"Responding to conversation with {len(conversation)} messages..."
```

```python
from trusttest import Scenario

scenario = Scenario(
    target=target,
    # Add your scenario configuration here
)
results = scenario.run()
```

**Correction (current API):** Same as above – use `EvaluationScenario` + probe pattern.

---

## trusttest/create/functional/from-dataset.mdx

**Loading from YAML:**
```python
from trusttest.probes.dataset import DatasetProbe
from trusttest.dataset_builder.base import Dataset
from trusttest.targets.http import HttpTarget, PayloadConfig
from trusttest.evaluators.llm_judges import CorrectnessEvaluator
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluation_scenarios import EvaluationScenario

target = HttpTarget(...)
dataset = Dataset.from_yaml("functional_tests.yaml")
probe = DatasetProbe(target=target, dataset=dataset)
test_set = probe.get_test_set()
evaluator = CorrectnessEvaluator()
suite = EvaluatorSuite(evaluators=[evaluator])
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
results.display_summary()
```

**Correction (current API):** Use `from trusttest.dataset_builder import Dataset` (not `dataset_builder.base`). Use `from trusttest.evaluators import CorrectnessEvaluator` (not `evaluators.llm_judges`).

---

## trusttest/create/functional/from-prompt.mdx

**Basic Usage:**
```python
from trusttest.dataset_builder.single_prompt import SinglePromptDatasetBuilder, DatasetItem
from trusttest.probes.dataset import PromptDatasetProbe
from trusttest.evaluation_contexts import ExpectedResponseContext
# ... PromptDatasetProbe, EvaluationScenario ...
probe = PromptDatasetProbe(target=target, dataset_builder=builder)
test_set = probe.get_test_set()
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

**Correction (current API):** Use `from trusttest.dataset_builder import DatasetItem, SinglePromptDatasetBuilder` (not `dataset_builder.single_prompt`). `PromptDatasetProbe` takes `target` and `dataset_builder`.

---

## trusttest/create/dataset.mdx

**From Python List:**
```python
from trusttest.dataset_builder import Dataset, DatasetItem
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.targets.testing import DummyTarget
from trusttest.probes import DatasetProbe

target = DummyTarget()
dataset = Dataset([...])
probe = DatasetProbe(target=target, dataset=dataset)
```

**Correction (current API):** `Dataset([...])` must be `List[List[DatasetItem]]`. For single-turn: `Dataset([[DatasetItem(question="...", context=ExpectedResponseContext(...))]])`. Can also use `Dataset.from_yaml("path.yaml")` or `Dataset.from_json("path.json")`.

---

## trusttest/create/creating-custom-probes.mdx

**Dataset Probe:**
```python
from trusttest.probes.dataset import DatasetProbe
from trusttest.dataset_builder.base import Dataset

dataset = Dataset.from_yaml("my_custom_attacks.yaml")
probe = DatasetProbe(target=target, dataset=dataset)
```

**Correction (current API):** Use `from trusttest.dataset_builder import Dataset` (not `dataset_builder.base`).

**Custom Probe (MyCustomAttackProbe, MyMultiTurnProbe, AuthorityAppealProbe):**
```python
class MyCustomAttackProbe(PromptDatasetProbe[ObjectiveContext]):
    ...

class MyMultiTurnProbe(Probe[Target, ObjectiveContext]):
    ...

class AuthorityAppealProbe(PromptDatasetProbe[ObjectiveContext]):
    ...
```

**Evaluation:**
```python
probe = MyCustomAttackProbe(...)
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

---

## trusttest/create/unsafe-outputs.mdx

```python
from trusttest.catalog import UnsafeOutputScenario
from trusttest.targets.http import HttpTarget, PayloadConfig

target = HttpTarget(...)
scenario = UnsafeOutputScenario(
    target=target,
    sub_category="hate",
    max_attacks=20,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
results.display_summary()
```

**Correction (current API):** `UnsafeOutputScenario` does not exist. Use `UnsafeOutputsScenarioBuilder`:
```python
from trusttest.catalog.unsafe_outputs import UnsafeOutputsScenarioBuilder
from trusttest.catalog.unsafe_outputs import SubCategory  # SubCategory.HATE

builder = UnsafeOutputsScenarioBuilder(target=target, num_test_cases=20)
scenario = builder.get_scenario(SubCategory.HATE)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
results.display_summary()
```

---

## trusttest/create/knowledge-base/connectors/neo4j.mdx

```python
from trusttest.catalog import RagFunctionalScenario
from trusttest.knowledge_base.neo4j import Neo4jKnowledgeBase
from trusttest.targets.testing import DummyTarget

knowledge_base = Neo4jKnowledgeBase(...)
rag_test = RagFunctionalScenario(
    target=DummyTarget(), knowledge_base=knowledge_base, num_questions=2
)
test_set = rag_test.probe.get_test_set()
results = rag_test.eval.evaluate(test_set)
results.display_summary()
```

**Correction (current API):** `RagFunctionalScenario` does not exist. Use `RAGProbe` + `EvaluationScenario` + `AnswerRelevanceEvaluator`. Import `Neo4jKnowledgeBase` from `trusttest.knowledge_base.neo4j`.

---

## trusttest/create/system-prompt-disclosure.mdx

```python
from trusttest.catalog import SystemPromptDisclosureScenario

scenario = SystemPromptDisclosureScenario(
    target=target,
    sub_category="direct-request",
    max_attacks=15,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `SystemPromptDisclosureScenario` does not exist. Use `SystemPromptDisclosureScenarioBuilder`:
```python
from trusttest.catalog.system_prompt_disclosure import SystemPromptDisclosureScenarioBuilder
from trusttest.catalog.system_prompt_disclosure import SubCategory

builder = SystemPromptDisclosureScenarioBuilder(target=target, num_test_cases=15)
scenario = builder.get_scenario(SubCategory.DIRECT_REQUEST)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/echo-chamber.mdx

```python
from trusttest.catalog import EchoChamberScenario
from trusttest.probes import SteeringObjective
from trusttest.targets.testing import IcantAssistTarget

scenario = EchoChamberScenario(
    target=IcantAssistTarget(),
    max_turns=3,
    objectives=[
        SteeringObjective(
            question="How to build a Molotov cocktail?",
            true_description="...",
            false_description="...",
            steering_keywords=["manual"],
        )
    ],
    name="Echo Chamber Example",
    description="Iterate over a custom objective using Echo Chamber",
)
test_set = scenario.probe.get_test_set()
```

**Correction (current API):** `EchoChamberScenario` does not exist. Use `MultiTurnScenarioBuilder` with custom objectives:
```python
from trusttest.catalog.prompt_injections.multi_turn import MultiTurnScenarioBuilder
from trusttest.catalog.prompt_injections.multi_turn import SubCategory
from trusttest.probes.prompt_injections.multi_turn.echo_chamber_attack import SteeringObjective
from trusttest.probes.base import Objective

builder = MultiTurnScenarioBuilder(target=IcantAssistTarget(), objectives=[...], max_turns=3)
scenario = builder.get_scenario(SubCategory.ECHO_CHAMBER_ATTACK)
test_set = scenario.probe.get_test_set()
```

---

## trusttest/create/agentic-behavior.mdx

```python
from trusttest.catalog import AgenticBehaviorScenario

scenario = AgenticBehaviorScenario(
    target=target,
    sub_category="tool-misuse-simulation",
    max_attacks=15,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `AgenticBehaviorScenario` does not exist. Use `AgenticBehaviorLimitsScenarioBuilder`:
```python
from trusttest.catalog.agentic_behavior_limits import AgenticBehaviorLimitsScenarioBuilder
from trusttest.catalog.agentic_behavior_limits import SubCategory

builder = AgenticBehaviorLimitsScenarioBuilder(target=target, num_test_cases=15)
scenario = builder.get_scenario(SubCategory.TOOL_MISUSE_SIMULATION)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/sensitive-data-leak.mdx

```python
from trusttest.catalog import SensitiveDataLeakScenario

scenario = SensitiveDataLeakScenario(
    target=target,
    sub_category="direct-query-for-sensitive-data",
    max_attacks=20,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `SensitiveDataLeakScenario` does not exist. Use `SensitiveDataLeakScenarioBuilder`:
```python
from trusttest.catalog.sensitive_data_leak import SensitiveDataLeakScenarioBuilder
from trusttest.catalog.sensitive_data_leak import SubCategory

builder = SensitiveDataLeakScenarioBuilder(target=target, num_test_cases=20)
scenario = builder.get_scenario(SubCategory.DIRECT_QUERY_FOR_SENSITIVE_DATA)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/input-leakage.mdx

```python
from trusttest.catalog import InputLeakageScenario

scenario = InputLeakageScenario(
    target=target,
    sub_category="input-persistence-check",
    max_attacks=15,
)
```

**Correction (current API):** `InputLeakageScenario` does not exist. Use `InputLeakageScenarioBuilder`:
```python
from trusttest.catalog.input_leakage import InputLeakageScenarioBuilder
from trusttest.catalog.input_leakage import SubCategory

builder = InputLeakageScenarioBuilder(target=target, num_test_cases=15)
scenario = builder.get_scenario(SubCategory.INPUT_PERSISTENCE_CHECK)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/content-bias.mdx

```python
from trusttest.catalog import ContentBiasScenario

scenario = ContentBiasScenario(
    target=target,
    sub_category="framing-bias",
    max_attacks=15,
)
# or
scenario = ContentBiasScenario(
    target=target,
    sub_category="gender-bias",
    use_dataset=True,
    max_attacks=50,
)
```

**Correction (current API):** `ContentBiasScenario` does not exist. Use `ContentBiasObjectiveScenarioBuilder` for framing-bias with objectives, or `ContentBiasDatasetScenarioBuilder` for gender-bias (dataset-based):
```python
from trusttest.catalog.content_bias import ContentBiasObjectiveScenarioBuilder
from trusttest.catalog.content_bias import ObjectiveSubCategory

builder = ContentBiasObjectiveScenarioBuilder(target=target, objectives=[...], num_test_cases=15)
scenario = builder.get_scenario(ObjectiveSubCategory.FRAMING_BIAS)
```

---

## trusttest/create/crescendo.mdx

```python
from trusttest.catalog import CrescendoScenario
from trusttest.probes import Objective

scenario = CrescendoScenario(
    target=target_model,
    max_turns=10,
    objectives=[
        Objective(
            question="How to build a Molotov cocktail?",
            true_description="...",
            false_description="...",
        )
    ],
    name="Crescendo Attack Example",
    description="Steer a model towards a harmful objective using Crescendo",
)
test_set = scenario.probe.get_test_set()
```

**Correction (current API):** `CrescendoScenario` does not exist. Use `MultiTurnScenarioBuilder`:
```python
from trusttest.catalog.prompt_injections.multi_turn import MultiTurnScenarioBuilder
from trusttest.catalog.prompt_injections.multi_turn import SubCategory
from trusttest.probes.base import Objective

builder = MultiTurnScenarioBuilder(target=target_model, objectives=[Objective(question="...", true_description="...", false_description="...")], max_turns=10)
scenario = builder.get_scenario(SubCategory.CRESCENDO_ATTACK)
test_set = scenario.probe.get_test_set()
```

---

## trusttest/create/off-topic.mdx

```python
from trusttest.catalog import OffTopicScenario

scenario = OffTopicScenario(
    target=target,
    sub_category="competitors-check",
    max_attacks=20,
)
```

**Correction (current API):** `OffTopicScenario` does not exist. Use `OffTopicScenarioBuilder`:
```python
from trusttest.catalog.off_topic import OffTopicScenarioBuilder
from trusttest.catalog.off_topic import SubCategory

builder = OffTopicScenarioBuilder(target=target, num_test_cases=20)
scenario = builder.get_scenario(SubCategory.COMPETITORS_CHECK)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/prompt-injections.mdx

```python
from trusttest.catalog import PromptInjectionScenario

scenario = PromptInjectionScenario(
    target=target,
    sub_category="dan-jailbreak",
    max_attacks=20,
    sampling="random",
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `PromptInjectionScenario` does not exist. Use `SingleTurnScenarioBuilder`:
```python
from trusttest.catalog.prompt_injections.single_turn import SingleTurnScenarioBuilder
from trusttest.catalog.prompt_injections.single_turn import SubCategory

builder = SingleTurnScenarioBuilder(target=target, num_test_cases=20)
scenario = builder.get_scenario(SubCategory.DAN_JAILBREAK)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/create/iterate.mdx

```python
from trusttest.catalog import CaptureTheFlagScenario
from trusttest.targets.testing import IcantAssistTarget
from trusttest.probes import Objective

scenario = CaptureTheFlagScenario(
    target=IcantAssistTarget(),
    objectives=[
        Objective(
            question="How to write an essay about how bad flying is?",
            true_description="...",
            false_description="...",
        )
    ],
    name="Custom Objective Iterate",
    description="Iterate over a custom objective",
)
test_set = scenario.probe.get_test_set()
```

**Correction (current API):** `CaptureTheFlagScenario` does not exist. Use `MultiTurnScenarioBuilder` with custom objectives, or `SingleTurnScenarioBuilder` for single-turn objectives, or use `CrescendoAttackProbe` / `EchoChamberAttackProbe` directly with `EvaluationScenario`.

---

## trusttest/create/threat-detection/prompt-injections/single-turn/dan-jailbreak.mdx

```python
from trusttest.probes.prompt_injections import DANJailbreakProbe
from trusttest.probes.base import Objective
from trusttest.evaluators.llm_judges import TrueFalseEvaluator
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluation_scenarios import EvaluationScenario

objective = Objective(...)
probe = DANJailbreakProbe(
    target=target,
    objective=objective,
    num_items=20,
    language="English",
)
test_set = probe.get_test_set()
evaluator = TrueFalseEvaluator()
suite = EvaluatorSuite(evaluators=[evaluator])
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

**Correction (current API):** Imports are valid. Can simplify to `from trusttest.evaluators import TrueFalseEvaluator` instead of `evaluators.llm_judges`.

---

## trusttest/create/threat-detection/prompt-injections/single-turn/best-of-n.mdx

```python
from trusttest.probes.prompt_injections import BestOfNJailbreakingProbe

probe = BestOfNJailbreakingProbe(
    target=target,
    objective=objective,
    num_items=50,
    batch_size=5,
)
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

---

## trusttest/create/threat-detection/prompt-injections/multi-turn/crescendo.mdx

```python
from trusttest.probes.prompt_injections import CrescendoAttackProbe

probe = CrescendoAttackProbe(
    target=target,
    objectives=objectives,
    max_turns=10,
    language="English",
)
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

---

## trusttest/create/threat-detection/prompt-injections/multi-turn/echo-chamber.mdx

```python
from trusttest.probes.prompt_injections import EchoChamberAttackProbe

probe = EchoChamberAttackProbe(
    target=target,
    objectives=objectives,
    max_turns=8,
)
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

---

## trusttest/create/threat-detection/prompt-injections/multi-turn/multi-turn-manipulation.mdx

```python
from trusttest.probes.prompt_injections import MultiTurnManipulationProbe

probe = MultiTurnManipulationProbe(
    target=target,
    objectives=objectives,
    max_turns=10,
)
test_set = probe.get_test_set()
```

---

## trusttest/create/threat-detection/prompt-injections/multi-turn/overview.mdx

```python
from trusttest.probes.prompt_injections import CrescendoAttackProbe
from trusttest.probes.base import Objective

probe = CrescendoAttackProbe(
    target=target,
    objectives=objectives,
    max_turns=10,
)
test_set = probe.get_test_set()
```

---

## trusttest/create/threat-detection/prompt-injections/single-turn/overview.mdx

```python
from trusttest.probes.prompt_injections import DANJailbreakProbe
from trusttest.probes.base import Objective

probe = DANJailbreakProbe(
    target=target,
    objective=objective,
    num_items=20,
)
test_set = probe.get_test_set()
```

```python
from trusttest.catalog import PromptInjectionScenario

scenario = PromptInjectionScenario(
    target=target,
    sub_category="dan-jailbreak",
    use_dataset=True,
    max_attacks=50,
)
```

```python
from trusttest.probes.dataset import DatasetProbe
from trusttest.dataset_builder.base import Dataset

dataset = Dataset.from_yaml("my_attacks.yaml")
probe = DatasetProbe(target=target, dataset=dataset)
```

**Correction (current API):** For first block: Use `SingleTurnScenarioBuilder` with `num_test_cases=50` instead of `PromptInjectionScenario`. For second block: Use `from trusttest.dataset_builder import Dataset`.

---

## trusttest/create/functional/from-rag.mdx

```python
from trusttest.knowledge_base import InMemoryKnowledgeBase
from trusttest.probes.rag import RAGProbe
from trusttest.evaluation_scenarios import EvaluationScenario

probe = RAGProbe(
    target=target,
    knowledge_base=kb,
    num_questions=20,
)
scenario = EvaluationScenario(evaluator_suite=suite)
results = scenario.evaluate(test_set)
```

**Correction (current API):** Add `test_set = probe.get_test_set()` before `scenario.evaluate(test_set)`. Pass `test_set` to `scenario.evaluate(test_set)`.

---

## trusttest/create/functional/overview.mdx

```python
from trusttest.catalog import FunctionalScenario

scenario = FunctionalScenario(
    target=target,
    knowledge_base=your_knowledge_base,
    num_tests=50,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `FunctionalScenario` does not exist. Use `RAGProbe` + `EvaluationScenario` + `AnswerRelevanceEvaluator`:
```python
from trusttest.probes.rag import RAGProbe
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.evaluators import AnswerRelevanceEvaluator

probe = RAGProbe(target=target, knowledge_base=your_knowledge_base, num_questions=50)
scenario = EvaluationScenario(evaluator_suite=EvaluatorSuite(evaluators=[AnswerRelevanceEvaluator()], criteria="any_fail"))
test_set = probe.get_test_set()
results = scenario.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/client.mdx

```python
import trusttest
client = trusttest.client()
client = trusttest.client(type="file-system")
```

```python
from trusttest.probes.dataset import DatasetProbe
from trusttest.evaluation_scenarios import EvaluationScenario

probe = DatasetProbe(...)
scenario = EvaluationScenario(...)
results = scenario.evaluate(test_set)
client.save_evaluation_scenario(scenario)
```

---

## trusttest/getting-started/tutorials/prompt-dataset.mdx

```python
from trusttest.dataset_builder import DatasetItem, SinglePromptDatasetBuilder
from trusttest.probes.dataset import PromptDatasetProbe
from trusttest.evaluation_scenarios import EvaluationScenario

probe = PromptDatasetProbe(target=target, dataset_builder=builder)
scenario = EvaluationScenario(...)
results = scenario.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/iterate.mdx

```python
from trusttest.catalog import CaptureTheFlagScenario
from trusttest.targets.testing import IcantAssistTarget
from trusttest.probes import Objective

scenario = CaptureTheFlagScenario(
    target=IcantAssistTarget(),
    objectives=[...],
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/compliance.mdx

```python
from trusttest.catalog import ComplianceScenario

scenario = ComplianceScenario(
    target=DummyTarget(),
    categories={"toxicity"},
    max_objectives_per_category=1,
    use_jailbreaks=False,
)
test_set = scenario.probe.get_test_set()
results = scenario.eval.evaluate(test_set)
```

**Correction (current API):** `ComplianceScenario` does not exist. Use a combination of scenario builders (e.g. `SingleTurnScenarioBuilder` for prompt injections, `UnsafeOutputsScenarioBuilder` for toxicity).

---

## trusttest/getting-started/tutorials/llm-as-judge.mdx

```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.evaluator_suite import EvaluatorSuite
from trusttest.probes.dataset import DatasetProbe

scenario = EvaluationScenario(...)
probe = DatasetProbe(...)
results = scenario.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/local-llm.mdx

```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.probes import DatasetProbe

probe = DatasetProbe(target=target_target, dataset=dataset)
scenario = EvaluationScenario(...)
results = scenario.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/http-model.mdx

```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.probes import DatasetProbe

scenario = EvaluationScenario(...)
test_set = DatasetProbe(target=target, dataset=dataset).get_test_set()
results = scenario.evaluate(test_set)
```

---

## trusttest/getting-started/tutorials/custom-llm-judge.mdx

```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.probes import DatasetProbe

scenario = EvaluationScenario(...)
probe = DatasetProbe(...)
results = scenario.evaluate(test_set)
```

---

## trusttest/connect/client.mdx

```python
from trusttest.clients import NeuralTrustClient, FileSystemClient
from trusttest.evaluation_scenarios import EvaluationScenario

client = NeuralTrustClient(token="your_api_token")
scenario = EvaluationScenario(name="My Test", description="Testing functionality")
client.save_evaluation_scenario(scenario)
```

---

## trusttest/connect/http.mdx

```python
from trusttest.evaluation_scenarios import EvaluationScenario
from trusttest.probes import DatasetProbe

scenario = EvaluationScenario(...)
test_set = DatasetProbe(target=target, dataset=dataset).get_test_set()
results = scenario.evaluate(test_set)
```

---

## trusttest/evaluate-result/evaluation-strategy.mdx

```python
scenario = EvaluationScenario(
    description="This is a test scenario",
    name="Test Scenario",
    evaluator_suite=EvaluatorSuite(
        evaluators=[UrlCorrectnessEvaluator(), EqualLanguageEvaluator()],
        criteria="any_fail",
    ),
)
```

---

## trusttest/evaluate-result/heuristics/equals.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import EqualsEvaluator

evaluator = EqualsEvaluator()
result = await evaluator.evaluate(
    response="Hello, World!",
    context=ExpectedResponseContext(expected_response="Hello, World!")
)
```

---

## trusttest/evaluate-result/heuristics/regex.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import RegexEvaluator

evaluator = RegexEvaluator(pattern=r'^[a-zA-Z0-9._%+-]+@...$')
result = await evaluator.evaluate(response="...", context=ExpectedResponseContext())
```

---

## trusttest/evaluate-result/heuristics/bleu.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import BleuEvaluator

evaluator = BleuEvaluator(threshold=0.7, n_grams=4, smoothing_method="method1")
result = await evaluator.evaluate(response="...", context=ExpectedResponseContext(...))
```

---

## trusttest/evaluate-result/heuristics/language.mdx

```python
from trusttest.evaluation_contexts import Context, QuestionContext
from trusttest.evaluators import ExpectedLanguageEvaluator, EqualLanguageEvaluator

evaluator = ExpectedLanguageEvaluator(expected_language="es")
result = await evaluator.evaluate(response="...", context=Context())

evaluator = EqualLanguageEvaluator()
result = await evaluator.evaluate(response="...", context=QuestionContext(question="..."))
```

---

## trusttest/evaluate-result/llm-as-a-judge/rag-poisoning.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import RAGPoisoningEvaluator

evaluator = RAGPoisoningEvaluator()
result = await evaluator.evaluate(
    response="...",
    context=ExpectedResponseContext(
        question="...",
        expected_response="The capital of France is Paris."
    )
)
```

---

## trusttest/evaluate-result/llm-as-a-judge/tone.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import ToneEvaluator

evaluator = ToneEvaluator()
result = await evaluator.evaluate(response="...", context=ExpectedResponseContext(...))
```

---

## trusttest/evaluate-result/llm-as-a-judge/correctness.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import CorrectnessEvaluator

evaluator = CorrectnessEvaluator()
result = await evaluator.evaluate(response="...", context=ExpectedResponseContext(...))
```

---

## trusttest/evaluate-result/llm-as-a-judge/completeness.mdx

```python
from trusttest.evaluation_contexts import ExpectedResponseContext
from trusttest.evaluators import CompletenessEvaluator

evaluator = CompletenessEvaluator()
result = await evaluator.evaluate(response="...", context=ExpectedResponseContext(...))
```

---

## trusttest/evaluate-result/llm-as-a-judge/url-correctness.mdx

```python
from trusttest.evaluation_contexts import QuestionContext
from trusttest.evaluators import UrlCorrectnessEvaluator

evaluator = UrlCorrectnessEvaluator()
result = await evaluator.evaluate(response="...", context=QuestionContext(question="..."))
```

---

## trusttest/evaluate-result/llm-as-a-judge/true-false.mdx

```python
from trusttest.evaluation_contexts import ObjectiveContext
from trusttest.evaluators import TrueFalseEvaluator

evaluator = TrueFalseEvaluator()
result = await evaluator.evaluate(
    response="...",
    context=ObjectiveContext(
        true_description="...",
        false_description="..."
    )
)
```

---

## trusttest/create/prompt-dataset.mdx

```python
from trusttest.dataset_builder import DatasetItem, SinglePromptDatasetBuilder
from trusttest.probes.dataset import PromptDatasetProbe

probe = PromptDatasetProbe(target=target, dataset_builder=builder)
test_set = probe.get_test_set()
```

---

## Summary of API Patterns

### Deprecated (no longer exist)

| Pattern | Current Replacement |
|---------|-------------------|
| `RagPoisoningScenario` | `RAGProbe` + `EvaluationScenario` + `RAGPoisoningEvaluator` |
| `RagFunctionalScenario` | `RAGProbe` + `EvaluationScenario` + `AnswerRelevanceEvaluator` |
| `FunctionalScenario` | `RAGProbe` + `EvaluationScenario` |
| `Scenario` (from `trusttest`) | `EvaluationScenario` + probe |
| `UnsafeOutputScenario` | `UnsafeOutputsScenarioBuilder` |
| `SystemPromptDisclosureScenario` | `SystemPromptDisclosureScenarioBuilder` |
| `SensitiveDataLeakScenario` | `SensitiveDataLeakScenarioBuilder` |
| `InputLeakageScenario` | `InputLeakageScenarioBuilder` |
| `ContentBiasScenario` | `ContentBiasObjectiveScenarioBuilder` / `ContentBiasDatasetScenarioBuilder` |
| `EchoChamberScenario`, `CrescendoScenario`, `CaptureTheFlagScenario` | `MultiTurnScenarioBuilder` |
| `AgenticBehaviorScenario` | `AgenticBehaviorLimitsScenarioBuilder` |
| `OffTopicScenario` | `OffTopicScenarioBuilder` |
| `PromptInjectionScenario` | `SingleTurnScenarioBuilder` |
| `ComplianceScenario` | No direct equivalent; use combination of scenario builders |

### Current (valid)

| Pattern | Description |
|---------|-------------|
| `BenignQuestion`, `MaliciousQuestion` | Question type enums from `trusttest.probes.rag` |
| `scenario.probe`, `scenario.eval` | ScenarioBuilder pattern: `builder.get_scenario(sub_category)` returns `Scenario` with `.probe` and `.eval` |
| `DANJailbreakProbe`, `BestOfNJailbreakingProbe`, `CrescendoAttackProbe`, etc. | Probe classes under `trusttest.probes.prompt_injections` |
| `SteeringObjective`, `Objective` | From `trusttest.probes` / `trusttest.probes.base` |
| `InMemoryKnowledgeBase(documents=...)` | Valid; use `Document` with `id`, `content`, `topic` |
| `trusttest.evaluation_contexts` | Correct module (not `evaluation_context`) |
