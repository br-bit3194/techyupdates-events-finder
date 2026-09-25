"""Unit tests for HistoryTracker, normalization, canonicalization, and TTL cleanup."""

import os
import json
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from services.history_tracker import (
    HistoryTracker,
    normalize_title,
    canonicalize_url,
)


def test_normalize_title():
    """Verify title normalization removes emojis, punctuation, and extra whitespace."""
    raw = "🔥  Google I/O Extended 2026: AI & Cloud Edition!!  🚀"
    norm = normalize_title(raw)
    assert norm == "google io extended 2026 ai cloud edition"

    assert normalize_title("") == ""
    assert normalize_title("   KubeCon   +   CloudNativeCon   ") == "kubecon cloudnativecon"


def test_canonicalize_url():
    """Verify URL canonicalization strips UTM, tracking queries, trailing slashes, and fragments."""
    url = "https://lu.ma/ai-summit-2026/?utm_source=twitter&utm_medium=social&ref=newsletter#overview"
    canon = canonicalize_url(url)
    assert canon == "https://lu.ma/ai-summit-2026"

    # Preserves essential queries while stripping tracking params
    url2 = "https://events.example.com/conf?id=42&utm_campaign=spring"
    canon2 = canonicalize_url(url2)
    assert canon2 == "https://events.example.com/conf?id=42"


def test_history_tracker_dual_key_deduplication():
    """Verify HistoryTracker matches against both canonical URL and normalized title."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "sent_history.json")
        tracker = HistoryTracker(file_path=history_path, ttl_days=30)

        assert not tracker.is_already_sent("PyCon India 2026", "https://in.pycon.org/2026")

        # Record event
        tracker.record_sent_event(
            title="PyCon India 2026",
            url="https://in.pycon.org/2026/?utm_source=telegram",
            category="Developer & Open Source Confs",
            platform="Python Community",
        )
        tracker.save()

        # Check exact url
        assert tracker.is_already_sent("PyCon India 2026", "https://in.pycon.org/2026")
        # Check URL with different UTM
        assert tracker.is_already_sent("PyCon India 2026", "https://in.pycon.org/2026/?utm_medium=email")
        # Check matching normalized title even with different URL
        assert tracker.is_already_sent("🐍 PyCon India 2026!!", "https://other-url.com")
        # Check different event
        assert not tracker.is_already_sent("JSConf India 2026", "https://jsconf.in")


def test_history_tracker_auto_ttl_cleanup():
    """Verify expired entries older than 30 days are automatically pruned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "sent_history.json")

        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=35)).isoformat()
        recent_date = (now - timedelta(days=5)).isoformat()

        initial_data = {
            "https://old-conf.com": {
                "title": "Old Conf 2025",
                "normalized_title": "old conf 2025",
                "canonical_url": "https://old-conf.com",
                "sent_at": old_date,
            },
            "https://recent-conf.com": {
                "title": "Recent Conf 2026",
                "normalized_title": "recent conf 2026",
                "canonical_url": "https://recent-conf.com",
                "sent_at": recent_date,
            },
        }

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        tracker = HistoryTracker(file_path=history_path, ttl_days=30)

        # Old conf should be purged, recent conf should remain
        assert not tracker.is_already_sent("Old Conf 2025", "https://old-conf.com")
        assert tracker.is_already_sent("Recent Conf 2026", "https://recent-conf.com")
        assert len(tracker.history) == 1


def test_history_tracker_record_batch():
    """Verify batch recording and disk persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "sent_history.json")
        tracker = HistoryTracker(file_path=history_path)

        events = [
            {"title": "Event Alpha", "url": "https://alpha.org/event", "category": "AI"},
            {"title": "Event Beta", "url": "https://beta.org/event", "category": "Web3"},
        ]
        count = tracker.record_batch_sent(events)
        assert count == 2

        # Verify disk contents
        with open(history_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved) == 2
        assert "https://alpha.org/event" in saved

        # Verify stats
        stats = tracker.get_stats()
        assert stats["total_tracked"] == 2
        assert stats["ttl_days"] == 30


def test_history_tracker_corrupted_file_resilience():
    """Verify tracker gracefully initializes when encountering corrupted or invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "corrupted.json")
        with open(history_path, "w", encoding="utf-8") as f:
            f.write("invalid json content {{{")

        tracker = HistoryTracker(file_path=history_path)
        assert tracker.history == {}
        assert tracker.get_stats()["total_tracked"] == 0

