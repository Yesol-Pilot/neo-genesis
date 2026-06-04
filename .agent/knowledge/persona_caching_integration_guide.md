# Persona Prompt Caching — 통합 가이드 v1

> **작성자:** Claude Opus 4.7 (Strategy Lead)
> **작성일:** 2026-05-10
> **연관 SSOT:** `persona_caching_cost_analysis_v1.md`
> **상태:** Design only — 실 코드 변경 X, owner G2 승인 후 Phase 2 진행

---

## 0. 가이드 목적

본 문서는 `persona_caching_cost_analysis_v1.md` 의 비용 분석에서 **승인된 적용** 을 어떻게 코드에 반영하는지 단계별로 정의한다. 실 코드 변경은 owner G2 승인 후 별도 세션에서 진행.

### Scope
- **In scope**: Anthropic API cache_control marker 사용법 / Sora engine 통합 패턴 / dispatcher 와 페르소나 frontmatter 연계 / 모니터링 hook
- **Out of scope**: Claude Code subagent path 의 cache enable wrapper (P2 작업, 별도 ticket)

---

## 1. Anthropic API cache_control 기본 사용법

### 1.1 단일 cache breakpoint (가장 간단한 패턴)

```python
import anthropic

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY env 필수

# 페르소나 body 를 system prompt 로 주입 + cache marker
persona_body = open(".agent/personas/tier-s/senior-da-pm-korean.md").read()

response = client.messages.create(
    model="claude-sonnet-4-5",  # 또는 "claude-opus-4-7"
    max_tokens=4096,
    system=[
        {
            "type": "text",
            "text": persona_body,
            "cache_control": {"type": "ephemeral"}  # 5min default
        }
    ],
    messages=[
        {"role": "user", "content": "이번 주 ToolPick 방문자 분석해줘"}
    ]
)

# 응답에서 cache hit/miss 확인
print(response.usage.cache_creation_input_tokens)  # cache write 시
print(response.usage.cache_read_input_tokens)      # cache hit 시
```

**중요 포인트**:
- `cache_control` 은 `system` array 의 **각 block 마다** 명시 가능
- 최대 4 cache breakpoints per request (Anthropic 정책)
- 1024 token 미만 block 은 cache 적용 안 됨 (Sonnet/Opus 기준)

### 1.2 1h ephemeral cache (Opus 4.7 + 고빈도 페르소나)

```python
system=[
    {
        "type": "text",
        "text": persona_body,
        "cache_control": {"type": "ephemeral", "ttl": "1h"}
    }
]
```

**적용 조건** (cost analysis §7 참조):
- 호출 빈도 ≥ 1/h
- ROI break-even N ≥ 3
- 권고 페르소나: `quant-strategy-lead`, `prompt-injection-auditor`

### 1.3 Multi-block cache (CLAUDE.md import + persona)

```python
system=[
    {
        "type": "text",
        "text": global_claude_md,         # 안정 prefix (10K tokens, 1h)
        "cache_control": {"type": "ephemeral", "ttl": "1h"}
    },
    {
        "type": "text",
        "text": persona_body,             # 변동 가능 prefix (3K tokens, 5min)
        "cache_control": {"type": "ephemeral"}
    },
    {
        "type": "text",
        "text": session_context,          # short-term context (uncached)
    }
]
```

**효과**:
- global_claude_md 는 1h 동안 모든 페르소나에서 공유
- persona body 는 페르소나별 5min cache
- session_context 는 caching 없이 매번 전달

---

## 2. Sora engine 통합 패턴

### 2.1 현 코드 위치 확인

```
src/core/sora_engine.py
- _call_anthropic_chat() 또는 유사 함수가 anthropic API 직접 호출
- 현재 cache_control marker 미사용 (확인 필요)
```

**확인 방법** (코드 변경 없이):
```bash
grep -n "anthropic" D:/00.test/neo-genesis/src/core/sora_engine.py | head -20
grep -n "cache_control" D:/00.test/neo-genesis/src/core/sora_engine.py
```

### 2.2 권고 wrapper 함수 패턴 (design)

