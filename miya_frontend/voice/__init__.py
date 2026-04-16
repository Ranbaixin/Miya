"""
NagaAgent voice 模块兼容层
"""


class VoiceMode:
    TEXT = "text"
    VOICE = "voice"


class UnifiedVoiceManager:
    def __init__(self, mode=VoiceMode.TEXT):
        self.mode = mode

    def start_listening(self):
        pass

    def stop_listening(self):
        pass


class MicrophoneRecorder:
    def __init__(self, parent=None):
        self.parent = parent
        self._recording = False

    def start(self):
        self._recording = True

    def stop(self):
        self._recording = False

    def is_recording(self):
        return self._recording


class VoiceIntegration:
    def __init__(self):
        self._speaking = False

    def speak(self, text):
        self._speaking = True

    def stop(self):
        self._speaking = False

    def is_speaking(self):
        return self._speaking


class VoicePrintAuth:
    pass


def get_voiceprint_auth():
    return None


def get_active_comm_manager():
    return None


def get_ai_diary_manager():
    return None


def get_windows_voice_input():
    return None
