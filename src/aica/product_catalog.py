"""Local product line and module catalog used by the ticket detail editor."""
from __future__ import annotations

from aica.text_sanitize import sanitize_text

PRODUCT_LINE_ALIASES: dict[str, str] = {
    "私网文档中台": "私有云文档",
    "文档中台": "私有云文档",
    "私网文档中心": "私有云文档",
    "zhongt": "私有云文档",
}

PRODUCT_LINE_MODULE_MAP: dict[str, list[str]] = {
    "PC Office": [
        "PC Office-文字",
        "PC Office-表格",
        "PC Office-演示",
        "PC Office-PDF",
        "PC Office-OFD",
        "KT",
        "MAC特性 & Mac平台RMS",
        "LINUX特性",
        "图片",
        "安全文档",
        "增值应用",
        "专业版 - 安装/卸载/升级/序列号",
        "WPS校对/黑马校对",
        "连接私有云文档相关",
        "Win二次开发",
        "WPS365商业版/教育版-企业专属新特性",
        "WPS365商业版/教育版-Win端二次开发",
        "主框",
        "会员",
        "测试专用",
        "个人版-安装/卸载/升级",
        "专业版vba",
        "jsapi",
        "np插件",
        "Linux二次开发",
        "Linux平台 安装/卸载/升级",
        "RMS",
        "鸿蒙平台特性（C端可复现）",
        "鸿蒙B端特性（仅B端复现、二开/dlp等）",
        "鸿蒙B端特性（RMS）",
    ],
    "公网Web Office": [
        "智能文档（AP）",
        "智能表格（AS）",
        "多维表格（DB）",
        "智能表单（FORM）",
        "公网Web Office-文字",
        "公网Web Office-演示",
        "公网Web Office-表格",
        "公网Web Office-PDF",
        "公网Web Office-OFD",
        "思维导图",
        "流程图",
        "设计",
        "白板",
    ],
    "稻壳": ["稻壳"],
    "WPS灵犀": ["WPS灵犀"],
    "Office云基础": ["分享&协作", "文档管控", "团队服务", "云文档", "云盘", "消息中心"],
    "私有化Web Office": [
        "在线文字",
        "在线表格",
        "在线演示",
        "表单",
        "在线PDF",
        "私有化Web Office-OFD",
        "智能文档",
        "智能表格",
        "多维表格",
        "格式处理",
        "WebServer",
        "金山文档-前端（v5/v6）",
        "云基础",
    ],
    "移动 Office": ["鸿蒙", "Android", "IOS"],
    "统一平台": ["统一平台"],
    "数科产品": ["PC端阅读器V3.0", "PC端阅读器V5.0", "移动端SDK", "OCR客户端", "OCR服务", "轻阅读", "转换服务", "电子签章"],
    "WPS协作（Server）": [
        "通讯录、消息收发、群相关、搜索等",
        "账号登录、官网下载页、安装卸载升级、个人中心、窗口相关、快捷键、水印、数据统计等",
        "协作机器人、协作应用",
        "文档助手、轻审批、人事助手、待办中心等",
        "协作工作台、服务台、企业公告",
        "协作中台",
        "轻打卡",
        "订阅号",
        "客户端JSAPI、DEEPPLINK、二开、零信任",
    ],
    "WPS协作（移动端）": [
        "移动端-通讯录、消息收发、群相关、搜索等",
        "移动端-账号登录、官网下载页、安装卸载升级、个人中心、窗口相关、快捷键、水印、数据统计等",
        "移动端-协作机器人、协作工作台、服务台等，协作端JSAPI，DEEPPLINK",
        "移动端-文档助手、轻审批、人事助手、待办中心等",
        "移动端-企业公告",
        "移动端-协作中台",
        "移动端-轻打卡",
        "移动端-订阅号",
    ],
    "WPS协作（PC/Web端）": [
        "PC/Web端-通讯录、消息收发、群相关、搜索等",
        "PC/Web端-账号登录、官网下载页、安装卸载升级、个人中心、窗口相关、快捷键、水印、数据统计等",
        "PC/Web端-协作机器人、协作工作台、服务台等，协作端JSAPI，DEEPPLINK",
        "PC/Web端-文档助手、轻审批、人事助手、待办中心等",
        "PC/Web端-企业公告",
        "PC/Web端-协作中台",
        "PC/Web端-轻打卡",
        "PC/Web端-订阅号",
    ],
    "WPS会议": ["WPS会议"],
    "WPS邮箱": ["WPS邮箱"],
    "WPS日历": ["WPS日历"],
    "私有云文档": [
        "私有云文档-云文档",
        "管理后台",
        "系统后台",
        "文档中台",
        "应用文档",
        "私有云文档-安全文档",
        "组织架构和通讯录",
        "数据升级",
        "xc小众数据库适配",
        "PO",
        "配置中心（V5/V6）",
        "存储（V5/V6）",
        "H5（V5/V6）",
        "云文档（V3/V4）",
        "部署平台",
        "运维平台",
        "AI中台",
    ],
    "WPSAI": ["AI server-公共问题", "AI server-AIPPT", "AI server-表格AI", "AI server-文字/AI排版/pdf"],
    "工行安全文档": ["工行安全文档"],
    "WPS365开放平台": [
        "solution开放平台",
        "二开-定制",
        "公网开放平台",
        "新open开放平台",
        "应用管理平台",
        "应用开发平台",
        "自研扩展应用",
        "数字员工",
    ],
    "智能文档库": ["智能问答", "搜索", "企业知识库基础模块", "企业知识库智能应用", "入库", "其他"],
    "WPS365企业": [
        "私有云（V7）-AI管理（AIhub）",
        "私有云（V5/V6）-企业管理后台/企业通讯录相关/企业模板",
        "私有云（V5/V6）-许可证授权/订单/权益",
        "企业商业化",
        "企业用户增长",
        "应用生态",
        "企业安全",
        "企业认证-企业",
        "企业认证-教育",
        "企业重名申诉",
        "企业身份",
        "产品体验",
        "增值与行业产品",
        "增值与行业产品-集成助手",
        "数据迁移中心",
    ],
    "WPS365教育": ["专包配置", "教学空间", "WPS教学平台", "内容中台", "教育官网", "KOS考试", "KOS官网"],
    "WPS政务AI平台": ["政务资源库前台", "政务资源库后台", "智能应用", "智能公文", "政务AI平台-内网版"],
    "云平台": ["私有云（V5/V6）-账号/权益", "私有云（V5/V6）-用户组/联系人/openevent/接口鉴权"],
    "公网-云文档基础(服务端)": ["云文档", "企业管控"],
    "WPS政务协作": ["政务协作"],
    "独立Web Office": [
        "独立Web Office-在线文字",
        "独立Web Office-在线表格",
        "独立Web Office-在线演示",
        "独立Web Office-表单",
        "独立Web Office-在线PDF",
        "独立Web Office-OFD",
        "独立Web Office-智能文档",
        "独立Web Office-智能表格",
        "独立Web Office-多维表格",
        "独立Web Office-格式处理",
        "独立Web Office-WebServer",
        "独立Web Office-金山文档-前端（V5/V6）",
        "独立Web Office-云基础",
    ],
    "WPS Comate": [
        "本地任务（功能问题、兼容性、交互体验等）",
        "本地对话（模型报错、工具调用异常等）",
        "云端任务（任务报错、沙盒创建失败等）",
        "skillhub",
        "渠道通信（协作链接、通信等）",
        "WPS365skill",
        "定时任务",
        "安装包问题",
        "应用",
        "登录问题",
        "专家",
        "团队",
        "WIKI",
        "Comate Studio",
    ],
}


