"""
GEO (Generative Engine Optimization) Content Validator
========================================================

콘텐츠 publish 전에 AI 인용 가능성을 결정하는 신호들을 자동 검증.
HIVE MIND, blog_pipeline, SBU 자동 발행 시스템 어디서든 import 해서 사용.

Reference: .agent/knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md
근거: GEO 논문 arXiv 2311.09735 (Aggarwal) — Statistics +41%, 인용문 +28%, 출처 +115%
       GEO-SFE 논문 arXiv 2603.29979 — heading depth 3-5, paragraph 150-300 words, list/table 0.25-0.35
       Wellows 회귀분석 — semantic completeness r=0.87, 4.2배 인용

사용:
    from src.pipelines.geo_validator import validate, Verdict

    verdict = validate(html_or_markdown, metadata={"category": "research"})
    if verdict.passes:
        publish(...)
    else:
        for issue in verdict.issues:
            print(f"[{issue.severity}] {issue.message}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional

Severity = Literal["error", "warn", "info"]


# ──────────────────────────────────────────────
# 룰 임계값 (Master §2.4 + 8 트랙 리서치 수렴)
# ──────────────────────────────────────────────

DEFAULT_THRESHOLDS = {
    # Statistics 단위 (숫자 + 단위) per 500 words. 2.7배 citation 효과 측정값
    "statistics_per_500w_min": 3,

    # 인용문 (quotation) 최소 1개 — Aggarwal +41%
    "quotations_min": 1,

    # 출처 링크 (외부 https) 최소 2개 — Aggarwal +115% (5위 사이트)
    "external_citations_min": 2,

    # Self-contained paragraph length (Wellows r=0.87 답변 단락)
    "answer_paragraph_min_words": 40,
    "answer_paragraph_max_words": 167,

    # Heading hierarchy (GEO-SFE p<0.001)
    "heading_depth_min": 2,    # 최소 H2
    "heading_depth_max": 5,    # 최대 H5
    "h2_min_count": 2,         # 최소 2개 H2 섹션

    # 단어 수 (너무 짧은 placeholder 차단)
    "min_word_count": 300,

    # Schema.org / Open Graph / dateModified 검증 (메타데이터 입력으로 처리)
    "require_schema_article": True,
    "require_date_modified": True,
    "require_canonical_url": True,
}


# ──────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────

@dataclass
class Issue:
    severity: Severity
    code: str
    message: str
    detail: Optional[str] = None


@dataclass
class Verdict:
    passes: bool
    score: int  # 0-100
    issues: list[Issue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


# ──────────────────────────────────────────────
# 검증 헬퍼
# ──────────────────────────────────────────────

# 통계 패턴: 숫자(+소수) + 단위/% 또는 표시. 예: "47.9%", "32K", "$15-25/month", "~$0.005/call"
STAT_RE = re.compile(
    r"(?:\d{1,3}(?:[,.]\d+)*\s*[%]"            # percentages (47.9%)
    r"|\$\d+(?:[.,]\d+)?(?:[KMBkmb])?"          # currency ($15, $399.99)
    r"|\d+(?:[.,]\d+)?\s*[KMBkmb](?=\s|/|$)"   # K/M/B suffix
    r"|\d+\s*(?:words?|tokens?|seconds?|days?|hours?|minutes?|months?|years?|requests?|samples?|seeds?|episodes?|cores?|GB|MB|GiB|MiB|x|×)\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:fold|times|배)\b"
    r")",
    flags=re.IGNORECASE,
)

QUOTE_RE = re.compile(r'(?:"[^"]{15,}?"|\'[^\']{20,}?\'|<blockquote>)', re.IGNORECASE)

# 외부 https 링크 (자기 도메인 제외)
EXT_LINK_RE = re.compile(r'https?://(?!neogenesis\.app|localhost|127\.0\.0\.1)([^\s\)\]\>"\']+)')

# Heading 추출 (HTML + Markdown 둘 다)
H_HTML_RE = re.compile(r'<(h[1-6])[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
H_MD_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w가-힣]+\b", text))


def _extract_paragraphs(content: str) -> list[str]:
    # HTML <p>...</p> 또는 Markdown 빈 줄 분리
    if "<p" in content.lower():
        return [
            _strip_html(m).strip()
            for m in re.findall(r"<p[^>]*>(.*?)</p>", content, flags=re.IGNORECASE | re.DOTALL)
        ]
    return [p.strip() for p in re.split(r"\n\s*\n", _strip_html(content)) if p.strip()]


def _extract_headings(content: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for m in H_HTML_RE.finditer(content):
        level = int(m.group(1)[1])
        out.append((level, _strip_html(m.group(2)).strip()))
    for m in H_MD_RE.finditer(content):
        out.append((len(m.group(1)), m.group(2).strip()))
    return out


# ──────────────────────────────────────────────
# 메인 validate
# ──────────────────────────────────────────────

def validate(
    content: str,
    metadata: Optional[dict] = None,
    thresholds: Optional[dict] = None,
) -> Verdict:
    """
    HTML 또는 Markdown 콘텐츠 + 메타데이터를 받아 GEO 검증 리포트 반환.

    metadata 권장 키:
      - category: 콘텐츠 카테고리 (research / blog / sbu / programmatic)
      - canonical_url: canonical absolute URL (None 이면 require_canonical_url 검증 실패)
      - date_modified: ISO 8601 (None 이면 require_date_modified 검증 실패)
      - schema_present: bool (Article/BlogPosting/ScholarlyArticle 부착 여부)
    """
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    meta = metadata or {}
    issues: list[Issue] = []

    plain = _strip_html(content)
    word_count = _word_count(plain)
    headings = _extract_headings(content)
    paragraphs = _extract_paragraphs(content)
    stats = STAT_RE.findall(plain)
    quotes = QUOTE_RE.findall(content)
    ext_links = EXT_LINK_RE.findall(content)

    metrics = {
        "word_count": word_count,
        "heading_count": len(headings),
        "paragraph_count": len(paragraphs),
        "statistics_count": len(stats),
        "quotation_count": len(quotes),
        "external_citation_count": len(ext_links),
        "h2_count": sum(1 for lvl, _ in headings if lvl == 2),
        "max_heading_depth": max((lvl for lvl, _ in headings), default=0),
        "min_heading_depth": min((lvl for lvl, _ in headings), default=0),
    }

    # Word count
    if word_count < th["min_word_count"]:
        issues.append(Issue(
            "error", "WORD_COUNT_LOW",
            f"단어 수 {word_count} < 최소 {th['min_word_count']}",
            "AI 가 인용할 만큼의 정보 밀도 부족. 최소 300단어, 권장 700+단어.",
        ))

    # Statistics density
    expected_stats = max(1, (word_count // 500)) * th["statistics_per_500w_min"]
    if len(stats) < expected_stats:
        issues.append(Issue(
            "error", "STATS_DENSITY_LOW",
            f"통계 단위 {len(stats)} < 권장 {expected_stats} (500단어당 {th['statistics_per_500w_min']}개)",
            "GEO 논문: Statistics +41% citation. 숫자 + 단위 형식 (예: '47.9%', '$399', '32K seeds').",
        ))

    # Quotations
    if len(quotes) < th["quotations_min"]:
        issues.append(Issue(
            "warn", "QUOTATIONS_LOW",
            f"인용문 {len(quotes)} < 최소 {th['quotations_min']}",
            "Aggarwal: 인용문 +28% visibility. \"...\" 또는 <blockquote> 권장.",
        ))

    # External citations
    if len(ext_links) < th["external_citations_min"]:
        issues.append(Issue(
            "error", "EXT_CITATIONS_LOW",
            f"외부 출처 {len(ext_links)} < 최소 {th['external_citations_min']}",
            "Aggarwal: 출처 인용 +115% visibility. 학술/공식 도메인 우선 (.edu/.gov/arxiv).",
        ))

    # Heading hierarchy
    if metrics["h2_count"] < th["h2_min_count"]:
        issues.append(Issue(
            "warn", "H2_COUNT_LOW",
            f"H2 섹션 {metrics['h2_count']} < 최소 {th['h2_min_count']}",
            "GEO-SFE: heading hierarchy 3-5 levels = +17.3% citation rate (p<0.001).",
        ))

    if headings and metrics["min_heading_depth"] < th["heading_depth_min"]:
        issues.append(Issue(
            "warn", "HEADING_DEPTH_OUT_OF_RANGE",
            f"최상위 heading {metrics['min_heading_depth']} 가 H{th['heading_depth_min']} 미만",
            "Page 본문은 H2 부터 시작. H1 은 article title 전용.",
        ))

    # Answer-first paragraph 길이 (첫 단락)
    if paragraphs:
        first_words = _word_count(paragraphs[0])
        if first_words < th["answer_paragraph_min_words"]:
            issues.append(Issue(
                "warn", "ANSWER_PARAGRAPH_SHORT",
                f"첫 단락 {first_words}단어 < 최소 {th['answer_paragraph_min_words']}",
                "Wellows: 134-167단어 self-contained 첫 단락이 r=0.87 인용 효과.",
            ))
        elif first_words > th["answer_paragraph_max_words"]:
            issues.append(Issue(
                "info", "ANSWER_PARAGRAPH_LONG",
                f"첫 단락 {first_words}단어 > 권장 {th['answer_paragraph_max_words']}",
                "권장 134-167. 더 길면 retrieval chunk 가 자르고 갈 수 있음.",
            ))

    # 메타데이터 검증
    if th["require_schema_article"] and not meta.get("schema_present"):
        issues.append(Issue(
            "error", "SCHEMA_MISSING",
            "Schema.org Article/BlogPosting/ScholarlyArticle 미부착",
            "Schema 적용 시 GPT-4 추출 정확도 16% → 54% (3.4배).",
        ))

    if th["require_canonical_url"] and not meta.get("canonical_url"):
        issues.append(Issue("warn", "CANONICAL_MISSING", "canonical URL 메타데이터 누락"))

    if th["require_date_modified"] and not meta.get("date_modified"):
        issues.append(Issue(
            "warn", "DATE_MODIFIED_MISSING",
            "dateModified 메타데이터 누락",
            "Freshness signal: 30일 sweet spot, 미설정 시 ChatGPT/Perplexity 인용 -40%.",
        ))

    # 점수 계산: 100 - error*15 - warn*5 - info*1, 0 floor
    score = 100
    for i in issues:
        score -= 15 if i.severity == "error" else 5 if i.severity == "warn" else 1
    score = max(0, score)

    passes = not any(i.severity == "error" for i in issues)

    return Verdict(passes=passes, score=score, issues=issues, metrics=metrics)


# ──────────────────────────────────────────────
# CLI 진입점
# ──────────────────────────────────────────────

def _format_verdict(v: Verdict) -> str:
    lines = [
        f"GEO Score: {v.score}/100 — {'PASS' if v.passes else 'BLOCK'}",
        f"Metrics: {v.metrics}",
    ]
    for i in v.issues:
        lines.append(f"  [{i.severity.upper()}] {i.code}: {i.message}")
        if i.detail:
            lines.append(f"      → {i.detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python geo_validator.py <html_or_md_path> [metadata.json]")
        sys.exit(1)

    content = open(sys.argv[1], encoding="utf-8").read()
    meta: dict = {}
    if len(sys.argv) >= 3:
        meta = json.loads(open(sys.argv[2], encoding="utf-8").read())

    v = validate(content, metadata=meta)
    print(_format_verdict(v))
    sys.exit(0 if v.passes else 1)
