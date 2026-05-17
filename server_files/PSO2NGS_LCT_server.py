"""
PSO2NGS LCT — Web Backend  v3.1
================================
Flask + Flask-SocketIO backend
หน้าที่: อ่าน ChatLog → ส่ง message event → browser
การแปล / TTS / Settings ทั้งหมดทำใน browser

ติดตั้ง:
  pip install flask flask-socketio

รัน standalone:
  python PSO2NGS_LCT_server.py

หรือรันผ่าน PSO2NGS_LCT.exe (launcher จะเรียก main() เอง)
"""

from flask import Flask, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit
import threading, time, os, glob, re, json, sys
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
app    = Flask(__name__)
app.config["SECRET_KEY"] = "pso2ngs-lct-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

DEFAULT_LOG = os.path.join(
    os.path.expanduser("~"),
    "Documents", "SEGA", "PHANTASYSTARONLINE2", "log_ngs"
)

LOG_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\t\d+\t([A-Za-z]+)\t\d+\t(.+?)\t(.+)$'
)

DEFAULT_CMD_PREFIXES = ["/la","/cla","/e","/c","/item","/s","/w","/p","/t","/g","/mn","/ci","/cf","/stamp","/cos","/cam"]

# Global state
watcher_thread = None
watcher_stop   = threading.Event()
settings = {
    "log_dir":        DEFAULT_LOG,
    "channels":       ["PUBLIC","PARTY","TEAM","GUILD","WHISPER","GROUP"],
    "cmd_prefixes":   list(DEFAULT_CMD_PREFIXES),
    "running":        False,
}

# When running as PyInstaller EXE: EXE is at resources/server/ → go up 2 levels to resources/app/
# When running as .py script, go up one level from .server/ to project root
# frozen (PyInstaller EXE): exe อยู่ที่ resources/server/
#   → .app/ และ .server/ อยู่ใน resources/app.asar.unpacked/
# script (dev): __file__ อยู่ใน .server/ → root = parent
if getattr(sys, "frozen", False):
    _res_dir  = os.path.dirname(os.path.dirname(sys.executable))                      # resources/app.asar.unpacked
    _BASE_DIR = os.path.join(os.path.dirname(_res_dir), "app.asar.unpacked", "app")   # resources/app.asar.unpacked/app/
else:
    _BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app_files")

# Settings → %APPDATA%/PSO2NGS_LCT (เขียนได้เสมอ ไม่ติด Program Files permission)
_APPDATA            = os.environ.get("APPDATA") or os.path.expanduser("~")
DIR_SETTINGS        = os.path.join(_APPDATA, "PSO2NGS_LCT", "settings")
DIR_SETTINGS_BACKUP = os.path.join(_APPDATA, "PSO2NGS_LCT", "settings_backup")
SETTINGS_FILE       = os.path.join(DIR_SETTINGS, "pso2ngs_lct_web_settings.json")

# ── Log Watcher Thread ────────────────────────────────────────────────────────
def watcher_run(stop_event):
    log_dir  = settings["log_dir"]
    prefixes       = settings["cmd_prefixes"]
    seen           = {}

    def emit_dbg(msg):
        socketio.emit("debug", {"text": msg})

    def readlines(path):
        for enc in ("utf-16","utf-8","cp932"):
            try:
                with open(path,"r",encoding=enc,errors="strict") as f:
                    return f.readlines()
            except Exception:
                continue
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as f:
                return f.readlines()
        except:
            return []

    def latest_files():
        all_f = sorted(glob.glob(os.path.join(log_dir, "ChatLog*.txt")))
        return all_f[-3:] if len(all_f) > 3 else all_f

    files = latest_files()
    emit_dbg(f"[Watcher] folder: {log_dir}")
    emit_dbg(f"[Watcher] monitoring latest {len(files)} file(s):")
    for f in files:
        emit_dbg(f"  -> {os.path.basename(f)}")
        seen[f] = len(readlines(f))
    if not files:
        emit_dbg("[!] ไม่พบ ChatLog*.txt — ตรวจสอบ path")

    while not stop_event.is_set():
        for path in latest_files():
            lines = readlines(path)
            if path not in seen:
                seen[path] = len(lines)
                emit_dbg(f"[Watcher] new file: {os.path.basename(path)}")
                continue
            prev = seen.get(path, len(lines))
            if len(lines) <= prev:
                seen[path] = len(lines)
                continue
            new_lines = lines[prev:]
            seen[path] = len(lines)
            for line in new_lines:
                raw = line.strip()
                if not raw: continue
                m = LOG_RE.match(raw)
                if not m:
                    emit_dbg(f"[skip] {raw[:80]}")
                    continue
                dt, ch, name, msg = m.groups()
                ch  = ch.upper()
                ch  = {"GUILD": "TEAM", "REPLY": "WHISPER"}.get(ch, ch)
                ts  = dt[11:19]
                if ch not in set(settings["channels"]): continue

                # strip command tokens + emote/numeric args ที่ตามหลัง
                def is_emote_arg(tok):
                    if bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_\-]{0,29}$', tok)) and all(ord(c) < 128 for c in tok):
                        return True
                    if re.match(r'^(s\d+(\.\d+)?|t\d+|nw)$', tok, re.IGNORECASE):
                        return True
                    return False

                tokens = msg.split(" ")
                clean_tokens = []
                last_was_cmd = False
                for tok in tokens:
                    if not tok:
                        continue
                    if tok.startswith("/"):
                        last_was_cmd = True
                        continue
                    if last_was_cmd and (tok.isdigit() or is_emote_arg(tok)):
                        continue
                    last_was_cmd = False
                    clean_tokens.append(tok)

                clean_msg = " ".join(clean_tokens).strip()

                if not clean_msg:
                    emit_dbg(f"[filter] {name}: all commands, skipped: {msg[:50]}")
                    continue

                emit_dbg(f"[line] {ts} {ch} {name}: {msg[:50]}")
                if clean_msg != msg.strip():
                    emit_dbg(f"[strip] cleaned: {clean_msg[:50]}")

                socketio.emit("message", {
                    "ts": ts, "name": name, "ch": ch,
                    "orig": msg.strip(),
                    "clean": clean_msg,
                    "tl": None
                })

        time.sleep(0.4)

