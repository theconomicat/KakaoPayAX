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
| The Econmicat | 공개 금융 도구 카탈로그 | Yahoo Finance, Unusual Whales, FRED, SEC EDGAR, Finviz, OpenInsider, Macrotrends, Stock Analysis 후보 검색 |
| 일반 공개 웹 | adaptive public reader | HTML, meta description, JSON-LD, RSS/feed, `.json`, Jina Reader, 선택적 Playwright |
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
python3 -m unittest discover -s tests
python3 -m py_compile $(find tools scripts -name '*.py' -print)
python3 scripts/smoke_check.py
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

## 검증 결과

현재 버전에서 확인한 결과:

```text
Ran 22 tests in 0.007s
OK
smoke check ok
submission structure ok
No errors detected in compressed data of dist/submission.zip.
```

라이브 smoke에서 확인한 항목:

- DART 공개 검색 실행
- DART report viewer section 추출
- OpenDART XBRL viewer role/fact-table 접근
- KIND 회사 공시 검색 실행
- KIND original external HTML 수집
- Byul news/calendar/index API 실행
- The Econmicat에서 Yahoo Finance 후보 검색
- Unusual Whales 옵션 플로우 후보 probe
- Yahoo Finance chart endpoint로 `000660.KS` 가격 데이터 수집
- source packet JSON/Markdown 생성

## 제출 폼 답변 초안

### 문항 1. 무엇을, 누가, 어떤 상황에서 쓰나요?

KPS Analyst Workbench는 카카오페이증권 리서치센터 애널리스트, 투자정보 담당자, 자기주도 투자자가 공시·뉴스·가격·시장지표를 한 번에 수집해 근거 패킷을 만드는 Codex 플러그인입니다. 애널리스트가 기업/산업/테마 리포트를 준비하거나, 투자자가 앱에서 본 시장 이슈를 확인할 때 자료가 DART, KIND, 뉴스, 가격 데이터, 경제 캘린더, 시장 심리지표로 흩어져 있어 막힙니다. 이 플러그인은 질문을 기업명·티커·주제·URL로 해석하고, 공개 소스를 읽은 뒤 출처별 접근 상태, 원문 URL, 핵심 숫자, 재무제표 표, 후속 확인 질문을 정리합니다. 최종 판단은 사람이 하되, 판단 전 자료 조사 시간을 줄이는 도구입니다.

### 문항 2. 왜 이 문제를 선택했나요?

카카오페이증권은 공개적으로 리서치와 투자정보를 제공하고, 공시 데이터 분석을 포함한 생성형 AI 활용 사례도 공개했습니다. 증권 리서치의 병목은 글쓰기 이전에 있습니다. 공시 원문에서 표를 찾고, 뉴스와 가격 변동을 맞추고, 어떤 출처를 실제로 읽었는지 확인하는 과정이 반복적이고 시간이 많이 듭니다. 특히 LLM은 출처 없이 그럴듯한 결론을 만들 위험이 있으므로, 카카오페이증권에는 “답변 생성”보다 “근거 수집과 검증 가능한 소스 패킷 생성”이 더 실무적인 AX 문제라고 판단했습니다. 이는 리서치센터 내부 생산성뿐 아니라 투자자가 시장 이슈를 스스로 검증하는 고객 경험과도 맞습니다.

출처 URL:

- https://www.kakaopaysec.com/company/about/dynamicPage.do
- https://www.kakaopaysec.com/research/industry/dynamicPage.do
- https://www.kakaopaysec.com/management/routine/dynamicPage.do
- https://www.kakaopaysec.com/company/news_page/dynamicNewsDetail.do?id=90
- https://dart.fss.or.kr/dsab007/main.do
- https://kind.krx.co.kr/main.do?method=loadInitPage&scrnmode=3
- https://api.byul.ai/api/v1/news

### 문항 3. 플러그인은 어떻게 작동하나요?

