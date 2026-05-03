"""
弥娅系统 v5.0 - 快速演示入口
"""

import sys
import os
from pathlib import Path

# 设置编码
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    try:
        import subprocess

        subprocess.run(["chcp", "65001"], shell=True, capture_output=True)
    except:
        pass

# 添加到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Miya System v5.0 - Quick Demo")
print("=" * 60)
print()

# 快速加载人格
print("Loading Miya...")

try:
    from core.personality import Personality
    from core.identity import Identity

    personality = Personality()
    identity = Identity()

    print("  [OK] Personality loaded")
    print("  [OK] Identity loaded")
    print()
    print("=" * 60)
    print("Miya is ready!")
    print("=" * 60)
    print()

except Exception as e:
    print(f"Error: {e}")
    print("Using fallback...")
    from core.personality import Personality

    personality = Personality()
    print("  [OK] Personality basic")
    print()

# 对话
print("Chat with Miya (type 'exit' to quit):")
print()

while True:
    try:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            break

        msg = user_input.lower()

        # 简单回复
        if any(w in msg for w in ["你好", "hello", "hi", "hey"]):
            print("Miya: 你好！我是弥娅，很高兴见到你~")
        elif any(w in msg for w in ["你是谁", "who"]):
            print("Miya: 我是弥娅，一个有灵魂的 AI 虚拟化身~")
        elif any(w in msg for w in ["帮助", "help"]):
            print("Miya: 我可以和你聊天~ 输入 exit 退出")
        elif any(w in msg for w in ["版本", "version"]):
            print("Miya: 弥娅系统 v5.0 - 统一架构版")
        else:
            import random

            responses = ["嗯...", "好的", "我知道了", "继续说"]
            print(f"Miya: {random.choice(responses)}")

        print()

    except KeyboardInterrupt:
        break
    except EOFError:
        break

print()
print("再见！下次再见~")
