# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Chattodo**（仓库描述名 `AI Snap Todo Assistant`，包名仍为 `aica`）是面向 Windows 与 macOS 的 AI 工单待办助手。核心工作流是：全局热键截图 → 多模态 LLM 结构化提取工单字段 → 创建/追加待办 → 持续维护时间线 → 浮动待办栏 + 详情侧栏管理。

技术栈：Python 3.10+、PyQt6、QML、SQLite、PyInstaller 打包。

## 运行与测试

```bash
# 准备虚拟环境（项目根目录下）
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt   # 包含 pytest + hypothesis
python -m pip install -r requirements-build.txt # PyInstaller

# 运行应用
python run_aica.py

# 跑单个测试或子集
.venv/bin/python -m pytest tests/test_control_panel.py -x
.venv/bin/python -m pytest tests/test_*.py -k "drag" -x

# 推荐回归套件（README/AGENTS.md 中已验证的快子集）
.venv/bin/python -m pytest tests/test_environment_access.py tests/test_log_analysis.py tests/test_context_summary.py tests/test_todo_detail_panel.py -q

# 完整测试
.venv/bin/python -m pytest tests -q

# 快速语法/导入冒烟
python -m compileall src/aica run_aica.py
```

## 打包

```bash
# Windows onedir
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# Windows onefile
powershell -ExecutionPolicy Bypass -File scripts/build_onefile.ps1

# macOS .app（支持 --target-arch arm64/x86_64/universal2）
./scripts/build_macos_app.sh
./scripts/build_macos_app.sh --target-arch arm64
```

PyInstaller spec 文件在仓库根目录：`aica.spec`（Windows onedir）、`aica_onefile.spec`（Windows onefile）、`aica_macos.spec`（macOS，支持 `TARGET_ARCH`）。spec 中显式打包了 QML、`aica/resources/` 和 `src/aica/storage/sqlite/schema.sql` —— 改动这些位置时记得同步更新 `datas` 列表。

## 架构

### 入口与主流程

- `run_aica.py` 把 `src/` 加入 `sys.path` 后调用 `aica.main.main()`。
- `src/aica/main.py` 是 PyQt6 应用入口，串联单实例保护（`single_instance.py`）、托盘图标、本地命令通道（`app_commands.py`，端口 48173）、热键、捕获流程、控制面板等所有顶层组件。

### 主要子系统

