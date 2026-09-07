# Documentation visuals

The SVG diagrams in this directory are editable source files. They use the
NeuralTrust product palette and describe integration behavior documented in this
repository. Update the diagram and its adjacent text together when that behavior
changes.

| Asset | Documentation source |
| --- | --- |
| `coding-agent-security-flow.svg` | `integrations/claude.mdx`, `integrations/cursor.mdx`, `integrations/codex.mdx`, `integrations/github-copilot.mdx` |
| `gateway-evaluation-flow.svg` | Gateway guides in `integrations/` and `integrations/coverage.mdx` |
| `edge-request-evaluation.svg` | `integrations/akamai.mdx`, `integrations/aws-cloudfront.mdx`, `integrations/cloudflare.mdx`, `integrations/fastly.mdx` |

The product illustration at `../static/img/trustguard-product.svg` follows
`trustguard/how-it-works.mdx` and `trustguard/concepts/policies.mdx`.

Each SVG includes a title and description. Pages embedding an image must also
provide descriptive `alt` text and explain any coverage limits in ordinary page
text so they remain readable on small screens.

For screenshots, record the product version, capture date, and example setup here.
Use a demo environment without customer information or credentials, and check
the image whenever the documented controls change.

## n8n screenshot

- File: `n8n-verdict-routing.png`
- Captured: 2026-09-07 from a local n8n 2.35.3 instance with
  `@neuraltrust/n8n-nodes-trustguard` 0.2.1.
- Workflow: [`trustguard-ask-approval.json`](../../examples/n8n/trustguard-ask-approval.json),
  adapted from the node's [four-verdict example](https://github.com/NeuralTrust/n8n-nodes-trustguard/blob/main/examples/workflows/01-input-gate-four-verdicts.json).
- The real n8n canvas shows the installed TrustGuard node and its four named
  outputs. A Switch after Block separates `ask` from `block` and routes Ask to
  a chat approval step. Ask support was added in 0.2.0; it does not add a fifth
  output to the node.
- This is a configuration example. The workflow was not executed and no live
  collector key, customer data, or external model connection was used.
- The chat participant is the approver in this demo. A production workflow that
  requires an authorized reviewer must use an authenticated approval channel
  restricted to those reviewers.
- To recapture, install the community node in a local demo instance, import the
  example workflow, and capture the canvas with all four outputs and the Ask
  approval branch visible.
