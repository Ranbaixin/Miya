"""
直播中枢 - 整合所有虚拟主播管线

消息入口 → 命令解析 → 意图分发 → 功能执行
调度系统：定时器轮询各路队列
"""

import asyncio
import json
import logging
import os
import re
import uuid
from threading import Thread

from plugins.yinmei.core import SharedData
from plugins.yinmei.core.obs_controller import OBSController, VideoControl, VideoStatus
from plugins.yinmei.core.nsfw_filter import NSFWFilter
from plugins.yinmei.core.image_search import ImageSearch
from plugins.yinmei.core.web_search import WebSearch
from plugins.yinmei.core.draw_engine import DrawEngine
from plugins.yinmei.core.sing_engine import SingEngine
from plugins.yinmei.core.dance_engine import DanceEngine
from plugins.yinmei.tools import singleton, StringUtil

logger = logging.getLogger(__name__)


@singleton
class LiveStreamHub:
    """直播中枢 - 虚拟主播主控制器"""

    def __init__(self):
        self._data = SharedData()
        self._obs = OBSController()
        self._nsfw = NSFWFilter()
        self._image_search = ImageSearch()
        self._web_search = WebSearch()
        self._draw = DrawEngine()
        self._sing = SingEngine()
        self._dance = DanceEngine()

        self._tts_callback = None
        self._llm_chat_callback = None
        self._emote_callback = None
        self._scheduler = None

    # ============ 回调注册 (对接 MIYA 现有系统) ============

    def set_tts_callback(self, callback):
        """注册 TTS 回调: callback(text: str)"""
        self._tts_callback = callback

    def set_llm_chat_callback(self, callback):
        """注册 LLM 对话回调: callback(question_list_item: dict)"""
        self._llm_chat_callback = callback

    def set_emote_callback(self, callback):
        """注册表情回调: callback(text: str) -> list[dict]"""
        self._emote_callback = callback

    def set_live2d_state(self, state: str):
        """通过 API 向 Live2D 窗口发送状态"""
        try:
            from plugins.yinmei.routes import live2d_set_state

            live2d_set_state(state)
        except Exception:
            pass

    def set_live2d_emotion(self, emotion: str):
        """通过 API 向 Live2D 窗口发送情绪"""
        try:
            from plugins.yinmei.routes import live2d_set_emotion

            live2d_set_emotion(emotion)
        except Exception:
            pass

    def set_live2d_mouth(self, params: dict):
        """通过 API 向 Live2D 窗口发送口型参数"""
        try:
            from plugins.yinmei.routes import live2d_set_mouth

            live2d_set_mouth(params)
        except Exception:
            pass

    # ============ 消息入口 ============

    def process_message(self, traceid: str, query: str, uid: str, username: str):
        """处理来自任意平台的输入消息"""
        query = self._nsfw.filter_text(query)
        logger.info(f"[{traceid}]消息捕获 [{username}]: {query}")

        # 1. 命令处理
        if self._handle_command(traceid, query, uid, username):
            return

        # 2. 跳过 "\" 开头的消息
        if query.startswith("\\"):
            return

        # 3. 表情/跳舞
        if self._dance.msg_deal_emote(traceid, query, uid, username):
            return

        # 4. 搜索
        if self._web_search.msg_deal(traceid, query, uid, username):
            return

        # 5. 搜图
        if self._image_search.msg_deal(traceid, query, uid, username):
            return

        # 6. 绘画
        if self._draw.msg_deal(traceid, query, uid, username):
            return

        # 7. 唱歌
        if self._sing.msg_deal(traceid, query, uid, username):
            return

        # 8. 跳舞
        if self._dance.msg_deal_dance(traceid, query, uid, username):
            return

        # 9. 场景切换
        if self._handle_scene(traceid, query, uid, username):
            return

        # 10. 聊天入口
        self._handle_chat(traceid, query, uid, username)

    # ============ 命令处理 ============

    def _handle_command(self, traceid: str, query: str, uid: str, username: str) -> bool:
        if query == "\\stop":
            self._data.is_singing = 2
            self._data.is_SearchText = 2
            self._data.is_SearchImg = 2
            self._data.is_drawing = 3
            self._data.is_ai_ready = True
            self._data.is_tts_ready = True
            os.system("taskkill /T /F /IM song.exe 2>nul")
            os.system("taskkill /T /F /IM accompany.exe 2>nul")
            os.system("taskkill /T /F /IM mpv.exe 2>nul")
            return True

        if query == "\\dance":
            os.system("taskkill /T /F /IM song.exe 2>nul")
            os.system("taskkill /T /F /IM accompany.exe 2>nul")
            os.system("taskkill /T /F /IM mpv.exe 2>nul")
            return True

        next_text = ["\\next", "下一首", "下首", "切歌", "next"]
        if StringUtil.has_string_reg_list(f"^{next_text}", query):
            os.system("taskkill /T /F /IM song.exe 2>nul")
            os.system("taskkill /T /F /IM accompany.exe 2>nul")
            self._data.is_singing = 2
            return True

        if "停止学歌" in query:
            self._data.is_creating_song = 2
            return True

        stop_dance_text = ["\\停止跳舞", "停止跳舞", "不要跳舞", "stop dance"]
        if StringUtil.has_string_reg_list(f"^{stop_dance_text}", query):
            self._data.is_dance = 2
            return True

        return False

    # ============ 场景控制 ============

    def _handle_scene(self, traceid: str, query: str, uid: str, username: str) -> bool:
        text = ["切换", "进入"]
        num = StringUtil.is_index_contain_string(text, query)
        if num > 0:
            scene_name = re.sub("(。|,|，)", "", query[num:].strip())
            self.change_scene(scene_name)
            return True
        return False

    def change_scene(self, scene_name: str):
        self._obs.change_scene(scene_name)
        if scene_name in self._data.song_background:
            song = self._data.song_background[scene_name]
            if self._obs.get_video_status("背景音乐") == VideoStatus.PAUSED.value:
                self._obs.play_video("背景音乐", song)
                from time import sleep

                sleep(1)
                self._obs.control_video("背景音乐", VideoControl.PAUSE)
            else:
                self._obs.play_video("背景音乐", song)

    # ============ 聊天入口 ============

    def _handle_chat(self, traceid: str, query: str, uid: str, username: str):
        cmd = self._data.cmd
        is_contain = StringUtil.has_string_reg_list(f"^{cmd}", query)
        if is_contain is not None:
            num = StringUtil.is_index_contain_string(cmd, query)
            extracted = query[num:].strip()
            if not extracted:
                return
            logger.info(f"[{traceid}]用户对话: {extracted}")
            self._data.QuestionList.put(
                {
                    "traceid": traceid,
                    "prompt": query,
                    "uid": uid,
                    "username": username,
                }
            )

    # ============ 定时器轮询 (FastAPI/APScheduler 驱动) ============

    def check_answer(self):
        """LLM 回复调度"""
        if not self._data.QuestionList.empty() and self._data.is_ai_ready:
            self._data.is_ai_ready = False
            if self._llm_chat_callback:
                Thread(target=self._llm_chat_callback, daemon=True).start()
            else:
                self._data.is_ai_ready = True

    def check_tts(self):
        """TTS 语音合成调度"""
        if not self._data.AnswerList.empty() and self._data.is_tts_ready:
            item = self._data.AnswerList.get()
            text = item.get("text", "")
            if text and self._tts_callback:
                Thread(target=self._tts_callback, args=(text,), daemon=True).start()

    def check_sing(self):
        """唱歌调度"""
        self._sing.check_sing()

    def check_playlist(self):
        """歌单播放调度"""
        self._sing.check_playlist()

    def check_draw(self):
        """绘画调度"""
        self._draw.check_draw()

    def check_img_search(self):
        """搜图调度"""
        self._image_search.check_img_search()

    def check_text_search(self):
        """搜文调度"""
        self._web_search.check_text_search()

    def check_dance(self):
        """跳舞调度"""
        self._dance.check_dance()

    def check_welcome(self):
        """欢迎语调度"""
        if self._data.WelcomeList:
            names = str(self._data.WelcomeList).replace("['", "").replace("']", "")
            count = len(self._data.WelcomeList)
            suffix = f"{count}位" if count > 1 else ""
            text = f'欢迎"{names}"{suffix}同学来到{self._data.Ai_Name}的直播间,跪求关注一下'
            self._data.WelcomeList.clear()
            if self._data.is_llm_welcome:
                self._data.QuestionList.put(
                    {
                        "traceid": str(uuid.uuid4()),
                        "prompt": text,
                        "uid": "0",
                        "username": self._data.Ai_Name,
                    }
                )
            elif self._tts_callback:
                Thread(target=self._tts_callback, args=(text,), daemon=True).start()

    # ============ 启动/停止 ============

    def register_scheduler(self, scheduler):
        """注册 APScheduler 实例，注册全部定时任务"""
        self._scheduler = scheduler
        scheduler.add_job(
            func=self.check_answer,
            trigger="interval",
            seconds=1,
            id="yinmei_answer",
            max_instances=100,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_tts,
            trigger="interval",
            seconds=1,
            id="yinmei_tts",
            max_instances=1000,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_sing,
            trigger="interval",
            seconds=1,
            id="yinmei_sing",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_playlist,
            trigger="interval",
            seconds=1,
            id="yinmei_playlist",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_draw,
            trigger="interval",
            seconds=1,
            id="yinmei_draw",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_img_search,
            trigger="interval",
            seconds=1,
            id="yinmei_img",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_text_search,
            trigger="interval",
            seconds=1,
            id="yinmei_text",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_dance,
            trigger="interval",
            seconds=1,
            id="yinmei_dance",
            kwargs={"sched": scheduler},
            max_instances=10,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self.check_welcome,
            trigger="interval",
            seconds=20,
            id="yinmei_welcome",
            max_instances=50,
            replace_existing=True,
        )
        scheduler.add_job(
            func=self._check_scene_time, trigger="cron", hour="6,17,18", id="yinmei_scene_time", replace_existing=True
        )
        logger.info("吟美直播定时任务注册完成")

    def _check_scene_time(self):
        """白天/黄昏/黑夜场景切换"""
        import time

        now = time.strftime("%H:%M:%S")
        if "06:00:00" <= now <= "16:59:59":
            logger.info("现在是白天")
        elif "17:00:00" <= now <= "17:59:59":
            logger.info("现在是黄昏")
        else:
            logger.info("现在是晚上")

    def shutdown(self):
        """停止所有"""
        self._data.is_singing = 2
        self._data.is_creating_song = 2
        self._data.is_drawing = 3
        self._data.is_dance = 2
        self._obs.disconnect()
        logger.info("吟美直播中枢已停止")
