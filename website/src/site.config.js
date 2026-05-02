export const siteMeta = {
  brand: "Chattodo",
  badge: "桌面 AI 工单待办助手",
  description:
    "Chattodo 把群聊、报错截图、日志材料和处理结论组织成可持续跟进的工单待办，适合技术支持、售后、实施和交付团队。",
};

export const homeContent = {
  hero: {
    label: "截图取证 -> AI 识别 -> 工单时间线 -> 知识归档",
    title: "把零散问题现场整理成可跟进的工单。",
    summary:
      "Chattodo 面向技术支持、售后、实施和交付团队，把日常群聊、报错截图、日志材料和处理结论串成一条可追踪的时间线。",
    primaryCta: "查看快速开始",
    primaryHref: "./docs/getting-started.html",
    secondaryCta: "阅读完整文档",
    secondaryHref: "./docs/index.html",
  },
  productDemo: [
    {
      title: "截图取证",
      body: "全局快捷键捕获群聊、报错、后台页面和日志片段。",
    },
    {
      title: "AI 识别",
      body: "提取标题、摘要、项目、产品线、证据和本次新增跟进。",
    },
    {
      title: "工单时间线",
      body: "新问题创建待办，已有问题追加到同一条处理记录。",
    },
    {
      title: "知识归档",
      body: "完成后沉淀结论、附件和可复用的知识库 Markdown。",
    },
  ],
  stats: [
    { value: "7 步", label: "从截图到知识归档" },
    { value: "4 类团队", label: "支持、售后、实施、交付" },
    { value: "本地留痕", label: "时间线、附件、结论、同步状态" },
  ],
  values: [
    {
      title: "解决信息散落",
      body: "客户群消息、报错截图、日志材料和研发回复不再散落在聊天工具、表格和临时文档里。",
    },
    {
      title: "保留排查上下文",
      body: "每次截图、补充材料、沟通和阶段总结都进入同一条时间线，交接时不用重新拼故事。",
    },
    {
      title: "让 AI 服务现场流程",
      body: "AI 不是单次问答，而是参与识别、总结、检索、日志分析和发客户/发研发摘要。",
    },
  ],
  workflow: [
    {
      step: "01",
      title: "捕获问题",
      body: "用全局快捷键截图，框选或标注群聊、报错、日志和后台页面。",
    },
    {
      step: "02",
      title: "AI 识别",
      body: "提取问题标题、摘要、项目、产品线、模块、严重程度和关键证据。",
    },
    {
      step: "03",
      title: "生成工单待办",
      body: "未选中待办时创建新工单，已选中时追加到当前工单。",
    },
    {
      step: "04",
      title: "时间线跟进",
      body: "持续记录沟通、排查、反馈、截图、日志和结论变化。",
    },
    {
      step: "05",
      title: "辅助排查",
      body: "生成排查建议、相似案例检索、阶段总结和日志分析结果。",
    },
    {
      step: "06",
      title: "补全业务上下文",
      body: "关联项目、环境、账号、OTP 和功能点，让问题更容易定位。",
    },
    {
      step: "07",
      title: "沉淀复用",
      body: "维护最终结论，导出图文方案，归档到知识库并生成索引。",
    },
  ],
  audiences: [
    {
      title: "技术支持",
      body: "从客户群、报错截图和日志材料中快速整理问题上下文。",
    },
    {
      title: "售后团队",
      body: "持续跟踪客户问题，避免信息散落在聊天记录里。",
    },
    {
      title: "实施 / 交付",
      body: "按项目管理环境、账号、跟进记录和最终结论。",
    },
    {
      title: "研发协同人员",
      body: "把排查过程整理成适合转研发、复盘和知识库沉淀的材料。",
    },
  ],
  capabilities: [
    {
      title: "截图采集与标注",
      body: "支持全局热键、框选、文字和箭头标注，也支持多图连续采集。",
    },
    {
      title: "工单识别与追加",
      body: "AI 识别结构化字段，保存为新工单或追加到当前选中的工单时间线。",
    },
    {
      title: "详情侧栏与附件",
      body: "维护标题、摘要、字段、项目、环境入口、时间线、附件和最终结论。",
    },
    {
      title: "辅助排查与案例检索",
      body: "结合当前摘要、时间线和材料生成建议，并检索可参考历史案例。",
    },
    {
      title: "日志分析 Agent",
      body: "在时间线中输入 /分析日志 并附加材料，即可创建异步分析任务。",
    },
    {
      title: "项目环境与账号",
      body: "维护项目主数据、环境入口、登录信息、OTP 和群聊自动关联。",
    },
    {
      title: "知识归档",
      body: "完成后把背景、排查过程、证据、方案和附件沉淀为 Markdown。",
    },
    {
      title: "外部平台同步",
      body: "通过脚本接收待办生命周期事件，连接内部工单系统、表格或 Webhook。",
    },
  ],
  scenarios: [
    "客户群里出现报错截图，需要马上形成可跟进事项。",
    "同一问题连续多天排查，需要保留每次沟通和日志材料。",
    "实施人员频繁登录不同客户环境，需要快速复制入口和账号信息。",
    "问题处理完成后，需要沉淀结论并给后续同事复用。",
  ],
  downloadCards: [
    {
      title: "下载安装",
      body: "官网保留正式安装包入口结构，后续替换为真实发布地址即可。",
      href: "./docs/installation.html#download",
      cta: "查看安装说明",
    },
    {
      title: "从主流程开始",
      body: "先跑通截图、AI 识别、新建或追加待办、时间线跟进和导出总结。",
      href: "./docs/getting-started.html",
      cta: "打开快速开始",
    },
  ],
};

