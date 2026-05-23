"""
QQ交互子网 - TTS语音处理逻辑
从原 qq.py 中拆分出来的TTS处理功能
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, List

logger = logging.getLogger(__name__)


class QQTTsHandler:
    """QQ TTS处理器"""

    def __init__(self, qq_net):
        self.qq_net = qq_net
        
        # TTS配置
        self.tts_enabled = True
        self.tts_voice_mode = "text"
        self.smart_tts_enabled = False
        
        # QQ消息分段配置
        self.qq_message_split = True
        self.qq_max_message_length = 200
        
        # 本地播放配置
        self.local_playback_enabled = False
        self.local_playback_volume = 1.0
        
        # 音频播放器
        self.audio_player = None

    def configure(
        self,
        tts_enabled: bool = True,
        tts_voice_mode: str = "text",
        smart_tts_enabled: bool = False,
        qq_message_split: bool = True,
        qq_max_message_length: int = 200,
        local_playback_enabled: bool = False,
        local_playback_volume: float = 1.0,
        audio_player = None
    ) -> None:
        """配置TTS处理器"""
        self.tts_enabled = tts_enabled
        self.tts_voice_mode = tts_voice_mode
        self.smart_tts_enabled = smart_tts_enabled
        self.qq_message_split = qq_message_split
        self.qq_max_message_length = qq_max_message_length
        self.local_playback_enabled = local_playback_enabled
        self.local_playback_volume = local_playback_volume
        self.audio_player = audio_player

    def _split_message(self, text: str, max_length: int) -> list:
        """
        分割长消息为多个片段

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            list: 分割后的文本片段
        """
        import re

        if len(text) <= max_length:
            return [text]

        segments = []
        current = ""

        # 按句子分割
        sentences = re.split(r'([。！？\n])', text)

        for sentence in sentences:
            if not sentence:
                continue

            if len(current) + len(sentence) <= max_length:
                current += sentence
            else:
                if current:
                    segments.append(current)
                current = sentence

        if current:
            segments.append(current)

        return segments

    def _get_message_length_type(self, text: str) -> str:
        """
        智能判断消息长度类型

        根据消息长度和内容自动判断消息类型：
        - short: 短文本（1-50字）
        - medium: 中等文本（51-150字）
        - long: 长文本（151-300字）
        - extra_long: 超长文本（>300字）

        Args:
            text: 消息文本

        Returns:
            str: 消息长度类型 (short/medium/long/extra_long)
        """
        text_length = len(text)

        if text_length <= 50:
            return "short"
        elif text_length <= 150:
            return "medium"
        elif text_length <= 300:
            return "long"
        else:
            return "extra_long"

    def _should_use_tts(self, text: str) -> bool:
        """
        智能判断是否应该使用TTS发送语音

        根据消息内容、长度、格式等因素自动判断

        Args:
            text: 消息文本

        Returns:
            bool: 是否使用TTS
        """
        # 如果未启用智能TTS判断，直接返回False
        if not self.smart_tts_enabled:
            logger.debug("[QQNet] 智能TTS判断未启用，使用文字")
            return False

        text_length = len(text)
        text.strip()

        # 1. 极短消息（1-5字）- 纯文字
        if text_length <= 5:
            logger.debug(f"[QQNet] 消息过短，使用文字: length={text_length}")
            return False

        # 2. 包含大量代码或特殊格式 - 纯文字
        code_indicators = ["```", "```python", "```json", "```javascript",
                         "```html", "```css", "<code>", "<pre>"]
        if any(indicator in text for indicator in code_indicators):
            logger.debug("[QQNet] 包含代码块，使用文字")
            return False

        # 3. 包含大量特殊符号和换行（如表格、列表）- 纯文字
        special_char_count = sum(1 for c in text if c in ['|', '─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴'])
        line_count = text.count('\n')
        if special_char_count > 10 or line_count > 15:
            logger.debug(f"[QQNet] 包含大量特殊符号或换行，使用文字: special_chars={special_char_count}, lines={line_count}")
            return False

        # 4. 超长消息（>300字）- 纯文字
        if text_length > 300:
            logger.debug(f"[QQNet] 消息过长，使用文字: length={text_length}")
            return False

        # 5. 短消息（6-50字）- 使用TTS语音
        if 6 <= text_length <= 50:
            logger.debug(f"[QQNet] 短消息，使用TTS语音: length={text_length}")
            return True

        # 6. 中等消息（51-150字）- 根据内容判断
        if 51 <= text_length <= 150:
            # 检查是否适合语音（对话、问候等）
            dialogue_indicators = ["好的", "明白", "收到", "没问题", "当然",
                               "你好", "谢谢", "再见", "晚安", "早安", "呢", "呀",
                               "哈", "嗯", "哦", "～", "~", "！", "!", "？", "?"]
            text.lower()
            if any(indicator in text for indicator in dialogue_indicators):
                logger.debug(f"[QQNet] 中等对话消息，使用TTS语音: length={text_length}")
                return True
            # 其他中等消息用文字
            logger.debug(f"[QQNet] 中等非对话消息，使用文字: length={text_length}")
            return False

        # 7. 较长消息（151-300字）- 根据内容判断
        if 151 <= text_length <= 300:
            # 检查是否包含大量专业术语或数据
            technical_indicators = ["API", "HTTP", "JSON", "XML", "SQL", "数据库",
                                  "配置", "参数", "函数", "方法", "类", "变量",
                                  "数组", "对象", "字符串", "数字", "布尔"]
            technical_count = sum(1 for indicator in technical_indicators if indicator in text)
            if technical_count > 5:
                logger.debug(f"[QQNet] 技术性内容过多，使用文字: technical_count={technical_count}")
                return False
            # 检查句子结构（是否有大量标点符号）
            punctuation_count = text.count('，') + text.count('.') + text.count('。') + text.count('！')
            if punctuation_count > 10:
                logger.debug(f"[QQNet] 句子过多，使用文字: punctuation={punctuation_count}")
                return False
            # 其他较长消息可以用TTS
            logger.debug(f"[QQNet] 较长消息，使用TTS语音: length={text_length}")
            return True

        # 默认不使用TTS
        logger.debug(f"[QQNet] 默认使用文字: length={text_length}")
        return False

    async def send_group_message(self, group_id: int, message: str | List[Dict], use_tts: bool = None) -> bool:
        """发送群消息"""
        try:
            # 检查是否需要TTS
            should_use_tts = False
            if self.tts_enabled and self.qq_net.tts_net and isinstance(message, str):
                if use_tts is None:
                    # 未显式指定，根据tts_voice_mode决定
                    if self.tts_voice_mode == "voice":
                        # 语音模式：启用TTS
                        should_use_tts = True
                        logger.debug("[QQNet] 语音模式，启用TTS")
                    elif self.tts_voice_mode == "text":
                        # 文本模式：使用智能判断
                        should_use_tts = self._should_use_tts(message)
                        logger.debug(f"[QQNet] 文本模式，使用智能判断: result={should_use_tts}")
                else:
                    # 显式指定模式，直接使用，跳过智能判断
                    should_use_tts = use_tts
                    logger.debug(f"[QQNet] 显式指定TTS模式: use_tts={use_tts}")

            # 使用TTS
            if should_use_tts:
                logger.debug(f"[QQNet] 使用TTS发送群消息: group={group_id}")
                await self._send_tts_group_message(group_id, message)
                return True

            # 普通消息 - 支持自动分段
            if isinstance(message, str):
                # 智能判断消息长度类型
                length_type = self._get_message_length_type(message)
                logger.info(f"[QQNet] 消息长度判断: type={length_type}, length={len(message)}")

                if self.qq_message_split and len(message) > self.qq_max_message_length:
                    logger.debug(f"[QQNet] 消息过长,自动分段: length={len(message)}")
                    segments = self._split_message(message, self.qq_max_message_length)
                    for i, segment in enumerate(segments):
                        await self.qq_net.onebot_client.send_group_message(group_id, segment)
                        # 分段之间稍微延迟
                        if i < len(segments) - 1:
                            await asyncio.sleep(0.5)
                    return True
                else:
                    await self.qq_net.onebot_client.send_group_message(group_id, message)
                    logger.debug(f"[QQNet] 发送群消息: group={group_id}")
                    return True

            # 列表格式消息(富文本)
            await self.qq_net.onebot_client.send_group_message(group_id, message)
            logger.debug(f"[QQNet] 发送群消息: group={group_id}")
            return True
        except Exception as e:
            logger.error(f"[QQNet] 发送群消息失败: {e}")
            return False

    async def send_private_message(self, user_id: int, message: str | List[Dict], use_tts: bool = None) -> bool:
        """发送私聊消息"""
        try:
            # 检查是否需要TTS
            should_use_tts = False
            if self.tts_enabled and self.qq_net.tts_net and isinstance(message, str):
                if use_tts is None:
                    # 未显式指定，根据tts_voice_mode决定
                    if self.tts_voice_mode == "voice":
                        # 语音模式：启用TTS
                        should_use_tts = True
                        logger.debug("[QQNet] 语音模式，启用TTS")
                    elif self.tts_voice_mode == "text":
                        # 文本模式：使用智能判断
                        should_use_tts = self._should_use_tts(message)
                        logger.debug(f"[QQNet] 文本模式，使用智能判断: result={should_use_tts}")
                else:
                    # 显式指定模式，直接使用，跳过智能判断
                    should_use_tts = use_tts
                    logger.debug(f"[QQNet] 显式指定TTS模式: use_tts={use_tts}")

            # 使用TTS
            if should_use_tts:
                logger.debug(f"[QQNet] 使用TTS发送私聊消息: user={user_id}")
                await self._send_tts_private_message(user_id, message)
                return True

            # 普通消息 - 支持自动分段
            if isinstance(message, str):
                # 智能判断消息长度类型
                length_type = self._get_message_length_type(message)
                logger.info(f"[QQNet] 消息长度判断: type={length_type}, length={len(message)}")

                if self.qq_message_split and len(message) > self.qq_max_message_length:
                    logger.debug(f"[QQNet] 消息过长,自动分段: length={len(message)}")
                    segments = self._split_message(message, self.qq_max_message_length)
                    for i, segment in enumerate(segments):
                        await self.qq_net.onebot_client.send_private_message(user_id, segment)
                        # 分段之间稍微延迟
                        if i < len(segments) - 1:
                            await asyncio.sleep(0.5)
                    return True
                else:
                    await self.qq_net.onebot_client.send_private_message(user_id, message)
                    logger.debug(f"[QQNet] 发送私聊消息: user={user_id}")
                    return True

            # 列表格式消息(富文本)
            await self.qq_net.onebot_client.send_private_message(user_id, message)
            logger.debug(f"[QQNet] 发送私聊消息: user={user_id}")
            return True
        except Exception as e:
            logger.error(f"[QQNet] 发送私聊消息失败: {e}")
            return False

    async def _send_tts_group_message(self, group_id: int, text: str) -> bool:
        """使用TTS发送群语音消息"""
        try:
            # 分段处理长文本
            if self.qq_message_split and len(text) > self.qq_max_message_length:
                segments = self._split_message(text, self.qq_max_message_length)
                for segment in segments:
                    await self._send_tts_segment(group_id, segment, is_group=True)
                return True

            # 直接发送
            return await self._send_tts_segment(group_id, text, is_group=True)

        except Exception as e:
            logger.error(f"[QQNet] 发送TTS群消息失败: {e}")
            # 回退到文本
            await self.qq_net.onebot_client.send_group_message(group_id, text)
            return False

    async def _send_tts_private_message(self, user_id: int, text: str) -> bool:
        """使用TTS发送私聊语音消息"""
        try:
            # 分段处理长文本
            if self.qq_message_split and len(text) > self.qq_max_message_length:
                segments = self._split_message(text, self.qq_max_message_length)
                for segment in segments:
                    await self._send_tts_segment(user_id, segment, is_group=False)
                return True

            # 直接发送
            return await self._send_tts_segment(user_id, text, is_group=False)

        except Exception as e:
            logger.error(f"[QQNet] 发送TTS私聊消息失败: {e}")
            # 回退到文本
            await self.qq_net.onebot_client.send_private_message(user_id, text)
            return False

    async def _send_tts_segment(self, target_id: int, text: str, is_group: bool) -> bool:
        """发送单个TTS语音片段"""
        tmp_path = None
        wav_path = None
        try:
            # 合成语音 - QQ 需要 silk 格式
            if not self.qq_net.tts_net:
                logger.warning("[QQNet] TTSNet 未初始化,回退到文本")
                return False
                
            audio_data = await self.qq_net.tts_net.synthesize(text, output_format="silk")
            if not audio_data:
                logger.warning("[QQNet] TTS合成失败,回退到文本")
                if is_group:
                    await self.qq_net.onebot_client.send_group_message(target_id, text)
                else:
                    await self.qq_net.onebot_client.send_private_message(target_id, text)
                return False

            # 创建 silk 临时文件（QQ 用）
            with tempfile.NamedTemporaryFile(suffix=".silk", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            # 如果需要本地播放，尝试合成 WAV 格式
            wav_path = None
            if self.local_playback_enabled and self.audio_player:
                try:
                    # 尝试用 WAV 格式再次合成（用于本地播放）
                    wav_data = await self.qq_net.tts_net.synthesize(text, output_format="wav")
                    if wav_data:
                        wav_path = tmp_path.replace('.silk', '.wav')
                        with open(wav_path, 'wb') as wav_file:
                            wav_file.write(wav_data)
                        logger.debug(f"[QQNet] 创建 WAV 文件用于本地播放: {wav_path}")
                except Exception as e:
                    logger.warning(f"[QQNet] 创建 WAV 失败: {e}")
                    wav_path = None

            try:
                # 构建语音消息段
                voice_message = [{
                    "type": "record",
                    "data": {
                        "file": f"file:///{tmp_path.replace(os.sep, '/')}"
                    }
                }]

                # 发送语音消息
                if is_group:
                    await self.qq_net.onebot_client.send_group_message(target_id, voice_message)
                else:
                    await self.qq_net.onebot_client.send_private_message(target_id, voice_message)

                logger.info(f"[QQNet] TTS语音片段已发送: target={target_id}, text={text[:30]}...")

                # 本地播放（异步）- 使用 WAV 文件
                if self.local_playback_enabled and self.audio_player and wav_path:
                    asyncio.create_task(self._play_audio_async(wav_path))

                return True
            finally:
                # 延迟清理临时文件（等待本地播放完成）
                await asyncio.sleep(0.5)  # QQ 发送需要时间

                if self.local_playback_enabled and self.audio_player:
                    # 等待播放完成后再删除
                    await self.audio_player.wait_until_finished()

                # 清理临时文件
                try:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    if wav_path and os.path.exists(wav_path):
                        os.unlink(wav_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"[QQNet] 发送TTS语音片段失败: {e}")
            return False

    async def _play_audio_async(self, audio_path: str):
        """异步播放音频"""
        try:
            if self.audio_player:
                await self.audio_player.play(audio_path, self.local_playback_volume)
        except Exception as e:
            logger.error(f"[QQNet] 本地播放失败: {e}")

    def set_tts_mode(self, mode: str):
        """设置TTS模式 (text 或 voice)"""
        if mode in ["text", "voice"]:
            self.tts_voice_mode = mode
            logger.info(f"[QQNet] TTS模式已设置为: {mode}")
        else:
            logger.warning(f"[QQNet] 无效的TTS模式: {mode}")

    def toggle_tts(self, enabled: bool = None):
        """切换TTS开关"""
        if enabled is None:
            self.tts_enabled = not self.tts_enabled
        else:
            self.tts_enabled = enabled
        logger.info(f"[QQNet] TTS已{'启用' if self.tts_enabled else '禁用'}")
        return self.tts_enabled

    def toggle_local_playback(self, enabled: bool = None):
        """切换本地播放开关"""
        if enabled is None:
            self.local_playback_enabled = not self.local_playback_enabled
        else:
            self.local_playback_enabled = enabled

        # 动态初始化音频播放器
        if self.local_playback_enabled and self.audio_player is None:
            from core.audio_player import get_audio_player
            self.audio_player = get_audio_player()
            self.audio_player.set_volume(self.local_playback_volume)

        logger.info(f"[QQNet] 本地播放已{'启用' if self.local_playback_enabled else '禁用'}")
        return self.local_playback_enabled

    def set_local_playback_volume(self, volume: float):
        """设置本地播放音量"""
        self.local_playback_volume = max(0.0, min(1.0, volume))
        if self.audio_player:
            self.audio_player.set_volume(self.local_playback_volume)
        logger.info(f"[QQNet] 本地播放音量设置为: {self.local_playback_volume}")

    def toggle_smart_tts(self, enabled: bool = None):
        """切换智能TTS判断开关"""
        if enabled is None:
            self.smart_tts_enabled = not self.smart_tts_enabled
        else:
            self.smart_tts_enabled = enabled
        logger.info(f"[QQNet] 智能TTS判断已{'启用' if self.smart_tts_enabled else '禁用'}")
        return self.smart_tts_enabled
