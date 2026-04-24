# Neo Genesis Collaboration Contract

## Scope

This contract applies to:

- all devices in the Neo Genesis fleet
- all supported agent runtimes
- all new sessions started after runtime sync

The collaboration contract is subordinate only to:

1. `.agent/NEO_MASTER_RULES.md`
2. direct owner instructions

## Core Collaboration Shape

> Updated 2026-04-24: owner-facing primary execution shifted from Codex to Claude. Codex remains a full-capability executor and is the designated fallback when Claude token budget is exhausted or when a sustained background/autonomous run is preferred.

- `Claude` is the primary executor, patch integrator, SSOT updater, and owner-facing collaborator.
- `Codex` is the fallback executor and cross-agent reviewer. It is used when Claude token budget is exhausted, when a long autonomous background run is preferred, or when repo-native shell/patch execution is the more economical path.
- `Gemini` is for comparative analysis and research when needed.
- `Sora` is the orchestrator and status surface.
- `Ollama` is the local low-cost support runtime.
- Cross-review remains symmetric: either Claude or Codex may act as the independent reviewer of the other. Review is selective, not mandatory-by-default.
- Design and strategy tasks are not considered complete from discussion alone; they must be decomposed into a task board, executed where feasible, and closed with QA.

## Session Rule

Every session should assume:

- one SSOT under `.agent/`
- one fleet status ledger under `.agent/shared-brain/`
- one shared review queue under `.agent/shared-brain/cross-agent-review.md`

If the runtime supports startup memory loading, it must load the collaboration contract and current shared state automatically.

## Cross-Review Rule (Claude ↔ Codex Symmetric)

Cross-review between the two primary executors (Claude and Codex) is required only when at least one of the following is true:

- the owner explicitly asks for cross-agent review, verification, or discussion
- the task needs complex reasoning, deep tradeoff analysis, conflict convergence, or design validation
- the task affects shared architecture, security policy, auth, credentials, rollback design, or multi-device behavior

If none of those conditions apply, the primary executor may complete the task without a cross-review.

Practical meaning:

- routine implementation, small document edits, straightforward validation, and local housekeeping do not need cross-review by default
- `Gemini` research becomes converged output only when the task itself meets the cross-review conditions above
- `Sora` should escalate to Claude (primary) first; to Codex (fallback) only when Claude is unavailable or token-exhausted
- `Ollama` output is supportive only and may still be adopted without cross-review on low-risk tasks, but not on high-risk shared decisions

## Fallback Handoff (Claude → Codex)

When Claude token budget is exhausted mid-task, or when the owner chooses Codex for a sustained autonomous run:

1. Claude writes a scoped handoff in `.agent/shared-brain/handoff.md` (goal, scope, files touched, pending verification, explicit non-goals)
2. Codex resumes from the handoff, confirms the scope, and preserves the SSOT boundary
3. On return, Codex appends a completion or status entry to the same handoff section
4. Destructive or external actions (G2+) remain owner-gated regardless of which executor is active

## Checkpoint Exemptions

Even when Claude collaboration would otherwise be required, the checkpoint path is exempt for bootstrap and self-maintenance only:

- `scripts/sync_agent_context.py` while regenerating adapters and runtime bundle files
- `infra/agent-runtime/claude_checkpoint.py` and `infra/agent-runtime/claude_collab.py` while repairing the collaboration path itself
- emergency break-fix needed to restore the Claude collaboration path when it is unavailable

## Device Tier Rule

Current fleet tiers:

- `personal-root`: personal control node, highest autonomy
- `gpu-worker`: heavy local inference and build execution
- `company-work-pc`: execution-plane only, restricted for sensitive control
- `company-assigned-personal-server`: orchestrator and server runtime
- `team-mac`: shared Apple build and research node
- `mobile-operator`: approval and monitoring only

Practical rule:

- the more shared or company-owned the device is, the less authority it has over secrets, master configuration, and irreversible actions

## Company Work PC Conflict Rule

If `DESKTOP-YESOL` or any future `company-work-pc` environment conflicts with the personal-root design:

1. record the issue in `.agent/shared-brain/cross-agent-review.md`
2. run an independent risk review with `neo-reviewer`
3. run a convergence/design pass with `neo-conflict-resolver` or `neo-architect`
4. let `Codex` apply the converged design
5. re-sync the runtime across execution nodes

Do not force a unilateral local override on the company work PC if it changes shared behavior or SSOT semantics.

## Sensitive Action Rule

On `company-work-pc` and `team-mac` tiers:

- do not change master credentials
- do not redefine SSOT without review
- do not treat local environment quirks as canonical architecture without cross-review

## Conflict Resolution Output

A conflict is considered resolved only when all of the following are true:

- the converged design is written into SSOT
- the runtime revision is regenerated
- the execution nodes are re-synced
- the review queue entry is closed or explicitly deferred

## Preferred Tools

- use `cross-agent-review.md` for bounded review requests
- use `neo-reviewer` for bug/risk review
- use `neo-architect` for tradeoff and rollout design
- use `neo-conflict-resolver` for environment or policy conflicts
- use `claude_checkpoint.py` when Claude collaboration is explicitly requested or required by task complexity
- use `claude_collab.py` as the low-level model router for normal Claude entrypoints

## Completion Gate

If Claude collaboration was explicitly requested or required by the selective collaboration rule, the task is eligible for final owner-facing completion only when all of the following are true:

- a Claude checkpoint file exists under `.agent/shared-brain/claude-checkpoints/`
- the checkpoint summary is written to `.agent/shared-brain/cross-agent-review.md`
- any material Claude finding is integrated, rebutted with evidence, or explicitly deferred

If the task did not require Claude collaboration under this contract, no checkpoint is needed for final completion.

## Goal-Intent Review Protocol

When `Codex` asks `Claude` to review a design or change, the review is valid only if all of the following are true:

- the handoff states the owner's primary goal, secondary goals, explicit constraints, and non-goals
- the handoff states the expected success criteria and the decision that is actually needed
- `Claude` restates the owner's goal and intent before critique
- `Claude` evaluates the proposal from an objective and cold perspective, not an agreement-first perspective
- `Codex` either integrates, rebuts with evidence, or explicitly defers each material finding

Required review lenses:

- goal fit
- hidden assumptions
- operational and security risk
- usability and owner experience
- maintenance burden
- test and rollback strategy

If the review reveals that the current proposal optimizes for the wrong goal, the converged output must replace the original proposal rather than merely annotate it.

## Multi-Agent Design Execution Rule

When the owner asks for design, strategy, roadmap, architecture, restructuring, or “make it complete” style work:

- reconstruct the owner goal and non-goals first
- choose the necessary personas from `PM`, `DA`, `Architect`, `Developer`, `Designer`, `QA`, `Ops`, `Research`, `Legal/Policy`
- create a task board before broad implementation
- ensure every task has owner, scope, output, done criteria, and QA gate
- finish with verification evidence, not narrative confidence

Practical meaning:

- no taskless strategy documents
- no owner-facing “done” status without QA
- no design output that omits execution sequencing when execution is feasible
