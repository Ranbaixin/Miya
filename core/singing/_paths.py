"""
弥娅唱歌系统 —— 路径解析。

消除 D 盘绝对路径硬编码，改为环境变量 + 自动查找。
"""
import os
import shutil
import logging

logger = logging.getLogger(__name__)


def find_ffmpeg() -> str:
    """查找 ffmpeg 可执行文件路径。"""
    path = shutil.which("ffmpeg") or os.getenv("MIYA_FFMPEG_PATH", "")
    if path and os.path.isfile(path):
        return path
    # 最后的兜底: 旧默认路径 (仅在原开发机上存在)
    legacy = r"D:\AIvoice\RVC20240604Nvidia50x0\RVC20240604Nvidia50x0\ffmpeg.exe"
    if os.path.isfile(legacy):
        return legacy
    logger.warning("ffmpeg 未找到，唱歌/音频处理功能不可用。请设置 MIYA_FFMPEG_PATH 环境变量。")
    return ""


def find_singing_python() -> str:
    """查找唱歌子系统使用的 Python 解释器 (用于 UVR5/Demucs 子进程)。"""
    path = os.getenv("MIYA_SINGING_PYTHON", "")
    if path and os.path.isfile(path):
        return path
    # 次选: 系统 PATH 上的 python
    sys_py = shutil.which("python") or shutil.which("python3")
    if sys_py:
        return sys_py
    logger.warning("唱歌子系统 Python 未配置。请设置 MIYA_SINGING_PYTHON 环境变量指向含 torch 的 Python。")
    return ""


def find_models_dir() -> str:
    """查找 AI 唱歌模型权重目录。

    环境变量 MIYA_SINGING_MODELS_DIR 应指向 GPT-SoVITS 安装目录，
    默认包含 tools/uvr5/uvr5_weights/ 子目录。
    """
    path = os.getenv("MIYA_SINGING_MODELS_DIR", "")
    if path and os.path.isdir(path):
        return path
    logger.warning("唱歌模型目录未配置。请设置 MIYA_SINGING_MODELS_DIR 环境变量。")
    return ""