export const faqItems = [
  {
    question: "首次使用前必须准备什么？",
    answer:
      "需要至少一个可访问的模型供应商接口和对应 API Key，并在控制面板中完成任务模型绑定。",
  },
  {
    question: "截图后一定会创建新工单吗？",
    answer:
      "不是。未选中待办时创建新工单；已选中待办时会把新截图和分析结果追加到当前工单时间线。",
  },
  {
    question: "配置文件和本地数据存在哪里？",
    answer:
      "默认保存在本地配置目录中，包括配置、待办数据、Prompt 调试快照、反馈记录和部分本地材料。",
  },
  {
    question: "日志分析会阻塞主界面吗？",
    answer:
      "不会。日志分析 Agent 会创建异步任务，执行过程中显示状态，完成后自动生成结果卡片。",
  },
  {
    question: "项目环境和账号信息适合放在哪里？",
    answer:
      "可以在项目管理和环境管理中维护全局环境、项目环境、访问地址、用户名、密码和 OTP 信息。",
  },
  {
    question: "知识归档会包含哪些内容？",
    answer:
      "归档文档会围绕工单元信息、问题背景、排查过程、关键证据、解决方案、附件和产品线标签组织。",
  },
  {
    question: "能接入公司内部工单系统吗？",
    answer:
      "可以通过外部脚本接收标准事件 JSON，再由脚本对接内部工单系统、表格、Webhook 或其他平台。",
  },
];

export const docsNav = [
  { key: "index", title: "文档首页", href: "index.html" },
  { key: "getting-started", title: "快速开始", href: "getting-started.html" },
  { key: "installation", title: "安装与启动", href: "installation.html" },
  { key: "configuration", title: "模型配置", href: "configuration.html" },
  { key: "capture-todos", title: "截图与工单", href: "capture-todos.html" },
  { key: "timeline-attachments", title: "时间线与附件", href: "timeline-attachments.html" },
  { key: "assist-troubleshooting", title: "辅助排查", href: "assist-troubleshooting.html" },
  { key: "log-analysis", title: "日志分析 Agent", href: "log-analysis.html" },
  { key: "project-environments", title: "项目环境与账号", href: "project-environments.html" },
  { key: "knowledge-archive", title: "知识归档", href: "knowledge-archive.html" },
  { key: "external-sync", title: "外部同步", href: "external-sync.html" },
  { key: "faq", title: "常见问题", href: "faq.html" },
];

