"""Telegram Channel Notifier & Document Dispatcher for Tech Events Finder."""

import io
import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from dotenv import load_dotenv

from services.ai_extractor import TechEventRecord

load_dotenv()

logger = logging.getLogger("techyupdates.telegram_notifier")


def generate_telegram_caption(records: List[TechEventRecord]) -> str:
    """Generate high-converting, clean Markdown caption for Telegram channel broadcast."""
    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    total_count = len(records)
    channel_handle = os.getenv("TELEGRAM_COMMUNITY_CHANNEL_ID") or os.getenv("TELEGRAM_CHANNEL_ID", "@techy_events_updates")

    # Count by category
    ai_count = sum(1 for r in records if r.category == "AI, Cloud & Data Summits")
    dev_count = sum(1 for r in records if r.category == "Developer & Open Source Confs")
    student_count = sum(1 for r in records if r.category == "Student Tech Fests & Workshops")
    meetup_count = sum(1 for r in records if r.category == "Meetups, Demo Days & CFPs")

    # Pick top spotlight items
    ai_spotlight = next((r for r in records if r.category == "AI, Cloud & Data Summits"), None)
    dev_spotlight = next((r for r in records if r.category == "Developer & Open Source Confs"), None)
    student_spotlight = next((r for r in records if r.category == "Student Tech Fests & Workshops"), None)
    meetup_spotlight = next((r for r in records if r.category == "Meetups, Demo Days & CFPs"), None)

    caption_lines = [
        f"🌐 *TechyUpdates Tech Events & Conferences Drop* | `{today_str}`",
        f"🔥 Scored & Curated `{total_count}` Verified Developer Gatherings & Summits",
        "",
        "📊 *Category Breakdown:*",
        f"• 🔮 *AI, Cloud & Data Summits:* `{ai_count}` events",
        f"• ⚡ *Developer & Open Source Confs:* `{dev_count}` events",
        f"• 🎓 *Student Tech Fests & Workshops:* `{student_count}` events",
        f"• 🚀 *Meetups, Demo Days & CFPs:* `{meetup_count}` events",
        "",
        "🌟 *Featured Opportunities Today:*",
    ]

    spotlights = [
        ("🔮 AI/Cloud", ai_spotlight),
        ("⚡ Dev Conf", dev_spotlight),
        ("🎓 Student Fest", student_spotlight),
        ("🚀 Meetup/CFP", meetup_spotlight),
    ]

    for label, item in spotlights:
        if item:
            mode_badge = f"[{item.mode}]"
            loc = item.location[:25]
            caption_lines.append(f"• *{label}:* [{item.title[:35]}]({item.registration_url}) {mode_badge} ({loc})")

    caption_lines.extend([
        "",
        "📁 *Attached Workbook:* Complete 4-tab spreadsheet with direct registration links, deadlines, speaker CFPs, and tracks.",
        "",
        f"📢 *Channel:* {channel_handle} | *Automated Daily Radar*",
    ])

    return "\n".join(caption_lines)


async def dispatch_telegram_document(
    excel_bytes: bytes,
    records: List[TechEventRecord],
    custom_filename: Optional[str] = None,
) -> bool:
    """Send generated Excel spreadsheet and formatted caption to configured Telegram channel."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_COMMUNITY_CHANNEL_ID") or os.getenv("TELEGRAM_CHANNEL_ID", "@techy_events_updates")

    if not bot_token:
        logger.warning("[Telegram] TELEGRAM_BOT_TOKEN not configured. Skipping Telegram broadcast (Dry Run).")
        return False

    if not channel_id:
        logger.warning("[Telegram] TELEGRAM_COMMUNITY_CHANNEL_ID not configured. Skipping broadcast.")
        return False

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = custom_filename or f"TechyUpdates_TechEvents_{today_str}.xlsx"
    caption = generate_telegram_caption(records)

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    # Telegram sendDocument with multipart/form-data
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {
                    "document": (filename, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                }
                data = {
                    "chat_id": channel_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": "true",
                }

                resp = await client.post(url, data=data, files=files)
                if resp.status_code == 200:
                    logger.info("[Telegram] Successfully broadcasted %s to %s", filename, channel_id)
                    return True
                else:
                    logger.warning("[Telegram] Attempt %d failed with status %d: %s", attempt + 1, resp.status_code, resp.text)
                    await asyncio.sleep(2.0 * (attempt + 1))
        except Exception as exc:
            logger.error("[Telegram] Error sending document on attempt %d: %s", attempt + 1, exc)
            await asyncio.sleep(2.0 * (attempt + 1))

    return False
