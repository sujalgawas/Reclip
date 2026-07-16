import ollama
import json

MODEL = "qwen2.5:3b-instruct"

OPT={
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 40,
    "num_ctx": 8192,
    "num_predict": 4096,
    "repeat_penalty": 1.1,
    "seed": 42,
}

def llm_cliper(system_prompt, query):
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "start": {"type": "number"},
                "end": {"type": "number"},
                "text": {"type": "string"}
            },
            "required": ["start", "end", "text"]
        }
    }

    response = ollama.chat(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': json.dumps(query)}
        ],
        stream=False,
        format=schema,
        options=OPT
    )

    return json.loads(response['message']['content'])