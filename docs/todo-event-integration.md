# 待办外部平台集成说明

## 目标

当前实现只覆盖两件事：

- 把待办生命周期事件通知到包外平台适配器
- 保存平台返回的 `externalId` 绑定关系

本期不做：

- 元数据查询
- UI 展示改造
- `todos.json` 结构调整

这样可以在不重新打包客户端的前提下，接入不同平台或替换适配脚本。

## 总体架构

通知主链路：

`生成待办 / 追加待办 / 完成待办 / 删除待办`
-> `TodoController`
-> `TodoEventBus.publish(event)`
-> 事件处理器
- `ScriptEventHandler`：当前已实现
- `WebhookEventHandler`：协议预留
- `CustomEventHandler`：扩展点预留

其中：

- `TodoController` 只在本地持久化成功后发布事件
- `TodoStore` 仍只负责本地待办读写
- `TodoBindingStore` 独立保存外部平台绑定，不进入 `TodoItem`

## 事件类型

支持 4 类待办生命周期事件：

- `created`
- `appended`
- `completed`
- `deleted`

触发规则：

- `save_analysis_result()` 创建待办时发布 `created`
- `save_analysis_result()` 追加待办时发布 `appended`
- `complete_todo()` 成功后发布 `completed`
- `delete_todo()` 成功后发布 `deleted`

普通编辑保存 `update_todo()` 不触发外部通知。

删除动作特殊处理：

- 删除前先读取待办快照
- 删除成功后再发布 `deleted`
- 因此处理器仍能拿到删除前的完整内容

## 事件模型

主程序发送给处理器的标准 JSON 顶层字段：

- `event_id`
- `event_type`
- `occurred_at`
- `scenario`
- `todo_id`
- `todo_snapshot`
- `delta`
- `bindings`

示例：

```json
{
  "event_id": "40cbfbe0-7cd4-4a8e-8f29-458c63da4f0f",
  "event_type": "appended",
  "occurred_at": "2026-04-09T12:30:00",
  "scenario": "工单待办助手",
  "todo_id": "c17c7b3a-3fdf-4dc4-9a2f-425eeced31d3",
  "todo_snapshot": {
    "id": "c17c7b3a-3fdf-4dc4-9a2f-425eeced31d3",
    "title": "上传失败",
    "status": "open",
    "summary_fields": {
      "group_name": "客户群",
      "environment": "生产",
      "product_line": "文档中台",
      "ticket_type": "排查类"
    },
    "current_summary": "客户反馈上传失败，需要排查。",
    "created_at": "2026-04-09T12:00:00",
    "updated_at": "2026-04-09T12:30:00",
    "timeline": []
  },
  "delta": {
    "timeline_event": {
      "id": "evt-1",
      "timestamp": "2026-04-09T12:30:00",
      "kind": "analysis",
      "scenario": "工单待办助手",
      "content": "客户补充上传时提示 500。",
      "attachments": []
    }
  },
  "bindings": [
    {
      "todo_id": "c17c7b3a-3fdf-4dc4-9a2f-425eeced31d3",
      "integration_id": "company-platform",
      "external_id": "TK-10001",
      "external_url": "https://platform.example.com/tickets/TK-10001",
      "created_at": "2026-04-09T12:01:00",
      "updated_at": "2026-04-09T12:20:00",
      "last_event_id": "prev-event-id",
      "last_event_type": "created",
      "last_sync_status": "ok:created",
      "metadata": {},
      "deleted_locally": false
    }
  ]
}
```

## 字段语义

### `todo_snapshot`

包含当前待办完整快照：

- `id`
- `title`
- `status`
- `summary_fields`
- `current_summary`
- `created_at`
- `updated_at`
- `timeline`

### `delta`

只描述本次变化：

- `created`：`timeline_event` 为首条时间线
- `appended`：`timeline_event` 为本次新增时间线
- `completed`：`{"status_change":{"from":"open","to":"done"}}`
- `deleted`：`{"deleted":true}`

### `bindings`

当前待办已有的外部绑定列表，至少包含：

- `integration_id`
- `external_id`
- `external_url`

如果当前还没有任何外部绑定，则返回空列表。

## 已实现处理器

### `ScriptEventHandler`

当前已实现的处理器类型为 `script`。

主程序行为：

- 从 `~/.aica/integrations.json` 读取启用的 integration
- 将事件 JSON 写入脚本 `stdin`
- 读取脚本 `stdout` 作为 JSON 回执
- 将脚本 `stderr` 只作为日志

配置示例：

```json
{
  "todo_event_integrations": [
    {
      "id": "company-platform",
      "enabled": true,
      "type": "script",
      "command": "C:/tools/aica-sync/sync_todo.exe",
      "args": [],
      "cwd": "C:/tools/aica-sync",
      "timeout_seconds": 8,
      "env": {
        "PLATFORM_BASE_URL": "https://platform.example.com/api",
        "PLATFORM_TOKEN": "your-token"
      }
    }
  ]
}
```

