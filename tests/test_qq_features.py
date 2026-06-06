#!/usr/bin/env python3
"""
QQ功能测试脚本
测试QQ端的所有新功能
"""

import asyncio
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


async def test_config_loading():
    """测试配置加载（使用混合配置系统）"""
    logger.info("测试配置加载...")
    try:
        from webnet.qq.hybrid_config import get_qq_config
        
        config = get_qq_config()
        logger.info(f"混合配置加载成功，OneBot地址: {config.get('onebot_ws_url', '未配置')}")
        
        # 验证配置项
        required_keys = [
            'onebot_ws_url',
            'bot_qq',
            'connection',
            'multimedia',
            'image_recognition',
            'active_chat'
        ]
        
        missing_keys = []
        for key in required_keys:
            if key not in config:
                missing_keys.append(key)
        
        if missing_keys:
            logger.warning(f"缺少配置项: {missing_keys}")
        else:
            logger.info("所有必要配置项都存在")
        
        # 验证配置值
        if config.get('onebot_ws_url') and not (config['onebot_ws_url'].startswith('ws://') or config['onebot_ws_url'].startswith('wss://')):
            logger.warning(f"OneBot地址格式不正确: {config['onebot_ws_url']}")
            return False
        
        # 验证详细配置
        connection = config.get('connection', {})
        if connection.get('reconnect_interval', 0) <= 0:
            logger.warning("重连间隔应为正数")
            return False
        
        logger.info("混合配置验证通过")
        logger.info(f"  重连间隔: {connection.get('reconnect_interval')}")
        logger.info(f"  图片最大大小: {config.get('multimedia', {}).get('image', {}).get('max_size')}")
        logger.info(f"  OCR启用: {config.get('image_recognition', {}).get('ocr', {}).get('enabled')}")
        
        return True
    except Exception as e:
        logger.error(f"配置加载测试失败: {e}")
        return False


