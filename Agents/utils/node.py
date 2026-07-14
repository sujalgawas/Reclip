from langchain.messages import ToolMessage
from state import videoState
from helpers import youtube_download, extract_audio,audio_to_txt
from llm import llm_cliper
from prompt import SYSTEM_PROMPT
from moviepy.editor import VideoFileClip, concatenate_videoclips

def video_preprocess(state: videoState):
    url = state.get('video_link')
    
    video_path = youtube_download(video_url=url)
    audio_path = extract_audio(path=video_path)
    
    state['video_file_path'] = video_path
    state['audio_file_path'] = audio_path
    
    #implement silero_vad in future
    
    return {'message':audio_path}

def transcript(state: videoState):
    audio_path = state.get('audio_file_path')
    
    output = audio_to_txt(audio_path)
    
    state['time_stamp'] = output
    
    return {"message":"done Transcribing"}

def llm_classification(state: videoState):
    time_stamp = state.get('time_stamp')

    chunk = []
    clips = []

    for segment in time_stamp:
        chunk.append(segment)

        if len(chunk) == 40:
            output = llm_cliper(system_prompt=SYSTEM_PROMPT, query=chunk)
            clips.extend(output)
            chunk = []

    if chunk:
        output = llm_cliper(system_prompt=SYSTEM_PROMPT, query=chunk)
        clips.extend(output)

    state['clips_transcript'] = clips

    return {"message": "clips time stamp done"}

def creating_clips(state: videoState):
    path = state.get('video_file_path')
    clips_transcript = state.get('clips_transcript')
    
    clip = VideoFileClip(path)
    
    for clips in clips_transcript:
        cut_clip = clip.subclip(clips.start,clips.end)
        
        cut_clip.write_videofile(f"{clips.start}_{clips.end}.mp4")
        
    return {"message": "video clips created"}