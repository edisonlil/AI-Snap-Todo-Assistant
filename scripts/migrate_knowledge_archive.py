from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.knowledge_archive import migrate_legacy_knowledge_archive


def main() -> int:
    archive_root = Path.home() / ".aica" / "knowledge_base"
    result = migrate_legacy_knowledge_archive(archive_root)

    target_counts = Counter(record.target_root for record in result.migrated if record.moved)
    report_path = archive_root / f"migration-report-{datetime.now().date().isoformat()}.md"
    report_lines = [
        "# 归档迁移报告",
        "",
        f"- 归档根目录：`{archive_root}`",
        f"- 已迁移：{result.migrated_count}",
        f"- 未迁移：{result.skipped_count}",
        "",
        "## 迁移统计",
        "",
    ]
    for target_root, count in sorted(target_counts.items()):
        report_lines.append(f"- `{target_root}`: {count}")
    if not target_counts:
        report_lines.append("- 无")
    report_lines.extend([
        "",
        "## 未迁移",
        "",
    ])
    if result.skipped:
        for item in result.skipped:
            report_lines.append(f"- `{item.source_path.relative_to(archive_root)}`: {item.reason}")
    else:
        report_lines.append("- 无")

    report_path.write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")
    print(f"migrated={result.migrated_count}")
    print(f"skipped={result.skipped_count}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
