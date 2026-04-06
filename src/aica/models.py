"""数据模型：StructuredResult"""
from dataclasses import dataclass


@dataclass
class StructuredResult:
    task_desc: str    # 任务描述，最多 100 字
    platform: str     # 协作平台：微信/钉钉/飞书/其他
    group_name: str   # 协作群聊名称
    ticket_type: str  # 工单类型：业务/技术/排查/培训
    environment: str  # 客户环境：未知/生产/测试

    def to_tab_row(self) -> str:
        """返回以制表符分隔的单行字符串，用于粘贴至多维表格"""
        return "\t".join([
            self.task_desc,
            self.platform,
            self.group_name,
            self.ticket_type,
            self.environment,
        ])
