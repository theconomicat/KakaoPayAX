# AX 해커톤 제출 답변 초안

대상 기업: 카카오페이증권  
플러그인: KPS Analyst Workbench

## 문항 1. 무엇을, 누가, 어떤 상황에서 쓰나요?

KPS Analyst Workbench는 카카오페이증권 리서치센터 애널리스트, 투자정보 담당자, 자기주도 투자자가 공시·뉴스·가격·시장지표를 한 번에 수집해 근거 패킷을 만드는 Codex 플러그인입니다. 애널리스트가 기업/산업/테마 리포트를 준비하거나, 투자자가 앱에서 본 시장 이슈를 확인할 때 자료가 DART, KIND, 뉴스, 가격 데이터, 경제 캘린더, 시장 심리지표로 흩어져 있어 막힙니다. 이 플러그인은 질문을 기업명·티커·주제·URL로 해석하고, 공개 소스를 읽은 뒤 출처별 접근 상태, 원문 URL, 핵심 숫자, 재무제표 표, 후속 확인 질문을 정리합니다. 최종 판단은 사람이 하되, 판단 전 자료 조사 시간을 줄이는 도구입니다.

## 문항 2. 왜 이 문제를 선택했나요?

카카오페이증권은 공개적으로 리서치와 투자정보를 제공하고, 공시 데이터 분석을 포함한 생성형 AI 활용 사례도 공개했습니다. 증권 리서치의 병목은 글쓰기 이전에 있습니다. 공시 원문에서 표를 찾고, 뉴스와 가격 변동을 맞추고, 어떤 출처를 실제로 읽었는지 확인하는 과정이 반복적이고 시간이 많이 듭니다. 특히 LLM은 출처 없이 그럴듯한 결론을 만들 위험이 있으므로, 카카오페이증권에는 “답변 생성”보다 “근거 수집과 검증 가능한 소스 패킷 생성”이 더 실무적인 AX 문제라고 판단했습니다. 이는 리서치센터 내부 생산성뿐 아니라 투자자가 시장 이슈를 스스로 검증하는 고객 경험과도 맞습니다.

### 출처 URL

- https://www.kakaopaysec.com/company/about/dynamicPage.do
- https://www.kakaopaysec.com/research/industry/dynamicPage.do
- https://www.kakaopaysec.com/management/routine/dynamicPage.do
- https://www.kakaopaysec.com/company/news_page/dynamicNewsDetail.do?id=90
- https://dart.fss.or.kr/dsab007/main.do
- https://kind.krx.co.kr/main.do?method=loadInitPage&scrnmode=3
- https://api.byul.ai/api/v1/news

## 문항 3. 플러그인은 어떻게 작동하나요?

사용자가 기업명, 티커, 주제, URL을 입력하면 orchestration skill이 필요한 소스군을 고릅니다. DART는 공개 검색에서 `corp_code`와 `rcpNo`를 찾고 report viewer와 OpenDART XBRL viewer 표를 읽습니다. KIND는 회사 자동완성, 공시 검색, viewer, original HTML을 따라가며 표를 추출합니다. Byul.ai는 뉴스, 캘린더, 어닝, 공포탐욕지수, VIX, KOSPI 변동성 등을 가져옵니다. Yahoo Finance는 public chart endpoint로 OHLCV를 읽고, The Econmicat catalog는 Yahoo, TipRanks, Unusual Whales, FRED 등 후보 소스를 찾습니다. 어려운 공개 페이지는 browser header, 모바일/RSS/feed/JSON, Jina Reader, TLS impersonation, Playwright 순서로 시도합니다. `source_deep_probe`는 공개 network JSON 후보까지 bounded loop로 follow합니다. 로그인/페이월/CAPTCHA는 넘지 않고 trace를 기록합니다.

## 문항 4. AI를 어떻게 썼나요?

AI에는 해커톤 규정 해석, 카카오페이증권에 맞는 문제 정의 비교, Codex plugin/skill 구조 설계, 공개 금융 에이전트 오픈소스 조사, 도구 코드 초안, 테스트와 README 초안 작성을 맡겼습니다. 직접 판단한 부분은 카카오페이증권을 대상으로 고른 것, “종목 추천 챗봇”이 아니라 “근거 수집 워크벤치”로 좁힌 것, 심사자가 API 키 없이 실행할 수 있도록 no-key 공개 경로를 우선한 것, 투자 조언 금지 가드레일을 둔 것입니다. 만들면서 어려웠던 지점은 DART/KIND의 실제 원문 표 접근과 외부 금융 사이트 차단 대응이었고, 공개 viewer와 trace 기반 reader로 해결했습니다. 받아들이지 않은 제안은 매수/매도 결론, 목표주가, 개인 API 키 의존 구조입니다.

## 문항 5. 어떻게 검증했나요?

예시는 `삼성전자 사업보고서`, `000660.KS 가격 데이터`, `TipRanks earnings`입니다. DART 공개 검색으로 사업보고서 `rcpNo`를 찾고 report viewer와 OpenDART XBRL viewer 표를 추출했습니다. KIND도 회사 검색, 공시 검색, original HTML 수집을 확인했습니다. Yahoo chart endpoint는 `000660.KS` OHLCV를 가져왔고, Byul은 뉴스·캘린더·Fear & Greed·VIX를 반환했습니다. TipRanks는 HTTP 403 후 Playwright로 earnings table을 읽고 공개 `payload.json`까지 follow했습니다. 유료/API 토큰 경계는 넘지 않습니다. 의심한 부분은 LLM이 읽지 않은 자료를 말하는 문제였고, access status와 trace를 강제해 고쳤습니다. unit test, compile, smoke, zip 검증을 통과했습니다.
