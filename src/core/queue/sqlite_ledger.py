# -*- coding: utf-8 -*-
"""
Jarvis Control-Plane Ledger — SQLite WAL durable queue + fencing lease + kill switch.

설계 정본: `.agent/knowledge/20260524_JARVIS_ARCHITECTURE_v2.md` (§5.4, §0.5/§0.6)
거버넌스: `command_governor.py` warn-then-obey + `execution_gate.py` G0-G5 + 2-Phase Sovereignty.

이 모듈이 control plane 의 "진실의 원천"이다:
- jobs            : 작업 큐 (status / fencing_token / lease)
- leases          : lease 발급 이력 (fencing)
- approvals       : strict approval FSM (inline button confirm_id, action_hash bind, TTL)
- audit           : append-only 감사 로그
- tool_runs       : 증거 기반 실행 진실 (exit_code=0 + output_hash 있어야 "실행 완료" 보고 가능)
- kill_switch     : 전역 동결 (epoch bump → in-flight lease 일괄 무효)
- fencing_sequence: 단조 증가 fencing token 발급기 (Kleppmann)
- ingress_dedupe  : update_id + content_hash 멱등성 (TTL)
- rate_buckets    : per-key 토큰 버킷 (LLM/CLI 호출 前 게이트)

설계 원칙 (정합):
- 모든 write 는 BEGIN IMMEDIATE (read→write 격상 데드락 회피, SQLITE_BUSY 시 backoff retry).
- transaction 안에서는 state 전이 + audit append 만. LLM/shell/network 호출 금지.
- stale worker 의 늦은 commit 은 fencing_token / lease_epoch 불일치로 0-row → 거부.
- 순수 stdlib (의존성 0). DB 는 반드시 로컬 디스크 (network/WSL mount 공유 금지).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import random
import secrets
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterator, Optional

# ── 튜닝 상수 (env override 가능, 하드코딩 회피) ──
BUSY_TIMEOUT_MS = int(os.getenv("JARVIS_DB_BUSY_TIMEOUT_MS", "10000"))
DEDUPE_TTL_SEC = int(os.getenv("JARVIS_DEDUPE_TTL_SEC", str(26 * 3600)))  # Telegram 24h 보관 + 여유
APPROVAL_TTL_SEC = int(os.getenv("JARVIS_APPROVAL_TTL_SEC", "60"))
LEASE_TTL_SEC = int(os.getenv("JARVIS_LEASE_TTL_SEC", "300"))
_TX_MAX_RETRIES = 6


# ──────────────────────────────────────────────────────────────────────────
# 연결 + 스키마
# ──────────────────────────────────────────────────────────────────────────
def connect(db_path: str) -> sqlite3.Connection:
    """WAL + 수동 트랜잭션 모드 연결.

    isolation_level=None: Python sqlite3 의 암묵 트랜잭션 비활성 → 명시적 BEGIN IMMEDIATE 강제.
    (표준 sqlite3 컨텍스트 매니저는 트랜잭션 시작 시점을 못 잡는 함정이 있음.)
    """
    conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id            TEXT PRIMARY KEY,
    source            TEXT NOT NULL,
    chat_id           TEXT,
    title             TEXT NOT NULL,
    command           TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN (
                          'queued','waiting_approval','running',
                          'succeeded','failed','cancelled','frozen')),
    risk_tier         TEXT NOT NULL DEFAULT 'G1',
    priority          INTEGER NOT NULL DEFAULT 100,
    idempotency_key   TEXT,
    fencing_token     INTEGER NOT NULL DEFAULT 0,
    lease_owner       TEXT,
    lease_epoch       INTEGER NOT NULL DEFAULT 0,
    lease_expires_at  REAL,
    attempt_count     INTEGER NOT NULL DEFAULT 0,
    created_at        REAL NOT NULL,
    updated_at        REAL NOT NULL,
    result_summary    TEXT,
    error_summary     TEXT,
    metadata_json     TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_jobs_claim ON jobs(status, priority, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_idem ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS leases (
    lease_id      TEXT PRIMARY KEY,
    job_id        TEXT NOT NULL,
    worker_id     TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    lease_epoch   INTEGER NOT NULL,
    acquired_at   REAL NOT NULL,
    expires_at    REAL NOT NULL,
    revoked_at    REAL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id      TEXT PRIMARY KEY,
    job_id           TEXT,
    chat_id          TEXT NOT NULL,
    user_id          TEXT NOT NULL,
    action_hash      TEXT NOT NULL,
    confirm_id_hash  TEXT NOT NULL,
    state            TEXT NOT NULL CHECK (state IN (
                         'requested','approved','rejected','expired','superseded')),
    risk_tier        TEXT NOT NULL,
    summary          TEXT NOT NULL,
    requested_at     REAL NOT NULL,
    expires_at       REAL NOT NULL,
    decided_at       REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_approvals_live
    ON approvals(confirm_id_hash) WHERE state = 'requested';

CREATE TABLE IF NOT EXISTS audit (
    audit_id     TEXT PRIMARY KEY,
    ts           REAL NOT NULL,
    job_id       TEXT,
    actor        TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    decision     TEXT,
    fencing_tk   INTEGER,
    detail_json  TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts);

CREATE TABLE IF NOT EXISTS tool_runs (
    tool_run_id  TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL,
    tool_name    TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN (
                     'planned','started','succeeded','failed','blocked','cancelled')),
    exit_code    INTEGER,
    output_hash  TEXT,
    stdout_path  TEXT,
    stderr_path  TEXT,
    artifact_uri TEXT,
    started_at   REAL NOT NULL,
    finished_at  REAL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS kill_switch (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    enabled      INTEGER NOT NULL DEFAULT 0,
    epoch        INTEGER NOT NULL DEFAULT 0,
    reason       TEXT,
    triggered_by TEXT,
    triggered_at REAL
);
INSERT OR IGNORE INTO kill_switch(id, enabled, epoch) VALUES (1, 0, 0);

CREATE TABLE IF NOT EXISTS fencing_sequence (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    next_val INTEGER NOT NULL DEFAULT 1
);
INSERT OR IGNORE INTO fencing_sequence(id, next_val) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS ingress_dedupe (
    source           TEXT NOT NULL,
    source_update_id TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    request_id       TEXT NOT NULL,
    first_seen_at    REAL NOT NULL,
    expires_at       REAL NOT NULL,
    PRIMARY KEY (source, source_update_id)
);
CREATE INDEX IF NOT EXISTS idx_dedupe_hash ON ingress_dedupe(source, content_hash);

CREATE TABLE IF NOT EXISTS rate_buckets (
    bucket_key     TEXT PRIMARY KEY,
    capacity       REAL NOT NULL,
    tokens         REAL NOT NULL,
    refill_per_sec REAL NOT NULL,
    updated_at     REAL NOT NULL
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


# ──────────────────────────────────────────────────────────────────────────
# 트랜잭션 헬퍼
# ──────────────────────────────────────────────────────────────────────────
@contextlib.contextmanager
def immediate_tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE + 자동 COMMIT/ROLLBACK + SQLITE_BUSY backoff 재시도."""
    last_exc: Optional[Exception] = None
    for attempt in range(_TX_MAX_RETRIES):
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            last_exc = exc
            if _is_busy(exc):
                _backoff(attempt)
                continue
            raise
        try:
            yield conn
            conn.execute("COMMIT")
            return
        except Exception:
            with contextlib.suppress(sqlite3.Error):
                conn.execute("ROLLBACK")
            raise
    raise TimeoutError(f"sqlite writer busy after {_TX_MAX_RETRIES} retries: {last_exc}")


