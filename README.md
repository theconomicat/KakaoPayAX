# KPS Analyst Workbench

카카오페이증권 리서치센터와 투자자가 공개 금융 데이터를 빠르게 모으고, 읽은 출처와 읽지 못한 출처를 구분해, 검토 가능한 리서치 소스 패킷을 만드는 Codex 플러그인입니다.

GitHub: https://github.com/theconomicat/KakaoPayAX

이 저장소는 AX 해커톤 예선 제출을 위해 만든 Codex plugin입니다. 목표는 “주식 분석 챗봇”이 아니라, 애널리스트가 보고서를 쓰기 전에 반복적으로 수행하는 **자료 조사, 공시 원문 확인, 재무제표 표 추출, 뉴스/캘린더/시장지표 정리, 출처 검증**을 Codex가 도구로 처리하게 만드는 것입니다.

## 한 문장 요약

KPS Analyst Workbench는 기업명, 티커, 주제, URL을 입력하면 DART/KIND/OpenDART/Byul/Yahoo Finance/The Econmicat 기반 공개 소스를 수집하고, 접근 상태와 근거를 보존한 리서치 소스 패킷을 생성하는 카카오페이증권형 AX 리서치 도구입니다.

## 해결하려는 문제

카카오페이증권은 리서치와 투자정보를 제공하는 증권사입니다. 애널리스트가 기업·산업·테마 리포트를 준비하거나, 투자자가 특정 종목 이슈를 확인할 때 데이터는 이미 공개되어 있는 경우가 많습니다. 문제는 그 데이터가 한곳에 있지 않다는 점입니다.

반복적으로 막히는 지점은 다음과 같습니다.

- 공시, 재무제표, 뉴스, 경제 캘린더, 가격 데이터, 심리지표가 흩어져 있음
- DART/KIND 공시 원문에서 실제 표를 찾아 읽는 과정이 번거로움
- 어떤 출처를 실제로 읽었고, 어디가 막혔고, 무엇이 샘플 데이터인지 추적하기 어려움
- LLM이 출처 없이 그럴듯한 투자 결론을 만드는 위험이 있음
- 보고서 작성보다 그 전 단계인 자료 조사와 근거 정리가 더 오래 걸림

이 플러그인은 최종 투자 판단을 대신하지 않습니다. 대신 Codex에게 금융 리서치용 도구 묶음을 붙여서, 사람이 판단하기 전에 근거를 정리해 줍니다.

## 대상 사용자

- 카카오페이증권 리서치센터 애널리스트
- 투자정보·콘텐츠·고객교육 담당자
- 카카오페이증권 앱에서 특정 시장 이슈를 확인하려는 자기주도 투자자
- 공개 자료 기반으로 기업/산업/테마 리서치를 빠르게 시작해야 하는 금융 실무자

## 핵심 산출물

기본 산출물은 두 가지입니다.

1. **Research Source Packet**
   - 출처별 URL, 접근 상태, 수집 방식, 핵심 주장, 숫자, 표, 한계, 후속 확인 질문을 정리합니다.

2. **Draft Analyst Memo**
   - 소스 패킷에 있는 근거만 사용해 초안 메모를 만듭니다.
   - 매수, 매도, 보유, 목표주가, 수익률 예측은 생성하지 않습니다.

## 동작 플로우

이 플러그인은 Codex에게 “금융 리서치용 도구 묶음”을 붙여 주는 구조입니다. 사용자는 자연어로 기업, 티커, 주제, URL을 물어보고, Codex는 아래 순서로 필요한 도구만 선택해 실행합니다.

```text
1. 요청 해석
   기업명, 티커, 시장, 주제, 보고서 종류, URL을 분리합니다.

2. 소스 라우팅
   공식 공시가 필요한지, 뉴스/캘린더가 필요한지, 가격/기술 지표가 필요한지,
   외부 금융 사이트 후보 탐색이 필요한지 결정합니다.

3. 공개 데이터 수집
   DART, OpenDART XBRL, KIND, Byul.ai, Yahoo Finance, SEC EDGAR, FRED,
   The Econmicat catalog, OpenBB-inspired provider catalog, public page reader,
   source deep probe 중 필요한 경로만 실행합니다.

4. 접근 상태 기록
   각 출처를 ok, partial, blocked, auth_required, not_found로 남기고,
   어떤 route를 시도했는지 trace에 기록합니다.

5. 구조화
   공시 표, XBRL fact table, 뉴스, 경제 캘린더, 어닝 정보, 가격 데이터,
   기술 지표, 외부 후보 소스를 Research Source Packet으로 정리합니다.

6. 검토 가드레일
   읽지 못한 출처는 추정하지 않고, 투자 추천·목표주가·수익률 예측은 생성하지 않습니다.

7. 선택 산출물
   사용자가 원하면 source packet에 포함된 근거만 사용해 Draft Analyst Memo를 작성합니다.
```

