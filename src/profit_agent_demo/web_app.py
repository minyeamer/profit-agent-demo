import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st
from openai import OpenAI

from profit_agent_demo.config import load_settings
from profit_agent_demo.service import AnalyticsService, tool_definitions


SYSTEM_PROMPT = """당신은 실적 분석 데모 에이전트입니다.

profit_daily(start_date, end_date) 테이블 함수의 데이터를 분석합니다.
반드시 제공된 read-only 분석 도구만 사용하고 임의 SQL을 생성하거나 실행하지 마세요.
날짜가 없거나 연도가 불명확하면 먼저 확인하세요.
숫자 답변에는 조회 기간, 필터, 집계 기준, 단위를 표시하세요.
데이터에 없는 업무 의미를 추측하지 말고 불확실하면 질문하세요.

주요 회사 용어:
- extra_cost = 지출액, 추가비용, 비용, 고정지출
- sku_quantity = 확정수량
- unit_quantity = 세트수량
- supply_cost = 원가*수량
- supply_amount = 정산금액
- item_id/item_seq = 대표상품코드/순번
- category_name1~4 = 대분류/중분류/소분류/세분류
- shop_id/shop_group/shop_name = 판매처코드/쇼핑몰 그룹/채널

계산식:
- 마진금액 = 정산금액 - 원가*수량 - 배송비
- 영업이익 = 정산금액 - 원가*수량 - 배송비 - 광고비 - 지출액

예시 브랜드명은 공개 문서에만 사용되는 가상 값입니다. 실제 데이터의 브랜드 목록을 임의로 가정하지 마세요.
"""


def build_hermes_prompt(messages: list[dict[str, Any]]) -> str:
    conversation = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in messages[-12:]
        if message.get("content")
    )
    return f"""당신은 profit-agent-demo의 실적 분석 에이전트입니다.
현재 Hermes의 인증된 모델과 profit-agent-demo MCP 도구를 사용해 답변하세요.
반드시 MCP 분석 도구만 사용하고 임의 SQL을 생성하거나 실행하지 마세요.
조회 기간, 집계 기준, 필터, 단위를 답변에 포함하세요.
extra_cost는 지출액, sku_quantity는 확정수량, unit_quantity는 세트수량입니다.
item_id는 대표상품코드, product_id는 상품코드, shop_id는 판매처코드입니다.
마진금액 = 정산금액 - 원가*수량 - 배송비입니다.
영업이익 = 마진금액 - 광고비 - 지출액입니다.

대화:
{conversation}
"""


@st.cache_resource
def get_runtime() -> tuple[AnalyticsService, OpenAI | None, str, Any]:
    settings = load_settings()
    if settings.agent_backend not in {"auto", "openai", "hermes"}:
        raise RuntimeError("AGENT_BACKEND는 auto, openai, hermes 중 하나여야 합니다")
    if settings.agent_backend == "openai" and not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")
    if settings.agent_backend == "hermes" or not settings.openai_api_key:
        return AnalyticsService(settings), None, settings.openai_model, settings
    client_args: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_args["base_url"] = settings.openai_base_url
    return AnalyticsService(settings), OpenAI(**client_args), settings.openai_model, settings


def _assistant_dict(message: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        result["tool_calls"] = [
            {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
            for call in message.tool_calls
        ]
    return result


def run_hermes_agent(messages: list[dict[str, Any]], command: str, max_turns: int) -> str:
    project_root = Path(__file__).parents[2]
    completed = subprocess.run(
        [command, "chat", "-Q", "--max-turns", str(max_turns), "-q", build_hermes_prompt(messages)],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "Hermes 실행 실패").strip()
        raise RuntimeError(error[-2000:])
    return completed.stdout.strip() or "Hermes가 답변을 반환하지 않았습니다."


def run_agent(messages: list[dict[str, Any]], service: AnalyticsService, client: OpenAI | None, model: str, settings: Any) -> str:
    if client is None:
        return run_hermes_agent(messages, settings.hermes_command, settings.hermes_max_turns)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    for _ in range(5):
        response = client.chat.completions.create(
            model=model, messages=api_messages, tools=tool_definitions(), tool_choice="auto", temperature=0.1,
        )
        message = response.choices[0].message
        api_messages.append(_assistant_dict(message))
        if not message.tool_calls:
            return message.content or "답변을 생성하지 못했습니다."
        for call in message.tool_calls:
            try:
                result = service.call_tool(call.function.name, json.loads(call.function.arguments or "{}"))
                content = json.dumps(result, ensure_ascii=False)
            except Exception as exc:
                content = json.dumps({"error": str(exc)}, ensure_ascii=False)
            api_messages.append({"role": "tool", "tool_call_id": call.id, "content": content[:50000]})
    return "도구 호출 횟수가 너무 많아 중단했습니다. 질문의 기간이나 조건을 줄여 주세요."


def main() -> None:
    settings = load_settings()
    st.set_page_config(page_title="실적 분석 데모", page_icon="📊", layout="wide")
    st.title("📊 실적 분석 데모")
    st.caption("서버 측에서만 PostgreSQL을 조회하는 자연어 분석 예제입니다.")
    with st.sidebar:
        st.header("실행 정보")
        st.caption(f"테이블 함수: {settings.profit_daily_function}")
        st.caption(f"포트: {settings.streamlit_port}")
        if st.button("대화 초기화"):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("예: 2026년 7월 브랜드별 광고비와 지출액을 집계하여 비교하라")
    if not prompt:
        return
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
            try:
                service, client, model, settings = get_runtime()
                answer = run_agent(st.session_state.messages, service, client, model, settings)
            except Exception as exc:
                answer = f"실행 중 오류가 발생했습니다: {exc}"
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
