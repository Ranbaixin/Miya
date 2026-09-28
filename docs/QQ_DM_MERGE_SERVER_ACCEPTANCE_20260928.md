# QQ 私聊输入合并：服务器验收记录

验收时间：2026-09-28 16:10–16:15（Asia/Shanghai）。

结论：**验收不通过**。部署与基础服务正常，已有专项测试通过，但补充边界测试复现了五个问题，另一个生成阶段记忆写入问题通过隔离执行服务器代码块确认。

## 环境与部署核对

- 直接通过 Workbench 在服务器 `/opt/miya` 检查，使用服务账号 `miya` 和服务实际 `.venv/bin/python`。
- `miya-daemon.service` 为 active/running，PID 223908，启动于 15:34:56；验收后 PID 不变。
- 实际健康端点 `/api/v1/health` HTTP 200，status=ok，AI 未降级，平台 1/1 在线；`/health` 返回 404 是地址错误。
- NapCat 容器运行，服务启动日志确认反向 WebSocket 已连接。
- 六个核心文件 SHA-256 与本地一致，合并器和平台文件修改时间早于服务启动时间。
- 本次部署备份目录 `/opt/miya-backups/20260928T073024Z` 存在；本次未检验其恢复能力。
- doctor：8 PASS、2 WARN、0 FAIL。WARN 为可选 TTS 配置缺失、PC Timer 隧道连接拒绝。
- doctor 的运行日志扫描为 0 行，不能用该项证明日志无错误；另以 root 读取 journal 检查启动与验收时间窗。

## 服务器上的现有测试

在独立临时目录安装 pytest 与 pytest-asyncio，未向服务虚拟环境安装依赖。

执行环境：Python 3.11.16、pytest 9.1.1、pytest-asyncio 1.4.0。

```sh
cd /opt/miya
runuser -u miya -- env \
  PYTHONPATH=/tmp/miya-accept-20260928T0812/deps \
  PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/unit/platform/test_dm_merger.py \
  tests/unit/platform/test_message_dispatch.py \
  tests/unit/platform/test_send_message_contract.py \
  tests/unit/platform/test_dm_route_branch.py \
  tests/unit/hub/test_decision_hub_respond_gate.py \
  tests/unit/webnet/test_tool_turn_gate.py
```

结果：**48 passed in 2.40s**。这些测试证明常规时序、路由分支和部分副作用闸门成立，但未覆盖以下缺陷。

## 未通过项与复现证据

所有补测都在服务器独立 Python 进程执行，使用部署代码与受控回调；不调用真实模型，不发送 QQ 消息，不写真实记忆。

### 1. P1：最新轮次失败后循环重试并重复提示

- 位置：`core/unified_platform_impl/dm_merger.py:212–221`。
- 复现：单条输入，生成回调每次等待 5ms 后抛出模型超时；45ms 后检查调用与发送计数。
- 实测：模型回调 9 次，失败提示 8 次；预期两者各一次。
- 原因：异常分支不清除本轮 pending，也不提交失败轮次，continue 后立即处理同一批输入。
- 改进：最新失败轮次也要原子确认版本并结束其输入批次；保留后来到达的输入，防止失败提示与新消息竞争。

### 2. P1：输入按入账完成顺序排列，可能颠倒

- 位置：`core/unified_platform_impl/dm_merger.py:143–179`。
- 复现：先收到 A，但暂停 A 的入账；随后收到 B 并完成入账，再释放 A。
- 实测：生成批次为 `[B, A]`；预期 `[A, B]`。
- 原因：收到时只增加版本，pending 在异步入账完成后 append。
- 改进：收到时分配顺序号/占位项，入账完成后补齐该项；原始输入与记忆均保留接收顺序，并覆盖图片等慢输入。

### 3. P1：草稿及已完成工具信息未交给下一轮

- 位置：`core/unified_platform_impl/dm_merger.py:226–227`、`onebot_platform.py:1026–1046`。
- 复现：状态中放入唯一草稿标记和已执行工具标记，调用真实 `_dm_generate`，在决策中心入口捕获上下文。
- 实测：模型输入只有合并的 A/B，没有两个标记。
- 原因：draft/draft_tools 仅保存用于观察；后续生成不读取，工具记录也只有名称、没有参数及结果。
- 改进：按已确认方案传入明确标记为未发送的回答草稿，以及已完成操作的参数、结果和状态，避免重复执行。实施计划中的“已知边界”不等于用户接受了该偏离。

### 4. P2：断线发送被报告为成功，并产生虚假助手事件

- 位置：`onebot_platform.py:1048–1057`、`1059–1097`。
- 复现：平台 `_connected=False`、`_ws=None`，调用真实 `_dm_send`，捕获桌面事件。
- 实测：返回 True，发布 1 个助手事件；预期 False、0 个已发送事件。
- 原因：底层发送断线时直接返回，分条异常也仅 break；上层忽略结果并无条件发布事件、返回 True。
- 改进：返回实际发送结果及已发送片段，处理断线和中途失败；未发送内容不能显示为已发出。

### 5. P1：权限检查等待期间失效的轮次仍启动写操作

- 位置：`webnet/ToolNet/registry.py:169–225`。
- 复现：第一次轮次检查时有效，在异步权限检查中使轮次失效，再允许权限检查通过。
- 实测：模拟写工具启动 1 次并返回 ok；预期不启动。
- 原因：闸门在 await 权限检查之前，工具实际启动前未重新确认。
- 改进：在执行工具前再次检查轮次；对其他执行入口和工具内部后续发送/写入阶段检查同样的问题。

### 6. P1：生成阶段仍能把未发送草稿写进 LifeBook

- 位置：`hub/decision_hub.py:2561` 起的 LifeBook 记录块；外层提交闸门在 `_respond_phase:1193`，位于整个生成调用之后。
- 复现范围：从服务器源码用 AST 提取生成函数中的原始 LifeBook try 块，隔离执行，替换存储对象以捕获参数；设置当前轮次为已被替代。
- 实测：捕获一次 `record_interaction`，`lover_response=UNSENT_DRAFT_MARKER`。
- 这是原代码块的执行证据，未执行完整真实模型链，也未写真实日记。
- 原因：生成函数内部已执行记忆写入，外层闸门无法阻止之前完成的副作用；现有闸门测试把生成函数替换为桩，因此漏检。
- 改进：把正式回答对应的日记、情绪/认知记忆等写入纳入提交阶段；明确区分内部分析与已发送对话，完整审查生成函数的存储路径。

## 验收清单本身的修正

`QQ_DM_MERGE_ACCEPTANCE.md` 的 T2a 将“5 秒内三条输入”限定为只调用一次模型、只收到一条 QQ 消息，与已确认方案不符。第一条立即思考，期间有输入时允许重算；一轮回答也允许分条。应检查最终回答轮数和覆盖内容，分别记录模型调用数与 QQ 分条数。

## 验收边界与下一步

- 未修改生产代码、配置，未重启服务，未发送真实 QQ 测试消息。
- 真实 QQ→NapCat→模型→QQ 的端到端交互尚未验收，服务在线不能代替该验证。
- 先修复上述阻断项并增加能复现它们的回归测试，再部署复验；最后用用户本人发送的连续消息完成真实 QQ 链路验收。
- 临时测试依赖位于 `/tmp/miya-accept-20260928T0812`，与运行服务的虚拟环境分离。
