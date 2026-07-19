import ollama
import json
import re
from groq import Groq
from groq import RateLimitError, APIError
from dotenv import load_dotenv
import os

from Agents.utils.prompt import JSON_WRAPPER_INSTRUCTION

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

GROQ_CLIENT = Groq(api_key=API_KEY)

GROQ_MODEL_PRIMARY = "openai/gpt-oss-120b"
GROQ_MODEL_SECONDARY = "llama-3.3-70b-versatile"
LOCAL_MODEL = "qwen2.5:3b-instruct"

TEMPERATURE = 0.1
TOP_P = 0.9

LOCAL_OPT = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": 20,
    "num_ctx": 8192,
    "num_predict": 4096,
    "repeat_penalty": 1.1,
    "seed": 42,
}

CLIP_SCHEMA = {
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


def _parse_llm_json(content):
    """Parse raw LLM string output into Python data, handling markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r'^```(json)?\s*|\s*```$', '', content, flags=re.M).strip()
    return json.loads(content)


def _normalize_clip_item(item):
    try:
        return {
            'start': float(item['start']),
            'end': float(item['end']),
            'text': str(item['text']),
            'category': str(item.get('category', 'unknown'))
        }
    except (KeyError, TypeError, ValueError):
        return None


def normalize_clips(raw_output, wrapped=True):
    """
    wrapped=True  -> expects {"clips": [...]}   (Groq, json_object mode)
    wrapped=False -> expects [...] directly      (Ollama, array schema mode)
    """
    if isinstance(raw_output, str):
        try:
            raw_output = _parse_llm_json(raw_output)
        except json.JSONDecodeError:
            print(f"[normalize_clips] failed to parse JSON, raw: {raw_output[:300]}")
            return []

    clip_list = raw_output.get('clips', []) if wrapped else raw_output

    if not isinstance(clip_list, list):
        print(f"[normalize_clips] 'clips' was not a list: {type(clip_list)}")
        return []

    normalized = [c for item in clip_list if (c := _normalize_clip_item(item)) is not None]
    return normalized

def call_groq(model_name, system_prompt, query):
    full_prompt = system_prompt + "\n" + JSON_WRAPPER_INSTRUCTION
    response = GROQ_CLIENT.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": json.dumps(query)}
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return normalize_clips(content, wrapped=True)


def call_local(system_prompt, query):
    response = ollama.chat(
        model=LOCAL_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': json.dumps(query)}
        ],
        stream=False,
        format=CLIP_SCHEMA,
        options=LOCAL_OPT
    )
    content = response['message']['content']
    return normalize_clips(content, wrapped=False)

def llm_cliper(system_prompt, query):
    try:
        print(f"[llm_cliper] trying {GROQ_MODEL_PRIMARY}...")
        return call_groq(GROQ_MODEL_PRIMARY, system_prompt, query)
    except (RateLimitError, APIError) as e:
        print(f"[llm_cliper] groq 70b failed: {e}")

    try:
        print(f"[llm_cliper] trying {GROQ_MODEL_SECONDARY}...")
        return call_groq(GROQ_MODEL_SECONDARY, system_prompt, query)
    except (RateLimitError, APIError) as e:
        print(f"[llm_cliper] groq 8b failed: {e}")

    print("[llm_cliper] falling back to local qwen2.5:3b...")
    return call_local(system_prompt, query)