"""
voice.output 模块兼容层
"""


class VoiceIntegration:
    """语音合成（占位符）"""

    def __init__(self):
        self._speaking = False

    def speak(self, text):
        """播报文本（空实现）"""
        self._speaking = True

    def stop(self):
        """停止播报"""
        self._speaking = False

    def is_speaking(self):
        return self._speaking
