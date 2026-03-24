import asyncio

import orjson

from app.services.grok.services.chat import CollectProcessor, StreamProcessor
from app.services.grok.services.responses import ResponsesService


def _json_line(payload: dict) -> bytes:
    return orjson.dumps(payload)


async def _iter_lines(lines):
    for line in lines:
        yield line


def _decode_sse_json(chunk: str) -> dict:
    assert chunk.startswith("data: ")
    return orjson.loads(chunk[6:])


class _FakeTokenManager:
    def __init__(self):
        self.refusals = []

    async def mark_upstream_refusal(
        self, token: str, reason: str, tag: str = "upstream_refused"
    ) -> bool:
        self.refusals.append(
            {
                "token": token,
                "reason": reason,
                "tag": tag,
            }
        )
        return True


def test_collect_processor_returns_estimated_usage(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        processor = CollectProcessor("grok-4", prompt_tokens=17)
        result = await processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "modelResponse": {
                                        "responseId": "resp_collect",
                                        "message": "你好，世界",
                                    },
                                }
                            }
                        }
                    )
                ]
            )
        )
        assert result["usage"]["prompt_tokens"] == 17
        assert result["usage"]["completion_tokens"] > 0
        assert (
            result["usage"]["total_tokens"]
            == result["usage"]["prompt_tokens"] + result["usage"]["completion_tokens"]
        )

    asyncio.run(_run())


def test_collect_processor_marks_refusal_token_and_preserves_content(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        token_mgr = _FakeTokenManager()
        refusal = (
            "I'm sorry, but I can't help with that. My purpose is to provide "
            "helpful and truthful answers, and I am not able to assist with "
            "requests that involve inappropriate content."
        )
        processor = CollectProcessor(
            "grok-4",
            token="tok_collect",
            prompt_tokens=17,
            token_mgr=token_mgr,
        )
        result = await processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "modelResponse": {
                                        "responseId": "resp_collect_refusal",
                                        "message": refusal,
                                    },
                                }
                            }
                        }
                    )
                ]
            )
        )

        assert result["choices"][0]["message"]["content"] == refusal
        assert token_mgr.refusals == [
            {
                "token": "tok_collect",
                "reason": "upstream_refusal:generic_refusal",
                "tag": "upstream_refused",
            }
        ]

    asyncio.run(_run())


def test_collect_processor_leaves_normal_content_unmarked(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        token_mgr = _FakeTokenManager()
        processor = CollectProcessor(
            "grok-4",
            token="tok_normal",
            prompt_tokens=17,
            token_mgr=token_mgr,
        )
        result = await processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "modelResponse": {
                                        "responseId": "resp_collect_normal",
                                        "message": "你好，世界",
                                    },
                                }
                            }
                        }
                    )
                ]
            )
        )

        assert result["choices"][0]["message"]["content"] == "你好，世界"
        assert token_mgr.refusals == []

    asyncio.run(_run())


def test_stream_processor_final_chunk_has_usage(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        processor = StreamProcessor("grok-4", prompt_tokens=11)
        chunks = []
        async for chunk in processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "responseId": "resp_stream",
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "token": "Hello",
                                }
                            }
                        }
                    ),
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "responseId": "resp_stream",
                                    "token": " world",
                                }
                            }
                        }
                    ),
                ]
            )
        ):
            chunks.append(chunk)

        assert chunks[-1] == "data: [DONE]\n\n"
        final_payload = _decode_sse_json(chunks[-2])
        assert final_payload["choices"][0]["finish_reason"] == "stop"
        assert final_payload["usage"]["prompt_tokens"] == 11
        assert final_payload["usage"]["completion_tokens"] > 0
        assert (
            final_payload["usage"]["total_tokens"]
            == final_payload["usage"]["prompt_tokens"]
            + final_payload["usage"]["completion_tokens"]
        )

    asyncio.run(_run())


def test_stream_processor_marks_refusal_token_and_preserves_chunks(monkeypatch):
    monkeypatch.setattr(
        "app.services.grok.services.chat.get_config",
        lambda key, default=None: 0 if key == "chat.stream_timeout" else [],
    )

    async def _run():
        token_mgr = _FakeTokenManager()
        refusal = "I'm sorry, but I can't help with that."
        processor = StreamProcessor(
            "grok-4",
            token="tok_stream",
            prompt_tokens=11,
            token_mgr=token_mgr,
        )
        chunks = []
        async for chunk in processor.process(
            _iter_lines(
                [
                    _json_line(
                        {
                            "result": {
                                "response": {
                                    "responseId": "resp_stream_refusal",
                                    "llmInfo": {"modelHash": "fp_test"},
                                    "token": refusal,
                                }
                            }
                        }
                    )
                ]
            )
        ):
            chunks.append(chunk)

        payloads = [
            _decode_sse_json(chunk)
            for chunk in chunks
            if chunk.startswith("data: {")
        ]
        visible_content = "".join(
            payload["choices"][0]["delta"].get("content", "")
            for payload in payloads
        )

        assert refusal in visible_content
        assert token_mgr.refusals == [
            {
                "token": "tok_stream",
                "reason": "upstream_refusal:generic_refusal",
                "tag": "upstream_refused",
            }
        ]

    asyncio.run(_run())


def test_responses_stream_completed_event_uses_chat_usage(monkeypatch):
    async def fake_chat_completions(**kwargs):
        async def _gen():
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{"role":"assistant","content":""},'
                '"logprobs":null,"finish_reason":null}]}\n\n'
            )
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{"content":"Hello"},'
                '"logprobs":null,"finish_reason":null}]}\n\n'
            )
            yield (
                'data: {"id":"chatcmpl_test","object":"chat.completion.chunk","created":1,'
                '"model":"grok-4","choices":[{"index":0,"delta":{},'
                '"logprobs":null,"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":13,"completion_tokens":5,"total_tokens":18,'
                '"prompt_tokens_details":{"cached_tokens":0,"text_tokens":13,"audio_tokens":0,"image_tokens":0},'
                '"completion_tokens_details":{"text_tokens":5,"audio_tokens":0,"reasoning_tokens":0}}}\n\n'
            )
            yield "data: [DONE]\n\n"

        return _gen()

    monkeypatch.setattr(
        "app.services.grok.services.responses.ChatService.completions",
        fake_chat_completions,
    )

    async def _run():
        stream = await ResponsesService.create(
            model="grok-4",
            input_value="hi",
            stream=True,
        )
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        completed_chunk = next(
            chunk for chunk in reversed(chunks) if "response.completed" in chunk
        )
        completed = orjson.loads(completed_chunk.split("data: ", 1)[1])
        usage = completed["response"]["usage"]
        assert usage["input_tokens"] == 13
        assert usage["output_tokens"] == 5
        assert usage["total_tokens"] == 18

    asyncio.run(_run())
