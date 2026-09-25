# Product Requirements Document (PRD)
## TechyUpdates Tech Events & Conferences Finder

---

### Executive Summary
**TechyUpdates Tech Events Finder** is an autonomous daily data synthesis engine, AI classification pipeline, and community broadcasting radar. It scours global and regional developer ecosystems every single day for verified **Tech Conferences**, **Enterprise Developer Summits**, **Meetups**, **College Tech Fests**, **Workshops**, and **Call for Papers (CFPs)**.

Enriched using **Google Gemini 3 AI Series** with automatic local heuristic failover, the engine compiles a 4-tab color-coded Excel workbook (`.xlsx`) in-memory and broadcasts daily curated opportunities to Telegram communities (`@techy_events_updates`).

---

### Core Upgrades & Feature Architecture

#### 1. 🔄 Cross-Day Persistent Deduplication & History Tracker
- **[services/history_tracker.py](file:///d:/TechyUpdates/tech_events_finder/services/history_tracker.py)**:
  - **Persistent JSON Store (`data/sent_history.json`)**: Durable local file tracking every event broadcasted across runs.
  - **Dual-Key Matching**: Prevents duplicate alerts by cross-matching both **normalized title** (stripping punctuation, emojis, casing, and whitespace) and **canonical URL** (stripping UTM tracking parameters, query artifacts, and trailing slashes).
  - **Auto-TTL Cleanup**: Automatically purges entries older than **30 days** to prevent file bloat.
  - **Cross-Run Sync**: Configured GitHub Actions ([.github/workflows/daily_pipeline.yml](file:///d:/TechyUpdates/tech_events_finder/.github/workflows/daily_pipeline.yml)) to automatically commit and push updated history back to the GitHub repository after every daily cron execution.

---

#### 2. 🛡️ Strict Active Liveness & Soft-404 Anti-Error Probes
- **[services/collectors/liveness_verifier.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/liveness_verifier.py)**:
  - **Active HTTP Verification**: Probes event URLs with asynchronous HTTP client before spreadsheet generation.
  - **Soft-404 Pattern Blocker**: Rejects pages returning HTTP 200 with unpublished, closed, or broken DOM text (*"Registration is Closed"*, *"Tickets Sold Out"*, *"This event has ended"*, *"Page not found"*, *"Draft Event"*).
  - **Direct URL Enforcer**: Rejects generic directory and filter search pages (e.g., `/events?category=...`) in favor of direct landing registration pages.
  - **Strict Active Registration & Future Date Filter**: Rejects past events ($\text{Start Date} \ge \text{Today}$, $\text{Deadline} \ge \text{Today}$).
  - **Anti-Scam & Quality Filter**: Drops MLM seminars, paid trading webinars, and non-technical spam.

---

#### 3. 🏢 Flagship Enterprise Developer Summits Collector
- **[services/collectors/flagship_summits.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/flagship_summits.py)**:
  - Dedicated real-time monitoring for tier-1 global developer flagships:
    - *Google I/O & Cloud Next*
    - *Microsoft Build & Ignite*
    - *AWS re:Invent & Global Summits*
    - *Apple Worldwide Developers Conference (WWDC)*
    - *GitHub Universe*
    - *NVIDIA GTC (GPU Technology Conference)*
    - *KubeCon + CloudNativeCon (CNCF / Linux Foundation)*
    - *OpenAI DevDay*
    - *DEF CON & Black Hat USA*
    - *DockerCon*

---

#### 4. ⚡ Multi-Source Asynchronous Community & Conference Collectors
- **[services/collectors/luma_eventbrite.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/luma_eventbrite.py)**: Lu.ma developer meetups, AI demo days, hacker houses, and Eventbrite tech workshops.
- **[services/collectors/dev_conferences.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/dev_conferences.py)**: Confs.tech open catalog across 10+ software engineering topics (AI, Python, DevOps, JavaScript, Rust, Golang, Security, Web, Cloud) and Dev.events.
- **[services/collectors/community_fests.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/community_fests.py)**: Commudle developer chapters, KonfHub technical workshops, and Unstop college tech festivals/symposiums.
- **[services/collectors/cfp_radar.py](file:///d:/TechyUpdates/tech_events_finder/services/collectors/cfp_radar.py)**: Active Call for Papers (CFP) speaker submission deadlines.

---

#### 5. 🤖 Gemini AI Rate-Limiting & Heuristic Safety Fallback
- **[services/ai_extractor.py](file:///d:/TechyUpdates/tech_events_finder/services/ai_extractor.py)**:
  - Powered by **Google Gemini Flash** (`gemini-2.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.5-flash`) via `google-genai` SDK.
  - **2.5s pacing delay** and exponential backoff retry mechanism to prevent Gemini API 429 quota exhaustion.
  - Automatic local rule-based heuristic classifier fallback when API key is not present or offline.

---

#### 6. 📊 12-Column Multi-Tab Excel Workbook
- **[services/excel_builder.py](file:///d:/TechyUpdates/tech_events_finder/services/excel_builder.py)**:
  - Generates 4 styled, color-coded tabs:
    1. 🔮 **AI, Cloud & Data Summits** (Deep Indigo `#312E81`)
    2. ⚡ **Developer & Open Source Confs** (Deep Teal `#0F766E`)
    3. 🎓 **Student Tech Fests & Workshops** (Forest Green `#065F46`)
    4. 🚀 **Meetups, Demo Days & CFPs** (Deep Rust `#9A3412`)
  - 12 Rich Columns:
    1. *Event Name*
    2. *Organizer / Source*
    3. *Event Type (Conference / Summit / Meetup / Workshop / Tech Fest / Demo Day / CFP)*
    4. *Domain & Track*
    5. *Mode (In-Person / Hybrid / Online)*
    6. *Location / City*
    7. *Start Date*
    8. *End Date*
    9. *Registration / RSVP Deadline*
    10. *Date Announced / Posted*
    11. *Pricing & Perks (Free RSVP / Virtual Pass / CFP Open / Paid)*
    12. *Direct Registration Link (`=HYPERLINK("url", "Register / RSVP")`)*

---

#### 7. 📢 Telegram Channel Broadcast & Serverless Automation
- **[services/telegram_notifier.py](file:///d:/TechyUpdates/tech_events_finder/services/telegram_notifier.py)**: Broadcasts rich Markdown summaries and delivers the `.xlsx` document directly to Telegram channels (`@techy_events_updates`).
- **[api/trigger.py](file:///d:/TechyUpdates/tech_events_finder/api/trigger.py)**: Serverless entrypoint for Vercel Cron and GitHub Actions (runs daily at **03:30 UTC / 9:00 AM IST**).

- **[api/health.py](file:///d:/TechyUpdates/tech_events_finder/api/health.py)**: Liveness probe returning operational status.

---

#### 8. 🧪 Automated Test Suite (17/17 Passing)
- **[tests/test_history_tracker.py](file:///d:/TechyUpdates/tech_events_finder/tests/test_history_tracker.py)** and **[tests/test_pipeline.py](file:///d:/TechyUpdates/tech_events_finder/tests/test_pipeline.py)**:
  - Comprehensive unit test coverage validating deduplication, deadline filtering, URL cleaning, Excel layout, soft-404 markers, and history tracking.