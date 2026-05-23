#!/usr/bin/env python3
"""
测试表情包功能

测试内容：
1. 表情包名称提取功能
2. 表情包文件查找功能
3. 自然语言表情包请求处理
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webnet.qq.message_handler import QQMessageHandler


def test_emoji_name_extraction():
    """测试表情包名称提取"""
    print("=" * 60)
    print("测试表情包名称提取功能")
    print("=" * 60)
    
    # 创建虚拟的消息处理器实例
    class MockQQNet:
        def __init__(self):
            self.onebot_client = None
    
    mock_qq_net = MockQQNet()
    handler = QQMessageHandler(mock_qq_net)
    
    # 测试用例
    test_cases = [
        "发送开心表情",
        "发个笑脸表情包",
        "来一个搞笑表情",
        "给我发个狗头表情",
        "想要一个可爱表情包",
        "发图",
        "发图片",
        "来张图",
        "发送弥娅表情",
        "发个测试表情",
        "今天天气真好",  # 非表情包请求
        "你好",  # 非表情包请求
    ]
    
    for test_text in test_cases:
        emoji_name = handler._extract_emoji_name_from_text(test_text)
        if emoji_name:
            print(f"[OK] '{test_text}' -> 提取到表情包名称: '{emoji_name}'")
        else:
            has_keyword = any(keyword in test_text for keyword in ['表情包', '表情', '发图', '发图片', '来张图'])
            if has_keyword:
                print(f"[OK] '{test_text}' -> 检测到表情包关键词，但未提取具体名称 (将发送随机表情)")
            else:
                print(f"[NO] '{test_text}' -> 未检测到表情包请求")

def test_emoji_file_search():
    """测试表情包文件查找"""
    print("\n" + "=" * 60)
    print("测试表情包文件查找功能")
    print("=" * 60)
    
    # 检查表情包目录
    emoji_dir = "./data/emojis"
    if os.path.exists(emoji_dir):
        print(f"[OK] 表情包目录存在: {emoji_dir}")
        
        # 列出所有表情包文件
        emoji_files = []
        for file in os.listdir(emoji_dir):
            file_path = os.path.join(emoji_dir, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                    emoji_files.append(file_path)
        
        if emoji_files:
            print(f"[OK] 找到 {len(emoji_files)} 个表情包文件:")
            for i, file_path in enumerate(emoji_files[:5], 1):  # 只显示前5个
                file_name = os.path.basename(file_path)
                file_name_without_ext = os.path.splitext(file_name)[0]
                print(f"  {i}. {file_name} -> 文件名: '{file_name_without_ext}'")
            
            if len(emoji_files) > 5:
                print(f"  ... 还有 {len(emoji_files) - 5} 个文件未显示")
            
            # 测试文件名匹配
            print("\n测试文件名匹配:")
            test_names = ["弥娅", "miya", "测试", "不存在"]
            for test_name in test_names:
                # 模拟查找逻辑
                found = False
                for file_path in emoji_files:
                    file_name = os.path.basename(file_path).lower()
                    file_name_without_ext = os.path.splitext(file_name)[0]
                    if test_name.lower() in file_name_without_ext or test_name.lower() in file_name:
                        print(f"  [OK] '{test_name}' -> 匹配到文件: {os.path.basename(file_path)}")
                        found = True
                        break
                
                if not found:
                    print(f"  [NO] '{test_name}' -> 未找到匹配文件")
        else:
            print("[NO] 表情包目录中没有图片文件")
    else:
        print(f"[NO] 表情包目录不存在: {emoji_dir}")
        print("[TIP] 建议创建目录并添加表情包文件")

def test_message_handler_creation():
    """测试消息处理器创建"""
    print("\n" + "=" * 60)
    print("测试消息处理器创建")
    print("=" * 60)
    
    try:
        # 创建虚拟的消息处理器实例
        class MockQQNet:
            def __init__(self):
                self.onebot_client = None
        
        mock_qq_net = MockQQNet()
        handler = QQMessageHandler(mock_qq_net)
        
        print("[OK] 消息处理器创建成功")
        
        # 测试方法存在性
        methods_to_check = [
            '_extract_emoji_name_from_text',
            'handle_emoji_request',
            '_send_emoji_response',
            '_send_local_emoji'
        ]
        
        for method_name in methods_to_check:
            if hasattr(handler, method_name):
                print(f"[OK] 方法存在: {method_name}")
            else:
                print(f"[NO] 方法不存在: {method_name}")
                
    except Exception as e:
        print(f"[ERROR] 消息处理器创建失败: {e}")

def main():
    """主测试函数"""
    print("Miya AI 表情包功能测试")
    print("=" * 60)
    
    # 运行测试
    test_emoji_name_extraction()
    test_emoji_file_search()
    test_message_handler_creation()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    print("\n使用说明:")
    print("1. 在QQ中发送以下消息测试表情包功能:")
    print("   - '发送表情' 或 '发个表情包' (随机表情)")
    print("   - '发送弥娅表情' 或 '发个miya表情' (指定名称表情)")
    print("   - '来张图' 或 '发图片' (图片表情)")
    print("2. 表情包目录: data/emojis/")
    print("3. 当前表情包文件:")
    
    # 显示当前表情包
    emoji_dir = "./data/emojis"
    if os.path.exists(emoji_dir):
        emoji_files = []
        for file in os.listdir(emoji_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                emoji_files.append(file)
        
        if emoji_files:
            for file in emoji_files:
                file_name_without_ext = os.path.splitext(file)[0]
                print(f"   - {file} -> 可用的表情包名称: '{file_name_without_ext}'")
        else:
            print("   - 暂无表情包文件")
    else:
        print("   - 表情包目录不存在")

if __name__ == "__main__":
    main()
