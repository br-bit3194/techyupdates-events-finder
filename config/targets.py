"""TechyUpdates Tech Events Finder Configuration: Platform endpoints, feed URLs, targets, and validation rules."""

from typing import Dict, List, Set, Any

# Platform Search Feeds & Endpoints
LUMA_CONFIG: Dict[str, Any] = {
    "base_url": "https://api.lu.ma",
    "search_queries": [
        "AI",
        "Generative AI",
        "Machine Learning",
        "Developer Meetup",
        "Web3",
        "Rust",
        "Open Source",
        "Hackathon Demo Day",
        "Tech Summit",
    ],
    "cities": [
        "San Francisco",
        "New York",
        "Bengaluru",
        "London",
        "Berlin",
        "Singapore",
        "Tokyo",
        "Seattle",
        "Austin",
        "Online",
    ],
}

EVENTBRITE_CONFIG: Dict[str, Any] = {
    "base_url": "https://www.eventbrite.com/d",
    "categories": ["science-and-tech", "developers", "artificial-intelligence"],
}

CONFS_TECH_CONFIG: Dict[str, Any] = {
    "topics": [
        "ai",
        "javascript",
        "python",
        "rust",
        "golang",
        "devops",
        "security",
        "web",
        "cloud",
        "data",
    ],
    "base_url": "https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences",
}

DEV_EVENTS_CONFIG: Dict[str, Any] = {
    "rss_url": "https://dev.events/rss.xml",
    "api_url": "https://dev.events/api/events",
}

COMMUDLE_CONFIG: Dict[str, Any] = {
    "api_url": "https://api.commudle.com/api/v1/public/events",
    "web_url": "https://www.commudle.com/events",
}

KONFHUB_CONFIG: Dict[str, Any] = {
    "api_url": "https://api.konfhub.com/events/public",
    "web_url": "https://konfhub.com",
}

UNSTOP_TECH_EVENTS_CONFIG: Dict[str, Any] = {
    "api_url": "https://unstop.com/api/public/opportunity/search-result",
    "categories": ["workshops", "conferences", "cultural-festivals", "webinars"],
}

