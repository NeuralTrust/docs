/*
 * JS-TrustGuard-BuildRequest
 * Decides whether this message is evaluated and builds the /v1/evaluate body.
 *
 * Inputs (flow variables):
 *   trustguard.direction      "input" | "output"  (FlowCallout <Parameter>; optional, else derived from context.flow)
 *   trustguard.consumer_id    caller (developer app / client_id); falls back to developer.app.name, client_id
 *   trustguard.user.id        end user id from the verified token (sub / oid)
 *   trustguard.user.email     end user email from the verified token
 *   trustguard.session_id     conversation id; falls back to header X-Session-Id, then messageid
 * Config (environment property set "trustguard"): see env-config/trustguard.properties
 *
 * Outputs:
 *   trustguard.skip           "true" when nothing is sent to TrustGuard
 *   trustguard.skip_reason
 *   trustguard.evaluate.body  JSON string for the AssignMessage policy
 *   trustguard.action         "allow" | "reject_stream" (set here) ; ApplyVerdict sets the rest
 */
var LLM_ROOTS = ['input', 'messages', 'system', 'contents', 'systemInstruction', 'tools'];

function hasLlmRoot(b) {
  for (var i = 0; i < LLM_ROOTS.length; i++) {
    if (b[LLM_ROOTS[i]] !== undefined && b[LLM_ROOTS[i]] !== null) { return true; }
  }
  return false;
}

function lastUserText(b) {
  // Minimal mode: the latest user message only (loses system prompt, history and tool results).
  if (typeof b.input === 'string') { return b.input; }
  var list = b.messages || b.contents || (b.input instanceof Array ? b.input : null);
  if (!(list instanceof Array)) { return ''; }
  for (var i = list.length - 1; i >= 0; i--) {
    var m = list[i];
    if (m && m.role === 'user') {
      if (m.parts instanceof Array) { return textOf(m.parts); }
      return textOf(m.content);
    }
  }
  return '';
}

function skip(reason) {
  tgSet('trustguard.skip', 'true');
  tgSet('trustguard.skip_reason', reason);
}

