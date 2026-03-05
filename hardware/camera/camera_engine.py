import subprocess
import os

def start_bridge():
    # This matches your Pi 5 camera command
    command = [
        "env", "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE",
        "gst-launch-1.0", "libcamerasrc", "!",
        "video/x-raw,width=640,height=480,format=YUY2", "!",
        "videoconvert", "!",
        "v4l2sink", "device=/dev/video10"
    ]
    
    print("Starting FSL Camera Bridge...")
    # Initialize the v4l2loopback device first
    os.system("sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1")
    os.system("sudo chmod 777 /dev/video10")
    
    # Run the GStreamer process
    subprocess.run(command)

if __name__ == "__main__":
    start_bridge()