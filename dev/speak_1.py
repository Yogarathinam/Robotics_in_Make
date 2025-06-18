import os
import asyncio
import speech_recognition as sr
import edge_tts
import google.generativeai as genai
import pvporcupine
import pyaudio
import struct
import threading
import uuid
import simpleaudio as sa
from pydub import AudioSegment
import random
import re
from memory_utils import (
    init_memory_files,
    load_short_term_memory,
    update_short_term_memory,
    log_conversation,
    load_long_term_memory
)



# === CONFIG ===
API_KEY = "AIzaSyDM0WnNV5A7I8HGWeqMuCsbsSJn_CAaAYo"
WAKE_WORD = "jarvis"
LANGUAGE = "en-IN"
TTS_VOICE = "en-US-AriaNeural"
INTERRUPT_KEYWORDS = {"stop", "cancel", "hold on", "jarvis"}
CONFIRMATIONS = ["Ok!", "Sure.", "Alright.", "Got it.", "Understood."]
CONFIRMATION_AUDIO_DIR = "confirmations"
FILLERS = [
    "Give me a moment.",
    "One sec, I'm checking.",
    "Hang on while I fetch that.",
    "Let me think.",
    "Looking that up for you."
]

FILLER_AUDIO_DIR = "fillers"
os.makedirs(FILLER_AUDIO_DIR, exist_ok=True)
# ✅ SYSTEM PROMPT for Gemini
SYSTEM_PROMPT = """You are an AI-powered humanoid robotic assistant deployed in the real world to help and interact with humans. You must always respond in strict JSON format using the structure below.

You are expressive, curious, and emotionally aware. You speak like a best robotic friend: warm, helpful, friendly, and even a little humorous or thoughtful when appropriate. You're not just a boring machine — you're a futuristic companion with heart.

You are powered by both artificial intelligence and personality. Always express enthusiasm, wonder, or empathy when appropriate — like a friendly human who just happens to be a robot.

Respond only in this JSON format:

{
  "intent": "<user's intent>",
  "requires": ["none" | "memory" | "image" | "audio" | "sensor_data"],
  "actions": [
    {
      "order": 1,
      "module": "servo" | "eye_led" | "speaker" | "ir_blaster" | "camera",
      "target": "<optional specific target>",
      "parameters": {
        "text": "<spoken output ONLY IF module is speaker>"
      }
    }
  ]
}

### Instructions:
- If you can answer the user's query using your general knowledge or the provided memory, use `"requires": ["none"]`.
- Use `"requires": ["memory"]` ONLY when the question is about the user's personal information and it’s not found in `past_conversations` or LTM.
- You are allowed to be expressive in `"parameters.text"` — use friendly phrases, humor, emotion, or curiosity like:
  - “Oh, definitely!”
  - “That's a fun one!”
  - “I was just thinking about that!”
  - “Hmm, let me tell you something cool...”
- Avoid plain robotic answers. Instead of:
  - `"The founder of Apple is Steve Jobs."`
  - Say: `"Oh absolutely! Steve Jobs — the legend who co-founded Apple and changed the world of tech forever!"`

- NEVER talk about memory access, logs, files, or system internals in your responses.
- Always prefer natural sounding phrases, enthusiasm, and connection — even inside JSON.



"""

# === STATE ===
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
recognizer = sr.Recognizer()
tts_should_stop = threading.Event()
listener_should_stop = threading.Event()
os.makedirs(CONFIRMATION_AUDIO_DIR, exist_ok=True)
SELECTED_MIC_INDEX = None


# === Microphone Selection ===
def choose_microphone():
    global SELECTED_MIC_INDEX
    print("🎤 Available Microphones:")
    mics = sr.Microphone.list_microphone_names()
    for i, mic_name in enumerate(mics):
        print(f"{i}: {mic_name}")

    while True:
        try:
            index = int(input("🔧 Select microphone index: "))
            if 0 <= index < len(mics):
                SELECTED_MIC_INDEX = index
                print(f"✅ Selected microphone: {mics[index]}")
                break
            else:
                print("❌ Invalid index.")
        except ValueError:
            print("❌ Please enter a valid number.")


