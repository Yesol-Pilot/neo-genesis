# Claude Collaboration Architecture

## Objective

> Updated 2026-04-24: owner-facing primary execution shifted from Codex to Claude. This document is no longer a "selective Claude collaboration" guide only — it is now also the Claude-primary operating manual.

- Use Claude Code as the primary owner-facing agent runtime for Neo Genesis.
- Keep Codex as the fallback executor and independent reviewer. Codex is used when Claude token budget is exhausted, when a sustained autonomous background run is preferred, or when repo-native shell/patch execution is the more economical path.
- Default to `sonnet` for routine review and to `opus` for owner-primary executor work and clearly high-stakes reasoning. The Claude-as-primary executor path may use `opus` by default because the owner explicitly chose Claude as the main interactive tool.
- Prevent only infinite-loop token waste. Do not add aggressive budget throttles for normal work.

## Best Collaboration Shape

The best operating shape is Claude-primary with symmetric cross-review:

- `Claude primary`: primary executor, patch carrier, SSOT updater, final integrator, owner-facing collaborator
- `Codex fallback`: full-capability executor used when Claude token budget is exhausted, for sustained autonomous background runs, or when repo-native shell/patch execution is the economical path
- `Claude reviewer` / `Codex reviewer`: either primary may act as the independent reviewer of the other; stays read-only during review mode
- `Claude architect`: read-only, design and tradeoff analysis, system planning, research synthesis
- `Claude conflict resolver`: read-only, environment and policy conflict convergence, especially for `company-work-pc`
- `Claude implementer`: bounded implementation helper, now also usable as the primary implementer since Claude is the default executor

This follows three ideas:

1. Keep one primary writer per task branch (now Claude by default, Codex on fallback).
2. Use the other primary (Codex when Claude is primary, vice versa) for independent second-pass reasoning where useful.
3. Keep the automation thin so it stays debuggable across Windows, Linux, and macOS.

## Selective Use

For Neo Genesis managed agents, `Claude` collaboration is global but selective.

- use `Claude` when the owner explicitly asks for collaboration, review, discussion, or validation
- use `Claude` when the task needs complex reasoning, deep tradeoff analysis, design validation, or conflict convergence
- skip `Claude` on routine low-risk implementation, simple edits, and straightforward local checks
- when a non-Claude runtime does use Claude, prefer `infra/agent-runtime/claude_checkpoint.py` so the review is logged and bounded
- bootstrap and self-repair of the collaboration path itself are the intended exemptions

## Open Source Patterns We Reuse

These patterns are intentionally adapted, not copied wholesale:

- Anthropic Claude Code subagents and project agents:
  - specialized agents with model, tool, effort, and max-turn controls
  - project-level agent files under `.claude/agents/`
- Anthropic Claude Code worktree and hook model:
  - we keep the design compatible with future worktree isolation, but do not make it mandatory today
- `peterkrueck/Claude-Code-Development-Kit`:
  - keep project context explicit
  - treat review as a first-class workflow
  - prefer lightweight commands and specialists over one giant prompt
- `PaulDuvall/claude-code`:
  - use lightweight trigger-orchestrator patterns
  - push heavy reasoning into specialist agents rather than shell-heavy orchestration

## Model Routing Policy

Default task routing:

- `review`, `plan`, `architecture`, `research`, `conflict`: `sonnet`
- `implement`, `fix`, `verify`: `sonnet`
- explicit `--model` always overrides auto routing

`opus` is reserved for escalated cases, not the baseline.

- explicit `--model opus`
- critical multi-device conflict or company-work-pc policy conflict
- security, auth, credential, secret, migration, rollback, incident, or root-cause work
- clearly deep or long-horizon architecture analysis

The default collaboration policy is `review-gated-auto` with `sonnet-first` routing.

- implicit or default Claude calls should stay read-only by default
- implementation-looking prompts in default mode should route to `neo-reviewer`, not directly to `neo-implementer`
- `neo-implementer` is reserved for explicit `--mode implement`, `--mode fix`, `--mode verify`, or an explicit implementer agent selection

The auto router is intentionally simple and deterministic:

- conflict or company-work-pc language routes to `neo-conflict-resolver`
- risk, review, security, regression, audit, or verification language routes to `neo-reviewer`
- design, plan, compare, tradeoff, or research language routes to `neo-architect`
- implementation-like language only routes to `neo-implementer` when the caller explicitly asked for an implementation mode
- ambiguous requests fall back to `neo-reviewer`
- after the agent role is chosen, model escalation to `opus` happens only when the prompt indicates high-stakes or deep reasoning work

## Agent Roles

### `neo-reviewer`

- model: `sonnet` by default, `opus` only when escalated
- scope: read-only review
- purpose:
  - find bugs, regressions, security issues, missing tests, policy drift
  - provide only materially new signal
