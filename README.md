# AI Snap Todo Assistant

面向 Windows 与 macOS 的 AI 工单待办助手。

围绕“截图采集上下文 -> AI 结构化提取 -> 创建/追加待办 -> 持续跟进时间线”设计，适合技术支持、售后、实施、交付等需要高频处理工单上下文的场景。

## 产品定位

- 使用全局热键快速截取群聊、报错和工单上下文
- 由 AI 提取结构化字段和本次新增跟进内容
- 未选中待办时创建新待办
- 已选中待办时追加到现有待办，并保持时间线连续
- 在浮动待办栏和详情侧栏中持续查看、编辑、完成和导出任务

## 当前能力

- 全局热键截图：Windows 默认 `Alt+A`，macOS 默认 `Command+Shift+A`
- 截图覆盖层支持框选与标注
- 单张截图分析与多张截图合并分析
- AI 结构化提取工单信息
- AI 二次生成更适合展示和保存的标题
- 待办浮动面板与详情侧栏
- 待办详情框支持通过顶部标题栏拖拽移动
- 项目管理面板支持按项目维护待办上下文
- 项目支持日期选择与项目级别设置
- 时间线附件上传、预览与导出
- 本地待办持久化
- 反馈采集与 Prompt 调试
- 单实例运行保护

## 运行环境

- Windows 10 或更高版本
- macOS 13 或更高版本（支持 Apple Silicon 与 Intel）
- Python 3.10+
- 可访问模型供应商接口
  - `openai_compatible`
  - `gemini`
  - 内置供应商包含 `SiliconFlow`、`阿里云百炼`、`MiniMax` 与 `Google Gemini`

## 安装

