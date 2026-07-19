import os
import subprocess
import yt_dlp
from moviepy import AudioFileClip
from moviepy.config import FFMPEG_BINARY
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
from pathlib import Path
from faster_whisper import WhisperModel
from moviepy import AudioFileClip

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

def check_device():
    try:
        import torch
        has_cuda = torch.cuda.is_available()
    except Exception:
        has_cuda = False

    device = "cuda" if has_cuda else "cpu"
    
    return device

def youtube_download(video_url:str):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(video_url, download=False)

        file_path = os.path.abspath(ydl.prepare_filename(info))

        ydl.download([video_url])

        return file_path

def extract_audio(path:str):
    audio_path = CUR_DIR / AUDIO_NAME
    audio_path_str = str(audio_path)
    try:
        ffmpeg_extract_audio(path, audio_path_str, bitrate=192, fps=44100, logger=None)
    except Exception as exc:
        raise RuntimeError(f"Failed to extract audio from {path}: {exc}") from exc
    
    if not os.path.exists(audio_path_str):
        raise FileNotFoundError(f"Audio file was not created at {audio_path_str}")
    
    return audio_path_str


def ffmpeg_extract_subclip(inputfile, start_time, end_time, outputfile, preset='veryfast', video_codec='libx264', audio_codec='aac', audio_bitrate='192k'):
    duration = float(end_time) - float(start_time)
    if duration <= 0:
        raise ValueError('end_time must be greater than start_time')

    cmd = [
        FFMPEG_BINARY,
        '-y',
        '-ss', f'{start_time:.3f}',
        '-i', inputfile,
        '-t', f'{duration:.3f}',
        '-map', '0',
        '-c:v', video_codec,
        '-preset', preset,
        '-pix_fmt', 'yuv420p',
        '-c:a', audio_codec,
        '-b:a', audio_bitrate,
        '-movflags', '+faststart',
        outputfile,
    ]

    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed to extract subclip ({start_time}-{end_time}): {process.stderr.strip() or process.stdout.strip()}"
        )

    if not os.path.exists(outputfile):
        raise FileNotFoundError(f"Clip file was not created at {outputfile}")


def audio_to_txt(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found at {path}")
    
    with AudioFileClip(path) as audio_clip:
        duration = audio_clip.duration
    
    print(f"[Transcription] Total audio duration: {duration:.2f} seconds")
    
    segment_duration = 1800
    num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
    print(f"[Transcription] Splitting into {num_segments} segments")
    
    device = check_device()
    
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"[Transcription] Using device: {device}, compute_type: {compute_type}")
    
    model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
    
    all_segments = []
    temp_files = []
    
    try:
        for i in range(num_segments):
            print(f"\n[Transcription] Processing segment {i+1}/{num_segments}...")
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)
            
            temp_segment_path = str(CUR_DIR / f"temp_segment_{i}.mp3")
            temp_files.append(temp_segment_path)
            
            print(f"[Transcription] Extracting audio segment {i+1} ({start_time:.1f}s - {end_time:.1f}s)...")
            with AudioFileClip(path) as source_audio:
                audio_segment = source_audio.subclipped(start_time, end_time)
                try:
                    audio_segment.write_audiofile(temp_segment_path)
                finally:
                    audio_segment.close()
            
            print(f"[Transcription] Transcribing segment {i+1}...")
            segments, info = model.transcribe(
                                temp_segment_path,
                                beam_size=1,
                                language="hi",
                                task="transcribe",  
                                vad_filter=True,
                                condition_on_previous_text=False,
                                #testing prompt while transciption
                                initial_prompt="This is a gaming livestream with mixed Hindi and English speech (Hinglish), casual conversation, chat interaction."
                            )
            segments_list = list(segments)
            print(f"[Transcription] Segment {i+1} transcribed. Found {len(segments_list)} segments.")
            
            for seg in segments_list:
                all_segments.append({
                    "start": seg.start + start_time,
                    "end": seg.end + start_time,
                    "text": seg.text
                })
            print(f"[Transcription] Segment {i+1} complete. Total segments collected: {len(all_segments)}")
    
    except Exception as e:
        print(f"[Transcription] Error during transcription: {e}")
        raise
    
    finally:
        print(f"\n[Transcription] Cleaning up {len(temp_files)} temporary files...")
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
    
    print(f"[Transcription] Complete. Total segments: {len(all_segments)}")
    return all_segments