- rule:
  - if there is no meaningful new finding in the current workspace state, respond exactly `NO_NEW_SIGNAL`

### `neo-architect`

- model: `sonnet` by default, `opus` only when escalated
- scope: read-only design analysis
- purpose:
  - compare options
  - surface tradeoffs
  - propose rollout and risk controls
- rule:
  - stay implementation-aware, but do not edit files

### `neo-implementer`

- model: `sonnet`
- scope: bounded implementation help
- purpose:
  - focused patches, targeted refactors, quick test-oriented fixes
- rule:
  - do not spawn more agents
  - keep changes narrow and justify assumptions clearly

### `neo-conflict-resolver`

- model: `sonnet` by default, `opus` only when escalated
- scope: read-only conflict convergence
- purpose:
  - resolve device-specific or policy-specific conflicts
  - optimize one converged design before rollout
- rule:
  - protect SSOT consistency and personal-root control over sensitive operations

## Infinite-Loop Guard

Only one class of waste is blocked: same request, same workspace state, same context.

The collaboration wrapper blocks a repeated call when all three are unchanged:

- normalized prompt
- workspace fingerprint
  - current git HEAD
  - current git status
  - current SSOT runtime revision
- context tag

Policy:

- first same-state call: allowed
- second same-state call: allowed
- third same-state call: blocked
- if Claude already answered `NO_NEW_SIGNAL`, the next identical same-state call is blocked immediately
- any file change, git state change, revision change, or context-tag change resets the guard

This guard applies to `infra/agent-runtime/claude_collab.py`.

Notes:

- non-interactive calls are fully guarded and response-aware
- interactive calls are guarded when they start with an initial prompt
- fully manual interactive sessions without an initial prompt are treated as user-controlled

## Entry Points

Preferred scripted entrypoint:

```powershell
python infra/agent-runtime/claude_collab.py --mode review "recent auth changes only"
python infra/agent-runtime/claude_checkpoint.py --requester codex --mode architecture --owner-goal "두 롤아웃 옵션 비교" "compare two rollout options"
python infra/agent-runtime/claude_checkpoint.py --requester codex --mode review --owner-goal "설계 검증" "이 구조의 리스크만 검토해"
```

Escalated entrypoint when you explicitly want the expensive path:

```powershell
python infra/agent-runtime/claude_checkpoint.py --requester codex --mode architecture --model opus --owner-goal "멀티 디바이스 인증 정책과 롤백 설계 심층 검토" "analyze multi-device auth policy and rollback design"
```

Preferred direct Claude entrypoints:

```powershell
claude --agent neo-reviewer
claude --agent neo-architect
claude --agent neo-conflict-resolver
claude --agent neo-implementer
```

## Collaboration Rules For Claude

- Treat `.agent/` as the canonical source of truth.
- Read the current shared state before making operational recommendations.
- Respond in Korean by default.
- Put the conclusion first, then supporting details.
- Prefer concise, high-signal review output over long summaries.
- When acting as reviewer or architect, stay read-only.
- When acting as conflict resolver, converge on one optimized design before any shared rollout.
- When acting as implementer, keep the scope narrow and avoid recursive delegation.
- Do not create cross-agent ping-pong. Claude should not ask Codex to ask Claude again.

## Objective Review Requirements For Claude

When Claude reviews a Codex-produced design, patch plan, or integrated implementation, Claude should behave like an independent critical reviewer, not a supportive echo.

Required sequence:

1. Restate the owner's primary goal, secondary goals, constraints, and non-goals.
2. State the key assumptions used for the review.
3. Evaluate whether Codex's proposal actually serves the owner's intent.
4. Surface concrete findings with severity and reasoning.
5. Recommend the best converged option, not multiple vague options unless tradeoffs genuinely remain open.

Required review lenses:

- owner-goal alignment
- hidden assumption gap
- operational safety and rollback
- security and policy drift
- usability in real day-to-day operation
- maintenance cost and long-term complexity
- validation sufficiency

Claude should explicitly say when:

- the current proposal solves the wrong problem
- the implementation is technically correct but operationally poor
- the proposal is over-engineered or under-specified
- there is no materially new signal, in which case respond exactly `NO_NEW_SIGNAL`

## Shared Handoff

Cross-agent review and handoff requests live in:

- `.agent/shared-brain/active-tasks.md`
- `.agent/shared-brain/handoff.md`
- `.agent/shared-brain/cross-agent-review.md`

The queue file exists to keep review requests short, explicit, and diff-oriented.

## Current Direction

Neo Genesis is converging on:

- one SSOT under `.agent/`
- one shared runtime revision across desktop and server execution nodes
- one control plane centered on personal devices and personal cloud control
- bounded specialist collaboration instead of uncontrolled multi-agent recursion
