# profit-agent-demo

PostgreSQL의 `profit_daily(start_date, end_date)` 테이블 함수를 자연어로 조회하는 작은 테스트용 분석 에이전트입니다.

- 매출·정산금액·마진금액·영업이익 요약
- 일별·월별 실적 추이
- 대표상품별 상위 목록
- 자연어 질문을 구조화된 read-only 분석 도구 호출로 변환
- 제공자 독립 API를 사용하는 Streamlit 채팅 UI

https://github.com/user-attachments/assets/832cb5f2-88c6-433d-904f-c2c3ae913679

https://github.com/user-attachments/assets/41eb26d0-bd33-4d70-87e9-50df04e117e3

## 빠른 시작

### 1. 환경 준비

Python 3.11 이상과 [`uv`](https://docs.astral.sh/uv/)를 설치합니다.

```bash
uv sync
cp .env.example .env
```

`.env`에 PostgreSQL 설정과 API 제공자 설정을 입력합니다. 채팅 UI는 지정한 API에 직접 요청하며 별도 에이전트 실행 파일이나 OAuth에 의존하지 않습니다.

```dotenv
# OpenAI: API_TYPE=openai, MODEL=gpt-4o-mini
# NVIDIA: API_TYPE=nvidia, MODEL=nvidia/nemotron-3-ultra-550b-a55b
API_TYPE=openai
# API_KEY에는 선택한 제공자의 비밀 키를 입력하세요.
API_KEY=
API_BASE_URL=
MODEL=gpt-4o-mini

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

### 4. 누구나 실행할 수 있는 데모 PostgreSQL

가상 식품 유통 데이터와 PostgreSQL 초기화 구성을 제공합니다. 실제 `.env`는 건드리지 않고 데모 설정을 별도 파일로 사용합니다.

```bash
cp .env.demo.example .env.demo
docker compose -f docker-compose.demo.yml --env-file .env.demo up -d demo-postgres
./scripts/run_demo_streamlit.sh
curl http://127.0.0.1:8510/_stcore/health
```

데모 데이터베이스는 호스트의 `127.0.0.1:15432`에서 접근할 수 있고, Streamlit은 `127.0.0.1:8510`에서 실행됩니다. 기본 Compose 실행은 PostgreSQL만 시작하고, 호스트에서 `./scripts/run_demo_streamlit.sh`를 실행하면 `.env.demo`의 공통 API 설정으로 채팅 UI를 시작합니다. `profit-agent-demo` 컨테이너 서비스에는 `container` profile이 붙어 있으며, API key를 전달한 경우에만 별도 실행할 수 있습니다. 데모용 계정과 비밀번호는 공개 예시값이므로 운영 환경에서 사용하지 마세요.

초기화 SQL은 다음 의존성 그래프를 재현합니다. 데모 DB에는 `analytics`와 `demo` 스키마만 생성됩니다.

```text
analytics.profit_daily(start_date, end_date)
  └─ analytics.profit_base(start_date, end_date)
       ├─ demo.sales_daily
       └─ demo.extra_profit
  ├─ demo.product
  └─ demo.shop
```

`demo_db/data/`에는 PostgreSQL이 그대로 읽는 정적 CSV 파일이 있습니다.

| 파일 | 적재 테이블 | 내용 |
|---|---|---|
| `demo.sales_daily.csv` | `demo.sales_daily` | 2025-08-01~2026-07-31의 판매 일별 합성 실적 |
| `demo.extra_profit.csv` | `demo.extra_profit` | 월별 조정 이익 |
| `demo.product.csv` | `demo.product` | 5개 합성 브랜드, 대표상품 90개·SKU 125개 |
| `demo.shop.csv` | `demo.shop` | 실제 공개 판매 채널명 기반의 데모 판매처 |

`demo_db/002_load.sql`은 이 파일들을 PostgreSQL `COPY`로 일괄 적재합니다. init 과정에서 난수·반복문·`generate_series`·수식 기반 데이터 생성을 하지 않습니다. CSV를 갱신해야 할 때만 개발용 스크립트 `uv run python scripts/generate_demo_csv.py`를 실행하고, 생성된 파일을 검토합니다.

브랜드별 월평균 결제금액과 대표상품 수는 솔담건강 약 10억 원(50개), 한결웰빙 약 3억 원(20개), 루미에르홈 약 1억 원(10개), 들꽃찬 약 8천만 원(5개), 모노에어 약 5천만 원(5개)입니다. 식품팀은 영양제·건강기능식품이 아닌 일반식품만 취급합니다. 가전팀은 색상과 구성에 따라 루미에르홈 30개, 모노에어 20개의 SKU를 둡니다. 월별·요일별 편차와 데이터 형태는 원격 데이터의 팀 단위 집계 패턴만 정규화해 반영했으며, 실제 행·식별자·브랜드·상품·판매처 목록은 복사하지 않았습니다.

`item_id`는 대표상품, `product_id`는 색상·포장 구성까지 구분한 SKU입니다. `category_name4`는 `단품`, `본품+소모품`, `2개 세트`처럼 SKU 구성을 구분할 때만 사용하며 해당 정보가 없는 일반식품은 `NULL`로 적재합니다. `color`도 값이 없는 식품은 `NULL`이고 가전 SKU에만 실제 색상값을 둡니다. 판매수량은 정수이며, 정상 판매의 결제금액은 SKU별 정상가 또는 제한적인 행사 단가에 수량을 곱해 계산합니다.

SQL 또는 CSV 파일을 변경한 뒤 기존 PostgreSQL volume에 이미 초기화된 데이터가 있으면 init script가 다시 실행되지 않습니다. 데모 데이터를 처음부터 재생성할 때만 다음 명령으로 데모 volume을 삭제하세요.

```bash
docker compose -f docker-compose.demo.yml --env-file .env.demo down -v
docker compose -f docker-compose.demo.yml --env-file .env.demo up -d demo-postgres
```

`scripts/run_demo_streamlit.sh`는 Docker PostgreSQL에 맞는 `127.0.0.1:15432` 연결정보와 `.env.demo`의 공통 API 설정을 주입합니다. 따라서 실제 회사용 `.env`를 읽지 않습니다.

## Streamlit secrets 사용

`.env` 대신 Streamlit secrets를 사용할 수도 있습니다. 파일을 생성합니다.

```text
.streamlit/secrets.toml
```

예시:

```toml
API_TYPE = "openai"
API_KEY = ""
API_BASE_URL = ""
MODEL = "gpt-4o-mini"
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
| `API_TYPE` | 필수 | `openai` 또는 `nvidia`. 제공자의 기본 endpoint·요청 제한 정책을 선택 |
| `API_KEY` | 필수 | 선택한 API 제공자에 전달하는 비밀 키 |
| `API_BASE_URL` | 선택 | OpenAI 호환 API의 endpoint 재정의. NVIDIA는 비워 두면 NIM 기본 endpoint 사용 |
| `MODEL` | 선택 | 제공자별 모델 식별자. OpenAI 기본값은 `gpt-4o-mini`, NVIDIA 기본값은 `nvidia/nemotron-3-ultra-550b-a55b` |
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

NVIDIA를 선택하면 서버는 OpenAI 호환 NIM endpoint를 사용합니다. API가 HTTP 429를 반환하면 정확히 60초 대기하고 다시 요청하며, 최대 세 번 재시도합니다. 이는 분당 40회 제한을 넘겼을 때만 적용됩니다.

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

- `product_id`: 색상·구성까지 구분하는 SKU 상품코드
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

일반적인 상품 분석에서는 `item_id`와 `category_name3`까지를 대표상품 수준으로 보고 `product_id`, `category_name4`, `color`를 SKU 수준으로 봅니다. SKU 세분 정보가 없으면 `category_name4`와 `color`는 `NULL`입니다. 실제 데이터 모델이 다르면 `semantic_schema.yml`을 자신의 규칙에 맞게 수정해야 합니다.

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
