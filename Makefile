# ========================================
#  Miya CI/CD 本地检查
#  模拟 GitHub Actions 的 CI 流程
#  用法: make ci
# ========================================

.PHONY: ci quality test security format help

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
	bandit -r core/ hub/ run/ -ll -f custom

# 单元测试
test:
	pytest tests/unit/ -v --tb=short

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
