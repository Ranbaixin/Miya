"""
搜图模块 - 百度搜图+NSFW过滤+OBS显示
"""

import base64
import io
import logging
import random
import time

import requests
from PIL import Image

from plugins.yinmei.tools import singleton, StringUtil
from plugins.yinmei.core import SharedData
from plugins.yinmei.core.obs_controller import OBSController
from plugins.yinmei.core.nsfw_filter import NSFWFilter

logger = logging.getLogger(__name__)


@singleton
class ImageSearch:
    """搜图 + 输出"""

    def __init__(self):
        self._data = SharedData()
        self._obs = OBSController()
        self._nsfw = NSFWFilter()

    def check_img_search(self):
        if not self._data.SearchImgList.empty() and self._data.is_SearchImg == 2:
            self._data.is_SearchImg = 1
            img_json = self._data.SearchImgList.get()
            self._search_and_output(img_json)
            self._data.is_SearchImg = 2

    def _search_and_output(self, img_json: dict):
        prompt = img_json["prompt"]
        username = img_json["username"]
        try:
            self._obs.show_text("状态提示", f"{self._data.Ai_Name}在搜图《{prompt}》")
            img_url = self._baidu_search(prompt)
            if img_url:
                image = self._download_and_filter(img_url, prompt, username)
                if image:
                    timestamp = int(time.time())
                    path = f"{self._data.image_physical_folder}{prompt}_{username}_{timestamp}.jpg"
                    image.convert("RGB").save(path, "JPEG")
                    self._obs.show_image("绘画图片", path)
                    self._obs.show_text("状态提示", "")
                    return
            self._obs.show_text("状态提示", "")
        except Exception:
            logger.exception("【搜图】异常")

    def _download_and_filter(self, img_url: str, prompt: str, username: str):
        resp = requests.get(img_url, timeout=(5, 60))
        img_data = resp.content
        imgb64 = base64.b64encode(img_data).decode()
        status, nsfw = self._nsfw.check(imgb64, prompt, username, 5, "搜图", 0.6)
        if status != 1:
            logger.info(f"搜图《{prompt}》nsfw={nsfw} 已拦截")
            return None
        img = Image.open(io.BytesIO(img_data))
        img = img.resize((self._data.image_width, self._data.image_height), Image.LANCZOS)
        return img

    def _baidu_search(self, query: str):
        try:
            from plugins.yinmei.core.search_image_util import baidu_get_image_url_regx

            img_search = {"query": query, "width": self._data.image_width, "height": self._data.image_height}
            images = baidu_get_image_url_regx(img_search, self._data.image_num)
            count = len(images)
            logger.info(f"搜图《{query}》数量: {count}")
            if count < self._data.image_num:
                img_search2 = {"query": query, "width": self._data.image_width, "height": 0}
                sec = baidu_get_image_url_regx(img_search2, self._data.image_num)
                images += sec
                count += len(sec)
            if count > 0:
                return images[random.randrange(0, min(count, len(images)))]
        except Exception:
            logger.exception("【百度搜图】异常")
        return None

    def msg_deal(self, traceid: str, query: str, uid: str, username: str) -> bool:
        text = ["搜图", "搜个图", "搜图片", "搜一下图片"]
        is_contain = StringUtil.has_string_reg_list(f"^{text}", query)
        if is_contain is not None:
            num = StringUtil.is_index_contain_string(text, query)
            q = query[num:].strip()
            if q:
                self._data.SearchImgList.put({"traceid": traceid, "prompt": q, "username": username})
            return True
        return False
