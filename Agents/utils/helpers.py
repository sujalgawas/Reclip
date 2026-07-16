import os
import yt_dlp
from moviepy import VideoFileClip, AudioFileClip
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
    
    audio.write_audiofile(audio_path_str)
    
    audio.close()
    video.close()
    
    if not os.path.exists(audio_path_str):
        raise FileNotFoundError(f"Audio file was not created at {audio_path_str}")
    
    return audio_path_str

def audio_to_txt(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found at {path}")
    
    from moviepy import AudioFileClip
    audio_clip = AudioFileClip(path)
    duration = audio_clip.duration
    audio_clip.close()
    
    print(f"[Transcription] Total audio duration: {duration:.2f} seconds")
    
    segment_duration = 600
    num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
    print(f"[Transcription] Splitting into {num_segments} segments")
    
    try:
        import torch
        has_cuda = torch.cuda.is_available()
    except Exception:
        has_cuda = False

    device = "cuda" if has_cuda else "cpu"
    compute_type = "float16" if has_cuda else "float32"
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
            audio_segment = AudioFileClip(path).subclipped(start_time, end_time)
            audio_segment.write_audiofile(temp_segment_path)
            audio_segment.close()
            
            print(f"[Transcription] Transcribing segment {i+1}...")
            segments, info = model.transcribe(temp_segment_path, beam_size=1)
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