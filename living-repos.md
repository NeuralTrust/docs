# Inventario de repos vivos — NeuralTrust

Documento interno. **No forma parte de la documentación publicada** en
[docs.neuraltrust.ai](https://docs.neuraltrust.ai): no está en `docs.json`.

| | |
| --- | --- |
| **Org** | [NeuralTrust](https://github.com/NeuralTrust) |
| **Fecha** | 2026-09-09 |
| **Criterio de vivo** | `pushed_at >= 2026-07-09` (últimos 2 meses) y no archivado |
| **Contributor principal** | humano con más commits recientes (bots fuera). Si `main` está quieto, se mira `develop` |
| **Alcance** | producto, integraciones, SDKs en uso, `docs`, `web-public` e infra |
| **Total a controlar** | **56 repos** — 36 producto · 9 integraciones/SDKs · 2 docs/web · 9 infra |

---

## Recuento

| Grupo | Repos |
| --- | ---: |
| Runtime (gateways, firewall, MCP, workers) | 10 |
| SaaS / control plane | 14 |
| Data / residencia | 7 |
| ML | 5 |
| Integraciones y SDKs | 9 |
| Docs y web | 2 |
| Infra | 9 |
| **Total** | **56** |

### Prioridad de test

| P | Significado |
| --- | --- |
| **P0** | Camino crítico de producto o de plataforma. Hay que testearlo siempre. |
| **P1** | Servicio o lib en uso; regresiones duelen. |
| **P2** | Superficie más pequeña o de soporte. |
| **P3** | Vivo por el criterio de push, pero POC, ops-only o al filo. No bloquear un board P0 por estos. |

---

## 1. Runtime

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [TrustGate](https://github.com/NeuralTrust/TrustGate) | público | Go | Edu | 2026-09-09 | P0 | Gateway open-source |
| [TrustGuard](https://github.com/NeuralTrust/TrustGuard) | privado | Go | Victor | 2026-09-09 | P0 | Runtime security |
| [LegacyGateway](https://github.com/NeuralTrust/LegacyGateway) | privado | Go | Edu | 2026-09-02 | P1 | Gateway legacy |
| [LegacyGateway-EE](https://github.com/NeuralTrust/LegacyGateway-EE) | privado | Go | Edu / Kadu | 2026-09-07 | P1 | Enterprise del legacy |
| [firewall](https://github.com/NeuralTrust/firewall) | privado | Python | Martí | 2026-09-08 | P1 | |
| [trustgate-worker](https://github.com/NeuralTrust/trustgate-worker) | privado | Go | Edu | 2026-08-28 | P1 | |
| [MCPCompose](https://github.com/NeuralTrust/MCPCompose) | privado | Go | Edu | 2026-08-28 | P1 | |
| [MCPCloud](https://github.com/NeuralTrust/MCPCloud) | privado | Go | Edu | 2026-08-28 | P1 | |
| [TrustShield](https://github.com/NeuralTrust/TrustShield) | privado | Rust | Edu | 2026-07-27 | P3 | POC |
| [AgentGuardian](https://github.com/NeuralTrust/AgentGuardian) | privado | Go | — | 2026-08-28 | P3 | Casi solo ops |

## 2. SaaS / control plane

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [app](https://github.com/NeuralTrust/app) | privado | TypeScript | Victor / Nerio | 2026-09-09 | P0 | Consola SaaS |
| [admin-console](https://github.com/NeuralTrust/admin-console) | privado | TypeScript | Edu | 2026-09-07 | P1 | |
| [control-plane-api](https://github.com/NeuralTrust/control-plane-api) | privado | Python | Kadu / Martí | 2026-09-09 | P0 | API REST del control plane |
| [data-plane-api](https://github.com/NeuralTrust/data-plane-api) | privado | Python | Kadu | 2026-09-07 | P1 | |
| [scheduler](https://github.com/NeuralTrust/scheduler) | privado | TypeScript | Kadu | 2026-09-07 | P1 | |
| [AlertEngine](https://github.com/NeuralTrust/AlertEngine) | privado | Go | Victor | 2026-09-08 | P1 | |
| [watchdog](https://github.com/NeuralTrust/watchdog) | privado | Go | Kadu | 2026-09-09 | P1 | |
| [TrustLens](https://github.com/NeuralTrust/TrustLens) | privado | Go | Albert | 2026-09-03 | P1 | Actividad reciente también en `develop` |
| [TrustTest](https://github.com/NeuralTrust/TrustTest) | privado | Python | Martí | 2026-09-02 | P1 | Red-teaming / evaluación |
| [aispm](https://github.com/NeuralTrust/aispm) | privado | Python | — | 2026-08-24 | P2 | Casi solo ops |
| [TrustScan](https://github.com/NeuralTrust/TrustScan) | privado | Python | — | 2026-08-19 | P2 | Scanner de model files; casi solo ops |
| [neuraltrust-browser-extension](https://github.com/NeuralTrust/neuraltrust-browser-extension) | privado | TypeScript | — | 2026-09-06 | P2 | |
| [agent-security](https://github.com/NeuralTrust/agent-security) | privado | TypeScript | — | 2026-09-07 | P2 | Next.js; push reciente fuera de `main`/`develop` |
| [red-teaming](https://github.com/NeuralTrust/red-teaming) | privado | Python | — | 2026-07-16 | P3 | Filo de vivo |

## 3. Data / residencia

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [DataCore](https://github.com/NeuralTrust/DataCore) | privado | Go | Kadu | 2026-09-09 | P0 | |
| [DataBridge](https://github.com/NeuralTrust/DataBridge) | privado | Go | Kadu | 2026-09-02 | P1 | |
| [DataAgent](https://github.com/NeuralTrust/DataAgent) | privado | Go | Kadu | 2026-09-02 | P1 | |
| [dataplane-bundle](https://github.com/NeuralTrust/dataplane-bundle) | privado | Go | Edu | 2026-09-02 | P1 | |
| [kafka-workers](https://github.com/NeuralTrust/kafka-workers) | privado | Python | Martí | 2026-09-02 | P1 | Observabilidad LLM |
| [SIEMConnectors](https://github.com/NeuralTrust/SIEMConnectors) | privado | JavaScript | Telm / Kadu | 2026-09-03 | P1 | |
| [collectors](https://github.com/NeuralTrust/collectors) | privado | Python | Victor | 2026-09-03 | P2 | Scaffold |

## 4. ML

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [ML](https://github.com/NeuralTrust/ML) | privado | Python | Miquel | 2026-09-09 | P1 | |
| [trustml](https://github.com/NeuralTrust/trustml) | privado | Python | Martí | 2026-09-09 | P1 | SDK interno de modelos |
| [analysis-api](https://github.com/NeuralTrust/analysis-api) | privado | Python | — | 2026-08-19 | P2 | Análisis y datasets del paquete ML |
| [aiapi](https://github.com/NeuralTrust/aiapi) | privado | Python | — | 2026-08-19 | P2 | |
| [deploy-api](https://github.com/NeuralTrust/deploy-api) | privado | Python | — | 2026-08-19 | P2 | |

## 5. Integraciones y SDKs

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [n8n-nodes-trustguard](https://github.com/NeuralTrust/n8n-nodes-trustguard) | público | TypeScript | Albert | 2026-09-08 | P1 | Nodo n8n de TrustGuard |
| [langchain-neuraltrust](https://github.com/NeuralTrust/langchain-neuraltrust) | público | Python | Albert | 2026-09-02 | P1 | Middleware LangChain; default branch `master` |
| [strands-neuraltrust](https://github.com/NeuralTrust/strands-neuraltrust) | público | Python | Albert | 2026-09-09 | P1 | Integración AWS Strands |
| [trustguard-cursor-plugin](https://github.com/NeuralTrust/trustguard-cursor-plugin) | público | Go | Victor | 2026-08-28 | P1 | Plugin Cursor |
| [trustguard-claude-code-plugin](https://github.com/NeuralTrust/trustguard-claude-code-plugin) | público | Go | Victor | 2026-08-31 | P1 | Plugin Claude Code |
| [trustguard-codex-plugin](https://github.com/NeuralTrust/trustguard-codex-plugin) | público | Go | Victor | 2026-08-28 | P1 | Plugin Codex |
| [trustguard-copilot-plugin](https://github.com/NeuralTrust/trustguard-copilot-plugin) | público | Go | Victor | 2026-08-31 | P1 | Plugin Copilot |
| [trustguard-sdk](https://github.com/NeuralTrust/trustguard-sdk) | público | Python | Victor | 2026-08-25 | P1 | SDK de TrustGuard |
| [event-schemas](https://github.com/NeuralTrust/event-schemas) | privado | Python | Edu | 2026-09-02 | P1 | Contratos Protobuf |

## 6. Docs y web

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [docs](https://github.com/NeuralTrust/docs) | público | MDX | Sergi Vidal | 2026-09-09 | P0 | Fuente de docs.neuraltrust.ai |
| [web-public](https://github.com/NeuralTrust/web-public) | privado | JavaScript | Nerio | 2026-09-09 | P0 | Site público (Storyblok / Vercel) |

## 7. Infra

| Repo | Vis. | Lang | Dueño | Último push | P | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| [neuraltrust-platform](https://github.com/NeuralTrust/neuraltrust-platform) | público | Shell | Kadu | 2026-09-09 | P0 | Helm umbrella |
| [gitops](https://github.com/NeuralTrust/gitops) | privado | Shell | Kadu | 2026-09-07 | P0 | Flux |
| [cloud-infrastructure](https://github.com/NeuralTrust/cloud-infrastructure) | privado | HCL | Kadu | 2026-09-09 | P0 | Terraform GCP / AWS / CF |
| [core-infrastructure](https://github.com/NeuralTrust/core-infrastructure) | privado | Shell | Kadu | 2026-09-02 | P0 | ClickStack / gateways |
| [observability](https://github.com/NeuralTrust/observability) | privado | Go | Kadu | 2026-09-09 | P1 | ClickStack as code |
| [workflows](https://github.com/NeuralTrust/workflows) | público | JavaScript | Kadu / Albert | 2026-09-03 | P1 | GitHub Actions reutilizables |
| [runtime-loca-infra](https://github.com/NeuralTrust/runtime-loca-infra) | privado | Shell | Edu | 2026-07-15 | P1 | e2e hybrid |
| [status-page](https://github.com/NeuralTrust/status-page) | privado | TypeScript | Kadu | 2026-09-07 | P2 | |
| [.github](https://github.com/NeuralTrust/.github) | público | — | Victor | 2026-09-03 | P3 | Perfil de la org |

---

## Fuera de alcance

No se controlan ni se testean como parte de este inventario.

### Excluidos a petición

| Repo | Motivo |
| --- | --- |
| `kafka-connect` | Conector viejo |
| `internal-sdk` | SDK interno, fuera de alcance |
| `agentguardian-api` | SDK / proto de AgentGuardian |
| `neuraltrust-typescript` | SDK TypeScript, fuera de alcance |
| `TrustGate-Client` | Cliente viejo de TrustGate |

### Vivos por push, pero benches / demos / POC / research

`e2e-tests`, `agent-gateway-eval`, `agentguardian-demo-api`, `poc-agents`, `tech-slides`, `multi-agent-tests`, `AI-Gateway-Benchmark`, `trusttest-examples`, `agent-swarms`, `compliance`, `agent-posture-research`, `benchmarks-v2`, `agents-hub`, `FakeAI`, `neuraltrust-iso-topology`.

### Resto

Repos sin push desde el 2026-07-09, archivados, y el resto de demos / research / slides de la org.

---

## Dueños (quién toca qué)

| Persona | Repos |
| --- | --- |
| **Victor** | TrustGuard, app, plugins IDE, `trustguard-sdk`, AlertEngine, collectors, `.github` |
| **Edu** | TrustGate, admin-console, LegacyGateway, event-schemas, dataplane-bundle, trustgate-worker, MCP\*, TrustShield, runtime-loca-infra |
| **Kadu** | Casi toda infra + DataCore / DataBridge / DataAgent + control-plane-api + scheduler + watchdog + SIEM |
| **Martí** | firewall, TrustTest, trustml, kafka-workers, control-plane-api |
| **Albert** | TrustLens, n8n, LangChain, Strands |
| **Nerio** | app, web-public |
| **Miquel** | ML |
| **Sergi Vidal** | docs |
| **Telm** | SIEM / bumps de seguridad |

---

## Board P0 (punto de partida para test)

Si solo se testea lo crítico:

1. `TrustGate`
2. `TrustGuard`
3. `app`
4. `control-plane-api`
5. `DataCore`
6. `docs`
7. `web-public`
8. `neuraltrust-platform`
9. `gitops`
10. `cloud-infrastructure`
11. `core-infrastructure`

---

## Cómo refrescar

1. Listar repos de la org no archivados con `pushed_at >=` (hoy − 2 meses).
2. Quitar benches, demos, POCs, research, slides y los cinco repos de la sección *Excluidos a petición*.
3. Recalcular contributor principal humano en `main` (o `develop` si `main` está quieto).
4. Actualizar las tablas y la fecha de este documento.
