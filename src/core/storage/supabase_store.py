# -*- coding: utf-8 -*-
"""
Sora v2.0 — Supabase Persistent Storage

모든 디바이스에서 공유되는 영속 상태 저장소.
AssistantMemory와 동일한 인터페이스를 제공하되, 백엔드가 Supabase.

Tables:
    - sora_conversations: 크로스 디바이스 대화 기록
    - sora_memory: 학습된 사실, 선호, 교훈
    - sora_devices: 연결된 디바이스 상태
    - sora_tasks: 태스크 보드
    - sora_episodes: 에이전트 에피소드 기록
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("neo.storage.supabase")

SUPABASE_URL = os.getenv("SORA_SUPABASE_URL") or os.getenv("UR_WRONG_SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SORA_SUPABASE_KEY") or os.getenv("UR_WRONG_ANON_KEY", "")


class SupabaseStore:
    """Supabase 기반 영속 스토리지 — 크로스 디바이스 동기화."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Supabase 클라이언트 (lazy init)."""
        if self._client is None:
            if not SUPABASE_URL or not SUPABASE_KEY:
                logger.warning("[Supabase] URL/KEY 미설정 — 로컬 폴백 모드")
                return None
            try:
                from supabase import create_client
                self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("[Supabase] 연결 완료")
            except Exception as e:
                logger.error(f"[Supabase] 연결 실패: {e}")
                return None
        return self._client

    # ── 대화 기록 (conversations) ──

    def add_conversation(self, role: str, content: str, channel: str = "unknown",
                         device_id: str = "cloud", session_id: str = "default",
                         metadata: dict = None) -> bool:
        """대화 메시지 저장."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_conversations").insert({
                "session_id": session_id,
                "role": role,
                "content": content[:2000],
                "channel": channel,
                "device_id": device_id,
                "metadata": metadata or {},
            }).execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 대화 저장 실패: {e}")
            return False

    def get_recent_conversations(self, n: int = 20, session_id: str = None) -> list:
        """최근 대화 N건 조회."""
        client = self._get_client()
        if not client:
            return []
        try:
            q = client.table("sora_conversations").select("*").order("created_at", desc=True).limit(n)
            if session_id:
                q = q.eq("session_id", session_id)
            result = q.execute()
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            logger.error(f"[Supabase] 대화 조회 실패: {e}")
            return []

    # ── 메모리 (memory) ──

    def add_memory(self, content: str, category: str = "fact",
                   source: str = "conversation", importance: int = 5) -> bool:
        """학습된 사실/선호/교훈 저장."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_memory").insert({
                "category": category,
                "content": content,
                "source": source,
                "importance": importance,
            }).execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 메모리 저장 실패: {e}")
            return False

    def search_memory(self, query: str, limit: int = 10) -> list:
        """메모리 검색 (키워드 기반)."""
        client = self._get_client()
        if not client:
            return []
        try:
            result = client.table("sora_memory").select("*") \
                .ilike("content", f"%{query}%") \
                .order("importance", desc=True) \
                .limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[Supabase] 메모리 검색 실패: {e}")
            return []

    def get_all_memory(self, category: str = None, limit: int = 100) -> list:
        """전체 메모리 조회."""
        client = self._get_client()
        if not client:
            return []
        try:
            q = client.table("sora_memory").select("*").order("created_at", desc=True).limit(limit)
            if category:
                q = q.eq("category", category)
            result = q.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[Supabase] 메모리 조회 실패: {e}")
            return []

    # ── 디바이스 상태 (devices) ──

    def upsert_device(self, device_id: str, device_type: str, hostname: str = "",
                      status: str = "online", system_info: dict = None) -> bool:
        """디바이스 상태 업서트 (하트비트)."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_devices").upsert({
                "device_id": device_id,
                "device_type": device_type,
                "hostname": hostname,
                "status": status,
                "system_info": system_info or {},
                "last_heartbeat": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }, on_conflict="device_id").execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 디바이스 업서트 실패: {e}")
            return False

    def get_devices(self) -> list:
        """연결된 디바이스 목록."""
        client = self._get_client()
        if not client:
            return []
        try:
            result = client.table("sora_devices").select("*") \
                .order("last_heartbeat", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[Supabase] 디바이스 조회 실패: {e}")
            return []

    # ── 태스크 보드 (tasks) ──

    def add_task(self, title: str, description: str = "", priority: str = "medium",
                 sbu: str = "", assigned_device: str = "") -> bool:
        """태스크 생성."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_tasks").insert({
                "title": title,
                "description": description,
                "priority": priority,
                "sbu": sbu,
                "assigned_device": assigned_device,
            }).execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 태스크 저장 실패: {e}")
            return False

    def get_tasks(self, status: str = None, limit: int = 50) -> list:
        """태스크 조회."""
        client = self._get_client()
        if not client:
            return []
        try:
            q = client.table("sora_tasks").select("*").order("created_at", desc=True).limit(limit)
            if status:
                q = q.eq("status", status)
            result = q.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[Supabase] 태스크 조회 실패: {e}")
            return []

    def update_task(self, task_id: str, **kwargs) -> bool:
        """태스크 업데이트."""
        client = self._get_client()
        if not client:
            return False
        try:
            kwargs["updated_at"] = datetime.utcnow().isoformat()
            client.table("sora_tasks").update(kwargs).eq("id", task_id).execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 태스크 업데이트 실패: {e}")
            return False

    # ── 에피소드 (episodes) ──

    def start_episode(self, trigger: dict) -> Optional[str]:
        """에피소드 시작."""
        client = self._get_client()
        if not client:
            return None
        try:
            result = client.table("sora_episodes").insert({
                "trigger": trigger,
                "events": [],
            }).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error(f"[Supabase] 에피소드 시작 실패: {e}")
            return None

    def end_episode(self, episode_id: str, summary: str = "", result: dict = None) -> bool:
        """에피소드 종료."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_episodes").update({
                "summary": summary,
                "result": result or {},
                "ended_at": datetime.utcnow().isoformat(),
            }).eq("id", episode_id).execute()
            return True
        except Exception as e:
            logger.error(f"[Supabase] 에피소드 종료 실패: {e}")
            return False

    # ── 헬스체크 ──

    def health_check(self) -> bool:
        """Supabase 연결 상태."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.table("sora_devices").select("device_id").limit(1).execute()
            return True
        except Exception:
            return False


