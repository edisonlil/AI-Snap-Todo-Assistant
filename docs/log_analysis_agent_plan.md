# `/分析日志` 异步日志排查 Agent 方案

## 1. 目标

在现有待办详情页时间线输入框中支持 `/分析日志` 命令，使用户可以：

- 在时间线中输入 `/分析日志 tradId=... request_id=...`
- 拖拽或粘贴日志/压缩包/截图作为本次排查材料
- 点击“添加”后立即生成一条日志分析任务记录
- 后台异步执行排查，不阻塞主界面
- 完成后再生成一条系统分析结果时间线

这不是“全文摘要”，而是一个：

- 参数化命令
- 异步任务
- 上下文感知的日志分析 Agent

## 2. 当前设计原则

- 时间线文本只是展示层，不是真相源
- 真相源统一落在结构化 JSON：
  - `parsed_focus_json`
  - `investigation_context_json`
  - `evidence_bundle_json`
  - `result_payload_json`
- orchestrator 只依赖 `LogAnalysisAgent` 接口
- 输出采用 producer / consumer 分层
- 附件处理采用 handler / registry 机制
- 模型绑定支持 `log_analysis -> fallback analysis`

## 3. 模块边界

### 3.1 命令解析

文件：

- `src/aica/log_analysis_commands.py`

职责：

- 判断是否为 `/分析日志`
- 提取 `trad_id`
- 提取 `request_id`
- 提取自由描述 `focus_terms`
- 生成结构化 `LogAnalysisCommand`

### 3.2 排查上下文压缩

文件：

- `src/aica/log_analysis_context.py`

职责：

- 收集最近 N 条排查相关时间线
- 压缩为结构化 `InvestigationContextSummary`
- 避免把时间线全文直接喂给模型

### 3.3 附件处理注册表

文件：

- `src/aica/log_analysis_attachments.py`

职责：

- `AttachmentHandlerRegistry`
- `ZipAttachmentHandler`
- `TextLogAttachmentHandler`
- `ImageAttachmentHandler`

输出：

- `EvidenceBundle`

### 3.4 Agent 接口与默认实现

文件：

- `src/aica/log_analysis_models.py`
- `src/aica/log_analysis_agent.py`

职责：

- `LogAnalysisAgent` 是明确接口
- `DefaultLogAnalysisAgent` 是首版实现
- 输入是结构化 request
- 输出是结构化 produced result

### 3.5 Producer / Consumer

文件：

- `src/aica/log_analysis_consumers.py`

职责：

- producer 产出 `result_payload_json`
- consumer 消费结构化结果
- 首版 consumer：`TimelineLogAnalysisPresenter`

预留 consumer：

- 阶段总结
- 发研发摘要
- 发客户摘要
- 经验回流摘要
- 相似问题检索摘要

### 3.6 Orchestrator

文件：

- `src/aica/log_analysis_orchestrator.py`
- `src/aica/log_analysis_worker.py`

职责：

- 读取任务
- 更新状态
- 构建上下文
- 收集附件证据
- 调用 agent
- 保存结构化结果
- 调用 consumer 输出 timeline

### 3.7 存储

文件：

- `src/aica/storage/sqlite/schema.sql`
- `src/aica/storage/sqlite/repositories.py`
- `src/aica/log_analysis_store.py`

表：

- `log_analysis_tasks`

核心字段：

- `status`
- `raw_command`
- `parsed_focus_json`
- `attachment_snapshot_json`
- `investigation_context_json`
- `evidence_bundle_json`
- `result_payload_json`
- `result_summary`
- `error_message`
- `model_binding_used`

### 3.8 UI 接入

文件：

- `src/aica/todo_detail_panel.py`
- `src/aica/qml/TodoDetailPanel.qml`
- `src/aica/main.py`

职责：

- 时间线斜杠命令入口
- 点击后立即落任务记录
- 显示任务状态
- 启动后台 worker
- 刷新详情页状态

## 4. 执行链路

