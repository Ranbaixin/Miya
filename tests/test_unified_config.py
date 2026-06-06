#!/usr/bin/env python3
"""
统一配置系统测试脚本
测试QQ配置是否已正确集成到统一的.env配置系统中
"""

import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_env_file_exists():
    """测试.env文件是否存在"""
    logger.info("测试.env文件...")
    
    # 检查多个可能的.env文件位置
    possible_env_paths = [
        project_root / '.env',           # 项目根目录
        project_root / 'config' / '.env', # config目录
    ]
    
    possible_example_paths = [
        project_root / '.env.example',
        project_root / 'config' / '.env.example',
    ]
    
    env_path = None
    env_example_path = None
    
    # 查找.env文件
    for path in possible_env_paths:
        if path.exists():
            env_path = path
            break
    
    # 查找.env.example文件
    for path in possible_example_paths:
        if path.exists():
            env_example_path = path
            break
    
    if not env_path:
        logger.error("未找到.env文件")
        # 检查config目录
        config_dir = project_root / 'config'
        if config_dir.exists():
            files = list(config_dir.iterdir())
            logger.info(f"config目录中的文件: {[f.name for f in files]}")
        return False
    
    if not env_example_path:
        logger.error("未找到.env.example文件")
        return False
    
    # 读取文件大小
    env_size = env_path.stat().st_size
    env_example_size = env_example_path.stat().st_size
    
    logger.info(f".env文件位置: {env_path}")
    logger.info(f".env文件大小: {env_size} 字节")
    logger.info(f".env.example文件位置: {env_example_path}")
    logger.info(f".env.example文件大小: {env_example_size} 字节")
    
    # 检查QQ配置是否存在
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    required_qq_configs = [
        'QQ_ONEBOT_WS_URL',
        'QQ_BOT_QQ',
        'QQ_IMAGE_MAX_SIZE',
        'QQ_FILE_MAX_SIZE',
        'QQ_OCR_ENABLED',
        'QQ_ACTIVE_CHAT_ENABLED'
    ]
    
    missing_configs = []
    for config in required_qq_configs:
        if config not in env_content:
            missing_configs.append(config)
    
    if missing_configs:
        logger.error(f".env文件中缺少QQ配置: {missing_configs}")
        return False
    
    logger.info(".env文件测试通过")
    return True


def test_settings_integration():
    """测试settings.py集成"""
    logger.info("测试settings.py集成...")
    
    try:
        from config.settings import Settings
        
        settings = Settings()
        qq_config = settings.get('qq', {})
        
        if not qq_config:
            logger.error("settings.py中没有QQ配置")
            return False
        
        # 检查基础配置
        required_keys = [
            'onebot_ws_url',
            'bot_qq',
            'multimedia',
            'image_recognition',
            'active_chat'
        ]
        
        missing_keys = []
        for key in required_keys:
            if key not in qq_config:
                missing_keys.append(key)
        
        if missing_keys:
            logger.error(f"settings.py中缺少QQ配置项: {missing_keys}")
            return False
        
        logger.info(f"settings.py QQ配置: {qq_config.get('onebot_ws_url')}")
        logger.info("settings.py集成测试通过")
        return True
        
    except ImportError as e:
        logger.error(f"无法导入settings.py: {e}")
        return False
    except Exception as e:
        logger.error(f"settings.py测试失败: {e}")
        return False


def test_unified_config_loader():
    """测试统一配置加载器"""
    logger.info("测试统一配置加载器...")
    
    try:
        from webnet.qq.unified_config import get_qq_config, validate_config
        
        config = get_qq_config()
        
        if not config:
            logger.error("统一配置加载器返回空配置")
            return False
        
        # 检查配置结构
        required_sections = [
            'onebot_ws_url',
            'bot_qq',
            'multimedia',
            'image_recognition',
            'active_chat'
        ]
        
        for section in required_sections:
            if section not in config:
                logger.error(f"统一配置缺少部分: {section}")
                return False
        
        # 验证配置
        is_valid, errors = validate_config()
        
        if not is_valid:
            logger.error(f"配置验证失败: {errors}")
            return False
        
        logger.info("统一配置加载成功:")
        logger.info(f"  - OneBot地址: {config.get('onebot_ws_url')}")
        logger.info(f"  - Bot QQ: {config.get('bot_qq')}")
        logger.info(f"  - OCR启用: {config.get('image_recognition', {}).get('ocr_enabled')}")
        logger.info(f"  - 主动聊天启用: {config.get('active_chat', {}).get('enabled')}")
        
        logger.info("统一配置加载器测试通过")
        return True
        
    except ImportError as e:
        logger.error(f"无法导入统一配置加载器: {e}")
        return False
    except Exception as e:
        logger.error(f"统一配置加载器测试失败: {e}")
        return False


