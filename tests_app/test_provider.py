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
