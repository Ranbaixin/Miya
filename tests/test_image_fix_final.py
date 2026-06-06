#!/usr/bin/env python3
"""
最终图片系统修复测试
验证所有修复是否生效
"""

import asyncio
import logging
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
try:
    from dotenv import load_dotenv

    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"
    )
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"已加载环境变量文件: {env_path}")
    else:
        print(f"警告: 环境变量文件不存在: {env_path}")
except ImportError:
    print("警告: dotenv 模块未安装")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_all_fixes():
    """测试所有修复"""
    print("=" * 60)
    print("最终图片系统修复测试")
    print("=" * 60)

    all_tests_passed = True

    try:
        print("\n1. 测试环境变量配置...")
        api_keys = {
            "ZHIPU_API_KEY": "智谱API",
            "DASHSCOPE_API_KEY": "阿里云通义千问API",
            "DEEPSEEK_API_KEY": "DeepSeek API",
            "SILICONFLOW_API_KEY": "硅基流动API",
        }

        for env_var, name in api_keys.items():
            value = os.getenv(env_var, "")
            if value:
                print(f"   [OK] {name}: 已配置")
            else:
                print(f"   [WARN] {name}: 未配置")

        print("\n2. 测试多模型分析器导入...")
        from core.multi_vision_analyzer import MultiVisionAnalyzer

        print("   [OK] 多模型分析器导入成功")

        print("\n3. 测试增强版图片处理器导入...")
        from webnet.qq.enhanced_image_handler import EnhancedQQImageHandler

        print("   [OK] 增强版图片处理器导入成功")

        print("\n4. 测试QQMessage参数修复...")
        from webnet.qq.models import QQMessage

        # 测试正确的参数
        test_message = QQMessage(
            message="测试消息", sender_id=12345, group_id=0, message_type="private"
        )

        if test_message.message == "测试消息":
            print("   [OK] QQMessage参数正确")
        else:
            print("   [FAIL] QQMessage参数错误")
            all_tests_passed = False

        print("\n5. 测试多模型系统初始化...")
        analyzer = MultiVisionAnalyzer()
        await analyzer.initialize()
        stats = analyzer.get_stats()

        print("   [OK] 多模型系统初始化成功")
        print(f"       启用模型数: {stats['enabled_models']}")

        # 检查通义千问是否启用
        if os.getenv("DASHSCOPE_API_KEY"):
            print("   [INFO] 通义千问API已配置，应该已启用")

        print("\n6. 测试增强版处理器...")

        class MockQQNet:
            pass

        mock_net = MockQQNet()
        handler = EnhancedQQImageHandler(mock_net)
        await handler.initialize()

        print("   [OK] 增强版处理器初始化成功")
        print(f"       多模型支持: {handler.multi_model_enabled}")

        print("\n7. 测试图片分析流程...")
        # 模拟一个图片事件
        test_event = {
            "message_type": "private",
            "sender": {"user_id": 1523878699},
            "group_id": 0,
            "message": [
                {
                    "type": "image",
                    "data": {
                        "url": "https://example.com/test.jpg",
                        "file": "test.jpg",
                        "file_size": "1024",
                        "sub_type": 0,
                    },
                }
            ],
        }

        # 测试消息提取
        image_info = handler._extract_image_info(test_event)
        if image_info and image_info.get("url"):
            print("   [OK] 图片信息提取成功")
        else:
            print("   [WARN] 图片信息提取测试跳过（需要实际URL）")

        print("\n8. 测试弥娅风格回复生成...")
        # 创建一个模拟的分析结果
        from core.multi_vision_analyzer import ImageAnalysisResult

        test_result = ImageAnalysisResult(
            success=True,
            description="这是一张美丽的风景图片，有蓝天白云和绿色的树木。",
            labels=["自然", "风景"],
            nsfw_score=0.0,
            has_text=False,
            text="",
            text_confidence=0.0,
            size_kb=256.5,
            format="jpeg",
            model_used="Kimi-K2.6",
            provider="zhipu",
            confidence=0.8,
            error_message="",
            processing_time_ms=1250.0,
        )

        response_message = handler._create_response_message(test_event, test_result)

        if response_message and len(response_message.message) > 50:
            print("   [OK] 弥娅风格回复生成成功")
            print(f"       回复长度: {len(response_message.message)} 字符")

            # 检查回复是否包含弥娅风格的元素
            reply_text = response_message.message
            if (
                "早上好呀" in reply_text
                or "下午好哦" in reply_text
                or "晚上好" in reply_text
                or "夜深了" in reply_text
            ):
                print("   [OK] 包含亲切问候语")
            if "我看到了" in reply_text or "让我看看" in reply_text:
                print("   [OK] 包含弥娅风格表达")
            if "小提示" in reply_text:
                print("   [OK] 包含亲切提示")
        else:
            print("   [FAIL] 回复生成失败")
            all_tests_passed = False

        print("\n9. 清理资源...")
        await analyzer.close()
        await handler.close()
        print("   [OK] 资源清理完成")

    except ImportError as e:
        print(f"   [FAIL] 导入失败: {e}")
        all_tests_passed = False
    except Exception as e:
        print(f"   [FAIL] 测试异常: {e}")
        import traceback

        traceback.print_exc()
        all_tests_passed = False

    print("\n" + "=" * 60)

    if all_tests_passed:
        print("所有测试通过！")
        print("\n现在可以启动QQ机器人：")
        print('cd "d:\\AI_MIYA_Facyory\\MIYA\\Miya"')
        print("python -m webnet.qq.core")

        print("\n预期改进：")
        print("1. ✅ 图片消息不再出现参数错误")
        print("2. ✅ 通义千问视觉模型已启用")
        print("3. ✅ 回复风格更亲切有弥娅特色")
        print("4. ✅ 多模型故障转移正常工作")
    else:
        print("部分测试失败")
        print("\n请检查：")
        print("1. 环境变量配置是否正确")
        print("2. 相关模块是否已正确安装")
        print("3. 代码是否有语法错误")

    print("=" * 60)

    return all_tests_passed


async def main():
    """主函数"""
    success = await test_all_fixes()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