def _is_busy(exc: sqlite3.Error) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


def _backoff(attempt: int) -> None:
    time.sleep(min(0.05 * (2 ** attempt), 0.8) + random.random() * 0.05)


def _now() -> float:
    return time.time()


def _next_fencing_token(conn: sqlite3.Connection) -> int:
    """반드시 immediate_tx 안에서 호출. 단조 증가 보장."""
    conn.execute("UPDATE fencing_sequence SET next_val = next_val + 1 WHERE id = 1")
    row = conn.execute("SELECT next_val FROM fencing_sequence WHERE id = 1").fetchone()
    return int(row["next_val"]) - 1  # 방금 소비한 값


def audit(conn: sqlite3.Connection, *, actor: str, event_type: str,
          job_id: Optional[str] = None, decision: Optional[str] = None,
          fencing_tk: Optional[int] = None, detail: Optional[dict] = None) -> None:
    """append-only 감사. immediate_tx 안/밖 모두 허용 (밖이면 autocommit)."""
    conn.execute(
        "INSERT INTO audit(audit_id, ts, job_id, actor, event_type, decision, fencing_tk, detail_json)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (uuid.uuid4().hex, _now(), job_id, actor, event_type, decision, fencing_tk,
         json.dumps(detail or {}, ensure_ascii=False)),
    )


