-- NeuralTrust TrustGuard plugin for Kong Gateway (OSS and Enterprise 3.x).
--
-- Request path (access phase): the request body is sent to POST /v1/evaluate with
-- direction "input" before the upstream (model provider or MCP server) is called.
-- Response path (response phase, buffered proxying): the completion or the MCP result is
-- sent with direction "output" before the client receives it.
--
-- /v1/evaluate answers HTTP 200 for every evaluation, including "block": the decision is
-- always read from the "status" field, never from the HTTP status.
--
-- Single file on purpose: no custom requires, so it can run as a Konnect / streamed
-- custom plugin as well as a classic one.
local cjson = require("cjson.safe").new()
-- Keep empty arrays as arrays ("tools": []), avoid "\/" escapes and keep 16 significant
-- digits when a (masked) body has to be re-encoded.
cjson.decode_array_with_array_mt(true)
cjson.encode_escape_forward_slash(false)
cjson.encode_number_precision(16)
local http = require("resty.http")

local ngx = ngx
local kong = kong
local fmt = string.format

local Plugin = {
  PRIORITY = 790,   -- after auth plugins (jwt 1450, key-auth 1250, openid-connect 1050),
                    -- rate limiting (910), before ai-proxy (770)
  VERSION = "1.0.0",
}

local LLM_ROOTS = { "input", "messages", "system", "contents", "systemInstruction", "tools" }
local KNOWN = { allow = true, report = true, transform = true, ask = true, block = true, skip = true }

---------------------------------------------------------------------------------------------
-- helpers
---------------------------------------------------------------------------------------------
local function is_object(v)
  if type(v) ~= "table" then return false end
  if next(v) == nil then return getmetatable(v) ~= cjson.array_mt end
  return v[1] == nil
end

local function is_array(v)
  return type(v) == "table" and (v[1] ~= nil or getmetatable(v) == cjson.array_mt)
end

local function header(name)
  if not name or name == "" then return nil end
  local v = kong.request.get_header(name)
  if type(v) == "table" then v = v[1] end
  if v == "" then return nil end
  return v
end

