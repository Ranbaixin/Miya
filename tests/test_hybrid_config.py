#!/usr/bin/env python3
"""
测试混合配置系统
"""

import logging
import os
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_env_file_exists():
    """测试.env文件是否存在"""
    logger.info("测试.env文件...")
    
    # 检查多个可能的.env文件位置
    possible_env_paths = [
        project_root / '.env',
        project_root / 'config' / '.env',
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
        return False
    
    if not env_example_path:
        logger.error("未找到.env.example文件")
        return False
    
    logger.info(f".env文件位置: {env_path}")
    logger.info(f".env.example文件位置: {env_example_path}")
    
    # 读取文件大小
    env_size = env_path.stat().st_size
    env_example_size = env_example_path.stat().st_size
    
    logger.info(f".env文件大小: {env_size} 字节")
    logger.info(f".env.example文件大小: {env_example_size} 字节")
    
    # 检查QQ配置是否存在
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    required_qq_configs = [
        'QQ_ONEBOT_WS_URL',
        'QQ_BOT_QQ',
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


def test_yaml_file_exists():
    """测试qq_config.yaml文件是否存在"""
    logger.info("测试qq_config.yaml文件...")
    
    # 检查多个可能的YAML文件位置
    possible_yaml_paths = [
        project_root / 'config' / 'qq_config.yaml',
        project_root / 'qq_config.yaml',
    ]
    
    yaml_path = None
    for path in possible_yaml_paths:
        if path.exists():
            yaml_path = path
            break
    
    if not yaml_path:
        logger.error("未找到qq_config.yaml文件")
        return False
    
    logger.info(f"qq_config.yaml文件位置: {yaml_path}")
    
    # 读取文件大小
    yaml_size = yaml_path.stat().st_size
    
    logger.info(f"qq_config.yaml文件大小: {yaml_size} 字节")
    
    # 检查配置内容
    try:
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            logger.error("YAML文件为空")
            return False
        
        if 'qq' not in config:
            logger.error("YAML文件中缺少'qq'配置节")
            return False
        
        qq_config = config['qq']
        
        # 检查必要的配置节
        required_sections = ['onebot', 'multimedia', 'image_recognition']
        missing_sections = []
        
        for section in required_sections:
            if section not in qq_config:
                missing_sections.append(section)
        
        if missing_sections:
            logger.error(f"QQ配置中缺少节: {missing_sections}")
            return False
        
        logger.info("qq_config.yaml文件测试通过")
        return True
        
    except Exception as e:
        logger.error(f"解析YAML文件失败: {e}")
        return False


def test_hybrid_config_loader():
    """测试混合配置加载器"""
    logger.info("测试混合配置加载器...")
    
    try:
        from webnet.qq.hybrid_config import get_hybrid_config
        
        config_manager = get_hybrid_config()
        full_config = config_manager.get_config()
        
        if not full_config:
            logger.error("获取配置失败")
            return False
        
        # 检查基础配置
        required_keys = ['onebot_ws_url', 'bot_qq', 'connection', 'multimedia']
        missing_keys = []
        
        for key in required_keys:
            if key not in full_config:
                missing_keys.append(key)
        
        if missing_keys:
            logger.error(f"配置中缺少键: {missing_keys}")
            return False
        
        # 检查详细配置
        connection = full_config.get('connection', {})
        full_config.get('multimedia', {})
        image_recognition = full_config.get('image_recognition', {})
        
        logger.info(f"WebSocket地址: {full_config.get('onebot_ws_url')}")
        logger.info(f"Bot QQ: {full_config.get('bot_qq')}")
        logger.info(f"重连间隔: {connection.get('reconnect_interval')}")
        logger.info(f"OCR启用: {image_recognition.get('ocr', {}).get('enabled')}")
        
        # 验证配置值
        if full_config.get('onebot_ws_url') and not (
            full_config['onebot_ws_url'].startswith('ws://') or
            full_config['onebot_ws_url'].startswith('wss://')
        ):
            logger.warning(f"WebSocket地址格式可能不正确: {full_config['onebot_ws_url']}")
        
        logger.info("混合配置加载器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"混合配置加载器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings_integration():
    """测试Settings集成"""
    logger.info("测试Settings集成...")
    
    try:
        from config.settings import Settings
        
        settings = Settings()
        all_config = settings.get_all()
        
        if 'qq' not in all_config:
            logger.error("Settings中缺少QQ配置")
            return False
        
        qq_config = all_config['qq']
        
        # 检查基础配置
        required_keys = ['onebot_ws_url', 'bot_qq']
        missing_keys = []
        
        for key in required_keys:
            if key not in qq_config:
                missing_keys.append(key)
        
        if missing_keys:
            logger.error(f"Settings QQ配置中缺少键: {missing_keys}")
            return False
        
        logger.info(f"Settings WebSocket地址: {qq_config.get('onebot_ws_url')}")
        logger.info(f"Settings Bot QQ: {qq_config.get('bot_qq')}")
        
        # 检查详细配置
        if 'multimedia' in qq_config:
            logger.info("Settings 包含多媒体配置")
        
        if 'image_recognition' in qq_config:
            logger.info("Settings 包含图片识别配置")
        
        logger.info("Settings集成测试通过")
        return True
        
    except Exception as e:
        logger.error(f"Settings集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_chain():
    """测试配置链"""
    logger.info("测试完整配置链...")
    
    try:
        # 1. 测试环境变量加载
        from dotenv import load_dotenv
        
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
        
        # 2. 检查环境变量
        ws_url = os.getenv('QQ_ONEBOT_WS_URL')
        bot_qq = os.getenv('QQ_BOT_QQ')
        
        if not ws_url:
            logger.error("环境变量中缺少QQ_ONEBOT_WS_URL")
            return False
        
        logger.info(f"环境变量 WebSocket地址: {ws_url}")
        logger.info(f"环境变量 Bot QQ: {bot_qq}")
        
        # 3. 测试混合配置加载器
        from webnet.qq.hybrid_config import get_hybrid_config
        
        config_manager = get_hybrid_config()
        hybrid_config = config_manager.get_config()
        
        if hybrid_config.get('onebot_ws_url') != ws_url:
            logger.error("混合配置与.env配置不一致")
            return False
        
        # 4. 测试Settings
        from config.settings import Settings
        
        settings = Settings()
        settings_config = settings.get_all()
        settings_qq = settings_config.get('qq', {})
        
        if settings_qq.get('onebot_ws_url') != ws_url:
            logger.error("Settings配置与.env配置不一致")
            return False
        
        logger.info("配置链验证通过：")
        logger.info(f"  .env -> {ws_url}")
        logger.info(f"  混合配置 -> {hybrid_config.get('onebot_ws_url')}")
        logger.info(f"  Settings -> {settings_qq.get('onebot_ws_url')}")
        
        return True
        
    except Exception as e:
        logger.error(f"配置链测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("开始测试混合配置系统")
    logger.info("=" * 60)
    
    tests = [
        ("测试.env文件", test_env_file_exists),
        ("测试YAML文件", test_yaml_file_exists),
        ("测试混合配置加载器", test_hybrid_config_loader),
        ("测试Settings集成", test_settings_integration),
        ("测试配置链", test_config_chain),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{test_name}...")
        try:
            if test_func():
                logger.info(f"✓ {test_name} 通过")
                passed += 1
            else:
                logger.error(f"✗ {test_name} 失败")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} 异常: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总:")
    logger.info(f"  通过: {passed}")
    logger.info(f"  失败: {failed}")
    logger.info(f"  通过率: {passed}/{len(tests)} ({passed/len(tests)*100:.1f}%)")
    
    if failed == 0:
        logger.info("🎉 所有测试通过！")
        return True
    else:
        logger.error("❌ 部分测试失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
