export const siteMeta = {
  brand: "Chattodo",
  badge: "截图驱动的 AI 待办工作台",
  description:
    "Chattodo 把问题截图、聊天记录、日志线索和排查结论整理成可追踪的待办事项，帮助支持、测试和研发团队减少信息搬运。",
};

export const homeContent = {
  hero: {
    label: "Capture -> Analyze -> Track -> Resolve",
    title: "把一张问题截图，变成可执行的待办闭环",
    summary:
      "Chattodo 面向每天处理问题、工单和环境上下文的团队。截图后由 AI 提炼背景、结论和下一步动作，再沉淀到待办、时间线和知识库里。",
    primaryCta: "查看使用文档",
    primaryHref: "./docs/getting-started.html",
    secondaryCta: "了解核心能力",
    secondaryHref: "#features",
  },
  stats: [
    { value: "7 步", label: "从截图捕获到归档复盘的完整工作流" },
    { value: "4 类", label: "待办、日志、环境、知识库统一管理" },
    { value: "本地优先", label: "运行配置和工作数据默认保存在本机" },
  ],
  values: [
    {
      title: "少写重复描述",
      body: "截图、选中文本和上下文会被整理成标题、摘要、现象、原因和下一步，不再反复手工补充问题背景。",
    },
    {
      title: "排查过程不断档",
      body: "每一次分析、补充、附件和结论都进入时间线，团队可以从同一个问题继续推进，而不是重新翻聊天记录。",
    },
    {
      title: "把经验留在团队里",
      body: "已解决的问题可以归档成 Markdown 知识材料，为后续相似问题、脚本集成和复盘提供可复用入口。",
    },
  ],
  workflow: [
    {
      step: "01",
      title: "捕获现场",
      body: "记录异常页面、报错、聊天线索和操作环境。",
    },
    {
      step: "02",
      title: "AI 结构化",
      body: "生成标题、摘要、关键线索、怀疑方向和建议动作。",
    },
    {
      step: "03",
      title: "进入工作台",
      body: "按项目、状态、优先级和环境追踪待办。",
    },
    {
      step: "04",
      title: "持续补充",
      body: "追加日志分析、附件、阶段结论和人工判断。",
    },
    {
      step: "05",
      title: "协助排障",
      body: "围绕单个待办收敛下一步排查路径。",
    },
    {
      step: "06",
      title: "同步外部系统",
      body: "把待办变化推送给工单、脚本或团队工具。",
    },
    {
      step: "07",
      title: "沉淀知识",
      body: "把最终结论、根因和处理方式留给团队复用。",
    },
  ],
  audiences: [
    {
      title: "技术支持",
      body: "把客户截图和沟通信息快速整理成内部可跟进事项。",
    },
    {
      title: "测试与 QA",
      body: "把复现步骤、环境信息和验证结果串成清晰时间线。",
    },
    {
      title: "研发与排障同学",
      body: "把日志、上下文、根因分析和后续动作留在同一条记录里。",
    },
    {
      title: "团队负责人",
      body: "看清问题积压、处理阶段和高频故障类型，方便复盘改进。",
    },
  ],
  capabilities: [
    {
      title: "截图生成待办",
      body: "从图片和选中文本中提炼问题描述，自动生成更适合跟进的待办卡片。",
    },
    {
      title: "详情时间线",
      body: "保留分析结果、人工补充、附件和结论，问题处理过程可回看。",
    },
    {
      title: "日志分析 Agent",
      body: "围绕待办收集日志线索，输出可执行的排查方向和阶段摘要。",
    },
    {
      title: "项目环境管理",
      body: "把项目、环境、账号和 OTP 相关信息绑定到具体问题上下文。",
    },
    {
      title: "知识归档",
      body: "将解决方案沉淀为 Markdown，形成可搜索、可复用的团队资料。",
    },
    {
      title: "外部同步",
      body: "用事件和 Webhook 连接脚本、工单系统或自定义自动化流程。",
    },
  ],
  scenarios: [
    "客户发来一张报错截图，需要快速变成支持团队可跟进的事项。",
    "测试同学发现偶现问题，需要把环境、复现线索和验证结果持续补齐。",
    "研发处理线上故障，需要把日志分析和阶段结论沉淀下来。",
    "团队希望把重复问题整理成知识库，减少下一次排查成本。",
  ],
  downloadCards: [
    {
      title: "先创建一条待办",
      body: "从截图、AI 摘要到进入时间线，先完成一次完整的问题记录。",
      href: "./docs/getting-started.html",
      cta: "打开快速开始",
    },
    {
      title: "了解功能模块",
      body: "继续查看待办、时间线、排障、环境和知识归档的使用方式。",
      href: "./docs/index.html",
      cta: "浏览文档中心",
    },
  ],
};

