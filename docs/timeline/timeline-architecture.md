# Timeline Architecture Design

## 1. 设计目标

timeline 不再是简单记录流，而是：

* 事件流（Event Stream）
* 指令容器（Command Container）
* Agent 执行载体

目标：

* 支持多种指令（日志分析 / 总结 / 转研发 / 环境排查）
* 不同指令拥有不同卡片表现
* timeline 本体不再被反复重构

---

## 2. 核心模型

### 2.1 Timeline Event

```ts
type TimelineEvent = {
  id: string
  event_type: string
  content: string
  payload?: any
  task_id?: string | null
  created_at: string
}
```

---

### 2.2 Task Model

```ts
type Task = {
  id: string
  task_type: string
  status: 'queued' | 'running' | 'success' | 'failed'
  current_step?: string
  error_message?: string
}
```

---

### 2.3 Command Event

```ts
type CommandPayload = {
  command_name: string
  raw_command: string
  args: object
}
```

---

### 2.4 Result Event

```ts
type ResultPayload = {
  source_command: string
  result_kind: string
  result_payload: object
}
```

---

## 3. 事件类型（当前）

* follow_up
* conclusion
* log_analysis_command
* log_analysis_result

---

## 4. 渲染机制

通过 Card Mapper：

```ts
switch(event.event_type) {
  case 'log_analysis_command':
    return LogAnalysisTaskCard
  case 'log_analysis_result':
    return LogAnalysisResultCard
  default:
    return DefaultTimelineCard
}
```

---

## 5. 扩展原则

新增能力必须只做：

1. 新增 event_type
2. 新增 payload schema
3. 新增卡片组件
4. 注册 mapper

禁止：

* 修改 timeline 主渲染逻辑
* 修改已有卡片逻辑

---

## 6. 核心理念

timeline = 能力容器，而不是 UI 列表
