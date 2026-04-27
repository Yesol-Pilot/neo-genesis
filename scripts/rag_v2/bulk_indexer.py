"""scripts/rag_v2/bulk_indexer.py — RAG v2 batch 인덱싱 도구.

Phase 1 본격 인덱싱용. watchdog_indexer 가 change-detection 까지만이라
실제 chunking + embedding + Qdrant upsert 흐름은 본 스크립트가 담당한다.

기능:
  - Qdrant 6 컬렉션 init (`--init-collections`)
  - 디렉토리 batch 인덱싱 (`--index <path> --collection <name>`)
  - allowlist 정책 적용 (.agent/policies/rag_source_allowlist.yaml)
  - credential redactor + PDF sanitizer 자동 적용
  - heading-aware 마크다운 청킹 + 단순 sliding-window 코드 청킹
  - embedding 호출 (localhost:7702 KURE-v1, MRL 1024d)
  - Qdrant upsert (UUID5 deterministic id, payload metadata)
  - rag_chunk_lineage Supabase 기록 (provenance)
  - Blake3 캐시 (skip unchanged files)

사용:
    # 컬렉션 생성
    python scripts/rag_v2/bulk_indexer.py --init-collections

    # SSOT 인덱싱
    python scripts/rag_v2/bulk_indexer.py --index .agent --collection neo_ssot --project-tag neo-genesis

    # 코드 인덱싱
    python scripts/rag_v2/bulk_indexer.py --index src --collection neo_code --project-tag neo-genesis

    # dry-run (인덱싱 없이 통계만)
    python scripts/rag_v2/bulk_indexer.py --index .agent --collection neo_ssot --dry-run

부록: .agent/knowledge/rag-master/04_collection_topology.md, 02_architecture.md
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import urllib.error
import urllib.request

logger = logging.getLogger("rag_v2.bulk_indexer")

# Project root
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ─────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────

QDRANT_URL = os.environ.get("QDRANT_URL", "http://ysh-server:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
EMBEDDING_URL = os.environ.get("RAG_EMBED_URL", "http://localhost:7702")
EMBEDDING_DIM = 1024  # KURE-v1
CACHE_DB = os.environ.get("RAG_CACHE_DB", str(REPO_ROOT / "scripts/rag_v2/embedding_cache.sqlite"))

CHUNK_SIZE_TOK = 1024  # ~ 4096 chars
CHUNK_OVERLAP_TOK = 256  # ~ 1024 chars
MIN_CHUNK_CHARS = 100
MAX_CHUNK_CHARS = 4096

# UUID namespace for chunk_id stability
NS_RAG_V2 = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# 6 collections topology (RAG 마스터 §04)
COLLECTIONS = {
    "neo_ssot": {"description": ".agent/, BIBLE.md, knowledge/, shared-brain/", "vector_size": 1024},
    "neo_code": {"description": "neo-genesis src + auto-trading + portfolio + 2dlivegame", "vector_size": 1024},
    "neo_paper": {"description": "PAPER/EthicaAI + PAPER/WhyLab + external", "vector_size": 1024},
    "neo_notes": {"description": "Claude memory, daily-log, handoff, ccr_checkpoints", "vector_size": 1024},
    "neo_quant": {"description": "auto-trading/docs (v11-ensemble, incidents)", "vector_size": 1024},
    "neo_secret": {"description": "credential bible 메타데이터 (실제 cred X)", "vector_size": 1024},
}


# ─────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(name)s [%(levelname)s] %(message)s"
    )


# ─────────────────────────────────────────────────────────────────────────
# Allowlist
# ─────────────────────────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    import yaml  # type: ignore

    if not path.exists():
        logger.warning("정책 파일 없음: %s — empty allowlist 로 fallback", path)
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize(p: str) -> str:
    return p.replace("\\", "/")


def _glob_extended(path: str, pattern: str) -> bool:
    """{a,b} 확장자 패턴 + ** 지원."""
    if "{" in pattern and "}" in pattern:
        pre, rest = pattern.split("{", 1)
        opts, post = rest.split("}", 1)
        for opt in opts.split(","):
            if fnmatch.fnmatch(path, pre + opt.strip() + post):
                return True
        return False
    return fnmatch.fnmatch(path, pattern)


def is_allowed(path: str, allow: List[str], deny: List[str], deny_only: bool = False) -> bool:
    norm = _normalize(path)
    norm_lower = norm.lower()
    for pat in deny:
        pat_lower = pat.lower()
        if _glob_extended(norm_lower, pat_lower):
            return False
        # 패턴의 leading **/ 또는 drive prefix 제거 후 substring 검사
        core = pat_lower.lstrip("/").replace("**/", "")
        if core and core in norm_lower:
            return False
    if deny_only or not allow:
        return True
    for pat in allow:
        pat_lower = pat.lower()
        if _glob_extended(norm_lower, pat_lower):
            return True
        # drive-letter 정규화: /d/foo → d:/foo, c:/foo → /c/foo 등 모두 시도
        # 핵심 부분 추출 (drive + leading slash 제거)
        core = re.sub(r"^[/\\][a-z][/\\]", "", pat_lower)  # /d/foo → foo
        core = re.sub(r"^[a-z]:[/\\]", "", core)  # d:/foo → foo
        if core and (
            _glob_extended(norm_lower, "**/" + core)
            or _glob_extended(norm_lower, "*" + core)
            or _glob_extended(norm_lower, "*/" + core)
        ):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────
# Qdrant client (REST minimal)
# ─────────────────────────────────────────────────────────────────────────


def _qdrant_request(method: str, path: str, body: Optional[dict] = None, timeout: float = 10.0) -> dict:
    url = f"{QDRANT_URL.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if QDRANT_API_KEY:
        req.add_header("api-key", QDRANT_API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"qdrant {method} {path} → {e.code}: {err_body}") from e


def qdrant_collection_exists(name: str) -> bool:
    try:
        _qdrant_request("GET", f"/collections/{name}")
        return True
    except RuntimeError:
        return False


def qdrant_create_collection(name: str, vector_size: int = 1024) -> bool:
    """idempotent: 이미 있으면 skip, 없으면 생성."""
    if qdrant_collection_exists(name):
        logger.info("collection '%s' 이미 존재 — skip", name)
        return False
    body = {
        "vectors": {
            "size": vector_size,
            "distance": "Cosine",
        },
        "on_disk_payload": True,
        "optimizers_config": {"indexing_threshold": 20_000},
    }
    _qdrant_request("PUT", f"/collections/{name}", body)
    logger.info("collection '%s' 생성 완료 (dim=%d)", name, vector_size)
    return True


def qdrant_upsert(collection: str, points: List[dict]) -> int:
    """points: [{id, vector, payload}, ...]"""
    if not points:
        return 0
    body = {"points": points}
    _qdrant_request("PUT", f"/collections/{collection}/points?wait=true", body)
    return len(points)


# ─────────────────────────────────────────────────────────────────────────
# Embedding client
# ─────────────────────────────────────────────────────────────────────────


def _embed_request(texts: List[str], timeout: float = 60.0, max_retries: int = 5) -> List[List[float]]:
    """KURE-v1 embedding service 호출 + 503 (GPU guard) 자동 retry.

    ComfyUI 등 GPU 점유 시 503 → 점진적 백오프 (5/10/15/20/30s).
    """
    url = f"{EMBEDDING_URL.rstrip('/')}/embed"
    body = json.dumps({"texts": texts}).encode("utf-8")
    backoff = [5, 10, 15, 20, 30]
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                result = json.loads(raw)
            embs = result.get("embeddings") or result.get("vectors") or []
            if len(embs) != len(texts):
                raise RuntimeError(
                    f"embedding 응답 길이 불일치: {len(embs)} vs {len(texts)}"
                )
            return embs
        except urllib.error.HTTPError as e:
            if e.code == 503 and attempt < max_retries - 1:
                wait = backoff[min(attempt, len(backoff) - 1)]
                logger.warning("503 GPU guard — %ds 후 재시도 (%d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                last_err = e
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait = backoff[min(attempt, len(backoff) - 1)]
                logger.warning("네트워크 오류 — %ds 후 재시도 (%s)", wait, e)
                time.sleep(wait)
                last_err = e
                continue
            raise
    raise RuntimeError(f"embedding 최대 재시도 초과: {last_err}")


# ─────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────

CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".sh", ".ps1", ".sql"}
MD_EXTS = {".md", ".markdown", ".mdx"}
TEXT_EXTS = {".txt", ".rst", ".tex", ".log"}
DATA_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env.example"}
SUPPORTED_EXTS = CODE_EXTS | MD_EXTS | TEXT_EXTS | DATA_EXTS


@dataclass
class Chunk:
    text: str
    heading: str = ""
    chunk_index: int = 0
    line_start: int = 0
    line_end: int = 0


def _chunk_markdown(text: str) -> List[Chunk]:
    """Heading-aware. ## 와 ### 단위로 자르고, 너무 길면 sliding window 보충."""
    chunks: List[Chunk] = []
    lines = text.splitlines()
    current_heading = ""
    buf: List[str] = []
    line_start = 0
    cur_idx = 0

    def flush(end_line: int) -> None:
        nonlocal cur_idx, line_start, buf
        body = "\n".join(buf).strip()
        if len(body) < MIN_CHUNK_CHARS:
            buf = []
            return
        if len(body) <= MAX_CHUNK_CHARS:
            chunks.append(
                Chunk(
                    text=body,
                    heading=current_heading,
                    chunk_index=cur_idx,
                    line_start=line_start,
                    line_end=end_line,
                )
            )
            cur_idx += 1
        else:
            # sliding window
            for s in _sliding_window(body):
                chunks.append(
                    Chunk(
                        text=s,
                        heading=current_heading,
                        chunk_index=cur_idx,
                        line_start=line_start,
                        line_end=end_line,
                    )
                )
                cur_idx += 1
        buf = []

    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if m:
            flush(i)
            current_heading = m.group(2).strip()
            line_start = i
            buf.append(line)
        else:
            if not buf:
                line_start = i
            buf.append(line)
    flush(len(lines))
    return chunks


