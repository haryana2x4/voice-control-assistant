import os
import json
import subprocess
import sys
import threading
import time

import pyttsx3
import speech_recognition as sr

# ------------------------------------------------------------
# Simple Voice‑Controlled Assistant for Windows
# ------------------------------------------------------------
# Features
#   • Listen to the microphone and convert speech to text.
#   • Match the spoken phrase against a small command catalog.
#   • Execute the corresponding action (open apps, run files, type text).
#   • If the assistant makes a mistake, you can correct it and the
#     correction is persisted in `commands.json` – a very lightweight
#     “training” loop.
#   • Runs as a background process with a tiny console UI.
# ------------------------------------------------------------

# Path to the user‑editable command mapping.
COMMANDS_FILE = os.path.join(os.path.dirname(__file__), "commands.json")

# Load or create the command map.
if os.path.exists(COMMANDS_FILE):
    with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
        COMMAND_MAP = json.load(f)
else:
    # A tiny default set – you can extend it later.
    COMMAND_MAP = {
        "open chrome": {
            "action": "run",
            "command": "chrome"
        },
        "open notepad": {
            "action": "run",
            "command": "notepad"
        },
        "show files": {
            "action": "run",
            "command": "explorer ."
        }
    }
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(COMMAND_MAP, f, indent=2)

engine = pyttsx3.init()
recognizer = sr.Recognizer()
mic = sr.Microphone()


def speak(text: str):
    """Speak a short sentence using the system TTS engine."""
    engine.say(text)
    engine.runAndWait()


def execute_action(action_dict: dict):
    """Perform the requested action.

    Supported actions (extendable):
        • run   – Execute a shell command via `subprocess.Popen`.
        • type  – Simulate typing text using `pyautogui` (not used here).
    """
    action = action_dict.get("action")
    if action == "run":
        cmd = action_dict.get("command")
        try:
            # `shell=True` lets us run simple commands like "explorer ."
            subprocess.Popen(cmd, shell=True)
            speak(f"Running {cmd}")
        except Exception as e:
            speak("Sorry, I could not run the command.")
            print(f"Error executing {cmd}: {e}")
    else:
        speak("I don't know how to handle that command yet.")


def listen_and_recognise():
    """Capture a short utterance and return the recognized text."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening… (say a command or say ‘stop listening’ to quit)")
        audio = recognizer.listen(source, phrase_time_limit=5)
    try:
        text = recognizer.recognize_google(audio)
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Speech‑recognition service error: {e}")
        return None


def save_correction(phrase: str, action: dict):
    """Add a new phrase → action mapping to the JSON file.

    This is the very basic “training” mechanism – after a mistake you
    can type the corrected command, and it will be persisted for future
    runs.
    """
    COMMAND_MAP[phrase] = action
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(COMMAND_MAP, f, indent=2)
    speak("I have learned the new command.")


def main_loop():
    speak("Voice assistant started. Say a command.")
    while True:
        spoken = listen_and_recognise()
        if spoken is None:
            speak("I didn't catch that. Try again.")
            continue
        if "stop listening" in spoken:
            speak("Goodbye!")
            break
        print(f"Heard: {spoken}")
        # Direct lookup first.
        if spoken in COMMAND_MAP:
            execute_action(COMMAND_MAP[spoken])
            continue
        # Simple fuzzy match – if any known phrase is a substring.
        matched = None
        for phrase in COMMAND_MAP:
            if phrase in spoken:
                matched = phrase
                break
        if matched:
            execute_action(COMMAND_MAP[matched])
            continue
        # Unknown command – ask for correction.
        speak("I don't know that command. What should I do?")
        correction = input("Enter action JSON (e.g. {\"action\": \"run\", \"command\": \"calc\"}): ")
        try:
            action_dict = json.loads(correction)
            save_correction(spoken, action_dict)
        except Exception as e:
            speak("Sorry, I couldn't understand the correction.")
            print(e)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        speak("Interrupted. Exiting.")
        sys.exit(0)
