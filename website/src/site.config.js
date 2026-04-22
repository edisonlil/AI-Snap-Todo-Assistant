export const siteMeta = {
  brand: "Chattodo",
  badge: "桌面 AI 待办工作台",
  description:
    "把截图、上下文和后续动作整理成可持续推进的任务，适合技术支持、售后、实施与交付团队。",
  footerNote:
    "当前对外品牌统一使用 Chattodo。部分配置路径、环境变量与本地目录仍沿用历史命名 AICA。",
};

export const homeContent = {
  heroStats: [
    { value: "4 步闭环", label: "截图到可跟进任务" },
    { value: "多模型", label: "支持 openai_compatible / gemini" },
    { value: "本地留痕", label: "时间线、附件与导出" },
  ],
  values: [
    {
      title: "截图进入任务",
      body: "把群聊、报错、工单或日志现场直接带进任务流，不再手工整理一遍再分发。",
    },
    {
      title: "AI 结构化整理",
      body: "自动提取标题、分组、环境、产品线和本次新增跟进内容，减少重复录入。",
    },
    {
      title: "持续跟进同一事项",
      body: "新截图可追加到已有待办，维持连续时间线，而不是制造更多孤立消息。",
    },
    {
      title: "沉淀可交接上下文",
      body: "阶段总结、附件与导出让一线信息变成可复用的交接资产。",
    },
  ],
  features: [
    {
      title: "截图采集与标注",
      body: "支持全局热键、框选和标注，先把信息抓对，再交给 AI 处理。",
      accent: "signal",
    },
    {
      title: "多图合并分析",
      body: "单张截图不够时，可以把多张图一起送入分析，保留完整上下文。",
      accent: "warm",
    },
    {
      title: "待办详情与时间线",
      body: "同一个问题持续沉淀处理经过、附件、结论和同步状态。",
      accent: "paper",
    },
    {
      title: "阶段总结与导出",
      body: "把阶段性处理结果整理成更适合发给同事或客户的结构化输出。",
      accent: "signal",
    },
    {
      title: "项目视角与外部集成",
      body: "从项目组织上下文，并把待办生命周期事件发给外部脚本或平台。",
      accent: "warm",
    },
  ],
  workflow: [
    {
      step: "01",
      title: "截图采集现场",
      body: "截取群聊、报错、工单、日志结果或客户反馈，保留问题发生时的原始证据。",
    },
    {
      step: "02",
      title: "AI 理解并归类",
      body: "模型提取结构化字段与本次新增信息，补齐更适合展示和保存的标题。",
    },
    {
      step: "03",
      title: "新建或追加待办",
      body: "没有选中待办就创建新任务；已经锁定事项就继续追加到原时间线。",
    },
    {
      step: "04",
      title: "持续推进与导出",
      body: "在详情侧栏中更新处理过程、管理附件、生成阶段总结并导出文档。",
    },
  ],
  audiences: [
    "技术支持",
    "售后团队",
    "实施顾问",
    "交付团队",
    "内部协作支持",
  ],
  downloadCards: [
    {
      title: "下载安装",
      body: "面向日常使用场景，安装后即可进入控制面板完成配置并开始使用。",
      href: "./docs/installation.html#download",
      cta: "查看安装说明",
    },
    {
      title: "使用文档",
      body: "从快速开始、配置说明到常见问题，帮助团队以成品软件方式完成落地。",
      href: "./docs/index.html",
      cta: "查看使用文档",
    },
  ],
};

export const faqItems = [
  {
    question: "Chattodo 和 AICA 是什么关系？",
    answer:
      "对外品牌已经统一为 Chattodo，但当前版本内部的配置目录、环境变量和部分文件命名仍保留 AICA 历史前缀。",
  },
  {
    question: "首次使用前必须准备什么？",
    answer:
      "需要至少一个可访问的模型供应商接口和对应的 API Key，首次启动后可在控制面板中完成配置。",
  },
  {
    question: "截图后是一定创建新待办吗？",
    answer:
      "不是。未选中待办时会新建；已选中待办时会把新内容追加到当前事项时间线。",
  },
  {
    question: "配置文件和本地数据存在哪里？",
    answer:
      "默认保存在 `~/.aica/` 目录，包括 `config.json`、待办数据、反馈和调试信息等。",
  },
  {
    question: "支持哪些模型供应商？",
    answer:
      "当前文档明确记录了 `openai_compatible` 与 `gemini` 两类供应商，以及 SiliconFlow、阿里云百炼、MiniMax、Google Gemini 等示例。",
  },
  {
    question: "macOS 上为什么需要额外权限？",
    answer:
      "首次使用全局截图热键时，系统可能要求为 Chattodo 开启“辅助功能”和“输入监听”权限。",
  },
];

