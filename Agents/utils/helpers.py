import os
import yt_dlp
from moviepy.editor import VideoFileClip
from pathlib import Path
from faster_whisper import WhisperModel

YDL_OPTS = {
    "format": "bestvideo+bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s"
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
    
    audio.write_audiofile(audio_path)
    
    audio.close()
    video.close()
    
    return audio_path

def audio_to_txt(path):
    model = WhisperModel(MODEL_SIZE, device='cpu', compute_type='int8')

    segments, info = model.transcribe(path, beam_size=5)

    time_stamp = [
        {"start": seg.start, "end": seg.end, "text": seg.text}
        for seg in segments
    ]

    return time_stamp