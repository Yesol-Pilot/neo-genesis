# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.queue import redis_bus


class _FakeRedisClient:
    def __init__(self, url, should_fail):
        self.url = url
        self.should_fail = should_fail
        self.closed = False

    async def ping(self):
        if self.should_fail:
            raise RuntimeError(f"connect failed: {self.url}")
        return True

    async def aclose(self):
        self.closed = True


class _FakeRedisDequeClient(_FakeRedisClient):
    def __init__(self, url, responses):
        super().__init__(url, should_fail=False)
        self._responses = list(responses)

    async def brpop(self, *args, **kwargs):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_build_redis_url_candidates_prefers_localhost_before_wsl_ip(monkeypatch):
    monkeypatch.setattr(redis_bus.sys, "platform", "win32")
    monkeypatch.setattr(redis_bus, "_resolve_wsl_primary_ip", lambda distro: "172.21.218.191")

    candidates = redis_bus._build_redis_url_candidates("redis://localhost:6379/0")

    assert candidates == [
        "redis://localhost:6379/0",
        "redis://172.21.218.191:6379/0",
    ]


def test_redis_bus_reads_env_when_instantiated(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://runtime-host:6380/2")

    bus = redis_bus.RedisBus()

    assert bus._redis_url == "redis://runtime-host:6380/2"


def test_default_redis_url_uses_local_runtime_password(monkeypatch, tmp_path):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("SORA_REDIS_PASSWORD", raising=False)
    monkeypatch.setattr(redis_bus, "PROJECT_ROOT", tmp_path)
    password_dir = tmp_path / "data" / "automation"
    password_dir.mkdir(parents=True)
    (password_dir / "redis_password.txt").write_text("secret-pass\n", encoding="ascii")

    bus = redis_bus.RedisBus()

    assert bus._redis_url == "redis://:secret-pass@localhost:6379/0"


def test_redact_redis_url_hides_password():
    redacted = redis_bus._redact_redis_url("redis://:secret-pass@localhost:6379/0")

    assert redacted == "redis://***@localhost:6379/0"
    assert "secret-pass" not in redacted


def test_redis_bus_has_no_connect_monkey_patch():
    source = Path(redis_bus.__file__).read_text(encoding="utf-8")

    assert "RedisBus.connect =" not in source
    assert "_redisbus_connect" not in source


def test_connect_falls_back_to_next_candidate(monkeypatch):
    clients = {}

    def _fake_from_url(url, **kwargs):
        client = _FakeRedisClient(url, should_fail=url == "redis://bad-host:6379/0")
        clients[url] = client
        return client

    monkeypatch.setattr(redis_bus.aioredis, "from_url", _fake_from_url)
    monkeypatch.setattr(
        redis_bus,
        "_build_redis_url_candidates",
        lambda url: ["redis://bad-host:6379/0", "redis://good-host:6379/0"],
    )

    bus = redis_bus.RedisBus(redis_url="redis://localhost:6379/0")
    client = asyncio.run(bus.connect())

    assert client is clients["redis://good-host:6379/0"]
    assert clients["redis://bad-host:6379/0"].closed is True
    assert bus._redis_url == "redis://good-host:6379/0"


def test_dequeue_request_retries_after_connection_error(monkeypatch):
    first = _FakeRedisDequeClient(
        "redis://localhost:6379/0",
        [redis_bus.RedisConnectionError("Connection closed by server."), (redis_bus.REQUEST_QUEUE, '{"hello": "world"}')],
    )
    clients = [first]

    def _fake_from_url(url, **kwargs):
        if clients:
            return clients.pop(0)
        return _FakeRedisDequeClient(url, [(redis_bus.REQUEST_QUEUE, '{"hello": "world"}')])

    monkeypatch.setattr(redis_bus.aioredis, "from_url", _fake_from_url)
    monkeypatch.setattr(redis_bus, "_build_redis_url_candidates", lambda url: ["redis://localhost:6379/0"])

    bus = redis_bus.RedisBus(redis_url="redis://localhost:6379/0")
    result = asyncio.run(bus.dequeue_request(timeout=0))

    assert result == {"hello": "world"}
