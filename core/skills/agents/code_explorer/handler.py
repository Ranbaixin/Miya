"""代码探索Agent处理器"""

from typing import Any, Dict


async def handler(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    """处理代码探索请求"""
    action = args.get("action", "explore")
    target = args.get("target", "")
    path = args.get("path", ".") or "."

    # 获取 TerminalUltra 实例
    from core.terminal_ultra import get_terminal_ultra

    terminal = get_terminal_ultra()

    if action == "explore":
        # 探索项目结构
        result = await terminal.directory_tree(path, max_depth=3)
        return result.output if result.success else f"错误: {result.error}"

    elif action == "find_symbol":
        # 搜索符号
        result = await terminal.code_search_symbol(target, path)
        return result.output if result.success else f"错误: {result.error}"

    elif action == "find_definitions":
        # 查找定义
        result = await terminal.code_find_definitions(target, path)
        return result.output if result.success else f"错误: {result.error}"

    elif action == "find_references":
        # 查找引用
        result = await terminal.code_find_references(target, path)
        return result.output if result.success else f"错误: {result.error}"

    elif action == "analyze_structure":
        # 分析项目结构
        result = await terminal.project_analyze(path)
        return result.output if result.success else f"错误: {result.error}"

    else:
        return f"未知动作: {action}"


# Skill 元数据
__skill_meta__ = {
    "name": "code_explorer",
    "version": "1.0.0",
    "description": "代码探索Agent - 分析项目结构、理解代码关系",
}
