from Agents.utils.state import videoState
from Agents.utils.helpers import youtube_download, extract_audio,audio_to_txt

from Agents.utils.llm import llm_cliper
from Agents.utils.prompt import SYSTEM_PROMPT
from moviepy import VideoFileClip, concatenate_videoclips

def video_preprocess(state: videoState):
    url = state.get('video_link')
    
    video_path = youtube_download(video_url=url)
    audio_path = extract_audio(path=video_path)
    
    return {
        'video_file_path': video_path,
        'audio_file_path': audio_path,
        'message': f'Audio extracted to: {audio_path}'
    }

def transcript(state: videoState):
    audio_path = state.get('audio_file_path')
    
    output = audio_to_txt(audio_path)
    
    return {
        'time_stamp': output,
        'message': 'done Transcribing'
    }

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

    return {
        'clips_transcript': clips,
        'message': 'clips time stamp done'
    }

def creating_clips(state: videoState):
    path = state.get('video_file_path')
    clips_transcript = state.get('clips_transcript')
    
    clip = VideoFileClip(path)
    
    for clip_data in clips_transcript:
        cut_clip = clip.subclipped(clip_data['start'], clip_data['end'])
        
        cut_clip.write_videofile(f"{clip_data['start']}_{clip_data['end']}.mp4")
        
    return {'message': 'video clips created'}