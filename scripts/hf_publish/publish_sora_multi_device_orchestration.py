"""
HuggingFace Datasets publish — Sora Multi-Device Orchestration Architecture 2026

Source : .agent/knowledge/SORA_UNIFIED_BIBLE.md
       + .agent/knowledge/SORA_MASTER_BLUEPRINT_V2.md
       + .agent/knowledge/20260428_SORA_ENTERPRISE_GRADE_MASTER_v1.md
       + .agent/knowledge/20260428_SORA_ENTERPRISE_DECISIONS_v1.md
       + .agent/policies/blast_radius.yaml
       + .agent/policies/capability_tokens.yaml
       + .agent/policies/permissions.yaml
       + .agent/runbooks/*.md (14 incident runbooks)

Target : huggingface.co/datasets/neogenesislab/sora-multi-device-orchestration-2026

Layout:
    README.md                    bilingual ko + en dataset card
    data/sections.jsonl          one record per parsed section (architecture/policy/decision/runbook)
    data/source_index.json       map of source files & doc_ids
    metadata.json                dataset-level meta + Schema.org

Why this dataset is unique:
- Personal/single-operator multi-device AI agent orchestration architecture is genuinely
  rare in the public corpus. Most public agent designs assume a single host.
- Real-world device tier model: personal-root + company-work-pc + server +
  team-mac + mobile-operator. Each tier has a distinct authority/blast-radius constraint.
- 6-tier blast-radius classification (0=read .. 5=irreversible) with explicit
  disclosure / 2FA / rollback ledger requirements per tier.
- Per-subagent capability-token model (per-task, not session) with TTL,
  blast_radius_ceiling, and resource scope.
- 14 production incident runbooks tied to a 5-step Article 0 (owner sovereignty)
  / Article 4 (dead-man switch) constitution.
- 11 D-gate enterprise decisions framework for honest scoping under
  single-operator constraints.

Anonymization:
- The architecture is published on the company website + Wikidata Q139569680 already.
- Strip: emails, phones, RRN, API tokens, absolute Windows paths, internal hostnames,
  Tailscale/private IPs.
- Preserve: device-tier names (personal-root, company-work-pc etc) since these are
  generic architecture concepts, not PII.

Run:
    set PYTHONIOENCODING=utf-8
    python scripts/hf_publish/publish_sora_multi_device_orchestration.py
"""
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
REPO_ID = "neogenesislab/sora-multi-device-orchestration-2026"

KNOWLEDGE_DIR = ROOT / ".agent" / "knowledge"
POLICIES_DIR = ROOT / ".agent" / "policies"
RUNBOOKS_DIR = ROOT / ".agent" / "runbooks"

# Source files with explicit doc_ids
ARCHITECTURE_DOCS = [
    ("unified-bible", "architecture", "v1.0", KNOWLEDGE_DIR / "SORA_UNIFIED_BIBLE.md"),
    ("blueprint-v2", "architecture", "v2.0", KNOWLEDGE_DIR / "SORA_MASTER_BLUEPRINT_V2.md"),
    ("enterprise-master", "architecture", "v1.1",
     KNOWLEDGE_DIR / "20260428_SORA_ENTERPRISE_GRADE_MASTER_v1.md"),
    ("decisions-v1", "decision", "v1.0",
     KNOWLEDGE_DIR / "20260428_SORA_ENTERPRISE_DECISIONS_v1.md"),
]

POLICY_DOCS = [
    ("blast-radius", "policy", "v1", POLICIES_DIR / "blast_radius.yaml"),
    ("capability-tokens", "policy", "v1", POLICIES_DIR / "capability_tokens.yaml"),
    ("permissions", "policy", "v1", POLICIES_DIR / "permissions.yaml"),
]


# ---------- Env ----------

def load_env(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


# ---------- Anonymization ----------

PII_PATTERNS = [
    (re.compile(r"\bdpthf1537@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\betribe\.cts@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\b010-?\d{4}-?\d{4}\b"), "<redacted-phone>"),
    # Stricter email: local-part must be >=2 chars (prevents `n@app.foo` code matches),
    # and TLD must be 2-6 alpha chars (prevents long code identifiers like `websocket`).
    (re.compile(
        r"\b[A-Za-z0-9][A-Za-z0-9._%+-]{1,}@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,6}\b"
    ), "<redacted-email>"),
    (re.compile(r"\b\d{6}-?[1-4]\d{6}\b"), "<redacted-rrn>"),
]

CRED_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<redacted-api-key>"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bgho_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"), "<redacted-hf-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"),
     "<redacted-jwt>"),
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), "<redacted-bot-token>"),
]

