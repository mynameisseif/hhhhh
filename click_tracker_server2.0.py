"""
click_tracker_server.py

Educational demo server for a cybersecurity presentation.
Companion to pixel_server.py -- but instead of logging on IMAGE LOAD,
this logs on LINK CLICK, then redirects the visitor to a normal site
(Google, by default).

This demonstrates the same underlying concept used by:
  - URL shorteners with analytics (bit.ly, etc.)
  - "Click here" tracking links in marketing emails
  - Phishing campaign click-tracking (for awareness/detection purposes)

There is no exploit, no malware, no code execution involved.
The "trick" is entirely server-side logging of a normal HTTP request,
followed by a standard HTTP redirect.

Usage:
    python3 click_tracker_server.py

Then embed a link (NOT an image) in an email/HTML:
    <a href="http://YOUR_IP_OR_NGROK_URL:8000/track">Click here</a>

When clicked:
  1. The link hits this server first
  2. The server logs visitor IP / user-agent / timestamp
  3. The server responds with an HTTP redirect to REDIRECT_TARGET
  4. The visitor's browser follows the redirect automatically and lands
     on a normal, harmless page (Google by default)

Watch the console / click_log.csv for incoming clicks.
"""

import http.server
import socketserver
import datetime
import csv
import os

PORT = int(os.environ.get("PORT", 8000))  # Railway sets PORT automatically; 8000 is the local fallback
LOG_FILE = "click_log.csv"
TRACK_PATH = ""          # the path your tracking link points to
REDIRECT_TARGET = "https://www.tiktok.com/@.marcus_aurelius?_r=1&_t=ZS-97UUv0eKVtc"  # where visitors land after the click


def log_click(visitor_ip, direct_ip, user_agent, path, referer):
    """Append a single click record to console and CSV log."""
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    row = [timestamp, visitor_ip, direct_ip, user_agent, path, referer]

    print(
        f"[CLICK] {timestamp} | Visitor IP: {visitor_ip} | "
        f"Direct connection from: {direct_ip} | UA: {user_agent} | "
        f"Path: {path} | Referer: {referer}"
    )

    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp", "visitor_ip", "direct_connection_ip", "user_agent", "path", "referer"]
            )
        writer.writerow(row)


class ClickTrackerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Same IP-resolution logic as the pixel demo: prefer X-Forwarded-For
        # (the real client IP, added by tunnels/proxies like ngrok) and
        # fall back to the raw socket address for plain/direct connections.
        direct_ip = self.client_address[0]
        forwarded_for = self.headers.get("X-Forwarded-For")

        if forwarded_for:
            visitor_ip = forwarded_for.split(",")[0].strip()
        else:
            visitor_ip = direct_ip

        user_agent = self.headers.get("User-Agent", "unknown")
        referer = self.headers.get("Referer", "none")

        if self.path.startswith(TRACK_PATH):
            # This is the tracked click -- log it, then redirect.
            log_click(visitor_ip, direct_ip, user_agent, self.path, referer)

            self.send_response(302)  # 302 Found = temporary redirect
            self.send_header("Location", REDIRECT_TARGET)
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
        else:
            # Any other path: simple placeholder response (not part of the demo flow,
            # just avoids a confusing 404 if someone hits the bare server URL).
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(
                f"Server is running. Tracked link path is {TRACK_PATH}".encode()
            )

    def log_message(self, format, *args):
        # Silence default stderr request logging; we have our own log_click().
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), ClickTrackerHandler) as httpd:
        print(f"Click-tracker server running on port {PORT}")
        print(f"Embed this LINK (not an image tag) in your email/HTML:")
        print(f'  <a href="http://YOUR_IP_OR_NGROK_URL:{PORT}{TRACK_PATH}">Click here</a>')
        print(f"Visitors will be logged, then redirected to: {REDIRECT_TARGET}")
        print(f"Logging clicks to ./{LOG_FILE}\n")
        httpd.serve_forever()
