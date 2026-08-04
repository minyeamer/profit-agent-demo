# profit-agent-demo

PostgreSQL의 `profit_daily(start_date, end_date)` 테이블 함수를 자연어로 조회하는 작은 테스트용 분석 에이전트입니다.

이 저장소는 특정 회사의 운영 코드나 실제 데이터를 공개하는 프로젝트가 아닙니다. 다른 사람이 자신의 `profit_daily` 호환 데이터에 연결해 다음을 실험할 수 있는 공개 데모입니다.

- 매출·정산금액·마진금액·영업이익 요약
- 일별·월별 실적 추이
- 대표상품별 상위 목록
- 자연어 질문을 구조화된 read-only 분석 도구 호출로 변환
- Hermes MCP와 독립적인 Streamlit 채팅 UI

모든 설명과 사용자 안내는 한국어로 작성되어 있습니다.

## 주의: 공개 저장소에 비밀값을 넣지 마세요

다음 값은 절대 커밋하지 않습니다.

- PostgreSQL host, database, user, password
- LLM API key 또는 사내 OpenAI-compatible endpoint
- VPN 주소·인증정보
- 실제 브랜드명, 실제 상품명, 실제 조회 결과
- 실제 스키마가 공개되면 안 되는 내부 식별자

`.env`와 `.streamlit/secrets.toml`은 `.gitignore`에 포함되어 있습니다. 저장소에는 설정 이름과 형식만 담은 `.env.example`을 제공합니다.

## 빠른 시작

### 1. 환경 준비

