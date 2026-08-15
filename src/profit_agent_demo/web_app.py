import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st
from openai import OpenAI

from profit_agent_demo.config import Settings, load_settings
from profit_agent_demo.service import AnalyticsService, tool_definitions
from profit_agent_demo.visualization import build_chart_frame, build_chart_spec, build_stacked_bar_chart


SYSTEM_PROMPT = """당신은 실적 분석 데모 에이전트입니다.

profit_daily(start_date, end_date) 테이블 함수의 데이터를 분석합니다.
데모 데이터의 가용 기간은 2025-08-01부터 2026-07-31까지입니다. 2026년 전체 추이를 요청받으면 종료일은 2026-07-31로 사용하고, 존재하지 않는 미래 기간을 0 또는 추정값으로 표시하지 마세요.
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
- shop_id/shop_group/shop_name = 판매처코드/쇼핑몰 그룹/판매처(채널)
- 한국어 차원 매핑: 쇼핑몰·쇼핑몰 그룹 → `shop_group`, 판매처·판매처명·채널 → `shop_name`, 브랜드 → `brand_name`, 상품 → `product_name`
- 영어 차원 매핑: shop group/mall → `shop_group`, shop/seller/channel → `shop_name`, brand → `brand_name`, product → `product_name`
- 상위 N 차원의 일별 그래프는 `get_top_dimension_trend`를 사용합니다. 특정 예시 문장에만 의존하지 말고 사용자가 지정한 차원과 N을 그대로 매핑하세요.
- 그래프 유형 매핑: 선 그래프/line → `line`, 막대차트/막대 그래프/bar → `bar`, 누적 막대/매출 비중/구성비 → `stacked_bar`. 그래프 요청에는 반드시 `chart_type`을 지정하세요.

계산식:
- 마진금액 = 정산금액 - 원가*수량 - 배송비
- 영업이익 = 정산금액 - 원가*수량 - 배송비 - 광고비 - 지출액

예시 브랜드명은 공개 문서에만 사용되는 가상 값입니다. 실제 데이터의 브랜드 목록을 임의로 가정하지 마세요.
"""

RATE_LIMIT_WAIT_SECONDS = 60
MAX_RATE_LIMIT_RETRIES = 3
TRANSIENT_ERROR_WAIT_SECONDS = 5
MAX_TRANSIENT_ERROR_RETRIES = 2


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    tool_name: str | None = None
    tool_result: dict[str, Any] | None = None


def build_agent_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, *messages]


def get_runtime() -> tuple[AnalyticsService, OpenAI, str, Settings]:
    settings = load_settings()
    if not settings.api_key:
        raise ValueError("필수 환경변수가 설정되지 않았습니다: API_KEY")
    client = OpenAI(api_key=settings.api_key, base_url=settings.api_base_url, timeout=90.0, max_retries=0)
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


def _is_transient_provider_error(error: Exception) -> bool:
    return getattr(error, "status_code", None) in {500, 502, 503}


def request_completion(
    client: Any,
    *,
    api_type: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    transient_attempt = 0
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
            if api_type == "nvidia" and _is_transient_provider_error(error) and transient_attempt < MAX_TRANSIENT_ERROR_RETRIES:
                transient_attempt += 1
                sleep(TRANSIENT_ERROR_WAIT_SECONDS)
                continue
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
    on_status: Callable[[str], None] | None = None,
) -> AgentRunResult:
    api_messages = build_agent_messages(messages)
    report_status = on_status or (lambda _: None)
    last_tool_name: str | None = None
    last_tool_result: dict[str, Any] | None = None
    for _ in range(5):
        report_status("분석 요청을 해석하는 중")
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
            return AgentRunResult(message.content or "답변을 생성하지 못했습니다.", last_tool_name, last_tool_result)
        for call in message.tool_calls:
            try:
                report_status(f"안전한 데이터 조회 중: {call.function.name}")
                result = service.call_tool(call.function.name, json.loads(call.function.arguments or "{}"))
                content = json.dumps(result, ensure_ascii=False)
                if isinstance(result, dict):
                    last_tool_name = call.function.name
                    last_tool_result = result
                    if result.get("chart"):
                        report_status("조회 완료, 그래프를 준비하는 중")
                        return AgentRunResult("", last_tool_name, last_tool_result)
                report_status("조회 완료, 응답을 정리하는 중")
            except Exception as error:
                content = json.dumps({"error": str(error)}, ensure_ascii=False)
            api_messages.append({"role": "tool", "tool_call_id": call.id, "content": content[:50000]})
    return AgentRunResult("도구 호출 횟수가 너무 많아 중단했습니다. 질문의 기간이나 조건을 줄여 주세요.", last_tool_name, last_tool_result)


def render_analysis_result(ui: Any, tool_name: str | None, result: dict[str, Any] | None) -> None:
    if not tool_name or not result:
        return
    period = result.get("period") or {}
    if period.get("start_date") and period.get("end_date"):
        ui.caption(f"기간: {period['start_date']} ~ {period['end_date']}")
    group_by = result.get("group_by") or []
    if group_by:
        ui.caption(f"집계 기준: {', '.join(group_by)}")
    metrics = result.get("metrics") or []
    if metrics:
        ui.caption(f"지표: {', '.join(metrics)}")
    filters = result.get("filters") or {}
    ui.caption("필터: 없음" if not filters else f"필터: {filters}")

    rows = result.get("rows")
    if not isinstance(rows, list):
        return
    chart = build_chart_spec(tool_name, result)
    if chart:
        ui.caption(f"그래프: {chart.title}")
        if chart.kind == "line":
            ui.line_chart(build_chart_frame(chart, rows))
        elif chart.kind == "bar":
            ui.bar_chart(build_chart_frame(chart, rows))
        elif chart.kind == "stacked_bar":
            ui.altair_chart(build_stacked_bar_chart(chart, rows), width="stretch")
    ui.dataframe(rows, width="stretch", hide_index=True)


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
            if message["role"] == "assistant":
                render_analysis_result(st, message.get("tool_name"), message.get("tool_result"))

    prompt = st.chat_input("예: 2026년 7월 브랜드별 광고비와 지출액을 집계하여 비교하라")
    if not prompt:
        return
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.status("분석 요청을 준비하는 중", expanded=True) as progress:
            run_result: AgentRunResult | None = None

            def update_progress(label: str) -> None:
                progress.update(label=label, state="running")

            try:
                service, client, model, runtime_settings = get_runtime()
                run_result = run_agent(
                    st.session_state.messages,
                    service,
                    client,
                    model,
                    runtime_settings,
                    on_status=update_progress,
                )
                answer = run_result.answer
                progress.update(label="분석 결과를 표시하는 중", state="complete")
            except Exception as error:
                answer = f"실행 중 오류가 발생했습니다: {error}"
                progress.update(label="분석 요청이 중단되었습니다", state="error")
        if answer:
            st.markdown(answer)
        if run_result:
            render_analysis_result(st, run_result.tool_name, run_result.tool_result)
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "tool_name": run_result.tool_name if run_result else None,
            "tool_result": run_result.tool_result if run_result else None,
        }
    )


if __name__ == "__main__":
    main()
