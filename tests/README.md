# tests/ — 测试套件

```
tests/
├── conftest.py        # 共享 fixture（mock_ai_client / mock_llm_func / temp_env_file 等；无全局 AI_PROVIDER 注入）
├── unit/              # 默认回归基线（pyproject testpaths）——提交前必须全绿
│   ├── memory/        #   记忆：并发/双后端/健康/迁移/稳定画像 (45)
│   ├── platform/      #   平台：消息分发/工具包/发送契约 (27)
│   ├── permission/    #   权限：scrypt+JWT 往返、fail-closed 回归 (10)
│   ├── utils/         #   token 预算公式 (13)
│   ├── hub/ config/ core/  # 各域单测
│   └── webapi/        #   Web API 安全回归（2026-09 新增，12 项）
└── core/              # 遗留顶层测试（config 热重载 16 项）；不被默认收集，需显式 pytest tests/core/
```

回归入口：`uv run --group dev python -X utf8 -m pytest tests/unit/ -q -p no:cacheprovider`。
具体通过数以最近一次本地或 CI 运行结果为准。

## 测试质量约定（新增测试必读）

- **断言真实行为**，mock 只作用于协作者与外部边界（现有测试即范本：真实 scrypt/JWT 往返、
  真实 `object.__new__` 绕过网络初始化等）；禁止 mock 被测对象本身自证。
- 禁止 `pytest.skip`/空断言凑数。
- `tests/unit/webapi/test_token_gate.py` 与 `test_webapi_security.py` 是 P0 安全修复的回归
  （鉴权网关 loopback/远程、RCE 封堵、`.env` 读取封堵、tools/list 假成功）——**改鉴权、
  工具路由、config/file 前先跑这两个文件**。

## 安全测试的轻量 WebAPI 构造

`core.web_api.WebAPI(None, None)` 可无后端构造（真实加载全部路由），配合
`fastapi.testclient.TestClient` 直接打路由。注意：构造时会真实初始化 MiyaAPI 与 ToolNet
注册表（加载真实工具），因此 `/api/tools/list` 断言 `total>0`。

## 运行子集

```bash
uv run python -X utf8 -m pytest tests/unit/webapi -q      # 安全回归
uv run python -X utf8 -m pytest tests/unit/memory -q      # 记忆域
uv run python -X utf8 -m pytest tests/core -q             # 遗留热重载测试
```