local function text_of(c)
  if type(c) == "string" then return c end
  if is_array(c) then
    local out = {}
    for _, p in ipairs(c) do
      if type(p) == "table" and type(p.text) == "string" then out[#out + 1] = p.text end
    end
    return table.concat(out, "\n")
  end
  return ""
end

local function has_llm_root(b)
  for _, k in ipairs(LLM_ROOTS) do
    if b[k] ~= nil and b[k] ~= cjson.null then return true end
  end
  return false
end

local function last_user_text(b)
  if type(b.input) == "string" then return b.input end
  local list = b.messages or b.contents or (is_array(b.input) and b.input) or nil
  if not is_array(list) then return "" end
  for i = #list, 1, -1 do
    local m = list[i]
    if type(m) == "table" and m.role == "user" then
      if is_array(m.parts) then return text_of(m.parts) end
      return text_of(m.content)
    end
  end
  return ""
end

-- Assistant text and tool calls of a provider response (OpenAI Chat / Responses,
-- Anthropic Messages, Gemini, Cohere v2). texts[] keeps {holder, key} so a masked value
-- can be written back.
local function extract_completion(r)
  local texts, calls = {}, {}
  if is_array(r.choices) then
    for _, ch in ipairs(r.choices) do
      local m = type(ch) == "table" and ch.message
      if type(m) == "table" then
        if type(m.content) == "string" and m.content ~= "" then texts[#texts + 1] = { holder = m, key = "content" } end
        if type(m.refusal) == "string" and m.refusal ~= "" then texts[#texts + 1] = { holder = m, key = "refusal" } end
        if is_array(m.tool_calls) then
          for _, tc in ipairs(m.tool_calls) do calls[#calls + 1] = tc end
        end
      end
    end
  elseif is_array(r.output) then
    for i, o in ipairs(r.output) do
      if type(o) == "table" and o.type == "message" and is_array(o.content) then
        for _, p in ipairs(o.content) do
          if type(p) == "table" and p.type == "output_text" and type(p.text) == "string" then
            texts[#texts + 1] = { holder = p, key = "text" }
          end
        end
      elseif type(o) == "table" and o.type == "function_call" then
        calls[#calls + 1] = { id = o.call_id or o.id or ("call_" .. i), type = "function",
          ["function"] = { name = o.name, arguments = type(o.arguments) == "string" and o.arguments or cjson.encode(o.arguments or {}) } }
      end
    end
  elseif is_array(r.content) and r.type == "message" then
    for _, p in ipairs(r.content) do
      if type(p) == "table" and p.type == "text" and type(p.text) == "string" then texts[#texts + 1] = { holder = p, key = "text" } end
      if type(p) == "table" and p.type == "tool_use" then
        calls[#calls + 1] = { id = p.id, type = "function", ["function"] = { name = p.name, arguments = cjson.encode(p.input or {}) } }
      end
    end
  elseif is_array(r.candidates) then
    for i, c in ipairs(r.candidates) do
      local parts = type(c) == "table" and type(c.content) == "table" and c.content.parts
      if is_array(parts) then
        for j, p in ipairs(parts) do
          if type(p) == "table" and type(p.text) == "string" and p.thought ~= true then texts[#texts + 1] = { holder = p, key = "text" } end
          if type(p) == "table" and type(p.functionCall) == "table" then
            calls[#calls + 1] = { id = fmt("call_%d_%d", i, j), type = "function",
              ["function"] = { name = p.functionCall.name, arguments = cjson.encode(p.functionCall.args or {}) } }
          end
        end
      end
    end
  elseif type(r.message) == "table" and is_array(r.message.content) then
    for _, p in ipairs(r.message.content) do
      if type(p) == "table" and p.type == "text" and type(p.text) == "string" then texts[#texts + 1] = { holder = p, key = "text" } end
    end
  end
  return texts, calls
end

-- Server-sent events: returns the list of decoded "data:" JSON objects.
local function sse_events(body)
  local events = {}
  for line in (body .. "\n"):gmatch("([^\n]*)\n") do
    local data = line:match("^data:%s?(.*)$")
    if data then
      data = data:gsub("\r$", "")
      if data ~= "" and data ~= "[DONE]" then
        local obj = cjson.decode(data)
        if type(obj) == "table" then events[#events + 1] = obj end
      end
    end
  end
  return events
end

-- Reassemble an LLM completion from SSE chunks (OpenAI Chat, OpenAI Responses, Anthropic).
local function sse_completion(events)
  local text, calls, by_index = {}, {}, {}
  for _, e in ipairs(events) do
    if is_array(e.choices) then
      for _, ch in ipairs(e.choices) do
        local d = type(ch) == "table" and ch.delta
        if type(d) == "table" then
          if type(d.content) == "string" then text[#text + 1] = d.content end
          if is_array(d.tool_calls) then
            for _, tc in ipairs(d.tool_calls) do
              local idx = tc.index or 0
              local acc = by_index[idx]
              if not acc then
                acc = { id = tc.id, type = "function", ["function"] = { name = "", arguments = "" } }
                by_index[idx] = acc
                calls[#calls + 1] = acc
              end
              local f = tc["function"] or {}
              if type(f.name) == "string" then acc["function"].name = acc["function"].name .. f.name end
              if type(f.arguments) == "string" then acc["function"].arguments = acc["function"].arguments .. f.arguments end
            end
          end
        end
      end
    elseif e.type == "response.output_text.delta" and type(e.delta) == "string" then
      text[#text + 1] = e.delta
    elseif e.type == "content_block_delta" and type(e.delta) == "table" and type(e.delta.text) == "string" then
      text[#text + 1] = e.delta.text
    elseif is_array(e.candidates) then
      local t = extract_completion(e)
      for _, s in ipairs(t) do text[#text + 1] = s.holder[s.key] end
    end
  end
  return table.concat(text), calls
end

local function first_jsonrpc(events)
  for _, e in ipairs(events) do
    if e.jsonrpc == "2.0" then return e end
  end
end

local function jwt_claims()
  local tok = kong.ctx.shared.authenticated_jwt_token
  if type(tok) ~= "string" then return nil end
  local seg = tok:match("^[^.]+%.([^.]+)%.")
  if not seg then return nil end
  seg = seg:gsub("-", "+"):gsub("_", "/")
  local pad = #seg % 4
  if pad > 0 then seg = seg .. string.rep("=", 4 - pad) end
  local raw = ngx.decode_base64(seg)
  return raw and cjson.decode(raw) or nil
end

local function consumer_id(conf)
  if conf.consumer_id_source == "none" then return nil end
  if conf.consumer_id_source == "header" then return header(conf.consumer_id_header) end
  local c = kong.client.get_consumer()
  if c then return c.username or c.custom_id or c.id end
  local cred = kong.client.get_credential()
  if cred then return cred.consumer_id or cred.id end
  return nil
end

local function user_attrs(conf)
  local uid, email = header(conf.user_id_header), header(conf.user_email_header)
  if not uid or not email then
    local claims = jwt_claims()
    if type(claims) == "table" then
      uid = uid or (conf.user_id_claim and claims[conf.user_id_claim])
      email = email or (conf.user_email_claim and claims[conf.user_email_claim])
    end
  end
  if uid == nil and email == nil then return nil end
  local u = {}
  if uid ~= nil then u.id = tostring(uid) end
  if email ~= nil then u.email = tostring(email) end
  return u
end

-- Verdict headers for the client (expose_headers). kong.response.set_header works in both
-- the access and the response phase; a plugin with a response handler cannot also have a
-- header_filter.
local function set_out_header(name, value)
  local t = kong.ctx.plugin.out_headers or {}
  t[name] = value
  kong.ctx.plugin.out_headers = t
  if kong.ctx.plugin.expose and value ~= nil then
    kong.response.set_header(name, tostring(value))
  end
end

local function deny(conf, status, message, extra_headers, trace_id, kind)
  local headers = { ["Content-Type"] = "application/json" }
  for k, v in pairs(extra_headers or {}) do headers[k] = v end
  if conf.expose_headers then
    for k, v in pairs(kong.ctx.plugin.out_headers or {}) do headers[k] = v end
  end
  local ctx = kong.ctx.plugin
  if ctx.protocol == "mcp" and ctx.rpc_id ~= nil and kind == "trustguard_block" then
    -- MCP clients expect a JSON-RPC error for the same id. Official MCP SDKs abort the whole
    -- session on a non-2xx answer, so the HTTP status is mcp_block_status (default 200).
    return kong.response.exit(conf.mcp_block_status, cjson.encode({ jsonrpc = "2.0", id = ctx.rpc_id, error = {
      code = -32001, message = message, data = { type = kind, trace_id = trace_id } } }), headers)
  end
  -- OpenAI-style error so SDK clients surface the message.
  return kong.response.exit(status, cjson.encode({ error = {
    message = message, type = kind, code = kind, trace_id = trace_id } }), headers)
end

-- fail_mode. Returns true when the caller must stop (response already sent).
local function failure(conf, direction, reason, retry_after)
  kong.log.warn("TrustGuard ", direction, " evaluation failed: ", reason)
  set_out_header("X-TrustGuard-Failure", reason)
  kong.ctx.plugin[direction .. "_failure"] = reason
  if conf.fail_mode == "open" then
    return false
  end
  deny(conf, 503, "TrustGuard unavailable", { ["Retry-After"] = tostring(retry_after or 5) }, nil, "trustguard_unavailable")
  return true
end

local function evaluate(conf, req)
  local body = cjson.encode(req)
  local httpc = http.new()
  httpc:set_timeout(conf.timeout)
  local url = conf.trustguard_url:gsub("/+$", "")
  if url:sub(-12) ~= "/v1/evaluate" then url = url .. "/v1/evaluate" end
  local res, err = httpc:request_uri(url, {
    method = "POST",
    body = body,
    ssl_verify = conf.ssl_verify,
    headers = {
      ["Content-Type"] = "application/json",
      ["Authorization"] = "Bearer " .. conf.api_key,
      ["User-Agent"] = "kong-neuraltrust-trustguard/" .. Plugin.VERSION,
    },
  })
  if not res then return nil, "callout_failed: " .. tostring(err) end
  if res.status == 429 then
    local r = cjson.decode(res.body or "")
    local reason = "rate_limited" .. ((type(r) == "table" and type(r.reason) == "string") and ("_" .. r.reason) or "")
    return nil, reason, tonumber(res.headers["Retry-After"])
  end
  if res.status < 200 or res.status > 299 then
    return nil, "http_" .. res.status
  end
  local r = cjson.decode(res.body or "")
  if not is_object(r) or type(r.status) ~= "string" then return nil, "bad_response" end
  if not KNOWN[r.status] then return nil, "unknown_status_" .. r.status end
  return r
end

local function build_request(conf, direction, protocol, payload, model)
  local ctx = kong.ctx.plugin
  local req = { protocol = protocol, direction = direction, payload = payload }
  if not ctx.identity then
    local route = kong.router.get_route()
    local service = kong.router.get_service()
    ctx.identity = {
      session_id = header(conf.session_id_header) or kong.request.get_header("X-Request-Id") or ngx.var.request_id,
      consumer_id = consumer_id(conf),
      user = user_attrs(conf),
      application = (route and route.name) or (service and service.name) or "kong",
    }
  end
  local id = ctx.identity
  req.session_id = id.session_id
  req.consumer_id = id.consumer_id
  local attrs = { source = { application = id.application } }
  if id.user then attrs.user = id.user end
  if type(model) == "string" and model ~= "" then
    attrs.model = { name = model, provider = conf.model_provider }
  end
  req.attributes = attrs
  return req
end

local function record(direction, r)
  set_out_header("X-TrustGuard-" .. (direction == "input" and "Input" or "Output") .. "-Status", r.status)
  if r.trace_id then
    set_out_header("X-TrustGuard-" .. (direction == "input" and "Input" or "Output") .. "-Trace-Id", r.trace_id)
  end
  kong.log.set_serialize_value("trustguard." .. direction .. ".status", r.status)
  kong.log.set_serialize_value("trustguard." .. direction .. ".trace_id", r.trace_id)
end

-- Turns transform/ask into a final action: "allow" | "block" | "mask".
local function decide(conf, direction, r)
  if r.status == "block" then return "block" end
  if r.status == "ask" then return conf.ask_policy == "block" and "block" or "allow" end
  if r.status == "transform" then
    local want = (direction == "input") and conf.mask_request or conf.mask_response
    if want then return "mask" end
    return conf.transform_fallback == "block" and "block" or "allow"
  end
  return "allow" -- allow, report, skip
end

---------------------------------------------------------------------------------------------
-- request path
---------------------------------------------------------------------------------------------
local function no_output(reason)
  -- Nothing to evaluate on the way back: proxy unbuffered (keeps streaming working).
  -- Kong turns buffered proxying on for every route that has a plugin with a response
  -- handler; this per-request opt-out is what lets stream:true requests stream.
  kong.ctx.plugin.output_skip = reason
  ngx.ctx.buffered_proxying = nil
end

function Plugin:access(conf)
  local ctx = kong.ctx.plugin
  ctx.expose = conf.expose_headers
  if conf.evaluate_output then
    -- Ask the upstream for an uncompressed body so it can be read in the response phase.
    kong.service.request.clear_header("Accept-Encoding")
  end

  local method = kong.request.get_method()
  if method ~= "POST" and method ~= "PUT" and method ~= "PATCH" then
    -- e.g. MCP GET (SSE notification stream) or DELETE (session end): nothing to evaluate.
    return no_output("no_body_method")
  end

  local raw, err = kong.request.get_raw_body(conf.max_body_bytes)
  if not raw then
    -- Body larger than max_body_bytes (or unreadable): never forward it uninspected in closed mode.
    if failure(conf, "input", "oversize_or_unreadable: " .. tostring(err)) then return end
    return no_output("input_failure")
  end
  if raw == "" then return no_output("empty_body") end
  if #raw > conf.max_body_bytes then
    if failure(conf, "input", "oversize") then return end
    return no_output("input_failure")
  end

  local ctype = (kong.request.get_header("Content-Type") or ""):lower()
  if ctype ~= "" and not ctype:find("json", 1, true) then return no_output("not_json") end

  local body = cjson.decode(raw)
  if is_array(body) and type(body[1]) == "table" and body[1].jsonrpc == "2.0" then
    -- JSON-RPC batch: /v1/evaluate takes one message. Treat as a failure so it is never
    -- forwarded uninspected in closed mode.
    if failure(conf, "input", "jsonrpc_batch_unsupported") then return end
    return no_output("input_failure")
  end
  if not is_object(body) then return no_output("not_json_object") end

  local protocol = conf.protocol
  if protocol == "auto" then protocol = (body.jsonrpc == "2.0") and "mcp" or "llm" end
  ctx.protocol = protocol
  ctx.model = type(body.model) == "string" and body.model or nil

  local payload
  if protocol == "mcp" then
    if body.jsonrpc ~= "2.0" then return no_output("not_jsonrpc") end
    if body.method == nil then return no_output("jsonrpc_no_method") end
    ctx.rpc_id = body.id
    if body.id == nil then
      -- Notification (e.g. notifications/initialized): no response body to evaluate.
      ctx.output_skip = "jsonrpc_notification"
    end
    payload = body
  else
    if not has_llm_root(body) then return no_output("not_llm_body") end
    if body.stream == true then
      ctx.streaming = true
      if conf.stream_policy == "reject" then
        return deny(conf, 400, "Streaming is not allowed on this route", nil, nil, "trustguard_stream_rejected")
      end
    end
    payload = (conf.payload_mode == "minimal") and { input = last_user_text(body) } or body
  end

  if conf.evaluate_input then
    local r, ferr, retry = evaluate(conf, build_request(conf, "input", protocol, payload, ctx.model))
    if not r then
      if failure(conf, "input", ferr, retry) then return end
    else
      record("input", r)
      local action = decide(conf, "input", r)
      if action == "block" then
        return deny(conf, conf.block_status, conf.block_message, nil, r.trace_id, "trustguard_block")
      elseif action == "mask" then
        local tp = r.transformed_payload
        local ok = false
        if is_object(tp) then
          if protocol == "mcp" then
            ok = tp.jsonrpc == "2.0"
          else
            ok = conf.payload_mode == "full" and has_llm_root(tp)
          end
        end
        if ok then
          local new = cjson.encode(tp)
          kong.service.request.set_raw_body(new)
          set_out_header("X-TrustGuard-Input-Masked", "true")
        elseif conf.transform_fallback == "block" then
          return deny(conf, conf.block_status, conf.block_message, nil, r.trace_id, "trustguard_block")
        end
      end
    end
  end

  if not conf.evaluate_output then return no_output("output_disabled") end
  if ctx.output_skip then return no_output(ctx.output_skip) end
  if ctx.streaming and conf.stream_policy == "allow" then
    set_out_header("X-TrustGuard-Output-Status", "unevaluated_stream")
    return no_output("stream_unevaluated")
  end
end

---------------------------------------------------------------------------------------------
-- response path (only runs with buffered proxying)
---------------------------------------------------------------------------------------------
local function write_response(status, body, headers)
  local out = {}
  for k, v in pairs(headers or {}) do
    local lk = k:lower()
    if lk ~= "content-length" and lk ~= "transfer-encoding" and lk ~= "content-encoding" and lk ~= "connection" then
      out[k] = v
    end
  end
  for k, v in pairs(kong.ctx.plugin.out_headers or {}) do
    if kong.ctx.plugin.expose then out[k] = v end
  end
  return kong.response.exit(status, body, out)
end

function Plugin:response(conf)
  local ctx = kong.ctx.plugin
  if not conf.evaluate_output or ctx.output_skip then return end

  local status = kong.service.response.get_status()
  if not status or status < 200 or status > 299 then return end   -- provider errors pass through
  local headers = kong.service.response.get_headers() or {}
  local raw = kong.service.response.get_raw_body()
  if not raw or raw == "" then return end
  local enc = headers["Content-Encoding"] or headers["content-encoding"]
  if type(enc) == "table" then enc = enc[1] end
  if enc and enc:lower() == "gzip" then
    local inflated = require("kong.tools.gzip").inflate_gzip(raw)
    if not inflated then
      if failure(conf, "output", "gzip_decode_failed") then return end
      return
    end
    raw = inflated
  elseif enc and enc ~= "" and enc:lower() ~= "identity" then
    if failure(conf, "output", "unsupported_content_encoding_" .. enc) then return end
    return
  end
  if #raw > conf.max_body_bytes then
    if failure(conf, "output", "oversize") then return end
    return
  end

  local ctype = headers["Content-Type"] or headers["content-type"] or ""
  if type(ctype) == "table" then ctype = ctype[1] end
  ctype = ctype:lower()
  local is_sse = ctype:find("text/event-stream", 1, true) ~= nil
  local protocol = ctx.protocol or "llm"

  local payload, writer
  if is_sse then
    local events = sse_events(raw)
    if protocol == "mcp" then
      -- MCP streamable HTTP may answer a POST with an SSE stream carrying the JSON-RPC response.
      local msg = first_jsonrpc(events)
      if not msg or msg.result == nil then return end
      payload = msg
      writer = function(tp)
        if not (is_object(tp) and tp.jsonrpc == "2.0" and tp.result ~= nil) then return nil end
        return "event: message\ndata: " .. cjson.encode(tp) .. "\n\n"
      end
    else
      local text, calls = sse_completion(events)
      if text == "" and #calls == 0 then return end
      local m = { role = "assistant", content = text }
      if #calls > 0 then m.tool_calls = calls end
      payload = { messages = { m } }
      writer = function() return nil end   -- a stream cannot be rewritten safely
    end
  else
    local body = cjson.decode(raw)
    if not is_object(body) then return end
    if protocol == "mcp" or body.jsonrpc == "2.0" then
      protocol = "mcp"
      if body.result == nil then return end    -- JSON-RPC error: nothing to evaluate
      payload = body
      writer = function(tp)
        if not (is_object(tp) and tp.jsonrpc == "2.0" and tp.result ~= nil) then return nil end
        return cjson.encode(tp)
      end
    else
      local texts, calls = extract_completion(body)
      if #texts == 0 and #calls == 0 then return end
      local parts = {}
      for _, t in ipairs(texts) do parts[#parts + 1] = t.holder[t.key] end
      local m = { role = "assistant", content = table.concat(parts, "\n") }
      if #calls > 0 then m.tool_calls = calls end
      -- A raw provider response is rejected with 400; it must be sent as an assistant message.
      payload = { messages = { m } }
      writer = function(tp)
        local msg = is_object(tp) and is_array(tp.messages) and tp.messages[1]
        if type(msg) ~= "table" or type(msg.content) ~= "string" or #texts ~= 1 then return nil end
        -- Masked tool-call arguments cannot be written back safely across formats.
        if is_array(msg.tool_calls) then
          for i, tc in ipairs(msg.tool_calls) do
            local o = calls[i] and calls[i]["function"] and calls[i]["function"].arguments
            local n = type(tc) == "table" and tc["function"] and tc["function"].arguments
            if o ~= n then return nil end
          end
        end
        texts[1].holder[texts[1].key] = msg.content
        return cjson.encode(body)
      end
    end
  end

  local r, ferr, retry = evaluate(conf, build_request(conf, "output", protocol, payload, ctx.model))
  if not r then
    if failure(conf, "output", ferr, retry) then return end
    return
  end
  record("output", r)
  local action = decide(conf, "output", r)
  if action == "block" then
    return deny(conf, conf.block_status, conf.block_message, nil, r.trace_id, "trustguard_block")
  elseif action == "mask" then
    local new = writer(r.transformed_payload)
    if new then
      set_out_header("X-TrustGuard-Output-Masked", "true")
      return write_response(status, new, headers)
    elseif conf.transform_fallback == "block" then
      return deny(conf, conf.block_status, conf.block_message, nil, r.trace_id, "trustguard_block")
    end
  end
  -- allowed: Kong sends the buffered upstream response unchanged.
end

return Plugin
