import json, hashlib, time, os
from typing import Any, Dict, List
from kernel.config import OPTIMIZATION

STATE_FILE = "pipeline_state.json"
CACHE_FILE = "token_cache.json"

def hash_payload(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

def load_cache() -> Dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_cache(cache: Dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(cache, f)

def load_state() -> Dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"run_id": hash_payload(time.time()), "stage": "INIT", "artifacts": {}, "token_budget": 0, "timestamp": time.time()}

def save_state(state: Dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump(state, f, indent=2)

def trim_context(messages: List[Dict], max_pct: float = 0.8) -> List[Dict]:
    # Simple heuristic: keep system + last N user/assistant turns
    if len(messages) <= 3: return messages
    keep = int(len(messages) * max_pct)
    return [messages[0]] + messages[-keep:]

def validate_json(text: str, schema: Dict = None) -> Dict:
    text = text.strip()
    # Remove markdown if present
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part_clean = part.strip()
            if part_clean.startswith("json"):
                part_clean = part_clean[4:].strip()
            try:
                data = json.loads(part_clean)
                if schema:
                    for k in schema.get("required", []):
                        if k not in data: raise ValueError(f"Missing key: {k}")
                return data
            except Exception:
                continue
    try:
        data = json.loads(text)
        if schema:
            # Basic schema validation (keys existence)
            for k in schema.get("required", []):
                if k not in data: raise ValueError(f"Missing key: {k}")
        return data
    except Exception as e:
        raise ValueError(f"Invalid JSON: {e}")

def compress_json(data: Dict) -> str:
    if OPTIMIZATION["json_compression"]:
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)
