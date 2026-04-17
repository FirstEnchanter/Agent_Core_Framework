import json
import os
from datetime import datetime

# Path to the local usage database
USAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "usage.json")

def _load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                pass
    return {"openai_cost": 0.0, "gemini_cost": 0.0, "openai_tokens": 0, "gemini_tokens": 0}

def _save_usage(data):
    with open(USAGE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def log_openai_usage(prompt_tokens, completion_tokens, model="gpt-4o"):
    """
    Log OpenAI usage and estimate cost locally.
    Call this inside your bots right after getting an API response.
    """
    # Rough estimate costs for gpt-4o
    cost_prompt = (prompt_tokens / 1000.0) * 0.005
    cost_comp = (completion_tokens / 1000.0) * 0.015
    total_cost = cost_prompt + cost_comp
    
    data = _load_usage()
    data["openai_tokens"] += (prompt_tokens + completion_tokens)
    data["openai_cost"] += total_cost
    _save_usage(data)

def log_gemini_usage(prompt_tokens, completion_tokens, model="gemini-1.5-pro"):
    """
    Log Gemini AI usage and estimate cost locally.
    """
    # Rough estimate costs for gemini-1.5-pro
    cost_prompt = (prompt_tokens / 1000000.0) * 1.25 # Adjust as needed
    cost_comp = (completion_tokens / 1000000.0) * 3.75
    total_cost = cost_prompt + cost_comp
    
    data = _load_usage()
    data["gemini_tokens"] += (prompt_tokens + completion_tokens)
    data["gemini_cost"] += total_cost
    _save_usage(data)
