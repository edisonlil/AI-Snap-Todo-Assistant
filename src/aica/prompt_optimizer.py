import json
from typing import Dict, List, Optional

from aica.feedback import FeedbackAnalyzer, FeedbackCollector, FeedbackData
from aica.llm.service import LLMService
from aica.llm.types import ContentPart, Message


class PromptOptimizer:
    """通过反馈分析结果自动优化提示词。"""

    FEEDBACK_THRESHOLD = 5

    def __init__(self, llm_service: LLMService, collector: FeedbackCollector, analyzer: FeedbackAnalyzer):
        self._llm_service = llm_service
        self._collector = collector
        self._analyzer = analyzer

    def analyze_feedback(self, feedback: FeedbackData, api_timeout: int = 30) -> bool:
        """分析单条反馈，生成错误根因分析。"""
        if not feedback.user_edited or feedback.feedback_status == "correct":
            return False

        try:
            analysis_prompt = self._build_analysis_prompt(feedback)
            analysis_text = self._call_analysis_api(analysis_prompt, feedback, api_timeout)
            feedback.analysis = analysis_text
            feedback.problem_tags = []
            return True
        except Exception as exc:
            print(f"反馈分析失败: {exc}")
            return False

    def apply_feedback_immediately(self, feedback: FeedbackData,
                                   prompts_module=None,
                                   api_timeout: int = 30) -> bool:
        """基于当前单条反馈立即微调对应场景的提示词。"""
        if prompts_module is None or not self._is_feedback_actionable(feedback):
            return False

        try:
            current_template = prompts_module.get_prompt(feedback.scenario)
            if current_template is None:
                return False

            payload = self._call_json_api(
                self._build_immediate_improvement_prompt(feedback, current_template),
                feedback=feedback,
                timeout=api_timeout,
            )

            new_system = (payload.get("system") or "").strip()
            new_user = (payload.get("user") or "").strip()
            if not new_system or not new_user:
                return False

            from aica.prompts import PromptTemplate

            new_template = PromptTemplate(
                system=new_system,
                user=new_user,
                version=self._format_next_version(current_template.version),
                last_improved_feedback_count=current_template.last_improved_feedback_count,
            )

            return prompts_module.update_scenario(
                feedback.scenario,
                new_template,
                reason=f"基于反馈 {feedback.id} 的即时优化",
            )
        except Exception as exc:
            print(f"即时优化提示词失败: {exc}")
            return False

    def apply_style_to_prompt(self, scenario: str, prompts_module=None) -> bool:
        """基于累计反馈规律自动优化提示词。"""
        feedback_list = self._collector.load_feedback_by_scenario(scenario)
        actionable_feedbacks = self._get_actionable_feedbacks(feedback_list)
        current_feedback_count = len(actionable_feedbacks)

        if current_feedback_count < self.FEEDBACK_THRESHOLD:
            return False

        try:
            style_prompt = self._build_style_analysis_prompt(scenario, actionable_feedbacks)
            example_feedback = actionable_feedbacks[0] if actionable_feedbacks else None
            style_patterns = self._call_analysis_api(style_prompt, example_feedback)

            if prompts_module is None:
                print("prompts_module 未提供，无法更新提示词")
                return False

            current_template = prompts_module.get_prompt(scenario)
            if current_template:
                current_prompt = {
                    "system": current_template.system,
                    "user": current_template.user,
                }
            else:
                current_prompt = {"system": "", "user": ""}

            payload = self._call_json_api(
                self._build_improvement_from_style(
                    scenario,
                    current_prompt,
                    style_patterns,
                    actionable_feedbacks,
                ),
                feedback=example_feedback,
            )

            new_system = (payload.get("system") or "").strip()
            new_user = (payload.get("user") or "").strip()
            if not new_system or not new_user:
                return False

            from aica.prompts import PromptTemplate

            new_template = PromptTemplate(
                system=new_system,
                user=new_user,
                version=self._format_next_version(current_template.version if current_template else "v1.0"),
                last_improved_feedback_count=current_feedback_count,
            )

            prompts_module.update_scenario(
                scenario,
                new_template,
                reason=f"基于 {current_feedback_count} 条有效反馈自动优化",
            )
            print(f"[改进提示词] 场景'{scenario}'已自动更新（第{current_feedback_count}条反馈时触发）")
            return True
        except Exception as exc:
            print(f"自动优化提示词失败: {exc}")
            return False

    def check_feedback_threshold(self, scenario: str, prompts_manager=None) -> bool:
        """检查某场景是否达到增量优化阈值。"""
        feedback_list = self._collector.load_feedback_by_scenario(scenario)
        actionable_feedbacks = self._get_actionable_feedbacks(feedback_list)
        current_count = len(actionable_feedbacks)
        print(f"[检查改进] 场景'{scenario}': 当前有效反馈数={current_count} (总反馈={len(feedback_list)})")

        if prompts_manager is None:
            result = current_count >= self.FEEDBACK_THRESHOLD
            print(f"[检查改进] 未提供 prompts_manager，简单判断结果={result}")
            return result

        try:
            prompt_template = prompts_manager.get_prompt(scenario)
            if prompt_template is None:
                print(f"[检查改进] 场景'{scenario}'的提示词不存在")
                return False

            last_improved_count = prompt_template.last_improved_feedback_count
            print(f"[检查改进] 上次改进时反馈数={last_improved_count}")

            if last_improved_count == 0 and current_count >= self.FEEDBACK_THRESHOLD:
                print(f"[检查改进] ✅ 触发首次改进 (当前={current_count} >= 初始阈值={self.FEEDBACK_THRESHOLD})")
                return True

            if last_improved_count > 0 and current_count >= last_improved_count + self.FEEDBACK_THRESHOLD:
                target = last_improved_count + self.FEEDBACK_THRESHOLD
                print(f"[检查改进] ✅ 触发增量改进 (当前={current_count} >= {target})")
                return True

            next_target = last_improved_count + self.FEEDBACK_THRESHOLD if last_improved_count > 0 else self.FEEDBACK_THRESHOLD
            print(f"[检查改进] ❌ 不触发 (当前={current_count}, 下次触发条件={next_target})")
            return False
        except Exception as exc:
            print(f"[检查改进] ❌ 异常: {exc}")
            result = current_count >= self.FEEDBACK_THRESHOLD
            print(f"[检查改进] 降级为简单判断: {result}")
            return result

    def _get_actionable_feedbacks(self, feedback_list: List[FeedbackData]) -> List[FeedbackData]:
        """筛选可用于优化提示词的反馈。"""
        return [fb for fb in feedback_list if self._is_feedback_actionable(fb)]

    def _is_feedback_actionable(self, feedback: FeedbackData) -> bool:
        """判断反馈是否足以驱动提示词优化。"""
        has_meaningful_notes = bool((feedback.notes or "").strip())
        has_correction = bool(feedback.correction)
        is_negative_feedback = feedback.feedback_status in ("incorrect", "partial")
        return feedback.user_edited or is_negative_feedback or has_meaningful_notes or has_correction

    def _increment_version(self, version: str) -> str:
        """版本号递增，如 v1.0 -> 1.1。"""
        try:
            normalized = version.lstrip("v")
            parts = normalized.split(".")
            if len(parts) >= 2:
                parts[1] = str(int(parts[1]) + 1)
                return ".".join(parts)
            return f"{parts[0]}.1"
        except Exception:
            return "1.0"

    def _format_next_version(self, version: str) -> str:
        return f"v{self._increment_version(version)}"

    def _build_style_analysis_prompt(self, scenario: str, feedbacks: List[FeedbackData]) -> str:
        feedback_examples = []
        for index, feedback in enumerate(feedbacks[:5], 1):
            feedback_examples.append(
                f"""
【示例{index}】
原始输出: {feedback.original_result}
---
用户修正: {feedback.edited_result}
用户说明: {feedback.notes or '（无补充说明）'}
"""
            )

        return f"""请分析以下用户反馈，总结用户偏好的输出风格规律。

场景: {scenario}

{chr(10).join(feedback_examples)}

请从以下方面总结可操作规律：
1. 格式偏好
2. 语气和表达风格
3. 内容组织方式
4. 其他特殊要求

请输出精炼、可执行的结论，后续会用于优化提示词。"""

    def _build_improvement_from_style(self, scenario: str, current_prompt: Dict[str, str],
                                      style_patterns: str, feedbacks: List[FeedbackData]) -> str:
        examples = []
        for index, feedback in enumerate(feedbacks[:3], 1):
            examples.append(
                f"""
案例{index}:
原始输出: {feedback.original_result}
用户修正: {feedback.edited_result}
"""
            )

        return f"""你是提示词工程专家。请根据用户累计反馈，改进当前场景提示词。

场景: {scenario}

当前提示词(JSON):
{json.dumps(current_prompt, ensure_ascii=False, indent=2)}

用户风格规律:
{style_patterns}

用户修正案例:
{chr(10).join(examples)}

要求:
1. 保留原任务目标，不改变场景。
2. 将用户偏好的表达、结构和约束融入提示词。
3. 直接输出 JSON，对象只包含 `system` 和 `user` 两个字符串字段。
4. 不要输出 markdown，不要解释。"""

    def _build_analysis_prompt(self, feedback: FeedbackData) -> str:
        image_ref = ""
        image_base64 = self._collector.get_feedback_image_base64(feedback)
        if image_base64:
            image_ref = "【原始截图】已附带，可结合截图分析。\n\n"

        return f"""分析以下 AI 输出的错误原因。

{image_ref}场景: {feedback.scenario}
模型: {feedback.model}

AI 输出:
{feedback.original_result}

正确答案:
{feedback.edited_result}

用户说明: {feedback.notes}

请回答：
1. 根本原因是什么
2. 错误属于哪一类
3. 如何在提示词中避免这类问题

请简洁作答。"""

    def _build_immediate_improvement_prompt(self, feedback: FeedbackData, current_template) -> str:
        current_prompt = {
            "system": current_template.system,
            "user": current_template.user,
        }
        correction = feedback.edited_result or json.dumps(feedback.correction, ensure_ascii=False)
        notes = (feedback.notes or "").strip() or "无补充说明"

        return f"""你是提示词工程专家。请根据这一次真实用户反馈，直接改写当前场景的提示词。

场景: {feedback.scenario}
模型: {feedback.model}

当前提示词(JSON):
{json.dumps(current_prompt, ensure_ascii=False, indent=2)}

本次反馈信息:
- feedback_status: {feedback.feedback_status}
- user_edited: {feedback.user_edited}
- 原始AI输出:
{feedback.original_result}

- 用户期望/修正后的输出:
{correction}

- 用户补充说明:
{notes}

要求:
1. 保留原提示词的核心目标，不要改成别的任务。
2. 只根据这次反馈做小步、精准的优化，避免过度拟合。
3. 如果截图信息对理解错误原因有帮助，请一并利用。
4. 输出必须是 JSON，对象只包含 `system` 和 `user` 两个字符串字段。
5. 不要输出 markdown，不要解释。"""

    def _call_analysis_api(self, prompt: str, feedback: Optional[FeedbackData] = None,
                           timeout: int = 30) -> str:
        content = [ContentPart(type="text", text=prompt)]
        image_base64 = self._collector.get_feedback_image_base64(feedback) if feedback else ""
        if image_base64:
            content.append(ContentPart(type="image_data_url", data_url=f"data:image/png;base64,{image_base64}"))

        return self._llm_service.run_task(
            "prompt_optimization",
            messages=[Message(role="user", content=content)],
            temperature=0.3,
            timeout=timeout,
        )

    def _call_json_api(self, prompt: str, feedback: Optional[FeedbackData] = None,
                       timeout: int = 30) -> Dict[str, str]:
        raw_text = self._call_analysis_api(prompt, feedback=feedback, timeout=timeout)
        cleaned = raw_text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("JSON response is not an object")
        return data
