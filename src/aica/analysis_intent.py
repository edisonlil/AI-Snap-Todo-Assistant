"""Intent definitions for screenshot analysis."""
from __future__ import annotations

from dataclasses import dataclass


SCENE_CHAT_FEEDBACK = "chat_feedback"
SCENE_ERROR_LOG = "error_log"
SCENE_API_DETAIL = "api_detail"
SCENE_STEP_SEQUENCE = "step_sequence"
SCENE_CUSTOM = "custom"

CAPTURE_MODE_SINGLE = "single"
CAPTURE_MODE_SEQUENCE = "sequence"

SCENE_OPTIONS: list[tuple[str, str]] = [
    ("工单跟进", SCENE_CHAT_FEEDBACK),
    ("错误与日志", SCENE_ERROR_LOG),
    ("参数与接口详情", SCENE_API_DETAIL),
    ("连续步骤截图", SCENE_STEP_SEQUENCE),
    ("其他自定义", SCENE_CUSTOM),
]

SCENE_LABEL_TO_TYPE = dict(SCENE_OPTIONS)
SCENE_LABELS = {scene_type: label for label, scene_type in SCENE_OPTIONS}


@dataclass(frozen=True)
class AnalysisIntent:
    scene_type: str
    focus_hint: str = ""
    capture_group_mode: str = CAPTURE_MODE_SINGLE

    @property
    def scene_label(self) -> str:
        return SCENE_LABELS.get(self.scene_type, "其他自定义")


def build_analysis_intent(scene_type: str, *, focus_hint: str = "", capture_count: int = 1) -> AnalysisIntent:
    capture_group_mode = CAPTURE_MODE_SEQUENCE if capture_count > 1 else CAPTURE_MODE_SINGLE
    normalized_scene = scene_type if scene_type in SCENE_LABELS else SCENE_CUSTOM
    return AnalysisIntent(
        scene_type=normalized_scene,
        focus_hint=str(focus_hint or "").strip(),
        capture_group_mode=capture_group_mode,
    )


def scene_type_from_label(label: str) -> str:
    return SCENE_LABEL_TO_TYPE.get(str(label or "").strip(), "")
