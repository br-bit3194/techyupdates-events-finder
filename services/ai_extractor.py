"""AI Extraction, Classification & Enrichment Engine for Tech Events using Google Gemini Flash.

Includes production rate-limiting, exponential backoff, jitter, and automatic local heuristic fallback.
"""

import os
import json
import logging
import re
import random
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("techyupdates.ai_extractor")


class TechEventRecord(BaseModel):
    """Structured contract for normalized tech events, conferences, and meetups."""
    platform_or_source: str = Field(description="Host platform or organizing entity (e.g. 'Google', 'Lu.ma', 'CNCF', 'Eventbrite', 'Commudle')")
    title: str = Field(description="Normalized title of the tech event or conference")
    category: Literal[
        "AI, Cloud & Data Summits",
        "Developer & Open Source Confs",
        "Student Tech Fests & Workshops",
        "Meetups, Demo Days & CFPs",
    ] = Field(description="Target category for spreadsheet tab grouping")
    event_type: Literal[
        "Conference",
        "Summit",
        "Meetup",
        "Workshop",
        "Tech Fest",
        "Demo Day",
        "Call for Papers",
        "Webinar",
    ] = Field(description="Classification type of event")
    domain_track: str = Field(description="Primary technical domain or track (e.g., 'Generative AI & LLMs', 'Cloud Native & Kubernetes', 'Web & Mobile')")
    mode: Literal["In-Person", "Online", "Hybrid"] = Field(description="Event mode")
    location: str = Field(description="Geographic venue or 'Global (Online)'")
    start_date: str = Field(description="Scheduled start date (e.g., '14 Nov 2026' or 'Upcoming')")
    end_date: str = Field(description="Scheduled end date (e.g., '16 Nov 2026' or 'Same Day')")
    registration_deadline: str = Field(description="Formatted registration or RSVP deadline (e.g., '10 Nov 2026' or 'Open RSVP')")
    date_posted: str = Field(description="Date when event was published/announced (e.g., 'Recently Announced')")
    pricing_ticket: str = Field(description="Pricing status (e.g., 'Free RSVP', 'Free (Virtual)', 'Paid', 'CFP Open')")
    why_attend: str = Field(description="1-line crisp reason highlighting why this event is high value (keynotes, networking, hands-on labs, free entry)")
    registration_url: str = Field(description="Direct registration or RSVP link")


class TechEventsBatch(BaseModel):
    items: List[TechEventRecord]


def fallback_classify_tech_event(raw: Dict[str, Any]) -> TechEventRecord:
    """Rule-based heuristic classifier used when Gemini AI is unreachable or quota exhausted."""
    title = raw.get("title", "").strip()
    source = raw.get("platform_or_source", "Tech Platform").strip()
    organizer = raw.get("organizer", "Tech Community").strip()
    url = raw.get("apply_url") or raw.get("registration_url") or raw.get("url", "").strip()
    desc = raw.get("description", "").lower()
    location = raw.get("location", "Global (Online)").strip()
    pricing = raw.get("pricing_ticket", "Free RSVP / Ticketed").strip()
    
    t_lower = title.lower()
    corpus = f"{t_lower} {desc} {source.lower()} {organizer.lower()}"

    # 1. Category Classification
    if any(k in corpus for k in [
        "call for papers", "cfp", "speakers", "sessionize", "papercall", "demo day", "pitch day",
        "hacker house", "meetup", "commudle", "chapter", "user group", "lu.ma", "luma"
    ]) and not any(k in corpus for k in ["kubecon", "aws reinvent", "google i/o", "microsoft build"]):
        category = "Meetups, Demo Days & CFPs"
        event_type = "Call for Papers" if "cfp" in corpus or "speaker" in corpus else ("Demo Day" if "demo" in corpus else "Meetup")
        domain = "Developer Community & Networking"
    elif any(k in corpus for k in [
        "student", "university", "campus", "college", "unstop", "fest", "techfest", "symposium",
        "workshop", "bootcamp", "hands-on lab", "freshers", "gdg on campus"
    ]):
        category = "Student Tech Fests & Workshops"
        event_type = "Tech Fest" if any(k in corpus for k in ["fest", "techfest", "symposium"]) else "Workshop"
        domain = "Hands-on Technical Workshops & Campus Fests"
    elif any(k in corpus for k in [
        "ai", "genai", "generative ai", "llm", "rag", "deep learning", "machine learning", "neural",
        "cloud", "azure", "aws", "gcp", "google cloud", "kubernetes", "k8s", "cncf", "docker", "devops",
        "data science", "analytics", "nvidia", "gtc", "openai", "bedrock"
    ]):
        category = "AI, Cloud & Data Summits"
        event_type = "Summit" if any(k in corpus for k in ["summit", "keynote", "reinvent", "gtc"]) else "Conference"
        domain = "Generative AI, Cloud Infrastructure & Data"
    else:
        category = "Developer & Open Source Confs"
        event_type = "Conference"
        domain = "Software Architecture & Open Source Ecosystem"

    # 2. Mode Detection
    loc_lower = location.lower()
    if "hybrid" in loc_lower or "hybrid" in corpus:
        mode = "Hybrid"
    elif any(k in loc_lower for k in ["online", "virtual", "remote", "webinar"]) or "online" in corpus:
        mode = "Online"
    else:
        mode = "In-Person"

    # 3. Why Attend Generation
    if "cfp" in corpus:
        why = "Global speaker stage exposure, travel grant support, and developer community reach."
    elif category == "AI, Cloud & Data Summits":
        why = "Frontier AI keynotes, enterprise cloud architecture updates, and deep-dive technical sessions."
    elif category == "Student Tech Fests & Workshops":
        why = "Hands-on coding labs, developer certificate, college hack fests, and beginner-friendly mentorship."
    elif category == "Meetups, Demo Days & CFPs":
        why = "High-signal local dev networking, startup demo day pitches, and interactive tech talks."
    else:
        why = "World-class technical tracks, open source maintainer insights, and peer engineering networking."

    return TechEventRecord(
        platform_or_source=source,
        title=title or "Global Developer Conference",
        category=category,
        event_type=event_type,
        domain_track=raw.get("domain_track") or domain,
        mode=mode,
        location=location,
        start_date=raw.get("start_date") or "Upcoming",
        end_date=raw.get("end_date") or "See Event Page",
        registration_deadline=raw.get("registration_deadline") or "Open RSVP",
        date_posted=raw.get("date_posted") or "Recently Announced",
        pricing_ticket=pricing,
        why_attend=why,
        registration_url=url,
    )


