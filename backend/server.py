import os
import json
import uuid
import tarfile
import email.message
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from database import init_db, get_connection
from video_processor import get_video_metadata, compute_checksum, render_duet, trim_video

PORT = 8765
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

def parse_multipart_upload(rfile, headers):
    content_length = int(headers.get('Content-Length', 0))
    if content_length > 200 * 1024 * 1024:  # 200MB limit
        raise ValueError("Upload too large")
    body = rfile.read(content_length)
    content_type = headers.get('Content-Type', '')
    
    msg = email.message.EmailMessage()
    msg['Content-Type'] = content_type
    msg.set_payload(body)
    
    files = {}
    fields = {}
    
    if msg.is_multipart():
        for part in msg.iter_parts():
            cd = part.get('Content-Disposition', '')
            params = {}
            for item in cd.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    params[k.strip()] = v.strip('"')
            name = params.get('name')
            filename = params.get('filename')
            payload = part.get_payload(decode=True)
            if filename:
                files[name] = {'filename': filename, 'data': payload}
            elif name and payload:
                fields[name] = payload.decode('utf-8', 'errors=ignore')
    return files, fields

class DuetStudioHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path.startswith("/api/"):
            self.handle_api_get(path, query)
        elif path == "/" or path == "":
            self.path = "/index.html"
            self.directory = str(FRONTEND_DIR)
            return super().do_GET()
        elif path.startswith("/media/"):
            rel = path[len("/media/"):]
            file_path = (DATA_DIR / rel).resolve()
            # Prevent path traversal
            if not str(file_path).startswith(str(DATA_DIR.resolve())):
                self.send_error(403, "Forbidden")
                return
            if file_path.exists() and file_path.is_file():
                self.send_file(file_path)
            else:
                self.send_error(404, "File not found")
        else:
            self.directory = str(FRONTEND_DIR)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            try:
                self.handle_api_post(path)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=500)
        else:
            self.send_error(404, "Not found")

    def handle_api_get(self, path, query):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if path == "/api/assets":
                cursor.execute("SELECT * FROM assets ORDER BY created_at DESC")
                rows = [dict(row) for row in cursor.fetchall()]
                self.send_json(rows)
            elif path == "/api/segments":
                cursor.execute("SELECT * FROM segments")
                rows = [dict(row) for row in cursor.fetchall()]
                self.send_json(rows)
            elif path == "/api/turns":
                cursor.execute("SELECT * FROM conversation_turns")
                rows = [dict(row) for row in cursor.fetchall()]
                self.send_json(rows)
            elif path == "/api/generations":
                cursor.execute("SELECT * FROM generations ORDER BY created_at DESC")
                rows = [dict(row) for row in cursor.fetchall()]
                self.send_json(rows)
            elif path == "/api/backup":
                conn.close() # close db before backup
                backup_filename = f"duet_backup_{uuid.uuid4().hex[:8]}.tar.gz"
                backup_path = BASE_DIR / backup_filename
                with tarfile.open(backup_path, "w:gz") as tar:
                    if DATA_DIR.exists():
                        tar.add(DATA_DIR, arcname="data")
                    audit_log = BASE_DIR / "audit.log"
                    if audit_log.exists():
                        tar.add(audit_log, arcname="audit.log")
                self.send_file(backup_path)
                return
            else:
                self.send_error(404, "API endpoint not found")
        finally:
            conn.close()

    def handle_api_post(self, path):
        content_type = self.headers.get("Content-Type", "")
        
        if path == "/api/assets/upload":
            if "multipart/form-data" in content_type:
                try:
                    files, fields = parse_multipart_upload(self.rfile, self.headers)
                except Exception as e:
                    self.send_json({"success": False, "error": f"Failed to parse upload: {str(e)}"}, status=400)
                    return
                
                if "video" in files:
                    fileitem = files["video"]
                    filename = os.path.basename(fileitem['filename'])
                    safe_name = f"{uuid.uuid4()}_{filename}"
                    dest_path = UPLOADS_DIR / safe_name
                    with open(dest_path, "wb") as f:
                        f.write(fileitem['data'])
                    
                    meta = get_video_metadata(str(dest_path))
                    checksum = compute_checksum(str(dest_path))
                    asset_id = f"asset_{uuid.uuid4().hex[:8]}"
                    
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO assets (asset_id, file_path, duration, width, height, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                            (asset_id, str(dest_path), meta["duration"], meta["width"], meta["height"], checksum)
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    
                    self.send_json({"success": True, "asset_id": asset_id, "file_path": str(dest_path), **meta})
                    return
            self.send_json({"success": False, "error": "Invalid upload data"}, status=400)

        elif path == "/api/render/duet":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            asset1_id = body.get("asset1_id")
            asset2_id = body.get("asset2_id")
            layout = body.get("layout", "side-by-side")
            trim1 = body.get("trim1") # e.g. {"start": 0.0, "duration": 5.0}
            trim2 = body.get("trim2")
            
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset1_id,))
                a1 = cursor.fetchone()
                cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset2_id,))
                a2 = cursor.fetchone()
            finally:
                conn.close()
            
            if not a1 or not a2:
                self.send_json({"success": False, "error": "Assets not found"}, status=404)
                return
                
            out_filename = f"duet_{uuid.uuid4().hex[:8]}.mp4"
            out_path = OUTPUTS_DIR / out_filename
            
            try:
                render_duet(a1["file_path"], a2["file_path"], str(out_path), layout, trim1=trim1, trim2=trim2)
                meta = get_video_metadata(str(out_path))
                checksum = compute_checksum(str(out_path))
                
                output_asset_id = f"asset_{uuid.uuid4().hex[:8]}"
                
                conn = get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO assets (asset_id, file_path, duration, width, height, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                        (output_asset_id, str(out_path), meta["duration"], meta["width"], meta["height"], checksum)
                    )
                    
                    generation_id = f"gen_{uuid.uuid4().hex[:8]}"
                    parent_assets_json = json.dumps([asset1_id, asset2_id])
                    recipe_json = json.dumps(body)
                    
                    cursor.execute(
                        "INSERT INTO generations (generation_id, parent_assets, segments, layout, edit_recipe, output_asset_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (generation_id, parent_assets_json, "[]", layout, recipe_json, output_asset_id)
                    )
                    conn.commit()
                finally:
                    conn.close()
                
                self.send_json({"success": True, "generation_id": generation_id, "output_asset_id": output_asset_id, "output_url": f"/media/outputs/{out_filename}"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=500)

        elif path == "/api/turns":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            turn_id = f"turn_{uuid.uuid4().hex[:8]}"
            segment_id = body.get("segment_id")
            transcript = body.get("transcript")
            reply_to = body.get("reply_to")
            relationship = body.get("relationship", "response")
            confidence = body.get("confidence", 1.0)
            
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO conversation_turns (turn_id, segment_id, transcript, reply_to, relationship, confidence) VALUES (?, ?, ?, ?, ?, ?)",
                    (turn_id, segment_id, transcript, reply_to, relationship, confidence)
                )
                conn.commit()
            finally:
                conn.close()
            self.send_json({"success": True, "turn_id": turn_id})
        else:
            self.send_error(404, "API endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path: Path):
        self.send_response(200)
        if file_path.suffix == ".mp4":
            self.send_header("Content-Type", "video/mp4")
        elif file_path.suffix == ".html":
            self.send_header("Content-Type", "text/html")
        elif file_path.suffix == ".js":
            self.send_header("Content-Type", "application/javascript")
        elif file_path.suffix == ".css":
            self.send_header("Content-Type", "text/css")
        else:
            self.send_header("Content-Type", "application/octet-stream")
        
        file_size = file_path.stat().st_size
        self.send_header("Content-Length", str(file_size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

def run():
    init_db()
    server_address = ('127.0.0.1', PORT)
    httpd = HTTPServer(server_address, DuetStudioHandler)
    print(f"DuetConversationStudio server running on http://127.0.0.1:{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
