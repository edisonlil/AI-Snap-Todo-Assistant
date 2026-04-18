# Timeline Card Design Spec

## 1. Design Goal

目标是把 timeline 卡片体系做成一套可长期扩展的显示规范，而不是一次性的样式拼装。

必须同时满足：

* 不同类型卡片视觉统一
* 不同能力卡片互不污染
* timeline 主渲染层稳定
* 新增能力时只新增卡片与映射，不再重构 timeline

---

## 2. Global Strategy

### 2.1 Container Policy

所有 timeline 卡片遵循：

* 统一外壳 + 类型微差

含义：

* 所有卡片共享统一的容器基础规范
* 不同类型只允许通过状态色、局部提示块、内容分区做差异
* 不允许每种卡片各自发明一套容器风格

---

### 2.2 Default Card Compatibility

`DefaultTimelineCard` 是兼容卡片。

要求：

* 保持当前结构不变
* 保持当前样式不变
* 保持当前行为不变

因此：

* `DefaultTimelineCard` 继承这份规范的接口与上下文约束
* 但不强制包进新的 Base 容器壳层

新卡片必须严格基于 `BaseTimelineCard` 实现。

---

### 2.3 Action Strategy

动作区统一采用：

* 轻量文本动作

不采用：

* 实体按钮式操作面板
* 大面积胶囊按钮堆叠

原因：

* timeline card 是信息容器，不是控制台面板
* 动作要轻，不打断阅读流

---

## 3. Unified Card Structure

所有新卡片统一使用以下结构：

### Header

必须承载：

* 时间
* 类型标签
* 状态标签（可选）

---

### Title / Summary

必须承载：

* 卡片标题
* 一句摘要或说明（可选）

要求：

* 标题必须让用户一眼知道这张卡片是什么
* 摘要只做轻说明，不重复正文

---

### Body

主体内容区。

允许：

* 自由分区
* 局部说明块
* 结构化列表
* 状态提示

不允许：

* 纯靠颜色区分信息层级
* 把 Body 做成复杂操作面板

---

### Action Row

动作区用于：

* 查看结果
* 查看过程
* 查看原因
* 复制内容

统一规则：

* 动作数量控制在 1 到 3 个
* 主动作靠前
* 危险动作靠后
* 动作统一使用文本链接样式

---

### Expandable Section

展开区是可选区域。

适用于：

* 过程详情
* 失败原因
* 补充信息
* 证据片段

统一规则：

* 默认收起
* 展开区样式统一
* 展开信息是补充层，不抢主内容层级

---

## 4. BaseTimelineCard Responsibilities

所有新卡片必须基于：

```ts
BaseTimelineCard
```

`BaseTimelineCard` 负责统一：

* spacing tokens
* typography tokens
* container radius / padding / border
* header 结构
* status pill 位置
* action row 样式
* expandable section 样式

`BaseTimelineCard` 不负责：

* 限制 body 的具体布局
* 写死某类业务逻辑
* 强制默认卡片重写外壳

---

## 5. Immutable vs Variable Rules

### 5.1 Immutable

以下内容对所有新卡片必须一致：

* 外层圆角体系
* 外边距与内边距节奏
* 边框厚度规则
* 标题 / 正文 / 辅助文字字号层级
* Header 内时间与类型标签布局
* 状态 pill 的位置与尺寸体系
* Action Row 文本样式
* Expandable Section 容器样式

---

### 5.2 Variable

以下内容允许按卡片类型变化：

* Body 内容结构
* 是否存在状态标签
* 是否存在展开区
* 内容是否分区
* 局部提示块样式

---

## 6. Status Spec

统一状态模型：

* `running`
* `success`
* `failed`

统一状态色语义：

* `running` -> 蓝色
* `success` -> 绿色
* `failed` -> 红色

约束：

* 状态色主要作用于 pill、提示文案、局部强调元素
* 不允许整卡大面积重色覆盖
* 状态是辅助识别，不是视觉主角

---

## 7. Card-Specific Rules

### 7.1 DefaultTimelineCard

用于：

* 普通反馈
* 跟进
* 结论

要求：

* 完整保留现有结构
* 完整保留现有样式
* 完整保留现有编辑与附件行为

---

### 7.2 LogAnalysisTaskCard

用于：

* `/分析日志` 触发后的任务事件

Header：

* 时间
* 类型：日志分析任务
* 状态 pill

Body：

* `running`：命令文本 + 当前步骤 + 轻量 loading
* `success`：已生成分析结果
* `failed`：失败原因一句话

Action Row：

* `running`：查看分析过程
* `success`：查看结果
* `failed`：查看原因

Expandable Section：

* `running`：过程步骤
* `failed`：失败详情

---

### 7.3 LogAnalysisResultCard

用于：

* 日志分析完成后的结果事件

Header：

* 时间
* 类型：日志分析结果
* 状态 pill（成功态）

Body 必须按区块展示：

* 已分析材料
* 关键发现
* 初步判断
* 建议下一步

Action Row：

* 复制结果
* 预留后续动作信号

要求：

* 结果卡不能退化成一段长纯文本
* 分区必须独立可读、可复制

---

## 8. Export Constraint

所有卡片的最终信息结构必须满足：

* 不依赖交互也能理解
* 信息层级清晰
* 分区稳定
* 复制与导出时仍可保留结构语义

---

## 9. Design Principle

* 强结构，弱装饰
* 强结果，弱过程
* 状态轻提示，不打断阅读
* 卡片是能力结果容器，不是操作面板

---

## 10. Implementation Notes

新增卡片时只允许做以下动作：

1. 新增 event type
2. 新增 payload schema
3. 新增 card component
4. 在 mapper 中注册

不允许：

* 修改 timeline 主渲染逻辑
* 修改已有默认卡片结构
* 把能力逻辑写死在 UI 中
