import json
import time
from typing import Any, Callable

import streamlit as st
from openai import OpenAI

from profit_agent_demo.config import Settings, load_settings
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

RATE_LIMIT_WAIT_SECONDS = 60
MAX_RATE_LIMIT_RETRIES = 3


def build_agent_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, *messages]


@st.cache_resource
def get_runtime() -> tuple[AnalyticsService, OpenAI, str, Settings]:
    settings = load_settings()
    if not settings.api_key:
        raise ValueError("필수 환경변수가 설정되지 않았습니다: API_KEY")
    client = OpenAI(api_key=settings.api_key, base_url=settings.api_base_url)
    return AnalyticsService(settings), client, settings.model, settings


def _assistant_dict(message: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in message.tool_calls
        ]
    return result


def _is_rate_limited(error: Exception) -> bool:
    return getattr(error, "status_code", None) == 429


def request_completion(
    client: Any,
    *,
    api_type: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
            )
        except Exception as error:
            if api_type != "nvidia" or not _is_rate_limited(error) or attempt == MAX_RATE_LIMIT_RETRIES:
                raise
            sleep(RATE_LIMIT_WAIT_SECONDS)
    raise RuntimeError("API 요청 재시도 한도를 초과했습니다.")


def run_agent(
    messages: list[dict[str, Any]],
    service: AnalyticsService,
    client: OpenAI,
    model: str,
    settings: Any,
) -> str:
    api_messages = build_agent_messages(messages)
    for _ in range(5):
        response = request_completion(
            client,
            api_type=settings.api_type,
            model=model,
            messages=api_messages,
            tools=tool_definitions(),
        )
        message = response.choices[0].message
        api_messages.append(_assistant_dict(message))
        if not message.tool_calls:
            return message.content or "답변을 생성하지 못했습니다."
        for call in message.tool_calls:
            try:
                result = service.call_tool(call.function.name, json.loads(call.function.arguments or "{}"))
                content = json.dumps(result, ensure_ascii=False)
            except Exception as error:
                content = json.dumps({"error": str(error)}, ensure_ascii=False)
            api_messages.append({"role": "tool", "tool_call_id": call.id, "content": content[:50000]})
    return "도구 호출 횟수가 너무 많아 중단했습니다. 질문의 기간이나 조건을 줄여 주세요."


def main() -> None:
    settings = load_settings()
    st.set_page_config(page_title="실적 분석 데모", page_icon="📊", layout="wide")
    st.title("📊 실적 분석 데모")
    st.caption("서버 측에서만 PostgreSQL을 조회하는 자연어 분석 예제입니다.")
    with st.sidebar:
        st.header("실행 정보")
        st.caption(f"API 제공자: {settings.api_type}")
        st.caption(f"모델: {settings.model}")
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
                service, client, model, runtime_settings = get_runtime()
                answer = run_agent(st.session_state.messages, service, client, model, runtime_settings)
            except Exception as error:
                answer = f"실행 중 오류가 발생했습니다: {error}"
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
