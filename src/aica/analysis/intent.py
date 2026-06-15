"""Intent definitions for screenshot analysis."""
from __future__ import annotations

from dataclasses import dataclass


SCENE_CHAT_FEEDBACK = "chat_feedback"
SCENE_STEP_SEQUENCE = "step_sequence"

CAPTURE_MODE_SINGLE = "single"
CAPTURE_MODE_SEQUENCE = "sequence"

SCENE_OPTIONS: list[tuple[str, str]] = [
    ("工单跟进", SCENE_CHAT_FEEDBACK),
    ("连续步骤截图", SCENE_STEP_SEQUENCE),
]

SCENE_LABEL_TO_TYPE = dict(SCENE_OPTIONS)
SCENE_LABELS = {scene_type: label for label, scene_type in SCENE_OPTIONS}


@dataclass(frozen=True)
class AnalysisIntent:
    scene_type: str
    capture_group_mode: str = CAPTURE_MODE_SINGLE

    @property
    def scene_label(self) -> str:
        return SCENE_LABELS.get(self.scene_type, "工单跟进")


def build_analysis_intent(scene_type: str, *, capture_count: int = 1) -> AnalysisIntent:
    capture_group_mode = CAPTURE_MODE_SEQUENCE if capture_count > 1 else CAPTURE_MODE_SINGLE
    normalized_scene = scene_type if scene_type in SCENE_LABELS else SCENE_CHAT_FEEDBACK
    return AnalysisIntent(
        scene_type=normalized_scene,
        capture_group_mode=capture_group_mode,
    )


def scene_type_from_label(label: str) -> str:
    return SCENE_LABEL_TO_TYPE.get(str(label or "").strip(), "")