function main() {
  // Reset per-call state (flow variables live for the whole transaction, so the
  // response-side call must not see the request-side values).
  tgSet('trustguard.skip', 'false');
  tgSet('trustguard.skip_reason', '');
  tgSet('trustguard.action', 'allow');
  tgSet('trustguard.failure', 'false');
  tgSet('trustguard.failure_reason', '');
  tgSet('trustguard.status', '');
  tgSet('trustguard.trace_id', '');
  tgSet('trustguard.evaluate.body', '');

  var direction = tgStr('trustguard.direction');
  var dirSource = 'parameter';
  if (direction !== 'input' && direction !== 'output') {
    // Flow hooks pass no parameter. Prefer context.flow (TARGET_REQ_FLOW / TARGET_RESP_FLOW);
    // if the runtime reports something else inside a hooked shared flow, fall back to whether
    // a target response exists yet. trustguard.direction_source shows which rule applied (Debug).
    var flow = String(context.flow || '');
    tgSet('trustguard.context_flow', flow);
    if (flow.indexOf('RESP') >= 0) { direction = 'output'; dirSource = 'flow'; }
    else if (flow.indexOf('REQ') >= 0) { direction = 'input'; dirSource = 'flow'; }
    else { direction = tgStr('response.status.code') !== '' ? 'output' : 'input'; dirSource = 'response_status'; }
  }
  tgSet('trustguard.direction', direction);
  tgSet('trustguard.direction_source', dirSource);

  if (tgProp('enabled', 'true') !== 'true') { return skip('disabled'); }
  // Each direction is evaluated once per transaction, so a proxy that has its own FlowCallouts
  // and also sits under the environment flow hooks is not evaluated (or billed) twice.
  if (tgStr('trustguard.' + direction + '.evaluated') === 'true') { return skip('already_evaluated'); }
  if (!tgInList(tgProp('proxies', '*'), tgStr('apiproxy.name'))) { return skip('proxy_not_enrolled'); }
  if (direction === 'output' && tgProp('evaluate_output', 'true') !== 'true') { return skip('output_disabled'); }

  var msg = direction === 'input' ? 'request' : 'response';
  var ctype = tgStr(msg + '.header.content-type').toLowerCase();

  if (direction === 'output') {
    var code = parseInt(tgStr('response.status.code'), 10);
    if (!(code >= 200 && code < 300)) { return skip('backend_status_' + code); }
    if (ctype.indexOf('text/event-stream') >= 0) {
      // Apigee cannot run a ServiceCallout in an EventFlow; a streamed completion is not evaluated.
      tgSet('trustguard.output.unevaluated', 'stream');
      return skip('streamed_response');
    }
  } else {
    var verb = tgStr('request.verb').toUpperCase();
    if (verb !== 'POST' && verb !== 'PUT' && verb !== 'PATCH') { return skip('no_body_verb'); }
  }

  var raw = tgStr(msg + '.content');
  if (raw === '') { return skip('empty_body'); }
  if (ctype !== '' && ctype.indexOf('json') < 0) { return skip('not_json'); }
  var body = tgParse(raw);
  if (!tgIsObject(body)) { return skip('not_json_object'); }   // JSON-RPC batches (arrays) are not supported by /v1/evaluate

  var maxBytes = parseInt(tgProp('max_body_bytes', '9437184'), 10);
  if (raw.length > maxBytes) {
    skip('oversize');
    return failure('oversize');            // TrustGuard would reject it (10 MiB default): apply fail_mode
  }

  // Protocol: MCP JSON-RPC or LLM provider body.
  var protocol = tgProp('protocol', 'auto');
  if (protocol === 'auto') { protocol = body.jsonrpc === '2.0' ? 'mcp' : 'llm'; }

  if (direction === 'input' && protocol === 'llm' && body.stream === true) {
    tgSet('trustguard.request.streaming', 'true');
    if (tgProp('stream_policy', 'allow') === 'reject') {
      tgSet('trustguard.action', 'reject_stream');
      return skip('stream_rejected');
    }
  }

  var payload;
  if (protocol === 'mcp') {
    if (body.jsonrpc !== '2.0') { return skip('not_jsonrpc'); }
    if (direction === 'output' && body.result === undefined) { return skip('jsonrpc_error_or_empty'); }
    if (direction === 'input' && body.method === undefined) { return skip('jsonrpc_no_method'); }
    payload = body;   // sent unchanged: tools/call -> params.name / params.arguments, tools/list result, tool result
  } else if (direction === 'input') {
    if (!hasLlmRoot(body)) { return skip('not_llm_body'); }  // protects non-LLM APIs behind an environment flow hook
    if (tgProp('payload_mode', 'full') === 'minimal') {
      payload = { input: lastUserText(body) };
    } else {
      payload = body;  // full provider body: system prompt, history, tools and tool results are all evaluated
    }
  } else {
    var c = extractCompletion(body);
    var text = [];
    for (var i = 0; i < c.texts.length; i++) { text.push(c.texts[i].holder[c.texts[i].key]); }
    if (text.length === 0 && c.toolCalls.length === 0) { return skip('no_completion_text'); }
    var assistant = { role: 'assistant', content: text.join('\n') };
    if (c.toolCalls.length > 0) { assistant.tool_calls = c.toolCalls; }
    payload = { messages: [assistant] };
    tgSet('trustguard.output.text_locations', String(c.texts.length));
  }

  // protocol is always sent: an omitted value resolves to llm server-side, which rejects JSON-RPC bodies.
  // Never add gateway_id (403 with a collector key) or application_id (400 on /v1).
  var req = { protocol: protocol, direction: direction, payload: payload };

  var session = tgFirst('trustguard.session_id', 'request.header.x-session-id', 'messageid');
  tgSet('trustguard.session_id', session);
  req.session_id = session;

  var consumer = tgFirst('trustguard.consumer_id', 'developer.app.name', 'client_id');
  if (consumer !== '') { req.consumer_id = consumer; }

  var attrs = {};
  var uid = tgStr('trustguard.user.id');
  var uemail = tgStr('trustguard.user.email');
  if (uid !== '' || uemail !== '') {
    attrs.user = {};
    if (uid !== '') { attrs.user.id = uid; }
    if (uemail !== '') { attrs.user.email = uemail; }
  }
  attrs.source = { application: tgStr('apiproxy.name') };
  var model = (direction === 'input') ? body.model : tgStr('trustguard.model.name');
  if (typeof model === 'string' && model !== '') {
    attrs.model = { name: model };
    var provider = tgProp('model_provider', '');
    if (provider !== '') { attrs.model.provider = provider; }
    tgSet('trustguard.model.name', model);
  }
  var consumerName = tgStr('trustguard.consumer_name');
  if (consumerName !== '') { attrs.consumer = { name: consumerName }; }
  req.attributes = attrs;

  tgSet('trustguard.protocol', protocol);
  tgSet('trustguard.evaluate.body', JSON.stringify(req));
  if (tgProp('host', '') === '') { skip('no_host'); return failure('not_configured'); }
  if (tgStr('private.trustguard.api_key') === '') { skip('no_api_key'); return failure('not_configured'); }
  tgSet('trustguard.' + direction + '.evaluated', 'true');
}

try {
  main();
} catch (e) {
  // Never let a script error silently skip enforcement: hand it to fail_mode.
  tgSet('trustguard.error', String(e));
  skip('script_error');
  failure('script_error');
}
// When nothing is sent, ApplyVerdict does not run: clear the direction here so it
// does not leak into the response-side call of this transaction.
if (tgStr('trustguard.skip') === 'true') { context.removeVariable('trustguard.direction'); }
