from langgraph.graph import StateGraph,START,END 
from Agents.utils.state import videoState
from Agents.utils.node import video_preprocess,title,transcript,llm_classification,creating_clips

def get_agent_graph():
    graph = StateGraph(videoState)
    
    graph.add_node(video_preprocess)
    graph.add_node(transcript)
    graph.add_node(llm_classification)
    graph.add_node(title)
    graph.add_node(creating_clips)
    
    
    graph.add_edge(START,'video_preprocess')
    graph.add_edge('video_preprocess','transcript')
    graph.add_edge('transcript','llm_classification')
    graph.add_edge('llm_classification','title')
    graph.add_edge('title','creating_clips')
    graph.add_edge('creating_clips',END)
    
    app = graph.compile()
    
    return app