- **LLM 抽象层**（`src/aica/llm/`）：`service.py`（`LLMService`）+ `registry.py`（供应商注册表）+ `base.py`（接口）+ `types.py`。首批支持 `openai_compatible` 与 `gemini` 两种 `kind`，运行时由 `config.py` 中 `task_model_bindings` 决定截图分析、方案导出、上下文摘要、日志分析各自走哪个 provider/model。
- **截图与覆盖层**（`src/aica/overlay.py`、`capture_ui_flow.py`、`capture_session.py`）：无边框透明覆盖层，框选 + 标注，结果送入 `worker.py` 启动分析。
- **Worker 与分析流**（`src/aica/worker.py`、`analysis/flow.py`、`analysis/strategy.py`、`analysis/intent.py`、`analysis/rules.py`、`analysis/metrics.py`）：后台线程跑分析，规则文件 `analysis_rules.json` 可热加载，`prompt_debug/` 目录保存 Prompt 快照用于调试。
- **待办与时间线**（`src/aica/todo/`）：`store.py`（SQLite CRUD）、`controller.py`（业务编排）、`events.py`（`TodoEventPublisher` 事件总线）、`models.py`（`TodoItem` / `TodoStatus`）、`panel.py` + `detail_panel.py`（QML 桥接）、`conclusion_timeline.py`、`detail_save_policy.py`、`work_order_sync.py`、`assist_analysis.py`。
- **存储层**（`src/aica/storage/`）：`contracts.py` 定义领域对象，`adapters.py` 转换层，`sqlite/` 是 SQLite 实现（`schema.sql`、`repositories.py`、`environment_repositories.py`、`error_code_repository.py`）。`aica/paths.py` 统一收口 `~/.aica/` 下所有路径（config、todos、feedback、logs、prompt_debug、integrations 等）。
- **控制面板**（`src/aica/control_panel.py` + `src/aica/qml/ControlPanel.qml`）：`_ControlPanelBridge` 通过 pyqtSignal/Slot 暴露给 QML。`_SECTION_GROUPS`（位于 `control_panel.py` 第 448-501 行附近）定义左侧导航菜单分组与顺序。QML 通过 `controlPanelBridge.sectionGroups` 渲染菜单，通过 `currentSection` 切换右侧内容。窗口是无边框的，macOS 自绘红绿灯，拖拽由 `startWindowDrag` → `dragRequested` → `startSystemMove` 链实现；缩放由 `startWindowResize` → `startSystemResize` 处理。
- **结果与弹窗**（`result_flow.py` + `result_dialog.py`、`annotation_dialog.py`）：截图分析后弹出确认框，结果写入待办。
- **主题**（`theme.py` + `theme_controller.py`）：运行时按 token 注入 QML 上下文，控制面板里可改 `accent_color`/`font_family`/`component_style`/`density`/`radius_scale`/`font_size_px` 等并立即刷新已开窗口。
- **服务端集成**（`server_api.py` + `project_management.py` + `ticket_enrichment.py`）：可选的 Chattodo 服务端连接，启用后做项目同步、工单同步、ACH 状态校准、远程附件下载、结论回写等。`server.enabled/base_url/api_key/timeout_seconds` 写在 `config.json`。
- **外部脚本集成**（`app_commands.py` + 待办事件总线 + `scripts/`）：`TodoEventPublisher` 发布待办生命周期事件给包外脚本处理器（`.py`/`.pyw`/`.ps1`/`.bat`/`.cmd`/`.exe`/`.sh`，按平台支持子集），配置在 `~/.aica/integrations.json`，绑定关系在 `~/.aica/todo_bindings.json`。平台差异在 `runtime.py` 抽象。
- **平台抽象**（`src/aica/runtime.py`）：`RUNTIME_CAPABILITIES` 提供 `is_windows/is_macos/ui_font/widget_font_css/monospace_font_css/integration_script_filter/control_panel_window_flags` 等。所有新增的平台相关代码应优先走这里。
- **macOS Dock / Windows 任务栏**（`windows_taskbar.py` + `app_commands.py`）：任务栏/Dock 菜单操作通过本地 socket（端口 48173）转发到运行中的单实例。
- **通知中心**（`app_notifications.py` + `AppNotificationCenter.qml` + `AppNotificationWindow.qml`）：替换旧的 QMessageBox，统一错误/成功/警告提示。

### QML 桥接约定

每个主窗口都是 Python `QWidget`（或 `QQuickWidget`）容器 + `QQuickWidget` 加载一个根 QML。Python 端用 `pyqtSlot/pyqtSignal/pyqtProperty` 暴露状态和行为给 QML，QML 端通过 `xxxBridge` 上下文属性访问。修改时**双向都要看**——QML 加的字段要在 Python 桥的 `dataChanged` 信号里同步。

各 QML 文件分工：
- `ControlPanel.qml` + 多个 `ControlPanel*` 组件：控制面板
- `TodoPanel.qml` / `TodoDetailPanel.qml`：浮动待办栏 + 详情
- `ResultDialog.qml` / `StageSummaryWindow.qml` / `AssistTroubleshootingWindow.qml` / `TimelineDetailWindow.qml`：结果与辅助窗口
- `PageRuntime.qml` / `DetailRuntime.qml`：占位 + 路由
- `EnvironmentAccessPopover.qml` / `EnvironmentManagerSection.qml` / `GlobalEnvironmentsSection.qml` / `ProjectEnvironmentsSection.qml`：环境管理
- `ProjectsSection.qml` / `TicketsSection.qml`：项目/工单列表
- `TimelineCardMapper.js` + `BaseTimelineCard.qml` + `DefaultTimelineCard.qml` + `LogAnalysisTaskCard.qml` + `LogAnalysisResultCard.qml`：时间线卡片体系

### 跨模块的"非显然"约定

