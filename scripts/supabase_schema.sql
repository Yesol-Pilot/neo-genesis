-- ============================================
-- Sora v2.0 — Supabase Schema (with Sessions)
--
-- Supabase Dashboard > SQL Editor에서 실행
-- 프로젝트: kfoixzebpztikurwqgdr (sora)
-- ============================================

-- 0. 세션 (대화 그룹)
CREATE TABLE IF NOT EXISTS sora_sessions (
    id TEXT PRIMARY KEY DEFAULT 'ses_' || substr(gen_random_uuid()::text, 1, 12),
    title TEXT NOT NULL DEFAULT '새 대화',
    channel TEXT DEFAULT 'dashboard',
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    pinned BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1. 대화 기록 (크로스 디바이스)
CREATE TABLE IF NOT EXISTS sora_conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT REFERENCES sora_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'unknown',
    device_id TEXT DEFAULT 'cloud',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 학습 메모리
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

-- 3. 디바이스 레지스트리
CREATE TABLE IF NOT EXISTS sora_devices (
    device_id TEXT PRIMARY KEY,
    device_type TEXT NOT NULL DEFAULT 'unknown',
    hostname TEXT DEFAULT '',
    status TEXT DEFAULT 'offline',
    system_info JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 태스크 보드
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

-- 5. 에이전트 에피소드
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
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sora_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_pinned ON sora_sessions(pinned DESC, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_session ON sora_conversations(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_channel ON sora_conversations(channel, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_category ON sora_memory(category, importance DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON sora_tasks(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_devices_heartbeat ON sora_devices(last_heartbeat DESC);

-- RLS (본인만 접근)
ALTER TABLE sora_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE sora_episodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner_only" ON sora_sessions FOR ALL USING (true);
CREATE POLICY "owner_only" ON sora_conversations FOR ALL USING (true);
CREATE POLICY "owner_only" ON sora_memory FOR ALL USING (true);
CREATE POLICY "owner_only" ON sora_devices FOR ALL USING (true);
CREATE POLICY "owner_only" ON sora_tasks FOR ALL USING (true);
CREATE POLICY "owner_only" ON sora_episodes FOR ALL USING (true);

-- Realtime 활성화
ALTER PUBLICATION supabase_realtime ADD TABLE sora_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE sora_conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE sora_devices;
