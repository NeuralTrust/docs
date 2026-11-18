# TrustGuard for Apigee

Shared Flow, configuration, and sample proxy for the
[Apigee integration guide](https://docs.neuraltrust.ai/integrations/apigee).

| Path | What it is |
| --- | --- |
| `trustguard-evaluate.zip` | The Shared Flow bundle to import (built from `sharedflowbundle/`) |
| `sharedflowbundle/` | Its source: policies and JavaScript |
| `trustguard.properties` | The environment property set `trustguard` |
| `sample-proxy/` | `llm-openai-guarded`: VerifyJWT, the identity AssignMessage, and both FlowCallouts in front of OpenAI. `llm-openai-guarded.zip` is the importable bundle |

Rebuild the zip after editing the source:

```bash
cd examples/apigee && rm -f trustguard-evaluate.zip && zip -r trustguard-evaluate.zip sharedflowbundle
```

The zip must have `sharedflowbundle/` at its root.
