# -*- coding: utf-8 -*-
"""
NEO GENESIS 통합 데몬 (Unified Daemon)

모든 계열사(SBU)를 하나의 프로세스로 관리하는 중앙 스케줄러.
기존 scheduler.py, crypto_scheduler.py의 기능을 통합하여
단일 APScheduler 인스턴스로 운영합니다.

스케줄:
    06:00 — 감사국 정기 감사 (전 계열사)
    07:00 — 리워드 수확기 (거래소 이벤트 크롤링)
    08:00 — 블로그 자동 포스팅 #1
    14:00 — 블로그 자동 포스팅 #2
    18:00 — 에어드롭 파밍 (테스트넷 트랜잭션)
    22:00 — 일일 종합 리포트 (텔레그램)
    매 3시간 — 리워드 수확 (추가, jitter ±1시간)
    매주 일요일 04:00 — Gödel 자기개선 사이클

사용법:
    python neo_genesis_daemon.py                  # 데몬 모드 (상시 실행)
    python neo_genesis_daemon.py --once harvest   # 리워드 수확만 1회
    python neo_genesis_daemon.py --once blog      # 블로그 포스팅 1회
    python neo_genesis_daemon.py --once report    # 일일 리포트 1회
    python neo_genesis_daemon.py --once audit     # 감사만 1회
    python neo_genesis_daemon.py --once farm      # 에어드롭 파밍 1회
    python neo_genesis_daemon.py --once godel     # Gödel 자기개선 1회
    python neo_genesis_daemon.py --status         # 현재 스케줄 상태 출력
"""
import sys
import os
import argparse
import logging
import json
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# ── Windows 콘솔 UTF-8 강제 설정 (cp949 이모지 에러 방지) ──
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 경로 설정 ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
PROFIT_ROOT = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
CORE_ROOT = PROJECT_ROOT / "src" / "core"

