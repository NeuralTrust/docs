# NeuralTrust documentation

**NeuralTrust is the security platform for AI and agents.** Route and govern model
traffic, inspect every prompt and response in real time, and stress-test your
applications before they ship — with one policy set and one audit trail across all of
it.

This repository is the source for [docs.neuraltrust.ai](https://docs.neuraltrust.ai).
More about the platform at [neuraltrust.ai](https://neuraltrust.ai/).

## The products

| | What it does |
| --- | --- |
| **TrustGate** | Open-source AI gateway for LLM and agent traffic — multi-provider routing, load balancing, policies, and MCP. |
| **TrustGuard** | Runtime security. Inspects prompts and responses inline for jailbreaks, PII, toxicity and tool abuse, then blocks or redacts. |
| **TrustTest** | Red-teaming and evaluation. Attack your own LLM applications and measure safety and reliability before rollout. |

Around them sits the platform: users and SSO, audit logs, SIEM export, custom domains
and feature flags, shared by every product.

## Run it where your data has to live

The same Helm chart covers four topologies, so the security layer follows your
constraints instead of the other way round.

| Model | Who runs the control plane | Where raw payloads live |
| --- | --- | --- |
| **SaaS** | NeuralTrust | NeuralTrust |
| **Hybrid** | NeuralTrust | Your cluster |
| **External** | You | Your cluster |
| **Central** | You, for many clusters | Each cluster keeps its own |

Every cross-boundary connection is outbound TLS on 443, initiated from your
environment — nothing dials into a data plane. Start at
[Deployment → Overview](https://docs.neuraltrust.ai/neuraltrust/deployment/overview).

## Where to start reading

- **New here** — [docs.neuraltrust.ai](https://docs.neuraltrust.ai) has the three
  first journeys: your first gateway, connecting TrustGuard, and your first red team.
- **Deploying** — `neuraltrust/deployment/` holds one self-contained guide per model,
  each with its architecture, prerequisites, network rules, install steps and high
  availability.
- **Diagrams** — published SVGs live in `images/static/img/`. Editable `.drawio`
  sources are **not** in this public repo; they live in the private `compliance`
  repository (`architecture/`). Notion holds PNG previews only.

## Contributing

Content lives in `.mdx` files; navigation, redirects and theming live in `docs.json`.
Keep one topic per page, link rather than repeat, and add a redirect in `docs.json`
whenever a page moves or is removed.

## Preview and deploy

Deployment is automatic: pushing to the default branch publishes to production through
the Mintlify GitHub App.

To preview locally you need **Node 20 or 22 LTS** (see `.nvmrc` — Mintlify does not
support Node 25+), then:

```bash
npm i -g mintlify@latest
mintlify dev            # run from the folder containing docs.json
```

If you use a version manager, `fnm use` or `nvm use` picks up `.nvmrc`. On Homebrew
without one: `brew install node@22` and put it first on your `PATH`.

Common problems:

- **"not supported on node versions 25+"** — you are on the wrong Node. Check
  `node -v` before `mintlify dev`.
- **Invalid theme** — upgrade the CLI with `npm i -g mintlify@latest`, and confirm
  `which mintlify` points at that install.
- **`mintlify dev` will not start** — run `mintlify install` to reinstall dependencies.
- **Every page 404s** — you are not in the folder that holds `docs.json`.
