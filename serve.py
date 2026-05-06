"""
Serve the property graph map on http://localhost:8765
"""
import http.server
import os
import threading
import webbrowser

PORT = 8765
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler
handler.log_message = lambda *a: None

def open_browser():
    webbrowser.open(f"http://localhost:{PORT}/data/property_graph_map.html")

print(f"Serving Sierra Madre Map on http://localhost:{PORT}")
threading.Timer(0.8, open_browser).start()
with http.server.HTTPServer(("", PORT), handler) as httpd:
    httpd.serve_forever()