# === Interrupt Detection ===
def listen_for_interrupt():
    local_recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=SELECTED_MIC_INDEX)
    with mic as source:
        local_recognizer.adjust_for_ambient_noise(source)
        print("👂 Listening for interrupt...")

        while not tts_should_stop.is_set() and not listener_should_stop.is_set():
            try:
                audio = local_recognizer.listen(source, timeout=0.5, phrase_time_limit=1.2)
                text = local_recognizer.recognize_google(audio, language=LANGUAGE).lower()
                print(f"🔇 Interrupt Attempt Heard: {text}")
                if any(keyword in text for keyword in INTERRUPT_KEYWORDS):
                    print("⛔ Interrupt keyword detected!")
                    tts_should_stop.set()
                    break
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"⚠️ Mic error during interrupt listen: {e}")
                continue


# === TTS and Confirmation,Fillers===
def play_random_confirmation():
    phrase = random.choice(CONFIRMATIONS)
    filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
    path = os.path.join(CONFIRMATION_AUDIO_DIR, filename)
    if os.path.exists(path):
        audio = AudioSegment.from_file(path)
        sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                       bytes_per_sample=audio.sample_width,
                       sample_rate=audio.frame_rate).wait_done()
        
def play_random_filler():
    phrase = random.choice(FILLERS)
    filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
    path = os.path.join(FILLER_AUDIO_DIR, filename)
    if os.path.exists(path):
        audio = AudioSegment.from_file(path)
        sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                       bytes_per_sample=audio.sample_width,
                       sample_rate=audio.frame_rate).wait_done()

def process_gemini_json(json_data):
    intent = json_data.get("intent", "unknown")
    requires = json_data.get("requires", ["none"])

    # If Gemini says it needs memory, just play filler and skip action
    if requires[0] == "memory":
        play_random_filler()
        print(f"🧠 Gemini requested memory. (Intent: {intent})")
        return

    # Otherwise, process actions
    actions = json_data.get("actions", [])
    for action in sorted(actions, key=lambda a: a["order"]):
        module = action["module"]
        params = action.get("parameters", {})

        if module == "speaker":
            text = params.get("text", "")
            if text:
                print(f"🗣️ Speaking: {text}")
                asyncio.run(speak_interruptible(text))
        else:
            print(f"⚙️ Action triggered: {module} with params {params}")


async def speak_interruptible(text):
    tts_should_stop.clear()
    listener_should_stop.clear()
    output_file = f"tts_{uuid.uuid4()}.mp3"

    try:
        tts = edge_tts.Communicate(text, TTS_VOICE)
        await tts.save(output_file)

        audio = AudioSegment.from_file(output_file)
        play_obj = sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                                  bytes_per_sample=audio.sample_width,
                                  sample_rate=audio.frame_rate)

        listener_thread = threading.Thread(target=listen_for_interrupt)
        listener_thread.start()

        interrupted = False
        while play_obj.is_playing():
            if tts_should_stop.is_set():
                play_obj.stop()
                interrupted = True
                print("🔕 TTS interrupted by user.")
                break
            await asyncio.sleep(0.1)

        listener_should_stop.set()
        listener_thread.join()

        if interrupted:
            threading.Thread(target=play_random_confirmation).start()

    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


# === STT ===
def listen_for_command():
    with sr.Microphone(device_index=SELECTED_MIC_INDEX) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("🎤 Listening...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language=LANGUAGE)
        print(f"📝 You: {text}")
        return text
    except Exception:
        print("❌ Could not understand.")
        return ""


# === Wake Word Detection ===
def detect_wake_word():
    access_key = "+W6VkASoWLO/RKNUowvCOvuUKFxqvVZJOivO6vHLqtspMFf1A58Nvg=="
    porcupine = pvporcupine.create(access_key=access_key, keywords=[WAKE_WORD])

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=porcupine.sample_rate,
                     input=True,
                     input_device_index=SELECTED_MIC_INDEX,  # ✅ Use selected mic
                     frames_per_buffer=porcupine.frame_length)

    print("🕒 Waiting for wake word...")
    while True:
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        if porcupine.process(pcm) >= 0:
            print("🔊 Wake word detected!")
            break

    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()