```python
# src/core/anthropic_cache_wrapper.py (NEW)
"""
Anthropic API caching wrapper for persona-aware calls.

owner G2 승인 후 적용. 현재 design only.
"""
from typing import Optional
import anthropic
import yaml
from pathlib import Path

PERSONA_DIR = Path(".agent/personas")


def load_persona_cache_strategy(persona_id: str) -> dict:
    """페르소나 frontmatter 의 cache_strategy 읽기."""
    # tier-s/A/B/C 디렉토리 검색
    for tier in ["tier-s", "tier-a", "tier-b", "tier-c"]:
        path = PERSONA_DIR / tier / f"{persona_id}.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # frontmatter parse (--- 사이)
            if content.startswith("---"):
                end = content.find("---", 3)
                fm = yaml.safe_load(content[3:end])
                return fm.get("cache_strategy", {})
    return {}


def build_cached_system(persona_id: str, persona_body: str) -> list[dict]:
    """페르소나 cache_strategy 에 따라 system block 구성."""
    strategy = load_persona_cache_strategy(persona_id)
    breakpoints = strategy.get("cache_breakpoints", [])

    if not breakpoints:
        # 기본: 5min ephemeral
        return [{
            "type": "text",
            "text": persona_body,
            "cache_control": {"type": "ephemeral"}
        }]

    # breakpoint 정의 따라 multi-block 구성
    blocks = []
    for bp in breakpoints:
        if bp["location"] == "system_prompt":
            blocks.append({
                "type": "text",
                "text": persona_body,
                "cache_control": {
                    "type": "ephemeral",
                    "ttl": bp.get("ttl", "5m")
                }
            })
    return blocks


def call_persona_aware(
    persona_id: str,
    persona_body: str,
    user_message: str,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 4096,
) -> dict:
    """페르소나-aware Anthropic API 호출."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=build_cached_system(persona_id, persona_body),
        messages=[{"role": "user", "content": user_message}]
    )

    # audit log 에 cache 통계 기록
    audit_log_cache_stats({
        "persona_id": persona_id,
        "model": model,
        "cache_creation_tokens": response.usage.cache_creation_input_tokens or 0,
        "cache_read_tokens": response.usage.cache_read_input_tokens or 0,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    })

    return {
        "text": response.content[0].text,
        "cache_hit": (response.usage.cache_read_input_tokens or 0) > 0,
        "usage": response.usage.model_dump(),
    }


def audit_log_cache_stats(stats: dict):
    """audit log JSONL 에 cache 통계 append."""
    import json
    from datetime import datetime, timezone

    log_path = Path("logs/anthropic_cache_audit.jsonl")
    log_path.parent.mkdir(exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **stats,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

### 2.3 sora_engine.py 통합 지점

기존 patch 적용 시 (design only):
```python
# src/core/sora_engine.py 의 anthropic 호출 부분
# Before:
#   response = self.anthropic_client.messages.create(model=model, ...)
# After:
from src.core.anthropic_cache_wrapper import call_persona_aware

result = call_persona_aware(
    persona_id=routing_result.persona_id,  # dispatcher 결과
    persona_body=routing_result.persona_body,
    user_message=user_input,
    model=routing_result.model,
)
return result["text"]
```

---

## 3. Claude Code 통합 가이드

### 3.1 Main session (자동 caching)

**owner action 불필요** — Claude Code 자체가 자동 caching.

**확인 방법**:
- Claude Code session 에서 `/cost` 명령 실행 (커뮤니티에 따라 다를 수 있음)
- 토큰 사용량에 cache_read_input_tokens 가 0 이상이면 작동 중

### 3.2 Subagent 환경 (caching 비활성)

**현 상태**: `enablePromptCaching: false` hardcoded
- citation: github.com/anthropics/claude-code/issues/29966
- 매 subagent call ~7K token uncached billing

**대안** (owner G2 별도 ticket):
1. **Wait for fix**: Anthropic 이 issue #29966 해결 시까지 대기
2. **Direct API path**: Claude Code 대신 Sora engine 의 wrapper 경유 (이미 caching 적용)
3. **Custom subagent runner**: `scripts/persona/dispatcher.py` 가 anthropic API 직접 호출 (현재 stub 형태)

### 3.3 권고
- Claude Code main session = owner-facing 대화 → 자동 caching 활용 (별도 작업 X)
- Sora engine path = telegram bot 호출 → cache_control 명시 적용 (Phase 2)
- subagent path = defer to Anthropic upstream fix

---

## 4. Frontmatter cache_strategy 표준 schema

### 4.1 v1.2 → v1.3 확장 (cache_breakpoints 신규)

```yaml
cache_strategy:
  ttl: "5m" | "30m" | "1h"     # 기본 TTL (cache_breakpoints 없을 때 사용)
  priority: P0 | P1 | P2        # 페르소나 caching 우선순위
  cache_breakpoints:            # 신규 (v1.3)
    - location: "system_prompt" # 또는 "instructions_prefix" / "global_claude_md"
      ttl: "5m" | "1h"
      ephemeral: true | false
  estimated_monthly_savings_usd: <X>   # cost_analysis §5 참조
  break_even_calls_per_hour: <Y>       # ROI 분기점
