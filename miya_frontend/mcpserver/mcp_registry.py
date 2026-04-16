"""
mcp_registry 兼容层
"""


class MCPRegistry:
    """MCP注册表（占位符）"""

    def __init__(self):
        self.tools = {}

    def get_tools(self):
        return []

    def get_tool(self, name):
        return None


MCP_REGISTRY = MCPRegistry()
