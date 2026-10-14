"""Portable configuration for the released synthetic memory mechanism."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def seal(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def protocol():
    return dict(max_read_rounds=3, search_top_k=3, external_read_budget=8192,
                controller_output_tokens=256, node_initial_top_k=3, node_next_top_k=3)