# ──────────────────────────────────────────────────────────────────────────
# 1) Ingress 멱등성 (update_id + content_hash)
# ──────────────────────────────────────────────────────────────────────────
def content_hash(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seen_or_mark(conn: sqlite3.Connection, *, source: str, update_id: str,
                 chash: str, ttl: int = DEDUPE_TTL_SEC) -> tuple[bool, str]:
    """반환 (is_duplicate, request_id). 신규면 mark 후 (False, 새 id), 중복이면 (True, 기존 id)."""
    now = _now()
    with immediate_tx(conn):
        conn.execute("DELETE FROM ingress_dedupe WHERE expires_at < ?", (now,))
        row = conn.execute(
            "SELECT request_id FROM ingress_dedupe WHERE source=? AND source_update_id=?",
            (source, update_id),
        ).fetchone()
        if row:
            return True, row["request_id"]
        # content_hash 2차 키 (다른 update_id 로 재전송된 동일 내용)
        row2 = conn.execute(
            "SELECT request_id FROM ingress_dedupe WHERE source=? AND content_hash=? AND expires_at>=?",
            (source, chash, now),
        ).fetchone()
        if row2:
            return True, row2["request_id"]
        req_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO ingress_dedupe(source, source_update_id, content_hash, request_id, first_seen_at, expires_at)"
            " VALUES (?,?,?,?,?,?)",
            (source, update_id, chash, req_id, now, now + ttl),
        )
        return False, req_id


# ──────────────────────────────────────────────────────────────────────────
# 2) Token bucket (LLM/CLI 호출 前 게이트)
# ──────────────────────────────────────────────────────────────────────────
def token_bucket_consume(conn: sqlite3.Connection, *, key: str, capacity: float,
                         refill_per_sec: float, cost: float = 1.0) -> bool:
    """True=허용(토큰 차감), False=거부(rate limited). 영속 토큰 버킷."""
    now = _now()
    with immediate_tx(conn):
        row = conn.execute("SELECT tokens, updated_at FROM rate_buckets WHERE bucket_key=?", (key,)).fetchone()
        if row is None:
            tokens = capacity
        else:
            elapsed = max(0.0, now - row["updated_at"])
            tokens = min(capacity, row["tokens"] + elapsed * refill_per_sec)
        if tokens >= cost:
            tokens -= cost
            allowed = True
        else:
            allowed = False
        conn.execute(
            "INSERT INTO rate_buckets(bucket_key, capacity, tokens, refill_per_sec, updated_at)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(bucket_key) DO UPDATE SET tokens=excluded.tokens,"
            " capacity=excluded.capacity, refill_per_sec=excluded.refill_per_sec, updated_at=excluded.updated_at",
            (key, capacity, tokens, refill_per_sec, now),
        )
        return allowed


# ──────────────────────────────────────────────────────────────────────────
# 3) Job 큐 + fencing lease
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class Claim:
    job_id: str
    command: str
    fencing_token: int
    lease_epoch: int
    risk_tier: str


