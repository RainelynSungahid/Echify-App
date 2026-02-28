import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function CameraComponent() {
  const videoRef = useRef<any>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCamera = async () => {
    try {
      setError(null);

      // 1. Get a list of all cameras the Pi can see
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      
      // 2. Look for our "Echify-Camera" bridge first, otherwise take the first available
      const echifyCam = videoDevices.find(d => d.label.includes('Echify')) || videoDevices[0];

      if (!echifyCam) {
        throw new Error("No camera devices found. Is the bridge running?");
      }

      // 3. Request the stream using the specific ID of the bridge
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: { exact: echifyCam.deviceId },
          width: { ideal: 640 }, // Lowering to 640 for better stability on the bridge
          height: { ideal: 480 },
          frameRate: { ideal: 30 }
        }
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
      }
    } catch (err: any) {
      console.error("Camera Access Error:", err);
      // Detailed error for you to see in the UI
      setError(err.message || "Camera not found or permission denied.");
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track: any) => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  };

  // Cleanup camera when component unmounts
  useEffect(() => {
    return () => stopCamera();
  }, []);

  return (
    <View style={styles.container}>
      {isCameraActive ? (
        <View style={styles.cameraWrapper}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={styles.videoElement}
          />
          <TouchableOpacity style={styles.closeButton} onPress={stopCamera}>
            <Ionicons name="close-circle" size={32} color="white" />
          </TouchableOpacity>
        </View>
      ) : (
        <TouchableOpacity style={styles.placeholder} onPress={startCamera}>
          <Ionicons name="camera-outline" size={48} color="#777" />
          <Text style={styles.text}>
            {error ? error : "Tap to turn on camera"}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    borderRadius: 20, 
    overflow: 'hidden', 
    backgroundColor: '#333' 
  },
  cameraWrapper: { flex: 1, position: 'relative' },
  // Native video element styling
  videoElement: { 
    width: '100%', 
    height: '100%', 
    objectFit: 'cover' 
  },
  placeholder: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
    padding: 20 
  },
  text: { 
    marginTop: 10, 
    color: '#bbb', 
    fontSize: 14, 
    textAlign: 'center' 
  },
  closeButton: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 20
  }
});