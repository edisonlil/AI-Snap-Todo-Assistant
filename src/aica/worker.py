"""AI workers: screenshot analysis and feedback optimization."""
import base64
import json
import re

import requests
from PyQt6.QtCore import QBuffer, QByteArray, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap

from .feedback import FeedbackAnalyzer, FeedbackCollector, FeedbackData
from .image_utils import compress_if_needed
from .parser import ResultParser
from .prompt_optimizer import PromptOptimizer
from .prompts import PromptManager

TITLE_GENERATION_MODEL = "Qwen/Qwen3-8B"
_TITLE_SYSTEM_PROMPT = (
    "你是一位资深的B端技术支持专家，负责生成最终展示和保存使用的工单标题。"
    "你的输出会直接进入界面和待办存储，因此必须准确、简洁、专业。"
)


class _BaseVisionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    parse_error = pyqtSignal(str)
    show_result = pyqtSignal(object, str, str)

    def _pixmap_to_bytes(self, pixmap: QPixmap) -> bytes:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()
        return bytes(byte_array)

    def _pixmap_to_base64(self, pixmap: QPixmap) -> str:
        img_bytes = self._pixmap_to_bytes(pixmap)
        return base64.b64encode(img_bytes).decode("utf-8")

    def _encode_for_api(self, pixmap: QPixmap) -> str:
        img_bytes = self._pixmap_to_bytes(pixmap)
        img_bytes = compress_if_needed(img_bytes)
        return base64.b64encode(img_bytes).decode("utf-8")

    def _build_combined_preview(self, pixmaps: list[QPixmap]) -> QPixmap:
        if not pixmaps:
            return QPixmap()

        width = max(pixmap.width() for pixmap in pixmaps)
        total_height = sum(pixmap.height() for pixmap in pixmaps)
        combined = QPixmap(width, total_height)
        combined.fill()

        painter = QPainter(combined)
        offset_y = 0
        for pixmap in pixmaps:
            painter.drawPixmap(0, offset_y, pixmap)
            offset_y += pixmap.height()
        painter.end()
        return combined

    def _post_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        temperature: float = 0.3,
        timeout: int | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        response = requests.post(
            self._api_url,
            json=payload,
            headers=headers,
            timeout=timeout or self._timeout,
        )
        if response.status_code != 200:
            raise requests.RequestException(f"HTTP {response.status_code}")
        data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _normalize_generated_title(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""

        md_match = re.search(r"```(?:json|text)?\s*([\s\S]*?)```", raw)
        if md_match:
            raw = md_match.group(1).strip()

        if raw.startswith("{"):
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                raw = str(payload.get("title") or "").strip()

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if lines:
            raw = lines[0]

        raw = re.sub(r"^(?:标题|工单标题)\s*[:：]\s*", "", raw)
        return raw.strip("`\"'“”‘’ ")

    @staticmethod
    def _build_title_generation_messages(result) -> list[dict[str, str]]:  # noqa: ANN001
        fields = result.fields
        user_prompt = (
            "请根据以下结构化工单信息，生成最终展示和保存使用的工单标题。\n"
            "只输出标题文本，不要解释，不要 JSON，不要 markdown。\n"
            "要求：\n"
            "1. 标题格式优先使用：【关联产品】[触发操作/核心异常点] + [关键报错/现象]。\n"
            "2. 如果信息同时包含背景、前置条件、排查动作和最终异常现象，优先保留最终用户可见的异常现象。\n"
            "3. 不要把“上传时未勾选”“确认字体”“检查服务器字体”这类背景或排查动作写成标题主体。\n"
            "4. 标题控制在 50 字以内，表述专业、准确、可检索。\n\n"
            f"群聊名称: {fields.group_name}\n"
            f"环境: {fields.environment}\n"
            f"产品线: {fields.product_line}\n"
            f"工单类型: {fields.ticket_type}\n"
            f"当前摘要: {result.current_summary}\n"
            f"本次跟进: {result.timeline_entry}"
        )
        return [
            {"role": "system", "content": _TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _generate_title(self, result) -> str:  # noqa: ANN001
        if not (result.current_summary.strip() or result.timeline_entry.strip()):
            return result.title.strip()

        try:
            raw_title = self._post_chat_completion(
                model=TITLE_GENERATION_MODEL,
                messages=self._build_title_generation_messages(result),
                temperature=0.1,
                timeout=min(self._timeout, 20),
            )
        except (requests.RequestException, KeyError, TypeError, ValueError):
            return result.title.strip()

        normalized_title = self._normalize_generated_title(raw_title)
        return normalized_title or result.title.strip()


class AIWorker(_BaseVisionWorker):
    def __init__(self, image: QPixmap, api_key: str, model: str,
                 api_url: str, timeout: int = 30,
                 prompt_manager: PromptManager = None,
                 scenario: str = "工单提取",
                 context_text: str = "",
                 parent=None):
        super().__init__(parent)
        self._image = image
        self._feedback_image_base64 = self._pixmap_to_base64(image)
        self._api_key = api_key
        self._model = model
        self._api_url = api_url
        self._timeout = timeout
        self._prompt_manager = prompt_manager or PromptManager()
        self._scenario = scenario
        self._context_text = context_text.strip()

    def run(self) -> None:
        try:
            raw_text = self._call_api(self._encode_for_api(self._image))
            try:
                result = ResultParser.parse(raw_text)
                result.title = self._generate_title(result)
                self.show_result.emit(result, self._scenario, self._model)
                self.finished.emit(result)
            except (ValueError, KeyError, TypeError):
                self.parse_error.emit(raw_text)
        except requests.Timeout:
            self.error.emit("请求超时，请检查网络后重试")
        except requests.RequestException as exc:
            self.error.emit(f"网络错误: {exc}")
        except Exception as exc:
            self.error.emit(f"未知错误: {exc}")

    def _call_api(self, b64_image: str) -> str:
        prompt = self._prompt_manager.get_current_prompt()
        messages = [
            {"role": "system", "content": prompt.system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"【已有待办上下文】\n{self._context_text}\n\n【当前截图分析要求】\n{prompt.user}"
                            if self._context_text
                            else prompt.user
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                ],
            },
        ]
        return self._post_chat_completion(
            model=self._model,
            messages=messages,
            temperature=0.3,
            timeout=self._timeout,
        )


class MultiCaptureAIWorker(_BaseVisionWorker):
    def __init__(self, images: list[QPixmap], api_key: str, model: str,
                 api_url: str, timeout: int = 30,
                 prompt_manager: PromptManager = None,
                 scenario: str = "工单提取",
                 context_text: str = "",
                 parent=None):
        super().__init__(parent)
        self._images = images
        self._feedback_image_base64 = self._pixmap_to_base64(self._build_combined_preview(images))
        self._api_key = api_key
        self._model = model
        self._api_url = api_url
        self._timeout = timeout
        self._prompt_manager = prompt_manager or PromptManager()
        self._scenario = scenario
        self._context_text = context_text.strip()

    def run(self) -> None:
        try:
            raw_text = self._call_api()
            try:
                result = ResultParser.parse(raw_text)
                result.title = self._generate_title(result)
                self.show_result.emit(result, self._scenario, self._model)
                self.finished.emit(result)
            except (ValueError, KeyError, TypeError):
                self.parse_error.emit(raw_text)
        except requests.Timeout:
            self.error.emit("请求超时，请检查网络后重试")
        except requests.RequestException as exc:
            self.error.emit(f"网络错误: {exc}")
        except Exception as exc:
            self.error.emit(f"未知错误: {exc}")

    def _call_api(self) -> str:
        prompt = self._prompt_manager.get_current_prompt()
        multi_intro = (
            "以下是同一问题场景下按时间顺序截取的多张连续聊天截图。"
            "请把它们视为一个整体进行理解，按截图顺序整合信息，"
            "自动忽略相邻截图中的重复内容，并输出符合当前场景要求的最终总结。"
        )
        context_intro = (
            f"【已有待办上下文】\n{self._context_text}\n\n【当前截图分析要求】\n"
            if self._context_text
            else ""
        )
        content = [{"type": "text", "text": f"{context_intro}{multi_intro}\n\n{prompt.user}"}]
        for index, pixmap in enumerate(self._images, 1):
            content.append({"type": "text", "text": f"第 {index} 张截图"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{self._encode_for_api(pixmap)}"},
                }
            )

        return self._post_chat_completion(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": content},
            ],
            temperature=0.3,
            timeout=self._timeout,
        )


class FeedbackOptimizeWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, model: str, api_url: str,
                 timeout: int, feedback: FeedbackData, parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._model = model
        self._api_url = api_url
        self._timeout = timeout
        self._feedback = feedback

    def run(self) -> None:
        summary = {
            "feedback_id": self._feedback.id,
            "scenario": self._feedback.scenario,
            "analysis_applied": False,
            "immediate_prompt_updated": False,
            "threshold_prompt_updated": False,
        }

        try:
            collector = FeedbackCollector()
            analyzer = FeedbackAnalyzer(collector)
            optimizer = PromptOptimizer(
                self._api_key,
                self._model,
                self._api_url,
                collector,
                analyzer,
            )
            prompt_manager = PromptManager()

            if self._feedback.user_edited and self._feedback.feedback_status != "correct":
                summary["analysis_applied"] = optimizer.analyze_feedback(
                    self._feedback,
                    self._timeout,
                )

            summary["immediate_prompt_updated"] = optimizer.apply_feedback_immediately(
                self._feedback,
                prompts_module=prompt_manager,
                api_timeout=self._timeout,
            )

            if optimizer.check_feedback_threshold(self._feedback.scenario, prompt_manager):
                summary["threshold_prompt_updated"] = optimizer.apply_style_to_prompt(
                    self._feedback.scenario,
                    prompts_module=prompt_manager,
                )

            self.finished.emit(summary)
        except Exception as exc:
            self.error.emit(str(exc))
