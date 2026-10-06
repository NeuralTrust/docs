from __future__ import annotations

import importlib.util
import json
import time
import tempfile
import unittest
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import httpx
import jwt
from fastapi import HTTPException
from litellm import ModelResponse, ModelResponseStream
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.llms.openai.chat.guardrail_translation.handler import OpenAIChatCompletionsHandler
from litellm.proxy._types import UserAPIKeyAuth

DOC: Final = Path(__file__).resolve().parents[1] / 'integrations' / 'litellm.mdx'
CODE: Final = DOC.read_text().split('```python\n', 1)[1].split('\n```', 1)[0]
with tempfile.TemporaryDirectory() as directory:
    path: Final = Path(directory) / 'trustguard_guardrail.py'
    path.write_text(CODE)
    spec: Final = importlib.util.spec_from_file_location('documented_guardrail', path)
    module: Final = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

EMAIL: Final = 'alice.review@example.com'
AUTH: Final = UserAPIKeyAuth(request_route='/v1/chat/completions')


def transform(request: httpx.Request) -> httpx.Response:
    body: Final = json.loads(request.content)
    payload: Final = json.loads(json.dumps(body['payload']).replace(EMAIL, '[EMAIL]'))
    return httpx.Response(200, json={'status': 'transform', 'transformed_payload': payload})


def block(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={'status': 'block'})