# sys.path에 필요한 경로 추가
for p in [str(PROJECT_ROOT), str(PROFIT_ROOT), str(CORE_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# .env 로드 (profit/.env가 모든 키를 가지고 있음)
from dotenv import load_dotenv
load_dotenv(PROFIT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env")  # 루트 .env 보조 로드

# APScheduler 임포트
try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    # APScheduler INFO 로그가 stderr로 나가 종료 코드 1을 유발하므로 WARNING으로 제한
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
except ImportError:
    print("[치명적 오류] APScheduler 미설치. 다음 명령어로 설치하세요:")
    print("  pip install apscheduler")
    sys.exit(1)

# ── 로깅 설정 ─────────────────────────────────────────
LOG_DIR = PROFIT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 로그 로테이션: 10MB × 7개 파일 = 최대 70MB
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOG_DIR / "daemon.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=7,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("neo.daemon")

# ── 텔레그램 헬퍼 (2채널) ────────────────────────────
# 코인/리워드 → 리뷰봇
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# 사업 보고/데몬 → 네오 제네시스 알럿
NEO_ALERT_BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN", "")
NEO_ALERT_CHAT_ID = os.getenv("NEO_ALERT_CHAT_ID", "")

# 채널 매핑: job 이름 → 텔레그램 채널
_CRYPTO_JOBS = {"harvest", "farm", "audit"}


def _tg_send(text: str, channel: str = "auto", job_name: str = "") -> bool:
    """소라 판단 레이어 경유 알림."""
    try:
        from src.core.sora_notify import sora_notify
        urgency = "high" if any(w in text for w in ["실패", "오류", "Error", "CRITICAL"]) else "medium"
        sora_notify(f"daemon_{channel}", {"message": text[:200], "job": job_name}, urgency)
        return True
    except Exception:
        pass
    return False


# 2026-05-06: 사전 NameError bug fix — _JOB_STATS 모듈 정의 누락. _record_result 매 호출마다
# `name '_JOB_STATS' is not defined` 발생 (daemon.log.4/5/6 매 5분 재발). _HEALTH 도 동일.
_JOB_STATS: dict = {}
_HEALTH = None  # placeholder — 실 구현 시 HealthMonitor 인스턴스 주입


def _record_result(job_name: str, success: bool, detail: str = ""):
    """각 Job의 실행 결과를 메모리에 기록"""
    if job_name not in _JOB_STATS:
        _JOB_STATS[job_name] = {
            "total_runs": 0, "success": 0, "fail": 0,
            "last_run": None, "last_success": None, "last_error": None,
        }
    stats = _JOB_STATS[job_name]
    stats["total_runs"] += 1
    stats["last_run"] = datetime.now().isoformat()
    if success:
        stats["success"] += 1
        stats["last_success"] = datetime.now().isoformat()
    else:
        stats["fail"] += 1
        stats["last_error"] = (detail or "")[:200]

    # 헬스 모니터에도 기록 (JSON 영속화)
    if _HEALTH:
        _HEALTH.record(job_name, success, detail)


# ══════════════════════════════════════════════════════
# Job 함수들 — 기존 코드를 임포트하여 안전하게 래핑
# ══════════════════════════════════════════════════════

def job_audit():
    """감사국 정기 감사 (06:00)"""
    logger.info("━━━ 🔍 감사국 정기 감사 시작 ━━━")
    try:
        # 기존 scheduler.py의 run_all_audits 재사용
        sys.path.insert(0, str(PROFIT_ROOT))
        from scheduler import run_all_audits
        run_all_audits()
        _record_result("audit", True)
        logger.info("━━━ 🔍 감사국 정기 감사 완료 ━━━")
    except ImportError:
        logger.warning("[감사] 감사 모듈 미설정 — 스킵")
        _record_result("audit", False, "ImportError")
    except Exception as e:
        logger.error(f"[감사] 실패: {e}", exc_info=True)
        _record_result("audit", False, str(e))


def job_harvest():
    """리워드 수확기 (07:00 + 매 3시간)"""
    logger.info("━━━ 🌾 리워드 수확기 시작 ━━━")
    try:
        # 기존 crypto_scheduler.py의 harvest_rewards 재사용
        sys.path.insert(0, str(PROFIT_ROOT))
        from crypto_scheduler import harvest_rewards
        harvest_rewards()
        _record_result("harvest", True)
        logger.info("━━━ 🌾 리워드 수확기 완료 ━━━")
    except ImportError as e:
        logger.warning(f"[수확] 크롤러 모듈 미설정: {e}")
        _record_result("harvest", False, f"ImportError: {e}")
    except Exception as e:
        logger.error(f"[수확] 실패: {e}", exc_info=True)
        _record_result("harvest", False, str(e))
        _tg_send(f"⚠️ <b>리워드 수확기 실패</b>\n{str(e)[:200]}")


def job_blog(tenant_id: str = "reviewlab"):
    """블로그 자동 포스팅 (08:00, 14:00)"""
    logger.info(f"━━━ 📝 블로그 포스팅 시작 ({tenant_id}) ━━━")
    try:
        sys.path.insert(0, str(PROFIT_ROOT))
        from apc_engine.pipeline import APCEngine
        engine = APCEngine(tenant_id, base_dir=PROFIT_ROOT)
        engine.run()
        _record_result("blog", True)
        logger.info(f"━━━ 📝 블로그 포스팅 완료 ({tenant_id}) ━━━")
    except ImportError as e:
        logger.error(f"[블로그] APC 엔진 임포트 실패: {e}")
        _record_result("blog", False, f"ImportError: {e}")
    except Exception as e:
        logger.error(f"[블로그] 실패: {e}", exc_info=True)
        _record_result("blog", False, str(e))
        _tg_send(f"⚠️ <b>블로그 포스팅 실패</b>\n테넌트: {tenant_id}\n{str(e)[:200]}")


def job_farm():
    """에어드롭 파밍 (18:00)"""
    logger.info("━━━ 🎁 에어드롭 파밍 시작 ━━━")
    try:
        sys.path.insert(0, str(PROFIT_ROOT))
        from crypto_scheduler import farm_airdrops
        farm_airdrops()
        _record_result("farm", True)
        logger.info("━━━ 🎁 에어드롭 파밍 완료 ━━━")
    except ImportError:
        logger.warning("[파밍] 에어드롭 파머 미설정 — 스킵")
        _record_result("farm", False, "ImportError")
    except Exception as e:
        logger.error(f"[파밍] 실패: {e}", exc_info=True)
        _record_result("farm", False, str(e))


def job_daily_report():
    """일일 종합 리포트 (22:00)"""
    logger.info("━━━ 📊 일일 종합 리포트 생성 ━━━")
    try:
        report_lines = [
            f"📊 <b>#NEO_GENESIS 일일 리포트</b>",
            f"📅 {datetime.now().strftime('%Y-%m-%d (%a)')}",
            "",
        ]

        # 1. 블로그 현황
        blog_content_dir = PROJECT_ROOT / "src" / "sbu" / "toolpick" / "content"
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_posts = 0
        total_posts = 0
        if blog_content_dir.exists():
            for f in blog_content_dir.rglob("*.mdx"):
                total_posts += 1
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if today_str in content[:200]:
                        today_posts += 1
                except Exception:
                    pass
            for f in blog_content_dir.rglob("*.md"):
                total_posts += 1

        report_lines.append("💰 <b>수익센터</b>")
        report_lines.append(f"  📝 블로그: 오늘 {today_posts}건 / 총 {total_posts}건")

        # 2. 크립토 이벤트 현황
        try:
            sys.path.insert(0, str(PROFIT_ROOT / "shared"))
            from database import get_db
            db = get_db()
            stats = db.get_event_stats()
            total_events = sum(s.get("total", 0) for s in stats)
            total_value = sum(s.get("total_value", 0) or 0 for s in stats)
            report_lines.append(f"  🌐 리워드: {total_events}건 (추정 ~${total_value:.0f})")
        except Exception as e:
            report_lines.append(f"  🌐 리워드: 데이터 조회 실패")
            logger.warning(f"[리포트] DB 조회 실패: {e}")

        # 3. Job 실행 통계
        report_lines.append("")
        report_lines.append("⚙️ <b>데몬 상태</b>")
        for name, stats in _JOB_STATS.items():
            icon = "✅" if stats["fail"] == 0 else "⚠️"
            report_lines.append(
                f"  {icon} {name}: {stats['success']}/{stats['total_runs']} 성공"
            )
            if stats["last_error"]:
                report_lines.append(f"     └─ 마지막 에러: {stats['last_error'][:80]}")

        # 4. 헬스 모니터 상태 (영속화된 데이터)
        if _HEALTH:
            health_warnings = _HEALTH.check_health()
            if health_warnings:
                report_lines.append("")
                report_lines.append("🏥 <b>헬스 경고</b>")
                report_lines.extend(health_warnings)

        # 5. 에러가 있으면 경고
        total_errors = sum(s.get("fail", 0) for s in _JOB_STATS.values())
        if total_errors > 0:
            report_lines.append("")
            report_lines.append(f"⚠️ 오늘 총 {total_errors}건의 에러가 발생했습니다.")

        report = "\n".join(report_lines)
        logger.info(f"\n{report}")
        _tg_send(report)
        _record_result("report", True)
        logger.info("━━━ 📊 일일 종합 리포트 발송 완료 ━━━")

    except Exception as e:
        logger.error(f"[리포트] 실패: {e}", exc_info=True)
        _record_result("report", False, str(e))


def job_godel():
    """Gödel 자기개선 사이클 — SBU별 다중 타겟 (매주 일요일 04:00)"""
    logger.info("━━━ ♾️ Gödel 자기개선 사이클 시작 ━━━")

    # SBU별 스캔 대상 (우선순위 순)
    targets = [
        ("core", "src/core"),
        ("toolpick", "src/sbu/toolpick/src"),
        ("toolpick_content", "src/sbu/toolpick/content"),
        ("ur_wrong", "src/sbu/ur-wrong"),
    ]

    total_found = 0
    total_fixed = 0
    results_summary = []

    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.core.godel_agent import GodelAgent
        agent = GodelAgent()

        for sbu_name, target_dir in targets:
            target_path = PROJECT_ROOT / target_dir
            if not target_path.exists():
                logger.info(f"[Gödel] {sbu_name} 스킵 (경로 없음: {target_dir})")
                continue

            try:
                result = agent.improvement_cycle(target_dir)
                total_found += result.issues_found
                total_fixed += result.issues_fixed
                results_summary.append(
                    f"  • {sbu_name}: {result.issues_found}발견/{result.issues_fixed}수정"
                )
                logger.info(f"[Gödel] {sbu_name}: {result.summary}")
            except Exception as e:
                results_summary.append(f"  • {sbu_name}: 실패 ({str(e)[:50]})")
                logger.warning(f"[Gödel] {sbu_name} 실패: {e}")

        summary = (
            f"♾️ <b>Gödel 자기개선 완료</b>\n"
            f"대상: {len(targets)} SBU\n"
            f"발견: {total_found}개 | 수정: {total_fixed}개\n"
            + "\n".join(results_summary)
        )
        logger.info(summary)
        _tg_send(summary)
        _record_result("godel", total_fixed > 0 or total_found == 0)
        logger.info("━━━ ♾️ Gödel 자기개선 사이클 완료 ━━━")

    except ImportError as e:
        logger.warning(f"[Gödel] 모듈 임포트 실패: {e}")
        _record_result("godel", False, f"ImportError: {e}")
    except Exception as e:
        logger.error(f"[Gödel] 실패: {e}", exc_info=True)
        _record_result("godel", False, str(e))
        _tg_send(f"⚠️ <b>Gödel 자기개선 실패</b>\n{str(e)[:200]}")



# ══════════════════════════════════════════════════════
# APScheduler 이벤트 리스너
# ══════════════════════════════════════════════════════

def _job_listener(event):
    """Job 실행/에러 이벤트 리스너"""
    if event.exception:
        logger.error(f"[스케줄러] Job 실패: {event.job_id} — {event.exception}")
    else:
        logger.debug(f"[스케줄러] Job 완료: {event.job_id}")


# ── HIVE MIND (UR WRONG 에이전트 시스템) ────────────────────

# Vercel 크론 API 호출용 환경변수
_VERCEL_CRON_URL = os.getenv("VERCEL_CRON_URL", "")
_CRON_SECRET = os.getenv("CRON_SECRET", "")

# ── ToolPick HIVE MIND ────────────────────────────────────
_TOOLPICK_HIVE_URL = os.getenv("TOOLPICK_HIVE_URL", "")
_TOOLPICK_CRON_SECRET = os.getenv("TOOLPICK_CRON_SECRET", _CRON_SECRET)


def _call_vercel_cron(job_name: str, **params) -> dict:
    """Vercel 호스팅된 UR WRONG 크론 API 호출"""
    import urllib.request
    import urllib.parse
    import json as _json

    if not _VERCEL_CRON_URL:
        raise RuntimeError("VERCEL_CRON_URL 환경변수 미설정")

    query = urllib.parse.urlencode({"job": job_name, **params})
    url = f"{_VERCEL_CRON_URL}?{query}"
    req = urllib.request.Request(url)
    if _CRON_SECRET:
        req.add_header("Authorization", f"Bearer {_CRON_SECRET}")
    req.add_header("User-Agent", "NeoGenesisDaemon/1.0")

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = _json.loads(resp.read().decode("utf-8"))
        return body


def job_hive_cron():
    """UR WRONG 크론 작업 순차 실행 (09:00, 15:00, 21:00)"""
    logger.info("━━━ 🔥 UR WRONG 크론 작업 시작 ━━━")
    results = {}
    jobs = ["generate", "fuel-patrol", "social", "reddit"]
    for job in jobs:
        try:
            result = _call_vercel_cron(job)
            results[job] = result
            logger.info(f"  ✔ {job}: {result}")
        except Exception as e:
            results[job] = {"error": str(e)}
            logger.warning(f"  ✖ {job}: {e}")

    ok_count = sum(1 for r in results.values() if "error" not in r)
    _record_result("hive_cron", ok_count > 0, "" if ok_count > 0 else str(results))
    logger.info(f"━━━ 🔥 UR WRONG 크론 완료 ({ok_count}/{len(jobs)} 성공) ━━━")
    if ok_count == 0:
        _tg_send(f"⚠️ <b>UR WRONG 크론 전체 실패</b>\n{str(results)[:300]}")
    return results


def job_hive_orchestrator():
    """HIVE MIND 오케스트레이터 실행 (매일 10:00, 16:00)"""
    logger.info("━━━ 🧠 HIVE MIND 오케스트레이터 시작 ━━━")
    try:
        import urllib.request
        import json as _json

        # HIVE MIND 오케스트레이터 엔드포인트 호출
        base_url = os.getenv("VERCEL_HIVE_URL", _VERCEL_CRON_URL.replace("/api/cron/index", "/api/agents/index") if _VERCEL_CRON_URL else "")
        if not base_url:
            raise RuntimeError("VERCEL_HIVE_URL 환경변수 미설정")

        req = urllib.request.Request(base_url, method="POST")
        req.add_header("Content-Type", "application/json")
        if _CRON_SECRET:
            req.add_header("Authorization", f"Bearer {_CRON_SECRET}")
        req.add_header("User-Agent", "NeoGenesisDaemon/1.0")

        # 오케스트레이터 실행 요청
        data = _json.dumps({"action": "orchestrate"}).encode("utf-8")
        with urllib.request.urlopen(req, data=data, timeout=180) as resp:
            result = _json.loads(resp.read().decode("utf-8"))

        _record_result("hive_orchestrator", True)
        logger.info(f"━━━ 🧠 HIVE MIND 오케스트레이터 완료: {result} ━━━")
        return result
    except Exception as e:
        logger.error(f"[하이브] 오케스트레이터 실패: {e}", exc_info=True)
        _record_result("hive_orchestrator", False, str(e))
        _tg_send(f"⚠️ <b>HIVE MIND 오케스트레이터 실패</b>\n{str(e)[:200]}")


def job_toolpick_hive():
    """ToolPick HIVE MIND 오케스트레이션 (08:30, 14:30, 20:30)"""
    logger.info("━━━ 🐝 ToolPick HIVE MIND 시작 ━━━")
    try:
        import urllib.request
        import json as _json

        base_url = _TOOLPICK_HIVE_URL
        if not base_url:
            raise RuntimeError("TOOLPICK_HIVE_URL 환경변수 미설정")

        req = urllib.request.Request(base_url, method="POST")
        req.add_header("Content-Type", "application/json")
        if _TOOLPICK_CRON_SECRET:
            req.add_header("Authorization", f"Bearer {_TOOLPICK_CRON_SECRET}")
        req.add_header("User-Agent", "NeoGenesisDaemon/1.0")

        data = _json.dumps({"action": "orchestration_cycle"}).encode("utf-8")
        with urllib.request.urlopen(req, data=data, timeout=180) as resp:
            result = _json.loads(resp.read().decode("utf-8"))

        _record_result("toolpick_hive", True)
        logger.info(f"━━━ 🐝 ToolPick HIVE MIND 완료: {result} ━━━")
        _tg_send(
            f"🐝 <b>ToolPick HIVE MIND 사이클 완료</b>\n"
            f"{_json.dumps(result, ensure_ascii=False)[:300]}"
        )
        return result
    except Exception as e:
        logger.error(f"[ToolPick] HIVE MIND 실패: {e}", exc_info=True)
        _record_result("toolpick_hive", False, str(e))
        _tg_send(f"⚠️ <b>ToolPick HIVE MIND 실패</b>\n{str(e)[:200]}")


def job_cross_sbu_sync():
    """SBU 간 크로스 데이터 동기화 (매 6시간)"""
    logger.info("━━━ 🔗 SBU 크로스 동기화 시작 ━━━")
    try:
        sync_results = {}

        # 1. 각 SBU 건강 상태 수집
        health = {}
        for name in ["hive_cron", "blog", "harvest", "farm", "toolpick_hive"]:
            stats = _JOB_STATS.get(name, {})
            health[name] = {
                "runs": stats.get("total_runs", 0),
                "success": stats.get("success", 0),
                "last_run": stats.get("last_run"),
            }
        sync_results["health"] = health

        # 2. 헬스 모니터에 기록
        if _HEALTH:
            _HEALTH.record("cross_sbu_sync", True, str(health))

        _record_result("cross_sbu_sync", True)
        logger.info(f"━━━ 🔗 SBU 크로스 동기화 완료 ━━━")
        return sync_results
    except Exception as e:
        logger.error(f"[동기화] 실패: {e}", exc_info=True)
        _record_result("cross_sbu_sync", False, str(e))


def job_morning_report():
    """업무 개시 보고 (08:50) — 각 SBU별 오늘 스케줄 + 어제 실적"""
    logger.info("━━━ 🏢 업무 개시 보고 ━━━")
    now = datetime.now()
    lines = [
        f"🏢 <b>NEO GENESIS 업무 개시 보고</b>",
        f"📅 {now.strftime('%Y-%m-%d (%a)')} {now.strftime('%H:%M')}",
        "",
        "<b>📋 오늘의 스케줄</b>",
        "  📝 ReviewLab — 08:00, 14:00 자동 포스팅",
        "  🐝 ToolPick  — 08:30, 14:30, 20:30 HIVE MIND",
        "  🔥 UR WRONG  — 09:00, 15:00, 21:00 배틀 생성",
        "  🧠 HIVE MIND — 10:00, 16:00 오케스트레이션",
        "  🌾 리워드     — 07:00 + 매 3시간",
        "  🎁 에어드롭   — 18:00",
        "  📊 종합리포트 — 22:00",
        "  🥊 UR WRONG 바이럴 — 20:00",
        "",
    ]

    # 어제 실적 요약
    lines.append("<b>📊 어제 실적 요약</b>")
    for name, stats in _JOB_STATS.items():
        icon = "✅" if stats.get("fail", 0) == 0 else "⚠️"
        lines.append(
            f"  {icon} {name}: {stats.get('success', 0)}/{stats.get('total_runs', 0)} 성공"
        )

    # 환경 상태 체크
    lines.append("")
    lines.append("<b>🔧 환경 상태</b>")
    checks = {
        "Gemini API": bool(os.getenv("GEMINI_API_KEY")),
        "Vercel 토큰": bool(os.getenv("VERCEL_TOKEN")),
        "UR WRONG 크론": bool(os.getenv("VERCEL_CRON_URL")),
        "ToolPick HIVE": bool(os.getenv("TOOLPICK_HIVE_URL")),
        "텔레그램": bool(TELEGRAM_BOT_TOKEN),
    }
    for k, v in checks.items():
        lines.append(f"  {'✅' if v else '❌'} {k}")

    lines.append("")
    lines.append("🚀 <b>전 계열사 업무 개시합니다.</b>")

    report = "\n".join(lines)
    logger.info(f"\n{report}")
    _tg_send(report)
    _record_result("morning_report", True)


def job_evening_report():
    """업무 종료 보고 (17:50) — 오늘 실적 + 에러 요약"""
    logger.info("━━━ 🏢 업무 종료 보고 ━━━")
    now = datetime.now()
    lines = [
        f"🏢 <b>NEO GENESIS 업무 종료 보고</b>",
        f"📅 {now.strftime('%Y-%m-%d (%a)')} {now.strftime('%H:%M')}",
        "",
    ]

    # SBU별 오늘 실적
    sbu_groups = {
        "📝 ReviewLab": ["blog"],
        "🐝 ToolPick": ["toolpick_hive"],
        "🔥 UR WRONG": ["hive_cron", "hive_orchestrator"],
        "🌾 리워드": ["harvest"],
        "🎁 에어드롭": ["farm"],
    }

    lines.append("<b>📊 오늘 실적</b>")
    total_success = 0
    total_fail = 0
    for sbu_name, job_keys in sbu_groups.items():
        sbu_success = sum(_JOB_STATS.get(k, {}).get("success", 0) for k in job_keys)
        sbu_fail = sum(_JOB_STATS.get(k, {}).get("fail", 0) for k in job_keys)
        sbu_total = sbu_success + sbu_fail
        total_success += sbu_success
        total_fail += sbu_fail
        icon = "✅" if sbu_fail == 0 and sbu_total > 0 else "⚠️" if sbu_fail > 0 else "⏸️"
        lines.append(f"  {icon} {sbu_name}: {sbu_success}/{sbu_total} 성공")

        # 에러가 있으면 표시
        for k in job_keys:
            last_err = _JOB_STATS.get(k, {}).get("last_error")
            if last_err:
                lines.append(f"     └─ {last_err[:60]}")

    lines.append("")
    if total_fail == 0 and total_success > 0:
        lines.append("🎉 <b>모든 작업이 정상 완료되었습니다.</b>")
    elif total_fail > 0:
        lines.append(f"⚠️ <b>총 {total_fail}건의 실패가 발생했습니다.</b>")
    else:
        lines.append("⏸️ <b>오늘 실행된 작업이 없습니다.</b>")

    lines.append("")
    lines.append("🌙 <b>야간 자동 운영으로 전환합니다.</b>")
    lines.append("  21:00 UR WRONG 크론 | 22:00 종합 리포트")

    report = "\n".join(lines)
    logger.info(f"\n{report}")
    _tg_send(report)
    _record_result("evening_report", True)


# ══════════════════════════════════════════════════════
# 메인 클래스
# ══════════════════════════════════════════════════════

class NeoGenesisDaemon:
    """NEO GENESIS 통합 데몬"""

    def sync_bible(self):
        """BIBLE 환경 동기화 (데몬 시작 + 매 6시간).

        2026-05-04 정정 (owner 알림 spam 정리):
        - 정상 완료 시 텔레그램 발송 안 함 (실패 시만 alert)
        - 직전 "warnings or actions_taken" 조건도 owner 입장에서는 자동 정상 동작이라 무가치
        """
        logger.info("━━━ 📖 BIBLE 환경 동기화 시작 ━━━")
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from src.core.bible_loader import BibleLoader
            loader = BibleLoader()
            result = loader.boot()
            _record_result("bible_sync", result.ok, result.summary())
            # owner 알림은 실패 시만 (정상 완료는 logger 만)
            logger.info(f"━━━ 📖 BIBLE 환경 동기화 완료 ━━━")
        except Exception as e:
            logger.error(f"[BIBLE] 동기화 실패: {e}", exc_info=True)
            _record_result("bible_sync", False, str(e))
            _tg_send(f"⚠️ <b>BIBLE 동기화 실패</b>\n{str(e)[:200]}")

    def job_weekly_traffic(self):
        """주간 트래픽 리뷰 (일요일 10:00)"""
        logger.info("━━━ 📈 주간 트래픽 리뷰 생성 ━━━")
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from scripts.traffic_alert import generate_traffic_report
            report = generate_traffic_report()
            logger.info(f"\n{report}")
            _tg_send(report, channel="business")
            _record_result("weekly_traffic", True)
            logger.info("━━━ 📈 주간 트래픽 리뷰 발송 완료 ━━━")
        except Exception as e:
            logger.error(f"[트래픽] 실패: {e}", exc_info=True)
            _record_result("weekly_traffic", False, str(e))
            _tg_send(f"⚠️ <b>주간 트래픽 리뷰 실패</b>\n{str(e)[:200]}")

    def job_ur_wrong_viral(self):
        """UR WRONG 바이럴 소셜 배포 초안 알림"""
        logger.info("━━━ 🥊 UR WRONG 바이럴 초안 생성 ━━━")
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from scripts.ur_wrong_viral_alert import run_viral_alert
            run_viral_alert()
            logger.info("━━━ 🥊 UR WRONG 바이럴 초안 발송 완료 ━━━")
            _record_result("ur_wrong_viral", True)
        except Exception as e:
            logger.error(f"UR WRONG 바이럴 알림 실패: {e}", exc_info=True)
            _record_result("ur_wrong_viral", False, str(e))
            _tg_send(f"⚠️ <b>UR WRONG 바이럴 알림 실패</b>\n{str(e)[:200]}")

    def __init__(self):
        self.scheduler = BlockingScheduler(timezone="Asia/Seoul")
        self.scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

        # Job 매핑 (--once 옵션용) — 인스턴스 메서드 참조는 __init__ 내부에서만 가능
        self.JOB_MAP = {
            "audit": job_audit,
            "harvest": job_harvest,
            "blog": job_blog,
            "farm": job_farm,
            "report": job_daily_report,
            "godel": job_godel,
            "hive_cron": job_hive_cron,
            "hive_orchestrator": job_hive_orchestrator,
            "toolpick_hive": job_toolpick_hive,
            "cross_sync": job_cross_sbu_sync,
            "morning_report": job_morning_report,
            "evening_report": job_evening_report,
            "bible_sync": self.sync_bible,
            "weekly_traffic": self.job_weekly_traffic,
            "ur_wrong_viral": self.job_ur_wrong_viral,
        }

        self._register_jobs()

    def _register_jobs(self):
        """모든 스케줄 작업 등록"""

        # ── 06:00 감사국 정기 감사 ──
        self.scheduler.add_job(
            job_audit, "cron", hour=6, minute=0,
            id="audit", name="🔍 감사국 정기 감사",
            misfire_grace_time=600,
        )

        # ── [CLOUD] 리워드 수확 — Vercel profit/api/sbu/dispatch (10분 주기) ──
        # 로컬 시스템 부하 최소화: Vercel+Supabase 기반 자동화로 이관
        # self.scheduler.add_job(
        #     job_harvest, "cron", hour=7, minute=0,
        #     id="harvest_fixed", name="🌾 리워드 수확기 (고정 07시)",
        #     misfire_grace_time=600,
        # )
        # self.scheduler.add_job(
        #     job_harvest, "interval", hours=1, jitter=300,
        #     id="harvest_interval", name="🌾 리워드 수확기 (1시간 주기)",
        #     misfire_grace_time=600,
        # )

        # ── [CLOUD] 블로그 포스팅 — Vercel profit/api/sbu/orchestrate (매시) ──
        # self.scheduler.add_job(
        #     job_blog, "interval", hours=1, jitter=300,
        #     id="blog_hourly", name="📝 블로그 포스팅 (1시간 주기)",
        #     misfire_grace_time=600,
        # )

        # ── 매 3시간 에어드롭 파밍 ──
        self.scheduler.add_job(
            job_farm, "interval", hours=3, jitter=1800,
            id="farm", name="🎁 에어드롭 파밍",
            misfire_grace_time=3600,
        )

        # [daily_report] 제거됨: 22:00 일일 종합 리포트 → evening_report(17:50)와 중복

        # [weekly_traffic] 제거됨: 주간 트래픽 리뷰 → 스크립트 없음, Vercel Analytics로 대체

        # [ur_wrong_viral] 제거됨: UR WRONG 바이럴 → 스크립트 없음

        # ── 매주 일요일 04:00 Gödel 자기개선 ──
        self.scheduler.add_job(
            job_godel, "cron", day_of_week="sun", hour=4, minute=0,
            id="godel", name="♾️ Gödel 자기개선",
            misfire_grace_time=3600,
        )

        # ── [CLOUD] UR WRONG 크론 — Vercel Cron 자체 실행 (이중 호출 제거) ──
        # vercel.json: generate(18h), social(10/22h), reddit(14h),
        # blog(6h), fuel-patrol(2/12/20h), agents(0/8/16h), feedback(4h)
        # self.scheduler.add_job(
        #     job_hive_cron, "cron", hour="9,15,21", minute=0,
        #     id="hive_cron", name="🔥 UR WRONG 크론",
        #     misfire_grace_time=1800,
        # )

        # ── [CLOUD] HIVE MIND 오케스트레이터 — Vercel Cron 자체 실행 ──
        # vercel.json: agents?role=orchestrator (0/8/16h)
        # self.scheduler.add_job(
        #     job_hive_orchestrator, "cron", hour="10,16", minute=0,
        #     id="hive_orchestrator", name="🧠 HIVE MIND 오케스트레이터",
        #     misfire_grace_time=1800,
        # )

        # ── [CLOUD] ToolPick HIVE MIND — Vercel Cron 자체 실행 ──
        # vercel.json: hive-mind/orchestrate (*/30분 주기)
        # self.scheduler.add_job(
        #     job_toolpick_hive, "cron", hour="8,14,20", minute=30,
        #     id="toolpick_hive", name="🐝 ToolPick HIVE MIND",
        #     misfire_grace_time=1800,
        # )

        # [cross_sbu_sync] 제거됨: SBU 크로스 동기화 → 메모리 통계만, 영속화 없음

        # ── 08:50 업무 개시 보고 ──
        self.scheduler.add_job(
            job_morning_report, "cron", hour=8, minute=50,
            id="morning_report", name="🏢 업무 개시 보고",
            misfire_grace_time=600,
        )

        # ── 17:50 업무 종료 보고 ──
        self.scheduler.add_job(
            job_evening_report, "cron", hour=17, minute=50,
            id="evening_report", name="🏢 업무 종료 보고",
            misfire_grace_time=600,
        )

        # ── 매 6시간 BIBLE 환경 동기화 (Phase -1) ──
        self.scheduler.add_job(
            self.sync_bible, "interval", hours=6,
            id="bible_sync", name="📖 BIBLE 환경 동기화",
            misfire_grace_time=3600,
        )

        # ── 🔱 God Mode: SelfHealer 주기적 헬스체크 (5분) ──
        try:
            from src.core.healer import SelfHealer
            _healer = SelfHealer()
            import asyncio
            def _healer_check():
                try:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_healer.periodic_check())
                    loop.close()
                except Exception as e:
                    logger.warning(f"[Healer] periodic_check 실패: {e}")
            self.scheduler.add_job(
                _healer_check, "interval", minutes=5,
                id="healer_check", name="🏥 SelfHealer 헬스체크",
                misfire_grace_time=120,
            )
            logger.info("🏥 SelfHealer 헬스체크 등록 (5분 주기)")
        except Exception as e:
            logger.warning(f"[Healer] 스케줄 등록 실패: {e}")

        # ── 🔱 God Mode: ProactiveAgent 이상징후 탐지 (15분) ──
        try:
            from src.core.proactive_agent import get_proactive_agent
            _proactive = get_proactive_agent()
            def _anomaly_check():
                try:
                    _proactive.check_anomalies()
                except Exception as e:
                    logger.warning(f"[Proactive] anomaly_check 실패: {e}")
            self.scheduler.add_job(
                _anomaly_check, "interval", minutes=15,
                id="anomaly_check", name="⚠️ ProactiveAgent 이상감지",
                misfire_grace_time=120,
            )
            logger.info("⚠️ ProactiveAgent 이상감지 등록 (15분 주기)")
        except Exception as e:
            logger.warning(f"[Proactive] 스케줄 등록 실패: {e}")

    def start(self):
        """데몬 시작 — God Mode 자율 루프 포함"""
        logger.info("=" * 60)
        logger.info("🏛️ NEO GENESIS 통합 데몬 시작")
        logger.info(f"   프로젝트 루트: {PROJECT_ROOT}")
        logger.info(f"   수익센터 루트: {PROFIT_ROOT}")
        logger.info(f"   텔레그램: {'✅ 설정됨' if NEO_ALERT_BOT_TOKEN else '❌ 미설정'}")

        # ── J.A.R.V.I.S. AI 비서 자동 기동 ──
        # 2026-05-03 정정 (owner 1인 운영 정책):
        # 직전엔 "Gateway webhook으로 통합" 가정으로 polling 비활성화했으나, 실제로는
        # webhook URL이 등록되지 않아 telegram → sora-live 메시지 경로가 4/26부터 단절됨.
        # 4/30~5/1 owner 가 "보라색 기억해" / "거래소 비밀번호" 메시지를 3번 재전송한 것이
        # 응답 안 도착 증거. 1인 owner-only 운영 = sora-live 1대만 polling 하면 409 Conflict 없음.
        # SORA_TELEGRAM_POLLING=0 환경변수로 owner override 가능 (CONSTITUTION Article 0).
        _telegram_polling_enabled = os.getenv("SORA_TELEGRAM_POLLING", "1").lower() in ("1", "true", "yes")
        if _telegram_polling_enabled and NEO_ALERT_BOT_TOKEN:
            # NeoAssistant.run() 은 PTB 20 의 app.run_polling() 호출. main thread 의 signal handler
            # (set_wakeup_fd) 를 요구하므로 daemon thread 안에서는 동작 불가.
            # 별도 subprocess 로 띄워서 main thread 보장 + 부모 daemon crash 시 supervisord 가
            # daemon 만 재시작 → 다음 boot 에서 자식 polling 도 재기동.
            try:
                import subprocess as _sp
                _polling_log = "/app/data/logs/sora_telegram_poll.log"

                def _spawn_polling_subprocess():
                    return _sp.Popen(
                        [sys.executable, "-c",
                         "from src.core.neo_assistant_bot import NeoAssistant; NeoAssistant().run()"],
                        cwd=str(PROJECT_ROOT),
                        stdout=open(_polling_log, "ab", buffering=0),
                        stderr=_sp.STDOUT,
                        start_new_session=True,
                    )

                _polling_proc = _spawn_polling_subprocess()
                logger.info(f"📨 NeoAssistantBot polling subprocess 기동 (pid={_polling_proc.pid}, log={_polling_log})")

                # 2026-05-04 F2: polling subprocess 가 단독으로 die 시 daemon 이 자동 re-spawn
                # 직전엔 daemon 이 한 번만 띄우고 monitor 안 함 → polling 죽어도 sora 텔레그램 단절.
                # supervisord 는 daemon 만 관리 (polling subprocess 는 daemon 의 자식).
                import threading as _th
                import time as _time
                _polling_supervisor_max_respawn = 10
                _polling_supervisor_respawn_count = 0

                def _polling_supervisor():
                    nonlocal _polling_proc, _polling_supervisor_respawn_count
                    while True:
                        _time.sleep(30)
                        try:
                            rc = _polling_proc.poll()
                            if rc is not None:
                                _polling_supervisor_respawn_count += 1
                                if _polling_supervisor_respawn_count > _polling_supervisor_max_respawn:
                                    logger.error(f"[TelegramBot] supervisor: respawn 한도 {_polling_supervisor_max_respawn} 초과 — 정지")
                                    _tg_send(f"🚨 <b>NeoAssistant polling supervisor 정지</b>\nrespawn {_polling_supervisor_respawn_count}회 초과 — owner 수동 점검 필요")
                                    return
                                logger.warning(f"[TelegramBot] supervisor: polling subprocess 종료 (rc={rc}). re-spawn ({_polling_supervisor_respawn_count}회)")
                                _polling_proc = _spawn_polling_subprocess()
                                logger.info(f"[TelegramBot] supervisor: 새 polling pid={_polling_proc.pid}")
                        except Exception as _sup_exc:
                            logger.warning(f"[TelegramBot] supervisor 예외: {_sup_exc}")

                _th.Thread(target=_polling_supervisor, daemon=True, name="sora-telegram-polling-supervisor").start()
                logger.info("👁️  NeoAssistant polling supervisor — 30s polling, max 10 respawn")
            except Exception as exc:
                logger.warning(f"[TelegramBot] subprocess 기동 실패: {exc}")
        else:
            _reason = "env SORA_TELEGRAM_POLLING=0" if not _telegram_polling_enabled else "NEO_ALERT_BOT_TOKEN 미설정"
            logger.info(f"📨 NeoAssistantBot polling 비활성: {_reason}")

        # ── 🔱 AutonomousLoop (소라의 심장) 기동 ──
        try:
            import threading
            import asyncio
            def _boot_autonomous():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    from src.core.autonomous.loop import AutonomousLoop
                    auto_loop = AutonomousLoop()
                    loop.run_until_complete(auto_loop.start())
                except Exception as e:
                    logger.warning(f"[AutonomousLoop] 기동 실패: {e}")
            t = threading.Thread(target=_boot_autonomous, daemon=True)
            t.start()
            logger.info("🔱 AutonomousLoop (소라의 심장) — 백그라운드 기동")
        except Exception as e:
            logger.warning(f"[AutonomousLoop] 스레드 시작 실패: {e}")

        logger.info("=" * 60)

        # 스케줄 출력
        for job in self.scheduler.get_jobs():
            next_run = getattr(job, "next_run_time", None)
            logger.info(f"  📌 {job.name} → 다음 실행: {next_run}")

        # 텔레그램 시작 알림 — 2026-05-04 정정 (owner spam 감축):
        # 정상 부팅 (uptime 1분 미만) 은 logger 만, alert 안 보냄.
        # crash recovery (직전 비정상 종료 후 부팅) 또는 환경변수 SORA_FORCE_BOOT_ALERT=1 시만 alert.
        # owner 가 sora-live 재시작/배포 1회 = telegram 1건 받던 spam 차단.
        job_count = len(self.scheduler.get_jobs())
        _force_boot_alert = os.getenv("SORA_FORCE_BOOT_ALERT", "").lower() in ("1", "true", "yes")
        # crash 검출: 직전 종료 직후 빠른 재부팅 = supervisord autorestart trigger 가설
        _crash_marker = Path("/tmp/sora_crash_detected")
        _is_crash_recovery = _crash_marker.exists()
        if _is_crash_recovery:
            try: _crash_marker.unlink()
            except Exception: pass
        if _force_boot_alert or _is_crash_recovery:
            tag = "🚨 crash recovery" if _is_crash_recovery else "🏛️ 데몬 시작"
            _tg_send(
                f"{tag} <b>NEO GENESIS — God Mode</b>\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"⚙️ {job_count}개 작업 등록됨"
            )
        else:
            logger.info(f"[Daemon] 정상 부팅 — telegram alert skip ({job_count} jobs ready)")

        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("🛑 데몬 종료 (Ctrl+C)")
            
        # 시작 알림 비활성화됨

            self.scheduler.shutdown()

    def run_once(self, job_name: str):
        """단일 작업 즉시 실행"""
        func = self.JOB_MAP.get(job_name)
        if not func:
            print(f"[오류] 알 수 없는 작업: {job_name}")
            print(f"[사용 가능] {', '.join(self.JOB_MAP.keys())}")
            return

        logger.info(f"🔧 단일 실행 모드: {job_name}")
        func()
        logger.info(f"🔧 단일 실행 완료: {job_name}")

    def print_status(self):
        """현재 스케줄 상태 출력"""
        print("\n🏛️ NEO GENESIS 데몬 — God Mode 스케줄 현황\n")
        print(f"  프로젝트: {PROJECT_ROOT}")
        print(f"  NEO Alert 봇: {'✅' if NEO_ALERT_BOT_TOKEN else '❌'}")
        print(f"  Gemini API: {'✅' if os.getenv('GEMINI_API_KEY') else '❌'}")
        print()

        jobs_info = [
            ("🔍 감사국", "06:00", "매일"),
            ("🎁 에어드롭", "매 3시간", "매일"),
            ("📊 리포트", "22:00", "매일"),
            ("♾️ Gödel", "04:00", "매주 일요일"),
            ("🔗 SBU동기화", "매 6시간", "매일"),
            ("🏢 조간보고", "08:50", "매일"),
            ("🏢 석간보고", "17:50", "매일"),
            ("📖 BIBLE", "매 6시간", "매일"),
            ("🏥 Healer", "매 5분", "상시"),
            ("⚠️ Anomaly", "매 15분", "상시"),
        ]

        print("  ┌──────────────┬──────────────────┬────────────┐")
        print("  │ 작업          │ 시각              │ 주기        │")
        print("  ├──────────────┼──────────────────┼────────────┤")
        for name, time_, cycle in jobs_info:
            print(f"  │ {name:<12} │ {time_:<16} │ {cycle:<10} │")
        print("  └──────────────┴──────────────────┴────────────┘")
        print()
        print("  [CLOUD] 블로그/리워드 → Vercel Cron 이관")
        print("  [CLOUD] UR WRONG → Vercel Cron 이관")
        print("  [GOD]   AutonomousLoop → 데몬 시작 시 자동 기동")
        print()


# ── 의존성 체크 ───────────────────────────────────────
def check_dependencies() -> bool:
    """핵심 의존성 패키지 확인"""
    required = ["apscheduler", "dotenv", "requests", "schedule"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[경고] 누락된 패키지: {', '.join(missing)}")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True


# ══════════════════════════════════════════════════════
# 엔트리포인트
# ══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🏛️ NEO GENESIS 통합 데몬 — 계열사 완전 자율 운영",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python neo_genesis_daemon.py                  # 데몬 시작 (상시 실행)
  python neo_genesis_daemon.py --once harvest   # 리워드 수확 1회
  python neo_genesis_daemon.py --once blog      # 블로그 포스팅 1회
  python neo_genesis_daemon.py --once report    # 일일 리포트 1회
  python neo_genesis_daemon.py --status         # 스케줄 현황
        """,
    )
    parser.add_argument(
        "--once",
        choices=["audit", "harvest", "blog", "farm", "report", "godel",
                 "hive_cron", "hive_orchestrator", "toolpick_hive", "cross_sync",
                 "morning_report", "evening_report", "bible_sync", "weekly_traffic", "ur_wrong_viral"],
        help="지정 작업을 1회 즉시 실행 후 종료",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="현재 스케줄 설정 출력",
    )
    args = parser.parse_args()

    # 의존성 체크
    check_dependencies()

    daemon = NeoGenesisDaemon()

    if args.status:
        daemon.print_status()
    elif args.once:
        daemon.run_once(args.once)
    else:
        import signal as _sig, os as _os, time as _time

        def _on_sigterm(signum, frame):
            try:
                import urllib.request
                tok = _os.getenv("NEO_ALERT_BOT_TOKEN", "")
                if tok:
                    urllib.request.urlopen(
                        f"https://api.telegram.org/bot{tok}/deleteWebhook",
                        timeout=3
                    )
            except Exception:
                pass
            _time.sleep(3)
            raise SystemExit(0)

        _sig.signal(_sig.SIGTERM, _on_sigterm)
        daemon.start()


if __name__ == "__main__":
    main()
