# AI Snap Todo Assistant

面向 Windows 的 AI 工单待办助手。

围绕“截图采集上下文 -> AI 结构化提取 -> 创建/追加待办 -> 在时间线中持续跟进”设计的轻量工作台，适合技术支持、售后、实施、交付等需要高频处理工单上下文的场景。

## 产品定位

AI Snap Todo Assistant 的核心目标是把零散的截图信息沉淀成可持续跟进的待办：

- 用 `Alt+A` 快速截取群聊、报错、工单上下文
- 由 AI 提炼结构化工单字段和本次跟进内容
- 未选中待办时创建新待办
- 已选中待办时追加到已有待办，并对时间线做增量去重
- 在浮动待办栏和详情侧栏中持续查看、编辑和完成任务

## 核心流程

1. 按 `Alt+A` 唤起截图。
2. 在覆盖层中框选区域，并按需进行标注。
3. 支持单张截图直接分析，也支持连续多张截图后统一分析。
4. AI 会输出结构化结果，核心字段包括：
   - `title`
   - `group_name`
   - `environment`
   - `product_line`
   - `ticket_type`
   - `current_summary`
   - `timeline_entry`
5. 结果确认后：
   - 如果当前没有选中待办，则创建新的待办项
   - 如果当前已选中待办，则更新当前摘要并向该待办追加一条新的时间线记录
6. 追加到已有待办时，程序会尽量从累计描述中提取“本次新增跟进”，避免把已有时间线重复写入。
7. 保存后的待办会显示在右上角浮动面板中，可继续跟进、编辑、完成或删除。

## 当前已实现功能

- 全局热键截图：`Alt+A`
- 截图覆盖层支持框选与标注
  - 移动
  - 矩形
  - 箭头
  - 文本
- 连续截图与多图统一分析
- AI 结构化提取工单信息
- AI 二次生成更适合展示与保存的工单标题
- 结果确认对话框
- 待办浮动面板（QML）
  - 展示进行中的待办
  - 选中待办，供后续截图追加
  - 标记完成
  - 展开 / 收起
  - 最小化
  - 拖拽移动与边缘吸附
- 待办详情侧栏（QML）
  - 编辑标题
  - 编辑群聊名称、环境、产品线、工单类型
  - 编辑当前摘要
  - 查看时间线历史
  - 直接编辑时间线文本
  - 完成待办
  - 删除待办
- 工单类型归一化
  - 统一归一为“排查类 / 咨询类 / 操作类”
- 产品线归一化
  - 当前走固定归一逻辑，避免自由输入导致的数据分散
- 本地待办持久化
- 反馈保存
- 基于反馈的后台 prompt 优化
- 单实例运行保护

## 数据模型

### TicketSnapshot

AI 分析和结果确认流程中的核心结构化对象，包含：

- `title`：待办标题
- `fields.group_name`：群聊名称
- `fields.environment`：环境信息
- `fields.product_line`：产品线
- `fields.ticket_type`：工单类型
- `current_summary`：当前问题摘要
- `timeline_entry`：本次新增跟进记录

用途：

- 作为 AI 识别结果的标准承载结构
- 作为结果确认对话框的输入
- 作为创建待办或追加时间线时的标准输入

### TodoItem

待办领域对象，代表一个持续跟进中的工单任务，包含：

- `title`：待办标题
- `summary_fields`：结构化工单字段
- `current_summary`：当前摘要
- `timeline`：时间线历史
- `status`：待办状态
- `created_at / updated_at`：创建与更新时间

### TimelineEvent

待办时间线中的单条事件，关键字段包括：

- `timestamp`：记录时间
- `scenario`：事件来源场景
- `kind`：事件类型
- `content`：时间线正文

当前 UI 已展示 `scenario` 和 `content`，并允许在详情页中直接编辑时间线内容。

## 运行环境

- Windows 10 或更高版本
- Python 3.10+
- 可访问兼容 OpenAI Chat Completions 的视觉模型接口

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

开发与测试依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

打包依赖：

```powershell
python -m pip install -r requirements-build.txt
```

## 配置

运行配置保存在 `~/.aica/config.json`。

示例：

```json
{
  "api_key": "",
  "model": "Qwen/Qwen2.5-VL-72B-Instruct",
  "title_generation_model": "Qwen/Qwen3-8B",
  "plan_export_model": "Qwen/Qwen2.5-VL-72B-Instruct",
  "api_base_url": "https://api.siliconflow.cn/v1/chat/completions",
  "timeout_seconds": 30,
  "max_image_bytes": 4194304
}
```

字段说明：