사용자가 기업명, 티커, 주제, URL을 입력하면 orchestration skill이 필요한 소스군을 고릅니다. DART는 공개 검색에서 `corp_code`와 `rcpNo`를 찾고 report viewer와 OpenDART XBRL viewer 표를 읽습니다. KIND는 회사 자동완성, 공시 검색, viewer, original HTML을 따라가며 표를 추출합니다. Byul.ai는 뉴스, 캘린더, 어닝, 공포탐욕지수, VIX, KOSPI 변동성 등을 가져옵니다. Yahoo Finance는 public chart endpoint로 OHLCV를 읽고, The Econmicat catalog는 Yahoo, Unusual Whales, FRED, SEC EDGAR, Finviz 등 후보 소스를 찾습니다. 어려운 공개 페이지는 browser header, 모바일/RSS/feed/JSON 변형, Jina Reader, optional TLS impersonation, optional Playwright 순서로 시도합니다. 결과는 source packet에 URL, access status, trace, 표, 숫자, caveat로 저장합니다. 로그인/페이월/CAPTCHA는 넘지 않고 실패 상태를 기록합니다.

### 문항 4. AI를 어떻게 썼나요?

AI에는 해커톤 규정 해석, 카카오페이증권에 맞는 문제 정의 비교, Codex plugin/skill 구조 설계, 공개 금융 에이전트 오픈소스 조사, 도구 코드 초안, 테스트와 README 초안 작성을 맡겼습니다. 직접 판단한 부분은 카카오페이증권을 대상으로 고른 것, “종목 추천 챗봇”이 아니라 “근거 수집 워크벤치”로 좁힌 것, 심사자가 API 키 없이 실행할 수 있도록 no-key 공개 경로를 우선한 것, 투자 조언 금지 가드레일을 둔 것입니다. 만들면서 어려웠던 지점은 DART/KIND의 실제 원문 표 접근과 외부 금융 사이트 차단 대응이었고, 공개 viewer와 trace 기반 reader로 해결했습니다. 받아들이지 않은 제안은 매수/매도 결론, 목표주가, 개인 API 키 의존 구조입니다.

### 문항 5. 어떻게 검증했나요?

예시는 `삼성전자 사업보고서`와 `000660.KS 가격 데이터`입니다. DART 공개 검색으로 사업보고서 `rcpNo`를 찾고 report viewer와 OpenDART XBRL viewer 표를 추출했습니다. KIND도 회사 검색, 공시 검색, original HTML 수집을 확인했습니다. Yahoo chart endpoint는 `000660.KS` OHLCV를 가져왔고, Byul은 뉴스·경제 캘린더·Fear & Greed·VIX·KOSPI 변동성을 반환했습니다. 예외 상황은 Unusual Whales 같은 외부 소스에서 확인했습니다. 공개 메타데이터는 읽고, 유료/API 토큰 경계는 넘지 않으며 trace를 남깁니다. 의심한 부분은 LLM이 읽지 않은 자료를 읽은 것처럼 말하는 문제였고, access status와 caveat를 강제해 고쳤습니다. `22`개 unit test, `py_compile`, smoke check, zip 구조 검증을 통과했습니다.

## 출처와 참고

- 카카오페이증권 회사 소개: https://www.kakaopaysec.com/company/about/dynamicPage.do
- 카카오페이증권 리서치: https://www.kakaopaysec.com/research/industry/dynamicPage.do
- 카카오페이증권 정기보고서: https://www.kakaopaysec.com/management/routine/dynamicPage.do
- DART: https://dart.fss.or.kr/dsab007/main.do
- OpenDART XBRL viewer: https://opendart.fss.or.kr/xbrl/viewer/main.do
- KIND: https://kind.krx.co.kr/main.do?method=loadInitPage&scrnmode=3
- Byul.ai API: https://api.byul.ai/api/v1/news
- The Econmicat: https://www.theconomicat.com/
- insane-search: https://github.com/fivetaku/insane-search
- Jina Reader: https://github.com/jina-ai/reader

## 라이선스와 주의

이 저장소의 코드는 MIT License로 공개합니다. 자세한 내용은 `LICENSE`를 확인하세요.

이 저장소는 공개 자료 기반 리서치 워크플로우 예시입니다. 투자 조언, 매수/매도 추천, 목표주가, 수익률 예측을 제공하지 않습니다. 외부 사이트의 로그인, 유료 구독, CAPTCHA, 접근 제한을 넘지 않습니다. 제출 로그에는 민감정보나 API 키가 들어가면 안 됩니다.
