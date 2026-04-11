# AICA Database Schema Reference

Database path: `D:\Users\Admin\.aica\aica.db`

## Tables

### todos
主表，存储待办事项。

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| title | TEXT | 待办标题 |
| current_summary | TEXT | 当前摘要 |
| group_name | TEXT | 关联群聊名称 |
| environment | TEXT | 环境（测试环境/生产环境/未知） |
| ticket_type | TEXT | 工单类型（操作类/排查类/咨询类等） |
| status | TEXT | 状态：`open` / `done` |
| created_at | TEXT | ISO时间戳 |
| updated_at | TEXT | ISO时间戳 |

### todo_timeline_events
待办时间线，记录每次跟进/分析。

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| todo_id | TEXT FK | 关联todos.id |
| timestamp | TEXT | 事件时间 |
| kind | TEXT | `analysis`（自动分析）/ `manual`（手动跟进） |
| scenario | TEXT | 场景标签 |
| content | TEXT | 事件详细内容 |

### projects
项目信息。

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| project_name | TEXT | 项目名称 |
| customer_name | TEXT | 客户名称 |
| task_order_no | TEXT | 任务单号 |
| project_level | TEXT | 项目等级 |

### project_group_aliases
项目与群聊的映射关系。

## 常用 group_name 值
路桥集团文档中台对接、路桥集团、广汽、中烟集团、厦门市监局、宝洁、广州四三九九信息科技有限公司--WPS
