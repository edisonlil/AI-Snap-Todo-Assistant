# 功能点匹配接口集成说明

## 目标

本文档说明当前仓库里“工单管理 -> 外部功能点匹配接口”的实际集成方式，帮助你判断现在应该怎么接入自己的外部接口，以及哪些地方需要改代码。

这份文档只覆盖“功能点匹配”能力，不覆盖外部工单同步脚本。两者是两条不同链路。

## 当前实现位置

当前仓库已经内置了功能点自动补全能力，核心代码在以下文件：

- `src/aica/config.py`
- `src/aica/ticket_enrichment.py`
- `src/aica/todo_controller.py`
- `src/aica/main.py`

对应职责如下：

- `config.py`
  - 定义功能点接口配置结构 `FeaturePointProviderConfig`
- `ticket_enrichment.py`
  - 定义外部功能点提供器 `HttpFeaturePointProvider`
  - 定义保存工单时的自动补全服务 `TicketEnrichmentService`
- `todo_controller.py`
  - 在工单更新时调用补全服务
- `main.py`
  - 根据配置构建补全服务并注入控制器

## 与外部工单同步的区别

仓库里有两套“对外集成”能力，容易混淆：

1. 外部工单事件同步
- 代码入口：`src/aica/todo_events.py`
- 用途：把工单的 created、updated、completed 等事件发给外部平台
- 配置文件：`~/.aica/integrations.json`

2. 功能点匹配接口
- 代码入口：`src/aica/ticket_enrichment.py`
- 用途：在编辑保存工单时，调用外部接口自动匹配 `feature_point`
- 配置文件：`~/.aica/config.json`

如果你的需求是“根据产品线 + 问题描述，从外部接口匹配功能点”，应该接第二条链路，不是 `todo_events.py`。

## 当前调用链路

当前功能点匹配是在“工单详情保存”时触发的，链路如下：

```text
工单详情保存
-> main.py::_on_todo_detail_saved()
-> TodoController.update_todo()
-> TicketEnrichmentService.enrich_for_update()
-> HttpFeaturePointProvider.resolve()
-> 外部 HTTP 接口
-> 回填 summary_fields.feature_point
```

也就是说：

- 新建工单时不会主动调用功能点接口
- 编辑工单并保存时，如果满足条件，会自动调用外部接口
- 自动匹配结果会写回 `summary_fields.feature_point`

## 触发条件

功能点接口不是每次保存都调用，当前逻辑在 `TicketEnrichmentService._should_refresh_feature_point()` 中。

只有满足下面条件时才会请求外部接口：

- `product_line` 有值
- `current_summary` 对应的问题描述有值
- 当前 `feature_point` 为空
  - 或者当前 `feature_point_source == "auto"`，并且产品线/问题描述发生了变化

不会自动覆盖的情况：

- 用户手工改过功能点
- 即 `feature_point_source == "manual"`

这意味着当前设计是：

- 自动填充可以补空值
- 手工修改优先级高于自动匹配

## 配置方式

功能点匹配接口配置在 `~/.aica/config.json`，结构来自 `FeaturePointProviderConfig`。

配置示例：

```json
{
  "ticket_enrichment": {
    "feature_point": {
      "enabled": true,
      "provider": "http",
      "base_url": "https://your-domain/api/feature-point/match",
      "api_key": "your-api-key",
      "timeout_seconds": 5
    }
  }
}
```

字段说明：

- `enabled`
  - 是否启用功能点匹配
- `provider`
  - 当前仅内置 `http`
- `base_url`
  - 外部接口地址
- `api_key`
  - 可选，会同时写入 `Authorization: Bearer ...` 和 `X-API-Key`
- `timeout_seconds`
  - 请求超时时间，最小会被修正为 `1`

## 当前请求格式

当前 `HttpFeaturePointProvider.resolve()` 发送的是 `POST` 请求。

请求头：

```http
Content-Type: application/json
Authorization: Bearer <api_key>
X-API-Key: <api_key>
```

说明：

- `api_key` 为空时，不会带 `Authorization` 和 `X-API-Key`
- `Content-Type` 固定是 `application/json`

请求体固定为：

```json
{
  "product_line": "产品线",
  "problem_desc": "问题描述"
}
```

其中：

- `product_line` 来自工单字段 `summary_fields.product_line`
- `problem_desc` 来自工单字段 `current_summary`

## 当前响应解析规则

当前代码对返回格式做了兼容解析，优先读取以下字段：

1. 顶层字段

```json
{
  "feature_point": "导出模块"
}
```

或：

```json
{
  "featurePoint": "导出模块"
}
```

2. `data` 对象内字段

```json
{
  "data": {
    "feature_point": "导出模块"
  }
}
```

或：

```json
{
  "data": {
    "featurePoint": "导出模块"
  }
}
```

3. `candidates` 列表中的首个可用值

```json
{
  "candidates": [
    {
      "feature_point": "导出模块"
    }
  ]
}
```

也支持：

```json
{
  "candidates": [
    {
      "featurePoint": "导出模块"
    }
  ]
}
```

以及：

```json
{
  "candidates": [
    {
      "name": "导出模块"
    }
  ]
}
```

状态字段读取规则：