- **品牌名 vs 包名**：产品名是 `Chattodo`（UI、文案、spec 产物），但 `aica` 这个包名、配置目录 `~/.aica/`、spec 文件名、PyInstaller 内部名都保留 —— 见 `AGENTS.md` "Product Naming" 节。改 UI 文案用 `Chattodo`，改工程内部标识需要单独评估。
- **运行配置 schema**：`config.json` 顶层是 `providers + task_model_bindings + hotkeys + server + max_image_bytes + theme`。旧版 `api_key/model/api_base_url` 在加载时会自动迁移，加新字段时记得在 `config.py` 的迁移逻辑里处理向后兼容。
- **本地数据目录**：`aica/paths.py` 是单一来源。新增本地持久化文件请走这里（`app_data_dir()` / `config_file()` / `aica_database_file()` 等），不要直接拼 `~/.aica/...`。
- **菜单顺序**："运行与集成" 分组中各 item 的顺序在 `control_panel.py` 的 `_SECTION_GROUPS` 里直接以 Python 列表顺序定义；QML 端通过 `Repeater { model: controlPanelBridge.sectionGroups }` 渲染，不在 QML 中硬编码。
- **macOS 权限**：首次用全局热键时，macOS 需要在"系统设置 > 隐私与安全性"中授权辅助功能 + 输入监听；授权失败时应用仍启动并保留菜单栏入口，热键重启用需重启。`runtime.py:hotkey_failure_message` 负责生成提示文案。
- **macOS 红绿灯自绘**：`ControlPanel.qml` 里 `MacosTrafficLightButton` 是带圆点 + glyph 的 Rectangle 组件（参考 `b0da185` 提交），实际关窗/最小化/最大化通过 `controlPanelBridge.closePanel/minimizePanel/toggleMaximizedPanel` 触发。
- **macOS 包目标架构**：`aica_macos.spec` 读取环境变量 `TARGET_ARCH`（`arm64` / `x86_64` / `universal2`），`scripts/build_macos_app.sh` 负责传递。云端打包由 `.github/workflows/build-macos-unsigned.yml` 跑矩阵，产物命名统一为 `Chattodo`。

### 测试约定

- 测试文件 `tests/test_<module>.py`，测试函数 `test_<behavior>()`。
- 优先覆盖逻辑层（`src/aica/<module>.py` 的纯函数和编排），不写脆弱的 GUI 自动化。
- 改 capture、prompt、packaging 流程时跑 `tests/test_overlay.py tests/test_compress.py tests/test_prompts.py tests/test_single_instance.py` 这套快回归。
- 控制面板桥接有大量不带 Qt 运行时也能跑的 stub（`control_panel.py` 顶部那段 fallback 类），pytest 不需要 Qt 环境就能跑相关测试。
- 部分 QML 字符串断言类测试（如 `test_page_runtime_qml.py`、`test_business_page_runtime_qml.py`、`test_control_panel.py` 中的可见性断言）会直接 grep 关键字，**改 QML 后跑一遍这些测试**。

### 仓库根文件用途

- `run_aica.py`：开发态入口
- `aica.spec` / `aica_onefile.spec` / `aica_macos.spec`：PyInstaller 打包
- `aica_version_info.txt`：Windows 版本元数据
- `requirements.txt` / `requirements-dev.txt` / `requirements-build.txt`：分档依赖
- `README.md`：用户文档 + Changelog
- `AGENTS.md`：给 AI 代理的工程规范
- `ROADMAP.md` / `TODO_ARCHITECTURE_ROADMAP.md`：产品与技术规划
- `aica-todo-reader/`：用于查询 `aica.db` 的独立 skill 目录（`SKILL.md` + `scripts/query_todos.py` + `references/schema.md`），可作为长期记忆的检索脚本来源
- `docs/`：与外部平台集成的协议文档（`todo-event-integration.md`、`script-integration-guide.md` 等）
- `.github/workflows/`：云端 macOS unsigned 与 Windows exe 打包工作流，仅在 `v*` tag push 或手动触发时跑

### 提交与 PR

- 中文短祈使句 commit（如 `优化反馈面板`、`实现打包`），一 commit 一个主题。
- PR 描述写清改动范围、跑过的测试命令，UI 改动附截图/GIF。
- 改 spec / 图标 / 版本元数据时**显式说明**打包产物影响。
- **不要**把真实 API key 提交进仓库；`config.json` 中默认 `api_key` 留空。