def test_core_integration():
    """测试core.py集成"""
    logger.info("测试core.py集成...")
    
    try:
        from webnet.qq.core import QQNet
        
        # 创建模拟核心
        class MockMiyaCore:
            def __init__(self):
                pass
        
        mock_core = MockMiyaCore()
        qq_net = QQNet(mock_core)
        
        # 检查配置是否已加载
        if not hasattr(qq_net, 'onebot_ws_url'):
            logger.error("QQNet没有onebot_ws_url属性")
            return False
        
        if not qq_net.onebot_ws_url:
            logger.error("QQNet的onebot_ws_url为空")
            return False
        
        logger.info("QQNet配置加载成功:")
        logger.info(f"  - WebSocket地址: {qq_net.onebot_ws_url}")
        logger.info(f"  - Bot QQ: {qq_net.bot_qq}")
        logger.info(f"  - 重连间隔: {qq_net.reconnect_interval}s")
        
        logger.info("core.py集成测试通过")
        return True
        
    except ImportError as e:
        logger.error(f"无法导入QQNet: {e}")
        return False
    except Exception as e:
        logger.error(f"core.py集成测试失败: {e}")
        return False


def test_config_chain():
    """测试配置链：.env -> settings.py -> unified_config -> QQNet"""
    logger.info("测试完整配置链...")
    
    try:
        # 1. 检查.env中的值
        from dotenv import load_dotenv
        
        # 尝试多个.env文件路径
        env_paths = [
            project_root / '.env',
            project_root / 'config' / '.env',
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                logger.info(f"从 {env_path} 加载环境变量")
                env_loaded = True
                break
        
        if not env_loaded:
            logger.error("未找到.env文件")
            return False
        
        env_ws_url = os.getenv('QQ_ONEBOT_WS_URL')
        env_bot_qq = os.getenv('QQ_BOT_QQ')
        
        if not env_ws_url:
            # 直接读取.env文件内容
            for env_path in env_paths:
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for line in content.split('\n'):
                            if line.startswith('QQ_ONEBOT_WS_URL='):
                                env_ws_url = line.split('=', 1)[1]
                                break
                    if env_ws_url:
                        break
            
            if not env_ws_url:
                logger.error(".env中没有QQ_ONEBOT_WS_URL")
                return False
        
        # 2. 检查settings.py中的值
        from config.settings import Settings
        settings = Settings()
        settings_ws_url = settings.get('qq', {}).get('onebot_ws_url')
        settings_bot_qq = settings.get('qq', {}).get('bot_qq')
        
        if settings_ws_url != env_ws_url:
            logger.error(f"settings.py中的OneBot地址不匹配: {settings_ws_url} != {env_ws_url}")
            return False
        
        # 3. 检查unified_config中的值
        from webnet.qq.unified_config import get_qq_config
        unified_config = get_qq_config()
        unified_ws_url = unified_config.get('onebot_ws_url')
        unified_bot_qq = unified_config.get('bot_qq')
        
        if unified_ws_url != env_ws_url:
            logger.error(f"unified_config中的OneBot地址不匹配: {unified_ws_url} != {env_ws_url}")
            return False
        
        # 4. 检查QQNet中的值
        from webnet.qq.core import QQNet
        
        class MockMiyaCore:
            def __init__(self):
                pass
        
        mock_core = MockMiyaCore()
        qq_net = QQNet(mock_core)
        
        if qq_net.onebot_ws_url != env_ws_url:
            logger.error(f"QQNet中的OneBot地址不匹配: {qq_net.onebot_ws_url} != {env_ws_url}")
            return False
        
        logger.info("配置链测试通过:")
        logger.info(f"  .env -> {env_ws_url} (QQ: {env_bot_qq})")
        logger.info(f"  settings.py -> {settings_ws_url} (QQ: {settings_bot_qq})")
        logger.info(f"  unified_config -> {unified_ws_url} (QQ: {unified_bot_qq})")
        logger.info(f"  QQNet -> {qq_net.onebot_ws_url} (QQ: {qq_net.bot_qq})")
        
        return True
        
    except Exception as e:
        logger.error(f"配置链测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("统一配置系统测试")
    logger.info("=" * 70)
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    tests = [
        (".env文件存在性", test_env_file_exists),
        ("settings.py集成", test_settings_integration),
        ("统一配置加载器", test_unified_config_loader),
        ("core.py集成", test_core_integration),
        ("完整配置链", test_config_chain),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n测试: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"[OK] {test_name}")
            else:
                logger.error(f"[FAIL] {test_name}")
        except Exception as e:
            logger.error(f"[ERROR] {test_name}: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("测试结果汇总:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[OK]" if success else "[FAIL]"
        logger.info(f"  {test_name:25} {status}")
    
    logger.info(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n✅ 统一配置系统测试全部通过！")
        logger.info("\n配置系统架构:")
        logger.info("  .env文件 -> settings.py -> unified_config -> QQNet")
        logger.info("\n已实现:")
        logger.info("  1. 所有QQ配置统一到.env文件")
        logger.info("  2. settings.py自动加载.env配置")
        logger.info("  3. unified_config提供统一接口")
        logger.info("  4. QQNet使用统一配置系统")
    else:
        logger.error(f"\n❌ 有 {total-passed} 个测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
