from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import yt_dlp
import os
import threading

app = FastAPI()

BASE_DIR = "downloads"
logs = []
log_lock = threading.Lock()

def log(msg: str):
    print(msg)
    with log_lock:
        logs.append(msg)
        if len(logs) > 100:
            logs.pop(0)

def sanitize(text: str) -> str:
    return "".join(c if c.isalnum() or c in " -_()" else "_" for c in text).strip()


import subprocess


@app.post("/download")
def download(url: str = Form(...), folder: str = Form(...)):
    try:
        logs.clear()
        sanitized_folder = sanitize(folder)
        folder_path = os.path.join(BASE_DIR, sanitized_folder)
        os.makedirs(folder_path, exist_ok=True)

        log("[DEBUG] Starting download using yt-dlp CLI with browser cookies...")

        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--no-check-certificate",
            "--geo-bypass",
            "--audio-format", "mp3",
            "--output", os.path.join(folder_path, "%(title)s.%(ext)s"),
            url
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            log(f"[ERROR] yt-dlp failed: {result.stderr}")
            return JSONResponse({"error": result.stderr})

        log("[DEBUG] yt-dlp completed successfully")

        # Find the downloaded mp3 file
        for fname in os.listdir(folder_path):
            if fname.endswith(".mp3"):
                mp3_path = os.path.join(folder_path, fname)
                log(f"[INFO] MP3 file found: {mp3_path}")
                return FileResponse(path=mp3_path, filename=fname, media_type="audio/mpeg")

        return JSONResponse({"error": "MP3 file not found after download."})

    except Exception as e:
        log(f"[ERROR] Exception: {str(e)}")
        return JSONResponse({"error": str(e)})


@app.get("/logs")
def get_logs():
    with log_lock:
        return JSONResponse({"logs": logs})

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>YouTube MP3 Downloader</title>
        <style>
            textarea {
                width: 100%;
                height: 300px;
                margin-top: 20px;
                resize: none;
                font-family: monospace;
                background-color: #f5f5f5;
            }
        </style>
        <script>
            async function fetchLogs() {
                const res = await fetch('/logs');
                const data = await res.json();
                const logText = data.logs.join('\\n');
                document.getElementById('logbox').value = logText;
            }

            setInterval(fetchLogs, 1500); // refresh logs every 1.5s
            window.onload = fetchLogs;
        </script>
    </head>
    <body>
        <h2>YouTube MP3 Downloader</h2>
        <form action="/download" method="post">
            YouTube URL: <input name="url" type="text"><br><br>
            Folder Name: <input name="folder" type="text"><br><br>
            <button type="submit">Download MP3</button>
        </form>

        <h3>Logs</h3>
        <textarea id="logbox" readonly></textarea>
    </body>
    </html>
    """
