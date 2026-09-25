"""Call for Papers (CFP) & Speaker Submissions Radar (Sessionize, PaperCall)."""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
import httpx


logger = logging.getLogger("techyupdates.collectors.cfp_radar")


async def fetch_cfp_opportunities(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Ingest open Call for Papers (CFP) for global tech conferences & summits."""
    events: List[Dict[str, Any]] = []
    logger.info("[CFP Radar] Ingesting open speaker Call for Papers (CFP)...")

    topics = ["python", "javascript", "devops", "security", "data", "rust"]
    year = datetime.now(timezone.utc).year

    for topic in topics:
        url = f"https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences/{year}/{topic}.json"
        try:
            resp = await client.get(url, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        cfp_url = item.get("cfpUrl")
                        name = item.get("name")
                        if not name or not cfp_url:
                            continue

                        events.append({
                            "platform_or_source": f"CFP Radar ({topic.upper()})",
                            "title": f"{name.strip()} - Call for Speakers",
                            "organizer": item.get("organizer") or f"{topic.capitalize()} Conference Committee",
                            "domain_track": f"{topic.upper()} & Software Architecture",
                            "mode": "Online" if item.get("online") else "In-Person",
                            "location": item.get("city") or "Global",
                            "start_date": item.get("startDate", "Upcoming"),
                            "end_date": item.get("endDate", "See Page"),
                            "registration_deadline": item.get("cfpEndDate", "CFP Open"),
                            "date_posted": "Call for Papers Open",
                            "pricing_ticket": "Free (Speaker Pass & Travel Grants)",
                            "description": f"Submit talk proposals for {name}. Gain global speaker stage exposure and travel support.",
                            "apply_url": cfp_url.strip(),
                        })
        except Exception as exc:
            logger.debug("[CFP Radar] Query failed for %s: %s", url, exc)

    logger.info("[CFP Radar] Extracted %d open CFPs.", len(events))
    return events

