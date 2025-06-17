import os
import json

# === Config ===
STM_FILE = "short_term_memory.json"
LOG_FILE = "convo_log.json"
MAX_STM = 4

# === Ensure files exist at startup ===
def init_memory_files():
    for path in [STM_FILE, LOG_FILE]:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)


# === Compress Gemini JSON into STM-friendly format ===
def compress_gemini_response(response_json):
    output_lines = []
    actions = response_json.get("actions", [])
    for action in sorted(actions, key=lambda x: x.get("order", 0)):
        order = f"O{action['order']}"
        module = action.get("module", "unknown")
        params = action.get("parameters", {})

        if module == "speaker":
            value = params.get("text", "")
        else:
            value = json.dumps(params, separators=(",", ":"))  # minified

        line = f"{order}:{module}:{value}"
        output_lines.append(line)

    return "\n".join(output_lines)


# === Save STM: Keeps only last MAX_STM entries ===
def update_short_term_memory(user_input, gemini_response):
    entry = {
        "user": user_input,
        "assistant": compress_gemini_response(gemini_response)
    }

    if not os.path.exists(STM_FILE):
        with open(STM_FILE, "w") as f:
            json.dump([], f)

    with open(STM_FILE, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

        data.append(entry)
        if len(data) > MAX_STM:
            data.pop(0)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


# === Get STM to prepend in prompt ===
def load_short_term_memory():
    if not os.path.exists(STM_FILE):
        return ""

    with open(STM_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return ""

    lines = []
    for entry in data:
        lines.append(f"user: {entry['user']}")
        lines.append(f"assistant: {entry['assistant']}")
    return "\n".join(lines)


# === Log full conversation for long-term archive ===
def log_conversation(user_input, gemini_raw_json):
    entry = {
        "user": user_input,
        "assistant": gemini_raw_json
    }

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

    with open(LOG_FILE, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
