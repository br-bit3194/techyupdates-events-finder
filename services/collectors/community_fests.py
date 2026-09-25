"""Community Meetups, KonfHub, Commudle & Unstop Tech Festivals Collector."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import httpx

from config.targets import COMMUDLE_CONFIG, KONFHUB_CONFIG, UNSTOP_TECH_EVENTS_CONFIG

logger = logging.getLogger("techyupdates.collectors.community_fests")


async def fetch_commudle_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch developer community meetups and tech talks from Commudle."""
    events: List[Dict[str, Any]] = []
    logger.info("[Commudle] Ingesting developer community meetups and chapters...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    try:
        url = f"{COMMUDLE_CONFIG['api_url']}?page=1&limit=30"
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data") or data.get("events") or []
            for ev in items:
                title = ev.get("title") or ev.get("name")
                slug = ev.get("slug") or ev.get("id")
                if not title or not slug:
                    continue

                full_url = f"https://www.commudle.com/events/{slug}" if not str(slug).startswith("http") else slug
                community = ev.get("community", {}).get("name") or "Developer Group"
                city = ev.get("city") or ev.get("location") or "Online"
                mode = "Online" if ev.get("is_virtual") or "online" in str(city).lower() else "In-Person"

                events.append({
                    "platform_or_source": f"Commudle ({community})",
                    "title": title.strip(),
                    "organizer": community,
                    "domain_track": "Community Meetup & Tech Talks",
                    "mode": mode,
                    "location": city if mode == "In-Person" else "Global (Online)",
                    "start_date": str(ev.get("start_date", ""))[:10] or "Upcoming",
                    "end_date": str(ev.get("end_date", ""))[:10] or "See Page",
                    "registration_deadline": "Open RSVP",
                    "date_posted": "Recently Published",
                    "pricing_ticket": "Free RSVP",
                    "description": ev.get("description", "")[:250],
                    "apply_url": full_url,
                })
    except Exception as exc:
        logger.debug("[Commudle] Query failed: %s", exc)

    logger.info("[Commudle] Extracted %d community events.", len(events))
    return events


async def fetch_konfhub_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch tech events, summits, and workshops from KonfHub."""
    events: List[Dict[str, Any]] = []
    logger.info("[KonfHub] Ingesting technical conferences and summits...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    try:
        url = "https://api.konfhub.com/events/public?page=1&size=25&category=tech"
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data") or data.get("events") or []
            for ev in items:
                title = ev.get("name") or ev.get("title")
                slug = ev.get("slug") or ev.get("short_name")
                if not title or not slug:
                    continue

                full_url = f"https://konfhub.com/{slug}" if not str(slug).startswith("http") else slug
                events.append({
                    "platform_or_source": "KonfHub",
                    "title": title.strip(),
                    "organizer": ev.get("organiser_name") or "Tech Community",
                    "domain_track": "Technical Workshop & Summit",
                    "mode": "Online" if ev.get("is_online") else "In-Person",
                    "location": ev.get("venue_city") or "Global (Online)",
                    "start_date": str(ev.get("start_date", ""))[:10] or "Upcoming",
                    "end_date": str(ev.get("end_date", ""))[:10] or "See Page",
                    "registration_deadline": "Open Registration",
                    "date_posted": "Recently Added",
                    "pricing_ticket": "Free / Ticketed",
                    "description": ev.get("description", "")[:250],
                    "apply_url": full_url,
                })
    except Exception as exc:
        logger.debug("[KonfHub] Query failed: %s", exc)

    logger.info("[KonfHub] Extracted %d events.", len(events))
    return events


async def fetch_unstop_tech_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch university tech festivals, symposiums, and engineering workshops from Unstop."""
    events: List[Dict[str, Any]] = []
    logger.info("[Unstop] Ingesting college tech fests, workshops, and symposiums...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    for cat in ["workshops", "conferences", "cultural-festivals"]:
        try:
            url = f"{UNSTOP_TECH_EVENTS_CONFIG['api_url']}?opportunity={cat}&per_page=20&oppstatus=open"
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("data", []) or []
                for opp in items:
                    title = opp.get("title")
                    slug = opp.get("public_url")
                    if not title or not slug:
                        continue

                    full_url = f"https://unstop.com/{slug}" if not slug.startswith("http") else slug
                    org = opp.get("organisation", {}).get("name") or "University / Tech Club"
                    reg_end = opp.get("regnRequirements", {}).get("end_regn_dt") or ""

                    events.append({
                        "platform_or_source": f"Unstop ({cat.capitalize()})",
                        "title": title.strip(),
                        "organizer": org,
                        "domain_track": "Student Tech Fest & Engineering Workshop",
                        "mode": "Online" if opp.get("region") == "online" else "In-Person",
                        "location": opp.get("organisation", {}).get("city") or "Campus / Online",
                        "start_date": str(opp.get("start_date", ""))[:10] or "Upcoming",
                        "end_date": str(opp.get("end_date", ""))[:10] or "See Details",
                        "registration_deadline": str(reg_end)[:10] or "Open Registration",
                        "date_posted": "Recently Listed",
                        "pricing_ticket": "Free Entry / Certificates",
                        "description": opp.get("meta_details", {}).get("description", "")[:250],
                        "apply_url": full_url,
                    })
        except Exception as exc:
            logger.debug("[Unstop] Category %s query failed: %s", cat, exc)

    logger.info("[Unstop] Extracted %d tech festival and workshop events.", len(events))
    return events


async def fetch_gdg_and_devpost_events(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch GDG chapters and Devpost community tech events."""
    events: List[Dict[str, Any]] = []
    logger.info("[GDG & Devpost] Ingesting developer community tech events...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    # Devpost public upcoming tech events feed
    try:
        url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=upcoming&status[]=open"
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("hackathons", [])
            for item in items[:15]:
                title = item.get("title")
                ev_url = item.get("url")
                if not title or not ev_url:
                    continue

                events.append({
                    "platform_or_source": "Devpost Community",
                    "title": title.strip(),
                    "organizer": item.get("organization_name") or "Developer Community",
                    "domain_track": item.get("themes", [{}])[0].get("name", "Software & Cloud") if item.get("themes") else "Open Innovation",
                    "mode": "Online" if item.get("open_state") != "in_person" else "In-Person",
                    "location": "Global (Online)",
                    "start_date": str(item.get("submission_period_dates", "Upcoming")),
                    "end_date": "See Event Page",
                    "registration_deadline": "Open Registration",
                    "date_posted": "Recently Listed",
                    "pricing_ticket": "Free (Swag & Prizes)",
                    "description": item.get("analytics_identifier", "Developer challenge and technical sprint."),
                    "apply_url": ev_url.strip(),
                })
    except Exception as exc:
        logger.debug("[Devpost Community] Query failed: %s", exc)

    logger.info("[GDG & Devpost] Extracted %d community opportunities.", len(events))
    return events


async def fetch_community_fests_and_meetups(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Aggregate all community meetups, KonfHub, Devpost, and Unstop tech festivals."""
    commudle_items = await fetch_commudle_events(client)
    konfhub_items = await fetch_konfhub_events(client)
    unstop_items = await fetch_unstop_tech_events(client)
    devpost_items = await fetch_gdg_and_devpost_events(client)
    return commudle_items + konfhub_items + unstop_items + devpost_items

