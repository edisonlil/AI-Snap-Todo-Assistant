"""AI workers: screenshot analysis and feedback optimization."""
import base64

import requests
from PyQt6.QtCore import QBuffer, QByteArray, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap

from .feedback import FeedbackAnalyzer, FeedbackCollector, FeedbackData
from .image_utils import compress_if_needed
from .parser import ResultParser
from .prompt_optimizer import PromptOptimizer
from .prompts import PromptManager


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
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
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
            ],
            "temperature": 0.3,
        }
        response = requests.post(
            self._api_url,
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise requests.RequestException(f"HTTP {response.status_code}")
        data = response.json()
        return data["choices"][0]["message"]["content"]


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
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": content},
            ],
            "temperature": 0.3,
        }
        response = requests.post(
            self._api_url,
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise requests.RequestException(f"HTTP {response.status_code}")
        data = response.json()
        return data["choices"][0]["message"]["content"]


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
