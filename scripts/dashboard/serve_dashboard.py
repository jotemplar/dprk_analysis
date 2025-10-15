#!/usr/bin/env python3
"""Simple HTTP server to serve the DPRK dashboard"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Change to the directory containing the dashboard files
os.chdir(Path(__file__).parent)

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow loading local resources
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Serve the dashboard by default
        if self.path == '/':
            self.path = '/dprk_comprehensive_dashboard.html'
        return super().do_GET()

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"🚀 DPRK Dashboard Server running at http://localhost:{PORT}")
    print(f"📊 Dashboard: http://localhost:{PORT}/dprk_comprehensive_dashboard.html")
    print("Press Ctrl+C to stop the server")

    # Open browser automatically
    webbrowser.open(f'http://localhost:{PORT}/dprk_comprehensive_dashboard.html')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server stopped")