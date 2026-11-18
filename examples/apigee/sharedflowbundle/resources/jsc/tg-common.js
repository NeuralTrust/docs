/*
 * TrustGuard for Apigee - shared helpers (ES5, Apigee JavaScript policy / Rhino).
 * Loaded with <IncludeURL>jsc://tg-common.js</IncludeURL> before the main script.
 */
var TG_PROPS = 'propertyset.trustguard.';

function tgStr(name) {
  var v = context.getVariable(name);
  return (v === null || v === undefined) ? '' : String(v);
}

function tgProp(key, dflt) {
  var v = tgStr(TG_PROPS + key);
  return v === '' ? dflt : v.trim();
}

function tgFirst() {
  for (var i = 0; i < arguments.length; i++) {
    var v = tgStr(arguments[i]);
    if (v !== '') { return v; }
  }
  return '';
}

function tgSet(name, value) {
  context.setVariable(name, value === undefined || value === null ? '' : String(value));
}

function tgParse(text) {
  if (!text) { return null; }
  try { return JSON.parse(text); } catch (e) { return null; }
}

function tgIsObject(o) {
  return o !== null && typeof o === 'object' && !(o instanceof Array);
}

function tgInList(csv, value) {
  if (!csv || csv === '*') { return true; }
  var parts = csv.split(',');
  for (var i = 0; i < parts.length; i++) {
    if (parts[i].trim() === value) { return true; }
  }
  return false;
}

function textOf(c) {
  // String, or an array of content parts ({type:'text'|'output_text'|'input_text', text}).
  if (typeof c === 'string') { return c; }
  if (c instanceof Array) {
    var out = [];
    for (var i = 0; i < c.length; i++) {
      if (c[i] && typeof c[i].text === 'string') { out.push(c[i].text); }
    }
    return out.join('\n');
  }
  return '';
}

/*
 * Pull the assistant completion out of a provider response so it can be sent as
 * {messages:[{role:'assistant', content, tool_calls?}]}. Records where the text
 * came from so a masked value can be written back (optional response masking).
 */
function extractCompletion(r) {
  var texts = [];      // [{holder, key}] - locations of assistant text
  var toolCalls = [];
  var i, j, p;
  if (r.choices instanceof Array) {                         // OpenAI Chat Completions
    for (i = 0; i < r.choices.length; i++) {
      var m = r.choices[i] && r.choices[i].message;
      if (!m) { continue; }
      if (typeof m.content === 'string' && m.content !== '') { texts.push({ holder: m, key: 'content' }); }
      if (typeof m.refusal === 'string' && m.refusal !== '') { texts.push({ holder: m, key: 'refusal' }); }
      if (m.tool_calls instanceof Array) { toolCalls = toolCalls.concat(m.tool_calls); }
    }
  } else if (r.output instanceof Array) {                   // OpenAI Responses
    for (i = 0; i < r.output.length; i++) {
      var o = r.output[i];
      if (o && o.type === 'message' && o.content instanceof Array) {
        for (j = 0; j < o.content.length; j++) {
          p = o.content[j];
          if (p && p.type === 'output_text' && typeof p.text === 'string') { texts.push({ holder: p, key: 'text' }); }
        }
      } else if (o && o.type === 'function_call') {
        toolCalls.push({ id: o.call_id || o.id || ('call_' + i), type: 'function',
          'function': { name: o.name, arguments: typeof o.arguments === 'string' ? o.arguments : JSON.stringify(o.arguments || {}) } });
      }
    }
  } else if (r.content instanceof Array && r.type === 'message') { // Anthropic Messages
    for (i = 0; i < r.content.length; i++) {
      p = r.content[i];
      if (p && p.type === 'text' && typeof p.text === 'string') { texts.push({ holder: p, key: 'text' }); }
      if (p && p.type === 'tool_use') {
        toolCalls.push({ id: p.id, type: 'function', 'function': { name: p.name, arguments: JSON.stringify(p.input || {}) } });
      }
    }
  } else if (r.candidates instanceof Array) {               // Gemini
    for (i = 0; i < r.candidates.length; i++) {
      var parts = r.candidates[i] && r.candidates[i].content && r.candidates[i].content.parts;
      if (!(parts instanceof Array)) { continue; }
      for (j = 0; j < parts.length; j++) {
        p = parts[j];
        if (p && typeof p.text === 'string' && p.thought !== true) { texts.push({ holder: p, key: 'text' }); }
        if (p && p.functionCall) {
          toolCalls.push({ id: 'call_' + i + '_' + j, type: 'function',
            'function': { name: p.functionCall.name, arguments: JSON.stringify(p.functionCall.args || {}) } });
        }
      }
    }
  } else if (r.message && r.message.content instanceof Array) { // Cohere Chat v2
    for (i = 0; i < r.message.content.length; i++) {
      p = r.message.content[i];
      if (p && p.type === 'text' && typeof p.text === 'string') { texts.push({ holder: p, key: 'text' }); }
    }
  }
  return { texts: texts, toolCalls: toolCalls };
}


/* Applies fail_mode: closed (default) -> fail_closed (503), open -> allow and flag. */
function failure(reason) {
  tgSet('trustguard.failure', 'true');
  tgSet('trustguard.failure_reason', reason);
  if (tgStr('trustguard.retry_after') === '') { tgSet('trustguard.retry_after', '5'); }   // RF-TrustGuard-Unavailable Retry-After
  if (tgProp('fail_mode', 'closed') === 'open') {
    tgSet('trustguard.action', 'allow');
  } else {
    tgSet('trustguard.action', 'fail_closed');
  }
}