```

### 4.2 5 Tier S 페르소나 권고 매트릭스

| 페르소나 | TTL 권고 | priority | 추정 절감/월 (Realistic) |
|---|---|---|---|
| senior-backend-eng-korean | **5m** | P0 | $0.81 |
| senior-da-pm-korean | **5m** | P0 | $0.51 |
| multi-agent-orchestrator | **5m** | P0 | $0.73 |
| quant-strategy-lead | **1h** | P0 | $0.50 |
| prompt-injection-auditor | **1h** | P0 | $0.53 |
| **합계** | — | — | **$3.08** |

---

## 5. 모니터링 + audit log

### 5.1 audit log 스키마

`logs/anthropic_cache_audit.jsonl`:
```json
{"ts": "2026-05-15T09:00:00Z", "persona_id": "senior-da-pm-korean", "model": "claude-sonnet-4-5", "cache_creation_tokens": 3300, "cache_read_tokens": 0, "input_tokens": 3300, "output_tokens": 850}
{"ts": "2026-05-15T09:02:15Z", "persona_id": "senior-da-pm-korean", "model": "claude-sonnet-4-5", "cache_creation_tokens": 0, "cache_read_tokens": 3300, "input_tokens": 50, "output_tokens": 1200}
```

위 예: 첫 호출 cache write 3,300 tokens, 2분 후 호출 cache hit 3,300 tokens.

### 5.2 주간 보고 metric

```sql
-- audit log JSONL 을 분석
SELECT
  persona_id,
  COUNT(*) AS calls,
  SUM(cache_creation_tokens) AS cache_writes,
  SUM(cache_read_tokens) AS cache_reads,
  ROUND(SUM(cache_read_tokens) * 1.0 / NULLIF(SUM(input_tokens), 0), 2) AS hit_rate,
  ROUND(SUM(cache_read_tokens) * 0.0000003, 4) AS cache_read_cost_usd,
  ROUND(SUM(input_tokens - cache_read_tokens) * 0.000003, 4) AS regular_input_cost_usd
