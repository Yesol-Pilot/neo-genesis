# Personal Context Routing

> Purpose: make agents aware that the owner's personal/legal context is already organized locally, without copying sensitive contents into shared prompts.
> Scope: applies to Codex, Claude Code, Antigravity/Gemini, Sora, and any generated runtime adapter.
> Sensitivity: HIGH. This is a routing/index document only.

## Rule

`D:\00.test\personal` is the protected local root for the owner's personal legal and financial records.

Agents must not inspect, index, summarize, move, upload, or share this root by default. Access is allowed only when the owner explicitly asks about personal legal, rehabilitation, debt, finance, court, law-firm, or related private context.

When access is allowed, use the smallest necessary file set and prefer existing trackers over raw evidence.

## Entry Points

- `D:\00.test\personal\PROJECT_SPEC.md` - folder purpose and handling rules.
- `D:\00.test\personal\전체자료_마스터인덱스.xlsx` - inventory of organized files.
- `D:\00.test\personal\01_사건서류\legal_case_status.md` - current case status tracker.
- `D:\00.test\personal\05_전략보고서\` - strategy reports and risk memos.
- `D:\00.test\personal\08_법무법인_제출용\` - law-firm submission packages and checklists.

## Workflow

1. Confirm the owner's request explicitly relates to the private context above.
2. Read `PROJECT_SPEC.md` and the master index first.
3. For current rehabilitation/court status, read `01_사건서류\legal_case_status.md` before asking the owner to restate facts.
4. For strategy/risk questions, check the newest matching report under `05_전략보고서\`.
5. If new facts are learned from owner-provided messages, update the relevant tracker/report instead of leaving the context only in chat.
6. Do not copy raw personal records into `.agent`, shared-brain, public repos, prompts, screenshots, or external services.

## Current Known Trackers

- `D:\00.test\personal\01_사건서류\legal_case_status.md`
- `D:\00.test\personal\05_전략보고서\20260512_슈퍼센트_이직_리스크_추적.md`

## Reporting

When responding, cite only the specific local tracker paths used. Do not quote credentials, account numbers, resident-registration-like numbers, court-access secrets, or private third-party contact details.