# Hostname -> generic device-tier label
DEVICE_MAP = {
    "desktop-yesol": "<work-pc>",
    "DESKTOP-YESOL": "<work-pc>",
    "desktop-sol01": "<gpu-worker>",
    "DESKTOP-SOL01": "<gpu-worker>",
    "ysh-server": "<server>",
    "YSH-Server": "<server>",
    "YSH-SERVER": "<server>",
    "mx-macbuild-mac-studio": "<mac-build>",
    "MX Mac Studio": "<mac-build>",
    "Mac Studio": "<mac-build>",
    "CTS_Sol": "<work-user>",
    "etribe-yesol": "<work-pc>",
}

PATH_PATTERNS = [
    (re.compile(r"D:/00\.test/neo-genesis", re.IGNORECASE), "<repo>"),
    (re.compile(r"D:\\00\.test\\neo-genesis", re.IGNORECASE), "<repo>"),
    (re.compile(r"D:/00\.test", re.IGNORECASE), "<workspace>"),
    (re.compile(r"D:\\00\.test", re.IGNORECASE), "<workspace>"),
    (re.compile(r"C:/Users/[A-Za-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"C:\\Users\\[A-Za-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"/home/[a-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"/Users/[a-z0-9_]+", re.IGNORECASE), "<home>"),
]

IP_PATTERNS = [
    (re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<tailscale-ip>"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
]


def anonymize(text):
    if text is None:
        return text
    s = str(text)
    for pat, repl in PATH_PATTERNS:
        s = pat.sub(repl, s)
    for hostname, generic in DEVICE_MAP.items():
        s = s.replace(hostname, generic)
    for pat, repl in PII_PATTERNS:
        s = pat.sub(repl, s)
    for pat, repl in CRED_PATTERNS:
        s = pat.sub(repl, s)
    for pat, repl in IP_PATTERNS:
        s = pat.sub(repl, s)
    return s


def assert_clean(text, where):
    bad = []
    if re.search(r"D:[\\/]00\.test", text, re.IGNORECASE):
        bad.append("absolute-path")
    for hostname in DEVICE_MAP:
        if hostname in text:
            bad.append(f"hostname:{hostname}")
    for pat, _ in PII_PATTERNS:
        if pat.search(text):
            bad.append("pii-leak")
            break
    for pat, _ in CRED_PATTERNS:
        if pat.search(text):
            bad.append("credential")
            break
    for pat, _ in IP_PATTERNS:
        if pat.search(text):
            bad.append("private-ip")
            break
    if bad:
        raise RuntimeError(f"anonymization leak in {where}: {bad}")


# ---------- Section parsing ----------

DEVICE_TIER_KEYWORDS = {
    "personal-root": [
        "personal-root", "퍼스널-루트", "personal root", "오너", "owner sovereignty",
    ],
    "company-work-pc": [
        "company-work-pc", "company work pc", "<work-pc>", "work-console",
        "execution-plane",
    ],
    "server": [
        "<server>", "ysh-server", "company-assigned-personal-server", "orchestrator",
        "server-runtime", "sora-primary",
    ],
    "team-mac": [
        "team-mac", "<mac-build>", "apple-build-node", "research-plane",
    ],
    "mobile-operator": [
        "mobile-operator", "mobile-approval", "ops-monitor", "personal-mobile",
        "tailscale-mobile",
    ],
}


def detect_device_tier_scope(text):
    text_l = text.lower()
    matched = []
    for tier, keywords in DEVICE_TIER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_l:
                matched.append(tier)
                break
    if not matched:
        return None
    if len(matched) >= 4:
        return "all"
    return ",".join(matched)


BLAST_RADIUS_PATTERNS = [
    (re.compile(r"\btier\s*0\b|\bblast[_\s]radius[_\s:]*0\b", re.IGNORECASE), 0),
    (re.compile(r"\btier\s*1\b|\bblast[_\s]radius[_\s:]*1\b", re.IGNORECASE), 1),
    (re.compile(r"\btier\s*2\b|\bblast[_\s]radius[_\s:]*2\b", re.IGNORECASE), 2),
    (re.compile(r"\btier\s*3\b|\bblast[_\s]radius[_\s:]*3\b", re.IGNORECASE), 3),
    (re.compile(r"\btier\s*4\b|\bblast[_\s]radius[_\s:]*4\b", re.IGNORECASE), 4),
    (re.compile(r"\btier\s*5\b|\bblast[_\s]radius[_\s:]*5\b", re.IGNORECASE), 5),
]


def detect_blast_radius_tier(text):
    found = []
    for pat, tier in BLAST_RADIUS_PATTERNS:
        if pat.search(text):
            found.append(tier)
    if not found:
        return None
    return max(found)


CAPABILITY_TOKEN_PATTERNS = [
    "neo-explorer", "neo-reviewer", "neo-architect", "neo-implementer",
    "neo-conflict-resolver", "neo-quant-researcher", "neo-paper-finalizer",
    "sora-filesystem", "sora-memory", "sora-devices", "sora-quant",
    "sora-comfyui", "sora-web", "sora-ops", "sora-calendar", "sora-gmail",
    "sora-sandbox",
]


def detect_capability_tokens(text):
    found = [tok for tok in CAPABILITY_TOKEN_PATTERNS if tok in text]
    return json.dumps(found, ensure_ascii=False) if found else None


def extract_references(text):
    refs = []
    for m in re.finditer(r"https?://[^\s)\]>]+", text):
        url = m.group(0).rstrip(".,;:")
        refs.append(url)
    for m in re.finditer(r"`([^`]+\.(?:md|yaml|json|py|js|ts))`", text):
        refs.append(m.group(1))
    seen = set()
    out = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return json.dumps(out, ensure_ascii=False)


def parse_markdown_sections(doc_id, doc_type, version, path, text):
    """Parse a markdown file into header-based sections."""
    sections = []
    # Split on # headings (any depth 1-4)
    pattern = re.compile(r"^(#{1,4})\s+(.+?)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        # No headings — treat full doc as one section
        sec_text = text.strip()
        if sec_text:
            sections.append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "version": version,
                "section_id": f"{doc_id}/root",
                "section_title": path.stem,
                "section_text": sec_text,
            })
        return sections

    # Header trail per depth
    trail = []
    for i, m in enumerate(matches):
        depth = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        # Maintain header trail
        trail = trail[: depth - 1]
        while len(trail) < depth - 1:
            trail.append("_")
        trail.append(title)

        section_id = f"{doc_id}/" + "/".join(
            re.sub(r"[^\w\-]+", "_", t)[:40] for t in trail
        )

        if not body:
            continue

        sections.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "section_id": section_id,
            "section_title": title,
            "section_text": body,
        })
    return sections


def parse_yaml_as_section(doc_id, doc_type, version, path, text):
    """YAML files: split by top-level keys."""
    sections = []
    # Strip header comments to look like first section
    lines = text.splitlines()
    current_key = None
    current_buf = []
    leading = []
    in_leading = True
    for ln in lines:
        if in_leading and (ln.strip().startswith("#") or not ln.strip()):
            leading.append(ln)
            continue
        in_leading = False
        # Top-level key (no indent, ends with : possibly with value)
        m = re.match(r"^([A-Za-z_][\w\-]*)\s*:", ln)
        if m and not ln.startswith(" "):
            if current_key is not None:
                sections.append({
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "version": version,
                    "section_id": f"{doc_id}/{current_key}",
                    "section_title": current_key,
                    "section_text": "\n".join(current_buf).strip(),
                })
            current_key = m.group(1)
            current_buf = [ln]
        else:
            current_buf.append(ln)
    if current_key is not None and current_buf:
        sections.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "section_id": f"{doc_id}/{current_key}",
            "section_title": current_key,
            "section_text": "\n".join(current_buf).strip(),
        })

    # Also include leading header as one section
    if leading and any(ln.strip() for ln in leading):
        sections.insert(0, {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "section_id": f"{doc_id}/_header",
            "section_title": "_header",
            "section_text": "\n".join(leading).strip(),
        })
    return sections


