# OntoClean Metaproperty Validation v0.1

> **Source**: Guarino & Welty (2002). "Evaluating Ontological Decisions with OntoClean." Communications of the ACM, 45(2), 61–65.
> **Validation date**: 2026-05-14
> **Locked by**: Strategy Lead Claude Opus 4.7 (G1-21 박제)
> **Status**: v0.2 진입 게이트 — 위반 클래스 4건 식별, 교정 권고 박제

OntoClean 의 4 metaproperty 를 11 클래스에 부여하여 taxonomy 의 형식적 정합성을 검증한다.

**Notation**:
- **Rigidity**: +R (rigid, 인스턴스가 항상 해당 클래스) / ~R (anti-rigid, 일부 시점만) / -R (non-rigid)
- **Identity** (carrier): +I (자체 identity criterion 보유) / -I (carrier 없음)
- **Unity**: +U (모든 인스턴스가 동일 unity 기준) / -U / ~U
- **Dependence**: +D (다른 entity 의존 / not self-contained) / -D

**핵심 규칙** (OntoClean §3):
1. anti-rigid (~R) 클래스는 rigid (+R) 클래스를 subsume 할 수 없음
2. identity carrier (+I) 의 하위 클래스는 반드시 +I
3. dependent (+D) 클래스는 dependent 한 것만 subsume

---

## 11 클래스 metaproperty 표

| 클래스 | Rigidity | Identity | Unity | Dependence | 위반 위험 | 교정 |
|---|---|---|---|---|---|---|
| **Artifact** | ~R ⚠️ | +I | +U | -D | "특정 revision 으로서의 파일" 은 +R 지만 "이 파일" 자체는 status 가변 | Revision 이 +R 부분 cover. v0.2 에서 `ImmutableArtifact(+R)` vs `MutableArtifactSlot(~R)` subtype 명시 검토 |
| **Revision** | +R | +I | +U | +D (Artifact 의존) | 낮음 — content_hash 가 identity, immutable | 유지. PROV-O Entity 정합 |
| **Project** | +R | +I | +U | -D | 낮음 — slug 가 identity, self-contained | 유지 |
| **Service** | ~R ⚠️ | +I | +U | +D (Device 의존) | status 가변 → anti-rigid. ITIL CI 논쟁과 동일 | v0.2: `ServiceDefinition(+R)` vs `ServiceInstance(~R)` 분리. v0.1 은 ServiceInstance 만 박제 (단일 클래스 유지) |
| **Device** | +R | +I | +U | -D | 낮음 — hostname identity | 유지 |
| **Agent** | ~R ⚠️ | +I (v0.1 fix) | -U | +D (Policy 의존 가능) | **직전 -I 위험 해소**: G1-12 박제로 `id` 만이 identity criterion. model/tier/label 은 속성 (변경 시 alias) | 유지. PROV-O Agent 정합 |
| **Task** | ~R | -I ⚠️ | -U | +D (Agent 의존) | 재실행 = 동일 task 인지 미정. identity carrier 모호 | v0.2: Task = template(+R), 재실행 = 신규 ActionRun. v0.1 은 단일 클래스 유지 + 명시적 doc |
| **Policy** | +R | +I | +U | -D | 낮음 — slug + owl:versionInfo identity | 유지 |
| **ActionRun** | +R | +I | +U | +D (Agent + Task 의존) | 낮음 — ulid identity, immutable audit | 유지. PROV-O Activity 정합 |
| **Skill** | +R | +I | +U | +D (Artifact 의존) | 낮음 — slug identity, validated 후만 commit (Voyager pattern) | 유지 |
| **Reflection** | +R | +I | +U | +D (Task/Decision/Artifact 의존) | 낮음 — ulid identity, immutable | 유지 |

---

## 위반 risk 식별 — 4 클래스

### A. Artifact — anti-rigid 혼재 (~R + +R 인스턴스 혼재)

**문제**: "active-tasks.md" 라는 Artifact 는 status (size, last_modified, content) 가 계속 변한다 → anti-rigid. 그러나 "active-tasks.md @ sha256:abc..." 라는 특정 revision 으로 본 같은 객체는 immutable → rigid. 두 관점이 한 클래스에 섞임.

