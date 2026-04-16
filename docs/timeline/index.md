# Timeline Agent System - Entry Point (Read This First)

## 📌 文档说明

本目录包含 timeline 重构与 Agent 能力扩展的核心设计文档。

这些文档不是独立存在的，请**严格按照阅读顺序理解**，否则会产生错误实现。

---

## 📖 阅读顺序（必须遵守）

### 1️⃣ timeline-architecture.md

👉 先读这个

说明：

* timeline 的核心模型
* event / task / command / result 的关系
* 系统如何扩展

这是整个系统的“数据与结构基础”。

---

### 2️⃣ timeline-card-spec.md

👉 第二个读

说明：

* 所有卡片的设计规范
* UI 结构约束
* BaseTimelineCard 规范

这是“视觉与组件约束层”。

---

### 3️⃣ agent-command-system.md

👉 最后读

说明：

* 指令体系设计
* Agent 执行流程
* 结果结构规范

这是“能力扩展层”。

---

## 🧠 设计分层（必须理解）

本系统分为三层：

### ① 数据层（Architecture）

* TimelineEvent
* Task
* Command
* Result

👉 定义“系统怎么运作”

---

### ② 展示层（Card System）

* BaseTimelineCard
* DefaultTimelineCard
* LogAnalysisTaskCard
* LogAnalysisResultCard

👉 定义“用户看到什么”

---

### ③ 能力层（Agent System）

* LogAnalysisAgent
* Future Agents（summary / handoff / etc）

👉 定义“系统能做什么”

---

## ⚠️ 强约束（必须遵守）

### 1. 不允许破坏现有卡片

* DefaultTimelineCard = 当前已有跟进/反馈卡片
* 样式与行为必须保持不变

---

### 2. 不允许写死逻辑

禁止：

* 根据 content 判断类型
* 在 timeline 渲染中写死 if/else 逻辑

必须：

* 使用 event_type
* 使用 Card Mapper

---

### 3. 不允许耦合结构

必须保持分离：

* timeline event ≠ task
* task ≠ UI
* UI ≠ agent

---

### 4. 不允许一次性设计

本次实现必须支持未来扩展：

* /总结
* /转研发
* /生成回复
* /环境排查

---

## 🧩 本次实现范围

当前阶段只需要实现：

* timeline 架构重构
* Card Mapper 机制
* BaseTimelineCard
* DefaultTimelineCard（兼容）
* LogAnalysisTaskCard
* LogAnalysisResultCard

---

## 🚫 禁止事项

❌ 不允许：

* 重写整个 timeline UI
* 修改现有普通卡片
* 把日志分析逻辑写进 UI
* 用样式 hack 实现多卡片

---

## 🎯 最终目标

构建一个：

👉 可扩展的 timeline + command + agent 系统

使未来新增能力时：

* 不需要重构 timeline
* 不需要修改已有卡片
* 只需新增模块即可

---

## 🧠 一句话理解

timeline 不再是“记录列表”，而是：

👉 **Agent 执行的可视化容器**