- `api_key`：模型服务密钥，代码中默认留空，不应提交真实密钥
- `model`：截图识别 / 截图分析使用的模型名称
- `title_generation_model`：标题生成使用的模型名称；旧版 `config.json` 没有这个字段时会自动回退到默认值 `Qwen/Qwen3-8B`
- `plan_export_model`：导出方案使用的模型名称；旧版 `config.json` 没有这个字段时会自动回退到默认值 `Qwen/Qwen2.5-VL-72B-Instruct`
- `api_base_url`：兼容 OpenAI Chat Completions 的接口地址
- `timeout_seconds`：接口请求超时时间
- `max_image_bytes`：图片压缩阈值，默认 `4MB`

补充说明：

- 如果首次运行时未配置 `api_key`，程序会弹窗引导配置
- 当前默认场景只有 `工单待办助手`
- 场景切换入口已预留，但当前并未开放多场景工作流

## Changelog

### 2026-04-08

- 待办详情时间线编辑保存修复：
  - 时间线编辑不再依赖失焦提交
  - 显式提供保存 / 取消，顶部保存也会带上当前时间线编辑内容
- 时间线附件能力上线：
  - 支持给时间线上传任意类型附件
  - 支持把文件直接拖拽到时间线卡片上传
  - 支持把剪贴板中的截图图片直接粘贴到当前时间线卡片
  - 附件区改为卡片内收起 / 展开，避免附件过多时卡片过高
- 附件预览体验增强：
  - 图片附件显示缩略图并可预览
  - 视频附件显示预览入口并可直接打开
  - 其他附件以文件项方式展示并支持移除
- 导出方案增强为图文版：
  - 时间线附件会进入导出方案上下文
  - 图片附件会作为多模态输入提供给方案生成模型
  - 导出的 Markdown 会自动追加“附件图示”区并嵌入图片
  - 视频与其他附件会在导出文档中追加可点击链接
  - 导出方案会强制补足“时间线回顾”章节，并保留明确时间节点
- 模型配置增强：
  - `config.json` 现支持三处模型分别配置：截图识别、标题生成、方案生成
  - 新增 `title_generation_model` 与 `plan_export_model`
  - 保持向后兼容：旧版 `config.json` 缺少新字段时仍可正常运行

## 本地数据目录

程序默认使用 `~/.aica/` 目录保存本地数据：

- `~/.aica/config.json`
- `~/.aica/prompts.json`
- `~/.aica/todos.json`
- `~/.aica/feedback/feedback.jsonl`
- `~/.aica/feedback/images/`

## 启动

推荐直接从源码运行：

```powershell
python .\run_aica.py
```

如果使用 conda 环境，例如：

```powershell
conda activate aica
python .\run_aica.py
```

## 项目结构

```text
.
├── run_aica.py
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── requirements-build.txt
├── scripts/
├── src/
│   └── aica/
│       ├── main.py
│       ├── analysis_flow.py
│       ├── capture_ui_flow.py
│       ├── capture_session.py
│       ├── overlay.py
│       ├── toolbar.py
│       ├── worker.py
│       ├── parser.py
│       ├── models.py
│       ├── prompts.py
│       ├── ticket_field_resolver.py
│       ├── result_dialog.py
│       ├── result_flow.py
│       ├── todo_store.py
│       ├── todo_controller.py
│       ├── todo_panel.py
│       ├── todo_detail_panel.py
│       ├── feedback.py
│       ├── feedback_panel.py
│       ├── single_instance.py
│       └── qml/
│           ├── TodoPanel.qml
│           ├── TodoDetailPanel.qml
│           └── ResultDialog.qml
└── tests/
```

## 测试

当前推荐的快速回归命令：

```powershell
pytest tests\test_overlay.py tests\test_compress.py tests\test_prompts.py tests\test_single_instance.py tests\test_analysis_flow.py tests\test_result_flow.py tests\test_todo_store.py tests\test_todo_controller.py tests\test_timeline_entry_dedup.py tests\test_ticket_field_resolver.py -q
```

运行完整测试：

```powershell
pytest -q
```

快速语法与导入检查：

```powershell
python -m compileall src\aica run_aica.py
```

## 打包

Windows `onedir`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Windows `onefile`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile.ps1
```

## 当前边界与未实现项

为避免 README 与当前实现脱节，下面这些内容明确不视为“已支持”：

- 当前主要面向 Windows，尚未完成 macOS 适配
- 当前只有单场景工作流，虽然 UI 中已预留场景切换能力
- 知识库联动检索尚未集成到现有工单处理链路
- 与外部工单系统的同步能力尚未落地

## 说明

这个项目当前的重点不是做一个通用截图分析器，而是把每次截图分析沉淀成可追踪、可编辑、可持续推进的工单待办与时间线，帮助一线支持和交付团队降低上下文切换成本。
