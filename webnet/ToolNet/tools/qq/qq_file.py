"""
QQ文件发送工具

支持发送文件到QQ群或私聊，支持多种文件类型
"""

import builtins
import contextlib
import logging
import os
from typing import Any, Dict, Optional

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class QQFileTool(BaseTool):
    """QQ文件发送工具"""
    
    # 支持的文件类型
    SUPPORTED_FILE_TYPES = {
        ".txt": "文本文档",
        ".pdf": "PDF文档",
        ".doc": "Word文档",
        ".docx": "Word文档",
        ".xls": "Excel表格",
        ".xlsx": "Excel表格",
        ".ppt": "PowerPoint演示",
        ".pptx": "PowerPoint演示",
        ".jpg": "图片",
        ".jpeg": "图片",
        ".png": "图片",
        ".gif": "动图",
        ".mp3": "音频",
        ".mp4": "视频",
        ".zip": "压缩包",
        ".rar": "压缩包",
        ".7z": "压缩包"
    }
    
    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "qq_file",
            "description": "发送文件到QQ群或私聊。支持本地文件路径、网络文件URL。用户说'发文件'、'发送文件'、'分享文件'时，必须调用此工具。注意检查文件大小限制和文件类型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_type": {
                        "type": "string",
                        "description": "目标类型：group(群聊)或private(私聊)，默认为当前会话类型",
                        "enum": ["group", "private"],
                        "default": "group"
                    },
                    "target_id": {
                        "type": "integer",
                        "description": "目标ID（群号或用户QQ号），默认为当前用户ID或群ID"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "文件路径或URL"
                    },
                    "caption": {
                        "type": "string",
                        "description": "文件说明文字，可选"
                    },
                    "file_source": {
                        "type": "string",
                        "description": "文件来源：local(本地文件)、url(网络地址)，默认为local",
                        "enum": ["local", "url"],
                        "default": "local"
                    },
                    "max_size_mb": {
                        "type": "integer",
                        "description": "最大文件大小（MB），默认为50MB",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["file_path"]
            }
        }
    
    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        """执行文件发送"""
        try:
            # 获取参数
            target_type = args.get("target_type", "group")
            target_id = args.get("target_id", self._get_default_target_id(context))
            file_path = args.get("file_path", "")
            caption = args.get("caption", "")
            file_source = args.get("file_source", "local")
            max_size_mb = args.get("max_size_mb", 50)
            
            if not file_path:
                return "❌ 请提供文件路径或URL"
            
            # 获取QQ客户端
            qq_client = getattr(context, 'onebot_client', None)
            if not qq_client:
                return "❌ QQ客户端不可用"
            
            # 处理文件
            temp_file_path = await self._process_file(
                file_source, file_path, max_size_mb
            )
            
            if not temp_file_path:
                return "❌ 文件处理失败"
            
            try:
                # 检查文件类型
                file_ext = os.path.splitext(temp_file_path)[1].lower()
                if file_ext not in self.SUPPORTED_FILE_TYPES:
                    logger.warning(f"发送不受支持的文件类型: {file_ext}")
                
                # 发送文件
                if target_type == "group":
                    result = await qq_client.send_group_file(
                        group_id=target_id,
                        file_path=temp_file_path,
                        caption=caption
                    )
                    target_desc = f"群 {target_id}"
                else:
                    result = await qq_client.send_private_file(
                        user_id=target_id,
                        file_path=temp_file_path,
                        caption=caption
                    )
                    target_desc = f"用户 {target_id}"
                
                # 清理临时文件（如果是下载的）
                if file_source == "url":
                    with contextlib.suppress(builtins.BaseException):
                        os.unlink(temp_file_path)
                
                if result and result.get("status") == "ok":
                    file_name = os.path.basename(temp_file_path)
                    file_type = self.SUPPORTED_FILE_TYPES.get(file_ext, "未知类型")
                    return f"✅ {file_type} '{file_name}' 已发送到 {target_desc}"
                else:
                    return f"❌ 文件发送失败: {result}"
                    
            except Exception as e:
                # 清理临时文件
                if file_source == "url":
                    with contextlib.suppress(builtins.BaseException):
                        os.unlink(temp_file_path)
                raise e
                
        except Exception as e:
            logger.error(f"文件发送失败: {e}", exc_info=True)
            return f"❌ 文件发送失败: {str(e)}"
    
    def _get_default_target_id(self, context: ToolContext) -> int:
        """获取默认目标ID"""
        # 优先使用群ID，没有则使用用户ID
        if context.group_id:
            return context.group_id
        elif context.user_id:
            return context.user_id
        else:
            return 0
    
    async def _process_file(
        self,
        file_source: str,
        file_path: str,
        max_size_mb: int
    ) -> Optional[str]:
        """处理文件，返回临时文件路径"""
        import tempfile

        import httpx
        
        temp_file = None
        temp_file_path = None
        
        try:
            if file_source == "local":
                # 本地文件
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                
                # 检查文件大小
                file_size = os.path.getsize(file_path)
                max_size_bytes = max_size_mb * 1024 * 1024
                
                if file_size > max_size_bytes:
                    raise ValueError(f"文件过大 ({file_size} bytes > {max_size_bytes} bytes)，请减小文件大小或调整限制")
                
                return file_path
                
            elif file_source == "url":
                # 网络文件
                import aiofiles
                
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file_path = temp_file.name
                temp_file.close()
                
                # 从URL下载文件
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_path, timeout=60.0, follow_redirects=True)
                    if response.status_code != 200:
                        raise Exception(f"下载文件失败: HTTP {response.status_code}")
                    
                    # 检查内容类型
                    response.headers.get('content-type', '')
                    content_length = int(response.headers.get('content-length', 0))
                    
                    max_size_bytes = max_size_mb * 1024 * 1024
                    if content_length > max_size_bytes:
                        raise ValueError(f"文件过大 ({content_length} bytes > {max_size_bytes} bytes)")
                    
                    # 保存文件
                    async with aiofiles.open(temp_file_path, 'wb') as f:
                        chunk_size = 8192
                        total_size = 0
                        
                        async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                            total_size += len(chunk)
                            
                            # 检查下载过程中的大小
                            if total_size > max_size_bytes:
                                raise ValueError("文件下载过程中超过大小限制")
                            
                            await f.write(chunk)
                
                # 从URL推断文件名
                parsed_url = httpx.URL(file_path)
                url_filename = parsed_url.path.split('/')[-1]
                
                # 如果有文件名，重命名临时文件
                if url_filename and '.' in url_filename:
                    new_temp_path = os.path.join(
                        os.path.dirname(temp_file_path),
                        url_filename
                    )
                    os.rename(temp_file_path, new_temp_path)
                    temp_file_path = new_temp_path
                
                return temp_file_path
                
            else:
                raise ValueError(f"不支持的文件来源: {file_source}")
            
        except Exception as e:
            logger.error(f"文件处理失败: {e}")
            
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(temp_file_path)
                    
            return None
    
    async def _get_supported_files_info(self) -> str:
        """获取支持的文件类型信息"""
        info_lines = ["支持的文件类型:"]
        
        # 按类别分组
        categories = {}
        for ext, desc in self.SUPPORTED_FILE_TYPES.items():
            category = desc.split(' ')[0] if ' ' in desc else desc
            if category not in categories:
                categories[category] = []
            categories[category].append(ext)
        
        for category, exts in categories.items():
            info_lines.append(f"  {category}: {', '.join(exts)}")
        
        info_lines.append("\n最大文件大小: 50MB")
        info_lines.append("注意: 实际限制可能受OneBot实现影响")
        
        return "\n".join(info_lines)
