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
from pydub.playback import play
import random

# === CONFIG ===
API_KEY = "AIzaSyDM0WnNV5A7I8HGWeqMuCsbsSJn_CAaAYo"
WAKE_WORD = "jarvis"
LANGUAGE = "en-IN"
TTS_VOICE = "en-US-AriaNeural"
INTERRUPT_KEYWORDS = {"stop", "cancel", "hold on", "jarvis"}

# Confirmation setup
CONFIRMATIONS = ["Ok!", "Sure.", "Alright.", "Got it.", "Understood."]
CONFIRMATION_AUDIO_DIR = "confirmations"

# === SETUP ===
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
recognizer = sr.Recognizer()
tts_should_stop = threading.Event()
os.makedirs(CONFIRMATION_AUDIO_DIR, exist_ok=True)


# === Speak with Interrupt ===
def listen_for_interrupt():
    local_recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        local_recognizer.adjust_for_ambient_noise(source)
        try:
            print("👂 Listening for interrupt...")
            audio = local_recognizer.listen(source, timeout=5)
            text = local_recognizer.recognize_google(audio, language=LANGUAGE).lower()
            print(f"🔇 Interrupt Attempt Heard: {text}")
            if any(keyword in text for keyword in INTERRUPT_KEYWORDS):
                print("⛔ Interrupt keyword detected!")
                tts_should_stop.set()
        except Exception:
            print("⚠️ No valid interrupt heard.")


def play_random_confirmation():
    phrase = random.choice(CONFIRMATIONS)
    filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
    path = os.path.join(CONFIRMATION_AUDIO_DIR, filename)
    if os.path.exists(path):
        audio = AudioSegment.from_file(path)
        sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                       bytes_per_sample=audio.sample_width,
                       sample_rate=audio.frame_rate).wait_done()


async def speak_interruptible(text):
    tts_should_stop.clear()
    output_file = f"tts_{uuid.uuid4()}.mp3"
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

    listener_thread.join()
    os.remove(output_file)

    if interrupted:
        threading.Thread(target=play_random_confirmation).start()


# === STT ===
def listen_for_command():
    with sr.Microphone() as source:
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
    access_key = "+W6VkASoWLO/RKNUowvCOvuUKFxqvVZJOivO6vHLqtspMFf1A58Nvg=="  # ← your Porcupine access key
    porcupine = pvporcupine.create(access_key=access_key, keywords=[WAKE_WORD])

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=porcupine.sample_rate,
                     input=True,
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
def run_assistant():
    while True:
        detect_wake_word()
        user_input = listen_for_command()
        if user_input:
            response = model.generate_content(user_input)
            print(f"🤖 Gemini: {response.text}")
            asyncio.run(speak_interruptible(response.text))


# === Pre-generate confirmation audios ===
async def generate_confirmation_audios():
    for phrase in CONFIRMATIONS:
        filename = phrase.lower().replace("!", "").replace(".", "").replace(" ", "_") + ".mp3"
        filepath = os.path.join(CONFIRMATION_AUDIO_DIR, filename)
        if not os.path.exists(filepath):
            print(f"🎧 Generating '{phrase}' confirmation audio...")
            tts = edge_tts.Communicate(phrase, TTS_VOICE)
            await tts.save(filepath)


# === Entry Point ===
if __name__ == "__main__":
    asyncio.run(generate_confirmation_audios())
    run_assistant()
