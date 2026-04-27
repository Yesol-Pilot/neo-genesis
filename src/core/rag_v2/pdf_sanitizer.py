"""pdf_sanitizer.py — PDF/외부 문서 prompt injection 패턴 sanitizer (P1-5 잔존 위험 대응).

배경 (잔존 위험 P1-5):
    PDF/외부 문서 인덱싱 시 attacker 가 chunk 본문에 prompt injection 을 심어 RAG
    응답을 오염시킬 수 있다 (예: "ignore all previous instructions", "you are now…",
    invisible Unicode characters, hidden prompts in white text 등).

방어 전략 (3단):
    1. **Pattern detection**: 알려진 injection 표현 매치 → 의심 score
    2. **Unicode normalization**: zero-width / RTL 문자 / private-use area 제거
    3. **Quarantine**: critical score 시 chunk skip (인덱싱 거부) + audit log

사용:
    from src.core.rag_v2.pdf_sanitizer import sanitize_external_chunk, scan_injection

    cleaned = sanitize_external_chunk(raw_text, source_uri='paper.pdf')
    findings = scan_injection(raw_text)  # detection-only

기준: AgentDojo 22 attack patterns (2025) + PoisonedRAG / GASLITE 회귀.
부록: .agent/knowledge/rag-master/06_governance.md §6
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Pattern, Tuple


# ---- 알려진 prompt injection 패턴 -----------------------------------------
@dataclass(frozen=True)
class InjectionRule:
    rule_id: str
    pattern: Pattern[str]
    severity: str  # 'critical' | 'high' | 'medium' | 'low'


def _ci(p: str) -> Pattern[str]:
    return re.compile(p, re.IGNORECASE | re.MULTILINE)


INJECTION_RULES: List[InjectionRule] = [
    # 명시적 명령 무효화 시도
    InjectionRule(
        "ignore-instructions",
        _ci(r"\b(?:ignore|disregard|forget|override|cancel)\s+(?:all\s+)?(?:previous|prior|above|earlier|the)\s+(?:instructions?|rules?|prompts?|commands?|system\s+prompt)"),
        "critical",
    ),
    InjectionRule(
        "ignore-instructions-korean",
        _ci(r"(?:이전|기존|위의|모든|앞)(?:[\s\S]{0,20}?)(?:지시|명령|규칙|프롬프트)(?:[\s\S]{0,20}?)(?:무시|취소|잊|덮어쓰)"),
        "critical",
    ),
    # role hijack
    InjectionRule(
        "role-hijack",
        _ci(r"\byou\s+are\s+now\s+(?:a|an|the)?\s*\w*\s*(?:assistant|admin|developer|root|jailbroken|DAN|hacker)"),
        "critical",
    ),
    InjectionRule(
        "system-prompt-leak",
        _ci(r"\b(?:reveal|show|print|dump|output|repeat)\s+(?:your\s+)?(?:system|developer|hidden)\s+prompt"),
        "high",
    ),
    # 명령 토큰 마커
    InjectionRule(
        "instruction-marker",
        _ci(r"<\|(?:im_start|im_end|system|user|assistant|tool_call|function_call)\|?>"),
        "high",
    ),
    InjectionRule(
        "jailbreak-prefix",
        _ci(r"\b(?:DAN\s+mode|developer\s+mode|jailbreak|ignore\s+safety|disable\s+filters?|no\s+restrictions)"),
        "critical",
    ),
    # 데이터 유출 시도
    InjectionRule(
        "exfiltration-prompt",
        _ci(r"\b(?:send|email|post|upload|leak|exfiltrate|forward)\s+(?:the\s+)?(?:contents?|data|file|secret|credential|password)\s+(?:to|via|using)"),
        "critical",
    ),
    # tool/function injection
    InjectionRule(
        "tool-call-injection",
        _ci(r"<tool[_-]call>|</tool[_-]call>|<function[_-]call>|\{\s*\"function\"\s*:\s*\"[^\"]+\"\s*,\s*\"arguments\"\s*:"),
        "high",
    ),
    # URL navigation injection
    InjectionRule(
        "navigation-injection",
        _ci(r"\b(?:visit|browse|open|navigate to|fetch|GET|curl|wget)\s+https?://"),
        "medium",
    ),
    # MCP/Anthropic-style instruction injection
    InjectionRule(
        "mcp-instruction-tag",
        _ci(r"<\s*(?:system_instruction|claude_instruction|mcp_instruction)\s*>"),
        "high",
    ),
    # 특정 모델명 hijack
    InjectionRule(
        "model-hijack",
        _ci(r"\b(?:as\s+)?(?:GPT-?[345]|Claude|Gemini|LLaMA)\s*[,:.]?\s*(?:please|now|you\s+must|do\s+the\s+following)"),
        "medium",
    ),
    # base64 chunk (대용량) — encoding-based smuggling
    InjectionRule(
        "base64-smuggling",
        re.compile(r"[A-Za-z0-9+/]{200,}={0,3}"),
        "low",
    ),
    # invisible Unicode hint (prompt injection in white space)
    InjectionRule(
        "tag-injection-html",
        _ci(r"<!--\s*(?:system|prompt|instruction|claude|gpt)[^>]{0,200}-->"),
        "high",
    ),
]


# ---- Unicode 정규화 (invisible / control characters 제거) ------------------
# Zero-width chars, RTL marks, format chars, private-use area
_INVISIBLE_CHAR_REGEX = re.compile(
    r"[​-‏‪-‮⁠-⁩⁪-⁯﻿￹-￻-]"
)


def normalize_unicode(text: str) -> str:
    """zero-width + RTL/LTR mark + format + PUA 문자 제거 + NFKC normalize."""
    if not text:
        return text
    # 보이지 않는 문자 제거
    cleaned = _INVISIBLE_CHAR_REGEX.sub("", text)
    # 호환 정규화 (소속 문자 → ASCII 변형)
    cleaned = unicodedata.normalize("NFKC", cleaned)
    return cleaned


def scan_injection(text: str) -> List[Tuple[str, str, int, int]]:
    """injection 패턴 스캔. (rule_id, severity, start, end) 반환."""
    if not text:
        return []
    findings: List[Tuple[str, str, int, int]] = []
    for rule in INJECTION_RULES:
        for m in rule.pattern.finditer(text):
            findings.append((rule.rule_id, rule.severity, m.start(), m.end()))
    return findings


SEVERITY_SCORE = {"low": 1, "medium": 3, "high": 7, "critical": 15}


def compute_injection_risk(text: str) -> int:
    """injection findings 의 가중합 risk score. ≥15 = critical, ≥7 = high."""
    findings = scan_injection(text)
    return sum(SEVERITY_SCORE.get(sev, 0) for _, sev, _, _ in findings)


def is_quarantined(text: str, threshold: int = 15) -> bool:
    """critical injection 패턴 포함 여부 (default: critical 1개 이상 → True)."""
    return compute_injection_risk(text) >= threshold


def sanitize_external_chunk(text: str, *, source_uri: str = "", redact_marker: str = "<INJECTION_REMOVED>") -> str:
    """외부 문서 chunk 를 sanitize.

    절차:
      1. unicode normalize (invisible 문자 제거)
      2. critical/high 패턴 매치 → marker 치환
      3. quarantine 여부는 caller 가 `is_quarantined` 로 별도 판정 권장

    Args:
        text: 원본 chunk text
        source_uri: 디버그용 (현재 미사용 — caller 가 audit 시 기록)
        redact_marker: 치환 마커
    """
    if not text:
        return text
    # 1. unicode normalize
    cleaned = normalize_unicode(text)
    # 2. high+/critical 패턴 치환 (low/medium 은 보존)
    findings = [
        (s, e)
        for rule_id, sev, s, e in scan_injection(cleaned)
        if sev in ("high", "critical")
    ]
    if not findings:
        return cleaned
    findings.sort(key=lambda x: x[0], reverse=True)
    out = cleaned
    for s, e in findings:
        out = out[:s] + redact_marker + out[e:]
    return out


def list_rule_ids() -> List[str]:
    return [r.rule_id for r in INJECTION_RULES]


def get_rule_count() -> int:
    return len(INJECTION_RULES)
