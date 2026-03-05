import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';

export default function CameraComponent() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isCameraActive, setIsCameraActive] = useState(false);

  useEffect(() => {
    const getPermission = async () => {
      if (!permission?.granted) {
        const result = await requestPermission();
        if (result.granted) {
          setIsCameraActive(true);
        }
      } else {
        setIsCameraActive(true);
      }
    };

    getPermission();
  }, [permission]);

  if (!permission) {
    return <View />;
  }

  return (
    <View style={styles.container}>
      {isCameraActive && permission.granted ? (
        <CameraView style={styles.camera} facing="front" />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.text}>Requesting camera access...</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, borderRadius: 20, overflow: 'hidden' },
  camera: { flex: 1 },
  placeholder: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  text: { color: '#777' }
});