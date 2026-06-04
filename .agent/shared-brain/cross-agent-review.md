# Cross-Agent Review Queue

Use this queue for explicit Codex <-> Claude review handoffs.

Rules:

- Keep each item tied to a concrete diff, file set, or decision.
- Record the requesting agent, the target agent, and the expected output.
- Record the owner goal and review lens, not just the raw task wording.
- Close the item after the finding is integrated or intentionally dismissed.
- Optional or required Claude checkpoints created through `infra/agent-runtime/claude_checkpoint.py` should append a completed record here and store the full transcript under `.agent/shared-brain/claude-checkpoints/`.
- Design or strategy requests must include the multi-agent task-board context: personas, task units, completion criteria, and QA expectations.

Template:

```markdown
- [ ] title
  - requester: codex | claude-code | antigravity | sora
  - target: codex | neo-reviewer | neo-architect | neo-implementer
  - scope: file paths, commit, or subsystem
  - owner_goal: one sentence
  - owner_intent: what outcome the owner actually wants
  - constraints: cost / device / policy / time / rollout constraints
  - assumptions: assumptions already made by the requester
  - personas: pm | da | architect | developer | designer | qa | ops | research | legal/policy
  - task_board: task ids or short task-board summary
  - success_criteria: what must be true for this to count as done
  - qa_gate: what verification or QA evidence is required before completion
  - review_lens: risk | architecture | usability | security | rollout | verification
  - ask: one sentence
  - expected: review | design | patch-plan | verification
```

## Active

- [ ] none

## Completed (recent — 30 days)

이전 entries 는 archive 로 이동.

## Archive

- 2026-04 (85 ccr checkpoints, 4/8~4/24): [`archive/2026-04/cross-agent-review.md`](./archive/2026-04/cross-agent-review.md)
  - 누적 entries: ~594 lines / 39 KB
  - 마이그레이션: 2026-05-12, Strategy Lead Claude Opus 4.7
  - rollback: `archive/backup-20260512-archive/cross-agent-review.md.bak`
