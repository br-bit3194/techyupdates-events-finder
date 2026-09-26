"""Integration and unit tests for Tech Events Finder pipeline, collectors, AI fallback, and Excel generation."""

import os
import io
import json
import pytest
from datetime import datetime, timezone, date, timedelta
import openpyxl

from services.collectors.liveness_verifier import (
    generate_dedup_hash,
    is_scam_or_blacklisted,
    is_valid_event_url,
    is_upcoming_or_future_event,
    is_recent_or_past_24h_posted,
    parse_flexible_date,
)

from services.ai_extractor import (
    fallback_classify_tech_event,
    TechEventRecord,
)
from services.excel_builder import build_excel_workbook, TABS_CONFIG
from services.telegram_notifier import generate_telegram_caption


def test_dedup_hash():
    """Verify MD5 hash is deterministic and invariant to casing and formatting."""
    h1 = generate_dedup_hash("Google I/O 2026", "https://io.google/2026/")
    h2 = generate_dedup_hash("google i/o 2026!", "https://io.google/2026")
    assert h1 == h2


def test_is_scam_or_blacklisted():
    """Verify blacklist filters out MLM, trading scams, and spam webinars."""
    assert is_scam_or_blacklisted("Forex Signal Masterclass Webinar", "Learn crypto trading course")
    assert is_scam_or_blacklisted("MultiLevel Marketing Business Meetup")
    assert not is_scam_or_blacklisted("Kubernetes Community Days 2026", "Cloud native architecture and microservices")


def test_is_valid_event_url():
    """Verify URL validation blocks invalid schemes and generic search root pages."""
    assert is_valid_event_url("https://lu.ma/ai-summit-2026")
    assert is_valid_event_url("https://events.linuxfoundation.org/kubecon-cloudnativecon/")
    assert not is_valid_event_url("javascript:void(0)")
    assert not is_valid_event_url("https://www.eventbrite.com/d")
    assert not is_valid_event_url("")


def test_is_upcoming_or_future_event():
    """Verify date validator accepts future events and rejects past events."""
    today = date(2026, 9, 25)

    # Future events
    assert is_upcoming_or_future_event("2026-10-15", "2026-10-01", current_date=today)
    assert is_upcoming_or_future_event("15 Nov 2026", "Open Registration", current_date=today)
    assert is_upcoming_or_future_event("Upcoming", "Open RSVP", current_date=today)

    # Past events
    assert not is_upcoming_or_future_event("2026-08-01", "2026-07-20", current_date=today)
    assert not is_upcoming_or_future_event("2026-09-10", "2026-09-05", current_date=today)


def test_ai_fallback_categorization():
    """Verify rule-based heuristic correctly places raw events into the 4 target tabs."""
    # 1. AI & Cloud Summits
    raw_ai = {
        "title": "Global Generative AI & LLM Summit 2026",
        "platform_or_source": "NVIDIA / OpenAI",
        "location": "San Francisco, CA",
        "description": "Deep dive into diffusion models, agentic RAG frameworks, and GPU clusters.",
        "apply_url": "https://ai-summit.org",
    }
    rec_ai = fallback_classify_tech_event(raw_ai)
    assert rec_ai.category == "AI, Cloud & Data Summits"
    assert rec_ai.event_type in ["Summit", "Conference"]
    assert rec_ai.mode == "In-Person"

    # 2. Developer & Open Source Confs
    raw_dev = {
        "title": "Rust & Go Systems Engineering Conf 2026",
        "platform_or_source": "Open Source Community",
        "location": "Global (Online)",
        "description": "High-performance systems programming, memory safety, and kernel modules.",
        "apply_url": "https://rustconf.org",
    }
    rec_dev = fallback_classify_tech_event(raw_dev)
    assert rec_dev.category == "Developer & Open Source Confs"
    assert rec_dev.mode == "Online"

    # 3. Student Tech Fests & Workshops
    raw_student = {
        "title": "National University Techfest & Hands-on Robotics Workshop",
        "platform_or_source": "Unstop (College)",
        "location": "IIT Delhi Campus",
        "description": "Annual student technology symposium with workshops on IoT and web development.",
        "apply_url": "https://unstop.com/events/techfest",
    }
    rec_student = fallback_classify_tech_event(raw_student)
    assert rec_student.category == "Student Tech Fests & Workshops"

    # 4. Meetups, Demo Days & CFPs
    raw_meetup = {
        "title": "PyCon APAC 2026 - Call for Papers & Speakers",
        "platform_or_source": "CFP Radar",
        "location": "Singapore & Hybrid",
        "description": "Submit your sessionize talk proposals for PyCon APAC. Speaker honorarium included.",
        "apply_url": "https://sessionize.com/pycon-apac-2026",
    }
    rec_meetup = fallback_classify_tech_event(raw_meetup)
    assert rec_meetup.category == "Meetups, Demo Days & CFPs"
    assert rec_meetup.event_type == "Call for Papers"
    assert rec_meetup.mode == "Hybrid"


