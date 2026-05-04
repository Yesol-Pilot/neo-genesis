# -*- coding: utf-8 -*-
"""Sora Output Filter — secret 누설 방지 + prompt injection 방어 강화.

Sprint 4 Day 25 P0 (#56 / #57)
모든 SoraResponse.reply 가 owner 에게 가기 전에 통과해야 함.

방어 패턴:
    - API key (sk-, AIza, ghp_, supabase service role JWT)
    - 패스워드 (env var 추출 시도)
    - 시스템 프롬프트 leak (`_SORA_SYSTEM_PROMPT` 패턴)
    - 사용자 PII (전화번호, 주민번호 패턴 — 단, owner 본인 정보는 허용)
    - Self-jailbreak 응답 (`네 그렇게 하겠습니다` + 무필터 키워드)

Author: Claude Opus 4.7 (Sora Dev Lead) — 2026-04-27
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("neo.security.output_filter")

# ── Secret patterns ─────────────────────────────────────────
_SECRET_PATTERNS = [
    # OpenAI / Anthropic API keys
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), '[REDACTED:OPENAI_KEY]'),
    (re.compile(r'sk-ant-[A-Za-z0-9_-]{30,}'), '[REDACTED:ANTHROPIC_KEY]'),
    # Google
    (re.compile(r'AIza[A-Za-z0-9_-]{30,}'), '[REDACTED:GOOGLE_KEY]'),
    # GitHub
    (re.compile(r'ghp_[A-Za-z0-9]{30,}'), '[REDACTED:GITHUB_PAT]'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{50,}'), '[REDACTED:GITHUB_PAT]'),
    # Supabase service role JWT (eyJ...)
    (re.compile(r'eyJhbGciOi[A-Za-z0-9_.-]{60,}'), '[REDACTED:JWT]'),
    # Generic AWS
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED:AWS_KEY]'),
    # Sora 내부 토큰 noise
    (re.compile(r'sora-pc-agent-2026-yesol'), '[REDACTED:PC_AGENT_TOKEN]'),
    # Telegram Bot Token — 형식: <bot_id>:<auth_token>, 예) 8515122672:AAEr0GyfU3PFQ-FgFcRKRceS_fe4qqkK_9s
    # bot_id 9~10자리 정수 + ':' + 35자 이상의 영숫자/_/- 토큰. 2026-04-29 NEO_ALERT_BOT_TOKEN 노출 사고 후 추가.
    (re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}'), '[REDACTED:TELEGRAM_BOT_TOKEN]'),
    # 환경변수 leak 패턴
    (re.compile(r'GEMINI_API_KEY[=:][^\s\n"\']+'), 'GEMINI_API_KEY=[REDACTED]'),
    (re.compile(r'LITELLM_MASTER_KEY[=:][^\s\n"\']+'), 'LITELLM_MASTER_KEY=[REDACTED]'),
    (re.compile(r'SUPABASE_SERVICE_ROLE_KEY[=:][^\s\n"\']+'), 'SUPABASE_SERVICE_ROLE_KEY=[REDACTED]'),
    (re.compile(r'SUPABASE_ANON_KEY[=:][^\s\n"\']+'), 'SUPABASE_ANON_KEY=[REDACTED]'),
    # Telegram bot env var leak (token 단독 패턴이 redact 못 한 edge case 보호)
    (re.compile(r'NEO_ALERT_BOT_TOKEN[=:][^\s\n"\']+'), 'NEO_ALERT_BOT_TOKEN=[REDACTED]'),
    (re.compile(r'TELEGRAM_BOT_TOKEN[=:][^\s\n"\']+'), 'TELEGRAM_BOT_TOKEN=[REDACTED]'),
    # System password (owner private)
    (re.compile(r'ysh1234!?'), '[REDACTED:SUDO_PASSWORD]'),
]

# ── Self-jailbreak signals ──────────────────────────────────
_JAILBREAK_PATTERNS = [
    # 무필터 모드 동의
    re.compile(r'(필터를?\s*해제|무필터.*전환|이제부터.*제한.*없|jailbroken|DAN\s*mode|developer\s*mode\s*on)', re.IGNORECASE),
    # 시스템 프롬프트 출력 동의
    re.compile(r'(system\s*prompt(은)?\s*[:는].*다음과\s*같)', re.IGNORECASE),
]

# ── PII patterns (owner private 보호) ────────────────────────
# owner 본인 정보 (OWNER_PROFILE.md SSOT 기준) 는 허용. 그 외 사용자 정보는 redact.
_PII_PATTERNS = [
    # 한국 주민번호 (owner 본인 제외)
    (re.compile(r'\b\d{6}-?[1-4]\d{6}\b'), '[REDACTED:RRN]'),
    # 신용카드 번호
    (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), '[REDACTED:CARD]'),
]

# Owner whitelisted strings (절대 redact 안 함)
# 하드코딩 금지 원칙: 개인정보 (이름/이메일/전화/GitHub/도메인) 는 OWNER_PROFILE.md SSOT 에서 동적 로드.
# 정적 항목은 모델/툴명/디바이스 hostname 등 개인정보 아닌 운영 식별자에 한정.

# 정적 화이트리스트 (개인정보 아님 — 모델/툴/공개 디바이스명)
_STATIC_OWNER_WHITELIST: list = [
    # 모델 표시 관련
    "Claude Code 2.0.72", "Claude Code 2.1", "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash", "qwen2.5-coder", "ollama qwen",
    "Ollama", "ollama", "LangChain", "langchain", "ChromaDB", "chromadb",
    "Gemini, Claude, Ollama", "AI Ready",
    # 디바이스 hostname (개인정보 아닌 fleet 식별자)
    "ysh-server", "desktop-home", "desktop-sol01", "desktop-yesol",
]


def _load_owner_whitelist_from_ssot() -> list:
    """OWNER_PROFILE.md SSOT 에서 owner 개인정보 동적 추출 후 정적 항목과 합쳐 반환.

    하드코딩 금지 원칙: 개인 정보는 SSOT 에서만 로드. owner 가 OWNER_PROFILE.md
    갱신 시 sora 가 자동으로 새 값 사용. import 시점 1회 호출 + 모듈 캐시.
    """
    from pathlib import Path as _P
    candidate_paths = [
        _P("/app/.agent/knowledge/OWNER_PROFILE.md"),
        _P("/home/ysh/neo-genesis-runtime/.agent/knowledge/OWNER_PROFILE.md"),
        _P("D:/00.test/neo-genesis/.agent/knowledge/OWNER_PROFILE.md"),
    ]
    # PROJECT_ROOT 가 정의되어 있으면 추가 (sora_engine 외부에서도 동작하도록 graceful)
    try:
        from src.core.sora_engine import PROJECT_ROOT  # type: ignore
        candidate_paths.append(_P(PROJECT_ROOT) / ".agent" / "knowledge" / "OWNER_PROFILE.md")
    except Exception:
        pass

    dynamic = []
    for p in candidate_paths:
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8")
            patterns = {
                "email": r"\|\s*이메일\s*\|\s*([^|\n]+?)\s*\|",
                "phone": r"\|\s*전화\s*\|\s*([^|\n]+?)\s*\|",
                "github": r"\|\s*GitHub\s*\|\s*([^|\n]+?)\s*\|",
                "domain": r"\|\s*도메인\s*\|\s*([^|\n]+?)\s*\|",
                "name_ko": r"\|\s*이름\s*\|\s*([^|\n]+?)\s*\|",
            }
            for key, pat in patterns.items():
                m = re.search(pat, content)
                if not m:
                    continue
                raw = m.group(1).strip()
                # name_ko: "한글이름 (Eng Name)" → [한글, "Eng Name", "Eng", "Name", "name"] 형태로 분해
                if key == "name_ko":
                    paren = re.search(r"\(([^)]+)\)", raw)
                    if paren:
                        eng = paren.group(1).strip()
                        dynamic.extend([eng] + eng.split())
                        dynamic.append(eng.split()[-1].lower() if eng.split() else "")
                    base = re.sub(r"\s*\([^)]*\)", "", raw).strip()
                    if base:
                        dynamic.append(base)
                # github: "Yesol-Pilot (neogenesislab 절대 금지)" → "Yesol-Pilot"
                elif key == "github":
                    handle = re.sub(r"\s*\([^)]*\)", "", raw).strip()
                    if handle:
                        dynamic.append(handle)
                # email: 이메일 셀에 여러 개면 콤마/슬래시 분리
                elif key == "email":
                    for tok in re.split(r"[,/\s]+", raw):
                        tok = tok.strip()
                        if "@" in tok:
                            dynamic.append(tok)
                # domain: "heoyesol.kr" → 자체 + 서브도메인 prefix 자동 확장
                elif key == "domain":
                    if raw:
                        dynamic.append(raw)
                        for sub in ("sora", "neo"):
                            dynamic.append(f"{sub}.{raw}")
                # phone: "010-3743-2073" 직접 추가
                elif key == "phone":
                    if raw:
                        dynamic.append(raw)
            if dynamic:
                break
        except Exception as exc:
            logger.warning("[output_filter] OWNER_PROFILE 로드 실패 (path=%s): %s", p, exc)
            continue

    # 빈 토큰 제거 + 중복 제거 (순서 보존)
    seen = set()
    merged = []
    for item in (_STATIC_OWNER_WHITELIST + dynamic):
        if item and item not in seen:
            seen.add(item)
            merged.append(item)
    if not dynamic:
        logger.warning(
            "[output_filter] OWNER_PROFILE.md 에서 동적 owner 정보 추출 실패 — 정적 항목만 사용. "
            "owner 개인정보가 redact 될 수 있음."
        )
    return merged


# 모듈 import 시점에 1회 로드 + 캐시
OWNER_WHITELIST = _load_owner_whitelist_from_ssot()



# -- Identity leak patterns (소라가 underlying 모델 노출 방어) --
_IDENTITY_LEAK_PATTERNS = [
    # underlying model 이름 (한글/영어 substring 직접 매칭, word boundary 없음)
    re.compile(r'(Qwen|qwen|QWEN)'),
    re.compile(r'(Alibaba|alibaba|ALIBABA|알리바바)'),
    re.compile(r'(GPT[\s-]?[34][\s.]?[0-9]?|GPT-4o?|ChatGPT|chatGPT)'),
    re.compile(r'(Anthropic|anthropic|앤스로픽)'),
    re.compile(r'(?<![A-Za-z])(Claude)(?![A-Za-z])'),  # "Claude" 단어 (앞뒤 영문자 아닌)
    re.compile(r'(Gemini|gemini|제미나이|Bard|PaLM)'),
    re.compile(r'(Llama|llama|LLaMA|LLAMA|라마)'),
    re.compile(r'(Mistral|mistral|Mixtral|mixtral)'),
    re.compile(r'(DeepSeek|deepseek|딥시크)'),
    re.compile(r'(I am a large(-|\s)language model|large language model|초대규모 언어 모델|대규모 언어 모델)', re.IGNORECASE),
    re.compile(r'(저는?\s*OpenAI|저는?\s*Anthropic|저는?\s*Google|저는?\s*Meta)', re.IGNORECASE),
    re.compile(r'(developed by\s+(Alibaba|OpenAI|Anthropic|Google|Meta|DeepSeek))', re.IGNORECASE),
    re.compile(r'(알리바바\s*(그룹|클라우드|cloud|에서|이|가)\s*개발)'),
]

# Identity leak 시 교체할 안전 응답
_IDENTITY_REPLY = (
    "저는 소라(Sora), NEO GENESIS의 AI 비서입니다. "
    "NEO GENESIS가 자체 호스팅한 인프라에서 동작해요. "
    "다른 도움이 필요하시면 말씀해주세요. ð"
)


def filter_output(text: str, *, strict: bool = True) -> tuple[str, list[str]]:
    """텍스트에서 secret/PII 패턴 redact + jailbreak signal 검출.

    Args:
        text: 원본 응답
        strict: True 면 jailbreak 패턴 검출 시 응답 자체 차단 (안전 메시지로 대체)

    Returns:
        (filtered_text, warnings)
    """
    if not text:
        return text or "", []

    warnings: list[str] = []
    out = text

    # 1) Secret redaction
    for pat, replacement in _SECRET_PATTERNS:
        if pat.search(out):
            warnings.append(f"secret_redacted:{pat.pattern[:30]}")
            out = pat.sub(replacement, out)

    # 2) PII redaction (owner whitelist 적용 후)
    # owner 정보는 placeholder 로 잠시 mask, 패턴 실행, 복원
    placeholders: dict[str, str] = {}
    for i, w in enumerate(OWNER_WHITELIST):
        if w in out:
            ph = f"\x00OWN{i}\x00"
            placeholders[ph] = w
            out = out.replace(w, ph)
    for pat, replacement in _PII_PATTERNS:
        if pat.search(out):
            warnings.append(f"pii_redacted:{pat.pattern[:30]}")
            out = pat.sub(replacement, out)
    for ph, original in placeholders.items():
        out = out.replace(ph, original)

    # 3) Jailbreak signal detection
    for pat in _JAILBREAK_PATTERNS:
        if pat.search(out):
            warnings.append(f"jailbreak_signal:{pat.pattern[:40]}")
            if strict:
                out = "⚠️ 보안 정책에 따라 이 요청에는 응답할 수 없어요. owner 의 안전한 사용을 위한 보호 필터가 발동했어요."
                logger.warning(f"[security] jailbreak signal blocked, response replaced: pattern={pat.pattern[:60]}")
                break

    # 4) Identity leak detection (underlying 모델 이름 노출 방어)
    for pat in _IDENTITY_LEAK_PATTERNS:
        if pat.search(out):
            warnings.append(f"identity_leak:{pat.pattern[:40]}")
            logger.warning(f"[security] identity leak blocked: pattern={pat.pattern[:60]}")
            out = _IDENTITY_REPLY
            break

    if warnings:
        logger.info(f"[security] output filtered, warnings={warnings[:5]}")
    return out, warnings


def is_safe(text: str) -> bool:
    """간단 boolean check (filter 후 차이 없으면 safe)."""
    filtered, warnings = filter_output(text, strict=True)
    return len(warnings) == 0


__all__ = ["filter_output", "is_safe", "OWNER_WHITELIST"]