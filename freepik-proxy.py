#!/usr/bin/env python3
"""
Simple proxy server for Freepik API to handle CORS
Run: python3 freepik-proxy.py
Then access: http://localhost:3002/icons?term=cooking
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import json

API_KEY = 'FPSX98b5430c546d73ef259e47ed0df6eabd'
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

            # Make request to Freepik using requests library
            headers = {
                'x-freepik-api-key': API_KEY,
                'Accept': 'application/json'
            }
            response = requests.get(api_url, headers=headers)

            # Send response with CORS headers
            self.send_response(response.status_code)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response.content)

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
    server = HTTPServer(('localhost', PORT), ProxyHandler)
    print(f"Freepik API Proxy running on http://localhost:{PORT}")
    print(f"Example: http://localhost:{PORT}/icons?term=cooking")
    server.serve_forever()
