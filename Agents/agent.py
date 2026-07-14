from langgraph.graph import StateGraph,START,END
from utils.state import videostate
from utils.node import video_preprocess,transcript,llm_classification,creating_clips

def get_agent_graph():
    graph = StateGraph(videostate)
    
    graph.add_node(video_preprocess)
    graph.add_node(transcript)
    graph.add_node(llm_classification)
    graph.add_node(creating_clips)
    
    graph.add(START,'video_preprocess')
    graph.add('video_preprocess','transcript')
    graph.add('transcript','llm_classification')
    graph.add('llm_classification','creating_clips')
    graph.add('creating_clips',END)
    
    app = graph.compile()
    
    return app