def enqueue(conn: sqlite3.Connection, *, source: str, title: str, command: str,
            chat_id: Optional[str] = None, risk_tier: str = "G1",
            priority: int = 100, idempotency_key: Optional[str] = None,
            status: str = "queued") -> str:
    job_id = uuid.uuid4().hex
    now = _now()
    with immediate_tx(conn):
        if idempotency_key:
            row = conn.execute("SELECT job_id FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if row:
                return row["job_id"]  # 멱등: 기존 job 반환
        conn.execute(
            "INSERT INTO jobs(job_id, source, chat_id, title, command, status, risk_tier,"
            " priority, idempotency_key, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, source, chat_id, title, command, status, risk_tier, priority,
             idempotency_key, now, now),
        )
        audit(conn, actor=source, event_type="enqueue", job_id=job_id, detail={"title": title})
    return job_id


def claim(conn: sqlite3.Connection, *, worker_id: str, lease_ttl: int = LEASE_TTL_SEC) -> Optional[Claim]:
    """가장 우선순위 높은 queued job 을 lease 획득. kill switch 활성 시 None."""
    now = _now()
    with immediate_tx(conn):
        ks = conn.execute("SELECT enabled, epoch FROM kill_switch WHERE id=1").fetchone()
        if ks["enabled"]:
            return None
        epoch = int(ks["epoch"])
        row = conn.execute(
            "SELECT job_id, command, risk_tier FROM jobs"
            " WHERE status='queued' OR (status='running' AND lease_expires_at IS NOT NULL AND lease_expires_at < ?)"
            " ORDER BY priority ASC, created_at ASC LIMIT 1",
            (now,),
        ).fetchone()
        if row is None:
            return None
        token = _next_fencing_token(conn)
        updated = conn.execute(
            "UPDATE jobs SET status='running', lease_owner=?, fencing_token=?, lease_epoch=?,"
            " lease_expires_at=?, attempt_count=attempt_count+1, updated_at=?"
            " WHERE job_id=? AND (status='queued' OR (status='running' AND lease_expires_at < ?))",
            (worker_id, token, epoch, now + lease_ttl, now, row["job_id"], now),
        ).rowcount
        if updated != 1:
            return None  # 경쟁에서 짐
        lease_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO leases(lease_id, job_id, worker_id, fencing_token, lease_epoch, acquired_at, expires_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (lease_id, row["job_id"], worker_id, token, epoch, now, now + lease_ttl),
        )
        audit(conn, actor=worker_id, event_type="claim", job_id=row["job_id"], fencing_tk=token)
        return Claim(job_id=row["job_id"], command=row["command"], fencing_token=token,
                     lease_epoch=epoch, risk_tier=row["risk_tier"])


def complete(conn: sqlite3.Connection, *, job_id: str, worker_id: str, fencing_token: int,
             lease_epoch: int, status: str = "succeeded",
             result_summary: str = "", error_summary: str = "") -> bool:
    """fencing 검증 통과 시에만 commit. stale worker / kill 이후 commit → False (거부)."""
    if status not in ("succeeded", "failed"):
        raise ValueError("status must be 'succeeded' or 'failed'")
    now = _now()
    with immediate_tx(conn):
        updated = conn.execute(
            "UPDATE jobs SET status=?, result_summary=?, error_summary=?, lease_owner=NULL,"
            " lease_expires_at=NULL, updated_at=?"
            " WHERE job_id=? AND lease_owner=? AND fencing_token=? AND lease_epoch=?"
            " AND lease_expires_at > ?"
            " AND (SELECT enabled FROM kill_switch WHERE id=1)=0"
            " AND lease_epoch=(SELECT epoch FROM kill_switch WHERE id=1)",
            (status, result_summary, error_summary, now, job_id, worker_id,
             fencing_token, lease_epoch, now),
        ).rowcount
        if updated != 1:
            audit(conn, actor=worker_id, event_type="stale_commit_blocked", job_id=job_id,
                  fencing_tk=fencing_token, detail={"reason": "fencing/kill/expiry mismatch"})
            return False
        audit(conn, actor=worker_id, event_type="complete", job_id=job_id,
              decision=status, fencing_tk=fencing_token)
        return True