export const faqItems = [
  {
    question: "Chattodo 会把数据保存在哪里？",
    answer:
      "默认运行数据保存在本机用户目录下的 Chattodo/AICA 配置和数据文件中。真实 API Key 不应提交到仓库。",
  },
  {
    question: "必须接入云端模型吗？",
    answer:
      "应用通过配置接入 OpenAI 兼容接口或其他支持的模型服务。具体可用提供方取决于当前配置。",
  },
  {
    question: "它和普通待办工具有什么区别？",
    answer:
      "Chattodo 关注问题处理场景：截图捕获、AI 摘要、日志分析、环境绑定、时间线和知识归档在同一个流程里。",
  },
  {
    question: "适合非技术团队使用吗？",
    answer:
      "可以用于收集和追踪问题，但它的核心优势在技术支持、测试、研发排障等需要保留上下文的工作里。",
  },
];

export const docsNav = [
  { key: "index", title: "文档首页", href: "index.html" },
  { key: "getting-started", title: "快速开始", href: "getting-started.html" },
  { key: "features", title: "功能概览", href: "features.html" },
  { key: "installation", title: "安装与下载", href: "installation.html" },
  { key: "configuration", title: "配置", href: "configuration.html" },
  { key: "capture-todos", title: "截图创建待办", href: "capture-todos.html" },
  { key: "timeline-attachments", title: "时间线与附件", href: "timeline-attachments.html" },
  { key: "assist-troubleshooting", title: "辅助排障", href: "assist-troubleshooting.html" },
  { key: "log-analysis", title: "日志分析", href: "log-analysis.html" },
  { key: "project-environments", title: "项目环境", href: "project-environments.html" },
  { key: "knowledge-archive", title: "知识归档", href: "knowledge-archive.html" },
  { key: "external-sync", title: "外部同步", href: "external-sync.html" },
  { key: "faq", title: "常见问题", href: "faq.html" },
];

function simplePage(title, eyebrow, summary, sections) {
  return { title, eyebrow, summary, sections };
}

