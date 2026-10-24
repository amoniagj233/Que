"""
Deriv AI Digit Bot - Local Web Server
=====================================
Serves the Deriv Bot Web App on http://127.0.0.1:8000 and automatically opens the browser.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).resolve().parent

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        # Redirect root / to /deriv_bot.html
        if self.path == "/" or self.path == "/index.html":
            self.path = "/deriv_bot.html"
        return super().do_GET()

def main():
    print("=" * 65)
    print(" " * 16 + "DERIV AI DIGIT DIFFERS BOT")
    print("=" * 65)
    print(f"\n[+] Serving web app on: http://127.0.0.1:{PORT}")
    print("[+] Opening your default web browser...")
    
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    
    print("\n[OK] Web App is LIVE! Press Ctrl+C in this window to stop the server.\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Server stopped.")

if __name__ == "__main__":
    main()