# ──────────────────────────────────────────────────────────────────────────
# 4) Kill switch (전역 동결)
# ──────────────────────────────────────────────────────────────────────────
def activate_kill_switch(conn: sqlite3.Connection, *, reason: str, actor: str) -> int:
    """epoch++ → in-flight lease 일괄 무효 + 모든 미완 job frozen. 새 epoch 반환."""
    now = _now()
    with immediate_tx(conn):
        conn.execute(
            "UPDATE kill_switch SET enabled=1, epoch=epoch+1, reason=?, triggered_by=?, triggered_at=? WHERE id=1",
            (reason, actor, now),
        )
        new_epoch = int(conn.execute("SELECT epoch FROM kill_switch WHERE id=1").fetchone()["epoch"])
        conn.execute(
            "UPDATE jobs SET status='frozen', updated_at=? WHERE status IN ('queued','waiting_approval','running')",
            (now,),
        )
        conn.execute("UPDATE leases SET revoked_at=? WHERE revoked_at IS NULL", (now,))
        audit(conn, actor=actor, event_type="kill_switch_triggered", decision="freeze_all",
              detail={"reason": reason, "epoch": new_epoch})
        return new_epoch


def clear_kill_switch(conn: sqlite3.Connection, *, actor: str) -> None:
    """해제. (강한 승인은 호출측 책임 — 한 단어 금지.)"""
    with immediate_tx(conn):
        conn.execute("UPDATE kill_switch SET enabled=0 WHERE id=1")
        audit(conn, actor=actor, event_type="kill_switch_cleared")


def is_kill_active(conn: sqlite3.Connection) -> bool:
    return bool(conn.execute("SELECT enabled FROM kill_switch WHERE id=1").fetchone()["enabled"])


# ──────────────────────────────────────────────────────────────────────────
# 5) Strict Approval FSM (inline button confirm_id, action_hash bind, TTL)
# ──────────────────────────────────────────────────────────────────────────
_APPROVAL_SECRET = os.getenv("JARVIS_APPROVAL_SECRET", "")


def _confirm_id_hash(confirm_id: str) -> str:
    return hashlib.sha256(confirm_id.encode("utf-8")).hexdigest()


def request_approval(conn: sqlite3.Connection, *, chat_id: str, user_id: str,
                     action_hash: str, summary: str, risk_tier: str = "G3",
                     job_id: Optional[str] = None, ttl: int = APPROVAL_TTL_SEC) -> tuple[str, str]:
    """반환 (approval_id, confirm_id). confirm_id 원본은 DB 미저장(hash만). 같은 job 이전 requested → superseded."""
    now = _now()
    approval_id = uuid.uuid4().hex
    confirm_id = secrets.token_hex(5)  # 10 chars, ≤64B callback_data
    with immediate_tx(conn):
        if job_id:
            conn.execute(
                "UPDATE approvals SET state='superseded' WHERE job_id=? AND state='requested'", (job_id,))
        conn.execute(
            "INSERT INTO approvals(approval_id, job_id, chat_id, user_id, action_hash, confirm_id_hash,"
            " state, risk_tier, summary, requested_at, expires_at)"
            " VALUES (?,?,?,?,?,?,'requested',?,?,?,?)",
            (approval_id, job_id, chat_id, user_id, action_hash, _confirm_id_hash(confirm_id),
             risk_tier, summary, now, now + ttl),
        )
        audit(conn, actor=user_id, event_type="approval_requested", job_id=job_id,
              detail={"approval_id": approval_id, "risk_tier": risk_tier})
    return approval_id, confirm_id


