import http.server
import socketserver
import webbrowser
import os
import time
import json
import glob
import subprocess
import sys
import re
from datetime import date

PORT = 8080
# Serve the dashboard folder
DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/usage':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            antigravity_dir = os.path.expanduser(r"~\.gemini\antigravity\conversations")
            total_sessions = 0
            if os.path.exists(antigravity_dir):
                total_sessions = len(glob.glob(os.path.join(antigravity_dir, "*.pb")))

            self.wfile.write(json.dumps({"sessions": total_sessions}).encode("utf-8"))
            return

        if self.path == '/api/billing_usage':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            usage_file = os.path.join(DIRECTORY, 'usage.json')
            if os.path.exists(usage_file):
                with open(usage_file, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(b'{"openai_cost": 0.0, "gemini_cost": 0.0, "openai_tokens": 0, "gemini_tokens": 0}')
            return

        if self.path == '/api/projects':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            projects_file = os.path.join(DIRECTORY, 'projects.json')
            if os.path.exists(projects_file):
                with open(projects_file, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(b'[]')
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/sync_projects':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            try:
                push_script = os.path.join(ROOT, "scripts", "push_to_sheets.py")
                python_exe  = sys.executable
                result = subprocess.run(
                    [python_exe, push_script],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    self.wfile.write(json.dumps({"status": "ok", "output": result.stdout}).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"status": "error", "output": result.stderr}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "output": str(e)}).encode("utf-8"))
            return

        if self.path == '/api/add_project':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                name = data.get('name')
                description = data.get('description')
                status = data.get('status', 'Active')

                if not name or not description:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Name and description are required."}).encode('utf-8'))
                    return

                projects_file = os.path.join(DIRECTORY, 'projects.json')
                projects = []
                if os.path.exists(projects_file):
                    with open(projects_file, 'r', encoding='utf-8') as f:
                        projects = json.load(f)

                # Simple slugify
                project_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

                # Check for duplicates
                if any(p.get('id') == project_id for p in projects):
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": f"Project ID '{project_id}' already exists."}).encode('utf-8'))
                    return

                new_project = {
                    "id": project_id,
                    "name": name,
                    "description": description,
                    "date_completed": str(date.today()),
                    "status": status
                }

                projects.append(new_project)
                with open(projects_file, 'w', encoding='utf-8') as f:
                    json.dump(projects, f, indent=4, ensure_ascii=False)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    # Restore default request logs for debugging
    def log_message(self, format, *args):
        print(f"[{self.date_time_string()}] {format % args}")


def start_server():
    print("=" * 55)
    print("  Autonomous Intelligence Systems - Project Dashboard")
    print("=" * 55)
    print(f"[*] Starting local server on port {PORT}...")

    # Using ThreadingTCPServer to avoid blocking on requests
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print("[*] Dashboard is LIVE.")
        print("[*] Opening your browser...")

        # Open browser automatically
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{PORT}")

        print(f"\n --> Dashboard: http://localhost:{PORT}")
        print(" --> Press Ctrl+C in this terminal to shut down.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down. Have a great day!")


if __name__ == "__main__":
    start_server()