export const docsNav = [
  { key: "index", title: "文档首页", href: "index.html" },
  { key: "getting-started", title: "快速开始", href: "getting-started.html" },
  { key: "installation", title: "安装与运行", href: "installation.html" },
  { key: "configuration", title: "配置说明", href: "configuration.html" },
  { key: "features", title: "核心功能", href: "features.html" },
  { key: "faq", title: "常见问题", href: "faq.html" },
];

export const docsPages = {
  index: {
    title: "文档首页",
    eyebrow: "基础用户文档",
    summary:
      "这套文档面向第一次接触 Chattodo 的团队成员，帮助你快速理解产品定位、落地方式和常见工作流。",
    sections: [
      {
        id: "what-is-chattodo",
        title: "Chattodo 是什么",
        blocks: [
          {
            type: "html",
            html:
              "<p>Chattodo 是一款面向 Windows 与 macOS 的桌面 AI 待办工作台。它围绕“截图采集上下文 -> AI 结构化提取 -> 创建或追加待办 -> 持续跟进时间线”设计，适合高频处理客户问题、内部协作事项和复杂问题排查记录的团队。</p>",
          },
          {
            type: "list",
            items: [
              "用全局截图热键快速收集现场信息",
              "自动提取结构化字段和本次新增跟进内容",
              "支持新建待办或追加到已有事项",
              "在浮动面板与详情侧栏中持续跟进任务",
            ],
          },
        ],
      },
      {
        id: "best-for",
        title: "适合谁使用",
        blocks: [
          {
            type: "html",
            html:
              "<p>如果你的日常工作里经常需要把零散聊天、报错和处理动作串起来，Chattodo 会比纯截图工具或纯待办工具更顺手。</p>",
          },
          {
            type: "list",
            items: [
              "技术支持：记录客户问题上下文与处理经过",
              "售后团队：持续跟进同一客户事项，避免消息散落",
              "实施与交付：保留项目推进节点、附件与结论",
              "内部协作：把临时对话沉淀为可交接的任务资产",
            ],
          },
        ],
      },
      {
        id: "doc-map",
        title: "推荐阅读顺序",
        blocks: [
          {
            type: "list",
            items: [
              "先看《快速开始》，建立对核心流程的整体理解",
              "再看《安装与运行》，按你的系统完成本地启动",
              "然后看《配置说明》，准备模型与本地数据目录",
              "最后看《核心功能》和《常见问题》，按团队场景细化使用方式",
            ],
          },
          {
            type: "callout",
            tone: "muted",
            title: "品牌说明",
            text: "当前网站与文档统一使用 Chattodo 品牌；若你在配置路径、目录名或日志中看到 AICA，这是同一产品的历史命名残留。",
          },
        ],
      },
    ],
  },
  "getting-started": {
    title: "快速开始",
    eyebrow: "先跑通主流程",
    summary:
      "第一版建议先把“安装 -> 配置模型 -> 截图分析 -> 新建或追加待办 -> 导出总结”跑通一次，再开始做团队内迁移。",
    sections: [
      {
        id: "prepare",
        title: "开始前准备",
        blocks: [
          {
            type: "list",
            items: [
              "完成 Chattodo 安装并确认应用可正常启动",
              "确认当前机器可访问模型供应商接口",
              "为至少一个供应商填写有效 API Key",
              "预留一个适合自己工作流的截图热键",
            ],
          },
        ],
      },
      {
        id: "first-loop",
        title: "第一次完整体验",
        blocks: [
          {
            type: "list",
            items: [
              "启动应用，确认控制面板可打开",
              "在配置中绑定截图分析任务使用的模型",
              "使用全局热键截取一段真实问题现场",
              "让 AI 生成结构化字段与标题",
              "在未选中待办时保存为新事项",
              "再次截图并在选中状态下追加到同一待办",
              "打开详情页查看时间线、附件与阶段总结",
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
              "<p>Chattodo 的关键价值之一，是帮你把同一事项保留在同一条时间线里。建议把“是否属于同一个待办上下文”作为判断标准，而不是仅看消息是否来自同一群聊。</p>",
          },
          {
            type: "list",
            items: [
              "全新问题、全新客户诉求、全新排查方向：新建待办",
              "原事项的补充截图、后续报错、处理结果、客户反馈：追加到原待办",
              "已经关闭但再次出现的问题：视情况重新打开或新建事项",
            ],
          },
        ],
      },
      {
        id: "team-adoption",
        title: "团队落地建议",
        blocks: [
          {
            type: "list",
            items: [
              "先从 1 到 2 个高频问题场景试用，而不是一次性替换所有工作流",
              "统一约定产品线、环境和群名字段的填写口径",
              "把阶段总结作为对外同步和交接的标准出口",
              "逐步再接入外部脚本或平台同步能力",
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
      "把 Chattodo 当作一款可直接交付给团队使用的桌面软件来看待时，安装文档应该只关注系统要求、下载安装、首次启动和权限提示。",
    sections: [
      {
        id: "requirements",
        title: "系统要求",
        blocks: [
          {
            type: "list",
            items: [
              "Windows 10 或更高版本",
              "macOS 13 或更高版本，当前以 Apple Silicon 为主",
              "可访问模型供应商接口",
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
            title: "交付说明",
            text: "官网可以直接承接正式安装包下载链接；当前版本先保留下载入口与说明结构，后续替换为真实发布地址即可。",
          },
          {
            type: "html",
            html:
              "<p>建议将 Chattodo 作为标准桌面应用分发。用户只需要下载安装包并完成安装，无需接触源码、命令行或构建过程。</p>",
          },
          {
            type: "list",
            items: [
              "从官网下载安装包",
              "按系统安装向导完成安装",
              "首次启动后打开控制面板完成模型与热键配置",
              "使用全局截图热键开始第一次任务闭环",
            ],
          },
        ],
      },
      {
        id: "first-launch",
        title: "首次启动",
        blocks: [
          {
            type: "html",
            html:
              "<p>首次进入 Chattodo 后，建议先打开控制面板检查模型供应商、任务模型绑定、截图热键和图片压缩阈值。若缺少可用的 API Key 或模型绑定，程序会引导你补齐配置。</p>",
          },
        ],
      },
      {
        id: "mac-permission",
        title: "macOS 权限说明",
        blocks: [
          {
            type: "html",
            html:
              "<p>首次在 macOS 使用全局截图热键时，可能需要在“系统设置 > 隐私与安全性”中为 Chattodo 开启“辅助功能”和“输入监听”权限。如果权限尚未开启，应用仍可继续启动，但热键不会立即生效。</p>",
          },
        ],
      },
    ],
  },
  configuration: {
    title: "配置说明",
    eyebrow: "模型、任务绑定与本地目录",
    summary:
      "运行配置默认保存在 `~/.aica/config.json`。虽然官网品牌已改为 Chattodo，但当前内部路径仍沿用 AICA 历史命名。",
    sections: [
      {
        id: "config-path",
        title: "配置文件位置",
        blocks: [
          {
            type: "html",
            html:
              "<p>运行配置默认保存在 <code>~/.aica/config.json</code>。这是当前版本的真实路径，首版文档保持与实际行为一致，不对目录名做伪装。</p>",
          },
          {
            type: "callout",
            tone: "muted",
            title: "历史命名说明",
            text: "如果你在日志、环境变量或本地目录中看到 AICA，这是品牌迁移中的历史命名残留，不代表你下载了另一款产品。",
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
              "当前支持 `openai_compatible` 与 `gemini` 两类供应商",
              "当前可用的供应商示例包括 SiliconFlow、MiniMax、阿里云百炼、Google Gemini",
              "每个供应商需要配置 `api_key`、超时时间以及可用模型列表",
              "模型能力标签当前主要使用 `vision_chat` 与 `text_chat`",
            ],
          },
        ],
      },
      {
        id: "bindings",
        title: "任务模型绑定",
        blocks: [
          {
            type: "html",
            html:
              "<p>Chattodo 把不同任务绑定到不同模型，例如截图分析、日志分析、方案导出与上下文摘要可以分别选择最合适的供应商和模型。</p>",
          },
          {
            type: "list",
            items: [
              "`analysis`：截图分析",
              "`log_analysis`：日志分析",
              "`plan_export`：方案导出",
              "`context_summary`：上下文摘要压缩",
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
              "`~/.aica/config.json`：运行配置",
              "`~/.aica/analysis_rules.json`：截图分析规则",
              "`~/.aica/prompt_debug/`：Prompt 调试快照",
              "`~/.aica/todos.json`：本地待办数据",
              "`~/.aica/feedback/feedback.jsonl`：反馈记录",
              "`~/.aica/feedback/images/`：反馈图片",
            ],
          },
        ],
      },
      {
        id: "migration",
        title: "配置迁移与默认值",
        blocks: [
          {
            type: "list",
            items: [
              "首次运行或任务绑定缺少可用模型时，程序会弹窗引导配置",
              "Windows 默认截图热键是 `Alt+A`",
              "macOS 新建配置默认使用 `Command+Shift+A`",
              "旧版 `config.json` 会在加载时自动迁移到新 schema",
            ],
          },
        ],
      },
    ],
  },
  features: {
    title: "核心功能",
    eyebrow: "产品能力总览",
    summary:
      "下面这些能力构成了 Chattodo 当前的主流程功能，也是官网首页最值得向用户解释清楚的部分。",
    sections: [
      {
        id: "capture",
        title: "截图采集与分析",
        blocks: [
          {
            type: "list",
            items: [
              "支持全局热键截图",
              "截图覆盖层支持框选与标注",
              "可处理单张截图，也可合并多张截图一起分析",
              "AI 可提取工单信息并生成更适合展示和保存的标题",
            ],
          },
        ],
      },
      {
        id: "todo-flow",
        title: "待办创建、追加与详情",
        blocks: [
          {
            type: "list",
            items: [
              "未选中待办时创建新待办",
              "已选中待办时追加到现有待办，并保持时间线连续",
              "支持待办浮动面板与详情侧栏",
              "详情框支持通过顶部标题栏拖拽移动",
            ],
          },
        ],
      },
      {
        id: "timeline",
        title: "时间线、附件与阶段总结",
        blocks: [
          {
            type: "list",
            items: [
              "支持时间线附件上传、预览与导出",
              "支持阶段总结与 Markdown 形式输出",
              "可保留处理经过、日志分析结果和当前结论",
              "适合把一次次沟通沉淀为最终方案或交接材料",
            ],
          },
        ],
      },
      {
        id: "project",
        title: "项目管理与本地持久化",
        blocks: [
          {
            type: "list",
            items: [
              "项目管理面板支持按项目维护待办上下文",
              "项目支持日期选择与项目级别设置",
              "待办数据支持本地持久化",
              "存在反馈采集与 Prompt 调试能力，便于持续优化分析质量",
            ],
          },
        ],
      },
      {
        id: "integration",
        title: "导出与外部集成",
        blocks: [
          {
            type: "list",
            items: [
              "支持导出更适合对外同步的文档内容",
              "支持单实例运行保护，减少多开干扰",
              "支持把待办生命周期事件发送给包外脚本处理",
              "进阶接入能力可以在后续扩展为单独的高级文档区",
            ],
          },
        ],
      },
    ],
  },
  faq: {
    title: "常见问题",
    eyebrow: "首版高频问答",
    summary:
      "下面的问题聚焦产品交付与品牌迁移场景，适合作为首发版 FAQ。",
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
      {
        id: "next-step",
        title: "还想继续深入？",
        blocks: [
          {
            type: "html",
            html:
              "<p>如果你的团队已经准备把 Chattodo 接入更复杂的脚本或平台，可以在后续补充单独的高级接入文档区。首版官网先聚焦标准安装、配置和日常使用流程。</p>",
          },
        ],
      },
    ],
  },
};