const productWorkflow = [
  { step: "01", title: "截图取证", body: "捕获群聊、报错、日志和后台页面。" },
  { step: "02", title: "AI 识别", body: "提取工单字段、摘要、证据和关键线索。" },
  { step: "03", title: "创建 / 追加工单", body: "根据当前选择决定新建或追加到时间线。" },
  { step: "04", title: "时间线跟进", body: "记录沟通、排查、反馈和附件材料。" },
  { step: "05", title: "辅助排查", body: "生成建议、检索相似案例、分析日志。" },
  { step: "06", title: "结论沉淀", body: "维护最终结论并导出图文方案。" },
  { step: "07", title: "知识归档", body: "归档 Markdown 并按产品线生成索引。" },
];

export const docsPages = {
  index: {
    title: "文档首页",
    eyebrow: "完整用户文档",
    summary:
      "这套文档按 Chattodo 的真实工作流组织，帮助团队从安装配置走到工单跟进、辅助排查、知识沉淀和外部同步。",
    sections: [
      {
        id: "what-is-chattodo",
        title: "Chattodo 是什么",
        blocks: [
          {
            type: "html",
            html:
              "<p>Chattodo 是一款面向技术支持、售后、实施和交付团队的桌面 AI 工单待办助手。它把日常群聊、报错截图、日志材料和处理结论组织成可持续跟进的工单待办。</p>",
          },
          {
            type: "workflow",
            items: productWorkflow,
          },
        ],
      },
      {
        id: "best-for",
        title: "适合谁使用",
        blocks: [
          {
            type: "list",
            items: [
              "技术支持：快速从客户群、报错截图、日志材料中整理问题上下文。",
              "售后团队：持续跟踪客户问题，避免信息散落在聊天记录里。",
              "实施 / 交付：按项目管理环境、账号、跟进记录和最终结论。",
              "研发协同人员：把排查过程整理成更适合转研发、复盘或知识库沉淀的材料。",
            ],
          },
        ],
      },
      {
        id: "reading-order",
        title: "推荐阅读顺序",
        blocks: [
          {
            type: "steps",
            items: [
              "先阅读《快速开始》，跑通第一次截图到工单的闭环。",
              "再阅读《模型配置》，确认截图分析、日志分析和方案导出使用的模型。",
              "然后阅读《截图与工单》《时间线与附件》，建立日常记录规范。",
              "最后按团队成熟度接入日志分析、项目环境、知识归档和外部同步。",
            ],
          },
        ],
      },
    ],
  },
  "getting-started": {
    title: "快速开始",
    eyebrow: "先跑通主流程",
    summary:
      "第一次使用建议只做一件事：把截图取证、AI 识别、新建或追加工单、时间线跟进和阶段总结跑通。",
    sections: [
      {
        id: "prepare",
        title: "开始前准备",
        blocks: [
          {
            type: "list",
            items: [
              "确认 Chattodo 已安装并可正常启动。",
              "准备可访问的模型供应商接口和 API Key。",
              "确认截图热键没有和常用软件冲突。",
              "准备一段真实问题现场，例如客户群消息、报错页面或日志截图。",
            ],
          },
        ],
      },
      {
        id: "first-loop",
        title: "第一次完整体验",
        blocks: [
          {
            type: "steps",
            items: [
              "打开控制面板，配置至少一个模型供应商。",
              "为截图分析任务绑定支持视觉能力的模型。",
              "使用全局快捷键截图并按需添加文字或箭头标注。",
              "检查 AI 识别出的标题、摘要、项目、产品线和证据。",
              "未选中待办时保存为新工单。",
              "再次截图，选中刚才的工单并保存为追加记录。",
              "打开详情侧栏，查看时间线、附件和当前摘要。",
            ],
          },
        ],
      },
      {
        id: "new-vs-append",
        title: "何时新建，何时追加",
        blocks: [
          {
            type: "html",
            html:
              "<p>判断标准不是截图来自哪个群，而是它是否属于同一个问题上下文。同一个客户问题、同一条排查线索或同一次处理过程，建议留在同一条时间线里。</p>",
          },
          {
            type: "list",
            items: [
              "全新客户诉求、全新报错、全新排查方向：新建工单。",
              "后续截图、客户补充反馈、研发回复、日志材料：追加到原工单。",
              "已完成问题再次出现：根据团队习惯选择重开或新建，并在摘要中注明关联关系。",
            ],
          },
        ],
      },
      {
        id: "team-rollout",
        title: "团队落地建议",
        blocks: [
          {
            type: "list",
            items: [
              "先选择 1 到 2 个高频问题场景试用。",
              "统一约定产品线、模块、项目和严重程度的填写口径。",
              "把阶段总结作为对外同步和内部交接的标准出口。",
              "待主流程稳定后，再接入日志分析、知识归档和外部同步。",
            ],
          },
        ],
      },
    ],
  },
  installation: {
    title: "安装与启动",
    eyebrow: "成品软件安装说明",
    summary:
      "把 Chattodo 当作一款桌面软件分发。安装文档只关注系统要求、下载安装、首次启动和必要权限。",
    sections: [
      {
        id: "requirements",
        title: "系统要求",
        blocks: [
          {
            type: "list",
            items: [
              "Windows 10 或更高版本。",
              "macOS 13 或更高版本，当前以 Apple Silicon 为主。",
              "可访问模型供应商接口。",
              "如需截图热键和系统级快捷操作，需要授予系统权限。",
            ],
          },
        ],
      },
      {
        id: "download",
        title: "下载安装",
        blocks: [
          {
            type: "callout",
            tone: "warm",
            title: "下载入口说明",
            text: "当前官网保留正式安装包下载入口结构，后续替换为真实发布地址即可。",
          },
          {
            type: "steps",
            items: [
              "从官网或团队内部发布渠道获取安装包。",
              "按系统安装向导完成安装。",
              "首次启动后打开控制面板。",
              "配置模型、截图热键和任务模型绑定。",
            ],
          },
        ],
      },
      {
        id: "first-launch",
        title: "首次启动检查",
        blocks: [
          {
            type: "list",
            items: [
              "控制面板可以正常打开。",
              "截图热键可被系统注册。",
              "截图分析任务已绑定可用模型。",
              "本地数据目录可正常写入。",
            ],
          },
        ],
      },
      {
        id: "mac-permission",
        title: "macOS 权限",
        blocks: [
          {
            type: "html",
            html:
              "<p>首次在 macOS 使用全局截图热键时，系统可能要求为 Chattodo 开启“辅助功能”和“输入监听”权限。权限未开启时应用可以启动，但热键可能不会立即生效。</p>",
          },
        ],
      },
    ],
  },
  configuration: {
    title: "模型配置",
    eyebrow: "供应商、任务绑定与本地目录",
    summary:
      "Chattodo 把不同 AI 任务绑定到不同模型。截图分析需要视觉能力，日志分析、方案导出和上下文摘要可按材料类型选择模型。",
    sections: [
      {
        id: "config-path",
        title: "配置文件位置",
        blocks: [
          {
            type: "html",
            html:
              "<p>运行配置保存在本地配置目录中。首次启动或任务模型绑定缺失时，Chattodo 会引导你补齐供应商、API Key 和模型信息。</p>",
          },
        ],
      },
      {
        id: "providers",
        title: "供应商与模型",
        blocks: [
          {
            type: "list",
            items: [
              "当前支持 `openai_compatible` 与 `gemini` 两类供应商。",
              "常见供应商示例包括 SiliconFlow、MiniMax、阿里云百炼、Google Gemini。",
              "每个供应商需要配置 `api_key`、超时时间和可用模型列表。",
              "模型能力标签主要包括 `vision_chat` 与 `text_chat`。",
            ],
          },
        ],
      },
      {
        id: "bindings",
        title: "任务模型绑定",
        blocks: [
          {
            type: "list",
            items: [
              "`analysis`：截图分析，通常需要视觉模型。",
              "`log_analysis`：日志分析，可根据材料类型选择视觉或文本模型。",
              "`plan_export`：方案导出，通常使用文本模型。",
              "`context_summary`：上下文摘要压缩，通常使用文本模型。",
            ],
          },
        ],
      },
      {
        id: "local-data",
        title: "本地数据目录",
        blocks: [
          {
            type: "list",
            items: [
              "运行配置：供应商、API Key、任务模型绑定和超时设置。",
              "截图分析规则：用于指导截图内容识别与字段提取。",
              "Prompt 调试快照：用于排查和优化模型提示词效果。",
              "本地待办数据：保存工单、时间线、字段和处理状态。",
              "反馈记录：保存用户反馈文本。",
              "反馈图片：保存反馈时附带的图片材料。",
            ],
          },
        ],
      },
    ],
  },
  "capture-todos": {
    title: "截图与工单",
    eyebrow: "问题捕获与工单识别",
    summary:
      "截图是 Chattodo 的入口。它负责把客户群、报错现场、后台页面和日志片段带进工单工作流。",
    sections: [
      {
        id: "capture",
        title: "截图捕获",
        blocks: [
          {
            type: "list",
            items: [
              "Windows 默认截图快捷键是 `Alt+A`。",
              "macOS 默认截图快捷键是 `Command+Shift+A`。",
              "截图后可以框选关键区域，也可以添加文字和箭头标注。",
              "适合捕获客户群消息、系统报错、后台页面、日志片段和监控告警。",
            ],
          },
        ],
      },
      {
        id: "multi-image",
        title: "多图采集",
        blocks: [
          {
            type: "html",
            html:
              "<p>当一次截图无法说明完整问题时，可以使用多图采集，把多张截图合并交给 AI 分析。多图适合连续聊天记录、前后对比页面和多段日志证据。</p>",
          },
        ],
      },
      {
        id: "ai-fields",
        title: "AI 提取字段",
        blocks: [
          {
            type: "list",
            items: [
              "问题标题与当前问题摘要。",
              "本次新增跟进内容。",
              "群聊名称、项目 / 客户信息、产品线。",
              "模块、问题类型、严重程度。",
              "证据、关键线索和待确认事项。",
            ],
          },
        ],
      },
      {
        id: "save-mode",
        title: "保存为新工单或追加记录",
        blocks: [
          {
            type: "list",
            items: [
              "未选择待办：保存为新工单，并形成首条时间线记录。",
              "已选择待办：追加到现有工单，并形成新增时间线记录。",
              "保存前建议检查标题、摘要和项目字段，避免同一问题被拆散。",
            ],
          },
        ],
      },
    ],
  },
  "timeline-attachments": {
    title: "时间线与附件",
    eyebrow: "持续跟进同一事项",
    summary:
      "时间线是 Chattodo 的核心记录方式。每次沟通、排查、截图、日志分析和结论变化都应该留下可追踪记录。",
    sections: [
      {
        id: "panel",
        title: "浮动待办面板",
        blocks: [
          {
            type: "list",
            items: [
              "查看当前仍在处理的问题。",
              "选择或取消当前工单。",
              "打开工单详情。",
              "快速完成、重开或删除工单。",
              "展开 / 收起列表，置顶面板，拖动调整位置。",
            ],
          },
        ],
      },
      {
        id: "detail",
        title: "工单详情",
        blocks: [
          {
            type: "list",
            items: [
              "维护标题、当前摘要和结构化字段。",
              "查看项目关联状态和环境入口。",
              "记录时间线、附件和最终结论。",
              "把阶段性处理结果整理成适合发客户或发研发的摘要。",
            ],
          },
        ],
      },
      {
        id: "attachments",
        title: "附件材料",
        blocks: [
          {
            type: "html",
            html:
              "<p>每条时间线都可以附加图片、日志、压缩包或其他文件。建议按“证据截图、原始日志、处理结论、外部回复”这样的类别保存，后续复盘会更轻松。</p>",
          },
        ],
      },
      {
        id: "final-conclusion",
        title: "最终结论",
        blocks: [
          {
            type: "list",
            items: [
              "完成前补齐最终处理结论。",
              "保留关键证据和附件。",
              "确认是否需要导出图文方案。",
              "满足条件后归档到知识库。",
            ],
          },
        ],
      },
    ],
  },
  "assist-troubleshooting": {
    title: "辅助排查",
    eyebrow: "建议、案例与阶段总结",
    summary:
      "辅助排查会结合当前摘要、时间线和已有材料，帮助团队整理下一步动作、历史参考和对外沟通摘要。",
    sections: [
      {
        id: "questions",
        title: "它适合回答什么",
        blocks: [
          {
            type: "list",
            items: [
              "当前问题最可能的方向是什么？",
              "下一步应该检查哪些信息？",
              "哪些线索值得优先确认？",
              "是否有类似历史案例？",
              "该如何整理给研发或客户？",
            ],
          },
        ],
      },
      {
        id: "case-search",
        title: "相似案例检索",
        blocks: [
          {
            type: "html",
            html:
              "<p>系统会根据当前工单内容生成检索 query，搜索历史案例或知识库内容，并对结果去重、排序和评分。高相关案例会展示匹配原因和可参考结论。</p>",
          },
        ],
      },
      {
        id: "stage-summary",
        title: "阶段总结",
        blocks: [
          {
            type: "list",
            items: [
              "整理当前已知背景。",
              "归纳已经做过的排查动作。",
              "突出仍需确认的问题。",
              "生成发客户摘要或发研发摘要。",
            ],
          },
        ],
      },
    ],
  },
  "log-analysis": {
    title: "日志分析 Agent",
    eyebrow: "异步日志排查任务",
    summary:
      "日志分析 Agent 适合处理日志、压缩包和截图材料。它在时间线中创建异步任务，不阻塞主界面。",
    sections: [
      {
        id: "create-task",
        title: "创建日志分析任务",
        blocks: [
          {
            type: "steps",
            items: [
              "打开需要排查的工单详情。",
              "在时间线输入 `/分析日志`。",
              "附加日志文件、压缩包或截图。",
              "提交后等待任务进入执行队列。",
              "完成后查看自动生成的分析结果卡片。",
            ],
          },
        ],
      },
      {
        id: "result",
        title: "分析结果通常包含",
        blocks: [
          {
            type: "list",
            items: [
              "阶段总结。",
              "关键日志线索。",
              "可能原因。",
              "建议排查路径。",
              "发研发摘要。",
              "发客户摘要。",
              "经验回流摘要。",
            ],
          },
        ],
      },
      {
        id: "usage-notes",
        title: "使用建议",
        blocks: [
          {
            type: "list",
            items: [
              "尽量上传原始日志，不要只上传截断后的片段。",
              "如果日志很多，优先补充发生时间、客户操作和报错现象。",
              "分析结果建议作为排查参考，最终结论仍应由处理人员确认。",
            ],
          },
        ],
      },
    ],
  },
  "project-environments": {
    title: "项目环境与账号",
    eyebrow: "业务上下文管理",
    summary:
      "项目和环境信息让工单不再只是一个问题描述，而是带有客户、系统入口、账号和项目生命周期的上下文。",
    sections: [
      {
        id: "projects",
        title: "项目管理",
        blocks: [
          {
            type: "list",
            items: [
              "新建和编辑项目。",
              "导入项目清单。",
              "维护项目别名和项目等级。",
              "维护跟进开始日期和支持结束日期。",
              "标识项目是否过保。",
              "根据群聊名称自动关联工单。",
            ],
          },
        ],
      },
      {
        id: "environments",
        title: "环境入口",
        blocks: [
          {
            type: "list",
            items: [
              "维护全局环境和项目环境。",
              "保存环境访问地址。",
              "在工单详情中快速打开环境。",
              "复制登录信息，减少重复查找。",
            ],
          },
        ],
      },
      {
        id: "accounts",
        title: "账号与 OTP",
        blocks: [
          {
            type: "list",
            items: [
              "维护用户名和密码。",
              "支持 OTP 动态验证码。",
              "可从二维码或剪贴板导入 OTP。",
              "处理客户环境登录时减少上下文切换。",
            ],
          },
        ],
      },
      {
        id: "feature-point",
        title: "功能点自动匹配",
        blocks: [
          {
            type: "html",
            html:
              "<p>当工单中已有产品线和问题描述时，系统可以调用外部功能点接口自动匹配对应功能点。自动匹配不会覆盖用户手动填写的功能点，接口异常也不会阻断工单保存。</p>",
          },
        ],
      },
    ],
  },
  "knowledge-archive": {
    title: "知识归档",
    eyebrow: "结论沉淀与复用",
    summary:
      "问题完成后，Chattodo 可以把处理过程沉淀为知识库 Markdown，让经验从一次性处理变成可检索资产。",
    sections: [
      {
        id: "before-archive",
        title: "归档前检查",
        blocks: [
          {
            type: "list",
            items: [
              "最终处理结论已维护。",
              "关键截图、日志和压缩包已作为附件保留。",
              "问题背景和排查过程足够清楚。",
              "产品线、项目和功能点信息尽量补齐。",
            ],
          },
        ],
      },
      {
        id: "archive-content",
        title: "归档内容",
        blocks: [
          {
            type: "list",
            items: [
              "工单元信息。",
              "问题背景。",
              "排查过程。",
              "关键证据。",
              "解决方案。",
              "附件材料。",
              "产品线标签。",
            ],
          },
        ],
      },
      {
        id: "wiki-index",
        title: "Wiki 索引",
        blocks: [
          {
            type: "html",
            html:
              "<p>系统可以按产品线生成 Wiki 索引，方便后续从产品域或问题类型切入检索。建议团队定期回看高频问题，把归档质量较好的工单整理为标准案例。</p>",
          },
        ],
      },
    ],
  },
  "external-sync": {
    title: "外部同步",
    eyebrow: "脚本集成与平台对接",
    summary:
      "Chattodo 支持通过外部脚本同步待办生命周期事件，由脚本负责对接公司内部工单系统、表格、Webhook 或其他平台。",
    sections: [
      {
        id: "events",
        title: "会触发同步的事件",
        blocks: [
          {
            type: "list",
            items: [
              "本地工单创建。",
              "工单追加新时间线。",
              "工单更新。",
              "工单完成。",
              "工单删除。",
              "用户手动同步。",
            ],
          },
        ],
      },
      {
        id: "payload",
        title: "事件数据",
        blocks: [
          {
            type: "html",
            html:
              "<p>系统会把标准事件 JSON 发送给外部脚本。脚本可以根据事件内容创建或更新公司内部平台中的记录。</p>",
          },
          {
            type: "code",
            language: "json",
            code:
              '{\n  "event_type": "todo.updated",\n  "todo": {\n    "title": "客户环境登录报错",\n    "summary": "已追加日志材料，等待进一步确认"\n  }\n}',
          },
        ],
      },
      {
        id: "binding",
        title: "回传外部绑定",
        blocks: [
          {
            type: "html",
            html:
              "<p>同步结果可以回传 <code>external_id</code> 和 <code>external_url</code>。Chattodo 会保存绑定关系，方便后续继续同步到同一个外部记录。</p>",
          },
        ],
      },
      {
        id: "script-docs",
        title: "进阶说明",
        blocks: [
          {
            type: "list",
            items: [
              "事件字段和脚本行为可参考 `docs/todo-event-integration.md`。",
              "脚本集成方式可参考 `docs/script-integration-guide.md`。",
              "接入前建议先在测试平台验证事件幂等和失败重试策略。",
            ],
          },
        ],
      },
    ],
  },
  faq: {
    title: "常见问题",
    eyebrow: "高频问题",
    summary:
      "这些问题覆盖品牌命名、首次配置、截图保存、日志分析、知识归档和外部同步。",
    sections: [
      {
        id: "common-questions",
        title: "常见问题列表",
        blocks: [
          {
            type: "faq",
            items: faqItems,
          },
        ],
      },
    ],
  },
};