Python 3.11 이상과 [`uv`](https://docs.astral.sh/uv/)를 설치합니다.

```bash
uv sync
cp .env.example .env
```

`.env`에 자신의 PostgreSQL 설정을 입력합니다. OpenAI-compatible API를 직접 사용할 경우에만 LLM API key를 입력합니다. API key가 없으면 `AGENT_BACKEND=auto` 설정에 따라 Hermes Desktop/CLI의 현재 OAuth 인증을 사용합니다.

```dotenv
OPENAI_API_KEY=실제_키
OPENAI_MODEL=gpt-4o-mini
AGENT_BACKEND=auto
HERMES_COMMAND=hermes
HERMES_MAX_TURNS=12

PGHOST=your-postgres-host
PGPORT=5432
PGDATABASE=your-database
PGUSER=readonly-user
PGPASSWORD=실제_비밀번호
PGSCHEMA=analytics
PROFIT_DAILY_FUNCTION=analytics.profit_daily
```

### 2. Streamlit 채팅 UI 실행

```bash
set -a
source .env
set +a

uv run streamlit run src/profit_agent_demo/web_app.py \
  --server.address=127.0.0.1 \
  --server.port=8510
```

브라우저에서 `http://127.0.0.1:8510`으로 접속합니다.

### 2-1. Hermes에서 실행하고 종료하기

Hermes Desktop에서 이 저장소를 작업 경로로 연 뒤, Hermes의 터미널 도구로 다음 명령을 실행할 수 있습니다. `source .env`를 통해 PostgreSQL 연결 설정을 현재 프로세스에만 주입합니다.

```bash
env -u PYTHONPATH bash -lc 'set -a; source .env; set +a; exec uv run streamlit run src/profit_agent_demo/web_app.py --server.address=127.0.0.1 --server.port=8510'
```

Hermes 터미널 도구에서 `background=true`로 실행하면 Streamlit을 백그라운드 서버로 유지할 수 있습니다. 실행 결과의 `session_id`를 기록해 두었다가 종료할 때 Hermes의 process 도구에서 다음과 같이 종료합니다.

```text
action: kill
session_id: <Streamlit 실행 결과의 session_id>
```

일반 터미널에서 실행한 프로세스를 종료해야 한다면 다음 명령을 사용할 수 있습니다.

```bash
pkill -f "streamlit run src/profit_agent_demo/web_app.py"
```

실행 여부는 다음 명령으로 확인합니다.

```bash
curl http://127.0.0.1:8510/_stcore/health
# 정상 결과: ok
```

같은 LAN의 다른 사용자가 접속해야 하면 서버 컴퓨터의 사설 IP에만 바인딩합니다.

```bash
uv run streamlit run src/profit_agent_demo/web_app.py \
  --server.address=<서버의-LAN-IP> \
  --server.port=8510
```

공인 인터넷에 포트 포워딩하지 마세요. 사내 LAN 방화벽, 인증, reverse proxy를 별도로 구성하는 것이 좋습니다.

### 3. Docker 실행

Docker가 VPN 경로와 PostgreSQL에 접근할 수 있는 환경에서만 사용하세요.

```bash
docker compose up -d --build
curl http://127.0.0.1:8510/_stcore/health
docker compose down
```

Docker Desktop에서는 컨테이너가 호스트 VPN 경로를 자동으로 사용할 수 없을 수 있습니다. 이 경우 VPN이 연결된 호스트에서 Streamlit을 직접 실행하세요.

## Streamlit secrets 사용

`.env` 대신 Streamlit secrets를 사용할 수도 있습니다. 파일을 생성합니다.

```text
.streamlit/secrets.toml
```

예시:

```toml
OPENAI_API_KEY = ""
OPENAI_BASE_URL = ""
OPENAI_MODEL = "gpt-4o-mini"
AGENT_BACKEND = "auto"
HERMES_COMMAND = "hermes"
HERMES_MAX_TURNS = 12
PGHOST = "your-postgres-host"
PGPORT = 5432
PGDATABASE = "your-database"
PGUSER = "readonly-user"
PGPASSWORD = "실제_비밀번호"
PGSCHEMA = "analytics"
PROFIT_DAILY_FUNCTION = "analytics.profit_daily"
STREAMLIT_PORT = 8510
STREAMLIT_BIND_ADDRESS = "127.0.0.1"
```

샘플 코드는 OS 환경변수를 우선 사용하고, 환경변수가 없으면 Streamlit secrets를 fallback으로 읽습니다. secrets 파일 자체는 반드시 비공개로 유지해야 합니다.

## 환경변수 설명

| 변수 | 필수 | 설명 |
|---|---:|---|
| `OPENAI_API_KEY` | 선택 | `AGENT_BACKEND=openai` 또는 API key가 있는 경우 서버에서 LLM 호출에 사용하는 API key. 없으면 Hermes backend를 사용 |
| `OPENAI_BASE_URL` | 선택 | OpenAI-compatible API의 기본 URL. 비워 두면 OpenAI 기본 endpoint 사용 |
| `OPENAI_MODEL` | 선택 | 사용할 모델명. 기본값 `gpt-4o-mini` |
| `AGENT_BACKEND` | 선택 | `auto`, `openai`, `hermes` 중 하나. 기본값 `auto` |
| `HERMES_COMMAND` | 선택 | Hermes 실행 파일 경로 또는 명령. 기본값 `hermes` |
| `HERMES_MAX_TURNS` | 선택 | Hermes의 최대 agent 반복 횟수. 기본값 `12`. 복잡한 분석은 `20` 정도로 높일 수 있음 |
| `PGHOST` | 필수 | PostgreSQL 호스트명 또는 사설 IP |
| `PGPORT` | 선택 | PostgreSQL 포트. 기본값 `5432` |
| `PGDATABASE` | 필수 | 데이터베이스 이름 |
| `PGUSER` | 필수 | read-only 조회 계정 권장 |
| `PGPASSWORD` | 필수 | PostgreSQL 비밀번호 |
| `PGSCHEMA` | 선택 | 논리적 스키마 설명용 기본값. 기본값 `analytics` |
| `PROFIT_DAILY_FUNCTION` | 선택 | `schema.function` 형식의 테이블 함수. 기본값 `analytics.profit_daily` |
| `STREAMLIT_PORT` | 선택 | 문서용 포트 설정. 기본값 `8510` |
| `STREAMLIT_BIND_ADDRESS` | 선택 | 문서용 bind address. 실제 실행 시 Streamlit CLI 옵션을 사용 |

`PROFIT_DAILY_FUNCTION`은 SQL identifier injection을 막기 위해 `schema.function` 형식만 허용합니다. 컬럼명, group-by, 지표도 allowlist로 제한하며 LLM이 임의 SQL을 실행하지 않습니다.

## `profit_daily` 테이블 함수

이 에이전트는 다음 형태의 PostgreSQL 테이블 함수를 호출합니다.

```sql
SELECT *
FROM analytics.profit_daily(
  DATE '2026-07-01',
  DATE '2026-07-31'
);
```

실제 schema와 함수명은 환경변수 `PROFIT_DAILY_FUNCTION`으로 변경합니다. 이 저장소의 `semantic_schema.yml`과 [docs/profit_daily-schema.md](docs/profit_daily-schema.md)는 공개 가능한 일반화된 계약을 설명합니다.

### 함수 매개변수

| 매개변수 | 타입 | 의미 |
|---|---|---|
| `DS_START_DATE` | `date` | 조회 시작일. 포함 |
| `DS_END_DATE` | `date` | 조회 종료일. 포함 |

서비스는 최대 366일의 기간만 허용하고, PostgreSQL 연결을 read-only transaction으로 열며 statement timeout을 30초로 설정합니다.

### 주요 컬럼 그룹

#### 차원 컬럼

분석 기준이나 필터로 사용할 수 있습니다.

- `product_id`: SKU 또는 상품코드
- `item_id`, `item_seq`: 대표상품코드와 순번
- `team_name`: 담당 조직 또는 팀
- `brand_name`: 브랜드명
- `category_name1`~`category_name4`: 대분류·중분류·소분류·세분류
- `color`: 색상
- `product_name`: 상품명
- `category_unit_name`: 단위가 포함된 상품명
- `shop_id`: 판매처코드
- `shop_group`: 쇼핑몰 그룹
- `shop_name`: 판매 채널명
- `order_status`: 주문 상태 코드
- `order_date`: 일자별 추이 기준 날짜

일반적인 상품 분석에서는 `category_name3`까지를 대표상품 수준으로 보고 `category_name4`를 SKU 수준으로 볼 수 있습니다. 실제 데이터 모델이 다르면 `semantic_schema.yml`을 자신의 규칙에 맞게 수정해야 합니다.

#### 수량 컬럼

- `unit_quantity` (`세트수량`): 세트·박스 단위 수량
- `sku_quantity` (`확정수량`): SKU 기준으로 확정된 수량

#### 금액·수익성 컬럼

- `payment_amount` (`결제금액`): 고객 결제 기준 금액
- `supply_amount` (`정산금액`): 수수료 등 정산 조정 후 분석에 사용하는 금액
- `supply_cost` (`원가*수량`): 원가와 수량을 반영한 원가 합계
- `delivery_fee` (`배송비`): 배송에 관련된 비용
- `ad_cost` (`광고비`): 광고 집행 비용
- `extra_cost` (`지출액`): 광고비를 제외한 추가 비용 또는 고정지출
- `margin_amount` (`마진금액`): 정산금액에서 원가와 배송비를 차감한 금액
- `profit` (`영업이익`): 마진금액에서 광고비와 지출액을 차감한 금액

### 계산식

```text
마진금액 = 정산금액 - 원가*수량 - 배송비
        = supply_amount - supply_cost - delivery_fee

영업이익 = 정산금액 - 원가*수량 - 배송비 - 광고비 - 지출액
        = supply_amount - supply_cost - delivery_fee - ad_cost - extra_cost
        = margin_amount - ad_cost - extra_cost
```

컬럼 이름이 조직마다 다를 수 있으므로, 자신의 함수 반환 컬럼과 `semantic_schema.yml`의 매핑을 함께 확인하세요. 이 저장소는 위 계산식이 이미 반환 컬럼에 반영되어 있다는 전제를 사용합니다.

### 주문 상태 예시

아래 코드는 일반화된 예시입니다. 실제 시스템의 상태 코드가 다르면 반드시 수정하세요.

| 코드 | 의미 | 주로 반영되는 값 |
|---:|---|---|
| `0` | 정상 | 수량·결제금액·정산금액·원가·배송비 |
| `1` | 반품 | 배송비 등 반품 관련 비용 |
| `2` | 교환 | 원가·배송비 등 교환 관련 비용 |
| `3` | 취소 | 데이터 모델 규칙에 따른 취소 금액 |
| `5` | 빈박스 | 배송비 등 |
| `6` | 증정 | 원가 등 |
| `7` | 배송 | 배송비 |
| `8` | 광고 | 광고비 |
| `9` | 비용 | 지출액 |

## 지원되는 분석 도구

### `describe_profit_schema`

컬럼, 업무 용어, 계산식, 주문 상태를 설명합니다.

### `get_profit_summary`

기간, group-by, 지표, 필터를 받아 집계합니다.

예시 질문:

- `2026년 7월의 매출과 영업이익을 알려줘`
- `브랜드별 정산금액과 마진금액을 비교해줘`
- `채널별 광고비와 지출액을 보여줘`

### `get_profit_trend`

일별 또는 월별 결제금액·지출액·영업이익 추이를 반환합니다.

### `get_top_products`

대표상품 기준으로 영업이익, 결제금액, 광고비, 지출액 또는 마진금액 상위 목록을 반환합니다.

## Hermes MCP 연결

환경변수가 설정된 터미널에서 패키지를 설치한 뒤 MCP 서버를 등록할 수 있습니다. 저장소의 `scripts/run_mcp.sh`가 로컬 `.env`를 읽으므로 비밀번호를 Hermes 명령 인자로 직접 넣지 않아도 됩니다.

```bash
uv sync
chmod +x scripts/run_mcp.sh
hermes mcp add profit-agent-demo \
  --command "$PWD/scripts/run_mcp.sh"
```

`scripts/run_mcp.sh`와 `.env`는 같은 로컬 저장소에서 실행해야 합니다. 비밀번호는 `.env`에만 보관하고 shell history나 Hermes 설정 파일에 직접 기록하지 마세요. 운영 환경에서는 별도 secret manager를 사용하세요. 등록 후 MCP 도구 discovery를 확인합니다.

```bash
hermes mcp test profit-agent-demo
```

## 보안 설계

- LLM은 raw SQL을 생성하지 않고 4개의 구조화된 도구만 호출합니다.
- relation, dimension, metric, filter는 allowlist로 검증합니다.
- 필터 값은 PostgreSQL parameter binding으로 전달합니다.
- 조회 기간은 최대 366일입니다.
- 결과는 최대 1,000행으로 제한하고 상품 순위는 최대 100개입니다.
- PostgreSQL 연결은 `default_transaction_read_only=on`과 30초 statement timeout을 사용합니다.
- 브라우저에는 DB credential이 전달되지 않습니다.
- 공개 저장소에는 실제 데이터, 브랜드명, endpoint, secret을 포함하지 않습니다.

## 개발 및 테스트

```bash
uv sync
uv run pytest tests/ -q
uv run python -m compileall -q src
```

이 프로젝트는 작은 테스트용 데모입니다. 운영 환경에 적용하려면 인증, 감사 로그, secret manager, 네트워크 ACL, query cost 제한, 데이터 마스킹을 추가하세요.

## 라이선스

저장소의 `LICENSE`를 확인하세요.
