import json
import httpx
import pytest
from sheetpilot.models import Ping
from sheetpilot.provider import MetaError, MetaProvider


def test_provider_contract_is_official_and_structured():
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"choices":[{"finish_reason":"stop","message":{"content":'{"ok":true}'}}]})
    p = MetaProvider("test-secret", transport=httpx.MockTransport(handle))
    assert p.structured([{"role":"user","content":"ping"}], Ping).ok
    payload = json.loads(requests[0].content)
    assert str(requests[0].url) == "https://api.meta.ai/v1/chat/completions"
    assert payload["model"] == "muse-spark-1.3"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert requests[0].headers["authorization"] == "Bearer test-secret"


@pytest.mark.parametrize("payload", [
    {"choices":[{"finish_reason":"stop","message":{"content":'{"wrong":1}'}}]},
    {"choices":[{"finish_reason":"length","message":{"content":'{"ok":true}'}}]},
    {"choices":[]},
])
def test_invalid_ai_output_is_rejected(payload):
    p = MetaProvider("x", transport=httpx.MockTransport(lambda r: httpx.Response(200,json=payload)))
    with pytest.raises(MetaError):
        p.structured([], Ping)


def test_missing_key_makes_no_network_call():
    p = MetaProvider("", transport=httpx.MockTransport(lambda r: pytest.fail("Network called")))
    assert p.status()["configured"] is False
    with pytest.raises(MetaError, match="not configured"):
        p.verify()


def test_provider_errors_hide_secrets():
    p = MetaProvider("secret", transport=httpx.MockTransport(lambda r: httpx.Response(401,text="secret raw body")))
    with pytest.raises(MetaError) as exc:
        p.verify()
    assert "secret" not in str(exc.value)


def test_truncated_output_retries_once_without_replaying_partial_content(caplog):
    requests = []
    messages = [{"role": "user", "content": "ping"}]
    def handle(request):
        requests.append(json.loads(request.content))
        message = {"content": 'private partial output'} if len(requests) == 1 else {"content": '{"ok":true}'}
        reason = "length" if len(requests) == 1 else "stop"
        return httpx.Response(200, json={"choices": [{"finish_reason": reason, "message": message}]})
    p = MetaProvider("test-secret", transport=httpx.MockTransport(handle))
    assert p.structured(messages, Ping).ok
    assert [r["max_completion_tokens"] for r in requests] == [8192, 16384]
    assert all(r["messages"] == messages and r["reasoning_effort"] == "medium" for r in requests)
    assert requests[0]["response_format"] == requests[1]["response_format"]
    assert "private partial output" not in caplog.text and "test-secret" not in caplog.text


def test_repeated_truncation_stops_after_one_retry_even_for_valid_json():
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": '{"ok":true}'}}]})
    p = MetaProvider("x", transport=httpx.MockTransport(handle))
    with pytest.raises(MetaError, match="response limit") as exc:
        p.structured([], Ping)
    assert len(requests) == 2
    assert exc.value.output_error is False  # Schema repair must not restart the exhausted token retry.


@pytest.mark.parametrize("reason", ["content_filter", None, "unexpected"])
def test_other_incomplete_finish_reasons_are_not_retried(reason):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"finish_reason": reason, "message": {"content": "private output"}}]})
    p = MetaProvider("x", transport=httpx.MockTransport(handle))
    with pytest.raises(MetaError) as exc:
        p.structured([], Ping)
    assert len(requests) == 1 and exc.value.output_error is False
    assert "private output" not in str(exc.value)


def test_auth_failure_after_truncation_does_not_trigger_more_output_retries():
    requests = []
    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]})
        return httpx.Response(401, text="private provider error")
    p = MetaProvider("x", transport=httpx.MockTransport(handle))
    with pytest.raises(MetaError, match="rejected the API key"):
        p.structured([], Ping)
    assert len(requests) == 2


def test_truncated_tool_calls_are_discarded_before_retrying():
    requests = []
    tools = [{"type": "function", "function": {"name": "sales", "parameters": {"type": "object", "properties": {}}}}]
    complete = {"role": "assistant", "content": None, "tool_calls": [{"id": "complete-call", "type": "function",
        "function": {"name": "sales", "arguments": "{}"}}]}
    def handle(request):
        requests.append(json.loads(request.content))
        message = {"tool_calls": [{"id": "partial-call", "function": {"arguments": "{"}}]} if len(requests) == 1 else complete
        return httpx.Response(200, json={"choices": [{"finish_reason": "length" if len(requests) == 1 else "tool_calls", "message": message}]})
    p = MetaProvider("x", transport=httpx.MockTransport(handle))
    assert p.completion([], tools=tools) == complete
    assert len(requests) == 2 and all(r["tools"] == tools and r["parallel_tool_calls"] is False for r in requests)


@pytest.mark.parametrize("message", [None, "not a message", []])
def test_malformed_completion_message_is_rejected(message):
    p = MetaProvider("x", transport=httpx.MockTransport(lambda r: httpx.Response(200,
        json={"choices": [{"finish_reason": "stop", "message": message}]})))
    with pytest.raises(MetaError, match="unexpected response format"):
        p.completion([])