export const docsPages = {
  index: simplePage("文档中心", "Documentation", "从日常问题处理出发，按 Chattodo 的完整使用流程组织。", [
    {
      id: "overview",
      title: "你可以从这里开始",
      blocks: [
        {
          type: "workflow",
          items: homeContent.workflow.slice(0, 5),
        },
      ],
    },
    {
      id: "areas",
      title: "主要模块",
      blocks: [
        {
          type: "list",
          items: ["截图创建待办", "待办详情和时间线", "日志分析 Agent", "项目环境管理", "知识归档和外部同步"],
        },
      ],
    },
  ]),
  "getting-started": simplePage("快速开始", "Getting Started", "用一条真实问题走完 Chattodo 的基础使用流程。", [
    {
      id: "first-todo",
      title: "创建第一条待办",
      blocks: [
        {
          type: "steps",
          items: [
            "打开 Chattodo 后，准备好要记录的问题截图或选中文本。",
            "使用截图入口捕获问题现场，必要时补充一句背景说明。",
            "等待 AI 生成待办标题、问题摘要、关键线索和建议动作。",
            "检查内容是否准确，再保存为待办。",
          ],
        },
      ],
    },
    {
      id: "follow-up",
      title: "继续跟进问题",
      blocks: [
        {
          type: "list",
          items: [
            "在工作台里按项目、状态或关键词找到待办。",
            "进入详情页查看摘要、时间线和已有结论。",
            "把新的截图、日志、验证结果或人工判断继续补充到时间线。",
            "需要进一步分析时，使用辅助排障或日志分析功能收敛下一步。",
          ],
        },
      ],
    },
    {
      id: "finish",
      title: "处理完成后",
      blocks: [
        {
          type: "list",
          items: [
            "补充最终原因和处理结论。",
            "把状态更新为已完成。",
            "对重复出现的问题，归档成知识材料，方便下次直接复用。",
          ],
        },
      ],
    },
  ]),
  features: simplePage("功能概览", "Features", "了解 Chattodo 如何把截图、待办、排障和知识沉淀接到同一条线上。", [
    {
      id: "capabilities",
      title: "核心能力",
      blocks: [
        {
          type: "workflow",
          items: homeContent.capabilities.map((item, index) => ({
            step: String(index + 1).padStart(2, "0"),
            title: item.title,
            body: item.body,
          })),
        },
      ],
    },
  ]),
  installation: simplePage("安装与下载", "Install", "获取 Chattodo 并完成首次启动准备。", [
    {
      id: "download",
      title: "下载与启动",
      blocks: [
        {
          type: "list",
          items: ["下载适合当前系统的版本。", "首次启动后进入配置页面。", "确认模型服务、快捷键和数据目录后即可开始使用。"],
        },
      ],
    },
  ]),
  configuration: simplePage("配置", "Configuration", "配置模型、运行目录和项目环境。", [
    {
      id: "runtime",
      title: "基础配置",
      blocks: [
        { type: "list", items: ["配置模型服务。", "设置截图和快捷键习惯。", "按团队需要维护项目、环境和账号信息。"] },
      ],
    },
  ]),
  "capture-todos": simplePage("截图创建待办", "Capture", "把截图、文本和上下文转换成可追踪事项。", [
    {
      id: "flow",
      title: "创建流程",
      blocks: [
        { type: "steps", items: ["截取问题现场。", "补充必要说明。", "让 AI 生成待办摘要。", "进入工作台继续跟进。"] },
      ],
    },
  ]),
  "timeline-attachments": simplePage("时间线与附件", "Timeline", "用时间线保留每一次分析、补充和结论。", [
    {
      id: "usage",
      title: "适合记录什么",
      blocks: [{ type: "list", items: ["日志片段", "截图附件", "阶段结论", "验证结果", "最终根因"] }],
    },
  ]),
  "assist-troubleshooting": simplePage("辅助排障", "Assist", "围绕单个待办生成下一步排查建议。", [
    {
      id: "questions",
      title: "建议提问方式",
      blocks: [{ type: "list", items: ["给出当前现象。", "补充已验证内容。", "让 AI 明确下一步检查项。"] }],
    },
  ]),
  "log-analysis": simplePage("日志分析", "Log Analysis", "把日志线索整理成阶段摘要和排查方向。", [
    {
      id: "result",
      title: "输出内容",
      blocks: [{ type: "list", items: ["关键异常", "时间顺序", "可能根因", "建议验证动作"] }],
    },
  ]),
  "project-environments": simplePage("项目环境", "Environments", "把项目、环境和账号信息绑定到问题上下文。", [
    {
      id: "manage",
      title: "管理对象",
      blocks: [{ type: "list", items: ["项目", "环境", "账号", "访问说明", "OTP 辅助信息"] }],
    },
  ]),
  "knowledge-archive": simplePage("知识归档", "Archive", "把解决过的问题整理成团队可复用资料。", [
    {
      id: "content",
      title: "归档内容",
      blocks: [{ type: "list", items: ["问题背景", "根因", "处理步骤", "验证方式", "相关附件"] }],
    },
  ]),
  "external-sync": simplePage("外部同步", "Sync", "用事件和 Webhook 连接外部工具。", [
    {
      id: "events",
      title: "常见事件",
      blocks: [{ type: "list", items: ["待办创建", "状态更新", "结论更新", "归档完成"] }],
    },
  ]),
  faq: simplePage("常见问题", "FAQ", "快速了解 Chattodo 的定位、数据和使用边界。", [
    {
      id: "common",
      title: "问题列表",
      blocks: [{ type: "faq", items: faqItems }],
    },
  ]),
};
