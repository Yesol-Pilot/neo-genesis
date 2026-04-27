# HIVE MIND × GEO Integration Guide

> 작성: 2026-04-27 by Claude Opus 4.7 (Strategy Lead)
> 목적: HIVE MIND, blog_pipeline, SBU 자동 발행 시스템에 GEO 검증 + 자동 인덱싱 통합
> 근거: `.agent/knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md`

## 핵심 원칙

콘텐츠 publish 흐름의 **3가지 게이트** 강제:

1. **GEO Validator (Pre-publish)** — `src/pipelines/geo_validator.py`
   - Statistics density (500단어당 3개 이상)
   - 외부 출처 2개 이상
   - Schema.org Article 부착
   - heading hierarchy H2 최소 2개
   - dateModified 메타데이터 필수
   - **점수 < 100 이면 publish 차단** (또는 warn 단계만 통과)

2. **Publish (배포)** — 기존 SBU/blog 빌드 + Vercel deploy
   - Next.js 의 경우 postbuild hook 이 자동으로 IndexNow ping (이미 통합)
   - Python pipeline 의 경우 다음 단계로 명시 호출

3. **Publish Hook (Post-publish)** — `src/pipelines/geo_publish_hook.py`
   - IndexNow 일괄 ping (Bing/Yandex/Naver fan-out)
   - Vercel ISR revalidate trigger (env 설정 시)

## blog_pipeline.py 통합 예시

```python
from langgraph.graph import StateGraph, END
from src.pipelines.geo_validator import validate
from src.pipelines.geo_publish_hook import notify_publish

def geo_gate_node(state):
    """publish 직전 GEO 검증. 통과 시만 다음 노드로."""
    content = state["content"]
    meta = state.get("metadata", {})
    verdict = validate(content, metadata=meta)
    state["geo_verdict"] = verdict
    if not verdict.passes:
        # error 발견 → writer 재실행 trigger
        state["needs_revision"] = True
        state["revision_notes"] = [
            f"{i.code}: {i.message}" for i in verdict.issues if i.severity == "error"
        ]
    return state

def publish_hook_node(state):
    """publish 직후 IndexNow ping + revalidate."""
    if state.get("published_urls"):
        result = notify_publish(state["published_urls"])
        state["geo_publish_result"] = result
    return state

# 그래프
workflow = StateGraph(AgentState)
workflow.add_node("researcher", research_node)
workflow.add_node("writer", writer_node)
workflow.add_node("geo_gate", geo_gate_node)
workflow.add_node("publish", publish_node)
workflow.add_node("publish_hook", publish_hook_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "geo_gate")

# 조건부: 검증 실패 시 writer 로 돌아감
workflow.add_conditional_edges(
    "geo_gate",
    lambda s: "writer" if s.get("needs_revision") else "publish",
)

workflow.add_edge("publish", "publish_hook")
workflow.add_edge("publish_hook", END)
```

## SBU Autonomous Growth Runner 통합 예시

`scripts/sbu_autonomous_growth_runner.mjs` 같은 Node 기반 자동 발행 시스템에서는:

```js
// 발행 직후 IndexNow ping
import { spawn } from "node:child_process";

function notifyIndexNow(urls) {
    return new Promise((resolve) => {
        const proc = spawn("python", [
            "src/pipelines/geo_publish_hook.py",
            ...urls,
        ]);
        proc.on("exit", (code) => resolve(code === 0));
    });
}

// 발행 흐름
async function publishSbuPost(sbuSlug, postSlug) {
    await buildAndDeploy(sbuSlug, postSlug);
    await notifyIndexNow([
        `https://${sbuSlug}.neogenesis.app/${postSlug}`,
        `https://${sbuSlug}.neogenesis.app/${postSlug}.md`,  // Markdown alt 있다면
    ]);
}
```

## V-Score 게이트와의 관계

기존 V-Score 가 콘텐츠 품질을 184.5+ 점으로 게이트한다면, GEO Validator 는 **AI 인용 가능성** 을 별도 차원에서 게이트한다. 두 게이트는 직교 (orthogonal):

| 차원 | V-Score | GEO Validator |
|---|---|---|
| 측정 대상 | 사실성 / EEAT / 가독성 | 통계 밀도 / Schema / heading 위계 / 외부 출처 |
| 통과 기준 | 점수 ≥ 184.5 | error 0건 (warn 허용) |
| 실패 시 액션 | writer 재실행 | writer 재실행 + 통계/출처 추가 지시 |

권장 순서: V-Score 통과 → GEO Validator 통과 → publish.

## 임계값 튜닝

콘텐츠 카테고리별로 임계값 조정 가능:

```python
from src.pipelines.geo_validator import validate, DEFAULT_THRESHOLDS

# 짧은 SBU 비교 페이지 (programmatic SEO)
SBU_COMPARISON_THRESHOLDS = {
    **DEFAULT_THRESHOLDS,
    "min_word_count": 200,           # 비교 표 위주라 짧음 OK
    "statistics_per_500w_min": 5,    # 비교 표 = 통계 풍부해야
    "external_citations_min": 0,     # 자체 비교 표 위주
}

# 학술/연구 페이지
RESEARCH_THRESHOLDS = {
    **DEFAULT_THRESHOLDS,
    "min_word_count": 1000,          # 깊이 필수
    "external_citations_min": 5,     # 학술 인용 최소 5개
    "h2_min_count": 4,               # 더 풍부한 구조
}

verdict = validate(content, metadata=meta, thresholds=RESEARCH_THRESHOLDS)
```

## CLI 사용

콘텐츠 파일 1개 검증:

```bash
python -m src.pipelines.geo_validator path/to/post.md metadata.json

# 종료코드: 0 = passes, 1 = fails
```

CI/CD 통합:

```yaml
# .github/workflows/geo-check.yml
- name: GEO Validation
  run: |
    for f in content/blog/*.md; do
      python -m src.pipelines.geo_validator "$f" || exit 1
    done
```

## Phase 1 다음 액션

- [ ] blog_pipeline.py 에 geo_gate / publish_hook 노드 추가
- [ ] HIVE MIND (실제 위치 파악 필요) 의 publish 흐름에 동일 게이트 삽입
- [ ] sbu_autonomous_growth_runner.mjs 의 발행 직후 hook 호출
- [ ] CI workflow 에 GEO 검증 자동 실행 (PR 시점)
- [ ] V-Score 게이트와의 통합 (단일 결정 함수로)
