"""Usage statistics tracking and persistence."""
import json
import os
import re
from typing import Optional


def get_stats_file_path() -> str:
    """Get the path to the stats JSON file."""
    return os.path.expanduser("~/.sensei/stats.json")


def parse_commit_type(message: str) -> str:
    """Parse commit type from message."""
    cleaned = re.sub(r'^(?:\:\w+\:|[\U00010000-\U0010ffff]\s*)\s*', '', message.strip())
    match = re.match(r'^([a-zA-Z0-9_-]+)', cleaned)
    if match:
        return match.group(1).lower()
    return "unknown"


def record_commit_stat(provider: str, decision: str, commit_type: str, message_len: int) -> None:
    """Record a commit attempt, type, provider and accept/reject decision."""
    path = get_stats_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    stats = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass
            
    stats["generated_attempts"] = stats.get("generated_attempts", 0) + 1
    
    decisions = stats.setdefault("decisions", {"accepted": 0, "rejected": 0})
    decisions[decision] = decisions.get(decision, 0) + 1
    
    providers = stats.setdefault("providers", {})
    providers[provider] = providers.get(provider, 0) + 1
    
    types = stats.setdefault("types", {})
    types[commit_type] = types.get(commit_type, 0) + 1
    
    # Calculate rolling average message length
    total_len_sum = stats.get("total_message_length_sum", 0) + message_len
    stats["total_message_length_sum"] = total_len_sum
    stats["average_message_length"] = round(total_len_sum / stats["generated_attempts"])
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass


def load_stats() -> dict:
    """Load stats from the JSON file. Returns empty dict if not found."""
    path = get_stats_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def clear_stats() -> bool:
    """Clear the stats file. Returns True if successful."""
    path = get_stats_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception:
            return False
    return True
