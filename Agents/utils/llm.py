import ollama
import json
import re
from groq import Groq
from groq import RateLimitError, APIError
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

# --- Global config ---
GROQ_CLIENT = Groq(api_key=API_KEY)

GROQ_MODEL_PRIMARY = "openai/gpt-oss-120b"
GROQ_MODEL_SECONDARY = "llama-3.3-70b-versatile"
LOCAL_MODEL = "qwen2.5:3b-instruct"

LOCAL_OPT = {
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 40,
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


def _normalize_clip_item(item):
    if not isinstance(item, dict):
        return None
    if not all(k in item for k in ('start', 'end', 'text')):
        return None

    try:
        start = float(item['start'])
        end = float(item['end'])
    except (TypeError, ValueError):
        return None

    return {
        'start': start,
        'end': end,
        'text': str(item['text'])
    }


def _find_candidate_list(raw_output):
    if isinstance(raw_output, list):
        return raw_output

    if isinstance(raw_output, dict):
        if all(k in raw_output for k in ('start', 'end', 'text')):
            return [raw_output]

        known_keys = ('clips', 'output', 'results', 'data', 'items', 'value', 'responses')
        for key in known_keys:
            if key in raw_output and isinstance(raw_output[key], list):
                return raw_output[key]

        for value in raw_output.values():
            if isinstance(value, list):
                if any(isinstance(item, dict) and all(k in item for k in ('start', 'end', 'text')) for item in value):
                    return value

        for value in raw_output.values():
            if isinstance(value, (dict, str)):
                candidate = _find_candidate_list(value)
                if candidate is not None:
                    return candidate

    return None


def _normalize_llm_output(raw_output):
    if isinstance(raw_output, str):
        try:
            parsed = json.loads(raw_output)
            raw_output = parsed
        except json.JSONDecodeError:
            array_match = re.search(r'(\[.*\])', raw_output, re.S)
            if array_match:
                try:
                    raw_output = json.loads(array_match.group(1))
                except json.JSONDecodeError:
                    raw_output = None
            else:
                object_match = re.search(r'(\{.*\})', raw_output, re.S)
                if object_match:
                    try:
                        raw_output = json.loads(object_match.group(1))
                    except json.JSONDecodeError:
                        raw_output = None
                else:
                    raw_output = None

    if raw_output is None:
        return []

    candidate = _find_candidate_list(raw_output)
    if candidate is None:
        return []

    normalized = []
    for item in candidate:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue

        normalized_item = _normalize_clip_item(item)
        if normalized_item is not None:
            normalized.append(normalized_item)

    return normalized


def call_groq(model_name, system_prompt, query):
    response = GROQ_CLIENT.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(query)}
        ],
        temperature=0.2,
        top_p=0.9,
        response_format={"type": "json_object"},  # groq wants an object, not bare array — see note below
    )
    content = response.choices[0].message.content
    normalized = _normalize_llm_output(content)
    if not normalized:
        raw_content = content if isinstance(content, str) else json.dumps(content, default=str)
        print(f"[llm_cliper] warning: groq returned no valid clips; raw content starts with: {raw_content[:1000]}")
    return normalized


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
    normalized = _normalize_llm_output(content)
    if not normalized:
        raw_content = content if isinstance(content, str) else json.dumps(content, default=str)
        print(f"[llm_cliper] warning: local model returned no valid clips; raw content starts with: {raw_content[:1000]}")
    return normalized


def llm_cliper(system_prompt, query):
    # 1. try groq 70b
    try:
        print(f"[llm_cliper] trying {GROQ_MODEL_PRIMARY}...")
        return call_groq(GROQ_MODEL_PRIMARY, system_prompt, query)
    except (RateLimitError, APIError) as e:
        print(f"[llm_cliper] groq 70b failed: {e}")

    # 2. try groq 8b
    try:
        print(f"[llm_cliper] trying {GROQ_MODEL_SECONDARY}...")
        return call_groq(GROQ_MODEL_SECONDARY, system_prompt, query)
    except (RateLimitError, APIError) as e:
        print(f"[llm_cliper] groq 8b failed: {e}")

    # 3. fallback to local
    print("[llm_cliper] falling back to local qwen2.5:3b...")
    return call_local(system_prompt, query)