"""Neo Genesis Business Ontology v0.1 extractor.

Per DESIGN_business_v0.1.md. 추출 대상:
- Founder × 1 (허예솔, 사업자 대표)
- Product × 16 (12 SBU + 2-3 paper + 1 game + 1 brand)
- Domain (사업자 명의 등록 도메인)
- Strategy + RevenueStream (Revenue Path Research v1)
- Investment (D2 ETF / D1 예금 등)
- ResearchIP (KoreanLLM / EthicaAI / WhyLab)
- Lead (koreanllm.org B2B target)
- KPI (per Product, MAU/ARR — initial seed)
- Decision (G1 박제 from handoff)

BOUNDARY (절대 in-scope 외):
- CTS-AI 클라이언트 (owner = employer 직원 context, Neo Genesis 가 아님)
- JD applications (owner = 구직자, Neo Genesis 와 별개)
- 9 master resume PDF (owner career asset, Neo Genesis founder 가 가진 personal asset 으로 reference 가능, 자산은 아님)
- 가족 / 법무 / 금융 / 개인회생

출력: `.agent/ontology/business/nodes.jsonl` + `edges.jsonl` (별도 디렉토리,
meta 와 분리. validate.py 가 union 로드해서 검증).

Usage:
    python scripts/ontology/business/extract_business.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_D = REPO_ROOT.parent  # D:/00.test
AGENT_DIR = REPO_ROOT / ".agent"
BIZ_DIR = AGENT_DIR / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"
EDGES_PATH = BIZ_DIR / "edges.jsonl"
REPORT_PATH = BIZ_DIR / "extract_report.json"

# Personal forbidden — ABSOLUTE skip (founder 의 다른 context)
PERSONAL_FORBIDDEN = {"personal/", "_secrets/", "/cts-projects.json", "/saramin", "/jobkorea"}

# Provenance vocabulary — fabrication 명시
PROV_HARDCODED = "hardcoded_strategy_lead_seed"  # 내 추정 / 직접 입력 (verify needed)
PROV_DOC_EXTRACTED = "extracted_from_doc"  # SSOT 문서에서 정확히 추출
PROV_PLACEHOLDER = "placeholder_pending_real_data"  # 실 데이터 도착 시 교체
PROV_OBSERVED = "observed_from_live_source"  # 실 API / 측정값


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


class BizExtractor:
    def __init__(self) -> None:
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.now = now_iso()

    def add_node(self, node: dict) -> str:
        if "created_at" not in node:
            node["created_at"] = self.now
        if "updated_at" not in node:
            node["updated_at"] = self.now
        self.nodes.append(node)
        return node["id"]

    def add_edge(self, rel_type: str, from_: str, to: str, props: dict | None = None) -> None:
        eid = f"neo://biz/relation/{rel_type}/{short_hash(from_+to+rel_type)}"
        e = {
            "id": eid,
            "type": rel_type,
            "from": from_,
            "to": to,
            "observed_at": self.now,
        }
        if props:
            e["linkProperties"] = props
        self.edges.append(e)

    # ============================================================
    # 1. Founder (hardcoded seed — 1 entity, Neo Genesis 대표)
    # ============================================================
    def extract_founder(self) -> str:
        founder_id = "neo://biz/founder/yesol-heo"
        self.add_node({
            "id": founder_id,
            "rdf_type": "biz:Founder",
            "label": "허예솔",
            "name_kr": "허예솔",
            "name_en": "Yesol Heo",
            "business_registration_partial": "630-17-*****",  # full = personal-forbidden
            "role": ["founder", "strategy_lead", "developer", "researcher"],
            "capabilities_summary": [
                "product_management",
                "ai_orchestration",
                "korean_llm_research",
                "strategy",
                "growth",
                "decision_authority",
            ],
            "markings": ["internal"],
            "neo_genesis_role": "Strategy Lead + sole founder (개인사업자, 일반과세자)",
            "provenance": PROV_DOC_EXTRACTED,
            "provenance_source": "사업자등록증 + handoff.md 2026-05-14 koreanllm migration entry",
        })
        return founder_id

    # ============================================================
    # 2. Product (SBU + papers + game + brand)
    # ============================================================
    def extract_products(self, founder_id: str) -> list[str]:
        products = [
            # 12 SBU
            ("kott", "sbu_saas", "live", "K-OTT subscription rotation", ["kott.kr"]),
            ("toolpick", "sbu_saas", "live", "ToolPick SaaS reviews + alternatives", ["toolpick.dev"]),
            ("ur-wrong", "sbu_saas", "live", "UR WRONG argument benchmark", ["ur-wrong.com"]),
            ("reviewlab", "sbu_saas", "live", "ReviewLab product reviews", []),
            ("sellkit", "sbu_saas", "live", "SellKit ecommerce decision UX", []),
            ("deploystack", "sbu_saas", "live", "DeployStack DevOps decision aid", []),
            ("aiforge", "sbu_saas", "live", "AIForge AI tools for developers", []),
            ("craftdesk", "sbu_saas", "live", "CraftDesk design/Figma resources", []),
            ("finstack", "sbu_saas", "live", "FinStack financial decision", []),
            ("whylab", "sbu_saas", "live", "WhyLab causal inference platform (live + paper companion)", []),
            ("sora-app", "sbu_saas", "live", "Sora app — AI assistant frontend", []),
            ("koreanllm", "sbu_saas", "idea", "koreanllm.org AO-1 (W0 = 2026-06-10, D-27)", ["koreanllm.org"]),
            # 2 papers (Neo Genesis IP)
            ("ethicaai-paper", "paper", "live", "EthicaAI Melting Pot manuscript (blind review)", []),
            ("whylab-paper", "paper", "live", "WhyLab causal inference manuscript (blind review)", []),
            # 1 game
            ("2dlivegame", "game", "paused", "NEO-GENESIS: Antigravity 2D live game", []),
            # 1 brand
            ("heoyesol-brand", "brand_site", "live", "heoyesol.kr personal brand HQ + /resume tool", ["heoyesol.kr"]),
        ]
        ids = []
        for slug, kind, stage, label, domains in products:
            pid = f"neo://biz/product/{slug}"
            ids.append(pid)
            self.add_node({
                "id": pid,
                "rdf_type": "biz:Product",
                "kind": kind,
                "stage": stage,
                "label": label,
                "slug": slug,
                "meta_project": f"neo://project/{slug}",  # cross-link to meta
                "markings": ["public" if kind == "sbu_saas" else "internal"],
            })
            self.add_edge("biz:owns", founder_id, pid)
            # Cross-link to meta Project (if exists)
            self.add_edge("biz:cross_ref_meta", pid, f"neo://project/{slug}",
                          props={"meta_class": "Project"})
            # deployed_at domains
            for d in domains:
                self.add_edge("biz:deployed_at", pid, f"neo://biz/domain/{d}")
        return ids

    # ============================================================
    # 3. Domain (사업자 명의 등록 도메인)
    # ============================================================
    def extract_domains(self) -> list[str]:
        # 13 GSC properties + koreanllm.org (Cloudflare 신규 등록)
        domains = [
            ("kott.kr", "Cloudflare", "2027-05-14"),
            ("toolpick.dev", "Cloudflare", None),
            ("ur-wrong.com", "Cloudflare", None),
            ("heoyesol.kr", "Cloudflare", None),
            ("koreanllm.org", "Cloudflare", "2027-05-14"),
            ("neogenesis.app", "Cloudflare", None),
            # ReviewLab / SellKit / DeployStack / AIForge / CraftDesk / FinStack / WhyLab / sora-app
            # 정확한 도메인은 별도 확인 필요 — 본 PoC 단계에선 known main 6개만
        ]
        ids = []
        for host, registrar, expires_at in domains:
            did = f"neo://biz/domain/{host}"
            ids.append(did)
            node = {
                "id": did,
                "rdf_type": "biz:Domain",
                "host": host,
                "label": host,
                "registrar": registrar,
                "owned_by_business": True,
                "markings": ["public"],
            }
            if expires_at:
                node["expires_at"] = expires_at
            self.add_node(node)
        return ids

    # ============================================================
    # 4. Strategy + RevenueStream (Revenue Path Research v1)
    # ============================================================
    def extract_strategy_and_revenue(self, founder_id: str) -> None:
        # Strategy Revenue Path v1 (2026-05-12 박제)
        strategy_id = "neo://biz/strategy/revenue-path-v1"
        self.add_node({
            "id": strategy_id,
            "rdf_type": "biz:Strategy",
            "label": "Revenue Path Research v1",
            "source_artifact": "neo://artifact/20260512_REVENUE_PATH_RESEARCH_v1",
            "framework_type": "revenue_path",
            "effective_from": "2026-05-12",
            "markings": ["internal"],
        })

        # 13 revenue paths (per .agent/shared-brain/active-tasks.md 2026-05-12 entry)
        paths = [
            # (id_slug, path_id, category, expected_monthly_revenue, status)
            ("a1-quant-other-asset", "A1", "quant", "-20%~+15%", "rejected"),
            ("a2-asset-management", "A2", "consulting", "연 5~12%", "deferred"),
            ("a3-hummingbot-saas", "A3", "saas", "0~1%/월", "rejected"),
            ("a4-robo-advisor", "A4", "consulting", "연 5~10%", "deferred"),
            ("b1-sbu-acceleration", "B1", "saas", "본업+α", "recommended"),
            ("b2-cts-ai-base-salary", "B2", "consulting", "연봉 5~15%", "active"),
            ("b3-ai-consulting", "B3", "consulting", "0~500만/월", "pilot"),
            ("c1-agentic-saas", "C1", "saas", "50만~5000만/월", "deferred"),
            ("c2-info-product", "C2", "info_product", "1500만~5억 누적", "recommended"),
            ("c3-affiliate-ads", "C3", "affiliate", "0~500만/월", "active"),
            ("d1-deposit-cma", "D1", "deposit", "연 3~4%", "recommended"),
            ("d2-us-etf", "D2", "index_fund", "연 7~10%", "recommended"),
            ("d3-real-estate-reits", "D3", "real_estate", "연 4~7%", "deferred"),
        ]
        for slug, path_id, category, expected, status in paths:
            rs_id = f"neo://biz/revenue_stream/{slug}"
            self.add_node({
                "id": rs_id,
                "rdf_type": "biz:RevenueStream",
                "label": f"{path_id} {slug}",
                "path_id": path_id,
                "category": category,
                "expected_monthly_revenue": expected,
                "status": status,
                "markings": ["internal"],
            })
            # Strategy defines RevenueStream
            self.add_edge("biz:defines", strategy_id, rs_id)

    # ============================================================
    # 5. Investment (Capital allocation)
    # ============================================================
    def extract_investments(self, founder_id: str) -> None:
        # Per Revenue Path Research v1 권고 — 자본 1000~8000만 분산
        investments = [
            ("d2-us-etf", "etf", 50.0, "planned", "S&P 500 / QQQ — 40~60% 보수 자본보호"),
            ("d1-deposit-cma", "deposit", 15.0, "planned", "예금 / CMA — 10~20% 유동성"),
            ("b1-sbu-ad-budget", "sbu_ad_budget", 20.0, "planned", "11 SBU 가속 광고비 — 30~40% 성장"),
            ("c2-info-product-pilot", "cash", 5.0, "planned", "정보재/강의 제작 — passive compounding seed"),
            ("a4-robo-advisor-optional", "etf", 5.0, "planned", "robo-advisor 보조 — 0~10% 선택"),
        ]
        for slug, kind, share_pct, status, rationale in investments:
            inv_id = f"neo://biz/investment/{slug}"
            self.add_node({
                "id": inv_id,
                "rdf_type": "biz:Investment",
                "kind": kind,
                "label": slug,
                "target_share_pct": share_pct,
                "current_balance_status": status,
                "rationale_artifact": "neo://artifact/20260512_REVENUE_PATH_RESEARCH_v1",
                "rationale_note": rationale,
                "markings": ["internal"],
                "provenance": PROV_DOC_EXTRACTED,
                "provenance_source": "Revenue Path Research v1 (2026-05-12) target_share recommendation. 실 자본 배분 0 — current_balance_status=planned 명시.",
            })
            self.add_edge("biz:allocates", founder_id, inv_id)

    # ============================================================
    # 6. ResearchIP (Neo Genesis 가 보유한 IP)
    # ============================================================
    def extract_research_ip(self, founder_id: str) -> None:
        research_ips = [
            ("koreanllm-ao1", "leaderboard", "wip", 287000,
             "Korean+English+Japanese Trilingual LLM/Embedding/Reranker Leaderboard with Academic Citation Backbone (W0=2026-06-10, D-27)",
             None, "neo://artifact/koreanllm-ao1-docs-root"),
            ("ethicaai-melting-pot", "paper_manuscript", "blind_review", 12000,
             "EthicaAI Melting Pot manuscript (NeurIPS double-blind review)",
             "NeurIPS 2026 (planned)", "neo://artifact/PAPER-EthicaAI-NeurIPS2026"),
            ("whylab-causal-inference", "paper_manuscript", "blind_review", 8000,
             "WhyLab causal inference manuscript",
             "double-blind venue (TBD)", "neo://artifact/PAPER-WhyLab"),
        ]
        for slug, kind, status, word_count, label, venue, meta_root in research_ips:
            rid = f"neo://biz/research_ip/{slug}"
            node = {
                "id": rid,
                "rdf_type": "biz:ResearchIP",
                "label": label[:80],
                "slug": slug,
                "kind": kind,
                "status": status,
                "total_word_count": word_count,
                "markings": ["internal"],
            }
            if venue:
                node["venue"] = venue
            if meta_root:
                node["meta_artifact_root"] = meta_root
            self.add_node(node)
            self.add_edge("biz:produced", founder_id, rid)

    # ============================================================
    # 7. Lead (잠재 고객 — koreanllm.org B2B target 등)
    # ============================================================
    def extract_leads(self, founder_id: str) -> None:
        """Lead 박제 — 가짜 prospect placeholder 제거.

        v0.1 정정 (cold honest 후): 실 prospect identity 0 단계에서
        12 placeholder 노드 박제는 fabrication. 2 LeadCategory 만 박제하고
        실 outreach 발생 시 instance 추가.
        """
        lead_categories = [
            ("koreanllm-b2b-enterprise", "b2b_enterprise",
             "neo://biz/revenue_stream/b1-sbu-acceleration",
             "neo://biz/product/koreanllm",
             "$30K~$80K (ARR) × 6-12 customers planned",
             "koreanllm.org AO-1 plan B2B target. 실 identity 0 (W0 launch 후 outreach 시작 예정).",
             0),  # actual_prospect_count = 0
            ("b3-ai-consulting", "consulting_client",
             "neo://biz/revenue_stream/b3-ai-consulting",
             None,
             "0~500만/월 per engagement",
             "B3 path consulting potential. 실 contact 0.",
             0),
        ]
        for slug, lead_type, rs, product, value, note, actual_count in lead_categories:
            lead_id = f"neo://biz/lead_category/{slug}"
            node = {
                "id": lead_id,
                "rdf_type": "biz:LeadCategory",  # 클래스 변경: Lead → LeadCategory (fabrication 명시)
                "label": f"Lead category: {slug}",
                "lead_type": lead_type,
                "target_revenue_stream": rs,
                "expected_value_per_prospect_usd": value,
                "actual_prospect_count": actual_count,
                "engagement_stage": "no_prospects_yet" if actual_count == 0 else "active",
                "note": note,
                "markings": ["internal"],
                "provenance": PROV_DOC_EXTRACTED,
                "provenance_source": "Revenue Path Research v1 + koreanllm.org AO-1 plan",
            }
            if product:
                node["target_product"] = product
                self.add_edge("biz:targets_lead_category", product, lead_id)
            self.add_node(node)

    # ============================================================
    # 8. KPI (per Product, initial seed)
    # ============================================================
    def extract_kpis(self) -> None:
        # 핵심 SBU 4 + koreanllm.org W0 launch metric
        kpis = [
            # (product_slug, metric_name, source, target_value)
            ("kott", "monthly_active_users", "ga4", "10,000 (next quarter)"),
            ("toolpick", "monthly_active_users", "ga4", "100,000 (long term)"),
            ("ur-wrong", "verified_human_arguments", "supabase", ">= 1 weekly"),
            ("koreanllm", "monthly_active_users", "ga4", "1M (24mo target)"),
            ("koreanllm", "annual_recurring_revenue", "manual", "$350K~$650K (24mo base)"),
            # PostHog DAU (HogQL live, 2026-05-29 endpoint 복구) — daily 활성 측정
            ("toolpick", "daily_active_users", "posthog", "1,000+ DAU (long term)"),
            ("kott", "daily_active_users", "posthog", "500+ DAU (next quarter)"),
        ]
        for product_slug, metric_name, source, target in kpis:
            kpi_id = f"neo://biz/kpi/{product_slug}/{metric_name}"
            self.add_node({
                "id": kpi_id,
                "rdf_type": "biz:KPI",
                "label": f"{product_slug} {metric_name}",
                "product": f"neo://biz/product/{product_slug}",
                "metric_name": metric_name,
                "source": source,
                "target_value": target,
                "markings": ["internal"],
                "provenance": PROV_HARDCODED,
                "provenance_note": "Strategy Lead seed target. kpi_fetch.py 가 source 별로 current_value 라이브 갱신 — 갱신 시 provenance=observed_from_live_source.",
            })
            self.add_edge("biz:measures",
                          kpi_id, f"neo://biz/product/{product_slug}")

        # GSC KPI — Search Console 4 sites × 3 metrics (CREDENTIAL_BIBLE OAuth refresh token 박제)
        gsc_sites = [
            # (product_slug, site_url, 28-day baseline target)
            ("kott", "https://kott.kr", "10K impressions / 100 clicks / position < 20 (next quarter)"),
            ("toolpick", "https://toolpick.dev", "100K impressions / 1K clicks / position < 15 (long term)"),
            ("ur-wrong", "https://ur-wrong.com", "5K impressions / 50 clicks / position < 30 (next quarter)"),
            ("heoyesol-brand", "https://heoyesol.kr", "1K impressions / 10 clicks / position < 10 (brand)"),
        ]
        for product_slug, site_url, target in gsc_sites:
            for metric_suffix in ("gsc_impressions_28d", "gsc_clicks_28d", "gsc_avg_position_28d"):
                kpi_id = f"neo://biz/kpi/{product_slug}/{metric_suffix}"
                self.add_node({
                    "id": kpi_id,
                    "rdf_type": "biz:KPI",
                    "label": f"{product_slug} {metric_suffix}",
                    "product": f"neo://biz/product/{product_slug}",
                    "metric_name": metric_suffix,
                    "source": "gsc",
                    "site_url": site_url,
                    "target_value": target,
                    "markings": ["internal"],
                    "provenance": PROV_HARDCODED,
                    "provenance_note": "kpi_fetch.py 가 GSC searchanalytics API 로 current_value 라이브 갱신 (refresh_token + GOOGLE_OAUTH_CLIENT_SECRET_FILE).",
                })
                self.add_edge("biz:measures",
                              kpi_id, f"neo://biz/product/{product_slug}")

    # ============================================================
    # P0 추가 — Capability, ExternalFederation, TemporalEvent, MonthlyCost
    # ============================================================

    def extract_capabilities(self, founder_id: str) -> None:
        """Founder + AI agent + persona 의 skill matrix."""
        # Founder capabilities (per memory user_career_profile + neo_genesis_role)
        founder_caps = [
            ("pm-po-domain", "product_management", "S", "10+ years CTS-AI PM/PO experience"),
            ("ai-orchestration", "agentic_systems", "A", "Claude/Codex/Sora multi-agent design"),
            ("korean-llm-research", "research", "S", "KoreanLLM Phase 1-9 (287K words)"),
            ("strategy-decision", "strategy", "S", "Neo Genesis Strategy Lead role"),
            ("growth-marketing", "growth", "B", "11 SBU growth loop ops"),
            ("quant-bot-ops", "quant", "C", "v11 PoC closed 5/12, learnings retained"),
            ("technical-writing", "writing", "A", "NeurIPS manuscript + 287K Korean research"),
        ]
        for slug, domain, tier, evidence in founder_caps:
            cap_id = f"neo://biz/capability/founder/{slug}"
            self.add_node({
                "id": cap_id,
                "rdf_type": "biz:Capability",
                "label": f"founder: {slug}",
                "domain": domain,
                "tier": tier,
                "owner": founder_id,
                "evidence_note": evidence,
                "markings": ["internal"],
                "provenance": PROV_HARDCODED,
                "provenance_note": "Strategy Lead seed estimate. owner verification 대기. 측정 가능 단계 시 outcome-based reassessment.",
            })
            self.add_edge("biz:has_capability", founder_id, cap_id)

        # AI agent capabilities (Tier S persona 8개)
        ai_caps = [
            ("claude-strategy-lead", "strategy", "S", "Strategy Lead (Opus 4.7) — G1 자율 권한"),
            ("claude-senior-backend-eng", "backend", "S", "PEV + Side-Effect Matrix"),
            ("claude-senior-da-pm", "data_pm", "S", "JTBD + AARRR + Pre-mortem"),
            ("claude-quant-strategy-lead", "quant", "S", "DSR/PBO + CPCV — quant-bot closed"),
            ("claude-sora-sre-ops", "sre", "S", "OODA + Google SRE Postmortem"),
            ("claude-prompt-injection-auditor", "security", "S", "STRIDE + DREAD + AgentDojo"),
            ("claude-korean-seo-geo", "seo_geo", "S", "Pirate Funnel + GEO citation"),
            ("claude-korean-copywriter", "copywriting", "S", "AIDA + 4U + Tone Matrix"),
            ("claude-multi-agent-orchestrator", "orchestration", "S", "Magentic Dual-Ledger + LATS"),
            ("codex", "execution", "A", "GPT-5-codex implementer"),
            ("sora", "interactive_assistant", "A", "Sora v5.19 Telegram bot"),
            ("antigravity", "thinking_reasoning", "A", "claude-opus-4.6-thinking"),
            ("ollama-local", "local_inference", "B", "Qwen3-14B / qwen2.5-coder fallback"),
        ]
        for slug, domain, tier, evidence in ai_caps:
            cap_id = f"neo://biz/capability/ai/{slug}"
            self.add_node({
                "id": cap_id,
                "rdf_type": "biz:Capability",
                "label": f"AI: {slug}",
                "domain": domain,
                "tier": tier,
                "owner": f"neo://agent/{slug.split('-')[-1] if slug.startswith('claude-') else slug}",
                "evidence_note": evidence,
                "markings": ["internal"],
                "provenance": PROV_DOC_EXTRACTED,
                "provenance_source": ".agent/personas/tier-*/*.md frontmatter",
            })

    def extract_external_federations(self) -> None:
        """운영 의존 external services (cost / status / dependency)."""
        federations = [
            # (slug, provider, kind, tier, monthly_usd, status, criticality)
            ("cloudflare-zones", "Cloudflare", "dns_cdn_security", "Free + Pro", "0-30",
             "active", "P0",
             "13 GSC zone + koreanllm.org 2026-05-14 등록 + Workers/Pages 잠재 OpEx M3 $58 → M24 $400-450"),
            ("vercel-deploys", "Vercel", "frontend_hosting", "Hobby + Pro", "0-20",
             "active", "P0",
             "11 SBU production deploys"),
            ("auradb-professional", "Neo4j", "graph_database", "AuraDB Professional (Trial 12d)", "65",
             "active", "P0",
             "instance 394b2602 (네오제네시스 project, Azure 서울 koreacentral, 2GB RAM / 1 CPU / 4GB storage). **trial 만료 2026-05-26 (D-12 from 2026-05-14)** — 만료 후 paid $65/월 또는 Free downgrade 결정 필요"),
            ("supabase", "Supabase", "postgres_realtime", "Free", "0",
             "active", "P0",
             "quant_* tables + assistant_memory + rag_audit_log. 비활성 시 sora-live degrade"),
            ("ga4-properties", "Google Analytics 4", "analytics", "Free", "0",
             "active", "P1",
             "11 SBU traffic + KPI source"),
            ("posthog", "PostHog", "product_analytics", "Free", "0",
             "active", "P1",
             "11 SBU event tracking"),
            ("github-yesol-pilot", "GitHub", "repo_hosting", "Pro", "4",
             "active", "P0",
             "Yesol-Pilot org, 11 SBU repos + neo-genesis monorepo"),
            ("tailscale-fleet", "Tailscale", "vpn_mesh", "Free", "0",
             "active", "P0",
             "8 device fleet (ysh-server, desktop-home, etribe-yesol, etc)"),
            ("anthropic-claude-max", "Anthropic", "llm_subscription", "Claude Max", "100",
             "active", "P0",
             "Strategy Lead / agent runtime / dispatcher / Sora"),
            ("openai-gpt-pro", "OpenAI", "llm_subscription", "GPT Pro", "200",
             "active", "P1",
             "GPT-5-codex (Codex agent) + 보조"),
            ("google-ai-ultra", "Google", "llm_subscription", "Ultra (Gemini)", "30",
             "active", "P1",
             "Gemini 3.1 Pro Preview + Calendar + Drive"),
            ("namecheap-domains", "Namecheap (또는 Cloudflare Registrar)", "domain_registration", "per-domain", "1-15",
             "active", "P0",
             "kott.kr, koreanllm.org, etc. — 사업자 명의"),
        ]
        for slug, provider, kind, tier_name, monthly_usd, status, criticality, note in federations:
            fed_id = f"neo://biz/federation/{slug}"
            self.add_node({
                "id": fed_id,
                "rdf_type": "biz:ExternalFederation",
                "label": f"{provider}: {slug}",
                "provider": provider,
                "kind": kind,
                "subscription_tier": tier_name,
                "monthly_cost_usd_range": monthly_usd,
                "status": status,
                "criticality": criticality,
                "note": note,
                "markings": ["internal"],
            })

    def extract_temporal_events(self, founder_id: str) -> None:
        """시점 의존 이벤트 (deadline / launch / trigger)."""
        events = [
            # (slug, kind, target_date, status, trigger_condition, impact)
            ("koreanllm-w0-launch", "product_launch", "2026-06-10", "scheduled",
             "Cloudflare bind + DNS propagation + W0 dashboard ready",
             "D-27 from 2026-05-14. AO-1 SBU live trigger."),
            ("arxiv-blind-review-unhold", "publication_unhold", None, "blocked",
             "double-blind venue accept/reject decision 발표",
             "EthicaAI + WhyLab manuscript arXiv 업로드 unblock. 현 passive 대기."),
            ("neurips-2026-camera-ready", "publication_deadline", "2026-09-15", "tentative",
             "EthicaAI Melting Pot accepted at NeurIPS",
             "venue accept 시 자동 활성, reject 시 owner G2 재검토."),
            ("auradb-trial-expiry", "infra_critical", "2026-05-26", "scheduled",
             "AuraDB Professional Trial 만료 (Chrome 검증 결과 Free 아님, Professional Trial 12일 잔여)",
             "D-12 from 2026-05-14. 만료 후 결정: (A) $65/월 paid Professional 유지 (B) Free 다운그레이드 (C) Docker self-host 전환. burn rate $448 + $65 = $513 권고 또는 owner G2."),
            ("quant-bot-closure", "product_retire", "2026-05-12", "completed",
             "v11 PoC 38-day 결과 (0/108 sweep cells PASS)",
             "PM2 stop, capital 권고 ❌."),
            ("revenue-path-30day-review", "strategy_review", "2026-06-08", "scheduled",
             "Revenue Path Research v1 30일 ROI 측정",
             "B1/D2/C2/B3 path 진척 확인 + 자본 추가 투입 결정 (G2)."),
            ("toolpick-gsc-retry", "growth_op", None, "recurring",
             "ToolPick GSC P0 URL 8건 indexing retry (daily cron)",
             "Codex automation `toolpick-gsc-indexing-retry` 09:10 KST."),
            ("cts-employer-bridge", "career_dependency", None, "active",
             "owner 본업 CTS-AI continued employment",
             "Neo Genesis 매출 0 단계 의존. Revenue Path Research v1 B2 path."),
        ]
        for slug, kind, target_date, status, trigger, impact in events:
            ev_id = f"neo://biz/event/{slug}"
            node = {
                "id": ev_id,
                "rdf_type": "biz:TemporalEvent",
                "label": slug,
                "kind": kind,
                "status": status,
                "trigger_condition": trigger,
                "impact_note": impact,
                "markings": ["internal"],
            }
            if target_date:
                node["target_date"] = target_date
            self.add_node(node)

    def extract_monthly_costs(self) -> None:
        """OpEx 분석 — federation 별 비용 + runway visibility."""
        # Aggregate by category (federation node 의 monthly_cost 합)
        cost_buckets = [
            ("llm_subscriptions", "LLM 구독 (Anthropic + OpenAI + Google)", 330,
             "Claude Max $100 + GPT Pro $200 + Google AI Ultra $30. API 과금 0 (구독 limit 내)."),
            ("infra_hosting", "인프라 (GitHub Pro + domains)", 10,
             "GitHub Pro $4 + 도메인 1-15 (kott.kr + koreanllm.org + 기타 평균). Tailscale/Vercel/Supabase/PostHog/GA4/AuraDB Free."),
            ("compute_devices", "장치 운영 비용 (전기/네트워크)", 50,
             "8 device fleet 추정. ysh-server (전기 + 네트워크). 정확한 측정 미실시."),
            ("cloudflare-scaling", "Cloudflare Workers/Pages/D1/KV (M3-M24 scaling)", 58,
             "현재 Free tier 충분. koreanllm.org W0 launch 후 M3 $58 → M24 $400~450 trajectory."),
            ("paper-compute", "논문 GPU 컴퓨트", 0,
             "EthicaAI Melting Pot 24+26 seed 마이그레이션 완료. 신규 실험 미진행."),
        ]
        total_baseline = sum(amount for _, _, amount, _ in cost_buckets)
        for slug, label, monthly_usd, note in cost_buckets:
            cost_id = f"neo://biz/cost/{slug}"
            self.add_node({
                "id": cost_id,
                "rdf_type": "biz:MonthlyCost",
                "label": label,
                "category": slug,
                "monthly_usd_estimate": monthly_usd,
                "note": note,
                "as_of": self.now,
                "markings": ["internal"],
                "provenance": PROV_HARDCODED,
                "provenance_note": "Strategy Lead 추정. 실 invoice 데이터 0. owner 가 신용카드 / 구독 영수증 박제 시 PROV_OBSERVED 전환.",
            })

        # Summary node — 전체 burn rate
        self.add_node({
            "id": "neo://biz/cost/_total_baseline",
            "rdf_type": "biz:MonthlyCost",
            "label": "Total baseline monthly burn (current state)",
            "category": "_aggregate",
            "monthly_usd_estimate": total_baseline,
            "note": f"Current 5 buckets 합산. Revenue 0 단계 → 전액 capital draw.",
            "as_of": self.now,
            "markings": ["internal"],
            "provenance": PROV_HARDCODED,
            "provenance_note": "5 estimate buckets 합산. 실 측정 0. owner 결정 시 invoice 기반 fact-check 필수.",
        })

    # ============================================================
    # P0 추가 batch 2 — Workflow, ContentCorpus, BrandAsset, Risk, AgentContribution
    # ============================================================

    def extract_workflows(self) -> None:
        """운영 절차 — executable_command + precondition 로 actuation 가능."""
        # (slug, kind, status, frequency, source_artifact, note, executable_command, precondition)
        # executable_command: workflow_runner.py 가 호출할 실 shell command (None = manual only)
        # precondition: digest 가 trigger 판단할 Python 표현식 (또는 None)
        workflows = [
            ("hive-mind-auto-publish", "content_publishing", "scheduled", "30min cron",
             "neo://artifact/hive-mind-pipeline",
             "11 SBU blog 자동 발행 (HIVE MIND). 현재 발행 0 — debug 필요",
             None,  # 외부 cron, ontology 가 직접 실행 안 함
             "blog_published_this_month == 0"),
            ("persona-dispatcher-routing", "agent_routing", "live", "per user_prompt",
             "neo://artifact/persona-dispatcher",
             "32 페르소나 L1/L2/L3/L4 4-tier hybrid routing",
             None,  # owner prompt 시 자동 발동, 별도 trigger 불필요
             None),
            ("g2-approval-flow", "governance", "live", "on owner irreversible command",
             "neo://artifact/g2-detection-hook",
             "production deploy / 자본 / 영구 비가역 → owner 명시 승인 필수",
             None,  # hook 자체가 trigger
             None),
            ("sbu-growth-loop", "growth", "live", "per SBU continuous",
             "neo://artifact/growth-loop-template",
             "Awareness → Conversion → Retention → Revenue. 11 SBU 적용",
             None,
             None),
            ("cross-publish-workflow", "content_distribution", "manual",
             "owner trigger", "neo://artifact/canonical-links",
             "Hashnode + Dev.to + LinkedIn re-publish with canonical link",
             None,  # owner manual
             None),
            ("strategy-lead-weekly-review", "strategy_review", "scheduled", "Monday 10:05 KST cron",
             "neo://artifact/weekly-review-template",
             "주간 진척 + 자본 입금 권고 + Stop/Go gate 판정",
             None,  # 별도 cron 박제 (Monday 10:05 KST)
             "today.weekday() == 0 and last_review_age_days >= 6"),
            ("ontology-daily-maintain", "ontology_ops", "live", "Daily 09:13 KST",
             "neo://artifact/daily-maintain-script",
             "Windows Task Scheduler. 10-step orchestrator",
             "python scripts/ontology/daily_maintain.py",
             None),  # Task Scheduler 가 trigger
            ("auto-record-actionrun", "audit", "live", "per dispatcher --query",
             "neo://artifact/auto-record-helper",
             "PROV-O Activity chain. dispatcher 호출마다 ActionRun 자동 박제",
             None,
             None),
            ("blind-review-hold-guard", "compliance", "active",
             "until paper review 결과", "neo://artifact/blind-review-hold-policy",
             "EthicaAI + WhyLab manuscript arXiv 업로드 차단. owner G2 재검토 후 unhold",
             None,
             None),
            # 신규 추가 — ontology-driven workflows (executable!)
            ("kpi-auto-fetch", "kpi_collection", "live", "Daily 09:13 (within daily_maintain)",
             "neo://artifact/kpi-fetch-script",
             "GA4 / GSC / PostHog 일일 자동 fetch → KPI.current_value 갱신",
             "python scripts/ontology/business/kpi_fetch.py",
             None),
            ("ontology-daily-digest", "decision_surfacing", "live", "Daily 09:13",
             "neo://artifact/daily-digest-script",
             "ontology state → owner attention digest 자동 생성",
             "python scripts/ontology/business/daily_digest.py --save-as-decision",
             None),
            ("auradb-heartbeat", "infra_keep_alive", "live", "Daily 09:13",
             "neo://artifact/migrate-script-verify",
             "AuraDB Free 3-day auto-pause 회피용 heartbeat",
             "python scripts/ontology/migrate_to_neo4j.py --verify",
             None),
            ("graphrag-rebuild", "rag_refresh", "live", "Daily 09:13",
             "neo://artifact/graphrag-script",
             "Louvain community detection 재계산",
             "python scripts/ontology/graphrag.py --rebuild",
             None),
        ]
        for slug, kind, status, frequency, source_artifact, note, executable_command, precondition in workflows:
            wf_id = f"neo://biz/workflow/{slug}"
            node = {
                "id": wf_id,
                "rdf_type": "biz:Workflow",
                "label": slug,
                "kind": kind,
                "status": status,
                "frequency": frequency,
                "source_artifact": source_artifact,
                "note": note,
                "markings": ["internal"],
            }
            if executable_command:
                node["executable_command"] = executable_command
            if precondition:
                node["precondition"] = precondition
            self.add_node(node)

    def extract_content_corpus(self) -> None:
        """Published / WIP content corpus — Neo Genesis IP 의 개별 단위."""
        # KoreanLLM Phase 1-9 research (40 docs 박제)
        for phase in range(1, 11):
            corp_id = f"neo://biz/corpus/koreanllm-phase{phase}"
            self.add_node({
                "id": corp_id,
                "rdf_type": "biz:ContentCorpus",
                "label": f"KoreanLLM Phase {phase}",
                "kind": "research_doc_set",
                "language": "ko_en_ja",
                "status": "wip" if phase >= 10 else "completed",
                "research_ip": "neo://biz/research_ip/koreanllm-ao1",
                "approx_word_count": 28700,  # 287K / 10 phase avg
                "markings": ["internal"],
            })

        # arXiv manuscripts
        manuscripts = [
            ("ethicaai-melting-pot", "EthicaAI Melting Pot manuscript", "neurips-2026-target", "blind_review"),
            ("whylab-causal-inference", "WhyLab causal inference manuscript", "blind-review-tbd", "blind_review"),
            ("revenue-path-research-v1", "Revenue Path Research v1 (1300+ words)", "internal-strategy", "completed"),
        ]
        for slug, label, venue_hint, status in manuscripts:
            self.add_node({
                "id": f"neo://biz/corpus/{slug}",
                "rdf_type": "biz:ContentCorpus",
                "label": label,
                "kind": "manuscript",
                "language": "en",
                "status": status,
                "venue_hint": venue_hint,
                "markings": ["internal"],
            })

        # SBU blog corpus (aggregate count placeholder)
        sbu_blogs = ["kott", "toolpick", "ur-wrong", "reviewlab", "sellkit",
                     "deploystack", "aiforge", "craftdesk", "finstack", "whylab"]
        for sbu in sbu_blogs:
            self.add_node({
                "id": f"neo://biz/corpus/{sbu}-blog",
                "rdf_type": "biz:ContentCorpus",
                "label": f"{sbu} blog corpus (aggregate)",
                "kind": "blog_series",
                "language": "ko_en",
                "status": "live",
                "product": f"neo://biz/product/{sbu}",
                "markings": ["public"],
            })

    def extract_brand_assets(self) -> None:
        """Brand identity / voice / 사업자 자산."""
        assets = [
            ("neo-genesis-corporate-identity", "corporate_identity", "사업자명 + 등록증 + 사업자번호",
             "internal", "네오 제네시스 / 630-17-***** / 일반과세자 / 2026-01-27"),
            ("heoyesol-personal-brand", "personal_brand", "owner 의 'Question-first builder' essence",
             "public", "heoyesol.kr — Personal Brand HQ + /resume tool"),
            ("brand-voice-luxury", "tone_of_voice", "결단력 있는 디렉터 voice — 옵션 나열·정량 자랑·마케팅 어휘·모호어 금지",
             "internal", "feedback_brand_voice memory 박제"),
            ("hero-tagline", "tagline", "'I build to find out' — Question-first builder",
             "public", "heoyesol.kr hero 영구 박제"),
            ("yesol-pilot-github", "code_identity", "Yesol-Pilot GitHub org (neogenesislab 절대 금지)",
             "internal", "11 SBU repos + neo-genesis monorepo + quant-bot"),
            ("pharl-resume-framework", "resume_framework", "Problem-Hypothesis-Action-Result-Learning",
             "internal", "9 master resume PDF 표준 frame"),
        ]
        for slug, kind, description, markings, note in assets:
            self.add_node({
                "id": f"neo://biz/brand/{slug}",
                "rdf_type": "biz:BrandAsset",
                "label": slug,
                "kind": kind,
                "description": description,
                "note": note,
                "markings": [markings],
            })

    def extract_risks(self) -> None:
        """Compliance / operational / strategic risk."""
        risks = [
            ("pipa-data-retention", "regulatory_compliance", "P1",
             "한국 개인정보보호법 (PIPA) — owner_facts / cron probe / Telegram chat 90-day retention",
             "neo://artifact/pipa-policy", "active"),
            ("blind-review-hold", "publication_compliance", "P0",
             "EthicaAI + WhyLab manuscript double-blind venue 심사 중 → arXiv 업로드 금지",
             "neo://artifact/blind-review-hold-policy", "active"),
            ("sa-business-tax", "tax_compliance", "P1",
             "개인사업자 일반과세자 — 매출 발생 시 부가세 신고 + 종합소득세 5월 신고",
             None, "monitoring"),
            ("financial-advisor-charter", "self-imposed-policy", "P0",
             "Strategy Lead = 재무책임자 헌장 — G1 자본 위험 0 / personal 0 / 영구 비가역 0 시만",
             "neo://artifact/financial-advisor-system-v1", "active"),
            ("auradb-free-3day-pause", "infra_risk", "P2",
             "AuraDB Free 3-day inactivity auto-pause — daily_maintain cron heartbeat 으로 회피",
             "neo://biz/event/auradb-free-auto-pause", "mitigated"),
            ("personal-context-leak", "data_governance", "P0",
             "personal/ 디렉토리 (법무·금융·개인회생) ontology / chat / agent context 절대 외",
             "neo://artifact/personal-context-routing-policy", "active"),
            ("cts-employer-double-loyalty", "career_risk", "P1",
             "owner = CTS-AI 직원 + Neo Genesis 대표 ← 시간 / IP / 의무 충돌 가능",
             None, "monitoring"),
            ("llm-subscription-dependency", "infra_risk", "P1",
             "월 $330 LLM 구독 (Anthropic / OpenAI / Google) — 1+ 종료 시 capability 감소",
             "neo://biz/cost/llm_subscriptions", "monitoring"),
            ("koreanllm-w0-readiness", "product_launch_risk", "P0",
             "D-27 (2026-06-10) W0 launch — Cloudflare bind + DNS + dashboard ready 필요",
             "neo://biz/event/koreanllm-w0-launch", "active"),
            ("ga4-sa-permission-gap", "observability_gap", "P1",
             "GA4 Data API 403 'User does not have sufficient permissions for this property' — 14 GA4 property 에 SA email Viewer 권한 미부여. kpi_fetch.py GA4 live current_value 갱신 차단. owner action: GA4 → Admin → Property Access → Add (SA email, Viewer).",
             "neo://artifact/credential-bible", "active"),
            ("posthog-api-permission-gap", "observability_gap", "P1",
             "PostHog REST API 403 Forbidden — POSTHOG_PERSONAL_API_KEY 가 project insights 권한 미보유 OR endpoint mismatch. kpi_fetch.py PostHog live current_value 갱신 차단. owner action: PostHog → Personal API Keys → Permissions → project_read or scope 확장.",
             "neo://artifact/credential-bible", "active"),
            ("langchain-cypher-chain-not-wired", "infra_risk", "P2",
             "ANTHROPIC_API_KEY .env.local 박제 확인 (2026-05-16). LangChain GraphCypherQAChain 통합 PoC 미구현 — 실 코드 wiring 시 즉시 라이브 LLM 호출 가능. v0.5 게이트 항목.",
             None, "monitoring"),
        ]
        for slug, kind, severity, description, source, status in risks:
            node = {
                "id": f"neo://biz/risk/{slug}",
                "rdf_type": "biz:Risk",
                "label": slug,
                "kind": kind,
                "severity": severity,
                "description": description,
                "status": status,
                "markings": ["internal"],
                "provenance": PROV_DOC_EXTRACTED,
                "provenance_source": "Strategy Lead Chrome verification + kpi_fetch.py 라이브 실행 결과 (2026-05-16)",
            }
            if source:
                node["source_artifact"] = source
            self.add_node(node)

    def extract_business_relationships(self, founder_id: str) -> None:
        """Connective tissue: 노드를 실제 그래프로 연결 (evidence-grounded, 날조 X).

        근거: Revenue Path Research v1 (`.agent/knowledge/20260512_REVENUE_PATH_RESEARCH_v1.md`)
        + Risk node description 의 명시적 제품 참조. 그래프가 "어느 제품이 어느
        매출을 내고 어느 리스크에 노출됐나"를 답하게 만든다 (이전엔 Product→Revenue 0건).
        """
        # 1. Product → RevenueStream (biz:generates_revenue_via)
        #    B1 = "11 SBU 가속" (Revenue Path Research v1 최우선 권고) → 11 commercial SBU
        SBU_TO_B1 = [
            "kott", "toolpick", "ur-wrong", "reviewlab", "sellkit", "deploystack",
            "aiforge", "craftdesk", "finstack", "whylab", "koreanllm",
        ]
        b1 = "neo://biz/revenue_stream/b1-sbu-acceleration"
        for slug in SBU_TO_B1:
            self.add_edge("biz:generates_revenue_via",
                          f"neo://biz/product/{slug}", b1)
        # C2 = 정보재/강의 (passive) → 콘텐츠 자산 강한 SBU (Revenue Path Research C2)
        c2 = "neo://biz/revenue_stream/c2-info-product"
        for slug in ["toolpick", "reviewlab", "kott"]:
            self.add_edge("biz:generates_revenue_via",
                          f"neo://biz/product/{slug}", c2)

        # 2. Product → Risk (biz:threatened_by) — Risk description 이 명시 참조하는 제품만
        PRODUCT_RISK = {
            "koreanllm": ["koreanllm-w0-readiness"],
            "ethicaai-paper": ["blind-review-hold"],
            "whylab-paper": ["blind-review-hold"],
        }
        for slug, risks in PRODUCT_RISK.items():
            for r in risks:
                self.add_edge("biz:threatened_by",
                              f"neo://biz/product/{slug}", f"neo://biz/risk/{r}")

        # 3. Capability → Product (biz:enables) — founder 핵심 역량이 어느 제품 구동
        #    근거: capability evidence_note + 제품 도메인 매핑 (보수적, 명시적인 것만)
        CAP_ENABLES = {
            "korean-llm-research": ["koreanllm"],     # KoreanLLM Phase 1-9
            "quant-bot-ops": [],                       # quant closed, 제품 링크 없음
        }
        for cap_slug, prods in CAP_ENABLES.items():
            for slug in prods:
                self.add_edge("biz:enables",
                              f"neo://biz/capability/founder/{cap_slug}",
                              f"neo://biz/product/{slug}")

        # ── P0 엣지 전사 (2026-05-29 ultracode critic) — 노드에 이미 박힌 사실을 엣지로.
        #    결정적 키 매칭만 (거짓 0). 추측/note-파싱 강제 연결 금지.
        ids = {n["id"] for n in self.nodes}

        # P0-7: Founder → MonthlyCost (biz:incurs) — founder 가 모든 운영비 발생 (결정적)
        for n in self.nodes:
            if n.get("rdf_type") == "biz:MonthlyCost":
                self.add_edge("biz:incurs", founder_id, n["id"])

        # P0-11 funds: Investment → RevenueStream (id slug 동일키, 예: d2-us-etf↔d2-us-etf)
        rs_slugs = {n["id"].split("/")[-1] for n in self.nodes if n.get("rdf_type") == "biz:RevenueStream"}
        for n in self.nodes:
            if n.get("rdf_type") == "biz:Investment":
                slug = n["id"].split("/")[-1]
                if slug in rs_slugs:
                    self.add_edge("biz:funds", n["id"], f"neo://biz/revenue_stream/{slug}")

        # P0-11 adopted: Founder → Strategy (founder 가 전략 채택)
        for n in self.nodes:
            if n.get("rdf_type") == "biz:Strategy":
                self.add_edge("biz:adopted", founder_id, n["id"])

        # P0-8 depends_on: live SBU Product → Vercel federation (전부 Vercel 배포, active-tasks 근거)
        vercel = "neo://biz/federation/vercel-deploys"
        if vercel in ids:
            for n in self.nodes:
                if n.get("rdf_type") == "biz:Product" and n.get("stage") == "live":
                    self.add_edge("biz:depends_on", n["id"], vercel)

        # P0-11 enables 확장: Capability → Product (evidence_note 에 제품 slug 명시분만)
        prod_slugs = [n["id"].split("/")[-1] for n in self.nodes if n.get("rdf_type") == "biz:Product"]
        for n in self.nodes:
            if n.get("rdf_type") == "biz:Capability":
                ev = (n.get("evidence_note") or "").lower()
                for slug in prod_slugs:
                    if len(slug) > 4 and slug in ev:
                        self.add_edge("biz:enables", n["id"], f"neo://biz/product/{slug}")

        # ── P0-9: Risk → source_artifact (biz:references)
        #    근거: Risk 노드의 source_artifact 필드 = 이미 박힌 사실.
        #    대상 노드가 현재 nodes set 에 존재할 때만 엣지 생성 (없으면 skip, 거짓 0).
        for n in self.nodes:
            if n.get("rdf_type") != "biz:Risk":
                continue
            sa = n.get("source_artifact")
            if sa and sa in ids:
                self.add_edge("biz:references", n["id"], sa)

        # ── P0-10: TemporalEvent → 영향 대상 (biz:affects)
        #    impact_note 에 제품 slug 가 명시적으로 언급된 경우만.
        #    추측 금지 — 명시 매핑만 아래에 선언, 대상 노드 존재 확인 후 생성.
        EVENT_AFFECTS: dict[str, list[str]] = {
            # "D-27 from 2026-05-14. AO-1 SBU live trigger." → koreanllm Product
            "neo://biz/event/koreanllm-w0-launch": ["neo://biz/product/koreanllm"],
            # "EthicaAI + WhyLab manuscript arXiv 업로드 unblock." → 양 논문 제품
            "neo://biz/event/arxiv-blind-review-unhold": [
                "neo://biz/product/ethicaai-paper",
                "neo://biz/product/whylab-paper",
            ],
            # "EthicaAI Melting Pot accepted at NeurIPS" → ethicaai-paper 제품
            "neo://biz/event/neurips-2026-camera-ready": ["neo://biz/product/ethicaai-paper"],
        }
        for ev_id, targets in EVENT_AFFECTS.items():
            if ev_id not in ids:
                continue
            for tgt in targets:
                if tgt in ids:
                    self.add_edge("biz:affects", ev_id, tgt)

    def extract_agent_contributions(self) -> None:
        """Agent × Product 기여 매트릭스 (delegation 의사결정 근거)."""
        # 본 세션 기준 contribution 측정 (rough estimate, owner cold judgment 후 갱신)
        contributions = [
            # (agent_slug, product_slug, role, intensity, evidence)
            ("claude-opus-4-7", "koreanllm", "strategy_lead", "high",
             "본 세션 ontology v0.1~v0.5 박제 + business v0.1 신설, Strategy Lead role"),
            ("claude-opus-4-7", "ethicaai-paper", "research_co_author", "medium",
             "Phase 1-9 deep research synthesis + manuscript drafting assist"),
            ("claude-opus-4-7", "whylab-paper", "research_co_author", "medium",
             "manuscript drafting + arXiv prep"),
            ("claude-opus-4-7", "kott", "strategy_advisor", "low",
             "5/10 growth performance monitoring + GSC indexing strategy"),
            ("codex", "kott", "implementer", "high",
             "K-OTT frontend + GSC monitoring + indexing automation"),
            ("codex", "toolpick", "implementer", "high",
             "ToolPick content quality + 100k MAU research + GSC operations"),
            ("codex", "ur-wrong", "implementer", "high",
             "UR WRONG growth hardening + rebuttal loop + share modal"),
            ("codex", "reviewlab", "implementer", "medium",
             "ReviewLab DB-backed metadata + buyer summary"),
            ("codex", "sellkit", "implementer", "medium",
             "SellKit ecommerce decision UX + comparison pages"),
            ("codex", "deploystack", "implementer", "medium",
             "DeployStack Railway pricing + Kubernetes resource optimization"),
            ("sora", "sora-app", "core_runtime", "high",
             "Sora bot Telegram polling + Korean conversation + output_filter"),
            ("antigravity", "2dlivegame", "asset_creator", "low",
             "Antigravity 게임 에셋 생성 (waifu-asset / glitch-ui / skin-texture)"),
            ("ollama-local", "sora-app", "local_inference_fallback", "low",
             "Qwen2.5-coder local LLM, Tailscale routing 차단 시 fallback"),
        ]
        for agent_slug, product_slug, role, intensity, evidence in contributions:
            contrib_id = f"neo://biz/contribution/{agent_slug}-{product_slug}"
            self.add_node({
                "id": contrib_id,
                "rdf_type": "biz:AgentContribution",
                "label": f"{agent_slug} → {product_slug}",
                "agent": f"neo://agent/{agent_slug}",
                "product": f"neo://biz/product/{product_slug}",
                "role": role,
                "intensity": intensity,
                "evidence_note": evidence,
                "markings": ["internal"],
                "provenance": PROV_HARDCODED,
                "provenance_note": "Strategy Lead 추정. git commit log + audit log 분석 0. owner 확인 + 자동 측정 필요.",
            })

    # ============================================================
    # 9. Decision (G1 박제 from handoff.md)
    # ============================================================
    def extract_decisions(self, founder_id: str) -> None:
        # 모든 .agent/**/*.md 파일 + 본 ontology 디렉토리 + handoff.md 통합 스캔
        # G1 박제는 여러 문서에 분산 (DESIGN / ontoclean / AURA_INSTANCE / DESIGN_business / active-tasks)
        sources: list[Path] = []
        # .agent/ontology/ 의 모든 .md
        ontology_dir = AGENT_DIR / "ontology"
        if ontology_dir.exists():
            sources.extend(ontology_dir.rglob("*.md"))
        # shared-brain handoff + active-tasks
        for fn in ("handoff.md", "active-tasks.md"):
            p = AGENT_DIR / "shared-brain" / fn
            if p.exists():
                sources.append(p)
        # neo4j docs
        neo4j_dir = AGENT_DIR / "ontology" / "neo4j"
        if neo4j_dir.exists():
            sources.extend(neo4j_dir.glob("*.md"))

        content = ""
        seen_files = set()
        for p in sources:
            real = p.resolve()
            if real in seen_files:
                continue
            seen_files.add(real)
            try:
                content += f"\n\n# source: {p.relative_to(REPO_ROOT)}\n" + p.read_text(encoding="utf-8")
            except Exception:
                continue
        if not content:
            return

        # Match `| G1-NN slug | text |` (markdown table) + `**G1-NN** text` (bold inline)
        decision_pat = re.compile(
            r"(?:"
            r"\|\s*(G[12]-\d+)(?:\s+([^|\n]+?))?\s*\|\s*([^|\n]{10,250})"  # table row
            r"|"
            r"\*\*(G[12]-\d+)\*\*\s+([^\n]{10,250})"  # bold inline
            r")"
        )
        seen = set()
        for m in decision_pat.finditer(content):
            # Table row: groups 1, 2, 3 = G_ID, slug_text (optional), rationale_text
            # Bold inline: groups 4, 5 = G_ID, rest
            if m.group(1):  # table row
                g_id = m.group(1)
                slug_text = (m.group(2) or "").strip()
                rationale = m.group(3).strip().rstrip("|").strip()
                title = f"{slug_text}: {rationale}" if slug_text else rationale
            else:  # bold inline
                g_id = m.group(4)
                title = m.group(5).strip()
            if g_id in seen or len(title) < 10:
                continue
            seen.add(g_id)
            decision_slug = f"{g_id.lower()}-{short_hash(title, 6)}"
            decision_id = f"neo://biz/decision/{decision_slug}"
            self.add_node({
                "id": decision_id,
                "rdf_type": "biz:Decision",
                "label": f"{g_id}: {title[:60]}",
                "g_level": g_id.split("-")[0],
                "g_id": g_id,
                "decided_by": founder_id if g_id.startswith("G2") else "neo://agent/claude-opus-4-7",
                "decided_at": "2026-05-14",  # 박제 일자 (대부분 본 세션)
                "reversible": True,
                "source_artifact": "neo://artifact/handoff-md",
                "markings": ["internal"],
            })
            self.add_edge("biz:decided",
                          founder_id if g_id.startswith("G2") else "neo://agent/claude-opus-4-7",
                          decision_id)

    # ============================================================
    # Finalize
    # ============================================================
    def report(self) -> dict:
        by_type: dict[str, int] = {}
        for n in self.nodes:
            by_type[n["rdf_type"]] = by_type.get(n["rdf_type"], 0) + 1
        edge_by_type: dict[str, int] = {}
        for e in self.edges:
            edge_by_type[e["type"]] = edge_by_type.get(e["type"], 0) + 1
        return {
            "extracted_at": self.now,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": by_type,
            "edges_by_type": edge_by_type,
        }


# 축1 provenance 무결성 (2026-05-29): provenance=none 노드에 정직한 출처 backfill.
# 코드에서 출처가 100% 증명된 클래스만 (거짓 박제 방지). 나머지 클래스는
# 메서드 출처 검증 후 2차 박제 — 모르는 출처를 추측해 채우지 않는다.
_CLASS_PROVENANCE_BACKFILL = {
    # extract_strategy_and_revenue: source_artifact=REVENUE_PATH_RESEARCH_v1 (코드 line 210/269)
    "biz:RevenueStream": (PROV_DOC_EXTRACTED, "neo://artifact/20260512_REVENUE_PATH_RESEARCH_v1"),
    "biz:Strategy": (PROV_DOC_EXTRACTED, "neo://artifact/20260512_REVENUE_PATH_RESEARCH_v1"),
    # extract_decisions: shared-brain/{handoff,active-tasks}.md read_text (코드 line 959/976)
    "biz:Decision": (PROV_DOC_EXTRACTED, "shared-brain/{handoff,active-tasks}.md (extract_decisions read_text)"),
    # extract_products: SBU 인벤토리 직접 입력 (FOLDER_BIBLE 11 SBU 목록 근거)
    "biz:Product": (PROV_HARDCODED, "SBU inventory (근거: D:/00.test/FOLDER_BIBLE.md SBU 목록)"),
    # 축1 2차 (2026-05-29): 전부 Strategy Lead 직접 입력 (read_text 증거 0 = hardcoded).
    # note 에 실제 근거 명시 → "출처 불명(none)" → "직접 입력 + 근거" 추적 가능화.
    "biz:Domain": (PROV_HARDCODED, "11 SBU 라이브 도메인 인벤토리 (근거: Cloudflare 등록 도메인 + FOLDER_BIBLE)"),
    "biz:ExternalFederation": (PROV_HARDCODED, "외부 federation 계정 (근거: CREDENTIAL_BIBLE — GitHub/Vercel/Cloudflare/Supabase)"),
    "biz:TemporalEvent": (PROV_HARDCODED, "사업 일정 이벤트 (근거: active-tasks/handoff 박제 일정)"),
    "biz:ResearchIP": (PROV_HARDCODED, "연구 IP (근거: PAPER/ EthicaAI + WhyLab manuscript)"),
    "biz:ContentCorpus": (PROV_HARDCODED, "SBU 콘텐츠 코퍼스 (근거: 11 SBU 라이브 사이트 콘텐츠)"),
    "biz:Workflow": (PROV_HARDCODED, "운영 워크플로우 (근거: SSOT 박제 운영 절차)"),
    "biz:BrandAsset": (PROV_HARDCODED, "브랜드 자산 (근거: heoyesol 브랜드 전략 memory)"),
}


# edge provenance: 관계 생성 규칙 출처 (노드와 대칭 무결성, 2026-05-29)
_BIZ_EDGE_PROVENANCE = {
    "biz:generates_revenue_via": (PROV_DOC_EXTRACTED, "Revenue Path Research v1 (11 SBU 가속 + 정보재)"),
    "biz:threatened_by": (PROV_DOC_EXTRACTED, "Risk node description 명시 참조"),
    "biz:enables": (PROV_DOC_EXTRACTED, "capability evidence_note 매핑"),
}
_BIZ_EDGE_DEFAULT = ("inferred_by_extractor", "extract_business structural inference")


def backfill_edge_provenance(edges: list[dict]) -> int:
    """provenance 없는 biz edge 에 관계 생성 규칙 출처 박제."""
    n = 0
    for e in edges:
        if not e.get("provenance"):
            prov, src = _BIZ_EDGE_PROVENANCE.get(e.get("type"), _BIZ_EDGE_DEFAULT)
            e["provenance"] = prov
            e["provenance_source"] = src
            n += 1
    return n


def backfill_provenance(nodes: list[dict]) -> int:
    """출처가 코드에서 증명된 클래스의 provenance=none 노드만 정직하게 backfill.
    Returns count backfilled. 매핑에 없는 클래스는 none 유지 (출처 추측 금지)."""
    n = 0
    for node in nodes:
        if node.get("provenance") in (None, "none"):
            m = _CLASS_PROVENANCE_BACKFILL.get(node.get("rdf_type"))
            if m:
                node["provenance"] = m[0]
                node.setdefault("provenance_source", m[1])
                n += 1
    return n


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# Fields that kpi_fetch.py writes as live observations. extract_business 는 매 실행마다
# 노드를 새로 생성하므로, 이전 nodes.jsonl 의 관측값을 보존하지 않으면 daily cron 의
# extract → kpi_fetch 순서에서 fetch 가 실패할 때 (예: GSC 토큰 만료) live 값이 영구
# 소실된다 (2026-05-16 grill-toast 발견). carry-forward 로 destructive overwrite 방지.
_OBSERVED_KPI_FIELDS = (
    "current_value",
    "current_value_observed_at",
    "current_value_source",
    "gsc_breakdown",
)


def preserve_observed_kpi_values(new_nodes: list[dict], existing_path: Path) -> int:
    """Carry forward kpi_fetch-written observation fields from prior nodes.jsonl.

    Only KPI nodes whose prior provenance == 'observed_from_live_source' are
    preserved (즉 실제 라이브 fetch 로 채워진 값만). Hardcoded seed 는 보존 안 함.
    Returns number of KPI nodes that had observed values carried forward.
    """
    if not existing_path.exists():
        return 0
    prior: dict[str, dict] = {}
    try:
        for line in existing_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            n = json.loads(line)
            if n.get("rdf_type") == "biz:KPI" and n.get("provenance") == "observed_from_live_source":
                prior[n["id"]] = n
    except Exception as e:
        print(f"[WARN] KPI carry-forward skipped (read failed): {e}", file=sys.stderr)
        return 0

    carried = 0
    for node in new_nodes:
        if node.get("rdf_type") != "biz:KPI":
            continue
        old = prior.get(node["id"])
        if not old:
            continue
        for field in _OBSERVED_KPI_FIELDS:
            if field in old:
                node[field] = old[field]
        node["provenance"] = "observed_from_live_source"
        carried += 1
    return carried


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ex = BizExtractor()
    founder_id = ex.extract_founder()
    ex.extract_products(founder_id)
    ex.extract_domains()
    ex.extract_strategy_and_revenue(founder_id)
    ex.extract_investments(founder_id)
    ex.extract_research_ip(founder_id)
    ex.extract_leads(founder_id)
    ex.extract_kpis()
    ex.extract_capabilities(founder_id)
    ex.extract_external_federations()
    ex.extract_temporal_events(founder_id)
    ex.extract_monthly_costs()
    ex.extract_workflows()
    ex.extract_content_corpus()
    ex.extract_brand_assets()
    ex.extract_risks()
    ex.extract_agent_contributions()
    ex.extract_decisions(founder_id)
    ex.extract_business_relationships(founder_id)  # connective tissue (evidence-grounded)

    report = ex.report()
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("[dry-run] not writing files")
        return 0

    # Root-cause fix (2026-05-16 grill-toast): carry forward live KPI observations
    # so daily cron extract → kpi_fetch ordering never wipes them when fetch fails.
    carried = preserve_observed_kpi_values(ex.nodes, NODES_PATH)
    if carried:
        print(f"[OK] carried forward {carried} observed KPI value(s) from prior nodes.jsonl")

    # 축1 provenance 무결성: 출처 증명된 클래스 backfill
    backfilled = backfill_provenance(ex.nodes)
    if backfilled:
        print(f"[OK] provenance backfilled for {backfilled} node(s) (출처 증명된 클래스)")
    edge_bf = backfill_edge_provenance(ex.edges)
    if edge_bf:
        print(f"[OK] edge provenance backfilled for {edge_bf} edge(s)")

    write_jsonl(NODES_PATH, ex.nodes)
    write_jsonl(EDGES_PATH, ex.edges)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] {len(ex.nodes)} nodes -> {NODES_PATH}")
    print(f"[OK] {len(ex.edges)} edges -> {EDGES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
