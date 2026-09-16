#!/usr/bin/env python3
"""
Simple proxy server for Freepik API to handle CORS
Run: FREEPIK_API_KEY=... python3 freepik-proxy.py
Then access: http://localhost:3002/icons?term=cooking
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import ssl
import json
import os
import sys

# Never hardcode this: the repo is public and GitHub Pages serves this
# directory, so a committed key is a published key.
#   export FREEPIK_API_KEY=...
API_KEY = os.environ.get('FREEPIK_API_KEY')
FREEPIK_BASE = 'https://api.freepik.com/v1'
PORT = 3002

class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        try:
            # Build Freepik API URL
            api_url = f"{FREEPIK_BASE}{self.path}"

            # Create request with headers
            req = urllib.request.Request(api_url)
            req.add_header('x-freepik-api-key', API_KEY)
            req.add_header('Accept', 'application/json')

            # SSL context
            ctx = ssl.create_default_context()

            # Make request
            with urllib.request.urlopen(req, context=ctx) as response:
                content = response.read()
                status = response.status

            # Send response with CORS headers
            self.send_response(status)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(content)

        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        print(f"[Proxy] {args[0]}")

if __name__ == '__main__':
    if not API_KEY:
        sys.exit('set FREEPIK_API_KEY in the environment first')
    server = HTTPServer(('localhost', PORT), ProxyHandler)
    print(f"Freepik API Proxy running on http://localhost:{PORT}")
    print(f"Example: http://localhost:{PORT}/icons?term=cooking")
    server.serve_forever()
