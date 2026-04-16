"""
voice.input 模块兼容层
"""


class VoiceMode:
    """语音模式"""

    TEXT = "text"
    VOICE = "voice"


class UnifiedVoiceManager:
    """统一语音管理器"""

    def __init__(self, mode=VoiceMode.TEXT):
        self.mode = mode

    def start_listening(self):
        pass

    def stop_listening(self):
        pass


class MicrophoneRecorder:
    """麦克风录音器"""

    def __init__(self, parent=None):
        self.parent = parent
        self._recording = False

    def start(self):
        self._recording = True

    def stop(self):
        self._recording = False

    def is_recording(self):
        return self._recording


def get_windows_voice_input():
    """获取Windows语音输入（空实现）"""
    return None
