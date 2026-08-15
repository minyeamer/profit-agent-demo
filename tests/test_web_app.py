from types import SimpleNamespace

from profit_agent_demo.web_app import build_agent_messages, request_completion


class RateLimitFailure(Exception):
    status_code = 429


class FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RateLimitFailure("rate limited")
        return "completed"


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_build_agent_messages_includes_readonly_analysis_contract():
    messages = build_agent_messages([{"role": "user", "content": "브랜드별 광고비를 비교해 주세요"}])

    assert messages[0]["role"] == "system"
    assert "임의 SQL" in messages[0]["content"]
    assert messages[-1]["content"] == "브랜드별 광고비를 비교해 주세요"


def test_nvidia_rate_limit_waits_one_minute_before_retry():
    client = FakeClient()
    waits = []

    result = request_completion(
        client,
        api_type="nvidia",
        sleep=lambda seconds: waits.append(seconds),
        model="nvidia/test-model",
        messages=[{"role": "user", "content": "테스트"}],
        tools=[],
    )

    assert result == "completed"
    assert client.completions.calls == 2
    assert waits == [60]
