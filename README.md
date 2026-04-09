# AI Snap Todo Assistant

面向 Windows 的 AI 工单待办助手。

围绕“截图采集上下文 -> AI 结构化提取 -> 创建/追加待办 -> 持续跟进时间线”设计，适合技术支持、售后、实施、交付等需要高频处理工单上下文的场景。

## 产品定位

- 使用 `Alt+A` 快速截取群聊、报错和工单上下文
- 由 AI 提取结构化字段和本次新增跟进内容
- 未选中待办时创建新待办
- 已选中待办时追加到现有待办，并保持时间线连续
- 在浮动待办栏和详情侧栏中持续查看、编辑、完成和导出任务

## 当前能力

- 全局热键截图：`Alt+A`
- 截图覆盖层支持框选与标注
- 单张截图分析与多张截图合并分析
- AI 结构化提取工单信息
- AI 二次生成更适合展示和保存的标题
- 待办浮动面板与详情侧栏
- 待办详情框支持通过顶部标题栏拖拽移动
- 时间线附件上传、预览与导出
- 本地待办持久化
- 反馈采集与 Prompt 优化
- 单实例运行保护

## 运行环境

- Windows 10 或更高版本
- Python 3.10+
- 可访问模型供应商接口
  - `openai_compatible`
  - `gemini`

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

运行配置保存到 `~/.aica/config.json`。

示例：

```json
{
  "default_provider_id": "siliconflow",
  "providers": [
    {
      "id": "siliconflow",
      "kind": "openai_compatible",
      "name": "SiliconFlow",
      "api_key": "",
      "base_url": "https://api.siliconflow.cn/v1/chat/completions",
      "timeout_seconds": 30,
      "models": [
        {
          "id": "qwen25-vl-72b",
          "name": "Qwen/Qwen2.5-VL-72B-Instruct",
          "capabilities": ["vision_chat", "text_chat"]
        },
        {
          "id": "qwen3-8b",
          "name": "Qwen/Qwen3-8B",
          "capabilities": ["text_chat"]
        }
      ]
    },
    {
      "id": "minmax",
      "kind": "openai_compatible",
      "name": "MiniMax",
      "api_key": "",
      "base_url": "https://api.minimax.io/v1/chat/completions",
      "timeout_seconds": 30,
      "models": [
        {
          "id": "minimax-m2-5",
          "name": "MiniMax-M2.5",
          "capabilities": ["text_chat"]
        },
        {
          "id": "minimax-m2-5-highspeed",
          "name": "MiniMax-M2.5-highspeed",
          "capabilities": ["text_chat"]
        }
      ]
    },
    {
      "id": "gemini",
      "kind": "gemini",
      "name": "Google Gemini",
      "api_key": "",
      "base_url": "",
      "timeout_seconds": 30,
      "models": [
        {
          "id": "gemini-2.5-flash",
          "name": "gemini-2.5-flash",
          "capabilities": ["vision_chat", "text_chat"]
        }
      ]
    }
  ],
  "task_model_bindings": {
    "analysis": {
      "provider_id": "siliconflow",
      "model_id": "qwen25-vl-72b"
    },
    "title_generation": {
      "provider_id": "siliconflow",
      "model_id": "qwen3-8b"
    },
    "plan_export": {
      "provider_id": "siliconflow",
      "model_id": "qwen25-vl-72b"
    },
    "prompt_optimization": {
      "provider_id": "siliconflow",
      "model_id": "qwen25-vl-72b"
    }
  },
  "hotkeys": {
    "capture": "Alt+A"
  },
  "max_image_bytes": 4194304
}
```

字段说明：

- `default_provider_id`：默认供应商 ID
- `providers`：供应商列表
- `providers[].kind`：当前支持 `openai_compatible` 与 `gemini`
- `providers[].api_key`：供应商密钥，不要提交真实密钥
- `providers[].base_url`：`openai_compatible` 供应商接口地址；Gemini 可留空
- `providers[].timeout_seconds`：该供应商默认请求超时时间
- `providers[].models`：该供应商可选模型目录
- `providers[].models[].capabilities`：能力标签，当前使用 `vision_chat` / `text_chat`
- `task_model_bindings`：为不同任务绑定供应商与模型
- `task_model_bindings.analysis`：截图分析
- `task_model_bindings.title_generation`：标题生成
- `task_model_bindings.plan_export`：方案导出
- `task_model_bindings.prompt_optimization`：Prompt 优化
- `max_image_bytes`：图片压缩阈值，默认 `4MB`

补充说明：

- 首次运行或任务绑定缺少可用 `api_key` / 模型时，程序会弹窗引导配置
- 旧版 `config.json` 会在加载时自动迁移到新 schema
- 运行时内部只使用新配置结构，不再依赖旧顶层字段

## 本地数据目录

程序默认使用 `~/.aica/` 目录保存本地数据：

- `~/.aica/config.json`
- `~/.aica/prompts.json`
- `~/.aica/todos.json`
- `~/.aica/feedback/feedback.jsonl`
- `~/.aica/feedback/images/`

## 启动

```powershell
python .\run_aica.py
```