def decide_approval(conn: sqlite3.Connection, *, approval_id: str, confirm_id: str,
                    chat_id: str, user_id: str, current_action_hash: str,
                    approve: bool) -> str:
    """반환 state: approved|rejected|expired|invalid. 실행 직전 action_hash 재검증 포함."""
    now = _now()
    with immediate_tx(conn):
        row = conn.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
        if row is None or row["state"] != "requested":
            return "invalid"
        # 바인딩 검증 (탈취/replay/spoof 차단)
        if (row["chat_id"] != chat_id or row["user_id"] != user_id
                or row["confirm_id_hash"] != _confirm_id_hash(confirm_id)):
            audit(conn, actor=user_id, event_type="approval_reject_bind", job_id=row["job_id"],
                  detail={"approval_id": approval_id})
            return "invalid"
        if now > row["expires_at"]:
            conn.execute("UPDATE approvals SET state='expired', decided_at=? WHERE approval_id=?", (now, approval_id))
            audit(conn, actor=user_id, event_type="approval_expired", job_id=row["job_id"])
            return "expired"
        if not approve:
            conn.execute("UPDATE approvals SET state='rejected', decided_at=? WHERE approval_id=?", (now, approval_id))
            audit(conn, actor=user_id, event_type="approval_rejected", job_id=row["job_id"])
            return "rejected"
        # action 이 승인 후 바뀌었으면 재승인 (TOCTOU 차단)
        if row["action_hash"] != current_action_hash:
            conn.execute("UPDATE approvals SET state='superseded', decided_at=? WHERE approval_id=?", (now, approval_id))
            audit(conn, actor=user_id, event_type="approval_action_changed", job_id=row["job_id"])
            return "invalid"
        conn.execute("UPDATE approvals SET state='approved', decided_at=? WHERE approval_id=?", (now, approval_id))
        audit(conn, actor=user_id, event_type="approval_approved", job_id=row["job_id"], decision="approved")
        return "approved"


# ──────────────────────────────────────────────────────────────────────────
# 6) 증거 기반 실행 진실 (tool_runs)
# ──────────────────────────────────────────────────────────────────────────
def record_tool_run(conn: sqlite3.Connection, *, job_id: str, tool_name: str, status: str,
                    exit_code: Optional[int] = None, output_hash: Optional[str] = None,
                    stdout_path: Optional[str] = None, stderr_path: Optional[str] = None,
                    artifact_uri: Optional[str] = None) -> str:
    run_id = uuid.uuid4().hex
    now = _now()
    finished = now if status in ("succeeded", "failed", "blocked", "cancelled") else None
    with immediate_tx(conn):
        conn.execute(
            "INSERT INTO tool_runs(tool_run_id, job_id, tool_name, status, exit_code, output_hash,"
            " stdout_path, stderr_path, artifact_uri, started_at, finished_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, job_id, tool_name, status, exit_code, output_hash,
             stdout_path, stderr_path, artifact_uri, now, finished),
        )
    return run_id


def can_report_success(conn: sqlite3.Connection, *, job_id: str) -> bool:
    """'실행 완료' 보고 허용 조건: succeeded + exit_code=0 + output_hash 존재한 tool_run 이 1건 이상.

    LLM 이 '실행했습니다'라고 써도 이 게이트가 False 면 sanitizer 가 '실행 증거 없음'으로 치환해야 함.
    """
    row = conn.execute(
        "SELECT 1 FROM tool_runs WHERE job_id=? AND status='succeeded' AND exit_code=0"
        " AND output_hash IS NOT NULL LIMIT 1",
        (job_id,),
    ).fetchone()
    return row is not None


# ── 자가 진단 (간단 smoke; 정식 테스트는 tests/core/test_sqlite_fencing_queue.py) ──
if __name__ == "__main__":
    import tempfile
    db = os.path.join(tempfile.mkdtemp(), "smoke.db")
    c = connect(db)
    init_schema(c)
    jid = enqueue(c, source="cli", title="smoke", command="echo hi")
    cl = claim(c, worker_id="w1")
    ok = complete(c, job_id=jid, worker_id="w1", fencing_token=cl.fencing_token, lease_epoch=cl.lease_epoch)
    print(f"smoke: enqueue+claim+complete -> {ok}  (job={jid[:8]})")