def product_line_options() -> list[dict[str, str]]:
    return [
        {"code": item, "value": item, "text": item}
        for item in PRODUCT_LINE_MODULE_MAP
    ]


def canonical_product_line(product_line: str) -> str:
    normalized_line = sanitize_text(product_line).strip()
    if not normalized_line:
        return ""
    if normalized_line in PRODUCT_LINE_MODULE_MAP:
        return normalized_line
    aliased = PRODUCT_LINE_ALIASES.get(normalized_line, "")
    if aliased:
        return aliased
    lowered = normalized_line.casefold()
    for key in PRODUCT_LINE_MODULE_MAP:
        if key.casefold() == lowered:
            return key
    for alias, target in PRODUCT_LINE_ALIASES.items():
        if alias.casefold() == lowered:
            return target
    return normalized_line


def product_module_options(product_line: str) -> list[dict[str, str]]:
    normalized_line = canonical_product_line(product_line)
    if not normalized_line:
        return []
    return [
        {"code": item, "value": item, "text": item}
        for item in PRODUCT_LINE_MODULE_MAP.get(normalized_line, [])
    ]


def normalize_product_module(product_line: str, product_module: str) -> str:
    normalized_module = sanitize_text(product_module).strip()
    if not normalized_module:
        return ""
    valid_modules = {item["value"] for item in product_module_options(product_line)}
    return normalized_module if normalized_module in valid_modules else ""
