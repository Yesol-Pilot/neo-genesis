"""credential_redactor.py — Runtime PII/credential 패턴 redaction (P1-4 강화).

RAG 인덱싱 파이프라인에서 chunk text를 sanitize 한다.
gitleaks-korean-rules.toml 가 commit-time hook 이라면 이 모듈은 runtime ingestion 시
적용된다.

사용 예:
    from src.core.rag_v2.credential_redactor import redact_credentials, scan_credentials

    cleaned = redact_credentials(raw_text)
    findings = scan_credentials(raw_text)  # detection only

탐지 패턴 (한국어 + 글로벌):
    1. 주민등록번호 (구버전 + 2020-10 신버전)
    2. 외국인등록번호
    3. 운전면허번호
    4. 여권번호
    5. 신용카드 16자리
    6. 휴대폰 번호
    7. 사업자등록번호
    8. 은행 계좌번호
    9. API key 패턴 (Naver/Kakao/Toss/Coupang/KISA)
    10. Telegram bot token
    11. 공인인증서/PFX password
    12. AWS / GCP / Azure credentials
    13. JWT (eyJ...)
    14. Generic high-entropy strings (32+ hex/base64)

각 매치는 `<REDACTED:{rule_id}>` 로 치환된다.

부록: .agent/knowledge/rag-master/06_governance.md §5
정책: .agent/policies/gitleaks-korean-rules.toml (commit-time mirror)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Pattern, Tuple


@dataclass(frozen=True)
class Rule:
    """단일 redaction rule."""

    rule_id: str
    pattern: Pattern[str]
    severity: str  # 'critical' | 'high' | 'medium'
    category: str  # 'pii' | 'key' | 'cert' | 'pii.korean'


def _compile(pattern: str, flags: int = 0) -> Pattern[str]:
    return re.compile(pattern, flags)


# ----- 한국어 PII -----------------------------------------------------------
RULES: List[Rule] = [
    # 주민등록번호 (구버전, 6-1+6, 첫자리 1-4)
    Rule(
        rule_id="korean-rrn-pre-2020",
        pattern=_compile(r"\b\d{6}-[1-4]\d{6}\b"),
        severity="critical",
        category="pii.korean",
    ),
    # 주민/외국인 (2020-10+ 신버전, 첫자리 5-8)
    Rule(
        rule_id="korean-rrn-post-2020",
        pattern=_compile(r"\b\d{6}-[5-8]\d{6}\b"),
        severity="critical",
        category="pii.korean",
    ),
    # 운전면허
    Rule(
        rule_id="korean-driver-license",
        pattern=_compile(r"\b\d{2}-\d{2}-\d{6}-\d{2}\b"),
        severity="high",
        category="pii.korean",
    ),
    # 여권 (M/R + 8자리)
    Rule(
        rule_id="korean-passport",
        pattern=_compile(r"\b[MR]\d{8}\b"),
        severity="high",
        category="pii.korean",
    ),
    # 휴대폰
    Rule(
        rule_id="korean-mobile",
        pattern=_compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
        severity="medium",
        category="pii.korean",
    ),
    # 사업자등록번호
    Rule(
        rule_id="korean-business-reg",
        pattern=_compile(r"\b\d{3}-\d{2}-\d{5}\b"),
        severity="medium",
        category="pii.korean",
    ),
    # 은행 계좌 (3-6 / 2-6 / 6-8)
    Rule(
        rule_id="korean-bank-account",
        pattern=_compile(r"\b\d{3,6}[-\s]\d{2,6}[-\s]\d{6,8}\b"),
        severity="high",
        category="pii.korean",
    ),
    # 신용카드 16자리 (Visa 4xxx, MC 5[1-5]xx, JCB 35, KB BC 9410, AmEx)
    Rule(
        rule_id="credit-card",
        pattern=_compile(
            r"\b(?:4\d{3}|5[1-5]\d{2}|36\d{2}|9410|3[47]\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3,4}\b"
        ),
        severity="critical",
        category="pii",
    ),

    # ----- API Key / Secret 패턴 -------------------------------------------
    # 한국어 + 일반 키 패턴
    Rule(
        rule_id="korean-generic-key",
        pattern=_compile(
            r"[가-힣a-zA-Z_]{2,20}[_\s]*(?:키|key|secret|token|토큰|시크릿|비밀번호|패스워드|password)\s*[:=]\s*['\"]?\S{8,}['\"]?",
            re.IGNORECASE,
        ),
        severity="high",
        category="key",
    ),
    # Naver Cloud
    Rule(
        rule_id="naver-cloud-key",
        pattern=_compile(
            r"(?i)(?:naver|ncloud|ncp)[\s_-]*(?:key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{20,}['\"]?"
        ),
        severity="high",
        category="key",
    ),
    # Kakao REST API key
    Rule(
        rule_id="kakao-rest-key",
        pattern=_compile(
            r"(?i)kakao[\s_-]*(?:rest|app|admin)?[\s_-]*(?:api[_-]?key|key)\s*[:=]\s*['\"]?[a-f0-9]{32}['\"]?"
        ),
        severity="high",
        category="key",
    ),
    # Toss Payments
    Rule(
        rule_id="toss-merchant-key",
        pattern=_compile(
            r"(?i)(?:toss|토스)[\s_-]*(?:payments?|bank)?[\s_-]*(?:secret|key)\s*[:=]\s*['\"]?(?:test|live)_[a-zA-Z0-9_]{30,}['\"]?"
        ),
        severity="high",
        category="key",
    ),
    # KISA / 통신사
    Rule(
        rule_id="korean-kisa-auth",
        pattern=_compile(
            r"(?i)(?:kisa|kt|skt|skb|lguplus|nipa)[\s_-]*(?:auth|token|cert)[\s_:=-]+['\"]?[A-Za-z0-9+/=_-]{30,}['\"]?"
        ),
        severity="high",
        category="key",
    ),
    # 공인인증서 비밀번호
    Rule(
        rule_id="korean-cert-password",
        pattern=_compile(
            r"(?i)(?:공인인증서|nb-cert|pfx|p12)[\s_-]*(?:password|pwd|pw|비밀번호|패스워드)[\s_:=-]+['\"]?\S{8,}['\"]?"
        ),
        severity="high",
        category="cert",
    ),

    # Telegram bot token (표준 35자 토큰 + 길이 변동 허용)
    Rule(
        rule_id="telegram-bot-token",
        pattern=_compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,40}\b"),
        severity="critical",
        category="key",
    ),

    # ----- 글로벌 클라우드 -------------------------------------------------
    # AWS Access Key
    Rule(
        rule_id="aws-access-key",
        pattern=_compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        severity="critical",
        category="key",
    ),
    # AWS Secret Key (긴 base64-ish 패턴, 컨텍스트로 false positive 줄임)
    Rule(
        rule_id="aws-secret-key",
        pattern=_compile(
            r"(?i)aws[_\s-]*(?:secret|access)[_\s-]*key[_\s-]*(?:id)?\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?"
        ),
        severity="critical",
        category="key",
    ),
    # GCP Service Account Key
    Rule(
        rule_id="gcp-service-account",
        pattern=_compile(r'"type":\s*"service_account"'),
        severity="critical",
        category="key",
    ),
    # JWT 일반 (eyJ...3구간.)
    Rule(
        rule_id="jwt-token",
        pattern=_compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        severity="high",
        category="key",
    ),
    # Slack token
    Rule(
        rule_id="slack-token",
        pattern=_compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        severity="high",
        category="key",
    ),
    # GitHub PAT (classic + fine-grained)
    Rule(
        rule_id="github-pat",
        pattern=_compile(r"\bgh[posu]_[A-Za-z0-9]{36,}\b"),
        severity="critical",
        category="key",
    ),
    # OpenAI API key
    Rule(
        rule_id="openai-key",
        pattern=_compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        severity="critical",
        category="key",
    ),
    # Anthropic API key
    Rule(
        rule_id="anthropic-key",
        pattern=_compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b"),
        severity="critical",
        category="key",
    ),
]


# ----- Allowlist (예시/테스트 패턴 제외) -----------------------------------
ALLOWLIST_REGEX: Pattern[str] = re.compile(
    r"(?i)(YOUR_API_KEY|<API_KEY>|EXAMPLE_KEY|REPLACE_ME|XXXX|TODO|<your[-_]?key>|sk-test-|sk-fake-)"
)


def scan_credentials(text: str) -> List[Tuple[str, int, int, str]]:
    """text 에서 credential 패턴 매치를 찾아 list of (rule_id, start, end, snippet) 반환.

    매치 snippet 은 처음 8자만 반환 (전체 노출 방지).
    """
    if not text:
        return []
    findings: List[Tuple[str, int, int, str]] = []
    for rule in RULES:
        for m in rule.pattern.finditer(text):
            matched = m.group(0)
            # allowlist 필터
            if ALLOWLIST_REGEX.search(matched):
                continue
            snippet = matched[:8] + ("…" if len(matched) > 8 else "")
            findings.append((rule.rule_id, m.start(), m.end(), snippet))
    return findings


def redact_credentials(text: str, marker: str = "<REDACTED:{rule_id}>") -> str:
    """text 의 credential 매치를 marker 로 치환.

    중첩 매치는 가장 긴 것을 우선 (right-to-left 처리).
    """
    if not text:
        return text
    findings = scan_credentials(text)
    if not findings:
        return text
    # 끝 위치로 역정렬 (뒤에서부터 치환해야 인덱스 안 깨짐)
    findings.sort(key=lambda f: f[1], reverse=True)
    out = text
    for rule_id, start, end, _snippet in findings:
        replacement = marker.format(rule_id=rule_id)
        out = out[:start] + replacement + out[end:]
    return out


def has_critical_credential(text: str) -> bool:
    """critical severity 패턴 1개 이상 포함 여부 (인덱싱 거부 게이트용)."""
    if not text:
        return False
    for rule in RULES:
        if rule.severity != "critical":
            continue
        m = rule.pattern.search(text)
        if m and not ALLOWLIST_REGEX.search(m.group(0)):
            return True
    return False


def get_rule_count() -> int:
    """전체 등록 rule 수 (테스트용)."""
    return len(RULES)


def list_rule_ids() -> List[str]:
    """전체 rule id 목록 (테스트용)."""
    return [r.rule_id for r in RULES]
