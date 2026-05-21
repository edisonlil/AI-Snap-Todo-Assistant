"""User rule storage and prompt debug persistence for screenshot analysis."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aica.analysis.intent import (
    SCENE_API_DETAIL,
    SCENE_CHAT_FEEDBACK,
    SCENE_CUSTOM,
    SCENE_ERROR_LOG,
    SCENE_LABELS,
    SCENE_STEP_SEQUENCE,
)
from aica.paths import analysis_rules_file as default_analysis_rules_file
from aica.paths import prompt_debug_dir as default_prompt_debug_dir


_SCENE_TYPES = (
    SCENE_CHAT_FEEDBACK,
    SCENE_ERROR_LOG,
    SCENE_API_DETAIL,
    SCENE_STEP_SEQUENCE,
    SCENE_CUSTOM,
)

_DEFAULT_DEBUG_MAX_RECORDS = 100
_MAX_DEBUG_RECORDS_LIMIT = 1000


def _coerce_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


@dataclass
class SceneAnalysisRule:
    title_preference: str = ""
    summary_preference: str = ""
    timeline_preference: str = ""
    must_include: str = ""
    must_avoid: str = ""
    extra_instructions: str = ""

    @classmethod
    def from_dict(cls, data: object) -> "SceneAnalysisRule":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            return cls()
        return cls(
            title_preference=str(data.get("title_preference", "")).strip(),
            summary_preference=str(data.get("summary_preference", "")).strip(),
            timeline_preference=str(data.get("timeline_preference", "")).strip(),
            must_include=str(data.get("must_include", "")).strip(),
            must_avoid=str(data.get("must_avoid", "")).strip(),
            extra_instructions=str(data.get("extra_instructions", "")).strip(),
        )

    def is_empty(self) -> bool:
        return not any(
            (
                self.title_preference,
                self.summary_preference,
                self.timeline_preference,
                self.must_include,
                self.must_avoid,
                self.extra_instructions,
            )
        )


def _normalize_rule_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_rule_lines(values: list[object]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = _normalize_rule_text(value)
        if text:
            normalized.append(text)
    return normalized


def _legacy_rule_lines(rule: SceneAnalysisRule) -> list[str]:
    lines: list[str] = []
    if rule.title_preference:
        lines.append(f"标题偏好：{rule.title_preference}")
    if rule.summary_preference:
        lines.append(f"摘要偏好：{rule.summary_preference}")
    if rule.timeline_preference:
        lines.append(f"时间线偏好：{rule.timeline_preference}")
    if rule.must_include:
        include_items = [line.strip() for line in rule.must_include.splitlines() if line.strip()]
        if include_items:
            lines.append(f"必须包含：{'；'.join(include_items)}")
    if rule.must_avoid:
        avoid_items = [line.strip() for line in rule.must_avoid.splitlines() if line.strip()]
        if avoid_items:
            lines.append(f"避免输出：{'；'.join(avoid_items)}")
    if rule.extra_instructions:
        lines.append(rule.extra_instructions)
    return lines


def _legacy_scene_rule_lines(raw_scenes: object) -> list[str]:
    if not isinstance(raw_scenes, dict):
        return []
    lines: list[str] = []
    for scene_type in _SCENE_TYPES:
        rule = SceneAnalysisRule.from_dict(raw_scenes.get(scene_type))
        for line in _legacy_rule_lines(rule):
            if line not in lines:
                lines.append(line)
    return lines


@dataclass
class UserRuleConfig:
    items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.items = [_normalize_rule_text(item) for item in self.items]

    @classmethod
    def from_dict(cls, data: object) -> "UserRuleConfig":
        if isinstance(data, cls):
            return cls(items=list(data.items))
        if isinstance(data, SceneAnalysisRule):
            return cls.from_items(_legacy_rule_lines(data), compact=True)
        if isinstance(data, (list, tuple)):
            return cls.from_items(list(data), compact=True)
        if not isinstance(data, dict):
            return cls()
        raw_items = data.get("items")
        if isinstance(raw_items, (list, tuple)):
            return cls.from_items(list(raw_items), compact=True)
        legacy_slots = [
            data.get("rule_1", data.get("rule1", "")),
            data.get("rule_2", data.get("rule2", "")),
            data.get("rule_3", data.get("rule3", "")),
        ]
        if any(_normalize_rule_text(item) for item in legacy_slots):
            return cls.from_items(legacy_slots, compact=True)
        if any(
            key in data
            for key in (
                "title_preference",
                "summary_preference",
                "timeline_preference",
                "must_include",
                "must_avoid",
                "extra_instructions",
            )
        ):
            return cls.from_items(_legacy_rule_lines(SceneAnalysisRule.from_dict(data)), compact=True)
        return cls()

    @classmethod
    def from_items(cls, values: list[object], *, compact: bool = False) -> "UserRuleConfig":
        items = [_normalize_rule_text(value) for value in values]
        if compact:
            items = [item for item in items if item]
        return cls(items=items)

    @classmethod
    def from_lines(cls, values: list[object]) -> "UserRuleConfig":
        return cls.from_items(values, compact=True)

    def to_lines(self) -> list[str]:
        return _normalize_rule_lines(self.items)

    def is_empty(self) -> bool:
        return not self.to_lines()


@dataclass
class AnalysisDebugConfig:
    enabled: bool = False
    max_records: int = _DEFAULT_DEBUG_MAX_RECORDS

    @classmethod
    def from_dict(cls, data: object) -> "AnalysisDebugConfig":
        if not isinstance(data, dict):
            return cls()
        max_records = _coerce_positive_int(data.get("max_records"), _DEFAULT_DEBUG_MAX_RECORDS)
        max_records = min(max_records, _MAX_DEBUG_RECORDS_LIMIT)
        return cls(
            enabled=bool(data.get("enabled", False)),
            max_records=max_records,
        )


def _default_scene_rules() -> dict[str, SceneAnalysisRule]:
    return {scene_type: SceneAnalysisRule() for scene_type in _SCENE_TYPES}


def _default_scene_user_rules() -> dict[str, UserRuleConfig]:
    return {scene_type: UserRuleConfig() for scene_type in _SCENE_TYPES}


@dataclass
class AnalysisRuleConfig:
    version: str = "built-in"
    debug: AnalysisDebugConfig = field(default_factory=AnalysisDebugConfig)
    rules: UserRuleConfig = field(default_factory=UserRuleConfig)
    scene_rules: dict[str, UserRuleConfig] = field(default_factory=_default_scene_user_rules)
    scenes: dict[str, SceneAnalysisRule] = field(default_factory=_default_scene_rules)

    def __post_init__(self) -> None:
        self.rules = UserRuleConfig.from_dict(self.rules)
        normalized_scene_rules = _default_scene_user_rules()
        if isinstance(self.scene_rules, dict):
            for scene_type in _SCENE_TYPES:
                normalized_scene_rules[scene_type] = UserRuleConfig.from_dict(self.scene_rules.get(scene_type))
        self.scene_rules = normalized_scene_rules
        if all(rule.is_empty() for rule in self.scene_rules.values()):
            if not self.rules.is_empty():
                self.scene_rules = {
                    scene_type: UserRuleConfig.from_items(self.rules.to_lines())
                    for scene_type in _SCENE_TYPES
                }
            else:
                self.scene_rules = {
                    scene_type: UserRuleConfig.from_dict(self.scenes.get(scene_type, SceneAnalysisRule()))
                    for scene_type in _SCENE_TYPES
                }
        if self.rules.is_empty():
            self.rules = UserRuleConfig.from_lines(_legacy_scene_rule_lines(self.scenes))

    @classmethod
    def from_dict(cls, data: object) -> "AnalysisRuleConfig":
        if not isinstance(data, dict):
            return cls()
        raw_scenes = data.get("scenes", {})
        raw_scene_rules = data.get("scene_rules", {})
        scenes = _default_scene_rules()
        if isinstance(raw_scenes, dict):
            for scene_type in _SCENE_TYPES:
                scenes[scene_type] = SceneAnalysisRule.from_dict(raw_scenes.get(scene_type))
        scene_rules = _default_scene_user_rules()
        if "scene_rules" in data and isinstance(raw_scene_rules, dict):
            for scene_type in _SCENE_TYPES:
                scene_rules[scene_type] = UserRuleConfig.from_dict(raw_scene_rules.get(scene_type))
        else:
            global_rules = UserRuleConfig.from_dict(data.get("rules"))
            if not global_rules.is_empty():
                scene_rules = {
                    scene_type: UserRuleConfig.from_items(global_rules.to_lines())
                    for scene_type in _SCENE_TYPES
                }
            else:
                for scene_type in _SCENE_TYPES:
                    scene_rules[scene_type] = UserRuleConfig.from_dict(raw_scenes.get(scene_type))
        return cls(
            version=str(data.get("version", "built-in")).strip() or "built-in",
            debug=AnalysisDebugConfig.from_dict(data.get("debug")),
            rules=(
                UserRuleConfig.from_dict(data.get("rules"))
                if "rules" in data
                else UserRuleConfig.from_lines(_legacy_scene_rule_lines(raw_scenes))
            ),
            scene_rules=scene_rules,
            scenes=scenes,
        )


class AnalysisRulesManager:
    """Loads and persists scene-specific analysis preferences."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else default_analysis_rules_file()
        self._config = self._load()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def config(self) -> AnalysisRuleConfig:
        return self._config

    def reload(self) -> AnalysisRuleConfig:
        self._config = self._load()
        return self._config

    def save(self) -> AnalysisRuleConfig:
        self._config.version = datetime.now().isoformat(timespec="seconds")
        payload = {
            "version": self._config.version,
            "debug": asdict(self._config.debug),
            "scene_rules": {
                scene_type: {"items": rule.to_lines()}
                for scene_type, rule in self._config.scene_rules.items()
            },
            "scenes": {scene_type: asdict(rule) for scene_type, rule in self._config.scenes.items()},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._config

    def update_scene_rule(self, scene_type: str, rule: SceneAnalysisRule) -> None:
        normalized_scene = scene_type if scene_type in self._config.scenes else SCENE_CUSTOM
        self._config.scenes[normalized_scene] = rule

    def update_debug_config(self, *, enabled: bool, max_records: int) -> None:
        self._config.debug.enabled = bool(enabled)
        self._config.debug.max_records = min(
            _coerce_positive_int(max_records, _DEFAULT_DEBUG_MAX_RECORDS),
            _MAX_DEBUG_RECORDS_LIMIT,
        )

    def update_user_rules(self, rules: UserRuleConfig) -> None:
        normalized = UserRuleConfig.from_dict(rules)
        self._config.rules = normalized
        self._config.scene_rules = {
            scene_type: UserRuleConfig.from_items(normalized.to_lines())
            for scene_type in _SCENE_TYPES
        }

    def get_user_rules(self) -> UserRuleConfig:
        return self._config.rules

    def update_scene_user_rules(self, scene_type: str, rules: UserRuleConfig) -> None:
        normalized_scene = scene_type if scene_type in self._config.scene_rules else SCENE_CUSTOM
        self._config.scene_rules[normalized_scene] = UserRuleConfig.from_dict(rules)

    def get_scene_user_rules(self, scene_type: str) -> UserRuleConfig:
        return self._config.scene_rules.get(scene_type, UserRuleConfig())

    def get_scene_rule(self, scene_type: str) -> SceneAnalysisRule:
        return self._config.scenes.get(scene_type, SceneAnalysisRule())

    def _load(self) -> AnalysisRuleConfig:
        if not self._path.exists():
            return AnalysisRuleConfig()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return AnalysisRuleConfig()
        return AnalysisRuleConfig.from_dict(payload)


class PromptDebugStore:
    """Persists analysis prompt traces for tuning and troubleshooting."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self._dir = Path(directory) if directory is not None else default_prompt_debug_dir()

    @property
    def directory(self) -> Path:
        return self._dir

    def write_record(self, payload: dict[str, Any], *, max_records: int) -> None:
        record_id = str(payload.get("trace_id", "")).strip()
        if not record_id:
            record_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
            payload["trace_id"] = record_id
        self._dir.mkdir(parents=True, exist_ok=True)
        target = self._dir / f"{record_id}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._prune(max_records=max_records)

    def list_records(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(self._dir.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            records.append(
                {
                    "traceId": str(payload.get("trace_id", "")).strip(),
                    "timestamp": str(payload.get("timestamp", "")).strip(),
                    "sceneLabel": str(payload.get("scene_label", "")).strip() or str(payload.get("scene_type", "")).strip(),
                    "status": str(payload.get("status", "")).strip(),
                    "model": str(payload.get("model", "")).strip(),
                    "imageCount": int(payload.get("image_count", 0) or 0),
                    "timingSummary": str(payload.get("timing_summary", "")).strip(),
                }
            )
            if len(records) >= max(1, int(limit)):
                break
        return records

    def load_record(self, trace_id: str) -> dict[str, Any] | None:
        normalized = str(trace_id or "").strip()
        if not normalized:
            return None
        path = self._dir / f"{normalized}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _prune(self, *, max_records: int) -> None:
        limit = max(1, min(int(max_records), _MAX_DEBUG_RECORDS_LIMIT))
        files = sorted(self._dir.glob("*.json"), reverse=True)
        for stale in files[limit:]:
            try:
                stale.unlink()
            except OSError:
                continue


def build_rule_section_text(rule: UserRuleConfig | SceneAnalysisRule) -> str:
    """Formats user rules as a compact prompt section."""
    if isinstance(rule, UserRuleConfig):
        lines = [f"{index}. {text}" for index, text in enumerate(rule.to_lines(), start=1)]
        if not lines:
            return ""
        return "【用户规则】\n" + "\n".join(lines)

    lines = [f"{index}. {text}" for index, text in enumerate(_legacy_rule_lines(rule), start=1)]
    if not lines:
        return ""
    return "【用户长期偏好规则】\n" + "\n".join(lines)


def build_scene_options_payload() -> list[dict[str, str]]:
    return [
        {
            "value": scene_type,
            "text": SCENE_LABELS.get(scene_type, scene_type),
        }
        for scene_type in _SCENE_TYPES
    ]