脚本输入：

- `stdin`: UTF-8 JSON，内容为完整 `TodoDomainEvent`

脚本输出：

- `stdout`: UTF-8 JSON 回执
- `stderr`: 可选日志
- 退出码 `0`: 视为执行成功
- 非 `0`: 视为失败，不影响本地待办操作

回执字段：

- `ok`
- `action`
- `integration_id`
- `external_id`
- `external_url`
- `message`
- `metadata`

回执示例：

```json
{
  "ok": true,
  "action": "created",
  "integration_id": "company-platform",
  "external_id": "TK-10001",
  "external_url": "https://platform.example.com/tickets/TK-10001",
  "message": "created",
  "metadata": {
    "priority": "P2"
  }
}
```

## 预留处理器

本期未实现，但协议已预留：

### `WebhookEventHandler`

建议语义：

- 请求体直接发送 `TodoDomainEvent` JSON
- 响应体字段与 script 回执保持一致

### `CustomEventHandler`

预留给未来扩展：

- 公司内部 SDK
- 本地代理服务
- 消息队列
- 其他自定义执行器

## externalId 绑定规则

绑定关系保存在：

- `~/.aica/todo_bindings.json`

每条 binding 的唯一键：

- `todo_id + integration_id`

结构示例：

```json
[
  {
    "todo_id": "c17c7b3a-3fdf-4dc4-9a2f-425eeced31d3",
    "integration_id": "company-platform",
    "external_id": "TK-10001",
    "external_url": "https://platform.example.com/tickets/TK-10001",
    "created_at": "2026-04-09T12:01:00",
    "updated_at": "2026-04-09T12:30:00",
    "last_event_id": "40cbfbe0-7cd4-4a8e-8f29-458c63da4f0f",
    "last_event_type": "appended",
    "last_sync_status": "ok:updated",
    "metadata": {},
    "deleted_locally": false
  }
]
```

统一规则：

- 任意事件回执只要返回合法 `external_id`
- 主程序都执行 binding 的创建或更新

具体语义：

- `created` 回执返回 `external_id`
  - 创建或更新 binding
  - 这是首选路径
- `created` 成功但不返回 `external_id`
  - 视为本次通知成功
  - 不创建有效 binding
  - 会保留一条仅含同步状态的本地记录，便于追踪
- `appended / completed / deleted` 首次返回 `external_id`
  - 允许补建 binding
- 已有 binding 且后续回执未返回 `external_id`
  - 不清空已有 binding
  - 仅刷新 `last_event_* / last_sync_status`

## 无 externalId 时的处理

如果事件处理成功，但回执没有 `external_id`：

- 本次事件仍可视为通知成功
- 主程序不自动猜测平台记录
- 主程序不会创建有效 binding
- 主程序会保留同步状态记录，方便后续排查
- 后续是否继续处理由外部脚本自己决定

这可以避免错误绑定到错误的平台工单。

## 未绑定事件的默认策略

对 `appended / completed / deleted` 三类事件，主程序默认只会发送给“已存在有效 binding”的 integration。

如果某个 integration 还没有 `external_id`：

- 主程序默认跳过该 integration
- 记录 `skipped:missing_binding`
- 不自动猜测平台记录
- 不自动补建平台工单

这样可以避免把未绑定待办误更新到错误的外部记录。

## 删除语义

本地删除成功后：

- `deleted` 事件会发送给外部处理器
- 若该待办已有 binding，则 binding 会保留最后同步状态
- 可标记 `deleted_locally=true`

这样后续仍能做排查或审计，不会因为本地待办删除而丢失外部关联信息。

## 错误处理

当前通知采用“尽力而为”模式：

- 外部脚本失败不影响本地待办创建、追加、完成、删除
- 非 `0`、超时、非法 JSON 只记录同步状态
- 不做持久化重试

## 与未来元数据查询方案的兼容性

本期方案不会阻碍后续查元数据，原因是：

- `externalId` 独立存储，没有混入 `TodoItem`
- integration 配置与处理器边界已经建立
- 后续做主数据查询时，可以直接复用 `integration_id + external_id`

未来若要增加“查产品线 / 项目元数据”，只需新增：

- 独立的 lookup 或 enrichment 调用层
- 独立的元数据存储
- UI 读取并展示这些元数据

无需回退本期的事件通知和 binding 设计。

## 最小脚本示例

```python
import json
import sys

event = json.load(sys.stdin)

if event["event_type"] == "created":
    response = {
        "ok": True,
        "action": "created",
        "external_id": "TK-10001",
        "external_url": "https://platform.example.com/tickets/TK-10001",
        "message": "created"
    }
else:
    response = {
        "ok": True,
        "action": "updated",
        "message": "updated"
    }

print(json.dumps(response, ensure_ascii=False))
```
