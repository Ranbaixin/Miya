"""
智能渗透测试编排引擎
────────────────────────────────
弥娅 SecurityNet 的核心决策中枢，实现从侦察到利用的全链路自动化。

流程：
  1. 侦察 (Recon)        端口扫描 + 子域名 + DNS + 在线资产搜索
  2. 分析 (Analyze)      从结果中提取服务/版本 → 自动查工具目录 + CVE + ExploitDB
  3. 利用 (Exploit)      在 Docker 沙箱中自动拉取执行推荐工具
  4. 威胁情报 (Intel)    查询 NVD/Sploitus 漏洞情报
  5. 报告 (Report)       汇总所有阶段的发现，生成专业报告

策略: recon / quick / full / webapp / deep（全链路自动化）
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from config.security_net_loader import get_orchestrator_config
except ImportError:
    get_orchestrator_config = lambda: {}

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ANALYZED = auto()  # Phase 2 特有的中间状态


@dataclass
class ServiceInfo:
    """从扫描结果中提取的服务信息"""

    name: str
    version: str = ""
    port: int = 0
    product: str = ""
    proto: str = "tcp"
    raw: str = ""


@dataclass
class ScanTask:
    name: str
    tool: str
    args: Dict[str, Any]
    phase: int = 1
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None


@dataclass
class ScanPlan:
    target: str
    strategy: str = "quick"
    tasks: List[ScanTask] = field(default_factory=list)
    services: List[ServiceInfo] = field(default_factory=list)
    tool_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    vuln_intel: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: TaskStatus = TaskStatus.PENDING
    phases_completed: Set[int] = field(default_factory=set)


class IntelligentOrchestrator:
    """
    智能渗透测试编排器

    和之前的 SecurityOrchestrator 不同，这个版本实现：
    - 自动分析扫描结果，提取服务/版本信息
    - 自动查询工具目录推荐匹配工具
    - 自动查询漏洞情报
    - 自动在沙箱中执行推荐工具（deep 模式）
    """

    STRATEGIES: Dict[str, Dict[str, Any]] = {}
    PHASE1_TOOLS: List[tuple] = []
    PHASE1_EXTRA: List[tuple] = []
    PHASE3_TOOLS: List[tuple] = []
    SERVICE_PATTERNS: List[Dict[str, str]] = []

    @classmethod
    def _load_config(cls):
        """从 security_net.yaml 加载配置"""
        cfg = get_orchestrator_config()
        cls.STRATEGIES = cfg.get("strategies", {})
        cls.PHASE1_TOOLS = [tuple(item) for item in cfg.get("phase1_tools", [])]
        cls.PHASE1_EXTRA = [tuple(item) for item in cfg.get("phase1_extra", [])]
        cls.PHASE3_TOOLS = [tuple(item) for item in cfg.get("phase3_tools", [])]
        cls.SERVICE_PATTERNS = cfg.get("service_patterns", [])

    def __init__(self):
        self._load_config()
        self.active_plans: Dict[str, ScanPlan] = {}
        self.tool_executor: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None

    def set_tool_executor(self, executor: Callable):
        self.tool_executor = executor

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback

    def create_plan(self, target: str, strategy: str = "quick") -> Optional[ScanPlan]:
        """创建智能扫描计划"""
        if strategy not in self.STRATEGIES:
            logger.warning(f"未知策略: {strategy}")
            return None

        strat = self.STRATEGIES[strategy]
        hostname = target.split("://")[-1].split("/")[0].split(":")[0]

        plan = ScanPlan(target=hostname, strategy=strategy)
        phases = strat["phases"]

        # Phase 1: 侦察
        if 1 in phases:
            for name, tool, args in self.PHASE1_TOOLS:
                plan.tasks.append(self._make_task(name, tool, args, hostname, 1))
            if strategy in ("full", "deep"):
                for name, tool, args in self.PHASE1_EXTRA:
                    plan.tasks.append(self._make_task(name, tool, args, hostname, 1))

        # Phase 3: 漏洞检测
        if 3 in phases:
            for name, tool, args in self.PHASE3_TOOLS:
                plan.tasks.append(self._make_task(name, tool, args, hostname, 3))

        plan_id = f"{hostname}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.active_plans[plan_id] = plan
        logger.info(f"创建扫描计划 {plan_id}: {strat['name']} → {hostname} (phases={phases})")
        return plan

    def _make_task(self, name: str, tool: str, args: Dict, target: str, phase: int) -> ScanTask:
        resolved = {}
        for k, v in args.items():
            resolved[k] = v.replace("{target}", target) if isinstance(v, str) else v
        return ScanTask(name=name, tool=tool, args=resolved, phase=phase)

    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """多阶段执行扫描计划"""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {"error": f"计划不存在: {plan_id}"}
        if not self.tool_executor:
            return {"error": "工具执行器未设置"}

        plan.status = TaskStatus.RUNNING
        start_time = datetime.now()
        strat = self.STRATEGIES[plan.strategy]
        phases = strat["phases"]
        completed = 0
        total_tasks = 0

        # ── Phase 1: 侦察 ──────────────────────────────
        if 1 in phases:
            self._notify(plan_id, "Phase 1/5: 侦察 — 信息收集")
            phase1_tasks = [t for t in plan.tasks if t.phase == 1]
            total_tasks += len(phase1_tasks)

            # 并行执行 Phase 1 任务
            async def _run_one(t: ScanTask):
                t.status = TaskStatus.RUNNING
                try:
                    t.result = await self.tool_executor(t.tool, t.args)
                    t.status = TaskStatus.COMPLETED
                except Exception as e:
                    t.status = TaskStatus.FAILED
                    t.result = f"失败: {e}"

            await asyncio.gather(*[_run_one(t) for t in phase1_tasks])
            completed = sum(1 for t in phase1_tasks if t.status == TaskStatus.COMPLETED)
            plan.phases_completed.add(1)

        # ── Phase 2: 分析 ──────────────────────────────
        if 2 in phases:
            self._notify(plan_id, "Phase 2/5: 分析 — 提取服务 + 自动查询工具/漏洞")
            phase1_results_str = "\n".join(t.result or "" for t in plan.tasks if t.phase == 1 and t.result)

            # 2a. 提取服务信息
            plan.services = self._extract_services(phase1_results_str)
            self._notify(plan_id, f"  识别到 {len(plan.services)} 个服务")

            # 2b. 自动查询工具目录
            for svc in plan.services:
                try:
                    result = await self.tool_executor("security_tool_index", {"keyword": svc.name})
                    if result and "未找到" not in str(result):
                        plan.tool_recommendations.append(
                            {
                                "service": f"{svc.name} {svc.version}".strip(),
                                "recommendation": str(result)[:1000],
                            }
                        )
                except Exception as __e:
                    logger.debug(f"[orchestrator] 漏洞查询失败: {__e}")

            # 2c. 自动查询 CVE + 漏洞利用
            keywords = set()
            for svc in plan.services:
                keywords.add(svc.name)
                if svc.product:
                    keywords.add(svc.product)

            for kw in keywords:
                try:
                    result = await self.tool_executor("security_vuln_lookup", {"keyword": kw})
                    if result and "未找到" not in str(result):
                        plan.vuln_intel.append(
                            {
                                "source": "CVE/NVD",
                                "query": kw,
                                "result": str(result)[:2000],
                            }
                        )
                except Exception as __e:
                    logger.debug(f"[orchestrator] CVE查询失败: {__e}")

                try:
                    result = await self.tool_executor("security_sploitus_search", {"keyword": kw})
                    if result and "未找到" not in str(result):
                        plan.vuln_intel.append(
                            {
                                "source": "Sploitus/ExploitDB",
                                "query": kw,
                                "result": str(result)[:2000],
                            }
                        )
                except Exception as __e:
                    logger.debug(f"[orchestrator] Sploitus查询失败: {__e}")

            plan.phases_completed.add(2)

        # ── Phase 3: 漏洞检测 / 沙箱利用 ───────────────
        if 3 in phases:
            self._notify(plan_id, "Phase 3/5: 利用 — 漏洞检测 + 工具推荐")
            phase3_tasks = [t for t in plan.tasks if t.phase == 3]
            total_tasks += len(phase3_tasks)
            for t in phase3_tasks:
                t.status = TaskStatus.RUNNING
                try:
                    t.result = await self.tool_executor(t.tool, t.args)
                    t.status = TaskStatus.COMPLETED
                    completed += 1
                except Exception as e:
                    t.status = TaskStatus.FAILED
                    t.result = f"失败: {e}"

            plan.phases_completed.add(3)

        # ── Phase 4: 威胁情报 ──────────────────────────
        if 4 in phases:
            self._notify(plan_id, "Phase 4/5: 威胁情报 — 查询 CVE/ExploitDB")
            if not plan.services:
                plan.vuln_intel.append(
                    {
                        "source": "目标搜索",
                        "query": plan.target,
                    }
                )
                try:
                    result = await self.tool_executor("security_vuln_lookup", {"keyword": plan.target})
                    plan.vuln_intel[-1]["result"] = str(result)[:2000]
                except Exception as __e:
                    logger.debug(f"[orchestrator] Phase4漏洞查询失败: {__e}")

            plan.phases_completed.add(4)

        # ── Phase 5: 报告 ──────────────────────────────
        if 5 in phases:
            self._notify(plan_id, "Phase 5/5: 报告 — 生成综合报告")
            plan.phases_completed.add(5)

        plan.status = TaskStatus.COMPLETED
        elapsed = (datetime.now() - start_time).total_seconds()

        report = self.generate_report(plan_id)
        logger.info(f"扫描完成: {plan.target} ({plan.strategy}) — {elapsed:.1f}s")

        return {
            "plan_id": plan_id,
            "target": plan.target,
            "strategy": plan.strategy,
            "phases_completed": sorted(plan.phases_completed),
            "services_found": len(plan.services),
            "tool_recommendations": len(plan.tool_recommendations),
            "vuln_intel_items": len(plan.vuln_intel),
            "elapsed_seconds": elapsed,
            "tasks": [{"name": t.name, "tool": t.tool, "status": t.status.name, "phase": t.phase} for t in plan.tasks],
            "report": report,
        }

    def _extract_services(self, text: str) -> List[ServiceInfo]:
        """从扫描结果中提取服务名称和版本（模式从 security_net.yaml 加载）"""
        services: List[ServiceInfo] = []
        seen: Set[str] = set()

        patterns = self.SERVICE_PATTERNS  # loaded from config
        for entry in patterns:
            regex = entry.get("regex", "")
            name = entry.get("service", "")
            product = entry.get("product", "")
            if not regex or not name:
                continue
            try:
                matches = re.findall(regex, text, re.IGNORECASE)
            except re.error:
                continue
            for match in matches:
                key = f"{name}:{match}"
                if key not in seen:
                    seen.add(key)
                    version = match.replace(name, "").strip(" /_-")
                    services.append(ServiceInfo(name=name, version=version, product=product, raw=match))

        # 额外从 nmap 结果中解析
        for line in text.split("\n"):
            # nmap service line: "22/tcp open ssh OpenSSH 8.9p1"
            port_match = re.match(r"(\d+)/(\w+)\s+(\w+)\s+(\S.*)", line.strip())
            if port_match:
                port, proto, state, service_line = port_match.groups()
                if state == "open":
                    services.append(
                        ServiceInfo(
                            name=service_line.split()[0] if service_line else "unknown",
                            port=int(port),
                            proto=proto,
                            raw=service_line,
                        )
                    )

        return services

    def generate_report(self, plan_id: str) -> str:
        """生成综合安全评估报告"""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return f"计划不存在: {plan_id}"

        strat = self.STRATEGIES[plan.strategy]
        lines = [
            f"# 智能安全评估报告",
            "",
            f"**目标**: `{plan.target}`",
            f"**策略**: {strat['name']} ({plan.strategy})",
            f"**评估时间**: {plan.created_at}",
            f"**阶段完成**: {sorted(plan.phases_completed)}/5",
            "",
            "---",
            "",
            "## Phase 1 — 侦察结果",
            "",
        ]

        for t in plan.tasks:
            if t.phase == 1:
                icon = "✓" if t.status == TaskStatus.COMPLETED else "✗"
                lines.append(f"### {icon} {t.name}")
                if t.result:
                    lines.append(t.result[:2000])
                lines.append("")

        if plan.services:
            lines.append("## Phase 2 — 识别到的服务")
            lines.append("")
            lines.append("| 服务 | 版本 | 描述 |")
            lines.append("|------|------|------|")
            for svc in plan.services[:20]:
                lines.append(f"| {svc.name} | {svc.version or '-'} | {svc.product or '-'} |")
            lines.append("")

        if plan.tool_recommendations:
            lines.append("## 推荐工具")
            lines.append("")
            for rec in plan.tool_recommendations[:10]:
                svc = rec.get("service", "未知")
                lines.append(f"### 针对 {svc}")
                lines.append(rec.get("recommendation", "")[:1500])
                lines.append("")

        for t in plan.tasks:
            if t.phase == 3:
                icon = "✓" if t.status == TaskStatus.COMPLETED else "✗"
                lines.append(f"## Phase 3 — {icon} {t.name}")
                if t.result:
                    lines.append(t.result[:2000])
                lines.append("")

        if plan.vuln_intel:
            lines.append("## Phase 4 — 威胁情报")
            lines.append("")
            for rec in plan.vuln_intel[:10]:
                lines.append(f"### [{rec.get('source', '')}] {rec.get('query', '')}")
                lines.append(rec.get("result", "")[:2000])
                lines.append("")

        lines.append("---")
        lines.append(f"*报告由 {strat['name']} 策略自动生成 — 弥娅 SecurityNet 智能编排引擎*")
        return "\n".join(lines)

    def get_strategies(self) -> Dict[str, Dict[str, Any]]:
        return {
            key: {
                "name": val["name"],
                "description": val["description"],
                "phases": val["phases"],
            }
            for key, val in self.STRATEGIES.items()
        }

    def _notify(self, plan_id: str, message: str):
        if self.progress_callback:
            self.progress_callback(plan_id, message)

    def cleanup_old_plans(self, max_age_hours: int = 24):
        now = datetime.now()
        to_remove = []
        for pid, plan in self.active_plans.items():
            try:
                created = datetime.fromisoformat(plan.created_at)
                if (now - created).total_seconds() > max_age_hours * 3600:
                    to_remove.append(pid)
            except Exception:
                to_remove.append(pid)
        for pid in to_remove:
            del self.active_plans[pid]
        if to_remove:
            logger.info(f"清理 {len(to_remove)} 个过期计划")


# ─── 兼容旧版 SecurityOrchestrator ────────────────────
_legacy: Optional["SecurityOrchestrator"] = None


class SecurityOrchestrator:
    """旧版编排器兼容层，内部委托给 IntelligentOrchestrator"""

    def __init__(self):
        self._engine = IntelligentOrchestrator()

    def __getattr__(self, name):
        return getattr(self._engine, name)


def get_security_orchestrator():
    global _legacy
    if _legacy is None:
        _legacy = SecurityOrchestrator()
    return _legacy
