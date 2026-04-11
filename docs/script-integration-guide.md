# 脚本集成指南

本文面向通过 `~/.aica/integrations.json` 接入外部脚本的使用者，重点说明：

- 如何编写一个最小可用的脚本集成
- Python 脚本推荐写法
- 打包版 AICA 下常见编码问题
- 常见错误与排查方法

相关协议说明可继续参考 [待办外部平台集成说明](./todo-event-integration.md)。

## 1. 集成方式概览

AICA 会在待办事件发生时启动外部脚本，并通过标准输入传递一个 JSON 事件对象：

- `stdin`：事件 JSON
- `stdout`：脚本返回的 ack JSON
- `stderr`：仅作为日志记录，不作为成功返回

常见事件类型：

- `created`
- `appended`
- `updated`
- `completed`
- `deleted`
- `manual_sync`

## 2. integrations.json 示例

```json
{
  "todo_event_integrations": [
    {
      "id": "aica-event-logger",
      "name": "aica_event_logger",
      "enabled": true,
      "type": "script",
      "command": "py",
      "args": [
        "C:\\Users\\Admin\\Desktop\\11\\aica_event_logger.py"
      ],
      "cwd": "C:\\Users\\Admin\\Desktop\\11",
      "timeout_seconds": 8,
      "env": {}
    }
  ]
}
```

建议：

- `id` 保持稳定，不要频繁改动
- `cwd` 设置为脚本所在目录，避免相对路径混乱
- `.py` 脚本优先用 `py` 或明确的 `python.exe`

## 3. 推荐 Python 脚本模板

推荐脚本在入口处显式固定标准流编码，然后再读取 `stdin`：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    event = json.load(sys.stdin)

    Path("event-log.json").write_text(
        json.dumps(event, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ack = {
        "ok": True,
        "action": "logged",
    }
    print(json.dumps(ack, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

如果是 PowerShell、Node.js、Go、Rust 等脚本，也建议显式指定输入输出使用 UTF-8。

## 4. 打包版下的编码注意事项

这是最容易踩坑的一点。

### 现象

源码运行正常，但打包后触发外部 Python 脚本时报错，例如：

```text
UnicodeEncodeError: 'utf-8' codec can't encode character '\udcaa' in position ...
surrogates not allowed
```

### 原因

在 Windows 上，打包后的 GUI 进程拉起外部 Python 脚本时，子进程的 `sys.stdin` 可能不是 UTF-8，而是类似：

- `encoding = "gbk"`
- `errors = "surrogateescape"`

这会导致 AICA 传入的文本在脚本侧被错误解码，原本正常的字符可能变成：

- `\udc80`
- `\udca1`
- `\udcaa`
- `\udcae`

随后你再把它按 UTF-8 写文件，就会报 `surrogates not allowed`。

### 当前 AICA 侧已经做了什么

为降低踩坑概率，AICA 当前已经做了两层保护：

- 传给外部脚本的事件 JSON 采用 ASCII-safe 转义传输
- 启动子进程时补充 `PYTHONIOENCODING=utf-8` 和 `PYTHONUTF8=1`

但仍然建议脚本自己显式 `reconfigure()`，这样最稳。

## 5. 常见错误

### 5.1 `UnicodeEncodeError: surrogates not allowed`

原因：

- 脚本读取 `stdin` 时实际没有按 UTF-8 解码
- 读入文本中已经出现孤立代理项字符

建议：

- 在脚本入口显式 `sys.stdin.reconfigure(encoding="utf-8", errors="strict")`
- 将 `stdout` 和 `stderr` 也固定为 UTF-8
- 不要依赖系统默认编码

### 5.2 `json.JSONDecodeError`

原因：

- 脚本没有正确读取完整的 `stdin`
- 脚本先输出了其他调试文本，导致 `stdout` 不是纯 JSON

建议：

- 只在 `stdout` 输出最终 ack JSON
- 调试信息写入文件或 `stderr`

### 5.3 `command not found` / 脚本未启动

原因：

- `command` 配错
- 脚本路径不存在
- `cwd` 不正确

建议：

- 先在终端中手动验证 `command + args`
- 确认 `script_integration_display_path` 指向的脚本真实存在

### 5.4 有执行，但没有落盘

原因：

- 脚本启动成功，但写文件时失败
- 最常见是编码错误或目标目录权限问题

建议：

- 优先检查 `stderr` 日志
- 在写文件前先确认目录存在
- 对写入文本固定使用 UTF-8

## 6. ack 返回建议

最小可用 ack：

```json
{
  "ok": true,
  "action": "logged"
}
```

如果要建立绑定关系，返回：

```json
{
  "ok": true,
  "action": "created",
  "external_id": "TK-10001",
  "external_url": "https://platform.example.com/tickets/TK-10001"
}
```

建议：

- `stdout` 只输出一段 JSON
- `external_id` 一旦返回，后续事件会复用该绑定

## 7. 排查顺序建议

当脚本集成异常时，建议按这个顺序排查：

1. 先看 `~/.aica/error.log` 中的 `todo_event_sync` 日志
2. 确认脚本是否真的被启动
3. 检查脚本 `stderr`
4. 检查脚本里 `sys.stdin.encoding` 和 `sys.stdin.errors`
5. 检查 `stdout` 是否为单段合法 JSON
6. 检查写文件目标目录是否存在、是否可写

## 8. 推荐实践

- Python 脚本入口统一 `reconfigure()` 标准流编码
- 所有事件日志落盘都显式 `encoding="utf-8"`
- 调试信息写文件或 `stderr`，不要混入 `stdout`
- 先实现最小脚本，再逐步接入真实平台 API
- 如果脚本依赖第三方接口，先在脚本内部捕获异常并写清楚错误信息
