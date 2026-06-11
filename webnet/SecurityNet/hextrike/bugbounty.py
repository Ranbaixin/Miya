"""Bug Bounty 目标管理与文件上传测试框架"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BugBountyTarget:
    """Bug Bounty 目标信息"""

    url: str = ""
    name: str = ""
    scope: list[str] = field(default_factory=list)
    platform: str = ""
    rewards: str = ""
    status: str = "active"


class BugBountyWorkflowManager:
    """Bug Bounty 工作流管理器"""

    def __init__(self):
        self.targets: dict[str, BugBountyTarget] = {}
        self.active_targets: list[str] = []

    def add_target(self, target: BugBountyTarget):
        self.targets[target.url] = target
        if target.status == "active":
            self.active_targets.append(target.url)

    def remove_target(self, url: str):
        self.targets.pop(url, None)
        if url in self.active_targets:
            self.active_targets.remove(url)

    def get_active_targets(self) -> list[BugBountyTarget]:
        return [self.targets[u] for u in self.active_targets if u in self.targets]

    def list_targets(self) -> list[BugBountyTarget]:
        return list(self.targets.values())


class FileUploadTestingFramework:
    """文件上传漏洞测试框架"""

    def __init__(self):
        self.test_cases: list[dict] = []
        self.results: list[dict] = []

    def add_test_case(self, name: str, payload: bytes, extension: str, content_type: str):
        self.test_cases.append(
            {
                "name": name,
                "payload": payload,
                "extension": extension,
                "content_type": content_type,
            }
        )

    def get_test_cases(self) -> list[dict]:
        return self.test_cases

    def add_result(self, test_name: str, success: bool, details: str = ""):
        self.results.append(
            {
                "test_name": test_name,
                "success": success,
                "details": details,
            }
        )

    def get_results(self) -> list[dict]:
        return self.results