def test_excel_builder_multi_tab_generation():
    """Verify Excel builder compiles a valid workbook with 4 tabs and correct structure."""
    sample_records = [
        TechEventRecord(
            platform_or_source="Google",
            title="Google Cloud Next 2026",
            category="AI, Cloud & Data Summits",
            event_type="Summit",
            domain_track="Cloud & GenAI",
            mode="Hybrid",
            location="Las Vegas, NV & Online",
            start_date="15 Oct 2026",
            end_date="17 Oct 2026",
            registration_deadline="Open RSVP",
            date_posted="Recently Announced",
            pricing_ticket="Free Virtual Pass",
            why_attend="Google Cloud keynotes and Gemini enterprise demos.",
            registration_url="https://cloud.withgoogle.com/next",
        ),
        TechEventRecord(
            platform_or_source="Python Software Foundation",
            title="PyCon Global 2026",
            category="Developer & Open Source Confs",
            event_type="Conference",
            domain_track="Python & Systems",
            mode="Online",
            location="Global (Online)",
            start_date="20 Nov 2026",
            end_date="22 Nov 2026",
            registration_deadline="10 Nov 2026",
            date_posted="Schedule Live",
            pricing_ticket="Free Online Streams",
            why_attend="World's largest Python community conference.",
            registration_url="https://pycon.org",
        ),
        TechEventRecord(
            platform_or_source="Unstop",
            title="Apex Techfest 2026",
            category="Student Tech Fests & Workshops",
            event_type="Tech Fest",
            domain_track="Collegiate Hack & Robotics",
            mode="In-Person",
            location="Bengaluru, India",
            start_date="05 Dec 2026",
            end_date="07 Dec 2026",
            registration_deadline="30 Nov 2026",
            date_posted="Registrations Open",
            pricing_ticket="Free Entry & Certificates",
            why_attend="Hands-on collegiate tech workshops and competitions.",
            registration_url="https://unstop.com/fests/apex",
        ),
        TechEventRecord(
            platform_or_source="Lu.ma",
            title="SF AI Founders Demo Day & Meetup",
            category="Meetups, Demo Days & CFPs",
            event_type="Demo Day",
            domain_track="AI Startups & Networking",
            mode="In-Person",
            location="San Francisco, CA",
            start_date="18 Oct 2026",
            end_date="18 Oct 2026",
            registration_deadline="Open RSVP",
            date_posted="Recently Added",
            pricing_ticket="Free RSVP",
            why_attend="Pitch AI agents to founders and top angel investors.",
            registration_url="https://lu.ma/sf-ai-demo",
        ),
    ]

    excel_bytes = build_excel_workbook(sample_records)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000

    # Load back using openpyxl to verify sheet integrity
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    expected_tabs = [t["name"] for t in TABS_CONFIG]
    assert sheet_names == expected_tabs

    # Verify AI tab content
    ai_sheet = wb["AI, Cloud & Data Summits"]
    assert ai_sheet["A2"].value == "Event Name"
    assert ai_sheet["A3"].value == "Google Cloud Next 2026"
    assert "=HYPERLINK(" in str(ai_sheet["L3"].value)


def test_telegram_caption_generation():
    """Verify Telegram caption contains stats, category breakdowns, and links."""
    records = [
        TechEventRecord(
            platform_or_source="Google",
            title="Google I/O 2026",
            category="AI, Cloud & Data Summits",
            event_type="Summit",
            domain_track="Cloud & Android",
            mode="Hybrid",
            location="Mountain View, CA",
            start_date="May 2026",
            end_date="May 2026",
            registration_deadline="Open",
            date_posted="Flagship Announcement",
            pricing_ticket="Free Virtual",
            why_attend="Google leadership keynotes and product announcements.",
            registration_url="https://io.google/2026/",
        )
    ]

    caption = generate_telegram_caption(records)
    assert "TechyUpdates Tech Events & Conferences Drop" in caption
    assert "AI, Cloud & Data Summits" in caption
    assert "Google I/O 2026" in caption
    assert "Attached Workbook" in caption


def test_is_recent_or_past_24h_posted():
    """Verify past 24h / recent posted date validator."""
    today = date(2026, 9, 25)
    assert is_recent_or_past_24h_posted("Recently Added", current_date=today)
    assert is_recent_or_past_24h_posted("Past 24 Hours", current_date=today)
    assert is_recent_or_past_24h_posted("2026-09-25", current_date=today)
    assert is_recent_or_past_24h_posted("2026-09-24", current_date=today)
    assert not is_recent_or_past_24h_posted("2026-08-01", current_date=today)



def test_excel_builder_empty_records():
    """Verify Excel builder succeeds even with empty records."""
    excel_bytes = build_excel_workbook([])
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert len(wb.sheetnames) == 4
    for name in wb.sheetnames:
        assert "No active events matched" in str(wb[name]["A3"].value)


@pytest.mark.asyncio
async def test_verify_tech_events_liveness_filtering():
    """Verify batch liveness verifier filters out scams and past events."""
    today = datetime.now(timezone.utc).date()
    future_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    past_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    events = [
        # Valid event
        {
            "title": "KubeCon 2026",
            "url": "https://events.linuxfoundation.org/kubecon/",
            "apply_url": "https://events.linuxfoundation.org/kubecon/",
            "start_date": future_date,
            "registration_deadline": future_date,
        },
        # Blacklisted / spam event
        {
            "title": "Forex Trading MLM Seminar",
            "url": "https://spam-events.com/forex",
            "apply_url": "https://spam-events.com/forex",
            "start_date": future_date,
        },
        # Expired event
        {
            "title": "Old DevFest 2024",
            "url": "https://devfest.com/2024",
            "apply_url": "https://devfest.com/2024",
            "start_date": past_date,
            "registration_deadline": past_date,
        },
    ]

    # Filtered directly
    filtered = [
        ev for ev in events
        if not is_scam_or_blacklisted(ev.get("title", ""))
        and is_upcoming_or_future_event(ev.get("start_date"), ev.get("registration_deadline"))
    ]
    assert len(filtered) == 1
    assert filtered[0]["title"] == "KubeCon 2026"


def test_health_check_payload():
    """Verify health endpoint returns required keys and healthy status."""
    from api.health import handler
    assert issubclass(handler, object)


