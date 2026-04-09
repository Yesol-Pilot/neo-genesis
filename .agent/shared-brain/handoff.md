## 2026-04-09 Codex -> Sora Handoff (GA4 Reporting SSOT)

- 결론: AIForge, CraftDesk, DeployStack, FinStack, SellKit는 개별 GA4 property가 아니라 NeoGenesis - Production (properties/526345390)에서 hostName 필터로 조회해야 한다.
- 검증 근거:
  - GA4 Admin Data Streams에서 NeoGenesis Web stream 확인
  - Measurement ID G-0GVNYZLEMX
  - ToolPick property(524659689)에는 위 5개 host가 없음
- 적용 완료 파일:
  - .agent/knowledge/20260408_GA4_SHARED_PROPERTY_LEARNING.md
  - scripts/ga4_traffic_report.py
  - scripts/ga4_check_streams.py
  - scripts/ga4_traffic_json.py
  - scripts/ga4-all-report.mjs
  - scripts/traffic_alert.py
  - .agent/shared-brain/active-tasks.md
- 운영 메모:
  - 	raffic_alert.py 출력은 Windows cp949 콘솔 호환을 위해 ASCII(-)로 고정
  - .agent 변경 후 python scripts/sync_agent_context.py --force 재실행 완료
- Sora 다음 액션:
  - 주간 자동 리포트가 shared-property 기준으로 유지되는지 모니터링
  - 필요 시 properties/526345390 + hostName 필터 규칙을 신규 SBU에도 동일 적용
# Handoff: Claude Code → Codex

> **작성 시점:** 2026-04-09 (Claude Opus 4.6)
> **사유:** Sora Unified Bible Tier S 설계 완료 → 구현 위임
> **우선순위:** 🟣 Tier S (즉시)

---

## 이번 핸드오프 핵심: Sora 코어 런타임 구현 5건

### 배경
Claude가 3-agent 병렬 리서치(OSS JARVIS / Sora SSOT 인벤토리 / Claude Code 패턴)를 수행하여 `SORA_UNIFIED_BIBLE.md` v1을 작성했다. 오너 지시로 **Owner Sovereignty(오너 주권)** 원칙을 Article 0으로 반영: Sora는 파괴적 명령이라도 고지→확인→수행. 거부권 없음.

설계 산출물(YAML 정책 3개 + Pydantic 계약 15개 모델 + Constitution + Bible)은 모두 완료. 남은 것은 이 스펙에 맞춘 **Python 런타임 구현 5건**.

### 완료된 산출물 (읽기 필수)
1. `.agent/knowledge/SORA_UNIFIED_BIBLE.md` — 7-Layer 아키텍처, 전체 설계 SSOT
2. `.agent/SORA_CONSTITUTION.md` — 8개 Article (Owner Sovereignty, Disclosure Duty, Tier, Anti-Loop 등)
3. `.agent/policies/permissions.yaml` — deny(자기보호 4개만) / ask(고지트리거) / allow(읽기) + owner_override
4. `.agent/policies/blast_radius.yaml` — tier 0-5 분류 + Telegram 고지 템플릿
5. `.agent/policies/capability_tokens.yaml` — subagent 7종 base capability + device tier 교차
6. `.agent/shared-brain/progress-ledger.md` — Magentic-One 2-Ledger 스캐폴드
7. `src/core/contracts/sora_contracts.py` — 15개 Pydantic 모델 (SideEffectBudget, DisclosureBundle, ToolCallEnvelope, SubagentResponse, CapabilityToken, RollbackLedgerEntry, ProgressEntry, HookEvent, HookDecision, OwnerIntent, BusEvent 등)

### 구현 대상 5건 (우선순위 순)

#### 1. Hook Pipeline 4종 (최우선)
- **위치**: `src/core/hooks/` (신규 디렉터리)
- **파일**: `__init__.py`, `session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`
- **스펙**: `SORA_UNIFIED_BIBLE.md` §7.1, `sora_contracts.py`의 `HookEvent`/`HookDecision`
- **핵심**:
  - `session_start`: `.agent/` 스코프 주입 + device_status 로드
  - `user_prompt_submit`: `time_context.py` 주입 + `OwnerIntent` 의도 분류 + core memory prepend
  - `pre_tool_use`: `permissions.yaml` 평가 + `DisclosureBundle` 생성 + Telegram 고지 + 오너 응답 대기
  - `post_tool_use`: audit JSONL + `RollbackLedgerEntry` + `ProgressEntry` 갱신
- **통합 지점**: `src/core/sora_engine.py`의 `process()` 메서드에서 hook 파이프라인 호출