def collect_sections():
    all_sections = []
    source_index = []

    # Architecture + decision markdown docs
    for doc_id, doc_type, version, path in ARCHITECTURE_DOCS:
        if not path.exists():
            print(f"WARN: missing source {path}", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        secs = parse_markdown_sections(doc_id, doc_type, version, path, text)
        all_sections.extend(secs)
        source_index.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "source_filename": path.name,
            "section_count": len(secs),
            "raw_chars": len(text),
        })

    # Policy YAML docs
    for doc_id, doc_type, version, path in POLICY_DOCS:
        if not path.exists():
            print(f"WARN: missing policy {path}", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        secs = parse_yaml_as_section(doc_id, doc_type, version, path, text)
        all_sections.extend(secs)
        source_index.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "source_filename": path.name,
            "section_count": len(secs),
            "raw_chars": len(text),
        })

    # Runbooks (skip POSTMORTEM_TEMPLATE.md and README.md)
    runbook_files = sorted(RUNBOOKS_DIR.glob("*.md"))
    rb_index = 0
    for rb_path in runbook_files:
        if rb_path.name in ("POSTMORTEM_TEMPLATE.md", "README.md"):
            continue
        rb_index += 1
        doc_id = f"runbook-{rb_index:02d}-{rb_path.stem}"
        doc_type = "runbook"
        version = "v1"
        text = rb_path.read_text(encoding="utf-8")
        secs = parse_markdown_sections(doc_id, doc_type, version, rb_path, text)
        all_sections.extend(secs)
        source_index.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "source_filename": rb_path.name,
            "section_count": len(secs),
            "raw_chars": len(text),
        })

    return all_sections, source_index


