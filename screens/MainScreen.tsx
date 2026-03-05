import { Audio } from 'expo-av';
import React, { useState, useEffect } from 'react';
import { Alert, StyleSheet, Text, TouchableOpacity, View, ScrollView } from 'react-native';
import AudioWave from '../components/AudioWave';
import CameraComponent from '../components/CameraView';

export default function MainScreen() {
  const [activeTab, setActiveTab] = useState<'sign' | 'speech'>('sign');
  const [isRecording, setIsRecording] = useState(false);
  
  // 1. Added dynamic state for translations
  const [translation, setTranslation] = useState('Waiting for sign...');
  const [speechResult, setSpeechResult] = useState('Listening...');

  const startSpeechToText = async () => {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      Alert.alert("Permission Required", "Please enable microphone access in settings.");
      return;
    }
    setIsRecording(true);
    setSpeechResult("Listening to speech...");
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
      {/* Toggle Buttons */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'sign' && styles.activeTab]} 
          onPress={() => setActiveTab('sign')}
        >
          <Text style={[styles.tabText, activeTab === 'sign' && styles.activeTabText]}>Sign to Speech</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'speech' && styles.activeTab]} 
          onPress={() => {
            setActiveTab('speech');
            startSpeechToText();
          }}
        >
          <Text style={[styles.tabText, activeTab === 'speech' && styles.activeTabText]}>Speech to Text</Text>
        </TouchableOpacity>
      </View>

      {/* Main Content Area */}
      {activeTab === 'sign' ? (
        <View style={styles.content}>
          <View style={styles.stackedContainer}>
            <View style={styles.cameraBox}>
              {/* This component should now handle the imx708 stream */}
              <CameraComponent />
            </View>
            <View style={styles.fullTextBox}>
              <Text style={styles.resultLabel}>FSL TRANSLATION:</Text>
              <Text style={styles.placeholderText}>{translation}</Text>
            </View>
          </View>
        </View>
        ) : (
          <View style={styles.content1}>
          <View style={styles.stackedContainer2}>
            <View style={styles.audioWave}>
              <AudioWave isRecording={isRecording} />
            </View>
            <View style={styles.fullTextBox}>
              <Text style={styles.resultLabel}>SPEECH RESULT:</Text>
              <Text style={styles.placeholderText}>{speechResult}</Text>
            </View>
          </View>
          </View>
        )}
    </ScrollView> 
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 20, paddingBottom: 20, backgroundColor: '#fff'},
  tabContainer: { flexDirection: 'row', backgroundColor: '#e5e0db', borderRadius: 25, padding: 0 },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 20 },
  activeTab: { backgroundColor: '#6d3d1e' },
  tabText: { color: '#777', fontWeight: '600' },
  activeTabText: { color: '#fff' },
  content: { 
    marginTop: 20, 
    flex: 1 
  },
  content1: { 
    flex: 1 
  },
  scrollContent: { 
    paddingHorizontal: 20, 
    paddingBottom: 40, 
  },
  stackedContainer: { 
    flexDirection: 'row',
    gap: 15, 
    height: 500,
    width: '100%',
  },
  cameraBox: { 
    flex: 2, 
    height: '100%', 
    borderRadius: 20, 
    backgroundColor: '#000',
    overflow: 'hidden' 
  },
  fullTextBox: { 
    flex: 1, 
    backgroundColor: '#f4f1ee', 
    height: '100%', 
    borderRadius: 20, 
    padding: 20,
    borderWidth: 1,
    borderColor: '#e5e0db'
  },
  stackedContainer2: {
    flexDirection: 'column',
    gap: 15,
    height: 500,
    width: '100%',
  },
  audioWave: {
    flex: 0.2,
    overflow: 'hidden'
  },
  resultLabel: {
    fontSize: 12,
    color: '#6d3d1e',
    fontWeight: 'bold',
    marginBottom: 8,
    textTransform: 'uppercase'
  },
  placeholderText: {
    fontSize: 24,
    color: '#333',
    fontWeight: '500'
  }
});