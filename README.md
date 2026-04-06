# AI Capture Assistant

面向 Windows 的截图增强与 AI 分析工具。通过全局快捷键 `Alt+A` 唤起截图，支持截图后直接编辑选区，再将截图交给大模型分析，最后对结果进行人工修正和反馈沉淀。

## 当前功能

- 全局快捷键 `Alt+A` 唤起截图
- 多屏截图遮罩与 DPI 感知
- 截图后直接进入编辑态
- 支持拖拽移动选区
- 支持方框、箭头、文字标注
- 文字标注为原位输入，不弹额外对话框
- 支持连续多张截图后统一分析
- 支持场景切换，提示词持久化到 `~/.aica/prompts.json`
- 支持识别结果二次编辑
- 支持反馈保存与基于反馈的提示词优化
- 单实例运行，重复启动会直接拦截

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

开发和测试依赖：

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

- `api_key` 默认为空，代码中不再内置密钥
- `api_base_url` 需要兼容 OpenAI Chat Completions
- `max_image_bytes` 当前用于图片压缩阈值，默认 `4MB`
- 如果执行智能总结时未配置 `api_key`，程序会弹出内置表单引导填写并保存

提示词配置会保存在：

- `~/.aica/prompts.json`
- `~/.aica/prompt_history/`

反馈数据会保存在：

- `~/.aica/feedback/feedback.jsonl`
- `~/.aica/feedback/images/`

## 启动

推荐直接运行：

```powershell
python .\run_aica.py
```

如果你已经把 `src` 加到 `PYTHONPATH`，也可以：

```powershell
$env:PYTHONPATH = "src"
python -m aica
```

## 使用流程

1. 按 `Alt+A` 唤起截图。
2. 鼠标框选截图区域。
3. 截图完成后直接进入编辑态，可继续：
   - 拖动移动选区
   - 画方框
   - 画箭头
   - 输入文字标注
4. 在浮动工具栏中选择场景。
5. 根据需要执行：
   - `智能总结`
   - `继续截图`
   - `复制截图`
   - `撤销`
   - `清空`
   - `取消`
6. AI 返回结果后，可在结果窗口中继续编辑。
7. 如果结果不理想，可进入反馈面板保存修正，并可触发提示词优化。

## 默认场景

程序内置 4 个默认场景：

- `工单提取`
- `代码审查`
- `数据提取`
- `界面审计`

这些场景在首次启动或提示词配置缺失时会自动提供。

## 项目结构

```text
.
├─ run_aica.py               # 本地启动入口
├─ aica.spec                 # PyInstaller 打包配置
├─ requirements.txt          # 运行依赖
├─ requirements-dev.txt      # 测试依赖
├─ requirements-build.txt    # 打包依赖
├─ scripts/
│  └─ build_exe.ps1          # Windows 打包脚本
├─ src/
│  └─ aica/
│     ├─ main.py             # 应用主流程
│     ├─ overlay.py          # 截图与编辑态交互
│     ├─ toolbar.py          # 浮动工具栏
│     ├─ worker.py           # AI 调用线程
│     ├─ prompts.py          # 提示词管理
│     ├─ feedback.py         # 反馈存储与分析
│     ├─ feedback_panel.py   # 反馈面板
│     ├─ result_dialog.py    # 结果编辑窗口
│     ├─ config.py           # 配置管理
│     └─ image_utils.py      # 图片压缩
└─ tests/
   ├─ conftest.py
   ├─ test_compress.py
   └─ test_overlay.py
```

## 打包为 EXE

当前仓库已接入两种 Windows 打包方案：

```text
one-dir:  dist\AICA\AICA.exe
onefile:  dist\AICA.exe
```

### 方式一：使用脚本

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

如果当前环境已安装依赖，可跳过安装阶段：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -SkipInstall
```

构建单文件版本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile.ps1
```

如果当前环境已安装依赖：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile.ps1 -SkipInstall
```

### 方式二：直接执行 PyInstaller

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean .\aica.spec
python -m PyInstaller --noconfirm --clean .\aica_onefile.spec
```

### 打包说明

- 入口脚本是 `run_aica.py`
- `aica.spec` 已包含 `src` 路径
- `aica_onefile.spec` 用于生成单文件 `exe`
- 已额外收集 `pynput` 和 `pyperclip` 的子模块，降低 Windows 打包后缺依赖的概率
- 已配置应用图标 `assets/aica_icon.ico`
- 已配置 Windows 版本信息，`CompanyName = edison`
- `one-dir` 启动更稳，`onefile` 分发更方便

## 测试

当前已验证的回归命令：

```powershell
pytest tests\test_overlay.py tests\test_compress.py tests\test_prompts.py -q
```

## 常见问题

### 1. 按 `Alt+A` 没反应

- 确认当前系统允许全局热键监听
- 确认没有被其他程序占用相同快捷键
- 尝试以同等权限重新启动程序

### 2. 截图后点选区还是操作到底层窗口

当前实现已经避免“透明挖空导致点击穿透”的模式。如果仍出现，优先检查是否运行的是旧版本可执行文件。

### 3. 工具栏看不到

当前工具栏会挂载到当前 overlay 上并自动限制在屏幕范围内。如果仍不可见，通常是旧构建产物未更新。

### 4. AI 调用失败

优先检查：

- `api_key` 是否配置
- `api_base_url` 是否正确
- 模型是否支持图像输入
- 网络是否可访问对应接口

## 说明

- 当前结果解析逻辑会优先保留模型原始文本内容，适合结果展示和人工二次编辑
- 如果你需要更强的结构化解析，可以继续扩展 `parser.py` 与对应场景提示词
- `annotation_dialog.py` 仍在仓库中，但当前主流程已经切到 overlay 内直接编辑
