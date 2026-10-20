import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from core.rooms_logic import walls, reports

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/summary':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "Бо 8.1"}).encode())
        elif self.path.startswith('/api/rooms/') and '/walls' in self.path:
            room_id = int(self.path.split('/')[3])
            data = walls.get_wall_state(room_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html = "<h1>🏗️ Бо 8.1 — Веб-панель</h1><p>Сайт работает!</p>"
            self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    PORT = 8080
    print(f"🚀 Сайт Бо запущен: http://0.0.0.0:{PORT}")
    HTTPServer(("", PORT), APIHandler).serve_forever()
