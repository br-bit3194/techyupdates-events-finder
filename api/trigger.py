"""Orchestration Engine & Serverless Entrypoint for TechyUpdates Tech Events Finder."""

import io
import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List
import httpx
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from services.collectors.luma_eventbrite import fetch_luma_eventbrite_events
from services.collectors.dev_conferences import fetch_dev_conferences
from services.collectors.community_fests import fetch_community_fests_and_meetups
from services.collectors.flagship_summits import fetch_flagship_enterprise_summits
from services.collectors.cfp_radar import fetch_cfp_opportunities
from services.collectors.liveness_verifier import (
    generate_dedup_hash,
    is_scam_or_blacklisted,
    is_valid_event_url,
    verify_tech_events_liveness,
)
from services.history_tracker import HistoryTracker
from services.ai_extractor import extract_and_tier_tech_events, TechEventRecord
from services.excel_builder import build_excel_workbook
from services.telegram_notifier import dispatch_telegram_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("techyupdates.pipeline")


async def run_pipeline() -> Dict[str, Any]:
    """Execute the end-to-end TechyUpdates Tech Events ingestion and broadcast pipeline."""
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 80)
    logger.info("🌐 [TECHYUPDATES TECH EVENTS RADAR] Starting Autonomous Pipeline @ %s", start_time.isoformat())
    logger.info("=" * 80)

    # -------------------------------------------------------------------------
    # PHASE 1: Asynchronous Platform Ingestion
    # -------------------------------------------------------------------------
    logger.info("[PHASE 1/5: INGESTION] Launching 5 asynchronous platform collectors...")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        collector_tasks = [
            ("Luma & Eventbrite", asyncio.create_task(fetch_luma_eventbrite_events(client))),
            ("Dev Conferences & Confs.tech", asyncio.create_task(fetch_dev_conferences(client))),
            ("Community Fests & Unstop", asyncio.create_task(fetch_community_fests_and_meetups(client))),
            ("Flagship Enterprise Summits", asyncio.create_task(fetch_flagship_enterprise_summits(client))),
            ("CFP Radar", asyncio.create_task(fetch_cfp_opportunities(client))),
        ]

        raw_events: List[Dict[str, Any]] = []
        source_counts: Dict[str, int] = {}

        for name, task in collector_tasks:
            try:
                results = await task
                raw_events.extend(results)
                source_counts[name] = len(results)
                logger.info("  ✓ [%s] Ingested %d raw events", name, len(results))
            except Exception as exc:
                logger.error("  ✗ [%s] Collector error: %s", name, exc)
                source_counts[name] = 0

    logger.info("[PHASE 1 COMPLETE] Ingested %d total raw events across %d sources.", len(raw_events), len(collector_tasks))

    # -------------------------------------------------------------------------
    # PHASE 2: Cross-Day Persistent Deduplication & History Filtering
    # -------------------------------------------------------------------------
    logger.info("[PHASE 2/5: DEDUPLICATION] Initializing HistoryTracker & in-run deduplicator...")
    tracker = HistoryTracker()
    history_stats = tracker.get_stats()
    logger.info("  • Historical entries in persistent store: %d", history_stats["total_tracked"])

    seen_hashes = set()
    deduped_candidates: List[Dict[str, Any]] = []
    skipped_history_count = 0

    for ev in raw_events:
        title = ev.get("title", "")
        url = ev.get("apply_url") or ev.get("registration_url") or ev.get("url") or ""

        if not title or not url or not is_valid_event_url(url):
            continue

        # Check cross-day persistent history
        if tracker.is_already_sent(title, url):
            skipped_history_count += 1
            continue

        # In-run dedup hash
        h = generate_dedup_hash(title, url)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        deduped_candidates.append(ev)

    logger.info(
        "[PHASE 2 COMPLETE] Candidates: %d (Skipped %d duplicates from 30-day persistent history).",
        len(deduped_candidates),
        skipped_history_count,
    )

    # -------------------------------------------------------------------------
    # PHASE 3: Strict Active Liveness & Soft-404 Probing
    # -------------------------------------------------------------------------
    logger.info("[PHASE 3/5: LIVENESS] Running active HTTP & soft-404 anti-error verification...")
    verified_events = await verify_tech_events_liveness(deduped_candidates)
    logger.info("[PHASE 3 COMPLETE] Live & valid events retained: %d", len(verified_events))

    if not verified_events:
        logger.warning("[PIPELINE WARNING] No fresh, un-broadcasted live events found for today.")
        return {
            "status": "success",
            "message": "No new live events after deduplication and liveness verification.",
            "raw_ingested": len(raw_events),
            "history_skipped": skipped_history_count,
            "verified_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -------------------------------------------------------------------------
    # PHASE 4: AI Extraction, Domain Categorization & Pacing
    # -------------------------------------------------------------------------
    logger.info("[PHASE 4/5: AI CATEGORIZATION] Enriching %d events via Gemini Flash with rate pacing...", len(verified_events))
    classified_records: List[TechEventRecord] = await extract_and_tier_tech_events(verified_events)
    logger.info("[PHASE 4 COMPLETE] Enriched & classified %d records across 4 categories.", len(classified_records))

    # -------------------------------------------------------------------------
    # PHASE 5: In-Memory Excel Compilation & Telegram Broadcast
    # -------------------------------------------------------------------------
    logger.info("[PHASE 5/5: OUTPUT] Building 4-tab styled Excel workbook and broadcasting...")
    excel_bytes = build_excel_workbook(classified_records)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    excel_filename = f"TechyUpdates_TechEvents_{today_str}.xlsx"

    # Broadcast via Telegram
    telegram_success = await dispatch_telegram_document(excel_bytes, classified_records, excel_filename)

    # Record newly sent events to persistent history store
    newly_recorded = tracker.record_batch_sent([
        {
            "title": r.title,
            "url": r.registration_url,
            "category": r.category,
            "platform_or_source": r.platform_or_source,
            "event_type": r.event_type,
        }
        for r in classified_records
    ])

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("=" * 80)
    logger.info(
        "✨ [PIPELINE SUCCESS] Processed %d events in %.2fs | Excel: %d bytes | Telegram: %s | Saved to History: %d",
        len(classified_records),
        elapsed,
        len(excel_bytes),
        "DISPATCHED" if telegram_success else "SKIPPED/DRY_RUN",
        newly_recorded,
    )
    logger.info("=" * 80)

    return {
        "status": "success",
        "raw_ingested": len(raw_events),
        "history_skipped": skipped_history_count,
        "verified_count": len(verified_events),
        "classified_count": len(classified_records),
        "excel_size_bytes": len(excel_bytes),
        "telegram_dispatched": telegram_success,
        "history_newly_recorded": newly_recorded,
        "elapsed_seconds": round(elapsed, 2),
        "source_breakdown": source_counts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function & Webhook trigger."""

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        # Basic security verification if CRON_SECRET is set
        cron_secret = os.getenv("CRON_SECRET")
        auth_header = self.headers.get("Authorization", "")
        token_param = qs.get("secret", [None])[0]

        if cron_secret:
            is_authorized = (
                auth_header == f"Bearer {cron_secret}"
                or token_param == cron_secret
            )
            if not is_authorized:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

        # Run pipeline
        try:
            result = asyncio.run(run_pipeline())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode("utf-8"))
        except Exception as exc:
            logger.error("[API] Unhandled pipeline error: %s", exc, exc_info=True)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(exc)}).encode("utf-8"))

    def do_POST(self):
        return self.do_GET()


if __name__ == "__main__":
    result = asyncio.run(run_pipeline())
    print("\n--- Pipeline Execution Summary ---")
    print(json.dumps(result, indent=2))