**v0.1 mitigation**: Revision 클래스로 rigid 부분을 분리. Artifact 자체는 anti-rigid container.

**v0.2 권고**: subtype 명시
- `ImmutableArtifact` (+R) — content_hash 가 정의된 시점 그대로
- `MutableArtifactSlot` (~R) — path 가 정의된 시점 그대로지만 내용 가변

단일 클래스 유지 + Revision 으로 rigid 부분 cover 는 v0.1 에서 받아들임.

### B. Service — anti-rigid (status 가변)

**문제**: `quant-bot-live` 는 running / stopped / draining 사이를 오간다. Service 자체는 ~R.

**v0.1 mitigation**: status 를 enum 속성으로 두고 한 클래스로 운영. 즉 "Service 라는 클래스의 인스턴스 정의 = 가동 중이든 멈춰있든 동일 instance".

**v0.2 권고**: subtype 분리
- `ServiceDefinition` (+R) — "quant-bot-live 라는 deployment 의 정의" (이름, 의존성, 코드 reference)
- `ServiceInstance` (~R) — 실제 가동 인스턴스의 상태 스냅샷

ITIL CI 모델과 같은 분해. v0.1 은 통합 유지.

### C. Agent — identity criterion 위험 해소됨 (G1-12 박제)

**문제 (직전)**: AI Agent 의 identity 가 무엇인가? model 인가? name 인가? endpoint 인가?

**v0.1 해소**: G1-12 박제 — `id` (URI) 가 유일한 identity criterion. model 변경, label 변경, tier 변경 모두 동일 agent (alias 추가만).

**예시**:
- `neo://agent/claude-opus-4-7` 에서 model 이 4-7 → 4-8 로 업그레이드 시: 동일 id 유지, model 속성만 갱신, aliases 에 `claude-opus-4-7` 추가
- `senior-da-pm-korean` persona 의 frontmatter 가 v1.2 → v1.3 변경 시: 동일 agent id, frontmatter_revision 만 갱신

### D. Task — identity carrier 모호

**문제**: "ToolPick 100k MAU 작업" task 가 5/13 에 in_progress, 5/14 에 다시 in_progress 가 됐다면 동일 task 인가 다른 task 인가? 재실행이 새 인스턴스인가?

**v0.1 mitigation**: Task = 작업 의도의 단위 (template-like). 재실행은 ActionRun 으로 박제. Task identity = slug or ulid (생성 시 fix).

**v0.2 권고**:
- Task subtype `TaskTemplate` (+R, "P0 #1 9-Layer Kill Switch wiring") vs `TaskExecution` (~R, 실제 한 번의 시도)
- 또는 단일 Task 유지 + ActionRun 의 `kind` 에 `task_execution` 추가

v0.1 은 단일 클래스 유지 + ActionRun 으로 실행 추적.

---

## v0.2 진입 시 적용 권고

| 우선순위 | 작업 | 영향 |
|---|---|---|
| P0 | Agent identity criterion `id` 만 박제 (G1-12 이미 박제) | -I 위험 해소 |
| P0 | Artifact / Service / Task 의 anti-rigid 본성 doc 명시 (이 문서가 그 박제) | 인식 공유 |
| P1 | v0.2 PoC 단계에서 subtype 분리 (`ImmutableArtifact` / `ServiceDefinition` / `TaskTemplate`) 평가 | 학술 정합성 ↑, 운영 비용 ↑ |
| P2 | OOPS! Pitfall Scanner 자동 검증 추가 (`scripts/ontology/validate_ontoclean.py`) | regression 방어 |

---

## 결론

**v0.1 acceptance**: OntoClean Critical 위반 0건 (Agent -I 위험은 G1-12 박제로 해소). 4 클래스의 anti-rigid / identity 모호 본성은 doc 박제로 인식 공유, subtype 분리는 v0.2 PoC 단계에서 평가 후 결정.

이 doc 박제 자체가 G1-21 (OntoClean Tier S 검증 v0.2 진입 전 의무화) 의 실행이다.

---

👤 Strategy Lead Claude Opus 4.7
