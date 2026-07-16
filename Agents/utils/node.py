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
    print("\n[Transcript Node] Starting transcription node...")
    audio_path = state.get('audio_file_path')
    
    output = audio_to_txt(audio_path)
    print(f"[Transcript Node] Transcription complete. Got {len(output)} segments.\n")
    
    return {
        'time_stamp': output,
        'message': 'done Transcribing'
    }

def llm_classification(state: videoState):
    print("\n[LLM Classification] Starting classification...")
    time_stamp = state.get('time_stamp')
    print(f"[LLM Classification] Processing {len(time_stamp)} segments...")

    chunk = []
    clips = []
    chunk_num = 0

    try:
        for idx, segment in enumerate(time_stamp):
            chunk.append(segment)

            if len(chunk) == 40:
                chunk_num += 1
                print(f"[LLM Classification] Sending chunk {chunk_num} to LLM ({len(chunk)} segments)...")
                try:
                    output = llm_cliper(system_prompt=SYSTEM_PROMPT, query=chunk)
                    clips.extend(output)
                    print(f"[LLM Classification] Chunk {chunk_num} complete. Got {len(output)} clips.")
                except Exception as e:
                    print(f"[LLM Classification] Error processing chunk {chunk_num}: {e}")
                    raise
                chunk = []

        if chunk:
            chunk_num += 1
            print(f"[LLM Classification] Sending final chunk {chunk_num} to LLM ({len(chunk)} segments)...")
            try:
                output = llm_cliper(system_prompt=SYSTEM_PROMPT, query=chunk)
                clips.extend(output)
                print(f"[LLM Classification] Final chunk complete. Got {len(output)} clips.")
            except Exception as e:
                print(f"[LLM Classification] Error processing final chunk: {e}")
                raise

        print(f"[LLM Classification] Classification complete. Total clips: {len(clips)}")
    except Exception as e:
        print(f"[LLM Classification] Fatal error: {e}")
        raise

    return {
        'clips_transcript': clips,
        'message': 'clips time stamp done'
    }

def creating_clips(state: videoState):
    print("\n[Creating Clips Node] Starting clip creation...")
    path = state.get('video_file_path')
    clips_transcript = state.get('clips_transcript')
    print(f"[Creating Clips Node] Creating {len(clips_transcript)} clips...")
    
    try:
        clip = VideoFileClip(path)
        
        for idx, clip_data in enumerate(clips_transcript):
            print(f"[Creating Clips Node] Creating clip {idx+1}/{len(clips_transcript)}...")
            cut_clip = clip.subclipped(clip_data['start'], clip_data['end'])
            
            output_file = f"{clip_data['start']}_{clip_data['end']}.mp4"
            cut_clip.write_videofile(output_file)
            print(f"[Creating Clips Node] Saved clip to {output_file}")
        
        print("[Creating Clips Node] All clips created successfully!")
        return {'message': 'video clips created'}
    except Exception as e:
        print(f"[Creating Clips Node] Error creating clips: {e}")
        raise