#### 2. Policy Engine (permissions.yaml 로더+평가기)
- **위치**: `src/core/governance/policy_engine.py` (신규)
- **스펙**: `permissions.yaml` 문법 그대로 로드 → tool call 매칭 → `deny|ask|allow` 판정
- **핵심**: deny > ask > allow 평가 순서, `owner_override` 감지 ("그냥 해" etc), device_constraints 적용
- **의존**: `sora_contracts.py`의 `ToolCallEnvelope`, `DisclosureBundle`

#### 3. Intent Classifier (OwnerIntent 생성)
- **위치**: `src/core/nlu/intent_classifier.py` (신규)
- **스펙**: `sora_contracts.py`의 `OwnerIntent` 모델
- **핵심**: Telegram 메시지 → primary_intent 분류 (query/schedule/deploy/analyze/approve/...) + bypass/quiet/force 플래그 감지
- **기존 참고**: `src/core/task_planner.py`의 multi-step 마커 감지 로직 (확장/교체)

#### 4. HITL Gate (Uncertainty-triggered)
- **위치**: `src/core/governance/hitl_gate.py` (신규)
- **스펙**: `SORA_UNIFIED_BIBLE.md` §6.5
- **핵심**: `SubagentResponse.confidence` + device tier별 임계값 (personal-root < 0.70, company-work-pc < 0.95, mobile < 0.80)

#### 5. Progress Ledger 자동 동기화
- **위치**: `post_tool_use.py` 안에 구현 또는 별도 `src/core/hooks/progress_sync.py`
- **스펙**: `progress-ledger.md` schema + stall 판정 (5분 무진전 → stall_count++, 3회 → replan 트리거)

### 구현 원칙
- 모든 I/O는 `sora_contracts.py` 모델 사용. free-text JSON 파싱 금지.
- 기존 `src/core/` 구조 존중. 불필요한 리팩터 금지.
- 각 파일에 `# 참조: SORA_UNIFIED_BIBLE.md §X.X` 주석 남기기.
- 완료 후 `claude_collab.py --mode review`로 Claude 리뷰 요청.

### 완료 후 체크리스트
- [ ] 5개 파일 작성 + import 연결
- [ ] `sora_engine.py`에 hook pipeline 통합
- [ ] 기본 테스트 (최소한 policy_engine 규칙 평가 + intent 분류)
- [ ] `active-tasks.md` Tier S 항목 ✅ 갱신
- [ ] `cross-agent-review.md`에 Claude 리뷰 요청 등록
- [ ] `sync_agent_context.py` 실행

---

## 이전 핸드오프 (2026-04-06, 참고용)

---

## Claude Code 마지막 작업 요약

### 세션 a5ba70d5 (가장 큰 작업, 18MB)
- 50+ 서브에이전트 동원한 대규모 작업
- 작업일: 2026-03-31 ~ 2026-04-06 14:49
- 주요 성과: 마스터 규칙 통합, 소라 God Mode, ComfyUI, GA4

### 세션 28e93999 (오늘 오전)
- 2026-04-06 09:35까지 활동
- 429 Rate Limited로 종료

### 세션 72d01fe7 (간단 질의)
- 소라/마스터규칙 관련 확인 작업

---

## Antigravity가 이어서 처리 가능한 것

1. ✅ Shared Brain 시스템 구축 (완료)
2. 📋 active-tasks.md의 🟡 항목 중 리서치성 작업
3. 📋 NeurIPS 논문 관련 추가 분석
4. 📋 포트폴리오/커리어 관련 문서 작업

## 반드시 Claude Code가 해야 하는 것

1. 🔴 whylab CI/CD 버그 수정 (코드 레벨)
2. 🔴 integrity_hashes.jsonl 수정
3. 🟡 GA4 서비스 계정 키 설정 (env 수정)
4. 🟡 deploy-linux-server.sh 스크립트 작성
5. 🔵 PC Agent systemd 설치

---

## 컨텍스트 (다음 에이전트가 알아야 할 것)

- Claude Code 버전: 2.1.88 (규칙에는 2.0.72 유지라고 되어있지만 실제론 업그레이드됨)
- 9개 claude.exe 프로세스 실행 중 (~864MB)
- `CLAUDE.md` 최종 갱신: 4/5 (259줄, 풀 하드룰)
- `.claude/settings.json`: 풀 퍼미션 + autoUpdatesChannel: latest
- `.claude/projects/D--00-test/` 에 메인 세션 14개 축적

---

## Codex Remote Access Note (2026-04-08 12:00 KST)

- 원격 접근 표준은 `desktop-yesol` 기준으로 정리 완료
- `ysh-server`: `ssh ysh-server`
- `ysh-server` fallback: `tailscale ssh ysh@ysh-server`
- `desktop-sol01`: `ssh desktop-sol01`
- `desktop-sol01` 로그인 사용자: `yesol`
- `desktop-sol01` identity: `~/.ssh/id_ed25519_ysh`
- `desktop-yesol`은 운영 점프 호스트로 사용

