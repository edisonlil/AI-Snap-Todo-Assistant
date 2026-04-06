# AI Snap Todo Assistant

面向 Windows 的工单待办助手。  
它不再是一个单纯的截图分析工具，而是一个围绕“收集信息、生成待办、持续跟进”的轻量工作台。

截图只是入口：通过 `Alt+A` 快速截取群聊、报错、工单上下文，再由 AI 生成结构化工单字段、当前摘要和时间线跟进记录，最终沉淀到待办中持续跟踪。

## 核心流程

1. 按 `Alt+A` 唤起截图。
2. 选择并标注截图内容。
3. AI 将截图整理为：
   - 待办标题
   - 群聊名称
   - 环境
   - 产品线
   - 工单类型
   - 当前摘要
   - 本次时间线记录
4. 保存后：
   - 未选中待办时，创建新待办
   - 已选中待办时，更新当前摘要并追加时间线
5. 在待办栏和详情页中持续查看、编辑和完成任务。

## 当前功能

- 全局快捷键截图：`Alt+A`
- 截图后直接框选、移动、矩形、箭头、文字标注
- 连续多张截图后统一分析
- 待办栏支持：
  - 选中待办
  - 展开 / 收起
  - 拖拽移动与边缘吸附
  - 最小化
- 详情页支持：
  - 编辑标题
  - 编辑固定字段摘要
  - 编辑当前摘要
  - 直接编辑时间线文本
- 单实例运行
- 反馈保存与提示词优化

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

首次运行前建议创建 `~/.aica/config.json`：

```json
{
  "api_key": "",
  "model": "Qwen/Qwen2.5-VL-72B-Instruct",
  "api_base_url": "https://api.siliconflow.cn/v1/chat/completions",
  "timeout_seconds": 30,
  "max_image_bytes": 4194304
}
```

说明：

- `api_key` 默认留空，程序不会内置真实密钥
- `api_base_url` 需要兼容 OpenAI Chat Completions
- `max_image_bytes` 用于图片压缩阈值，默认 `4MB`

本地数据目录：

- `~/.aica/config.json`
- `~/.aica/prompts.json`
- `~/.aica/todos.json`
- `~/.aica/feedback/feedback.jsonl`
- `~/.aica/feedback/images/`

## 启动

推荐直接运行：

```powershell
python .\run_aica.py
```

如果你使用 conda 环境，例如：

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
│       ├── overlay.py
│       ├── toolbar.py
│       ├── worker.py
│       ├── parser.py
│       ├── models.py
│       ├── prompts.py
│       ├── todo_store.py
│       ├── todo_controller.py
│       ├── todo_panel.py
│       ├── todo_detail_panel.py
│       ├── result_dialog.py
│       ├── result_flow.py
│       └── qml/
└── tests/
```

## 测试

当前建议的快速回归命令：

```powershell
pytest tests\test_prompts.py tests\test_todo_store.py tests\test_todo_controller.py tests\test_result_flow.py -q
```

PyQt 相关回归：

```powershell
pytest tests\test_overlay.py tests\test_compress.py tests\test_single_instance.py -q
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

## 当前产品定位

AI Snap Todo Assistant 的核心不是“提取截图文本”，而是：

- 快速采集工单上下文
- 自动归纳成结构化待办
- 把每次截图分析沉淀为可追踪的时间线
- 帮助支持、售后、实施、交付场景中的任务跟进

后续演进重点也将围绕待办、摘要、时间线和协作效率，而不是继续做通用型截图分析器。
