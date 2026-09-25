"""Lu.ma & Eventbrite Tech Events and Developer Meetups Collector."""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import quote_plus
import httpx

from config.targets import LUMA_CONFIG, EVENTBRITE_CONFIG

logger = logging.getLogger("techyupdates.collectors.luma_eventbrite")


async def fetch_luma_tech_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch developer, AI, Web3, and startup demo day events from Lu.ma."""
    events: List[Dict[str, Any]] = []
    logger.info("[Lu.ma] Scraping developer events, meetups, and demo days...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://lu.ma/explore",
    }

    # Query Luma's public calendar and discovery endpoints
    calendar_slugs = ["sf-ai", "ai-engineers", "genai", "bay-area-ai", "bengaluru-tech", "tech-meetups", "web3-builders"]
    
    for slug in calendar_slugs:
        try:
            url = f"https://api.lu.ma/public/v1/calendar/get-items?calendar_slug={slug}"
            resp = await client.get(url, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("entries") or data.get("items") or []
                for item in items:
                    ev_data = item.get("event", item)
                    name = ev_data.get("name") or ev_data.get("title")
                    ev_url = ev_data.get("url") or ev_data.get("slug")
                    if not name or not ev_url:
                        continue
                    full_url = f"https://lu.ma/{ev_url}" if not str(ev_url).startswith("http") else str(ev_url)
                    start_at = ev_data.get("start_at") or ""
                    geo = ev_data.get("geo_address_info") or {}
                    city = geo.get("city") or "Online / Bay Area"

                    events.append({
                        "platform_or_source": f"Lu.ma ({slug})",
                        "title": name.strip(),
                        "organizer": ev_data.get("organizer", {}).get("name") or f"{slug.replace('-', ' ').title()}",
                        "domain_track": "AI, Generative Agents & Developer Community",
                        "mode": "Online" if "online" in str(city).lower() else "In-Person",
                        "location": str(city),
                        "start_date": str(start_at)[:10] if len(str(start_at)) >= 10 else "Upcoming",
                        "end_date": "See Event Page",
                        "registration_deadline": "Open RSVP",
                        "date_posted": "Recently Added",
                        "pricing_ticket": "Free RSVP",
                        "description": ev_data.get("description", "")[:250],
                        "apply_url": full_url,
                    })
        except Exception as exc:
            logger.debug("[Lu.ma] Slug %s query failed: %s", slug, exc)


    logger.info("[Lu.ma] Extracted %d live events.", len(events))
    return events


async def fetch_eventbrite_tech_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch developer workshops, technical conferences, and AI summits from Eventbrite feeds."""
    events: List[Dict[str, Any]] = []
    logger.info("[Eventbrite] Ingesting technology and developer meetup listings...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    search_urls = [
        "https://www.eventbrite.com/d/online/science-and-tech--events/developer/",
        "https://www.eventbrite.com/d/online/science-and-tech--events/artificial-intelligence/",
    ]

    for url in search_urls:
        try:
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                html = resp.text
                # Parse structured JSON-LD or search result cards
                json_ld_matches = re.findall(r'<script type="application/ld\+json">({.*?})</script>', html, re.DOTALL)
                for match in json_ld_matches:
                    try:
                        import json
                        data = json.loads(match)
                        if data.get("@type") == "Event" or (isinstance(data.get("itemListElement"), list)):
                            items = data.get("itemListElement") or [data]
                            for it in items:
                                ev_obj = it.get("item", it) if isinstance(it, dict) else {}
                                title = ev_obj.get("name")
                                ev_url = ev_obj.get("url")
                                if title and ev_url:
                                    events.append({
                                        "platform_or_source": "Eventbrite",
                                        "title": title.strip(),
                                        "organizer": ev_obj.get("organizer", {}).get("name") or "Tech Community",
                                        "domain_track": "Developer Workshop & Technology",
                                        "mode": "Online",
                                        "location": "Global (Online)",
                                        "start_date": str(ev_obj.get("startDate", ""))[:10] or "Upcoming",
                                        "end_date": str(ev_obj.get("endDate", ""))[:10] or "See Event Page",
                                        "registration_deadline": "Open Registration",
                                        "date_posted": "Recently Listed",
                                        "pricing_ticket": "Free / Ticketed",
                                        "description": ev_obj.get("description", "")[:250],
                                        "apply_url": ev_url.split("?")[0],
                                    })
                    except Exception:
                        continue
        except Exception as exc:
            logger.debug("[Eventbrite] Feed query failed (%s): %s", url, exc)

    logger.info("[Eventbrite] Extracted %d live events.", len(events))
    return events


async def fetch_luma_eventbrite_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Aggregate all Lu.ma and Eventbrite tech opportunities."""
    luma_items = await fetch_luma_tech_events(client)
    eventbrite_items = await fetch_eventbrite_tech_events(client)
    return luma_items + eventbrite_items