Windows：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
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
      "id": "dashscope",
      "kind": "openai_compatible",
      "name": "阿里云百炼",
      "api_key": "",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
      "timeout_seconds": 30,
      "models": [
        {
          "id": "qwen-vl-max",
          "name": "qwen-vl-max",
          "capabilities": ["vision_chat", "text_chat"]
        },
        {
          "id": "qwen-plus",
          "name": "qwen-plus",
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
    "log_analysis": {
      "provider_id": "siliconflow",
      "model_id": "qwen25-vl-72b"
    },
    "plan_export": {
      "provider_id": "siliconflow",
      "model_id": "qwen25-vl-72b"
    },
    "context_summary": {
      "provider_id": "siliconflow",
      "model_id": "qwen3-8b"
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
- `task_model_bindings.log_analysis`：日志分析
- `task_model_bindings.plan_export`：方案导出
- `task_model_bindings.context_summary`：上下文摘要压缩
- `analysis_rules.json`：截图分析规则配置
- `prompt_debug/`：截图分析 Prompt 调试快照
- `max_image_bytes`：图片压缩阈值，默认 `4MB`

补充说明：

- 首次运行或任务绑定缺少可用 `api_key` / 模型时，程序会弹窗引导配置
- Windows 默认截图热键为 `Alt+A`；macOS 新建配置默认使用 `Command+Shift+A`
- 旧版 `config.json` 会在加载时自动迁移到新 schema
- 运行时内部只使用新配置结构，不再依赖旧顶层字段

## 本地数据目录

程序默认使用 `~/.aica/` 目录保存本地数据：

- `~/.aica/config.json`
- `~/.aica/analysis_rules.json`
- `~/.aica/prompt_debug/`
- `~/.aica/todos.json`
- `~/.aica/feedback/feedback.jsonl`
- `~/.aica/feedback/images/`

## 启动

Windows：

```powershell
python .\run_aica.py
```

macOS：

```bash
python run_aica.py
```

如果使用 conda 环境，例如：

```powershell
conda activate aica
python .\run_aica.py
```

## 测试

推荐的回归命令：

Windows：

```powershell
pytest tests\test_environment_access.py tests\test_log_analysis.py tests\test_context_summary.py tests\test_todo_detail_panel.py -q
```

macOS：

```bash
pytest tests/test_environment_access.py tests/test_log_analysis.py tests/test_context_summary.py tests/test_todo_detail_panel.py -q
```

运行完整测试：

```powershell
pytest tests -q
```

快速语法与导入检查：

Windows：

```powershell
python -m compileall src\aica run_aica.py
```

macOS：

```bash
python -m compileall src/aica run_aica.py
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

macOS `.app`：

```bash
./scripts/build_macos_app.sh
```

Intel Mac 原生 `x86_64` `.app`：

```bash
./scripts/build_macos_app.sh --target-arch x86_64
```

Apple Silicon 原生 `arm64` `.app`：

```bash
./scripts/build_macos_app.sh --target-arch arm64
```

通用 `universal2` `.app`：

```bash
./scripts/build_macos_app.sh --target-arch universal2
```

补充说明：

- 在 Intel Mac 上打 Intel 包时，直接使用本机 Python 环境执行即可。
- 在 Apple Silicon 机器上如果要打 `x86_64` 包，需要先准备 `x86_64` Python 环境（通常通过 Rosetta）。
- 打 `universal2` 包时，Python 解释器和关键依赖需要同时提供 `universal2` 兼容轮子，否则 PyInstaller 可能无法合并成通用包。
- 可通过 `./scripts/build_macos_app.sh --python /path/to/python` 指定用于打包的 Python。

## macOS 权限说明

- 首次在 macOS 使用全局截图热键时，可能需要在“系统设置 > 隐私与安全性”中为终端或打包后的 `AICA.app` 开启“辅助功能”和“输入监听”权限。
- 如果权限未开启，AICA 会继续启动，并保留菜单栏入口；授权后重启应用即可重新启用热键。

## 控制面板更新

当前版本已经切换为“系统托盘 + 统一控制面板”入口，控制面板负责模型供应商、任务模型、截图热键、压缩阈值与本地目录跳转等配置，并新增了项目管理能力、项目日期/项目级别设置以及窗口最大化支持。详细变更记录见下方 `Changelog`。

## Changelog

后续功能更新请同步记录到本节，避免 README 与实际行为脱节。

### 2026-05-14

- Chattodo macOS 云端打包流程上线：
  - 新增 GitHub Actions unsigned macOS 构建工作流，支持在云端产出未签名的 macOS 应用包
  - 新增 `chattodo-cross-packager` 打包 skill，补充 OpenAI agent 配置、构建矩阵说明以及 PowerShell、Shell、Python 打包脚本
  - 补充跨平台打包脚本测试，覆盖打包命令生成、产物路径与关键参数传递
- macOS 架构参数修复：
  - 修复云端打包时目标架构参数未正确传递到 PyInstaller spec 的问题
  - 在 `aica_macos.spec` 中接入 `TARGET_ARCH` 目标架构配置，确保 `arm64`、`x86_64` 与 `universal2` 构建结果符合预期
  - 新增 macOS spec 架构参数测试，防止后续构建脚本改动造成回归

### 2026-05-13

- 待办事项排序与数据库模式升级：
  - SQLite 数据库新增待办排序相关字段，为控制面板和存储层提供稳定的排序能力
  - 更新 SQLite 仓储逻辑，写入待办时维护排序值，保证新增和既有待办在列表中的展示顺序可控
- macOS Intel 打包支持补强：
  - 更新 macOS 构建脚本，支持显式指定 `arm64`、`x86_64` 与 `universal2` 目标架构
  - 增加构建前架构输出与兼容性提示，降低在 Apple Silicon 上误打 Intel 包的风险
  - 补充 README 中的 Intel Mac 与通用包构建说明，明确不同机器上的打包前提
  - 增加 macOS 构建文档测试，确保 README 中的多架构打包说明与脚本能力保持一致

### 2026-04-29

- 待办与项目关联维护增强：
  - 新增工单项目关联解除能力，可在控制面板中取消待办与项目的绑定关系
  - 同步更新存储契约、SQLite 仓储与待办存储逻辑，确保解除关联后数据状态一致
- 辅助排查与案例检索修复：
  - 修复待办详情面板中辅助分析的加载状态展示，避免分析流程结束后状态残留
  - 案例匹配结果新增低分过滤，低于 50 分的相似案例不再进入展示和辅助分析链路
- 方案导出稳定性修复：
  - 修正方案导出任务的模型类型选择逻辑
  - 调整方案导出过程中的通知机制，使导出状态反馈与实际执行结果保持一致

### 2026-04-28

- 故障排查窗口能力上线：
  - 新增辅助排查分析入口与故障排查结果展示窗口，支持在待办详情中查看结构化排查建议
  - 新增相似案例检索能力，可基于当前工单上下文查找历史相似案例
  - 案例搜索结果支持评分、排序与低分过滤，提升推荐案例的相关性
- 结论时间线与附件处理修复：
  - 修复结论时间线中的附件处理逻辑，避免附件同步、展示或分析时出现遗漏
  - 同步补充结论时间线、待办详情和辅助排查相关测试覆盖
- 环境访问与 QML 交互优化：
  - 优化环境访问弹窗的链接复制功能，提高访问凭据和环境链接复用效率
  - 优化 QML 布局、快捷键处理和加载弹窗逻辑，改善详情面板与环境管理区域的交互稳定性
  - 更新故障排查窗口配色主题，使其与近期控制面板视觉风格保持一致

### 2026-04-27

- 控制面板与环境配置增强：
  - 新增 OTP 二维码配置导入功能，支持从二维码中提取并写入环境相关配置
  - 环境访问弹窗新增复制能力，便于快速复制访问地址或凭据
- 组件样式与文本质量优化：
  - 重构 `ControlPanelSettingsCombo` 组合框组件，支持自定义弹窗样式
  - 更新代码风格指南，并修复界面中文文本乱码问题

### 2026-04-24

- 环境管理功能增强：
  - 持续完善控制面板中的环境管理能力，增强环境配置维护、展示与项目维度管理体验
  - 同步补充控制面板环境管理相关测试，降低后续配置功能迭代风险

### 2026-04-23

- 环境管理与访问控制上线：
  - 控制面板新增环境管理模块，支持维护全局环境和项目环境配置
  - 新增环境访问控制链路，用于在待办详情中按上下文打开或展示相关环境信息
  - 新增 OTP 密钥提取工具与导入脚本，支持从二维码或配置来源中提取动态口令密钥
  - SQLite schema、仓储层和存储契约补齐环境配置相关数据结构
- 测试覆盖补充：
  - 新增控制面板、环境访问和 OTP 密钥提取相关测试，覆盖环境配置的核心读写与访问流程

### 2026-04-22

- 待办详情操作与草稿状态增强：
  - 待办详情面板新增核心操作能力，补齐详情侧的任务处理入口
  - 时间线编辑新增草稿状态管理，减少编辑过程中未保存内容丢失的风险
  - 新增待办结论时间线同步能力，并完善工单丰富化失败时的错误处理
- 工单丰富化与保存策略重构：
  - 重构工单丰富化逻辑和待办详情保存策略，使丰富化、结论生成与保存链路更清晰
  - 补充丰富化失败、结论同步和保存策略相关测试，提升复杂状态下的回归保障
- 官网、文档与主题样式更新：
  - 新增官网和文档网站相关内容
  - 统一主题颜色变量并优化 QML 样式配置，减少界面色彩和组件状态不一致

### 2026-04-21

- 工单流转与补全能力增强：
  - 新增“重新打开已完成工单”功能，便于已关闭事项再次进入跟进流程
  - 新增异步工单丰富能力，可在后台补全和增强工单上下文信息
- 阶段总结与时间线编辑优化：
  - 优化阶段总结功能，并改进时间线梳理规则，提升总结内容的可读性与结构性
  - 重构时间线卡片编辑实现，进一步理顺编辑交互与数据更新链路
  - 修复待办详情面板位置保持问题，减少多窗口协同时的位置跳动
- 通知与资源管理重构：
  - 新增应用内通知系统，替换原有消息提示方式，统一反馈体验
  - 重构通知中心的布局与同步逻辑，改善通知展示和状态更新的一致性
  - 统一资源文件路径管理，降低图标、图片等静态资源在不同模块中的维护成本
- 构建版本控制补充：
  - 新增版本过期检查能力，可在构建产物过期后给出运行限制或提示

### 2026-04-20

- 阶段总结窗口持续升级：
  - 阶段总结输出从纯文本切换为 Markdown，提升内容展示与后续复用能力
  - 新增阶段总结编辑模式与分段展示能力，便于按结构调整总结内容
  - 新增可调整大小的阶段摘要窗口，并重构其 UI 组件与数据处理逻辑，改善编辑和阅读体验
- 时间线摘要与日志分析增强：
  - 时间线汇总新增附件过滤能力，减少无关附件对摘要结果的干扰
  - 优化日志分析代理的请求链归因和 LLM 回退逻辑，提升复杂场景下的稳定性
- 前端体验统一：
  - 统一前端界面样式，进一步收敛近期新增面板与组件的视觉风格
  - 移除工单复制成功状态消息，减少冗余提示对主流程操作的打扰

### 2026-04-19

- 待办与反馈界面交互优化：
  - 新增待办置顶交互，方便优先关注高价值或紧急事项
  - 将反馈面板重构为 QML 实现，统一与控制面板、待办相关界面的技术栈和视觉表现
- 界面细节与工程整理：
  - 调整模型页标签激活色，优化页签切换时的视觉反馈
  - 更新 `.gitignore` 并同步本地工程改动，整理构建与开发过程中的文件管理策略

### 2026-04-18

- macOS 适配与运行时能力补齐：
  - 新增 macOS 打包配置与构建脚本，补齐 `.app` 产物构建链路
  - 引入运行时能力抽象，统一处理 macOS 与 Windows 下的窗口、字体、脚本与热键差异
  - 完善单实例、主入口与相关窗口在 macOS 下的行为兼容性，确保菜单栏入口和基础流程可用
- 日志分析结果结构化升级：
  - 重构日志分析消费者，支持输出更结构化的分析结果
  - 同步调整日志分析结果卡片与待办详情展示，提升日志排查结果的可读性
  - 补充日志分析相关测试，覆盖结构化输出后的核心链路
- 控制面板与品牌视觉优化：
  - 优化快捷键录入交互，增强热键配置过程中的反馈与可用性
  - 调整控制面板按钮、列表、配色和品牌资源，统一近期界面视觉风格
  - 更新应用图标与控制面板品牌呈现，提升桌面端识别度
- 待办面板样式调整：
  - 调整待办浮动面板标题文案与头部布局
  - 优化待办面板视觉样式，使其与控制面板的新品牌风格保持一致

### 2026-04-17

- 阶段总结窗口与交互升级：
  - 新增阶段总结功能，支持从待办详情中触发阶段性总结
  - 将阶段总结面板重构为独立窗口，持续优化布局、尺寸同步、交互逻辑与视觉样式
  - 完善邻居面板位置解析能力，提升阶段总结窗口与待办详情联动时的定位稳定性
- 上下文摘要能力增强：
  - 控制面板补充日志分析与上下文摘要相关入口，便于统一配置和使用
  - 重构上下文摘要代理的提示词与规则，提升摘要结果的结构化与可控性
  - 在时间线总结中新增“当前结论”段落，方便快速查看阶段性判断
- 存储与界面细节完善：
  - 存储层新增任务完成时间字段，支持更准确的完成状态记录与后续筛选统计
  - 调整待办详情面板与待办面板配色，统一近期新增窗口的视觉风格
  - 补充热键、上下文摘要与存储相关测试，覆盖新增交互和数据字段

### 2026-04-16

- 时间线架构与日志分析链路重构：
  - 重构待办时间线卡片体系，拆分基础卡片与日志分析卡片，完善时间线扩展能力
  - 集成日志分析代理系统，新增日志分析命令、任务卡片、结果卡片及编排与持久化链路
  - 接入日志分析能力到主流程与控制面板，为后续上下文摘要和时间线总结打基础
- 时间线交互与反馈优化：
  - 新增时间线卡片删除功能，补齐时间线内容清理操作
  - 增加日志分析进度显示，提升长任务执行过程中的可见性
  - 调整日志分析命令的显示逻辑，避免在不合适场景下暴露操作入口
- 上下文摘要能力落地：
  - 新增上下文摘要代理、模型与服务层，形成独立的摘要能力模块
  - 支持基于日志分析结果生成上下文摘要，作为时间线总结能力的底层支撑
  - 补充日志分析与上下文摘要测试，覆盖核心流程与命令隐藏逻辑

### 2026-04-15

- 项目环境访问与 OTP 能力扩展：
  - 新增项目环境访问管理能力，可在待办相关流程中维护环境访问信息
  - 增强 OTP 能力，支持多种算法与配置项，并补充 OTP 密钥提取脚本
  - 优化环境访问弹窗中的 OTP 展示与复制体验，减少手动处理成本
- 待办附件与摘要信息增强：
  - 待办草稿新增附件支持，补齐草稿阶段的附件管理链路
  - 优化附件相关操作体验，提升附件增删改查的顺畅度
  - 待办摘要新增产品线字段，方便在列表和概览中快速识别业务归属
- 工单面板操作体验优化：
  - 控制面板新增工单复制功能与“今日完成”筛选选项，提升日常检索和复用效率
  - 调整工单表格列宽、布局间距与操作列呈现，改善高信息密度场景下的可读性
- 设计探索：
  - 新增阶段总结轻量改写原型页面，用于支持总结内容的轻量化重写与方案验证

### 2026-04-14

- 工单列表与字段编辑能力升级：
  - 重构工单列表界面并新增筛选功能，提升工单检索与批量浏览效率
  - 控制面板新增工单复制、删除以及新字段支持，补齐工单维护操作链路
  - 新增产品线字段并实现功能点自动刷新，进一步完善工单上下文字段
- QML 组件与交互细节优化：
  - 新增可选择复制的文本组件，并替换原有文本控件，增强信息复制体验
  - 优化 `DetailField` 组件实现，重构字段编辑状态管理机制，降低复杂字段编辑的维护成本
- 存储与配置修复：
  - 修复产品线字段存储与同步逻辑，避免字段数据在持久化和联动过程中丢失
  - 增加推荐兼容性 API 超时时间，改善弱网或慢响应场景下的稳定性

### 2026-04-13

- 工单详情页与字段体系完善：
  - 新增工单详情页面，并持续重构页面布局与样式，提升详情展示与编辑体验
  - 控制面板补充产品线、版本号、ACH 单号、ACH 填写时间等字段支持
  - 存储层新增工单增强字段、结论字段以及 ACH 相关字段支持，确保新字段可完整落盘
- 根因分析与表单交互优化：
  - 新增根因分析级联选择功能，支持更结构化的问题归因录入
  - 重构级联选择器 UI 组件，并调整根因描述字段布局，提升复杂表单的可用性
- 待办时间线体验优化：
  - 持续优化待办事项时间线功能，改善时间线内容维护与浏览体验
- 控制面板结构增强：
  - 重构控制面板界面结构并增强工单管理能力，为后续工单相关功能扩展打下基础

### 2026-04-12

- 控制面板能力与界面重构：
  - 新增窗口边缘调整大小能力，支持在不同屏幕尺寸下灵活调整控制面板布局
  - 重构控制面板界面结构并拆分复用组件（按钮、分组卡片、输入框、下拉框等），降低后续配置模块维护成本
  - 新增项目视图模式切换与管理入口，完善项目维度下的浏览与操作体验
- 工单管理与存储能力升级：
  - 控制面板新增工单管理相关入口与界面联动，补齐工单信息维护链路
  - SQLite 存储层新增工单版本字段支持，覆盖模型、仓储与控制面板展示，提升工单状态演进可追踪性
  - 打包配置新增 SQLite schema 文件（`src/aica/storage/sqlite/schema.sql`）纳入，确保构建产物包含完整数据库结构
- 分析流程与规则调试升级：
  - 重构截图分析流程，进一步梳理分析链路中的 worker、结果回传与状态衔接
  - 新增分析规则管理与调试追踪能力，可记录 Prompt 快照与相关调试信息，便于排查分析结果和规则配置问题
- 待办分析辅助能力：
  - 新增 `aica-todo-reader` skill，可直接查询 `aica.db` 中的待办、时间线与统计信息，用于历史工单回顾、客户问题汇总和数据分析
- 测试覆盖补充：
  - 新增屏幕坐标与虚拟几何相关测试，提升多屏与复杂显示布局场景下的稳定性验证

### 2026-04-11

- 控制面板能力扩展：
  - 新增项目管理模块，用于维护项目维度的待办上下文
  - 新增项目日期选择器，便于按日期管理项目记录
  - 新增项目级别设置，支持给项目标记优先级或层级信息
  - 支持控制面板窗口最大化，提升大屏下的操作体验

### 2026-04-10

- 待办同步体验增强：
  - 待办详情的同步状态区新增最近同步事件与同步记录展示
  - 新增 `manual_sync` 事件，支持从待办详情手动触发同步/重试同步
- 分析链路增强：
  - 新增分析指标记录能力，补充分析过程数据落盘与对应测试，便于后续排查模型调用与结果质量问题
  - 新增图片预处理与文本清理工具，进一步稳定截图分析前的数据输入
  - 调整分析策略说明，补充 `group_name` 信息提取规则
- 模型与供应商配置升级：
  - 新增阿里云百炼 `DashScope` 供应商接入，可在控制面板中直接配置并绑定模型
  - 优化模型配置管理体验，补充相关配置项与测试覆盖
  - 修复阿里云百炼模型别名兼容与图片大小限制处理，减少因模型名映射或超限导致的分析失败
- 控制面板与本地存储管理：
  - 控制面板新增存储路径管理，可集中查看和操作配置、数据等本地目录入口
  - 本地路径状态管理与路径工具同步完善，补充对应测试用例
- 运行稳定性与打包修复：
  - 修复 UPX 压缩相关打包问题，改善可执行文件构建稳定性
  - 补强主程序异常处理与日志记录，便于定位运行时故障

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
  - 截图分析、方案导出全部改为通过任务绑定选择模型
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