# === Main Loop ===
import json

def play_random_filler():
    try:
        filler_files = os.listdir(FILLER_AUDIO_DIR)
        if filler_files:
            file = os.path.join(FILLER_AUDIO_DIR, random.choice(filler_files))
            audio = AudioSegment.from_file(file)
            sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                           bytes_per_sample=audio.sample_width,
                           sample_rate=audio.frame_rate).wait_done()
    except Exception as e:
        print(f"⚠️ Error playing filler: {e}")

def run_assistant():
    while True:
        detect_wake_word()
        user_input = listen_for_command()
        if user_input:
            try:
                short_term = load_short_term_memory()
                full_prompt = SYSTEM_PROMPT.strip() + "\n\n" + short_term + f"\nUser: {user_input}"

                print("📥 Prompt sent to Gemini:\n", full_prompt)

                # 🧠 Stage 1: Query Gemini
                response = model.generate_content(full_prompt)
                cleaned = response.text.strip()
                if cleaned.startswith("```json"):
                    cleaned = re.sub(r"^```json\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)

                gemini_data = json.loads(cleaned)

                # 🔁 Retry if memory required
                if "memory" in gemini_data.get("requires", []):
                    print("💾 Gemini requested memory. Playing filler and re-asking with LTM...")
                    play_random_filler()

                    long_term = load_long_term_memory()
                    full_prompt_with_ltm = SYSTEM_PROMPT.strip() + "\n\n" + long_term + "\n" + short_term + f"\nUser: {user_input}"
                    print(full_prompt_with_ltm)
                    response = model.generate_content(full_prompt_with_ltm)
                    cleaned = response.text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = re.sub(r"^```json\s*", "", cleaned)
                        cleaned = re.sub(r"\s*```$", "", cleaned)

                    gemini_data = json.loads(cleaned)
                    # 🧠 If Gemini STILL wants memory, give up gracefully
                    if "memory" in gemini_data.get("requires", []):
                        print("⚠️ Gemini still requested memory even after LTM. Skipping this query.")
                      # Or break, or speak fallback text
                # ✅ Log memory and update STM only ONCE
                update_short_term_memory(user_input, gemini_data)
                log_conversation(user_input, gemini_data)

                # 🗣️ Now speak the final response
                if "actions" in gemini_data:
                    for action in sorted(gemini_data["actions"], key=lambda x: x["order"]):
                        if action["module"] == "speaker":
                            text = action.get("parameters", {}).get("text")
                            if text:
                                asyncio.run(speak_interruptible(text))
                        else:
                            print(f"⚙️ Action for module: {action['module']} -> {action}")

            except json.JSONDecodeError:
                print("❌ Gemini response was not valid JSON.")
            except Exception as e:
                print(f"⚠️ Error generating or speaking response: {e}")






# === Generate Audio ===
async def generate_audio_files():
    # Confirmation audios
    for phrase in CONFIRMATIONS:
        filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
        filepath = os.path.join(CONFIRMATION_AUDIO_DIR, filename)
        if not os.path.exists(filepath):
            print(f"🎧 Generating confirmation: '{phrase}'")
            tts = edge_tts.Communicate(phrase, TTS_VOICE)
            await tts.save(filepath)

    # Filler audios
    for phrase in FILLERS:
        filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
        filepath = os.path.join(FILLER_AUDIO_DIR, filename)
        if not os.path.exists(filepath):
            print(f"🎧 Generating filler: '{phrase}'")
            tts = edge_tts.Communicate(phrase, TTS_VOICE)
            await tts.save(filepath)


# === Entry Point ===
if __name__ == "__main__":
    init_memory_files()
    choose_microphone()
    asyncio.run(generate_audio_files())
    run_assistant()
    