如果使用 conda 环境，例如：

```powershell
conda activate aica
python .\run_aica.py
```

## 测试

推荐的回归命令：

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

## 控制面板更新

当前版本已经切换为“系统托盘 + 统一控制面板”入口，控制面板负责模型供应商、任务模型、截图热键、压缩阈值与本地目录跳转等配置。详细变更记录见下方 `Changelog`。

## Changelog

后续功能更新请同步记录到本节，避免 README 与实际行为脱节。

### 2026-04-09

- 托盘控制面板重构：
  - 应用启动后默认驻留系统托盘，点击托盘图标可打开控制面板
  - 新增基于 QML 的统一控制面板，集中管理模型供应商、任务模型绑定、截图热键、图片压缩阈值与本地目录入口
  - 移除旧的 `api_key_dialog.py` 配置对话框，缺少 `api_key` 或模型绑定时只提示前往控制面板完成设置
- 待办详情框交互优化：
  - 待办详情框支持通过顶部标题栏拖拽移动，方便在查看待办列表和详情内容时手动调整位置
- 外部脚本集成能力：
  - 新增待办事件总线、脚本处理器与外部绑定存储，支持把待办生命周期事件发布给包外脚本处理
  - 新增 `~/.aica/integrations.json` 与 `~/.aica/todo_bindings.json`，分别保存集成配置和外部 `externalId` 绑定关系
  - 控制面板新增“脚本集成”分组，可导入、启用、停用、替换和移除本地脚本
  - 支持导入 `.py`、`.pyw`、`.ps1`、`.bat`、`.cmd`、`.exe`，并按脚本类型自动生成调用命令
  - `update_todo()` 编辑保存后也会发布 `updated` 事件，外部脚本可通过 `delta.changed_fields` 判断本次修改内容
- 配置与运行时体验升级：
  - `config.json` 新增 `hotkeys.capture`，默认值为 `Alt+A`，并保持旧配置自动补全
  - 截图热键支持在控制面板保存后立即重绑，无需重启应用
  - 新增统一的本地路径辅助层，收口 `~/.aica` 下的配置、Prompt 历史、反馈和错误日志入口
- 控制面板视觉优化：
  - 控制面板整体改为更扁平的分组样式，减少多层边框嵌套
  - 窗口外层改为自定义圆角窗体，移除系统原生直角标题栏
  - 顶部新增自定义拖拽栏与最小化/关闭按钮，使窗体圆角与内部风格保持一致

### 2026-04-08

- 模型架构重构：
  - 模型调用从 worker 中抽离，新增统一 `LLMService`、Provider Registry 和任务绑定层
  - 首批内置两类供应商：`openai_compatible` 与 `gemini`
  - 截图分析、标题生成、方案导出、Prompt 优化全部改为通过任务绑定选择模型
- 配置体系升级：
  - `config.json` 改为 `providers + task_model_bindings` 新 schema
  - 模型供应商与模型均支持配置
  - 新增 Gemini 原生供应商配置入口
  - 旧版 `api_key/model/api_base_url` 配置会自动迁移到新结构
- 待办详情时间线编辑保存修复：
  - 时间线编辑不再依赖失焦提交
  - 显式提供保存 / 取消，顶部保存也会带上当前时间线编辑内容
- 时间线附件能力上线：
  - 支持给时间线上传任意类型附件
  - 支持把文件直接拖拽到时间线卡片上
  - 支持把剪贴板中的截图图片直接粘贴到当前时间线卡片
  - 附件区改为卡片内收起 / 展开，避免附件过多时卡片过高
- 附件预览体验增强：
  - 图片附件显示缩略图并可预览
  - 视频附件显示预览入口并可直接打开
  - 其他附件以文件项形式展示并支持移除
- 导出方案增强为图文版：
  - 时间线附件会进入导出方案上下文
  - 图片附件会作为多模态输入提供给方案生成模型
  - 导出的 Markdown 会自动追加“附件图示”区并嵌入图片
  - 视频与其他附件会在导出文档中追加可点击链接
  - 导出方案会强制补足“时间线回顾”章节，并保留明确时间节点

## 外部平台集成

当前版本支持将待办生命周期事件以统一 JSON 协议发送给包外适配器，并独立保存平台返回的 `externalId` 绑定关系。

- 详细接入文档：`docs/todo-event-integration.md`
- 脚本集成指南：`docs/script-integration-guide.md`
- integration 配置文件：`~/.aica/integrations.json`
- 外部绑定文件：`~/.aica/todo_bindings.json`

设计目标：

- 不修改 `todos.json` 结构
- 不把平台 API、鉴权、字段映射硬编码到主程序
- 主程序只负责发布标准事件、调用处理器、保存 binding
- 后续增加 webhook / 自定义处理器或做查元数据时可复用同一套 integration 边界

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
│       ├── control_panel.py
│       ├── capture_ui_flow.py
│       ├── capture_session.py
│       ├── config.py
│       ├── overlay.py
│       ├── toolbar.py
│       ├── worker.py
│       ├── prompt_optimizer.py
│       ├── llm/
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
└── tests/
```
