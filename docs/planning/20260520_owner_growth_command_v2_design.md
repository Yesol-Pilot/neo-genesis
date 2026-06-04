# Owner Growth Command v2 설계

- 작성일: 2026-05-20
- 목적: GA4, PostHog, GSC를 다시 보여주는 화면이 아니라 대표가 매일 바로 판단하는 성과 지휘판을 만든다.
- 핵심 수정: 성과 숫자와 방문자 지표를 첫 화면 최상단에 고정한다.

## 1. 결론

v2 대시보드는 첫 화면에서 아래 네 가지를 5초 안에 보여줘야 한다.

1. 오늘 방문자 수
2. 최근 7일 방문자 수
3. 지난 7일 대비 증감
4. 성과 이벤트 수와 전환율

현재 v1은 측정 상태와 액션 큐는 있으나, 대표가 가장 먼저 보고 싶은 성과 숫자가 화면의 중심이 아니다. v2는 `성과 요약 -> 사이트 랭킹 -> 오늘 할 일 -> 측정 신뢰도` 순서로 재구성한다.

## 2. 첫 화면 KPI

첫 화면 상단에는 카드 6개만 둔다.

| 카드 | 표시값 | 주 소스 | 보조 소스 | 의미 |
|---|---:|---|---|---|
| 오늘 방문자 | today_visitors | GA4 Realtime 또는 PostHog daily | live_tag_probe | 오늘 실제 사람이 들어왔는가 |
| 주간 방문자 | visitors_7d | PostHog distinct users | GA4 users_7d | 최근 일주일 관심 규모 |
| 주간 페이지뷰 | pageviews_7d | PostHog pageviews | GA4 views_7d | 콘텐츠 소비량 |
| 성과 이벤트 | decision_events_7d | PostHog allowlist | 없음 | CTA, 도구 실행, 외부 클릭 등 행동 |
| 전환율 | decision_events_7d / pageviews_7d | PostHog | 없음 | 방문이 성과로 이어지는가 |
| 전주 대비 | visitors_7d vs visitors_prev_7d | PostHog daily rollup | GA4 report | 성장/하락 방향 |

중요 원칙:

- GA4와 PostHog 숫자가 충돌하면 숫자를 합치지 않는다.
- 대표 화면에는 `대표값`을 크게 보여주되, 우측에 `출처: PostHog 우선 / GA4 불신` 같은 신뢰 라벨을 붙인다.
- GA4가 0이고 PostHog가 살아 있으면 방문자 카드는 숨기지 않고 `측정 주의` 배지를 붙인다.
- 성과 이벤트는 `$pageview`가 아니다. `cta_click`, `pricing_view`, `tool_submit`, `affiliate_click`, `outbound_click` 등 allowlist 이벤트만 카운트한다.

## 3. 현재 데이터에서 보이는 문제

2026-05-20 최신 owner snapshot 기준:

| 지표 | 값 |
|---|---:|
| GA4 오늘 사용자 합계 | 0 |
| GA4 7일 사용자 합계 | 0 |
| PostHog 7일 사용자 합계 | 701 |
| PostHog 7일 페이지뷰 합계 | 721 |
| PostHog 7일 성과 이벤트 합계 | 3 |

따라서 현재 대표 화면의 첫 문장은 다음이어야 한다.

> 최근 7일 방문자는 PostHog 기준 701명으로 잡히지만, GA4 수집은 신뢰 불가 상태다. 성과 이벤트는 3건뿐이라 오늘의 핵심 과제는 트래픽 확대보다 전환 이벤트/CTA 보강이다.

이 문장이 나오지 않는 대시보드는 대표용 대시보드가 아니다.

## 4. 새 정보 구조

### 4.1 오늘 탭

모바일 첫 화면 기준 순서:

1. 성과 KPI 6개
2. 오늘의 요약 문장 1개
3. 상위 사이트 5개
4. 오늘 할 일 3개
5. 측정 주의 1줄

데스크톱에서는 같은 정보를 2열로 배치한다.

### 4.2 사이트 탭

사이트별 행은 다음 컬럼을 가진다.

| 컬럼 | 설명 |
|---|---|
| 사이트 | 이름과 도메인 |
| 상태 | 성장, 전환누수, 측정주의, 안정, 방치위험 |
| 오늘 | 오늘 방문자 |
| 7일 | 최근 7일 방문자 |
| 전주 대비 | 증감률과 방향 |
| PV | 주간 페이지뷰 |
| 성과 | 주간 decision events |
| 전환율 | decision_events / pageviews |
| 다음 액션 | 구체적 작업 1개 |

모바일에서는 테이블이 아니라 사이트 카드 목록으로 바꾼다.

### 4.3 기회 탭

GSC 기반이다.

- 노출은 있는데 클릭이 낮은 페이지
- 평균 순위 4-20위 구간의 개선 후보
- 새로 잡힌 쿼리
- 한국어 쿼리 깨짐 여부
- sitemap/live page 상태

GSC는 지연 데이터이므로 실시간 방문자와 분리해 보여준다.

### 4.4 전환 탭

PostHog 기반이다.

- decision events 추이
- CTA 클릭
- 도구 실행
- 검색/필터 사용
- 가격/가입/외부 링크 클릭
- 페이지뷰는 많은데 성과 이벤트가 0인 사이트

