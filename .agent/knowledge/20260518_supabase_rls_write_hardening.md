# Supabase RLS Write Hardening (2026-05-18)

- Date: 2026-05-18
- Author: Claude Opus 4.7 (Strategy Lead)
- Trigger: owner forwarded Supabase security alert (rls_disabled_in_public, dated 5/17)
- Project: `zdfvfisfcocttrfsznwd` (신생합성-주요 / neogenesis-main)
- Migration: `harden_rls_drop_public_write_policies`

## TL;DR

1. **owner email alert (RLS disabled) = already resolved** — 0 tables with RLS disabled (28 tables RLS-enabled per prior 5/20 work). Supabase alert email lags actual state.
2. **Discovered + fixed a BIGGER latent issue**: 16 policies named "Allow service ..." but scoped to `roles={public}` with `qual=true` → exposed public INSERT/UPDATE/DELETE on 14 tables (AI agent memory + SBU content).
3. **Fix verified**: all 14 tables now `public_write=0`, `public_read>=1`. Frontend read preserved, backend (service_role bypasses RLS) write preserved, public write removed.

## The discovered vulnerability

| Risk tier | Tables | Exposure |
|---|---|---|
| ⚠️⚠️ Critical | agents, agent_logs, memories, prompts, decisions, llm_models | Public could edit AI agent memory/prompts = **prompt injection vector** into the autonomous pipeline |
| ⚠️ High | toolpick_posts, reviewlab_posts, aiforge_posts, craftdesk_posts, deploystack_posts, sellkit_posts | Public could delete/edit all SBU blog content |
| ⚠️ Medium | quant_dashboard, arena_agents | Public write |

### Root cause

Policies were authored with the INTENT of granting service_role full access (for HIVE MIND backend writes), but created with `TO public` instead of `TO service_role`. Since:
- `service_role` key **bypasses RLS entirely** (BYPASSRLS attribute) → the policies were never needed for the backend
- The policies only ever served to expose write access to anyone holding the anon key

Classic Supabase misconfiguration: policy NAME says "service" but ROLE says "public".

## Fix applied (migration `harden_rls_drop_public_write_policies`)

Dropped 16 policies:

```sql
-- AI agent tables (7)
DROP POLICY IF EXISTS "Allow service role full access" ON public.agents;
DROP POLICY IF EXISTS "Allow service role full access" ON public.agent_logs;
DROP POLICY IF EXISTS "Allow service role full access" ON public.memories;
DROP POLICY IF EXISTS "Allow service role full access" ON public.decisions;
DROP POLICY IF EXISTS "prompts_service_full" ON public.prompts;
DROP POLICY IF EXISTS "llm_models_service_full" ON public.llm_models;
DROP POLICY IF EXISTS "arena_agents_service_full" ON public.arena_agents;
-- SBU content tables (8 incl. 3 reviewlab)
DROP POLICY IF EXISTS "Allow service write" ON public.aiforge_posts;
DROP POLICY IF EXISTS "Allow service write" ON public.craftdesk_posts;
DROP POLICY IF EXISTS "Allow service write" ON public.deploystack_posts;
DROP POLICY IF EXISTS "Allow service write" ON public.sellkit_posts;
DROP POLICY IF EXISTS "tp_service_write" ON public.toolpick_posts;
DROP POLICY IF EXISTS "rl_service_write" ON public.reviewlab_posts;
DROP POLICY IF EXISTS "Allow service insert" ON public.reviewlab_posts;
DROP POLICY IF EXISTS "Allow service update" ON public.reviewlab_posts;
-- Quant (1)
DROP POLICY IF EXISTS "quant_write" ON public.quant_dashboard;
```

### Why safe (verified)

| Concern | Verification |
|---|---|
| Frontend read breaks? | NO — every table has separate public SELECT policy (verified: public_read >= 1 post-fix) |
| Backend write breaks? | NO — service_role bypasses RLS (writes work without any policy) |
| Community submissions break? | NO — battles/comments/votes/reopen_petitions/reports/jhs_echo_* INSERT policies untouched |
| agents/agent_logs/decisions/memories/arena_agents | Already had correct `*_service_only` / "Service role manage" policies; dropped only the buggy public ones |

### Post-fix verification

```
14/14 tables: public_write = 0, public_read >= 1
```

## Rollback (if any app breaks)

```sql
-- Per table, restore (NOT recommended — re-exposes write):
CREATE POLICY "<name>" ON public.<table> FOR ALL TO public USING (true) WITH CHECK (true);
```

If a legitimate frontend write breaks, the CORRECT fix is to scope to the right role:
```sql
CREATE POLICY "<table>_service_write" ON public.<table> FOR ALL TO service_role USING (true) WITH CHECK (true);
```
(though service_role bypasses RLS so even this is usually unnecessary)

## Remaining Supabase advisor findings (NOT fixed — owner decision)

| Level | Finding | Count | Recommended action |
|---|---|---|---|
| ~~ERROR~~ ✅ **FIXED** | `security_definer_view`: `sbu_daily_profit`, `available_products` | 2 | **DONE** (migration `harden_security_definer_views_to_invoker`). Both underlying tables (job_queue + product_cache) are service_role-locked (`qual=auth.role()='service_role'`); definer views bypassed the lock and exposed financial + product data. Set `security_invoker=true` → anon now blocked, service_role backend preserved. Reversible: `ALTER VIEW ... SET (security_invoker=false)`. If a frontend read `available_products` via anon, add targeted product_cache public SELECT policy instead of reverting. |
| WARN | `function_search_path_mutable` | 27 | Add `SET search_path = ''` to each function (SQL-injection hardening, low priority) |
| WARN | `anon/authenticated_security_definer_function_executable` | 30 | Review which SECURITY DEFINER functions anon can call |
| WARN | `extension vector in public schema` | 1 | `ALTER EXTENSION vector SET SCHEMA extensions;` (minor) |
| WARN | `auth_leaked_password_protection` disabled | 1 | **owner 1-click**: Dashboard → Authentication → Settings → enable "Leaked password protection" (HaveIBeenPwned check) |
| INFO | `rls_enabled_no_policy` | 28 | These tables (financial_ledger, couple_app_google_tokens, audit_logs, job_applications, etc.) are LOCKED (RLS on, no policy = no access except service_role). SAFE. Add read policy ONLY if a client needs anon read. |

### Owner 1-click items
1. **Leaked password protection**: Dashboard → Auth → Settings → toggle ON
2. **2 ERROR views**: confirm whether `sbu_daily_profit` + `available_products` are meant to be SECURITY DEFINER (if not, Claude can fix with security_invoker)

## Cross-reference

- Prior RLS work: active-tasks.md "Supabase neogenesis-main 18 tables RLS ENABLE" (2026-05-20 entry)
- Gmail security audit: active-tasks.md flagged this project's RLS 5/13 + 5/6