FROM cache_audit_log
WHERE ts > NOW() - INTERVAL '7 days'
GROUP BY persona_id;
```

### 5.3 권고 alerting
- `hit_rate < 30%` per 페르소나 7일 기준 → 비효율 경고 (TTL 또는 dispatcher 라우팅 점검)
- `cache_writes / cache_reads > 1.0` → break-even 미달 (cache 무용지물)
- Anthropic Console `Usage and Cost API` 와 cross-check (citation: docs.anthropic.com/en/api/usage-cost-api)

---

## 6. 통합 단계별 체크리스트 (owner G2 승인 후 Phase 2)

### Day 1: Frontmatter 갱신 (이번 세션 P1 완료)
- [x] 5 Tier S 페르소나 frontmatter 에 `cache_breakpoints` 필드 추가
- [x] schema v1.3 표준 docstring 박제

### Day 2: Wrapper 코드 작성
- [ ] `src/core/anthropic_cache_wrapper.py` 신규 (250 lines)
- [ ] `tests/test_anthropic_cache_wrapper.py` (10 unit tests)
- [ ] dispatcher.py 가 cache_strategy 읽도록 통합

### Day 3: Sora engine 통합
- [ ] `src/core/sora_engine.py` 의 anthropic 호출 wrapper 경유 변경
- [ ] audit log JSONL 가동 (`logs/anthropic_cache_audit.jsonl`)
- [ ] 첫 라이브 호출 검증 (cache_creation_tokens 비-0 확인)

### Week 2: 모니터링
- [ ] 주간 hit_rate 보고서 생성 (Sora telegram 통합 가능)
- [ ] Anthropic Console 실측 비용 vs 추정 비교

### Week 4: 재평가
- [ ] 실측 절감액 vs 본 SSOT v1 추정 비교
- [ ] Tier A 9 페르소나 확장 결정 (G2)
- [ ] cost_analysis_v2.md 작성

---

## 7. 위험 + rollback 계획

### 위험 매트릭스

| 위험 | 영향 | 확률 | mitigation |
|---|---|---|---|
| Anthropic API 가격 인상 | 비용 증가 | 낮음 | API price 모니터링 cron |
| cache_control 마커 잘못 적용 | cache miss 100% | 중간 | unit test + dry-run |
| audit log JSONL 비대화 | disk 부담 | 낮음 | 30일 rotation 정책 |
| 페르소나 body 자주 변경 | cache write 비용 ↑ | 중간 | 변경 시 audit log + 주간 리포트 |
| Sora engine 호출 path 변경 | 통합 깨짐 | 낮음 | 통합 테스트 + git diff 검증 |

### Rollback 절차

**즉시 비활성** (1줄 환경변수):
```bash
export ANTHROPIC_CACHE_DISABLED=1
```
→ wrapper 가 cache_control 무시하고 plain 호출

**완전 원복** (코드):
```python
# anthropic_cache_wrapper.py 의 build_cached_system() 을 plain text 로 단순화
return [{"type": "text", "text": persona_body}]
```
→ 재배포 시 cache 미사용

**페르소나 frontmatter 원복**:
- `cache_breakpoints` 필드 제거 → 자동 default (5min) 적용
- 또는 `cache_strategy.disabled: true` 추가 (v1.4 schema 확장 가능)

---

## 8. FAQ

### Q1: Sonnet 과 Opus 모두 cache 적용 가능?
**A**: ✅ 모두 가능. Haiku 도 가능 (단 minimum 2048 tokens).

### Q2: Cache write 가 base price 의 1.25 배인데 손해 안 나?
**A**: 같은 prefix 가 N≥2 회 호출되면 break-even. 5min cache 기준 1.278회. Tier S 5 페르소나 모두 평균 호출 ≥ 3 충족.

### Q3: 시스템 reboot / Sora 재시작 후 cache 유지?
**A**: ❌ Anthropic 서버 측 cache 라 클라이언트 재시작과 무관. 단, 5분/1시간 TTL idle 후 만료.

### Q4: cache 적용으로 응답 latency 개선?
**A**: ⚠️ 약간. Anthropic 측에서 cached prefix 처리 시간 단축 (~30% TTFT 개선 보고, citation: anthropic.com/news/prompt-caching).

### Q5: Tier A/B 페르소나도 적용?
**A**: 본 분석은 Tier S 한정. Phase B 4주 측정 후 ROI 검증 시 Tier A 확장 권고.

### Q6: 다른 LLM (Gemini, OpenAI) 의 caching 과 호환?
**A**: 호환 X — Anthropic-specific. Gemini context caching, OpenAI prompt caching 모두 별도 API 필요.

### Q7: Workspace 격리 (2026-02-05+) 영향은?
**A**: Neo Genesis 단일 workspace 운영 → 영향 없음. Multi-tenant 운영 시점에 재검토.

---

## 9. 변경 이력

| 일자 | 작성자 | 변경 |
|---|---|---|
| 2026-05-10 | Claude Opus 4.7 | v1 초안 작성 (cache_control marker / Sora engine wrapper / dispatcher 통합) |

---

## 10. Citation 출처

1. [Prompt caching - Claude API Docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
2. [Pricing - Claude API Docs](https://docs.anthropic.com/en/docs/about-claude/pricing)
3. [Lessons from building Claude Code: Prompt caching is everything](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything)
4. [Agent SDK subagents have prompt caching disabled by default - GitHub issue #29966](https://github.com/anthropics/claude-code/issues/29966)
5. [Usage and Cost API - Claude API Docs](https://docs.anthropic.com/en/api/usage-cost-api)
6. [Prompt caching with Claude](https://www.anthropic.com/news/prompt-caching) — TTFT 개선 메트릭
7. [System Prompts release notes](https://docs.anthropic.com/en/release-notes/system-prompts) — Workspace isolation

👤 Claude Opus 4.7 (Strategy Lead, design only — owner G2 결정 대기)
