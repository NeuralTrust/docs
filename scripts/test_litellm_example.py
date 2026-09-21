from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import httpx
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


if __name__ == '__main__':
    unittest.main()
