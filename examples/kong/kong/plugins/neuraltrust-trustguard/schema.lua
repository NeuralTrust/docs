-- NeuralTrust TrustGuard plugin for Kong Gateway: configuration schema.
-- Self-contained (no custom requires), so it also works as a Konnect custom plugin schema.
local typedefs = require("kong.db.schema.typedefs")

return {
  name = "neuraltrust-trustguard",
  fields = {
    { consumer = typedefs.no_consumer },
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          -- Connection
          { trustguard_url = { type = "string", required = true, default = "https://trustguard.neuraltrust.ai",
              description = "TrustGuard base URL (SaaS or your self-hosted data plane). /v1/evaluate is appended." } },
          { api_key = { type = "string", required = true, referenceable = true, encrypted = true,
              description = "Collector API key. Use a vault reference such as {vault://env/trustguard-api-key}." } },
          { timeout = { type = "integer", default = 10000, between = { 100, 120000 },
              description = "Timeout in ms for each /v1/evaluate call." } },
          { ssl_verify = { type = "boolean", default = true,
              description = "Verify the TrustGuard TLS certificate (needs lua_ssl_trusted_certificate)." } },

          -- What is evaluated
          { evaluate_input = { type = "boolean", default = true } },
          { evaluate_output = { type = "boolean", default = true } },
          { protocol = { type = "string", default = "auto", one_of = { "auto", "llm", "mcp" },
              description = "auto: JSON-RPC 2.0 bodies are sent as mcp, everything else as llm." } },
          { payload_mode = { type = "string", default = "full", one_of = { "full", "minimal" },
              description = "full: the provider body as sent (system prompt, history, tools, tool results). "
                .. "minimal: only {input: last user message}; Indirect Prompt Injection cannot run." } },
          { max_body_bytes = { type = "integer", default = 9437184, between = { 1024, 10485760 },
              description = "Bodies larger than this are not sent; fail_mode decides." } },

          -- Verdict handling
          { block_status = { type = "integer", default = 403, between = { 400, 499 } } },
          { block_message = { type = "string", default = "Request blocked by TrustGuard" } },
          { mcp_block_status = { type = "integer", default = 200, between = { 200, 499 },
              description = "HTTP status of a blocked MCP call. The body is always a JSON-RPC error for the "
                .. "request id; 200 keeps MCP client sessions alive (official SDKs abort on 4xx)." } },
          { mask_request = { type = "boolean", default = false,
              description = "On transform, forward transformed_payload instead of the original request." } },
          { mask_response = { type = "boolean", default = false,
              description = "On transform, write the masked completion / MCP result back into the response." } },
          { transform_fallback = { type = "string", default = "forward", one_of = { "forward", "block" },
              description = "What to do with a transform verdict that is not (or cannot be) applied." } },
          { ask_policy = { type = "string", default = "forward", one_of = { "forward", "block" },
              description = "A gateway cannot prompt the user: forward (record only) or block." } },
          { stream_policy = { type = "string", default = "allow", one_of = { "allow", "buffer", "reject" },
              description = "Requests with stream:true. allow: prompt evaluated, stream passes unevaluated. "
                .. "buffer: the whole stream is buffered and evaluated before the client gets it. "
                .. "reject: 400." } },

          -- Failure behaviour
          { fail_mode = { type = "string", default = "closed", one_of = { "closed", "open" },
              description = "TrustGuard unreachable, timeout, non-200, bad body, oversize: "
                .. "closed answers 503, open forwards and flags." } },

          -- Identity and grouping
          { consumer_id_source = { type = "string", default = "consumer",
              one_of = { "consumer", "header", "none" },
              description = "consumer: the authenticated Kong consumer (username, else custom_id, else id)." } },
          { consumer_id_header = { type = "string", default = "X-Consumer-Username" } },
          { session_id_header = { type = "string", default = "X-Session-Id",
              description = "Conversation id header. When absent, the Kong request id is used (one session per call)." } },
          { user_id_header = { type = "string",
              description = "Header with the end-user id set by a trusted auth plugin (e.g. openid-connect "
                .. "upstream_headers_claims). Sent as attributes.user.id." } },
          { user_email_header = { type = "string" } },
          { user_id_claim = { type = "string", default = "sub",
              description = "Claim read from the JWT verified by the jwt plugin (kong.ctx.shared.authenticated_jwt_token)." } },
          { user_email_claim = { type = "string", default = "email" } },
          { model_provider = { type = "string", description = "Sent as attributes.model.provider." } },

          -- Observability
          { expose_headers = { type = "boolean", default = false,
              description = "Add X-TrustGuard-* headers (status, trace id, failure reason) to the client response." } },
        },
    } },
  },
}
