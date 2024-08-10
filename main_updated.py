import asyncio
import base64
import datetime
import difflib
import io
import json
import os
import sys
import queue
import re
import subprocess
import tempfile
import threading
import time
import logging
import venv
import wave
from typing import Any, Dict, Tuple

import aiohttp
import numpy as np
import simpleaudio as sa
import sounddevice as sd
from anthropic import Anthropic, APIError, APIStatusError
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from pydub import AudioSegment
from pynput import keyboard
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.live import Live

# ... (keep all the existing imports and global variables)

def text_to_speech(message, service="openai"):
    def convert_opus_to_wav(opus_file_path):
        wav_file_path = opus_file_path.replace(".opus", ".wav")
        command = f"ffmpeg -i {opus_file_path} {wav_file_path} > /dev/null 2>&1"
        os.system(command)
        return wav_file_path

    def audio_player(playback_queue, active_play_objects):
        while True:
            wav_path = playback_queue.get()
            try:
                audio = AudioSegment.from_file(wav_path, format="wav")
                play_obj = sa.play_buffer(
                    audio.raw_data,
                    num_channels=audio.channels,
                    bytes_per_sample=audio.sample_width,
                    sample_rate=audio.frame_rate,
                )
                active_play_objects.append((play_obj, wav_path))
                print(f"Audio queued: {wav_path}")
            except subprocess.CalledProcessError as e:
                print(f"Subprocess error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
            finally:
                playback_queue.task_done()

    def cleanup_wav_files(active_play_objects):
        while True:
            for play_obj, wav_path in active_play_objects[:]:
                if not play_obj.is_playing():
                    os.remove(wav_path)
                    active_play_objects.remove((play_obj, wav_path))
                    print(f"Cleaned up: {wav_path}")
            time.sleep(1)  # Check every second

    message_queue = queue.Queue()
    playback_queue = queue.Queue()
    active_play_objects = []

    def audio_generator():
        while True:
            service, message = message_queue.get()
            if service == "openai":
                try:
                    temp_path = generate_with_openai(message)
                    playback_queue.put(convert_opus_to_wav(temp_path))
                except Exception as e:
                    print(f"Error generating audio: {e}")
            else:
                print(f"Unknown service: {service}")
            message_queue.task_done()

    message_queue.put((service, message))

    threading.Thread(target=audio_generator, daemon=True).start()
    threading.Thread(target=audio_player, args=(playback_queue, active_play_objects), daemon=True).start()
    threading.Thread(target=cleanup_wav_files, args=(active_play_objects,), daemon=True).start()

    # Wait for the queues to be empty
    message_queue.join()
    playback_queue.join()

# ... (keep all the other existing functions)

# The rest of the file remains unchanged