전환 탭의 핵심 질문은 `방문자가 뭘 했나`다.

### 4.5 신뢰도 탭

진단은 여기로 몰아낸다.

- GA4 태그 있음/없음
- GA4 수집 지연 또는 property mapping 문제
- PostHog 이벤트 잡음
- GSC 지연
- live page/sitemap 오류
- source freshness

첫 화면에 진단을 크게 올리면 대표가 성과를 못 본다. 단, 신뢰도가 낮은 KPI에는 작은 배지만 붙인다.

## 5. 데이터 계약

`owner-traffic-latest.json`에 `performance_summary`를 추가한다.

```json
{
  "performance_summary": {
    "primary_source": "posthog",
    "trust_state": "degraded",
    "today_visitors": 0,
    "yesterday_visitors": 0,
    "visitors_7d": 701,
    "visitors_prev_7d": null,
    "visitors_7d_delta_pct": null,
    "pageviews_7d": 721,
    "pageviews_prev_7d": null,
    "decision_events_7d": 3,
    "decision_events_prev_7d": null,
    "decision_rate_7d": 0.0042,
    "top_site_by_visitors": "toolpick",
    "top_site_by_growth": null,
    "top_conversion_leak": "toolpick"
  }
}
```

각 site에도 `performance`를 추가한다.

```json
{
  "performance": {
    "today_visitors": 0,
    "yesterday_visitors": 0,
    "visitors_7d": 358,
    "visitors_prev_7d": null,
    "visitors_delta_pct": null,
    "pageviews_7d": 371,
    "decision_events_7d": 0,
    "decision_rate_7d": 0,
    "stage": "conversion_leak",
    "primary_issue": "방문자는 가장 많지만 성과 이벤트가 0입니다.",
    "next_action": "ToolPick 상위 유입 페이지에 명확한 CTA와 decision event를 심습니다."
  }
}
```

## 6. 필요한 수집기 변경

현재 PostHog 수집기는 7일 합계 중심이다. v2에는 일간 rollup이 필요하다.

필수 추가:

- PostHog `daily` 배열: 최근 14일 `date, users, pageviews, decision_events`
- site별 최근 14일 daily series
- `today`, `yesterday`, `last_7d`, `previous_7d` 계산
- `delta_pct` 계산
- `top_growth`, `top_drop`, `conversion_leak` 파생

GA4는 보조 지표로 유지한다.

- `users_today`
- `users_7d`
- `users_prev_7d`
- `views_7d`
- `views_prev_7d`
- GA4가 0인데 PostHog가 0보다 크면 `GA4_COLLECTION_LAG_OR_BLOCKED`

## 7. 첫 화면 와이어프레임

```text
┌──────────────────────────────────────────────┐
│ Owner Growth Command                         │
│ 최근 갱신 14:38 · PostHog 기준 · GA4 주의     │
├──────────┬──────────┬──────────┬──────────┤
│ 오늘 방문 │ 주간 방문 │ 주간 PV  │ 성과 이벤트 │
│ 0        │ 701      │ 721      │ 3        │
├──────────┬──────────┬──────────────────────┤
│ 전환율    │ 전주 대비 │ 오늘의 판단             │
│ 0.42%    │ 비교대기  │ 트래픽보다 CTA 보강 우선 │
├──────────────────────────────────────────────┤
│ 상위 사이트                                  │
│ 1 ToolPick 358명 · 성과 0 · 전환누수          │
│ 2 NeoGenesis 181명 · 성과 1 · 측정주의        │
│ 3 ReviewLab 57명 · 성과 1 · 성장 후보         │
├──────────────────────────────────────────────┤
│ 오늘 할 일                                   │
│ 1 ToolPick CTA/event 심기                    │
│ 2 GA4 수집 불일치 원인 확인                   │
│ 3 ReviewLab/K-OTT 성과 이벤트 강화            │
└──────────────────────────────────────────────┘
```

## 8. 수용 기준

v2는 아래 조건을 통과해야 한다.

1. 모바일 첫 화면에서 스크롤 없이 오늘 방문자, 주간 방문자, 주간 PV, 성과 이벤트가 보인다.
2. 숫자마다 출처와 신뢰 상태가 보인다.
3. GA4가 0이어도 PostHog 방문자를 숨기지 않는다.
4. 사이트별 7일 방문자 랭킹이 보인다.
5. 페이지뷰가 많은데 성과 이벤트가 0인 사이트가 자동으로 `전환 누수`로 표시된다.
6. 전주 대비는 데이터가 없으면 `비교대기`로 표시하고 거짓 증감률을 만들지 않는다.
7. 대표 화면에는 API path, credential path, raw property id가 노출되지 않는다.
8. 신뢰도 문제는 KPI를 가리지 않고 배지와 별도 탭으로 분리한다.

## 9. 구현 우선순위

1. PostHog 14일 daily rollup 수집
2. `performance_summary`와 site별 `performance` 생성
3. 첫 화면 KPI 6개 재배치
4. 사이트 랭킹을 방문자/성과/전환누수 기준으로 재정렬
5. 모바일 카드형 UI 적용
6. 전주 대비, 급상승, 급락, 성과 이벤트 발생 알림 추가

이 순서로 해야 한다. 디자인부터 다시 만지면 숫자 구조가 또 흐려진다.