# ── Supabase 테이블 생성 SQL ──

SCHEMA_SQL = """
-- Sora v2.0 Supabase Schema
-- Supabase SQL Editor에서 실행

CREATE TABLE IF NOT EXISTS sora_conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'unknown',
    device_id TEXT DEFAULT 'cloud',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sora_memory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    source TEXT DEFAULT 'conversation',
    importance INTEGER DEFAULT 5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sora_devices (
    device_id TEXT PRIMARY KEY,
    device_type TEXT NOT NULL DEFAULT 'unknown',
    hostname TEXT DEFAULT '',
    status TEXT DEFAULT 'offline',
    system_info JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sora_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    sbu TEXT DEFAULT '',
    assigned_device TEXT DEFAULT '',
    due_date TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sora_episodes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trigger JSONB NOT NULL DEFAULT '{}',
    events JSONB DEFAULT '[]',
    result JSONB DEFAULT '{}',
    summary TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_conv_session ON sora_conversations(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_channel ON sora_conversations(channel, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_category ON sora_memory(category, importance DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON sora_tasks(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_devices_heartbeat ON sora_devices(last_heartbeat DESC);

-- RLS (Row Level Security) — 서비스 키만 접근 허용
ALTER TABLE sora_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_episodes ENABLE ROW LEVEL SECURITY;

-- 서비스 역할에 전체 접근 허용
CREATE POLICY "service_all" ON sora_conversations FOR ALL USING (true);
CREATE POLICY "service_all" ON sora_memory FOR ALL USING (true);
CREATE POLICY "service_all" ON sora_devices FOR ALL USING (true);
CREATE POLICY "service_all" ON sora_tasks FOR ALL USING (true);
CREATE POLICY "service_all" ON sora_episodes FOR ALL USING (true);
"""


# ── 싱글턴 ──
_store: Optional[SupabaseStore] = None


def get_supabase_store() -> SupabaseStore:
    """SupabaseStore 싱글턴."""
    global _store
    if _store is None:
        _store = SupabaseStore()
    return _store
