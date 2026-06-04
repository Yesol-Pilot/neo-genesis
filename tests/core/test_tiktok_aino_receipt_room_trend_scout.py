from src.core.tiktok_aino import receipt_room_trend_scout as scout


RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Taylor Swift and Travis Kelce Red Carpet Moment Has Fans Asking What Happened</title>
      <link>https://people.com/example</link>
      <description>Fans are debating the body language after a public appearance.</description>
      <pubDate>Thu, 14 May 2026 02:00:00 GMT</pubDate>
      <source url="https://people.com">People</source>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_maps_source_alias() -> None:
    strategy = scout._strategy()

    items = scout._parse_rss(RSS_SAMPLE, "Google News", "google_news", strategy, query="celebrity")

    assert len(items) == 1
    assert items[0].source_id == "people"
    assert "Taylor Swift" in items[0].title


def test_item_to_candidate_extracts_signals_and_entities() -> None:
    strategy = scout._strategy()
    item = scout._parse_rss(RSS_SAMPLE, "Google News", "google_news", strategy, query="celebrity")[0]

    candidate = scout.item_to_candidate(item, strategy)
    plan = scout.planner.plan_episode(candidate, strategy)

    assert "Taylor Swift" in candidate.entities
    assert candidate.trend_signals["visual_drama"] >= 50
    assert plan["decision"] in {"greenlight", "revise"}
    assert plan["roast_gate"]["passed"]


def test_discover_and_plan_uses_fetch_results(monkeypatch) -> None:
    strategy = scout._strategy()
    item = scout._parse_rss(RSS_SAMPLE, "Google News", "google_news", strategy, query="celebrity")[0]

    monkeypatch.setattr(scout, "fetch_feed_items", lambda _strategy: ([item], []))

    result = scout.discover_and_plan(limit=1, strategy=strategy, allow_network_research=True)

    assert result.selected_count == 1
    assert result.plans[0]["episode_title"].startswith("Taylor Swift")
    assert result.plans[0]["scout_source"]["source_id"] == "people"


def test_local_only_blocks_network_research_by_default(monkeypatch) -> None:
    strategy = scout._strategy()
    called = False

    def _fail_if_called(_strategy):
        nonlocal called
        called = True
        return ([], [])

    monkeypatch.setattr(scout, "fetch_feed_items", _fail_if_called)

    result = scout.discover_and_plan(limit=1, strategy=strategy)

    assert not called
    assert result.selected_count == 0
    assert "network_research_blocked_by_local_only_privacy_mode" in result.errors
