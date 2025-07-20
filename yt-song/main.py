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

@app.post("/download")
def download(url: str = Form(...), folder: str = Form(...)):
    try:
        # Clear previous logs
        with log_lock:
            logs.clear()

        sanitized_folder = sanitize(folder)
        folder_path = os.path.join(BASE_DIR, sanitized_folder)
        os.makedirs(folder_path, exist_ok=True)

        log("[DEBUG] Starting metadata fetch...")
        ydl_opts_meta = {'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'audio')
            log(f"[DEBUG] Fetched title: {title}")
            safe_title = sanitize(title)
            log(f"[DEBUG] Sanitized title: {safe_title}")

        filename_template = os.path.join(folder_path, "%(title)s.%(ext)s")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'postprocessor_args': ['-qscale:a', '0'],
            'quiet': True,
            'noplaylist': True,
        }

        log("[DEBUG] Starting audio download...")
        downloaded_file_path = None
        def hook(d):
            nonlocal downloaded_file_path
            if d['status'] == 'finished':
                downloaded_file_path = d['filename'].rsplit('.', 1)[0] + ".mp3"
                log(f"[DEBUG] yt_dlp reported downloaded path: {downloaded_file_path}")

        ydl_opts['progress_hooks'] = [hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            log(f"[ERROR] File not found: {downloaded_file_path}")
            return JSONResponse({"error": "File not found after download."})

        log(f"[INFO] Download complete: {downloaded_file_path}")
        return FileResponse(
            path=downloaded_file_path,
            filename=os.path.basename(downloaded_file_path),
            media_type="audio/mpeg"
        )

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