- 优先取 `status`
- 否则取 `code`
- 否则取 `message`
- 否则回退为 HTTP 状态码字符串

## 成功后的回填行为

接口调用成功且解析出功能点后，会执行：

```text
summary_fields.feature_point = 返回值
summary_fields.feature_point_source = "auto"
```

如果接口请求失败或返回无法解析：

- 不会阻断工单保存
- 只是不回填功能点
- 错误会记录到 `errors` 列表中

因此当前行为是“弱依赖”：

- 外部接口异常不会影响主流程保存
- 只是自动补全失效

## 现阶段最适合的接入方式

如果你们的外部接口已经存在，先判断它属于哪一种：

### 情况 1：接口入参与当前实现一致

接口要求：

- `POST`
- JSON body
- 参数名就是 `product_line` 和 `problem_desc`
- 返回里能提供 `feature_point`

这种情况最简单，只需要配置：

- `ticket_enrichment.feature_point.enabled = true`
- `base_url`
- `api_key`

不需要改代码。

### 情况 2：接口入参不同

例如对方接口要求：

- 参数名叫 `productLine`
- 参数名叫 `problemDesc`
- 需要 `tenant_id`
- 需要额外 header

这种情况需要修改：

- `src/aica/ticket_enrichment.py`
- 主要改 `HttpFeaturePointProvider.resolve()`

例如把请求体从：

```json
{
  "product_line": "...",
  "problem_desc": "..."
}
```

改成：

```json
{
  "productLine": "...",
  "problemDesc": "...",
  "tenantId": "..."
}
```

如果还需要更多配置项，建议同步扩展：

- `src/aica/config.py` 中的 `FeaturePointProviderConfig`

### 情况 3：接口出参不同

例如对方返回：

```json
{
  "result": {
    "name": "导出模块"
  }
}
```

或：

```json
{
  "records": [
    {
      "label": "导出模块"
    }
  ]
}
```

这种情况需要修改：

- `src/aica/ticket_enrichment.py`
- 主要改 `_extract_feature_point_value()`

建议做法是继续保留现有兼容逻辑，再补充你们自己的解析分支，避免影响已有行为。

## 如果你想把匹配时机提前

当前只在“编辑保存工单”时触发。

如果你希望在“新建工单后立刻自动匹配功能点”，可以考虑两种方案：

1. 在 `save_analysis_result()` 创建新工单后，再走一次 enrichment
2. 在 `TodoStore.create_todo_from_analysis()` 前后补一层 enrichment

更推荐方案 1：

- 业务层更清晰
- 不污染存储层
- 和当前 `update_todo()` 的设计一致

## 如果你想把匹配结果展示得更明显

当前结果已经会保存在工单字段里，控制面板和详情面板能读到 `feature_point`。

如果你还想增强显示，可以考虑：

- 在工单详情页增加“自动匹配/手工填写”来源标识
- 在保存后给出“已自动匹配功能点”的轻提示
- 在无法匹配时显示“未匹配到功能点”

这部分是 UI 增强，不影响当前主链路。

## 调试建议

如果你要联调外部接口，建议先检查这几个点：

1. 配置是否生效
- `~/.aica/config.json` 中 `ticket_enrichment.feature_point.enabled` 是否为 `true`
- `base_url` 是否正确

2. 工单字段是否满足触发条件
- `product_line` 是否为空
- `current_summary` 是否为空
- `feature_point_source` 是否已经是 `manual`

3. 外部接口是否返回 JSON
- 当前实现要求 `response.json()`
- 非 JSON 会被判定为失败

4. 返回结构是否能被当前解析逻辑识别
- 是否存在 `feature_point`
- 或 `featurePoint`
- 或 `data.feature_point`
- 或 `candidates[].name`

## 推荐改造原则

如果后续你们会接多个不同平台的功能点接口，建议不要一直往 `HttpFeaturePointProvider` 里堆 if/else。

更合适的做法是：

1. 保留 `FeaturePointProvider` 协议
2. 增加多个 provider 实现
- 例如 `HttpFeaturePointProvider`
- `CompanyFeaturePointProvider`
- `ScriptFeaturePointProvider`
3. 在 `build_feature_point_provider()` 里按 `provider` 字段分发

这样比把所有平台差异都塞进一个类里更稳。

## 最小接入结论

基于当前仓库，实现外部功能点匹配接口接入的最小方案是：

1. 在 `~/.aica/config.json` 里配置 `ticket_enrichment.feature_point`
2. 确保外部接口能接收：
   - `product_line`
   - `problem_desc`
3. 确保外部接口返回：
   - `feature_point`
   - 或当前解析函数支持的等价字段
4. 在工单详情里编辑并保存，验证 `feature_point` 是否被自动回填

如果你们接口格式和当前实现不一致，改动重点只在一个文件：

- `src/aica/ticket_enrichment.py`

通常只需要调整两处：

- `HttpFeaturePointProvider.resolve()`
- `_extract_feature_point_value()`

## 相关文件索引

- `src/aica/config.py`
- `src/aica/main.py`
- `src/aica/ticket_enrichment.py`
- `src/aica/todo_controller.py`
- `tests/test_ticket_enrichment.py`

