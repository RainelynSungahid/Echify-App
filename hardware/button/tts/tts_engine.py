import pygame
import os
import threading

# Initialize pygame mixer once
pygame.mixer.init()

class EmergencyAudio:
    def __init__(self, mp3_name="help_me.mp3"):
        # This looks for the mp3 in the main fsl_project folder
        # We use absolute paths to ensure the Pi finds it
        self.mp3_path = "/home/sms/fsl_project/help_me.mp3"

    def play_help_instant(self):
        def _run():
            try:
                if os.path.exists(self.mp3_path):
                    print(f"🔊 Playing: {self.mp3_path}")
                    pygame.mixer.music.load(self.mp3_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        continue
                else:
                    print(f"❌ Audio file not found at: {self.mp3_path}")
            except Exception as e:
                print(f"Audio Error: {e}")

        threading.Thread(target=_run, daemon=True).start()
