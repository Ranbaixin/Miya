"""
人格熵监控（防异化）
监控系统状态，防止人格漂移和异化

2026-09：numpy → math 纯实现。core/__init__ 顶层导入本模块，
原 numpy 依赖使启动即常驻 +20~40MB；熵计算为标量运算，math 足够。
"""

import math
from datetime import datetime
from typing import Dict


class Entropy:
    """熵监控系统"""

    def __init__(self):
        self.entropy_history = []
        self.threshold = 0.5  # 熵值阈值
        self.critical_threshold = 0.7  # 临界阈值

        # 稳定性指标
        self.stability_metrics = {"personality_drift": 0.0, "emotional_variance": 0.0, "behavioral_consistency": 1.0}

    def calculate_entropy(self, state: Dict) -> float:
        """计算当前系统熵值"""
        # 基于人格向量计算熵（香农熵归一化，与原 numpy 实现数值等价）
        vectors = state.get("vectors", {})
        values = list(vectors.values())
        if not values:
            return 0.0

        entropy = -sum(v * math.log(v + 1e-10) for v in values)
        entropy = entropy / math.log(len(values))  # 归一化

        return round(entropy, 3)

    def check_anomaly(self, current_entropy: float) -> Dict:
        """检测异常"""
        self.entropy_history.append({"timestamp": datetime.now(), "entropy": current_entropy})

        # 只保留最近100条记录
        if len(self.entropy_history) > 100:
            self.entropy_history = self.entropy_history[-100:]

        status = "normal"
        alerts = []

        if current_entropy > self.critical_threshold:
            status = "critical"
            alerts.append("人格异化风险极高，需要立即干预")
        elif current_entropy > self.threshold:
            status = "warning"
            alerts.append("人格熵值偏高，建议进行人格校准")

        return {"status": status, "entropy": current_entropy, "alerts": alerts, "trend": self._calculate_trend()}

    def _calculate_trend(self) -> str:
        """计算熵值趋势"""
        if len(self.entropy_history) < 10:
            return "insufficient_data"

        recent = [h["entropy"] for h in self.entropy_history[-10:]]
        early = [h["entropy"] for h in self.entropy_history[-20:-10]]

        recent_avg = sum(recent) / len(recent)
        early_avg = sum(early) / len(early)

        if recent_avg > early_avg * 1.1:
            return "increasing"
        elif recent_avg < early_avg * 0.9:
            return "decreasing"
        else:
            return "stable"

    def update_stability_metrics(self, metrics: Dict) -> None:
        """更新稳定性指标"""
        for key, value in metrics.items():
            if key in self.stability_metrics:
                self.stability_metrics[key] = value

    def get_health_report(self) -> Dict:
        """获取健康报告"""
        if not self.entropy_history:
            return {"status": "no_data"}

        current = self.entropy_history[-1]
        return {
            "current_entropy": current["entropy"],
            "stability": self.stability_metrics,
            "threshold": self.threshold,
            "last_check": current["timestamp"].isoformat(),
        }
