"""
SecurityNet 子网核心

弥娅的网络安全分析引擎，提供专业的安全评估能力。
遵循 BaseSubnet 接口规范运行。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """安全子网配置"""

    subnet_name: str = "SecurityNet"
    subnet_id: str = "subnet.security"
    version: str = "1.0.0"
    enabled: bool = True
    risk_warning_enabled: bool = True
    max_scan_timeout: int = 30

    # 核心组件引用
    memory_engine: Any = None
    onebot_client: Any = None
    knowledge_graph: Any = None

    # 统计信息
    total_scans: int = 0
    vulnerabilities_found: int = 0
    last_scan_time: Optional[datetime] = None


class SecuritySubnet:
    """
    弥娅的网络安全子网

    能力范围：
    - 网络侦查与信息收集
    - 漏洞查询与分析
    - 安全评估与建议
    - 安全知识库管理

    使用示例:
        subnet = SecuritySubnet(config=SecurityConfig())
        result = await subnet.scan_ports("example.com", [80, 443, 22])
        whois_info = await subnet.whois_lookup("example.com")
        report = await subnet.generate_security_report("example.com")
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.logger = logging.getLogger(self.config.subnet_name)
        self.tools: Dict[str, Any] = {}
        self._scan_history: List[Dict[str, Any]] = []
        self._init_tools()
        self.logger.info(f"[{self.config.subnet_name}] 子网已启动 v{self.config.version}")

    def _init_tools(self):
        """初始化安全工具（14 个）"""
        from webnet.ToolNet.tools.security.port_scanner import get_security_port_scan_tool
        from webnet.ToolNet.tools.security.nmap_scan import get_security_nmap_scan_tool
        from webnet.ToolNet.tools.security.subdomain_enum import get_security_subdomain_enum_tool
        from webnet.ToolNet.tools.security.dns_enum import get_security_dns_enum_tool
        from webnet.ToolNet.tools.security.http_headers import get_security_http_headers_tool
        from webnet.ToolNet.tools.security.ssl_cert import get_security_ssl_cert_tool
        from webnet.ToolNet.tools.security.vuln_lookup import get_security_vuln_lookup_tool
        from webnet.ToolNet.tools.security.sploitus_search import get_security_sploitus_search_tool
        from webnet.ToolNet.tools.security.online_asset import get_security_online_asset_tool
        from webnet.ToolNet.tools.security.dir_brute import get_security_dir_brute_tool
        from webnet.ToolNet.tools.security.web_vuln_scanner import get_security_web_vuln_scanner_tool
        from webnet.ToolNet.tools.security.sandbox_exec import get_security_sandbox_exec_tool
        from webnet.ToolNet.tools.security.ctf_workflow import get_security_ctf_workflow_tool
        from webnet.ToolNet.tools.security.tool_index import get_security_tool_index_tool

        self.tools["security_port_scan"] = get_security_port_scan_tool()
        self.tools["security_nmap_scan"] = get_security_nmap_scan_tool()
        self.tools["security_subdomain_enum"] = get_security_subdomain_enum_tool()
        self.tools["security_dns_enum"] = get_security_dns_enum_tool()
        self.tools["security_http_headers"] = get_security_http_headers_tool()
        self.tools["security_ssl_cert"] = get_security_ssl_cert_tool()
        self.tools["security_vuln_lookup"] = get_security_vuln_lookup_tool()
        self.tools["security_sploitus_search"] = get_security_sploitus_search_tool()
        self.tools["security_online_asset"] = get_security_online_asset_tool()
        self.tools["security_dir_brute"] = get_security_dir_brute_tool()
        self.tools["security_web_vuln_scanner"] = get_security_web_vuln_scanner_tool()
        self.tools["security_sandbox_exec"] = get_security_sandbox_exec_tool()
        self.tools["security_ctf_workflow"] = get_security_ctf_workflow_tool()
        self.tools["security_tool_index"] = get_security_tool_index_tool()

        self.logger.info(f"[SecurityNet] 已加载 {len(self.tools)} 个安全工具")

    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        message_type: Optional[str] = None,
        sender_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """执行安全工具"""
        tool = self.tools.get(tool_name)
        if not tool:
            return f"❌ 工具未找到: {tool_name}"

        if self.config.risk_warning_enabled:
            self.logger.warning(f"[SecurityNet] 安全工具调用: {tool_name} by user={user_id} group={group_id}")

        try:
            from webnet.ToolNet.base import ToolContext

            context = ToolContext(
                user_id=user_id,
                group_id=group_id,
                message_type=message_type,
                sender_name=sender_name,
            )
            result = await tool.execute(args, context)
            self._record_scan(tool_name, args, "success")
            return result
        except Exception as e:
            self._record_scan(tool_name, args, "failed")
            self.logger.error(f"[SecurityNet] 执行 {tool_name} 失败: {e}", exc_info=True)
            return f"❌ 安全扫描失败: {str(e)}"

    def _record_scan(self, tool_name: str, args: Dict[str, Any], status: str):
        """记录扫描历史"""
        self.config.total_scans += 1
        self.config.last_scan_time = datetime.now()
        self._scan_history.append(
            {
                "tool": tool_name,
                "args": {k: v for k, v in args.items() if k != "raw_data"},
                "status": status,
                "time": self.config.last_scan_time.isoformat(),
            }
        )
        if len(self._scan_history) > 1000:
            self._scan_history = self._scan_history[-500:]

    def get_tool_list(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        result = []
        for name, tool in self.tools.items():
            result.append(
                {
                    "name": name,
                    "config": tool.config,
                    "subnet": self.config.subnet_name,
                }
            )
        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取子网统计"""
        return {
            "subnet_name": self.config.subnet_name,
            "version": self.config.version,
            "total_tools": len(self.tools),
            "total_scans": self.config.total_scans,
            "vulnerabilities_found": self.config.vulnerabilities_found,
            "last_scan_time": self.config.last_scan_time.isoformat() if self.config.last_scan_time else None,
        }

    def health_check(self) -> bool:
        """健康检查"""
        return self.config.enabled and len(self.tools) > 0

    async def shutdown(self):
        """关闭子网"""
        self.logger.info(f"[{self.config.subnet_name}] 子网正在关闭...")
        self.tools.clear()
        self._scan_history.clear()
        self.logger.info(f"[{self.config.subnet_name}] 子网已关闭")

    async def generate_security_report(self, target: str, findings: List[Dict[str, Any]]) -> str:
        """生成安全评估报告"""
        hostname = target.split("://")[-1].split("/")[0].split(":")[0]
        report = [
            f"## 安全评估报告",
            f"**目标**: {hostname}",
            f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**评估引擎**: 弥娅 SecurityNet v{self.config.version}",
            "",
            "---",
            "",
            "### 发现摘要",
            "",
            f"- 总检查项: {len(findings)}",
        ]

        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        low = sum(1 for f in findings if f.get("severity") == "low")

        report.append(f"- 严重: {critical}  |  高危: {high}  |  中危: {medium}  |  低危: {low}")
        report.append("")
        report.append("### 详细发现")
        report.append("")

        for i, finding in enumerate(findings, 1):
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}.get(
                finding.get("severity", "info"), "⚪"
            )
            report.append(
                f"**{i}. {severity_icon} [{finding.get('severity', 'info').upper()}] {finding.get('title', '未知')}**"
            )
            report.append(f"- 描述: {finding.get('description', 'N/A')}")
            report.append(f"- 建议: {finding.get('recommendation', 'N/A')}")
            report.append("")

        report.append("---")
        report.append(f"*报告由弥娅 SecurityNet 自动生成*")

        return "\n".join(report)
