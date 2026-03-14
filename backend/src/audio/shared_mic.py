import queue
import threading

import numpy as np
import sounddevice as sd


class SharedMic:
    def __init__(
        self,
        samplerate=48000,
        channels=2,
        blocksize=4800,
        device_index=1,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.device_index = device_index

        self.stream = None
        self.running = False
        self.level = 0.0
        self.lock = threading.Lock()
        self.chunk_queue = queue.Queue()

    def start(self):
        if self.running:
            return

        try:
            print("🎤 Available audio devices:")
            print(sd.query_devices())
            print(f"✅ Using microphone device index: {self.device_index}")

            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                blocksize=self.blocksize,
                dtype="int32",
                device=self.device_index,
                callback=self._audio_callback,
            )
            self.stream.start()
            self.running = True
            print("✅ Shared microphone started")
        except Exception as e:
            print(f"❌ Failed to start shared microphone: {e}")
            raise

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️ Mic status: {status}")

        # Convert int32 → float32 in [-1.0, 1.0], left channel only
        mono = indata[:, 0].astype(np.float32) / np.float32(2**31)
        mono = np.clip(mono * 15.0, -1.0, 1.0)  # gain 15 matches your working script

        rms = float(np.sqrt(np.mean(np.square(mono)))) if len(mono) > 0 else 0.0

        with self.lock:
            self.level = rms

        self.chunk_queue.put(mono)

    def get_level(self):
        with self.lock:
            return self.level

    def drain_chunks(self):
        chunks = []
        while not self.chunk_queue.empty():
            try:
                chunks.append(self.chunk_queue.get_nowait())
            except queue.Empty:
                break
        return chunks

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        print("🛑 Shared microphone stopped")


shared_mic = SharedMic()