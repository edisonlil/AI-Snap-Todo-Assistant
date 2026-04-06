"""反馈系统：收集、存储、分析用户反馈，优化提示词"""
import base64
import json
import os
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FeedbackData:
    """单条反馈数据"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    scenario: str = ""  # 场景名称，如 "工单提取"
    model: str = ""  # 使用的模型，如 "gpt-4v"
    prompt_version: str = "v1.0"  # 提示词版本

    # 原始AI输出
    ai_output: Dict = field(default_factory=dict)

    # 用户编辑
    user_edited: bool = False
    original_result: str = ""
    edited_result: str = ""

    # 用户反馈
    feedback_status: str = "correct"  # correct / partial / incorrect
    problem_tags: List[str] = field(default_factory=list)
    correction: Dict = field(default_factory=dict)
    notes: str = ""
    image_base64: str = ""  # 原始截图，供即时分析使用
    image_path: str = ""  # 落盘后的截图路径，供历史回溯使用

    # AI分析结果
    analysis: str = ""
    improvement_suggestion: str = ""

    def to_dict(self) -> Dict:
        """转为可序列化的字典"""
        return asdict(self)


@dataclass
class FeedbackStats:
    """反馈统计数据"""
    total_feedback: int = 0
    correct_count: int = 0
    partial_count: int = 0
    incorrect_count: int = 0
    problem_frequency: Dict[str, int] = field(default_factory=dict)
    most_common_problems: List[str] = field(default_factory=list)
    accuracy_rate: float = 0.0


class FeedbackCollector:
    """反馈收集器：存储和读取反馈"""

    def __init__(self, feedback_dir: Optional[str] = None):
        """初始化反馈收集器"""
        if feedback_dir is None:
            aica_dir = os.path.join(os.path.expanduser("~"), ".aica")
            feedback_dir = os.path.join(aica_dir, "feedback")

        self._dir = feedback_dir
        os.makedirs(self._dir, exist_ok=True)
        self._feedback_file = os.path.join(self._dir, "feedback.jsonl")
        self._images_dir = os.path.join(self._dir, "images")
        os.makedirs(self._images_dir, exist_ok=True)

    def save_feedback(self, feedback: FeedbackData) -> str:
        """保存反馈到文件，并将关联截图单独落盘。"""
        if feedback.image_base64 and not feedback.image_path:
            feedback.image_path = self._save_feedback_image(feedback)

        payload = feedback.to_dict()
        if payload.get("image_path"):
            # 图片已单独保存，避免 jsonl 膨胀过快
            payload["image_base64"] = ""

        with open(self._feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        return feedback.id

    def load_all_feedback(self) -> List[FeedbackData]:
        """加载所有反馈。"""
        if not os.path.exists(self._feedback_file):
            return []

        feedback_list = []
        try:
            with open(self._feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    feedback_list.append(FeedbackData(**data))
        except Exception as e:
            print(f"加载反馈文件失败: {e}")

        return feedback_list

    def load_feedback_by_scenario(self, scenario: str) -> List[FeedbackData]:
        """加载特定场景的反馈。"""
        all_feedback = self.load_all_feedback()
        return [f for f in all_feedback if f.scenario == scenario]

    def load_feedback_by_status(self, status: str) -> List[FeedbackData]:
        """加载特定状态的反馈。"""
        all_feedback = self.load_all_feedback()
        return [f for f in all_feedback if f.feedback_status == status]

    def get_feedback_image_base64(self, feedback: FeedbackData) -> str:
        """获取反馈关联截图的 Base64，优先使用内存数据，其次从磁盘回读。"""
        if feedback.image_base64:
            return feedback.image_base64

        if not feedback.image_path or not os.path.exists(feedback.image_path):
            return ""

        try:
            with open(feedback.image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"读取反馈截图失败: {e}")
            return ""

    def _save_feedback_image(self, feedback: FeedbackData) -> str:
        """将反馈关联截图落盘，便于后续分析与追溯。"""
        image_path = os.path.join(self._images_dir, f"{feedback.id}.png")

        try:
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(feedback.image_base64))
        except Exception as e:
            print(f"保存反馈截图失败: {e}")
            return ""

        return image_path


class FeedbackAnalyzer:
    """反馈分析器：分析反馈数据，生成改进建议"""

    def __init__(self, collector: FeedbackCollector):
        self._collector = collector

    def analyze_scenario(self, scenario: str) -> FeedbackStats:
        """分析特定场景的反馈统计。"""
        feedback_list = self._collector.load_feedback_by_scenario(scenario)

        if not feedback_list:
            return FeedbackStats()

        stats = FeedbackStats(total_feedback=len(feedback_list))

        for fb in feedback_list:
            if fb.feedback_status == "correct":
                stats.correct_count += 1
            elif fb.feedback_status == "partial":
                stats.partial_count += 1
            elif fb.feedback_status == "incorrect":
                stats.incorrect_count += 1

        problem_counter = Counter()
        for fb in feedback_list:
            for tag in fb.problem_tags:
                problem_counter[tag] += 1

        stats.problem_frequency = dict(problem_counter)
        stats.most_common_problems = [tag for tag, _ in problem_counter.most_common(3)]

        if stats.total_feedback > 0:
            stats.accuracy_rate = stats.correct_count / stats.total_feedback

        return stats

    def generate_improvement_suggestion(self, scenario: str) -> Optional[str]:
        """根据反馈生成改进建议。"""
        stats = self.analyze_scenario(scenario)

        if stats.total_feedback < 5:
            return None

        if stats.accuracy_rate < 0.8:
            suggestion = f"📊 基于 {stats.total_feedback} 条反馈分析：\n"
            suggestion += f"当前准确率：{stats.accuracy_rate * 100:.1f}%\n"

            if stats.most_common_problems:
                suggestion += f"最常见问题：{', '.join(stats.most_common_problems)}。\n"
                suggestion += "建议优化提示词以强化对这些问题的处理。"

            return suggestion

        return None

    def get_correction_examples(self, scenario: str, problem_tag: str, limit: int = 3) -> List[Dict]:
        """获取特定问题的修正案例。"""
        feedback_list = self._collector.load_feedback_by_scenario(scenario)

        examples = []
        for fb in feedback_list:
            if problem_tag in fb.problem_tags and fb.correction:
                examples.append({
                    "ai_output": fb.ai_output,
                    "correction": fb.correction,
                    "notes": fb.notes,
                    "timestamp": fb.timestamp,
                    "image_path": fb.image_path,
                })

        return examples[:limit]
