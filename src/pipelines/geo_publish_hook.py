"""
GEO Publish Hook — 콘텐츠 publish 후 인덱싱 가속

용도:
    HIVE MIND, blog_pipeline, SBU 자동 발행 어디서든 publish 직후 호출.
    IndexNow 일괄 ping (Bing → ChatGPT Search 분~시간 lag) + sitemap revalidate trigger.

사용:
    from src.pipelines.geo_publish_hook import notify_publish

    notify_publish([
        "https://neogenesis.app/blog/new-post",
        "https://neogenesis.app/blog/new-post/markdown",
    ])
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Iterable

logger = logging.getLogger(__name__)

# neogenesis.app 의 IndexNow key (public, 코드 포함 안전)
INDEXNOW_KEY = "68833447363a462a612e658317313cbc"
INDEXNOW_HOST = "neogenesis.app"
INDEXNOW_KEY_LOCATION = f"https://{INDEXNOW_HOST}/{INDEXNOW_KEY}.txt"

INDEXNOW_ENDPOINTS = (
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
)


def notify_indexnow(urls: list[str]) -> list[dict]:
    """
    URL 목록을 IndexNow 엔드포인트 3개에 일괄 push.
    실패해도 raise 안 함 — caller publish flow 가 IndexNow 이슈로 막히지 않게.
    """
    if not urls:
        return []
    if len(urls) > 10000:
        raise ValueError("IndexNow: 단일 요청 최대 10,000 URL")

    body = json.dumps({
        "host": INDEXNOW_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": INDEXNOW_KEY_LOCATION,
        "urlList": urls,
    }).encode("utf-8")

    results: list[dict] = []
    for endpoint in INDEXNOW_ENDPOINTS:
        try:
            req = urllib.request.Request(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                results.append({"endpoint": endpoint, "status": r.status, "ok": 200 <= r.status < 300})
        except Exception as e:  # noqa: BLE001
            logger.warning("IndexNow %s failed: %s", endpoint, e)
            results.append({"endpoint": endpoint, "status": 0, "ok": False, "error": str(e)})
    return results


def trigger_revalidate(paths: Iterable[str]) -> None:
    """
    Vercel On-Demand ISR revalidate trigger.
    환경변수 NEXT_REVALIDATE_TOKEN + REVALIDATE_ENDPOINT 설정 시 호출.
    """
    token = os.environ.get("NEXT_REVALIDATE_TOKEN")
    endpoint = os.environ.get("REVALIDATE_ENDPOINT")
    if not token or not endpoint:
        logger.info("revalidate skip: NEXT_REVALIDATE_TOKEN or REVALIDATE_ENDPOINT not set")
        return
    for path in paths:
        try:
            req = urllib.request.Request(
                f"{endpoint}?path={path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:  # noqa: BLE001
            logger.warning("revalidate %s failed: %s", path, e)


def notify_publish(urls: list[str], also_revalidate: bool = True) -> dict:
    """
    publish 후 통합 hook.
    1. IndexNow 일괄 ping (Bing/Yandex/Naver fan-out)
    2. Vercel ISR revalidate (env 설정 시)
    """
    indexnow_results = notify_indexnow(urls)
    if also_revalidate:
        # URL → path 변환 (origin 제거)
        paths = [u.replace(f"https://{INDEXNOW_HOST}", "") or "/" for u in urls]
        trigger_revalidate(paths)
    return {"indexnow": indexnow_results, "url_count": len(urls)}


if __name__ == "__main__":
    import sys

    urls = sys.argv[1:]
    if not urls:
        print("Usage: python geo_publish_hook.py <url1> [url2 ...]")
        sys.exit(1)
    print(json.dumps(notify_publish(urls), ensure_ascii=False, indent=2))
