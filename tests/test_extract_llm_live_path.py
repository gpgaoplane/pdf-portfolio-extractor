import json
import respx
import httpx
from portfolio_extract.extract_llm import extract_with_llm

BASE = "https://mock.example/v1"

def _completion(content: dict) -> dict:
    return {
        "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": "mock-model",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": json.dumps(content)}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }

@respx.mock
def test_extract_with_llm_parses_mocked_response(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", BASE)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODE", "JSON")
    monkeypatch.setenv("LLM_MODEL", "mock-model")
    payload = {
        "company_name": "NovaCloud Analytics Inc.", "sector": "SaaS",
        "period_year": 2025, "period_quarter": "Q2", "currency": "USD",
        "metrics": [{"metric": "revenue_quarterly", "raw_text": "$8.4M",
                     "label_as_reported": "Recognized Revenue", "source_page": 1,
                     "source_snippet": "Recognized Revenue $8.4M"}],
    }
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion(payload)))

    out = extract_with_llm(["[page 1]\nRecognized Revenue $8.4M"])

    assert out.company_name == "NovaCloud Analytics Inc."
    assert out.metrics[0].metric == "revenue_quarterly"
    assert out.metrics[0].raw_text == "$8.4M"
