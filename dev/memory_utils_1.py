import os
import json
import requests
import threading

# === Config ===
STM_FILE = "short_term_memory.json"
LOG_FILE = "convo_log.json"
LTM_FILE = "long_term_memory.json"
MAX_STM = 4
SUMMARY_TRIGGER_COUNT = 4  # Trigger summarization every 4 logs

# === DeepSeek Config ===
DEEPSEEK_API_KEY = "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"  # Replace with actual key
DEEPSEEK_MODEL = "deepseek/deepseek-chat-v3-0324:free"
HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost",
    "X-Title": "ltm-summarizer"
}


def init_memory_files():
    for path in [STM_FILE, LOG_FILE, LTM_FILE]:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)


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
            value = json.dumps(params, separators=(",", ":"))

        line = f"{order}:{module}:{value}"
        output_lines.append(line)

    return "\n".join(output_lines)


def update_short_term_memory(user_input, gemini_response):
    entry = {
        "user": user_input,
        "assistant": compress_gemini_response(gemini_response)
    }

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


def load_long_term_memory():
    if not os.path.exists(LTM_FILE):
        return ""

    with open(LTM_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return ""

    return "\n".join(data)  # data is a list of summaries


def log_conversation(user_input, gemini_raw_json):
    entry = {
        "user": user_input,
        "assistant": gemini_raw_json
    }

    with open(LOG_FILE, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

        # Background summarization trigger
        if len(data) % SUMMARY_TRIGGER_COUNT == 0:
            threading.Thread(target=summarize_and_store_ltm, daemon=True).start()


# === DeepSeek summarization and store to LTM ===
def summarize_and_store_ltm():
    with open(LOG_FILE, "r") as f:
        try:
            log_data = json.load(f)
        except json.JSONDecodeError:
            return

    if not log_data:
        return

    recent = log_data[-SUMMARY_TRIGGER_COUNT:]
    log_text = "\n".join([
        f"User: {e['user']}\nAssistant: {json.dumps(e['assistant'], indent=2)}"
        for e in recent
    ])

    prompt = [
        {"role": "system", "content": """You are a memory-processing assistant for a humanoid AI robot system. Your job is to process past conversation logs between a user and a robotic assistant (formatted as JSON dialogues) and extract only the **factual and useful personal memory information**.

🧠 Your task is to simulate a Long-Term Memory (LTM) summary, which will be used by a robotic AI (Gemini) to answer user questions in the future. The assistant will receive this summary as part of its system prompt.

🎯 Output only simple, short, factual sentences — one fact per line. Do not use headings, markdown, lists, or extra commentary. No summaries or metadata.

✅ Include:
- User's name if shared ("Your name is...")
- Native place or location
- Preferences or favorite items
- Recalled personal facts
- Any direct answers the user has given about themselves

🚫 Do NOT include:
- General knowledge (e.g., “India is in Asia”)
- Assistant responses unless they include a personal fact
- Dialogue format, timestamps, system messages, or JSON structure
- Speculative or unclear statements

🔄 Format:
Only use **plain natural language** sentences for facts. Keep each line complete and standalone.

🧾 Example output:
 """ },
        {"role": "user", "content": log_text}
    ]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=HEADERS,
            json={"model": DEEPSEEK_MODEL, "messages": prompt}
        )

        if response.status_code == 200:
            summary = response.json()["choices"][0]["message"]["content"]
            store_ltm_summary(summary)
        else:
            print(f"[LTM] ❌ DeepSeek error: {response.status_code}")
    except Exception as e:
        print(f"[LTM] ❌ Failed to summarize: {e}")


def store_ltm_summary(summary_text):
    if not summary_text:
        return

    with open(LTM_FILE, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

        data.append(summary_text)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