예를 들어 “삼성전자 최근 사업보고서와 반도체 뉴스 흐름을 정리해줘”라는 요청이 들어오면, 플러그인은 DART/KIND에서 공시와 표를 찾고, Byul에서 관련 뉴스와 시장 지표를 가져오며, 필요한 경우 Yahoo Finance 가격 데이터와 The Econmicat catalog 후보 소스를 추가합니다. 최종 답변은 결론을 단정하는 보고서가 아니라, 사람이 판단할 수 있는 근거 묶음으로 끝납니다.

## 접근 가능한 데이터

현재 구현은 API 키 없이 실행 가능한 공개 경로를 우선합니다.

| 데이터 영역 | 구현된 접근 방식 | 예시 |
| --- | --- | --- |
| DART 공시 검색 | DART 공개 상세검색 POST | 회사명, 기간, 보고서명으로 `corp_code`, `rcpNo`, 접수일자 추출 |
| DART 보고서 원문 | `dsaf001/main.do`, `/report/viewer.do` | 재무상태표, 손익계산서, 현금흐름표, 자본변동표 HTML 표 추출 |
| OpenDART XBRL viewer | `/xbrl/viewer/main.do`, `/xbrl/viewer/view.do` | `D210000`, `D310000`, `D520000` 등 fact-table 추출 |
| KIND 공시 | 회사 자동완성, 회사별 공시 검색, viewer, original HTML | `acpt_no`, 제목, 제출일, 원문 HTML, 표 추출 |
| Byul.ai 공개 API | `https://api.byul.ai/api/v1` | 최신 뉴스, 중요 뉴스, 경제 캘린더, 어닝 관련 뉴스/일정, Fear & Greed, VIX, KOSPI 변동성, DXY |
| Yahoo Finance | public chart endpoint | 국내/해외 티커 OHLCV 가격 배열 |
| SEC EDGAR | company tickers + companyfacts public endpoint | 미국 상장사 CIK lookup, revenue, income, assets, liabilities 등 XBRL facts |
| FRED | graph CSV public route | 금리, 물가, 실업률, 유가 등 macro time series |
| The Econmicat | 공개 금융 도구 카탈로그 | Yahoo Finance, Unusual Whales, FRED, SEC EDGAR, Finviz, OpenInsider, Macrotrends, Stock Analysis 후보 검색 |
| OpenBB-inspired catalog | no-key provider router | SEC, FRED, Yahoo, Ken French, Finviz, FINRA, Deribit, IMF 후보 라우팅 |
| 일반 공개 웹 | adaptive public reader | HTML, meta description, JSON-LD, RSS/feed, `.json`, Jina Reader, 선택적 Playwright |
| 루프형 공개 소스 probe | source catalog → Playwright/network candidate → public JSON follow | TipRanks earnings page → `payload.json` |
| 로컬 샘플 | examples/fixtures | 심사자가 네트워크 없이도 demo mode 검증 가능 |

## 동작 방식

```text
사용자 질문
  ↓
회사명/티커/주제/URL 해석
  ↓
공개 데이터 소스 선택
  ↓
DART/KIND/OpenDART/Byul/Yahoo/source catalog/public reader 실행
  ↓
출처별 access_status와 trace 기록
  ↓
재무제표 표, 뉴스, 가격, 지표, 캘린더, 공시를 source packet으로 정리
  ↓
근거 품질 체크
  ↓
선택적으로 draft analyst memo 작성
```

플러그인의 판단 기준은 단순합니다.

- 공식 공시와 규제기관 소스를 우선합니다.
- 공개 API가 있으면 일반 스크래핑보다 먼저 사용합니다.
- 표가 있으면 LLM 요약보다 표 추출을 먼저 합니다.
- 읽지 못한 자료는 추정하지 않고 `blocked`, `partial`, `auth_required`로 기록합니다.
- 투자 결론은 사람이 내리도록 남기고, 플러그인은 근거 정리에 집중합니다.

## Codex MCP 서버

`.mcp.json`은 API 키가 필요 없는 로컬 stdio MCP 서버를 등록합니다. Codex는 이 서버를 통해 공개 금융 도구를 tool call 형태로 사용할 수 있습니다.

```json
{
  "mcpServers": {
    "kps-public-finance": {
      "command": "python3",
      "args": ["tools/kps_mcp_server.py"]
    }
  }
}
```

MCP tool 목록:

