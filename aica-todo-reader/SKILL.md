---
name: aica-todo-reader
description: |
  查询 AICA 工单待办数据库，获取历史待办内容进行总结和分析。数据库路径：D:\Users\Admin\.aica\aica.db。
  触发场景：
  1. 用户要求总结/回顾待办工单（"总结待办"、"最近处理了哪些工单"、"看看最近的问题"）
  2. 用户要求分析特定客户或群聊的工单（"路桥集团最近有什么问题"、"广汽的待办情况"）
  3. 用户要求统计工单数据（"工单统计"、"完成率多少"、"有多少open的"）
  4. 用户要求查看某个具体待办的详情和时间线
  5. 用户提到"AICA"、"aica.db"、"工单数据库"相关内容
---

# AICA 待办读取与分析

从 `D:\Users\Admin\.aica\aica.db` 查询待办数据并生成总结分析。

## 快速使用

运行查询脚本（位于 `scripts/query_todos.py`）：

```bash
# 工单统计概览
python scripts/query_todos.py --action stats --days 30

# 列出所有 open 待办（含时间线事件）
python scripts/query_todos.py --action list --status open --with-events

# 按群聊/客户筛选
python scripts/query_todos.py --action list --group "路桥集团" --with-events

# 查看最近7天更新
python scripts/query_todos.py --action list --days 7 --with-events

# 查看单个待办详情
python scripts/query_todos.py --action detail --todo-id <ID>
```

## 常用参数

| 参数 | 说明 |
|------|------|
| `--action` | `list` / `detail` / `stats` |
| `--status` | `open` 或 `done` |
| `--group` | 按 group_name 模糊匹配 |
| `--days` | 仅查询最近 N 天更新的数据 |
| `--with-events` | 附带时间线事件（用于深度分析） |
| `--limit` | 返回条数上限（默认50） |

## 分析模式

总结分析时，按以下维度组织输出：

1. **概览** — 总数、open/done 比例、近期活跃度
2. **按客户/群聊分组** — 各客户的问题分布
3. **按类型分组** — 排查类 vs 咨询类 vs 操作类
4. **重点问题摘要** — open 状态的待办详细说明
5. **已完成事项回顾** — 近期已关闭的工单清单

## 数据库结构

详见 [references/schema.md](references/schema.md)。