# ── Settings persistence ──────────────────────────────────────────────────────
def load_settings():
    os.makedirs(DIR_SETTINGS, exist_ok=True)
    os.makedirs(DIR_SETTINGS_BACKUP, exist_ok=True)
    try:
        with open(SETTINGS_FILE,"r",encoding="utf-8") as f:
            d = json.load(f)
            settings.update(d)
            settings["running"] = False
    except: pass

def save_settings():
    try:
        os.makedirs(DIR_SETTINGS, exist_ok=True)
        # บันทึกทุก field ที่ไม่ใช่ runtime state
        exclude = {"running"}
        d = {k: v for k, v in settings.items() if k not in exclude}
        with open(SETTINGS_FILE,"w",encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except: pass

# ── SocketIO Events ───────────────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    emit("settings", settings)
    emit("debug", {"text": "[Web] Client connected"})
    if settings["running"]:
        emit("status", {"running": True})
        emit("debug", {"text": "[Web] Watcher ยังทำงานอยู่ — ไม่ต้อง Start ใหม่"})

@socketio.on("start")
def on_start(data):
    global watcher_thread, watcher_stop
    settings.update(data)
    save_settings()
    if settings["running"]:
        return
    watcher_stop.clear()
    watcher_thread = threading.Thread(
        target=watcher_run, args=(watcher_stop,), daemon=True)
    watcher_thread.start()
    settings["running"] = True
    emit("status", {"running": True})

@socketio.on("stop")
def on_stop():
    global watcher_stop
    watcher_stop.set()
    settings["running"] = False
    emit("status", {"running": False})

@socketio.on("save_settings")
def on_save_settings(data):
    settings.update(data)
    save_settings()
    emit("settings", settings)

# ── Launch BouyomiChan ────────────────────────────────────────────────────────
from flask import request, jsonify
import subprocess

@app.route("/save_appsettings", methods=["POST"])
def save_appsettings():
    try:
        os.makedirs(DIR_SETTINGS, exist_ok=True)
        data = request.get_json()
        path = os.path.join(DIR_SETTINGS, "appsettings.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/load_appsettings")
def load_appsettings():
    try:
        path = os.path.join(DIR_SETTINGS, "appsettings.json")
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": "not found"})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/launch_bouyomi", methods=["POST"])
def launch_bouyomi():
    try:
        data = request.get_json()
        path = data.get("path", "").strip()
        if not path:
            return jsonify({"ok": False, "error": "ไม่มี path"})
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": f"ไม่พบไฟล์: {path}"})
        subprocess.Popen([path], cwd=os.path.dirname(path))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/backup_settings", methods=["POST"])
def backup_settings_route():
    try:
        os.makedirs(DIR_SETTINGS_BACKUP, exist_ok=True)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"settings_backup_{now}.json"
        backup_path = os.path.join(DIR_SETTINGS_BACKUP, backup_name)
        data = request.get_json()
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True, "filename": backup_name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/open_folder", methods=["POST"])
def open_folder():
    try:
        data = request.get_json()
        folder = data.get("folder", "").strip()
        folder_map = {
            "settings":        DIR_SETTINGS,
            "settings_backup": DIR_SETTINGS_BACKUP,
        }
        target = folder_map.get(folder)
        if not target:
            return jsonify({"ok": False, "error": "ไม่รู้จัก folder"})
        os.makedirs(target, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", target])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return jsonify({"ok": True, "path": target})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

from flask import make_response

@app.route("/")
def index():
    html_path = os.path.join(_BASE_DIR, "PSO2NGS_LCT.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        resp = make_response(content)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return f"<h1>Not found</h1><p>Looking for: {html_path}</p><p>EXE: {sys.executable}</p>"

# ══════════════════════════════════════════════════════════════════════════════
# ▼▼▼  เพิ่ม main() เพื่อให้ launcher.py เรียกได้  ▼▼▼
def main():
    load_settings()
    print("=" * 55)
    print("  PSO2NGS LCT Web Server  v3.2")
    print("  http://localhost:5000")
    print("=" * 55)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
