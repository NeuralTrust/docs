/*
 * JS-TrustGuard-ApplyVerdict
 * Reads the ServiceCallout response, applies fail_mode and the verdict.
 * /v1/evaluate answers 200 for every evaluation, including "block": the decision
 * is always read from the body, never from the HTTP status.
 *
 * Sets trustguard.action to one of:
 *   allow | block | fail_closed
 * and, when masking is enabled and a transform verdict arrives, rewrites
 * request.content (input) or response.content (output).
 */
var SC_NAME = 'SC-TrustGuard-Evaluate';
var RESP = 'trustguard.evaluateResponse';

// UTF-8 byte length (Rhino strings are UTF-16).
function utf8Len(str) {
  return unescape(encodeURIComponent(str)).length;
}

// Writes a new body and keeps Content-Length consistent when the message carries one.
// Apigee normally recalculates it; setting the correct value explicitly is harmless and
// protects targets that reject a mismatched length (chunked messages have no header).
function setBody(msg, str) {
  context.setVariable(msg + '.content', str);
  if (tgStr(msg + '.header.content-length') !== '') {
    context.setVariable(msg + '.header.content-length', String(utf8Len(str)));
  }
}

function maskRequest(tp) {
  // Input: verified for OpenAI Chat (string and parts content, tool_calls,
  // tool results), OpenAI Responses (string and input_text parts), Anthropic (string and
  // blocks), Gemini, and MCP tools/call: transformed_payload is the SAME body with only the
  // matched substrings replaced by [MASKED_*]; every other key, type and null is preserved.
  // So it is forwardable as-is. Caveat: integers above 2^53 (e.g. a 20-digit seed) lose
  // precision, both in TrustGuard and in Rhino.
  if (!tgIsObject(tp)) { return false; }
  var mcp = tgStr('trustguard.protocol') === 'mcp';
  if (mcp) {
    if (tp.jsonrpc !== '2.0') { return false; }
  } else if (tgProp('payload_mode', 'full') !== 'full') {
    return false;   // minimal mode sent only {input}: nothing to forward
  }
  setBody('request', JSON.stringify(tp));
  return true;
}

function maskResponse(tp) {
  if (!tgIsObject(tp)) { return false; }
  // MCP output: we sent the JSON-RPC response unchanged, and transformed_payload is that
  // response masked in place (result.content[].text, structuredContent, ...), verified live.
  if (tgStr('trustguard.protocol') === 'mcp') {
    if (tp.jsonrpc !== '2.0' || tp.result === undefined) { return false; }
    setBody('response', JSON.stringify(tp));
    return true;
  }
  // LLM output: we sent {messages:[{role:'assistant', content, tool_calls?}]}, so the masked
  // text has to be written back into the provider response. Only done when the completion
  // came from exactly one text location (the common single-choice case).
  var msg = tp.messages && tp.messages[0];
  if (!msg || typeof msg.content !== 'string') { return false; }
  var body = tgParse(tgStr('response.content'));
  if (!tgIsObject(body)) { return false; }
  var c = extractCompletion(body);
  // Masked tool-call arguments cannot be written back safely across provider formats:
  // report "not masked" so transform_fallback decides.
  var tcs = msg.tool_calls instanceof Array ? msg.tool_calls : [];
  for (var i = 0; i < tcs.length; i++) {
    var orig = c.toolCalls[i] && c.toolCalls[i]['function'] && c.toolCalls[i]['function'].arguments;
    var now = tcs[i] && tcs[i]['function'] && tcs[i]['function'].arguments;
    if (orig !== now) { return false; }
  }
  if (c.texts.length === 0 && msg.content === '') { return false; }
  if (c.texts.length !== 1 || tgStr('trustguard.output.text_locations') !== '1') { return false; }
  c.texts[0].holder[c.texts[0].key] = msg.content;
  setBody('response', JSON.stringify(body));
  return true;
}

function main() {
  var direction = tgStr('trustguard.direction');
  var failed = tgStr('servicecallout.' + SC_NAME + '.failed') === 'true';
  var code = parseInt(tgStr(RESP + '.status.code'), 10);
  var text = tgStr(RESP + '.content');
  tgSet('trustguard.' + direction + '.http_status', isNaN(code) ? '' : String(code));

  if (isNaN(code)) { return failure(failed ? 'callout_failed' : 'no_response'); }   // timeout, DNS, TLS, connection
  if (code === 429) {
    // Plan burst limit or monthly quota (verified live: burst limit 100, Retry-After ~15 s,
    // X-RateLimit-Reason burst). Pass TrustGuard's Retry-After through to the client.
    var ra = parseInt(tgStr(RESP + '.header.Retry-After'), 10);
    if (!isNaN(ra) && ra >= 0) { tgSet('trustguard.retry_after', String(ra)); }
    var rr = tgParse(text);
    return failure('rate_limited' + (tgIsObject(rr) && typeof rr.reason === 'string' ? '_' + rr.reason : ''));
  }
  if (code < 200 || code > 299) { return failure('http_' + code); }                // 400/401/402/403/413/5xx

  var r = tgParse(text);
  if (!tgIsObject(r) || typeof r.status !== 'string') { return failure('bad_response'); }

  var status = r.status;
  tgSet('trustguard.status', status);
  tgSet('trustguard.trace_id', r.trace_id || '');
  tgSet('trustguard.' + direction + '.status', status);
  tgSet('trustguard.' + direction + '.trace_id', r.trace_id || '');

  tgSet('trustguard.blocked_side', direction === 'input' ? 'request' : 'response');
  if (status === 'block') {
    tgSet('trustguard.action', 'block');
    return;
  }
  if (status === 'transform') {
    var done = false;
    if (direction === 'input' && tgProp('mask_request', 'false') === 'true') {
      done = maskRequest(r.transformed_payload);
    } else if (direction === 'output' && tgProp('mask_response', 'false') === 'true') {
      done = maskResponse(r.transformed_payload);
    }
    tgSet('trustguard.' + direction + '.masked', done ? 'true' : 'false');
    if (!done && tgProp('transform_fallback', 'forward') === 'block') {
      tgSet('trustguard.action', 'block');
      return;
    }
    tgSet('trustguard.action', 'allow');
    return;
  }
  if (status === 'ask' && tgProp('ask_policy', 'forward') === 'block') {
    tgSet('trustguard.action', 'block');
    return;
  }
  tgSet('trustguard.action', 'allow');   // allow, report, skip, ask(forward)
}

try {
  main();
} catch (e) {
  tgSet('trustguard.error', String(e));
  failure('script_error');
}
// The direction must not leak into the next call of this transaction (response side).
context.removeVariable('trustguard.direction');