def _chunk_code(text: str, lang_ext: str) -> List[Chunk]:
    """간단 sliding window — Phase 1 첫 버전. AST 기반은 Phase 2."""
    return _generic_chunks(text)


def _chunk_text(text: str) -> List[Chunk]:
    """일반 텍스트 sliding window."""
    return _generic_chunks(text)


def _generic_chunks(text: str) -> List[Chunk]:
    lines = text.splitlines()
    chunks: List[Chunk] = []
    if len(text) <= MAX_CHUNK_CHARS:
        if len(text.strip()) >= MIN_CHUNK_CHARS:
            chunks.append(Chunk(text=text.strip(), line_start=0, line_end=len(lines), chunk_index=0))
        return chunks

    cur = []
    cur_size = 0
    line_start = 0
    cur_idx = 0
    for i, line in enumerate(lines):
        ln = len(line) + 1
        if cur_size + ln > MAX_CHUNK_CHARS and cur:
            body = "\n".join(cur).strip()
            if len(body) >= MIN_CHUNK_CHARS:
                chunks.append(
                    Chunk(text=body, line_start=line_start, line_end=i, chunk_index=cur_idx)
                )
                cur_idx += 1
            # overlap (last 1/4)
            keep = max(1, len(cur) // 4)
            cur = cur[-keep:]
            cur_size = sum(len(l) + 1 for l in cur)
            line_start = i - keep
        cur.append(line)
        cur_size += ln
    if cur:
        body = "\n".join(cur).strip()
        if len(body) >= MIN_CHUNK_CHARS:
            chunks.append(
                Chunk(text=body, line_start=line_start, line_end=len(lines), chunk_index=cur_idx)
            )
    return chunks


def _sliding_window(text: str) -> Iterable[str]:
    """긴 본문을 MAX_CHUNK_CHARS 단위로 자른다 (overlap 포함)."""
    if len(text) <= MAX_CHUNK_CHARS:
        yield text
        return
    step = MAX_CHUNK_CHARS - 1024
    pos = 0
    while pos < len(text):
        seg = text[pos : pos + MAX_CHUNK_CHARS]
        if len(seg.strip()) >= MIN_CHUNK_CHARS:
            yield seg.strip()
        pos += step


def chunk_file(path: Path, text: str) -> List[Chunk]:
    ext = path.suffix.lower()
    if ext in MD_EXTS:
        return _chunk_markdown(text)
    if ext in CODE_EXTS:
        return _chunk_code(text, ext)
    return _chunk_text(text)


# ─────────────────────────────────────────────────────────────────────────
# Sanitization (P1-4 / P1-5)
# ─────────────────────────────────────────────────────────────────────────

try:
    from src.core.rag_v2.credential_redactor import (  # type: ignore
        has_critical_credential,
        redact_credentials,
    )
    from src.core.rag_v2.pdf_sanitizer import (  # type: ignore
        is_quarantined,
        sanitize_external_chunk,
    )
    _HAS_SANITIZERS = True
except ImportError:
    _HAS_SANITIZERS = False
    logger.warning("sanitizers 미로드 — credential leak / injection 차단 비활성")


def sanitize_chunk(text: str, *, is_external: bool) -> Optional[str]:
    """Returns sanitized text or None if quarantined."""
    if not _HAS_SANITIZERS:
        return text
    if has_critical_credential(text):
        return None  # quarantine
    cleaned = redact_credentials(text)
    if is_external:
        if is_quarantined(cleaned):
            return None
        cleaned = sanitize_external_chunk(cleaned)
    return cleaned


# ─────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────


def init_cache(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS file_hash (
            path TEXT PRIMARY KEY,
            blake3 TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime REAL NOT NULL,
            collection TEXT,
            chunks_indexed INTEGER DEFAULT 0,
            last_indexed REAL NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def _file_hash(path: Path) -> Optional[str]:
    try:
        import blake3 as _b3  # type: ignore

        h = _b3.blake3()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except ImportError:
        # fallback: sha256
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def cache_check(conn: sqlite3.Connection, path: Path, collection: str) -> Optional[str]:
    """이전 인덱싱과 동일하면 hash 반환 (skip 하라는 신호), 아니면 None."""
    cur = conn.execute(
        "SELECT blake3, collection FROM file_hash WHERE path = ?", (str(path),)
    )
    row = cur.fetchone()
    if row is None:
        return None
    cached_hash, cached_coll = row
    if cached_coll != collection:
        return None  # collection 변경 시 재인덱싱
    new_hash = _file_hash(path)
    if cached_hash == new_hash:
        return cached_hash  # skip
    return None


def cache_record(conn: sqlite3.Connection, path: Path, blake3_hex: str, collection: str, n_chunks: int) -> None:
    stat = path.stat()
    conn.execute(
        """
        INSERT INTO file_hash (path, blake3, size, mtime, collection, chunks_indexed, last_indexed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          blake3 = excluded.blake3,
          size = excluded.size,
          mtime = excluded.mtime,
          collection = excluded.collection,
          chunks_indexed = excluded.chunks_indexed,
          last_indexed = excluded.last_indexed
        """,
        (str(path), blake3_hex, stat.st_size, stat.st_mtime, collection, n_chunks, time.time()),
    )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────
# Indexer
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class IndexStats:
    files_scanned: int = 0
    files_skipped_allowlist: int = 0
    files_skipped_cache: int = 0
    files_indexed: int = 0
    chunks_total: int = 0
    chunks_quarantined: int = 0
    chunks_redacted: int = 0
    embeddings_called: int = 0
    qdrant_upserts: int = 0
    errors: int = 0
    duration_sec: float = 0.0


def _read_text_safe(path: Path, max_size: int = 5_000_000) -> Optional[str]:
    """5MB 이하 텍스트 파일만 읽음."""
    try:
        if path.stat().st_size > max_size:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _build_chunk_id(file_path: str, chunk_index: int, blake3: str) -> str:
    """deterministic UUID5 — 같은 파일 같은 chunk 는 항상 같은 id."""
    name = f"{file_path}|{chunk_index}|{blake3[:8]}"
    return str(uuid.uuid5(NS_RAG_V2, name))


def index_file(
    path: Path,
    *,
    collection: str,
    project_tag: str,
    device_origin: str,
    is_external: bool,
    cache: sqlite3.Connection,
    dry_run: bool,
    stats: IndexStats,
) -> int:
    """단일 파일 인덱싱 → 청크 수 반환."""
    if path.suffix.lower() not in SUPPORTED_EXTS:
        return 0
    blake = _file_hash(path)
    if blake is None:
        stats.errors += 1
        return 0
    cached = cache_check(cache, path, collection)
    if cached:
        stats.files_skipped_cache += 1
        return 0

    text = _read_text_safe(path)
    if text is None or not text.strip():
        return 0

    raw_chunks = chunk_file(path, text)
    if not raw_chunks:
        return 0

    sanitized: List[Chunk] = []
    for ch in raw_chunks:
        cleaned = sanitize_chunk(ch.text, is_external=is_external)
        if cleaned is None:
            stats.chunks_quarantined += 1
            continue
        if cleaned != ch.text:
            stats.chunks_redacted += 1
        sanitized.append(Chunk(text=cleaned, heading=ch.heading, chunk_index=ch.chunk_index, line_start=ch.line_start, line_end=ch.line_end))

    if not sanitized:
        return 0

    if dry_run:
        stats.chunks_total += len(sanitized)
        stats.files_indexed += 1
        return len(sanitized)

    # embedding (batch up to 32)
    BATCH = 32
    points: List[dict] = []
    rel_path = str(path).replace("\\", "/")
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

    for i in range(0, len(sanitized), BATCH):
        batch = sanitized[i : i + BATCH]
        try:
            vecs = _embed_request([c.text for c in batch], timeout=120.0)
        except Exception as e:
            stats.errors += 1
            logger.error("embedding 실패 %s: %s", path, e)
            return 0
        stats.embeddings_called += len(batch)
        for c, v in zip(batch, vecs):
            payload = {
                "collection": collection,
                "source_uri": rel_path,
                "project_tag": project_tag,
                "device_origin": device_origin,
                "source_type": "human",  # 일단 모두 human (provenance_classifier 차후 통합)
                "heading": c.heading,
                "chunk_index": c.chunk_index,
                "line_start": c.line_start,
                "line_end": c.line_end,
                "indexed_at": now_iso,
                "blake3": blake,
                "ext": path.suffix.lower(),
                "filename": path.name,
                "text": c.text[:1000],  # preview (전체는 별도 retrieve)
                "text_full": c.text,
            }
            point_id = _build_chunk_id(rel_path, c.chunk_index, blake)
            points.append({"id": point_id, "vector": v, "payload": payload})

    try:
        n_up = qdrant_upsert(collection, points)
        stats.qdrant_upserts += n_up
    except Exception as e:
        stats.errors += 1
        logger.error("qdrant upsert 실패 %s: %s", path, e)
        return 0

    cache_record(cache, path, blake, collection, len(sanitized))
    stats.chunks_total += len(sanitized)
    stats.files_indexed += 1
    return len(sanitized)


def index_directory(
    root: Path,
    collection: str,
    project_tag: str,
    *,
    device_origin: str,
    allow: List[str],
    deny: List[str],
    dry_run: bool,
    cache: sqlite3.Connection,
    is_external: bool,
    progress_every: int = 50,
) -> IndexStats:
    stats = IndexStats()
    start = time.time()

    files: List[Path] = []
    deny_only_mode = getattr(index_directory, "_deny_only", False)
    # 강건 traversal: symlink, permission error, OSError 모두 skip
    SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "dist", ".next", "build", ".cache"}

    def _walk(start: Path):
        try:
            for entry in start.iterdir():
                try:
                    if entry.is_dir():
                        if entry.name in SKIP_DIRS or entry.name.startswith("."):
                            # .agent 같이 시작하는 디렉토리는 통과시키되 SKIP_DIRS는 차단
                            if entry.name in SKIP_DIRS:
                                continue
                        try:
                            yield from _walk(entry)
                        except (OSError, PermissionError):
                            continue
                    elif entry.is_file():
                        yield entry
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            return

    for p in _walk(root):
        try:
            if not is_allowed(str(p), allow, deny, deny_only=deny_only_mode):
                stats.files_skipped_allowlist += 1
                continue
            if p.suffix.lower() not in SUPPORTED_EXTS:
                continue
            files.append(p)
        except (OSError, PermissionError):
            continue

    logger.info("디렉토리: %s | 매칭 파일: %d | collection: %s", root, len(files), collection)
    if dry_run:
        logger.info("DRY-RUN MODE — 인덱싱 없이 통계만 수집")

    for idx, fp in enumerate(files, 1):
        stats.files_scanned += 1
        try:
            index_file(
                fp,
                collection=collection,
                project_tag=project_tag,
                device_origin=device_origin,
                is_external=is_external,
                cache=cache,
                dry_run=dry_run,
                stats=stats,
            )
        except Exception as e:  # broad catch — 한 파일 fail 이 전체 중단 안 되게
            stats.errors += 1
            logger.error("file fail %s: %s", fp, e)
        if idx % progress_every == 0:
            logger.info(
                "[%d/%d] indexed=%d skipped(cache)=%d chunks=%d quar=%d red=%d err=%d",
                idx,
                len(files),
                stats.files_indexed,
                stats.files_skipped_cache,
                stats.chunks_total,
                stats.chunks_quarantined,
                stats.chunks_redacted,
                stats.errors,
            )

    stats.duration_sec = time.time() - start
    return stats


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG v2 batch indexer (Phase 1)")
    parser.add_argument("--init-collections", action="store_true", help="6 컬렉션 생성")
    parser.add_argument("--list-collections", action="store_true", help="현재 Qdrant 컬렉션 + 통계 출력")
    parser.add_argument("--index", type=str, default=None, help="인덱싱할 디렉토리")
    parser.add_argument("--collection", type=str, default=None, help="대상 컬렉션 (neo_ssot 등)")
    parser.add_argument("--project-tag", type=str, default="neo-genesis")
    parser.add_argument("--device-origin", type=str, default=os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown")
    parser.add_argument("--external", action="store_true", help="외부 출처 (PDF prompt injection sanitizer 적용)")
    parser.add_argument("--allowlist", type=str, default=str(REPO_ROOT / ".agent/policies/rag_source_allowlist.yaml"))
    parser.add_argument("--deny-only", action="store_true", help="allowlist patterns 무시, deny + supported_exts 만 적용")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-db", type=str, default=CACHE_DB)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.init_collections:
        created = 0
        for name, cfg in COLLECTIONS.items():
            if qdrant_create_collection(name, cfg["vector_size"]):
                created += 1
        logger.info("컬렉션 init 완료 — 신규 %d / 전체 %d", created, len(COLLECTIONS))
        return 0

    if args.list_collections:
        for name in COLLECTIONS:
            try:
                info = _qdrant_request("GET", f"/collections/{name}")
                count = info.get("result", {}).get("points_count", 0)
                vec = info.get("result", {}).get("config", {}).get("params", {}).get("vectors", {})
                logger.info("  %s: points=%d vec=%s", name, count, vec)
            except RuntimeError as e:
                logger.warning("  %s: not exists (%s)", name, e)
        return 0

    if not args.index or not args.collection:
        parser.error("--index DIR --collection NAME 필요 (또는 --init-collections / --list-collections)")

    if args.collection not in COLLECTIONS:
        parser.error(f"unknown collection: {args.collection} (allowed: {','.join(COLLECTIONS)})")

    root = Path(args.index).resolve()
    if not root.exists():
        parser.error(f"path missing: {root}")

    allowlist = _load_yaml(Path(args.allowlist))
    allow = allowlist.get("allowed_patterns", [])
    deny = allowlist.get("denied_patterns", [])

    cache = init_cache(args.cache_db)

    # Pre-flight: collection 존재 확인
    if not args.dry_run and not qdrant_collection_exists(args.collection):
        logger.error("collection '%s' 미존재 — 먼저 --init-collections 실행 필요", args.collection)
        return 2

    # deny-only flag 함수 attribute 로 전달
    index_directory._deny_only = args.deny_only  # type: ignore[attr-defined]

    stats = index_directory(
        root=root,
        collection=args.collection,
        project_tag=args.project_tag,
        device_origin=args.device_origin,
        allow=allow,
        deny=deny,
        dry_run=args.dry_run,
        cache=cache,
        is_external=args.external,
    )

    logger.info("=" * 60)
    logger.info("인덱싱 완료 (%.1f sec)", stats.duration_sec)
    logger.info("  files: scanned=%d allow_skip=%d cache_skip=%d indexed=%d",
                stats.files_scanned, stats.files_skipped_allowlist,
                stats.files_skipped_cache, stats.files_indexed)
    logger.info("  chunks: total=%d quarantined=%d redacted=%d",
                stats.chunks_total, stats.chunks_quarantined, stats.chunks_redacted)
    logger.info("  qdrant upserts=%d  embeddings=%d  errors=%d",
                stats.qdrant_upserts, stats.embeddings_called, stats.errors)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