# ---------- Main ----------

def main():
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    print("Collecting sections from architecture / policy / decision / runbook sources...")
    sections, source_index = collect_sections()
    print(f"Parsed {len(sections)} raw sections from {len(source_index)} source files")

    # Enrich each section with derived columns + anonymize
    enriched = []
    for s in sections:
        title = anonymize(s["section_title"]) or ""
        body = anonymize(s["section_text"]) or ""
        sec_id = s["section_id"]  # ids are slug-safe but still anonymize
        sec_id = anonymize(sec_id) or ""

        record = {
            "doc_id": s["doc_id"],
            "doc_type": s["doc_type"],
            "version": s["version"],
            "section_id": sec_id,
            "section_title": title,
            "section_text": body,
            "device_tier_scope": detect_device_tier_scope(body + "\n" + title),
            "blast_radius_tier": detect_blast_radius_tier(body),
            "capability_tokens_required": detect_capability_tokens(body),
            "references": extract_references(body),
        }
        enriched.append(record)

    # doc_type counts
    by_type = defaultdict(int)
    for r in enriched:
        by_type[r["doc_type"]] += 1
    print(f"Section breakdown: {dict(by_type)}")

    # Build artifacts
    sections_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in enriched
    ) + "\n"
    source_index_json = json.dumps(source_index, ensure_ascii=False, indent=2)

    metadata = {
        "name": "Sora Multi-Device Orchestration Architecture 2026",
        "version": "1.0.0",
        "publisher": "Neo Genesis Lab (neogenesislab)",
        "wikidata_qid_company": "Q139569680",
        "wikidata_qid_founder": "Q139569708",
        "license": "CC-BY-4.0",
        "language": ["ko", "en"],
        "totals": {
            "sections": len(enriched),
            "by_doc_type": dict(by_type),
            "sources": len(source_index),
        },
        "schema_columns": {
            "doc_id": "string — e.g. unified-bible / blueprint-v2 / enterprise-master / decisions-v1 / blast-radius / capability-tokens / runbook-XX",
            "doc_type": "string — architecture | policy | decision | runbook",
            "version": "string — semantic version of the source doc",
            "section_id": "string — slugified heading hierarchy",
            "section_title": "string — heading title",
            "section_text": "string — actual section content",
            "device_tier_scope": "string|null — personal-root | company-work-pc | server | team-mac | mobile-operator | all (comma-separated if multi)",
            "blast_radius_tier": "int|null — 0..5 (0=read, 5=irreversible)",
            "capability_tokens_required": "string|null — JSON array of subagent/tool token names",
            "references": "string — JSON array of inline links / file paths",
        },
        "schema_org_dataset": {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Sora Multi-Device Orchestration Architecture 2026",
            "description": (
                "A reference architecture corpus for a single-operator, multi-device "
                "personal AI orchestration core (codename: Sora). Covers a 7-layer "
                "design (Identity, Memory, Tool, Agent, Governance, Execution, Fleet), "
                "6-tier blast-radius classification, capability-token model, 11 "
                "enterprise D-gate decisions, and 13 production incident runbooks."
            ),
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {
                "@type": "Organization",
                "name": "Neo Genesis Lab",
                "url": "https://neogenesis.app",
                "sameAs": "https://www.wikidata.org/wiki/Q139569680",
            },
            "publisher": {
                "@type": "Organization",
                "name": "Neo Genesis Lab",
                "url": "https://neogenesis.app",
            },
            "url": f"https://huggingface.co/datasets/{REPO_ID}",
            "inLanguage": ["ko", "en"],
            "keywords": [
                "agent-architecture", "multi-device-orchestration",
                "blast-radius", "capability-tokens", "owner-sovereignty",
                "incident-runbook", "personal-ai-core", "single-operator",
                "tailscale-fleet", "model-context-protocol",
            ],
            "variableMeasured": [
                {"@type": "PropertyValue", "name": "device_tier_scope",
                 "description": "which fleet tier(s) the section applies to"},
                {"@type": "PropertyValue", "name": "blast_radius_tier",
                 "description": "0..5 risk classification of described action"},
                {"@type": "PropertyValue", "name": "capability_tokens_required",
                 "description": "list of subagent / tool tokens referenced"},
            ],
        },
        "anonymization": {
            "device_tier_names": "preserved as generic concepts (personal-root, server, etc)",
            "internal_hostnames": "redacted to <work-pc>, <gpu-worker>, <server>, <mac-build>",
            "owner_email_phone": "redacted to <redacted-email> / <redacted-phone>",
            "korean_rrn": "redacted to <redacted-rrn>",
            "api_tokens": "redacted to <redacted-*>",
            "absolute_paths": "redacted to <repo> / <workspace> / <home>",
            "private_ips": "redacted to <tailscale-ip> / <private-ip>",
            "post_emit_assertion": "every emitted string re-tested with all redaction regexes; publish aborts on leak",
        },
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    n_arch = by_type.get("architecture", 0)
    n_policy = by_type.get("policy", 0)
    n_decision = by_type.get("decision", 0)
    n_runbook = by_type.get("runbook", 0)

    yaml_front = """---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- text-generation
- text-classification
tags:
- agent-architecture
- multi-device-orchestration
- blast-radius
- capability-tokens
- incident-runbook
- model-context-protocol
- mcp
- personal-ai-core
- single-operator
- tailscale-fleet
- owner-sovereignty
- magentic-one
- langgraph
- claude-code
- sora
- neo-genesis
- bilingual
- korean
- english
size_categories:
- n<1K
pretty_name: "Sora Multi-Device Orchestration Architecture 2026"
configs:
- config_name: sections
  data_files:
  - split: train
    path: data/sections.jsonl
---
"""

    body = f"""
# Sora Multi-Device Orchestration Architecture 2026

> **A reference architecture corpus for a single-operator, multi-device personal AI orchestration core.** {len(enriched)} parsed sections from {len(source_index)} canonical source files: **{n_arch} architecture, {n_policy} policy, {n_decision} decision, {n_runbook} runbook** sections.

Released by **[Neo Genesis](https://neogenesis.app)** ([Wikidata Q139569680](https://www.wikidata.org/wiki/Q139569680)).

## Why this dataset is unique

Public AI-agent design corpora overwhelmingly assume a **single host** ("agent runs on one box"). What is rare publicly:

1. **Single-operator multi-device orchestration** — one human owner, several physical devices (`personal-root`, `<work-pc>`, `<server>`, `<mac-build>`, `<mobile-operator>`), and one logical agent core that coordinates across them under a unified policy.
2. **6-tier blast-radius classification** with explicit disclosure / 2FA / rollback-ledger requirements per tier (tier 0=read .. tier 5=irreversible).
3. **Per-task capability-token model** (not session tokens) with TTL, `blast_radius_ceiling`, and resource scope per subagent.
4. **Owner-sovereignty constitution** — the agent core is required to *disclose risk and ask*, and *never to refuse* an explicitly re-confirmed owner command. The opposite of typical "safety-by-refusal" public agents.
5. **Production incident runbooks** ({n_runbook} of them) all tied to Article 0 (owner override) + Article 4 (dead-man switch).

This is a real, in-use design — not a paper proposal — and it is published because the underlying brand and architect are publicly attested via Wikidata.

## Dataset summary

- **{len(enriched)} sections** in `data/sections.jsonl`. Each row is one parsed heading-section.
- **{len(source_index)} source files** indexed in `data/source_index.json`:
  - **Architecture & decision** ({n_arch + n_decision} sections): the unified bible (7-layer design), v2 master blueprint, enterprise-grade master with 9 workstreams, and the 11 D-gate decision ledger.
  - **Policies** ({n_policy} sections): `blast_radius.yaml` (6 tiers + disclosure templates), `capability_tokens.yaml` (per-subagent base capability), `permissions.yaml` (deny / ask / allow rules).
  - **Runbooks** ({n_runbook} sections): brain crash, redis OOM, gemini quota, telegram 409, qdrant down, local-LLM down, secret expired, VM reboot, hook loop, audit-log overflow, disk full, sora-engine import error, and full DR recovery.

## Schema

`data/sections.jsonl` — one JSON record per line:

| column | type | description |
|---|---|---|
| `doc_id` | string | e.g. `unified-bible / blueprint-v2 / enterprise-master / decisions-v1 / blast-radius / capability-tokens / runbook-01-brain_crash` |
| `doc_type` | string | `architecture | policy | decision | runbook` |
| `version` | string | semantic version of the source doc |
| `section_id` | string | slugified heading hierarchy (`<doc_id>/<h1>/<h2>/...`) |
| `section_title` | string | heading title |
| `section_text` | string | actual section body content |
| `device_tier_scope` | string\\|null | which fleet tier(s) the section applies to (`personal-root`, `company-work-pc`, `server`, `team-mac`, `mobile-operator`, `all`, or comma-separated) |
| `blast_radius_tier` | int\\|null | `0..5` if explicitly mentioned (0 = read, 5 = irreversible) |
| `capability_tokens_required` | string\\|null | JSON array of subagent / tool token names mentioned (`neo-explorer`, `neo-reviewer`, `sora-filesystem`, ...) |
| `references` | string | JSON array of inline links / file paths |

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "sections", split="train")
print(len(ds), "sections")

# Filter to runbook sections
runbooks = ds.filter(lambda r: r["doc_type"] == "runbook")
print(f"{{len(runbooks)}} runbook sections")

# Filter to high-blast-radius sections
risky = ds.filter(lambda r: r["blast_radius_tier"] is not None and r["blast_radius_tier"] >= 3)
print(f"{{len(risky)}} sections covering tier >= 3 actions")

# Filter by device tier
mobile_ops = ds.filter(
    lambda r: r["device_tier_scope"] is not None and "mobile-operator" in r["device_tier_scope"]
)
```

## Suggested research applications

1. **Multi-device agent design** — train or fine-tune routing agents on which device tier should host which capability.
2. **Blast-radius reasoning** — supervise classifiers that decide whether an LLM tool call requires disclosure / 2FA / rollback ledger before execution.
3. **Capability-token granting policies** — learn per-task token issuance under least-privilege constraints.
4. **Incident-response RAG** — runbook sections are structured under a uniform `Symptom / Trigger / Diagnose / Recovery / Prevention / CONSTITUTION` schema, suitable as ground-truth for incident-response retrieval evaluation.
5. **Owner-sovereignty alignment** — a real example of a "disclose-and-do" rather than "refuse-by-default" agent constitution.

## Anonymization

| Class | Treatment |
|---|---|
| Device tier names (`personal-root`, `company-work-pc`, `server`, `team-mac`, `mobile-operator`) | **Preserved** — generic architecture concepts |
| Internal hostnames | Redacted to `<work-pc>`, `<gpu-worker>`, `<server>`, `<mac-build>`, `<work-user>` |
| Owner email / phone | Redacted to `<redacted-email>` / `<redacted-phone>` |
| Korean RRN | Redacted to `<redacted-rrn>` |
| API tokens (`sk-*`, `ghp_*`, `hf_*`, JWT, bot tokens) | Redacted to `<redacted-*>` |
| Absolute Windows paths | Redacted to `<repo>` / `<workspace>` / `<home>` |
| Tailscale / private IPs | Redacted to `<tailscale-ip>` / `<private-ip>` |

Each emitted string is re-tested with all redaction regexes; publish aborts on leak.

## Provenance

- **Source**: Neo Genesis private SSOT (`.agent/knowledge/SORA_*` + `.agent/policies/*.yaml` + `.agent/runbooks/*.md`).
- **Curator**: Neo Genesis Lab (`neogenesislab` HuggingFace org).
- **Wikidata**: [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680), [Q139569708 (Yesol Heo, founder)](https://www.wikidata.org/wiki/Q139569708).
- **Related releases by the same operator**:
  - [`korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`ethicaai-meltingpot-mixedsafe-2026`](https://huggingface.co/datasets/neogenesislab/ethicaai-meltingpot-mixedsafe-2026)
  - [`whylab-gemini25-docker-validation`](https://huggingface.co/datasets/neogenesislab/whylab-gemini25-docker-validation)
  - [`sbu-pseo-effects-2026-04`](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04)
  - [`cross-agent-review-queue-2026`](https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026)
  - [`korean-llm-citation-baseline-2026`](https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026)

## Citation

```bibtex
@misc{{neogenesis_sora_orchestration_2026,
  title  = {{Sora Multi-Device Orchestration Architecture 2026: A reference corpus for single-operator multi-device personal AI orchestration}},
  author = {{Neo Genesis Lab}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{Architecture, policy, decision, and runbook sections covering 7-layer design, 6-tier blast radius, capability tokens, owner-sovereignty constitution, and {n_runbook} production incident runbooks}}
}}
```

## License

CC-BY-4.0 — free for research and commercial use with attribution to Neo Genesis Lab.

---

## 한국어 요약

**Sora Multi-Device Orchestration Architecture 2026** 은 1인 운영자가 여러 디바이스(`personal-root`, `<work-pc>`, `<server>`, `<mac-build>`, `<mobile-operator>`) 를 하나의 논리적 AI 코어로 통합 운영하는 **실사용 중인 reference 아키텍처** 의 SSOT 코퍼스다.

공개 에이전트 설계 자료 대부분이 **단일 호스트** 가정에서 출발하는 것과 달리, 이 데이터셋이 다루는 것:

1. **1인 운영자, 다중 디바이스, 단일 정책** — 사적 노드 / 회사 PC / 서버 / 빌드 노드 / 모바일을 동일한 권한 모델 아래 묶는다.
2. **6-tier blast-radius** — tier 0 (read) ~ tier 5 (irreversible) 로 행동을 분류하고, tier 별로 고지/2FA/롤백 의무를 명시한다.
3. **per-task capability-token 모델** — 세션 토큰이 아니라 작업당 토큰. TTL, blast_radius_ceiling, resource scope 가 subagent 별로 정의됨.
4. **오너 주권(Owner Sovereignty) 헌법** — "거부" 가 아니라 "고지 후 수행". 일반적인 safety-by-refusal 과 정반대 설계.
5. **{n_runbook} 개 실운영 incident runbook** — 모두 Article 0 (owner override) + Article 4 (dead-man switch) 와 정합.

이 데이터셋은 paper proposal 이 아니라 실제로 운영 중인 시스템의 SSOT 를 세션 단위로 파싱한 것이다. Wikidata 로 publicly attest 된 브랜드라서 익명화 후 공개 가능했다.

**익명화**: 디바이스 tier 이름은 generic architecture concept 으로 유지. 실제 hostname / email / phone / RRN / 절대 경로 / private IP 는 모두 redaction. 발행 직전 모든 문자열을 redaction regex 로 재검증.

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    readme = yaml_front + body

    # Final pre-emit assertion — every artifact must be clean
    artifacts = [
        ("README.md", readme),
        ("data/sections.jsonl", sections_jsonl),
        ("data/source_index.json", source_index_json),
        ("metadata.json", metadata_json),
    ]
    for name, content in artifacts:
        assert_clean(content, f"final-artifact:{name}")
    print("All artifacts passed anonymization assertion.")

    # Push to HF
    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"create_repo {REPO_ID} (dataset, public)")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    for path_in_repo, content in artifacts:
        print(f"upload {path_in_repo} ({len(content):,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/datasets/{REPO_ID}"
    print()
    print("PUBLISHED:", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