# Flagship Enterprise Summits & Developer Days
FLAGSHIP_SUMMITS: List[Dict[str, Any]] = [
    {
        "title": "Google I/O & Cloud Next 2026",
        "organizer": "Google",
        "domain": "AI, Cloud & Android Ecosystem",
        "mode": "Hybrid",
        "location": "Mountain View, CA & Global Online",
        "apply_url": "https://io.google/2026/",
        "pricing": "Free RSVP (Virtual) / Invited In-Person",
        "eligibility": "Global Developers & Cloud Engineers",
        "why_attend": "Keynotes from Google leadership, Android & Gemini product reveals, hands-on codelabs.",
    },
    {
        "title": "Microsoft Build 2026",
        "organizer": "Microsoft",
        "domain": "Generative AI, Copilot, Azure & Windows Dev",
        "mode": "Hybrid",
        "location": "Seattle, WA & Global Online",
        "apply_url": "https://build.microsoft.com/",
        "pricing": "Free (Online) / Paid (In-Person)",
        "eligibility": "Developers, AI Architects, Enterprise Engineers",
        "why_attend": "Azure AI updates, OpenAI partnership announcements, Microsoft Copilot deep dives.",
    },
    {
        "title": "AWS re:Invent & Global Summits 2026",
        "organizer": "Amazon Web Services",
        "domain": "Cloud Infrastructure, Bedrock AI & Serverless",
        "mode": "Hybrid",
        "location": "Las Vegas, NV & Global Cities",
        "apply_url": "https://reinvent.awsevents.com/",
        "pricing": "Free Keynotes Online / Pass for Expo",
        "eligibility": "Cloud Practitioners, DevOps Engineers, Architects",
        "why_attend": "Hundreds of breakout sessions, new AWS service launches, hands-on builder workshops.",
    },
    {
        "title": "Apple Worldwide Developers Conference (WWDC 2026)",
        "organizer": "Apple",
        "domain": "iOS, macOS, visionOS, Swift & Apple Intelligence",
        "mode": "Hybrid",
        "location": "Cupertino, CA & Online",
        "apply_url": "https://developer.apple.com/wwdc26/",
        "pricing": "Free (Online)",
        "eligibility": "Apple Ecosystem Developers & Students",
        "why_attend": "Unveiling next-gen iOS/macOS APIs, Swift updates, Apple Intelligence capabilities.",
    },
    {
        "title": "GitHub Universe 2026",
        "organizer": "GitHub",
        "domain": "Developer Tooling, AI Pair Programming & DevOps",
        "mode": "Hybrid",
        "location": "San Francisco, CA & Global Online",
        "apply_url": "https://githubuniverse.com/",
        "pricing": "Free Virtual Pass / In-Person Ticket",
        "eligibility": "All Software Developers, Open Source Maintainers",
        "why_attend": "GitHub Copilot evolution, Octoverse releases, world-class developer experience sessions.",
    },
    {
        "title": "NVIDIA GTC (GPU Technology Conference) 2026",
        "organizer": "NVIDIA",
        "domain": "Accelerated Computing, LLMs, Robotics & CUDA",
        "mode": "Hybrid",
        "location": "San Jose, CA & Online",
        "apply_url": "https://www.nvidia.com/gtc/",
        "pricing": "Free Virtual Keynote & Tracks / Paid Conference",
        "eligibility": "AI Researchers, CUDA Developers, Roboticists",
        "why_attend": "Jensen Huang keynote, Blackwell/next-gen GPU architecture, cutting-edge AI breakthroughs.",
    },
    {
        "title": "KubeCon + CloudNativeCon 2026",
        "organizer": "CNCF / Linux Foundation",
        "domain": "Kubernetes, Cloud Native, Microservices & Observability",
        "mode": "In-Person & Virtual",
        "location": "Global Tour (North America, Europe, India)",
        "apply_url": "https://events.linuxfoundation.org/",
        "pricing": "Free Virtual Keynotes / Paid Pass",
        "eligibility": "DevOps Engineers, SREs, Platform Engineers",
        "why_attend": "The flagship cloud native gathering with official maintainer tracks and CNCF project updates.",
    },
    {
        "title": "OpenAI DevDay 2026",
        "organizer": "OpenAI",
        "domain": "Frontier AI, GPT Models, APIs & Agentic Frameworks",
        "mode": "Hybrid",
        "location": "San Francisco, CA & Live Stream",
        "apply_url": "https://devday.openai.com/",
        "pricing": "Free Live Stream / Developer Applications",
        "eligibility": "AI Engineers, Founders, API Builders",
        "why_attend": "Direct announcements of next-generation OpenAI models, developer SDKs, and tooling.",
    },
    {
        "title": "DEF CON 34 & Black Hat USA 2026",
        "organizer": "DEF CON Communications",
        "domain": "Cybersecurity, Ethical Hacking, AppSec & Exploit Dev",
        "mode": "In-Person",
        "location": "Las Vegas, NV",
        "apply_url": "https://defcon.org/",
        "pricing": "Standard Door Pass / CFP Open",
        "eligibility": "Security Researchers, Penetration Testers, Hackers",
        "why_attend": "World's premier hacker gathering, technical villages, CTFs, and hardware hacking labs.",
    },
    {
        "title": "DockerCon 2026",
        "organizer": "Docker Inc.",
        "domain": "Containers, Dev Environments, Docker AI & Microservices",
        "mode": "Hybrid",
        "location": "Online & Global Watch Parties",
        "apply_url": "https://www.docker.com/dockercon/",
        "pricing": "Free (Virtual)",
        "eligibility": "Software Developers, Platform Teams",
        "why_attend": "Latest Docker Desktop features, container optimization techniques, and developer workflows.",
    },
]

# Targeted Tech Keywords
POSITIVE_TECH_KEYWORDS: Set[str] = {
    "conference",
    "summit",
    "meetup",
    "workshop",
    "tech fest",
    "techfest",
    "symposium",
    "developer day",
    "demo day",
    "call for papers",
    "cfp",
    "keynote",
    "bootcamp",
    "webinar",
    "ai",
    "genai",
    "machine learning",
    "deep learning",
    "cloud",
    "devops",
    "kubernetes",
    "docker",
    "cybersecurity",
    "web3",
    "blockchain",
    "rust",
    "python",
    "golang",
    "javascript",
    "typescript",
    "react",
    "system design",
    "open source",
    "gdg",
    "aws community",
}

# Unwanted / Low Quality / Spam Keywords
BLACKLIST_KEYWORDS: Set[str] = {
    "mlm",
    "crypto trading course",
    "forex signal",
    "dropshipping webinar",
    "real estate investment seminar",
    "astrology",
    "weight loss",
    "multilevel marketing",
    "earn 1000 daily with no skills",
    "guaranteed job package pay upfront",
    "dating meetup",
    "party night",
}

# Soft-404 text patterns that signal an event page is dead or invalid
SOFT_404_PATTERNS: List[str] = [
    "oops! this initiative isn't live yet",
    "oops! this initiative isn’t live yet",
    "this event has ended",
    "event has ended",
    "registration is closed",
    "registration closed",
    "tickets sold out",
    "page not found",
    "404 not found",
    "event not found",
    "draft event",
    "this listing is private",
    "the event you are looking for does not exist",
    "we couldn't find the page",
    "we couldn’t find the page",
    "access denied",
]
