"""Liveness probe & health status endpoint for TechyUpdates Tech Events Finder."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Vercel serverless / standard HTTP health probe."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        payload = {
            "status": "healthy",
            "service": "techyupdates-tech-events-finder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collectors": [
                "Luma & Eventbrite",
                "Dev Conferences & Confs.tech",
                "Community Fests & Unstop",
                "Flagship Enterprise Summits",
                "CFP Radar",
            ],
            "version": "1.0.0",
        }
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))


if __name__ == "__main__":
    from http.server import HTTPServer
    server = HTTPServer(("0.0.0.0", 8000), handler)
    print("Health server running on port 8000...")
    server.serve_forever()
