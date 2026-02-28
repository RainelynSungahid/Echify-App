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
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');

      // 1. Try to find the Echify bridge specifically
      // 2. Fallback to the first available camera if name is different
      const selectedDevice = videoDevices.find(d => 
        d.label.toLowerCase().includes('echify')
      ) || videoDevices[0];

      if (!selectedDevice) {
        throw new Error("No camera hardware detected.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: { exact: selectedDevice.deviceId },
          width: 640,
          height: 480
        }
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
      }
    } catch (err) {
      console.error(err);
      setError("Camera found but access denied. Try: sudo chmod 777 /dev/video10");
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