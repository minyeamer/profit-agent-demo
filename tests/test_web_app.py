from profit_agent_demo.web_app import build_hermes_prompt


def test_hermes_prompt_requests_structured_profit_analysis():
    prompt = build_hermes_prompt([{"role": "user", "content": "브랜드별 광고비를 비교해 주세요"}])

    assert "profit-agent-demo" in prompt
    assert "임의 SQL" in prompt
    assert "브랜드별 광고비를 비교해 주세요" in prompt
    assert "MCP" in prompt
