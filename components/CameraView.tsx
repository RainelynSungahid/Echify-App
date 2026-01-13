import React, { useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';

export default function CameraComponent() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isCameraActive, setIsCameraActive] = useState(false);

  if (!permission) {
    // Camera permissions are still loading.
    return <View />;
  }

  const handlePress = async () => {
    if (!permission.granted) {
      const { granted } = await requestPermission();
      if (granted) setIsCameraActive(true);
    } else {
      setIsCameraActive(true);
    }
  };

  return (
    <View style={styles.container}>
      {isCameraActive && permission.granted ? (
        <CameraView style={styles.camera} facing="front" />
      ) : (
        <TouchableOpacity style={styles.placeholder} onPress={handlePress}>
          <Ionicons name="camera-outline" size={48} color="#777" />
          <Text style={styles.text}>Tap to turn on camera</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, borderRadius: 20, overflow: 'hidden', backgroundColor: '#e0e0e0' },
  camera: { flex: 1 },
  placeholder: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  text: { marginTop: 10, color: '#777', fontSize: 12 }
});