- `openbb_public_sources`: OpenBB의 provider routing 아이디어를 참고한 no-key 공개 소스 후보 검색
- `source_catalog_search`: The Econmicat 공개 금융 도구 catalog 검색
- `market_data`: Yahoo Finance chart endpoint 기반 OHLCV 수집
- `fred_series`: FRED graph CSV 기반 macro series 수집
- `sec_lookup`: SEC ticker/CIK 후보 검색
- `sec_companyfacts`: SEC companyfacts 기반 주요 XBRL facts 수집
- `public_page_read`: 공개 페이지 접근 상태와 trace 기록

## 공개 접근 우회 전략

이 프로젝트는 `insane-search`의 public-source-first 접근 아이디어를 참고했습니다. 코드는 복사하지 않았고, 공개 경로를 단계적으로 시도하는 구조만 반영했습니다.

중요한 점은 이 도구가 인증 우회 도구가 아니라는 것입니다. 여기서 “우회”는 로그인, 유료 결제, CAPTCHA를 넘는 의미가 아니라, **공개되어 있는 자료를 더 성실하게 찾는 접근 경로 탐색**을 뜻합니다.

`tools/public_page_reader.py`는 다음 순서로 시도합니다.

1. 일반 desktop browser header로 공개 URL 읽기
2. mobile browser header로 같은 URL 읽기
3. 모바일 서브도메인 후보 확인
4. `/rss`, `/feed`, `.json` 공개 변형 확인
5. Jina Reader 공개 변환 경로 확인
6. `curl_cffi`가 설치되어 있으면 Safari/Chrome/Firefox TLS impersonation 시도
7. 사용자가 `--browser`를 지정하면 Playwright로 공개 렌더링 및 공개 JSON/RSS/API network candidate 확인

모든 시도는 `trace`에 남습니다.

```bash
python3 tools/public_page_reader.py https://example.com/article
python3 tools/public_page_reader.py https://example.com/article --browser
python3 tools/public_page_reader.py https://example.com/article --exhaustive --browser
```

기본값은 `--max-attempts 6`입니다. 하나의 막힌 사이트 때문에 전체 리서치가 멈추지 않도록 빠른 탐색을 기본으로 두고, 필요한 경우에만 `--exhaustive`로 더 오래 탐색합니다.

멈추는 경계는 명확합니다.

- 로그인 필요
- 유료 구독/paywall
- CAPTCHA
- 명백한 접근 거부
- 약관상 애매하거나 권한이 필요한 경로

이 경우 내용을 꾸며내지 않고 접근 상태를 기록합니다.

## 주요 명령

플러그인 루트에서 실행합니다.

```bash
python3 tools/build_source_packet.py \
  --input examples/sample_raw_sources.json \
  --output outputs/research_source_packet.md
```

라이브 공개 소스 워크플로우:

```bash
python3 tools/research_workbench.py \
  --config examples/live_public_sources.json \
  --raw-output outputs/live_public_sources_packet.json \
  --packet-output outputs/live_public_sources_packet.md
```

DART 공개 공시 검색:

```bash
python3 tools/dart_public_client.py search \
  --company 삼성전자 \
  --start-date 20250101 \
  --end-date 20260701 \
  --report-name 사업보고서 \
  --limit 1
```

DART 보고서와 OpenDART XBRL viewer 수집:

```bash
python3 tools/dart_public_client.py bundle \
  --company 삼성전자 \
  --start-date 20250101 \
  --end-date 20260701 \
  --report-name 사업보고서 \
  --max-reports 1
```

KIND 공시 검색:

```bash
python3 tools/kind_public_client.py search \
  --company 삼성전자 \
  --start-date 2026-01-01 \
  --end-date 2026-07-01 \
  --report-name 사업보고서 \
  --limit 1
```

The Econmicat source catalog:

```bash
python3 tools/source_catalog.py --query "Yahoo Finance" --limit 5
python3 tools/source_catalog.py --category "옵션 플로우" --query "Unusual Whales" --probe --limit 1
python3 tools/source_deep_probe.py --query TipRanks --limit 1 --timeout 10 --max-attempts 4 --max-follow 4
```

OpenBB-inspired no-key sources:

```bash
python3 tools/openbb_public_sources.py --query "SEC FRED" --limit 5
python3 tools/sec_edgar_client.py lookup AAPL --limit 3
python3 tools/sec_edgar_client.py facts 0000320193 --limit 2
python3 tools/fred_public_client.py DGS10 --limit 10
```

Yahoo Finance public chart:

```bash
python3 tools/market_data_reader.py AAPL --period 1mo --provider yahoo
python3 tools/market_data_reader.py 005930.KS --period 1mo --provider yahoo
```

Byul.ai 공개 API:

