"""Parse AI responses into ticket snapshots."""
from __future__ import annotations

import json
import re

from .models import TicketSnapshot


class ResultParser:
    @staticmethod
    def parse(text: str) -> TicketSnapshot:
        raw = text.strip()
        md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if md_match:
            raw = md_match.group(1).strip()

        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return TicketSnapshot.from_dict(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        return TicketSnapshot.from_text(raw)
