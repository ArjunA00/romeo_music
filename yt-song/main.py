from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
import yt_dlp
import uuid
import os

app = FastAPI()

BASE_DIR = "downloads"  # all MP3s will go under this

@app.get("/", response_class=HTMLResponse)
def form():
    return """
        <form action="/download" method="post">
            YouTube URL: <input name="url" type="text" /><br>
            Folder Name: <input name="folder" type="text" /><br>
            <button type="submit">Download MP3</button>
        </form>
    """

@app.post("/download")
def download(url: str = Form(...), folder: str = Form(...), background_tasks: BackgroundTasks = None):
    folder_path = os.path.join(BASE_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)

    output_filename = f"{uuid.uuid4()}.mp3"
    full_path = os.path.join(folder_path, output_filename)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': full_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            # Remove 'preferredquality' to keep best quality
        }],
        'postprocessor_args': ['-qscale:a', '0'],  # VBR (best quality)
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Optional: schedule cleanup
    if background_tasks:
        background_tasks.add_task(os.remove, full_path)

    return FileResponse(path=full_path, filename="audio.mp3", media_type='audio/mpeg')
