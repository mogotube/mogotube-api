from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import yt_dlp
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIES = "/app/cookies.txt"

COMMON_OPTS = {
    "cookiefile": COOKIES,
    "quiet": True,
    "retries": 10,
    "fragment_retries": 10,
    "ignoreerrors": False,
    "nocheckcertificate": True,
    "socket_timeout": 30,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
}

@app.get("/")
def root():
    existe = os.path.exists(COOKIES)
    return {"status": "MogoTube API corriendo", "cookies_encontradas": existe}

@app.get("/download")
def download(url: str = Query(...), fmt: str = Query("mp4"), quality: str = Query("720")):
    try:
        tmpdir = tempfile.mkdtemp()

        if fmt == "mp3":
            ydl_opts = {
                **COMMON_OPTS,
                "format": "bestaudio/best",
                "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        elif fmt == "wav":
            ydl_opts = {
                **COMMON_OPTS,
                "format": "bestaudio/best",
                "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }],
            }
        else:
            ydl_opts = {
                **COMMON_OPTS,
                "format": "best[ext=mp4]/best",
                "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
                "merge_output_format": "mp4",
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")

        files = os.listdir(tmpdir)
        if not files:
            return JSONResponse({"error": "No se pudo descargar"}, status_code=500)

        filepath = os.path.join(tmpdir, files[0])
        ext = files[0].split(".")[-1]

        def iterfile():
            with open(filepath, "rb") as f:
                yield from f
            os.remove(filepath)

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        filename = f"{safe_title}.{ext}"

        return StreamingResponse(
            iterfile(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