async def stream(*deltas: dict[str, object]) -> AsyncIterator[ModelResponseStream]:
    for delta in deltas:
        yield ModelResponseStream(id='completion-test', model='test-model', choices=[{'index': 0, 'delta': delta}])
    yield ModelResponseStream(
        id='completion-test', model='test-model', choices=[{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]
    )


def guard(client: httpx.AsyncClient) -> CustomGuardrail:
    return module.TrustGuard(
        api_base='https://guard.test', api_key='test', http_client=client,
        streaming_transform_mode='incremental_diff', guardrail_name='test',
        event_hook=['pre_call', 'post_call'], default_on=True,
    )


OPENWEBUI_SECRET: Final = 'openwebui-test-secret'


def openwebui_token(secret: str = OPENWEBUI_SECRET, **claims: object) -> str:
    """The token Open WebUI forwards when FORWARD_USER_INFO_HEADER_JWT_SECRET is set."""
    now: Final = int(time.time())
    return jwt.encode({'sub': 'owui-1', 'email': 'ana@example.com', 'name': 'Ana', 'role': 'user',
                       'iss': 'open-webui', 'iat': now, 'exp': now + 300, **claims}, secret, algorithm='HS256')


async def evaluated(request_data: dict, **options: object) -> dict:
    """The /v1/evaluate body the guardrail sends for one request."""
    sent: Final = []

    def allow(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={'status': 'allow'})

    async with httpx.AsyncClient(transport=httpx.MockTransport(allow)) as client:
        connector: Final = module.TrustGuard(api_base='https://guard.test', api_key='test', http_client=client,
                                             guardrail_name='test', **options)
        await connector.apply_guardrail({'texts': ['hello']}, request_data, 'request')
    return sent[0]


def with_headers(**headers: str) -> dict:
    return {'proxy_server_request': {'headers': {name.replace('_', '-'): value for name, value in headers.items()}}}

class DocumentedGuardrailTests(unittest.IsolatedAsyncioTestCase):
    async def test_email_spanning_chunks_never_reaches_client(self) -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(transform)) as client:
            chunks: Final = [chunk async for chunk in guard(client).async_post_call_streaming_iterator_hook(
                AUTH, stream({'content': 'Contact alice.review@'}, {'content': 'example.com'}), {}
            )]
        self.assertEqual(''.join(choice.delta.content or '' for chunk in chunks for choice in chunk.choices),
                         'Contact [EMAIL]')
        self.assertEqual(chunks[-1].choices[0].finish_reason, 'stop')

    async def test_tool_block_never_releases_first_chunk(self) -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(block)) as client:
            iterator: Final = guard(client).async_post_call_streaming_iterator_hook(
                AUTH, stream({'tool_calls': [{'index': 0, 'id': 'call_test', 'type': 'function',
                                              'function': {'name': 'contact', 'arguments': '{"email":"' + EMAIL + '"}'}}]}), {}
            )
            with self.assertRaises(HTTPException) as error:
                await anext(iterator)
            self.assertEqual(error.exception.status_code, 400)

    async def test_tool_arguments_rewritten_in_stream_and_ordinary_response(self) -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(transform)) as client:
            connector: Final = guard(client)
            tool: Final = {'id': 'call_test', 'type': 'function',
                           'function': {'name': 'contact', 'arguments': '{"email":"' + EMAIL + '"}'}}
            ordinary: Final = ModelResponse(choices=[{'index': 0, 'message': {
                'role': 'assistant', 'content': None, 'tool_calls': [tool]}, 'finish_reason': 'tool_calls'}])
            rewritten: Final = await OpenAIChatCompletionsHandler().process_output_response(
                response=ordinary, guardrail_to_apply=connector, request_data={}, user_api_key_dict=AUTH
            )
            self.assertEqual(json.loads(rewritten.choices[0].message.tool_calls[0].function.arguments),
                             {'email': '[EMAIL]'})
            chunks: Final = [chunk async for chunk in connector.async_post_call_streaming_iterator_hook(
                AUTH, stream({'tool_calls': [{**tool, 'index': 0}]}), {}
            )]
            self.assertEqual(json.loads(chunks[0].choices[0].delta.tool_calls[0].function.arguments),
                             {'email': '[EMAIL]'})

    async def test_tool_result_transform_preserves_null_assistant_and_call_id(self) -> None:
        messages: Final = [
            {'role': 'user', 'content': 'Get contact'},
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call_test', 'type': 'function',
                                                                 'function': {'name': 'contact', 'arguments': '{}'}}]},
            {'role': 'tool', 'tool_call_id': 'call_test', 'content': 'Contact ' + EMAIL},
        ]
        async with httpx.AsyncClient(transport=httpx.MockTransport(transform)) as client:
            result: Final = await OpenAIChatCompletionsHandler().process_input_messages(
                data={'messages': messages}, guardrail_to_apply=guard(client)
            )
        self.assertIsNone(result['messages'][1]['content'])
        self.assertEqual(result['messages'][2]['tool_call_id'], result['messages'][1]['tool_calls'][0]['id'])
        self.assertEqual(result['messages'][2]['content'], 'Contact [EMAIL]')

    async def test_upstream_failure_releases_no_partial_output(self) -> None:
        async def interrupted() -> AsyncIterator[ModelResponseStream]:
            yield ModelResponseStream(choices=[{'index': 0, 'delta': {'content': EMAIL}}])
            raise RuntimeError('Upstream disconnected')

        async with httpx.AsyncClient(transport=httpx.MockTransport(transform)) as client:
            iterator: Final = guard(client).async_post_call_streaming_iterator_hook(AUTH, interrupted(), {})
            with self.assertRaisesRegex(RuntimeError, 'Upstream disconnected'):
                await anext(iterator)

    async def test_parallel_tool_calls_keep_indexes_finish_reason_and_usage(self) -> None:
        async def proposed() -> AsyncIterator[ModelResponseStream]:
            yield ModelResponseStream(id='completion-test', model='test-model', choices=[{
                'index': 0, 'delta': {'role': 'assistant', 'tool_calls': [
                    {'index': index, 'id': 'call_' + str(index), 'type': 'function',
                     'function': {'name': 'contact', 'arguments': '{"email":"' + EMAIL + '"}'}}
                    for index in range(2)
                ]}, 'finish_reason': 'tool_calls',
            }])
            yield ModelResponseStream(id='completion-test', model='test-model', choices=[],
                                      usage={'prompt_tokens': 7, 'completion_tokens': 11, 'total_tokens': 18})

        async with httpx.AsyncClient(transport=httpx.MockTransport(transform)) as client:
            chunks: Final = [chunk async for chunk in guard(client).async_post_call_streaming_iterator_hook(
                AUTH, proposed(), {}
            )]
        calls: Final = chunks[0].choices[0].delta.tool_calls
        self.assertEqual([call.index for call in calls], [0, 1])
        self.assertEqual([call.id for call in calls], ['call_0', 'call_1'])
        self.assertTrue(all(json.loads(call.function.arguments) == {'email': '[EMAIL]'} for call in calls))
        self.assertEqual(chunks[0].choices[0].finish_reason, 'tool_calls')
        self.assertEqual(chunks[0].usage.total_tokens, 18)

    async def test_transform_cannot_drop_tool_calls(self) -> None:
        inputs: Final = {'texts': [], 'tool_calls': [{'id': 'call_test', 'type': 'function',
                                                    'function': {'name': 'contact', 'arguments': '{}'}}]}
        with self.assertRaises(HTTPException) as error:
            module.TrustGuard._apply_transform(inputs, {'messages': [{'role': 'assistant', 'content': None}]}, 'response')
        self.assertEqual(error.exception.status_code, 400)


class EndUserAttributionTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_webui_headers_name_the_user(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-User-Id': 'owui-1',
                                                      'X-OpenWebUI-User-Email': 'ana@example.com'}))
        self.assertEqual(body['attributes'], {'user': {'id': 'owui-1', 'email': 'ana@example.com'}})

    async def test_open_webui_token_is_read_unverified_without_the_secret(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-User-Jwt': openwebui_token('any-secret')}))
        self.assertEqual(body['attributes'], {'user': {'id': 'owui-1', 'email': 'ana@example.com'}})

    async def test_a_token_open_webui_did_not_issue_is_ignored(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-User-Jwt': openwebui_token(iss='other')}))
        self.assertNotIn('attributes', body)

    async def test_litellm_end_user_names_the_user(self) -> None:
        body: Final = await evaluated({'metadata': {'user_api_key_end_user_id': 'maria@example.com'}})
        self.assertEqual(body['attributes'], {'user': {'id': 'maria@example.com'}})

    async def test_a_request_naming_nobody_sends_no_attributes(self) -> None:
        body: Final = await evaluated({})
        self.assertNotIn('attributes', body)

    async def test_values_are_capped(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-User-Id': 'a' * 300}))
        self.assertEqual(body['attributes'], {'user': {'id': 'a' * 256}})

    async def test_open_webui_chat_is_the_session_when_litellm_has_none(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-Chat-Id': 'chat-42'}))
        self.assertEqual(body['session_id'], 'chat-42')

    async def test_verified_mode_accepts_a_token_signed_with_the_secret(self) -> None:
        body: Final = await evaluated(with_headers(**{'X-OpenWebUI-User-Jwt': openwebui_token()}),
                                      openwebui_jwt_secret=OPENWEBUI_SECRET)
        self.assertEqual(body['attributes'], {'user': {'id': 'owui-1', 'email': 'ana@example.com'}})

    async def test_verified_mode_rejects_a_forged_or_expired_token(self) -> None:
        for token in (openwebui_token('attacker'), openwebui_token(exp=int(time.time()) - 60)):
            body = await evaluated(with_headers(**{'X-OpenWebUI-User-Jwt': token}),
                                   openwebui_jwt_secret=OPENWEBUI_SECRET)
            self.assertNotIn('attributes', body)

    async def test_verified_mode_ignores_unsigned_sources(self) -> None:
        request_data: Final = with_headers(**{'X-OpenWebUI-User-Email': 'boss@example.com'})
        request_data['metadata'] = {'user_api_key_end_user_id': 'boss@example.com'}
        body: Final = await evaluated(request_data, openwebui_jwt_secret=OPENWEBUI_SECRET)
        self.assertNotIn('attributes', body)


if __name__ == '__main__':
    unittest.main()
