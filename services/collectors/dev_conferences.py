"""Global Developer Conferences & Open Source Summits Collector (Confs.tech, Dev.events)."""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
import httpx

from config.targets import CONFS_TECH_CONFIG, DEV_EVENTS_CONFIG

logger = logging.getLogger("techyupdates.collectors.dev_conferences")


async def fetch_confs_tech_conferences(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch global developer conferences from confs.tech open data repositories."""
    events: List[Dict[str, Any]] = []
    current_year = datetime.now(timezone.utc).year
    years = [current_year, current_year + 1]
    topics = CONFS_TECH_CONFIG.get("topics", ["ai", "python", "javascript", "devops", "security", "rust", "golang"])

    logger.info("[Confs.tech] Ingesting conference catalogs across %d topics...", len(topics))

    for topic in topics:
        for year in years:
            url = f"{CONFS_TECH_CONFIG['base_url']}/{year}/{topic}.json"
            try:
                resp = await client.get(url, timeout=8.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for conf in data:
                            name = conf.get("name")
                            conf_url = conf.get("url")
                            if not name or not conf_url:
                                continue

                            start_date = conf.get("startDate", "")
                            end_date = conf.get("endDate", "")
                            city = conf.get("city", "")
                            country = conf.get("country", "")
                            online = conf.get("online", False)

                            location = "Global (Online)" if online and not city else f"{city}, {country}".strip(", ")
                            if not location:
                                location = "Global (Online)" if online else "See Event Website"

                            mode = "Online" if online and not city else ("Hybrid" if online and city else "In-Person")
                            cfp_url = conf.get("cfpUrl")
                            cfp_end = conf.get("cfpEndDate")
                            pricing = "CFP Open / Tickets on Site" if cfp_url else "Conference Pass / RSVP"

                            events.append({
                                "platform_or_source": f"Confs.tech ({topic.upper()})",
                                "title": name.strip(),
                                "organizer": f"{topic.capitalize()} Community",
                                "domain_track": f"{topic.upper()} & Software Engineering",
                                "mode": mode,
                                "location": location,
                                "start_date": start_date or "Upcoming",
                                "end_date": end_date or "See Event Page",
                                "registration_deadline": cfp_end or "Open Registration",
                                "date_posted": f"{year} Schedule",
                                "pricing_ticket": pricing,
                                "description": f"Global {topic} developer conference. CFP and ticket registration available.",
                                "apply_url": conf_url.strip(),
                            })
            except Exception as exc:
                logger.debug("[Confs.tech] Failed fetching %s/%s: %s", topic, year, exc)

    logger.info("[Confs.tech] Extracted %d conferences.", len(events))
    return events


async def fetch_dev_events_conferences(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch developer events and summits from dev.events public feeds."""
    events: List[Dict[str, Any]] = []
    logger.info("[Dev.events] Fetching developer summits and tech conferences...")

    try:
        url = "https://raw.githubusercontent.com/dev-events/events-data/main/events.json"
        resp = await client.get(url, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for item in data[:40]:
                    title = item.get("name") or item.get("title")
                    ev_url = item.get("url") or item.get("link")
                    if not title or not ev_url:
                        continue

                    events.append({
                        "platform_or_source": "Dev.events",
                        "title": title.strip(),
                        "organizer": item.get("organizer") or "Developer Community",
                        "domain_track": item.get("topic") or "Software Engineering & Cloud",
                        "mode": "Online" if item.get("online") else "In-Person",
                        "location": item.get("location") or "Global (Online)",
                        "start_date": item.get("startDate") or "Upcoming",
                        "end_date": item.get("endDate") or "See Page",
                        "registration_deadline": "Open Registration",
                        "date_posted": "Recently Listed",
                        "pricing_ticket": "Conference Tickets / Free Stream",
                        "description": item.get("description", "")[:250],
                        "apply_url": ev_url.strip(),
                    })
    except Exception as exc:
        logger.debug("[Dev.events] Feed query failed: %s", exc)

    logger.info("[Dev.events] Extracted %d developer events.", len(events))
    return events


async def fetch_dev_conferences(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Aggregate global developer conferences and summits."""
    confs_items = await fetch_confs_tech_conferences(client)
    dev_items = await fetch_dev_events_conferences(client)
    return confs_items + dev_items