1. 用户输入 `/分析日志 ...`
2. 用户拖入 zip / log / 图片
3. 点击“添加”
4. 立即落一条“日志分析任务”时间线
5. 创建 `log_analysis_tasks` 任务，状态 `queued`
6. 主线程启动 `LogAnalysisWorker`
7. worker 将任务切到 `running`
8. orchestrator 构建：
   - `parsed_command`
   - `investigation_context`
   - `evidence_bundle`
9. agent 产出：
   - `result_payload_json`
   - `result_summary`
10. timeline presenter 把结构化结果转成系统时间线
11. 任务状态更新为 `completed`
12. 若异常则标记 `failed`

## 5. 当前已知交互问题

你反馈的现象是：

- 用斜杠命令做日志分析
- 拖拽日志后点击“添加”
- UI 看起来像“问题反馈”
- 不清楚是否真的在分析

这说明当前实现虽然已经接了 `/分析日志` 的后台链路，但前端交互还不够清晰，主要问题可能有这几类：

### 5.1 输入类型标签默认仍是“问题反馈”

当前 composer 的类型标签仍沿用原有 follow-up 视觉，导致用户误以为提交的是普通反馈。

### 5.2 命令菜单选择态不够显式

即使输入 `/分析日志`，也可能没有足够强的 UI 提示让用户知道当前模式已经切换到日志分析任务。

### 5.3 状态回显不够强

虽然时间线卡片已经有 `taskStatusLabel`，但在交互上还不够醒目，用户仍然不知道是否正在分析。

### 5.4 “添加”按钮语义不清

对普通跟进和异步分析任务使用同一个按钮文案，用户难以判断点击后是“记一条反馈”还是“提交一个后台任务”。

## 6. 下一步建议修正

建议继续做以下 UI 修正：

### 6.1 composer 明确区分日志分析模式

- 当识别到 `/分析日志` 时
- 输入框上方或类型标签显示“日志分析任务”
- 颜色与普通问题反馈区分开

### 6.2 按钮文案动态切换

- 普通模式：`添加`
- `/分析日志` 模式：`提交分析`

### 6.3 提交后即时 toast

- `已提交日志分析任务，后台排查中`

### 6.4 时间线卡片加强状态展示

- `排队中`
- `分析中`
- `已完成`
- `失败`

并在命令卡片中固定显示：

- 原始命令
- 分析重点
- 当前状态

### 6.5 分析结果卡片与普通反馈卡片做视觉区分

- `日志分析结果` 使用系统风格头部
- 不再与普通“问题反馈”混淆

## 7. 配置策略

模型绑定：

- 配置层支持 `log_analysis`
- 若未配置则 fallback 到 `analysis`

当前代码路径：

- `src/aica/config.py`
- `src/aica/llm/service.py`

## 8. 当前相关文件

- `src/aica/log_analysis_models.py`
- `src/aica/log_analysis_commands.py`
- `src/aica/log_analysis_context.py`
- `src/aica/log_analysis_attachments.py`
- `src/aica/log_analysis_agent.py`
- `src/aica/log_analysis_consumers.py`
- `src/aica/log_analysis_orchestrator.py`
- `src/aica/log_analysis_worker.py`
- `src/aica/log_analysis_store.py`
- `src/aica/todo_detail_panel.py`
- `src/aica/qml/TodoDetailPanel.qml`
- `src/aica/main.py`
- `src/aica/storage/sqlite/schema.sql`
- `src/aica/storage/sqlite/repositories.py`
- `tests/test_log_analysis.py`

## 9. 当前验证方式

已执行：

```powershell
python -m compileall src\aica run_aica.py
pytest tests\test_log_analysis.py tests\test_todo_detail_panel.py -q --basetemp=.codex_tmp\pytest
```

结果：

- `8 passed`

说明：

- 核心命令解析
- 模型 fallback
- handler registry 分发
- bridge 命令提交流
- 时间线相关回归

均已通过基本验证。
