from typing import List, Dict, Optional
from typing_extensions import TypedDict


class videoState(TypedDict, total=False):
    video_link: str
    video_file_path: str
    audio_file_path: str
    time_stamp: List[Dict]
    clips_transcript: List[Dict]
    clips_with_title: List[Dict]
    output_title : list[Dict]
    error: Optional[str]
    message: Optional[str]