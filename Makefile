# ========================================
#  Miya CI/CD 本地检查
#  模拟 GitHub Actions 的 CI 流程
#  用法: make ci
# ========================================

.PHONY: ci quality test security format help smoke smoke-fast graph memory-check

# 默认：运行所有 CI 检查
ci: quality test security
	@echo ""
	@echo "===== CI 检查全部完成 ====="

# 代码质量检查（ruff + black）
quality:
	@echo "[1/3] ruff check..."
	ruff check .
	@echo "[2/3] black --check..."
	black --check core/ hub/ run/

# 安全审计
security:
	@echo "[3/3] bandit security audit..."
	bandit -r core/ hub/ run/ -ll -f custom || true

# 单元测试 (pytest) — 与 CI 一致，只跑 tests/unit/（可信回归基线）
test:
	pytest tests/unit/ -q -p no:cacheprovider

# 死代码静态检查
graph:
	python scripts/import_graph.py --check

# 记忆健康检查（索引覆盖度 + 双库一致性）
memory-check:
	python scripts/memory_health_check.py

# 冒烟测试 (全量, ~3-5 分钟)
smoke:
	python scripts/smoke_test.py

# 冒烟测试 (快速, ~40 秒)
smoke-fast:
	python scripts/smoke_test.py --fast

# 自动修复格式问题
fix:
	ruff check --fix .
	ruff format .
	black core/ hub/ run/

# 帮助
help:
	@echo "make ci       - 运行完整 CI 检查"
	@echo "make quality  - 代码质量（ruff + black）"
	@echo "make security - 安全审计（bandit）"
	@echo "make test     - 单元测试"
	@echo "make fix      - 自动修复格式问题"