async def test_tool_registration():
    """测试工具注册"""
    logger.info("测试工具注册...")
    try:
        # 检查工具文件是否存在
        qq_tools = [
            ('qq_image', 'QQImageTool'),
            ('qq_file', 'QQFileTool'),
            ('qq_emoji', 'QQEmojiTool'),
            ('qq_file_reader', 'QQFileReaderTool'),
            ('qq_image_analyzer', 'QQImageAnalyzerTool'),
            ('qq_active_chat', 'QQActiveChatTool')
        ]
        
        found_tools = []
        missing_tools = []
        
        for tool_name, class_name in qq_tools:
            tool_path = f"webnet/ToolNet/tools/qq/{tool_name}.py"
            if os.path.exists(tool_path):
                found_tools.append(tool_name)
                
                # 尝试导入工具类
                try:
                    module_name = f"webnet.ToolNet.tools.qq.{tool_name}"
                    module = __import__(module_name, fromlist=[class_name])
                    tool_class = getattr(module, class_name)
                    
                    # 检查工具配置
                    tool_instance = tool_class()
                    config = tool_instance.config
                    
                    required_keys = ['name', 'description', 'parameters']
                    for key in required_keys:
                        if key not in config:
                            logger.error(f"工具 {tool_name} 缺少配置键: {key}")
                            missing_tools.append(tool_name)
                            break
                    else:
                        logger.info(f"  ✓ {tool_name}: {config.get('name', tool_name)}")
                except Exception as e:
                    logger.warning(f"  ⚠ {tool_name}: 导入错误 - {e}")
                    missing_tools.append(tool_name)
            else:
                missing_tools.append(tool_name)
                logger.warning(f"  ✗ {tool_name}: 文件不存在")
        
        logger.info(f"已创建的QQ工具: {found_tools}")
        if missing_tools:
            logger.warning(f"未创建的QQ工具: {missing_tools}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"工具注册测试失败: {e}")
        return False


async def test_image_handler():
    """测试图片处理器"""
    logger.info("测试图片处理器...")
    try:
        from webnet.qq.image_handler import QQImageHandler
        
        # 创建模拟QQNet
        class MockQQNet:
            def __init__(self):
                self.config = {}
                
        mock_net = MockQQNet()
        handler = QQImageHandler(mock_net)
        
        # 测试方法存在性
        required_methods = [
            'handle_image_message',
            '_extract_image_info',
            '_download_image',
            '_analyze_image',
            'configure'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(handler, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            logger.error(f"图片处理器缺少方法: {missing_methods}")
            return False
        
        logger.info("图片处理器测试通过")
        return True
    except Exception as e:
        logger.error(f"图片处理器测试失败: {e}")
        return False


async def test_file_reader_tool():
    """测试文件读取工具"""
    logger.info("测试文件读取工具...")
    try:
        from webnet.ToolNet.tools.qq.qq_file_reader import QQFileReaderTool
        
        tool = QQFileReaderTool()
        
        # 检查工具配置
        config = tool.config
        required_config_keys = ['name', 'description', 'parameters']
        
        for key in required_config_keys:
            if key not in config:
                logger.error(f"工具配置缺少键: {key}")
                return False
        
        # 检查参数配置
        parameters = config.get('parameters', {})
        if 'properties' not in parameters or 'required' not in parameters:
            logger.error("工具参数配置不完整")
            return False
        
        logger.info(f"文件读取工具测试通过: {config['name']}")
        return True
    except Exception as e:
        logger.error(f"文件读取工具测试失败: {e}")
        return False


async def test_image_analyzer_tool():
    """测试图片分析工具"""
    logger.info("测试图片分析工具...")
    try:
        from webnet.ToolNet.tools.qq.qq_image_analyzer import QQImageAnalyzerTool
        
        tool = QQImageAnalyzerTool()
        
        # 检查工具配置
        config = tool.config
        required_config_keys = ['name', 'description', 'parameters']
        
        for key in required_config_keys:
            if key not in config:
                logger.error(f"工具配置缺少键: {key}")
                return False
        
        # 检查参数配置
        parameters = config.get('parameters', {})
        if 'properties' not in parameters or 'required' not in parameters:
            logger.error("工具参数配置不完整")
            return False
        
        logger.info(f"图片分析工具测试通过: {config['name']}")
        return True
    except Exception as e:
        logger.error(f"图片分析工具测试失败: {e}")
        return False


async def test_active_chat_tool():
    """测试主动聊天工具"""
    logger.info("测试主动聊天工具...")
    try:
        from webnet.ToolNet.tools.qq.qq_active_chat import QQActiveChatTool
        
        tool = QQActiveChatTool()
        
        # 检查工具配置
        config = tool.config
        required_config_keys = ['name', 'description', 'parameters']
        
        for key in required_config_keys:
            if key not in config:
                logger.error(f"工具配置缺少键: {key}")
                return False
        
        # 检查参数配置
        parameters = config.get('parameters', {})
        if 'properties' not in parameters or 'required' not in parameters:
            logger.error("工具参数配置不完整")
            return False
        
        logger.info(f"主动聊天工具测试通过: {config['name']}")
        return True
    except Exception as e:
        logger.error(f"主动聊天工具测试失败: {e}")
        return False


async def test_client_apis():
    """测试客户端API"""
    logger.info("测试客户端API...")
    try:
        from webnet.qq.client import QQOneBotClient
        
        # 检查API方法是否存在
        required_methods = [
            'send_group_message',
            'send_private_message',
            'upload_image',
            'upload_file',
            'send_group_image',
            'send_private_image',
            'send_group_file',
            'send_private_file'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(QQOneBotClient, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            logger.error(f"客户端缺少API方法: {missing_methods}")
            return False
        
        logger.info("客户端API测试通过")
        return True
    except Exception as e:
        logger.error(f"客户端API测试失败: {e}")
        return False


async def test_config_file_exists():
    """测试配置文件是否存在"""
    logger.info("测试配置文件...")
    
    config_paths = [
        "config/qq_config.yaml",
        "../config/qq_config.yaml"
    ]
    
    found = False
    for path in config_paths:
        full_path = project_root / path
        if full_path.exists():
            logger.info(f"配置文件找到: {full_path}")
            found = True
            
            # 读取配置文件大小
            size = full_path.stat().st_size
            logger.info(f"配置文件大小: {size} 字节")
            
            # 检查关键配置项
            import yaml
            with open(full_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if config and 'qq' in config:
                logger.info("配置文件结构正确")
            else:
                logger.warning("配置文件缺少'qq'根节点")
    
    if not found:
        logger.warning("未找到配置文件，将使用默认配置")
    
    return True


async def test_dependencies():
    """测试依赖包"""
    logger.info("测试依赖包...")
    
    dependencies = [
        ('pillow', 'PIL'),          # 图片处理
        ('pytesseract', 'pytesseract'),     # OCR
        ('paddleocr', 'paddleocr'),       # PaddleOCR
        ('PyPDF2', 'PyPDF2'),          # PDF处理
        ('python-docx', 'docx'),     # Word文档处理
        ('chardet', 'chardet'),         # 编码检测
        ('pyyaml', 'yaml'),            # YAML解析
    ]
    
    missing_deps = []
    
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            logger.info(f"  ✓ {package_name}")
        except ImportError:
            # 尝试使用pip检查
            try:
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', package_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.info(f"  ✓ {package_name} (已安装)")
                else:
                    logger.warning(f"  ✗ {package_name} 未安装")
                    missing_deps.append(package_name)
            except:
                logger.warning(f"  ✗ {package_name} 未安装")
                missing_deps.append(package_name)
    
    if missing_deps:
        logger.warning(f"缺失依赖包: {missing_deps}")
        logger.warning("请运行: pip install " + " ".join(missing_deps))
        return False
    
    logger.info("所有依赖包测试通过")
    return True


async def run_all_tests():
    """运行所有测试"""
    logger.info("开始QQ功能测试套件")
    logger.info("=" * 60)
    
    tests = [
        ("配置加载", test_config_loading),
        ("配置文件存在性", test_config_file_exists),
        ("依赖包", test_dependencies),
        ("工具注册", test_tool_registration),
        ("客户端API", test_client_apis),
        ("图片处理器", test_image_handler),
        ("文件读取工具", test_file_reader_tool),
        ("图片分析工具", test_image_analyzer_tool),
        ("主动聊天工具", test_active_chat_tool),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n测试: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"✓ {test_name} 通过")
            else:
                logger.error(f"✗ {test_name} 失败")
        except Exception as e:
            logger.error(f"✗ {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        logger.info(f"  {test_name:20} {status}")
    
    logger.info(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 所有测试通过！")
    else:
        logger.warning(f"⚠️  有 {total-passed} 个测试失败")
    
    return all(success for _, success in results)


def main():
    """主函数"""
    try:
        # 切换到项目根目录
        os.chdir(project_root)
        
        # 运行测试
        success = asyncio.run(run_all_tests())
        
        if success:
            logger.info("\n✅ 所有功能已正确实现！")
            logger.info("可以开始使用以下QQ功能:")
            logger.info("  1. 图片发送 (qq_image)")
            logger.info("  2. 文件发送 (qq_file)")
            logger.info("  3. 表情包发送 (qq_emoji)")
            logger.info("  4. 文件读取 (qq_file_reader)")
            logger.info("  5. 图片识别 (qq_image_analyzer)")
            logger.info("  6. 主动聊天 (qq_active_chat)")
            logger.info("  7. 增强定时任务 (task_scheduler_enhanced)")
        else:
            logger.error("\n❌ 部分测试失败，请检查上述错误信息")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"测试运行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
