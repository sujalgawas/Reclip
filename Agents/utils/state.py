from typing import List, Dict
from typing_extensions import TypedDict


class videoState(TypedDict):
    video_link : str
    video_file_path : str
    audio_file_path : str
    time_stamp : List[Dict]
    clips_transcript : List[Dict]
    title : str