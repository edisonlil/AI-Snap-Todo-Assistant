# Agent Command System Design

## 1. 目标

支持未来：

* /分析日志
* /总结
* /转研发
* /生成回复
* /环境排查

---

## 2. 命令模型

```ts
type Command = {
  name: string
  input_schema: object
  output_schema: object
}
```

---

## 3. 执行流程

用户输入：

/分析日志 request_id=xxx

↓

生成：

* log_analysis_command event

↓

创建 task

↓

执行 agent

↓

生成：

* log_analysis_result event

---

## 4. 结果结构（必须结构化）

```json
{
  "analyzed_materials": [],
  "findings": "",
  "judgment": "",
  "next_steps": ""
}
```

---

## 5. 解耦原则

必须分离：

* command（触发）
* task（执行）
* result（产出）
* timeline（展示）

---

## 6. 日志分析 Agent

必须通过接口：

```ts
interface LogAnalysisAgent {
  analyze(input): ResultPayload
}
```

支持未来替换模型

---

## 7. 扩展能力

新增指令只需：

* 新 command
* 新 agent
* 新 result schema
* 新 card

---

## 8. 核心理念

不要把能力写进 UI
UI 只是结果展示层
