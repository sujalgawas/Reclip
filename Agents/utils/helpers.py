import os
import yt_dlp
from moviepy import VideoFileClip
from pathlib import Path
from faster_whisper import WhisperModel

YDL_OPTS = {
    "format": "bestvideo+bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    },
    "socket_timeout": 30,
    "quiet": False,
    "no_warnings": False
}

AUDIO_NAME = "extracted_audio.mp3"

CUR_DIR = Path(__file__).resolve().parent

MODEL_SIZE = 'tiny'

def youtube_download(video_url:str):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(video_url, download=False)

        file_path = os.path.abspath(ydl.prepare_filename(info))

        ydl.download([video_url])

        return file_path

def extract_audio(path:str):
    video = VideoFileClip(path)
    
    audio = video.audio
    
    audio_path = CUR_DIR / AUDIO_NAME
    audio_path_str = str(audio_path)
    
    # Write audio file
    audio.write_audiofile(audio_path_str)
    
    audio.close()
    video.close()
    
    # Verify file exists before returning
    if not os.path.exists(audio_path_str):
        raise FileNotFoundError(f"Audio file was not created at {audio_path_str}")
    
    return audio_path_str

def audio_to_txt(path):
    # Verify file exists before processing
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found at {path}")
    
    model = WhisperModel(MODEL_SIZE, device='cpu', compute_type='int8')

    segments, info = model.transcribe(path, beam_size=5)

    time_stamp = [
        {"start": seg.start, "end": seg.end, "text": seg.text}
        for seg in segments
    ]

    return time_stamp