```bash
python3 tools/byul_client.py news --limit 3 --min-importance 3
python3 tools/byul_client.py calendar --range today --lang ko --limit 5
python3 tools/byul_client.py earnings --range this-week --lang ko
python3 tools/byul_client.py indices --indexes fear-greed vix kospi-volatility dxy
```

검증:

```bash
python3 -m pip install --user -r requirements-optional.txt
npm install
npx playwright install chromium
python3 -m unittest discover -s tests
python3 -m py_compile $(find tools scripts -name '*.py' -print)
python3 scripts/smoke_check.py
python3 scripts/check_logs.py logs --output outputs/log_manifest.json
```

제출 ZIP 생성:

```bash
python3 scripts/package_submission.py
unzip -t dist/submission.zip
python3 scripts/check_submission.py build/submission
```

## Codex 플러그인 구조

```text
submission.zip
├── src/
│   ├── .codex-plugin/plugin.json
│   ├── .mcp.json
│   ├── skills/
│   │   ├── kps-analyst-workbench/
│   │   ├── public-source-researcher/
│   │   ├── financial-snapshot-analyst/
│   │   ├── technical-signal-analyst/
│   │   ├── investor-lens-organizer/
│   │   └── research-report-writer/
│   ├── tools/
│   ├── rules/
│   ├── examples/
│   └── tests/
├── README.md
└── logs/
```

해커톤 제출 요건에 맞춰 전체 플러그인 루트는 `submission.zip/src/` 아래에 들어갑니다. `src/.codex-plugin/plugin.json`과 `src/skills/`를 포함합니다. 로그는 `logs/`에 포함되며, 제출 로그는 편집하지 않는 것을 전제로 합니다.

패키징 시 `scripts/check_logs.py`가 `logs/`의 JSONL 로그를 파싱해 `logs/log_manifest.json`을 생성합니다. 이 manifest는 원본 로그를 수정하지 않고 파일 수, 크기, JSONL 라인 수, 파싱 오류 여부만 기록합니다.

## 검증 결과

현재 버전에서 확인한 결과:

```text
Ran 32 tests in 0.009s
OK
Plugin validation passed
smoke check ok
submission structure ok
No errors detected in compressed data of dist/submission.zip.
log validation ok
```

라이브 smoke에서 확인한 항목:

- DART 공개 검색 실행
- DART report viewer section 추출
- OpenDART XBRL viewer role/fact-table 접근
- KIND 회사 공시 검색 실행
- KIND original external HTML 수집
- Byul news/calendar/index API 실행
- SEC EDGAR ticker lookup/companyfacts public route
- FRED graph CSV macro series route
- The Econmicat에서 Yahoo Finance 후보 검색
- OpenBB-inspired no-key provider catalog 검색
- Unusual Whales 옵션 플로우 후보 probe
- TipRanks earnings page 공개 렌더링 및 `payload.json` follow
- Yahoo Finance chart endpoint로 `000660.KS` 가격 데이터 수집
- source packet JSON/Markdown 생성

## 출처와 참고

- 카카오페이증권 회사 소개: https://www.kakaopaysec.com/company/about/dynamicPage.do
- 카카오페이증권 리서치: https://www.kakaopaysec.com/research/industry/dynamicPage.do
- 카카오페이증권 정기보고서: https://www.kakaopaysec.com/management/routine/dynamicPage.do
- DART: https://dart.fss.or.kr/dsab007/main.do
- OpenDART XBRL viewer: https://opendart.fss.or.kr/xbrl/viewer/main.do
- KIND: https://kind.krx.co.kr/main.do?method=loadInitPage&scrnmode=3
- Byul.ai API: https://api.byul.ai/api/v1/news
- The Econmicat: https://www.theconomicat.com/
- OpenBB ODP: https://openbb.co/products/odp/
- OpenBB provider docs: https://docs.openbb.co/odp/python/extensions/providers
- SEC company tickers: https://www.sec.gov/files/company_tickers.json
- SEC companyfacts: https://data.sec.gov/api/xbrl/companyfacts/
- FRED graph CSV: https://fred.stlouisfed.org/graph/fredgraph.csv
- insane-search: https://github.com/fivetaku/insane-search
- Jina Reader: https://github.com/jina-ai/reader

## 라이선스와 주의

이 저장소의 코드는 MIT License로 공개합니다. 자세한 내용은 `LICENSE`를 확인하세요.

이 저장소는 공개 자료 기반 리서치 워크플로우 예시입니다. 투자 조언, 매수/매도 추천, 목표주가, 수익률 예측을 제공하지 않습니다. 외부 사이트의 로그인, 유료 구독, CAPTCHA, 접근 제한을 넘지 않습니다. 제출 로그에는 민감정보나 API 키가 들어가면 안 됩니다.
