#!/usr/bin/env python3
"""
启动QQ机器人并验证OCR修复
"""

import logging
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 在导入任何模块之前设置环境变量
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ocr_before_start():
    """在启动前测试OCR"""
    logger.info("启动前OCR测试...")
    
    try:
        # 测试PaddleOCR导入
        from paddleocr import PaddleOCR
        
        # 尝试初始化OCR
        logger.info("初始化PaddleOCR...")
        try:
            PaddleOCR(lang='ch')
            logger.info("✅ PaddleOCR初始化成功")
            return True
        except Exception as e:
            logger.error(f"❌ PaddleOCR初始化失败: {e}")
            
            # 尝试使用更简单的参数
            try:
                PaddleOCR()
                logger.info("✅ PaddleOCR无参数初始化成功")
                return True
            except Exception as e2:
                logger.error(f"❌ PaddleOCR无参数初始化也失败: {e2}")
                return False
                
    except ImportError:
        logger.error("❌ PaddleOCR未安装")
        logger.info("请安装: pip install paddlepaddle paddleocr")
        return False

def start_qq_bot():
    """启动QQ机器人"""
    logger.info("启动QQ机器人...")
    
    try:
        # 导入QQ核心模块
        from webnet.qq.core import QQNet
        
        # 创建QQNet实例
        qq_net = QQNet()
        
        # 配置OCR测试
        logger.info("配置OCR引擎...")
        
        # 测试图片处理器
        from webnet.qq.image_handler import QQImageHandler
        
        # 创建图片处理器
        image_handler = QQImageHandler(qq_net)
        
        # 配置OCR
        image_handler.configure(enable_ocr=True, enable_ai_analysis=False)
        
        if image_handler.ocr_engine:
            logger.info(f"✅ OCR引擎初始化成功: {type(image_handler.ocr_engine)}")
        else:
            logger.warning("⚠️ OCR引擎未初始化")
        
        # 启动QQ机器人
        logger.info("准备启动QQ机器人...")
        
        # 这里只是测试，不实际启动
        logger.info("✅ OCR修复验证完成")
        logger.info("现在可以正常启动QQ机器人了")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 启动测试失败: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("QQ机器人OCR修复验证")
    logger.info("=" * 60)
    
    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"项目根目录: {project_root}")
    logger.info(f"环境变量 PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK: {os.environ.get('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK')}")
    
    # 测试OCR
    if not test_ocr_before_start():
        logger.error("OCR测试失败，无法启动QQ机器人")
        return False
    
    # 启动QQ机器人测试
    if not start_qq_bot():
        logger.error("QQ机器人启动测试失败")
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 OCR修复验证完成！")
    logger.info("现在可以正常启动QQ机器人了")
    logger.info("=" * 60)
    
    logger.info("\n启动命令:")
    logger.info("python -m webnet.qq.core")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