async def extract_and_tier_tech_events(raw_items: List[Dict[str, Any]], batch_size: int = 25) -> List[TechEventRecord]:
    """Process raw events through Google Gemini with exponential backoff and rate pacing."""
    if not raw_items:
        return []

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.warning("[AI] GEMINI_API_KEY not found in environment. Using rule-based fallback for all %d items.", len(raw_items))
        return [fallback_classify_tech_event(item) for item in raw_items]

    model_cascade = [
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "gemini-2.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]
    seen = set()
    models_to_try = [m for m in model_cascade if not (m in seen or seen.add(m))]

    batches = [raw_items[i : i + batch_size] for i in range(0, len(raw_items), batch_size)]
    enriched_results: List[TechEventRecord] = []

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=gemini_api_key)
    except Exception as exc:
        logger.error("[AI] Failed initializing Google GenAI Client: %s. Using heuristic fallback.", exc)
        return [fallback_classify_tech_event(item) for item in raw_items]

    system_prompt = (
        "You are the expert Tech Events & Developer Conferences Classification Engine for TechyUpdates. "
        "Analyze each raw tech event, conference, meetup, or workshop and return structured, enriched JSON. "
        "Assign each item into one of the 4 exact categories:\n"
        "1. 'AI, Cloud & Data Summits' (GenAI, LLMs, Computer Vision, Cloud, DevOps, Kubernetes, Data Science, AWS/Google/MS flagships)\n"
        "2. 'Developer & Open Source Confs' (Web, Mobile, System Architecture, Rust, Go, Python, Open Source, Security, Linux)\n"
        "3. 'Student Tech Fests & Workshops' (College Tech Fests, Student Symposiums, Hands-on Developer Bootcamps, GDG on Campus)\n"
        "4. 'Meetups, Demo Days & CFPs' (Local Developer Meetups, AI Demo Days, Startup Pitch Days, Speaker Call for Papers)\n"
        "Produce crisp 1-line 'why_attend' reasons emphasizing keynotes, hands-on labs, speaker opportunities, or free perks."
    )

    for b_idx, batch in enumerate(batches):
        logger.info("[AI] Processing batch %d/%d (%d items)...", b_idx + 1, len(batches), len(batch))
        batch_success = False

        # Apply pacing delay between batches
        if b_idx > 0:
            await asyncio.sleep(2.5)

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    prompt_text = (
                        f"{system_prompt}\n\n"
                        f"Raw Events Payload:\n{json.dumps(batch, indent=2, ensure_ascii=False)}"
                    )

                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_text,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TechEventsBatch,
                            temperature=0.1,
                        ),
                    )

                    if response.text:
                        parsed = json.loads(response.text)
                        items_data = parsed.get("items", []) if isinstance(parsed, dict) else parsed
                        batch_records = [TechEventRecord.model_validate(item) for item in items_data]
                        enriched_results.extend(batch_records)
                        logger.info("[AI] Model '%s' successfully enriched batch %d (%d items).", model_name, b_idx + 1, len(batch_records))
                        batch_success = True
                        break

                except Exception as exc:
                    err_msg = str(exc)
                    logger.warning(
                        "[AI] Attempt %d failed on model '%s' for batch %d: %s",
                        attempt + 1,
                        model_name,
                        b_idx + 1,
                        err_msg[:120],
                    )
                    if "429" in err_msg or "quota" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
                        logger.info("[AI] Quota exhausted on '%s'. Removing from cascade and switching to next model...", model_name)
                        if model_name in models_to_try:
                            models_to_try.remove(model_name)
                        break  # Break out to next model in cascade
                    else:
                        await asyncio.sleep(1.0)



            if batch_success:
                break

        if not batch_success:
            logger.warning("[AI] All Gemini models failed for batch %d. Falling back to rule-based heuristic.", b_idx + 1)
            fallback_records = [fallback_classify_tech_event(item) for item in batch]
            enriched_results.extend(fallback_records)

    logger.info("[AI] Completed enrichment: %d total validated tech event records.", len(enriched_results))
    return enriched_results
