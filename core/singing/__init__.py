"""
弥娅 AI 唱歌系统 — 多引擎AI翻唱子系统

结构：
- base.py: SingingEngine 抽象基类
- providers.py: 具体引擎实现 (AutoConvertMusicEngine, RVCEngine)
- provider_builtin.py: BuiltinSingingEngine 内置引擎
- music_source.py: 音乐源抽象层 (Netease / Local)
- separator.py: 人声分离模块 (demucs)
- manager.py: SingingRegistry + SingingWorkflow（点歌→搜索→学唱→播放流水线）
- engine_router.py: 跨平台入口 + 触发词检测

使用方式：
```python
from core.singing import get_singing_registry
registry = get_singing_registry()
reply = await registry.workflow.process_song_request("青花瓷", username="佳")
```

版本：
v2.0.0: 内置引擎 (BuiltinSingingEngine)，自包含本地管线
"""

from .base import SingingEngine, SongInfo, LearnTask, LearnStatus, SongOutput
from .providers import AutoConvertMusicEngine, RVCEngine
from .provider_builtin import BuiltinSingingEngine
from .manager import SingingRegistry, SingingWorkflow, get_singing_registry
from .engine_router import is_sing_request, extract_song_name, handle_sing_request

__all__ = [
    "SingingEngine",
    "SongInfo",
    "LearnTask",
    "LearnStatus",
    "SongOutput",
    "AutoConvertMusicEngine",
    "RVCEngine",
    "BuiltinSingingEngine",
    "SingingRegistry",
    "SingingWorkflow",
    "get_singing_registry",
    "is_sing_request",
    "extract_song_name",
    "handle_sing_request",
]

__version__ = "2.0.0"
