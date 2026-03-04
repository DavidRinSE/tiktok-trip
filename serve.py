import http.server
import socketserver

PORT = 3001

with socketserver.TCPServer(("0.0.0.0", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"Serving at http://tiktok-trip.local:{PORT}/docs/index.html")
    httpd.serve_forever()
