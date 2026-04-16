"""
统一语音管理器
"""


class VoiceMode:
    TEXT = "text"
    VOICE = "voice"
    REALTIME = "realtime"
    LOCAL = "local"
    END_TO_END = "end2end"
    HYBRID = "hybrid"
    WINDOWS = "windows"


class UnifiedVoiceManager:
    def __init__(self, mode=VoiceMode.TEXT):
        self.mode = mode
        self._listening = False

    def start_listening(self):
        self._listening = True

    def stop_listening(self):
        self._listening = False

    def is_listening(self):
        return self._listening


def get_windows_voice_input():
    return UnifiedVoiceManager(VoiceMode.REALTIME)
