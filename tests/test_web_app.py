from types import SimpleNamespace

from profit_agent_demo.web_app import AgentRunResult, build_agent_messages, render_analysis_result, request_completion, run_agent


class RateLimitFailure(Exception):
    status_code = 429


class TransientServerFailure(Exception):
    status_code = 500


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


class RenderProbe:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


def test_ui_renders_bar_and_stacked_bar_without_text_chart_fallback():
    rows = [
        {"period": "2026-07-01", "brand_name": "솔담건강", "payment_amount": 100},
        {"period": "2026-07-02", "brand_name": "솔담건강", "payment_amount": 120},
    ]
    for kind, expected_renderer in (("bar", "bar_chart"), ("stacked_bar", "altair_chart")):
        ui = RenderProbe()
        render_analysis_result(ui, "get_profit_trend", {
            "period": {"start_date": "2026-07-01", "end_date": "2026-07-02"},
            "group_by": ["brand_name"], "metrics": ["payment_amount"], "rows": rows,
            "chart": {"kind": kind, "title": "테스트", "x_column": "period",
                        "series_column": "brand_name", "value_column": "payment_amount"},
        })
        assert any(call[0] == expected_renderer for call in ui.calls)
        assert not any(call[0] == "markdown" for call in ui.calls)


def test_build_agent_messages_includes_readonly_analysis_contract():
    messages = build_agent_messages([{"role": "user", "content": "브랜드별 광고비를 비교해 주세요"}])

    assert messages[0]["role"] == "system"
    assert "임의 SQL" in messages[0]["content"]
    assert "2026-07-31" in messages[0]["content"]
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


def test_transient_provider_500_retries_before_failing():
    client = FakeClient()
    client.completions.create = lambda **kwargs: "completed"
    calls = {"count": 0}

    def create(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TransientServerFailure("temporary provider failure")
        return "completed"

    client.completions.create = create
    waits = []
    result = request_completion(
        client, api_type="nvidia", sleep=lambda seconds: waits.append(seconds),
        model="nvidia/test-model", messages=[], tools=[],
    )

    assert result == "completed"
    assert calls["count"] == 2
    assert waits == [5]


class ToolCallingCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            call = SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(
                    name="get_profit_summary",
                    arguments='{"start_date":"2026-01-01","end_date":"2026-07-31"}',
                ),
            )
            message = SimpleNamespace(content=None, tool_calls=[call])
        else:
            message = SimpleNamespace(content="분석 결과입니다.", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ToolCallingClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=ToolCallingCompletions())


class FakeAnalyticsService:
    def call_tool(self, name, arguments):
        assert name == "get_profit_summary"
        assert arguments["start_date"] == "2026-01-01"
        return {"rows": [{"brand_name": "솔담건강", "payment_amount": 100000}]}


def test_run_agent_returns_last_successful_tool_result_for_visualization():
    result = run_agent(
        [{"role": "user", "content": "분석해 주세요"}],
        FakeAnalyticsService(),
        ToolCallingClient(),
        "test-model",
        SimpleNamespace(api_type="openai"),
    )

    assert isinstance(result, AgentRunResult)
    assert result.answer == "분석 결과입니다."
    assert result.tool_name == "get_profit_summary"
    assert result.tool_result == {"rows": [{"brand_name": "솔담건강", "payment_amount": 100000}]}


class ChartAnalyticsService(FakeAnalyticsService):
    def call_tool(self, name, arguments):
        return {
            "rows": [
                {"period": "2026-07-01", "product_name": "상품 A", "payment_amount": 100000},
                {"period": "2026-07-02", "product_name": "상품 A", "payment_amount": 120000},
            ],
            "chart": {
                "kind": "line",
                "title": "일별 상위 상품 결제금액",
                "x_column": "period",
                "series_column": "product_name",
                "value_column": "payment_amount",
            },
        }


def test_run_agent_skips_second_model_call_when_a_chart_result_is_ready():
    client = ToolCallingClient()

    result = run_agent(
        [{"role": "user", "content": "상위 상품 그래프를 보여 주세요"}],
        ChartAnalyticsService(),
        client,
        "test-model",
        SimpleNamespace(api_type="openai"),
    )

    assert result.answer == ""
    assert result.tool_name == "get_profit_summary"
    assert client.chat.completions.calls == 1


def test_run_agent_reports_model_and_data_query_progress():
    statuses = []

    run_agent(
        [{"role": "user", "content": "분석해 주세요"}],
        FakeAnalyticsService(),
        ToolCallingClient(),
        "test-model",
        SimpleNamespace(api_type="openai"),
        on_status=statuses.append,
    )

    assert "분석 요청을 해석하는 중" in statuses
    assert "안전한 데이터 조회 중: get_profit_summary" in statuses
    assert "조회 완료, 응답을 정리하는 중" in statuses
