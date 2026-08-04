from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.knowledge_archive import migration as migration_module
from aica.knowledge_archive import migrate_legacy_knowledge_archive
from aica.models import TicketSummaryFields
from aica.todo.models import TodoConclusion, TodoItem, TodoStatus


def _write_note(
    path: Path,
    *,
    product_line: str,
    issue_product: str = "",
    feature_point: str = "",
    ticket_type: str = "排查类",
    ticket_version: str = "release_x",
    title: str = "示例文档",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{title}"',
                f'product_line: "{product_line}"',
                f'issue_product: "{issue_product}"',
                f'ticket_version: "{ticket_version}"',
                f'ticket_type: "{ticket_type}"',
                f'feature_point: "{feature_point}"',
                "---",
                "",
                "# body",
            ]
        ),
        encoding="utf-8",
    )


def test_migrate_legacy_knowledge_archive_moves_document_middle_notes(tmp_path: Path) -> None:
    source = tmp_path / "私网文档中台" / "release_x" / "排查类" / "问题.md"
    _write_note(
        source,
        product_line="私网文档中台",
        feature_point="文档中台-PUB-预览编辑-协作-预览异常",
    )
    (source.parent / "assets").mkdir(parents=True, exist_ok=True)
    (source.parent / "assets" / "shot.png").write_bytes(b"img")

    result = migrate_legacy_knowledge_archive(tmp_path)

    target = tmp_path / "文档中台" / "V7" / "release_x" / "排查类" / "问题.md"
    assert result.migrated_count == 1
    assert result.skipped_count == 0
    assert target.exists()
    assert "issue_product: \"文档中台\"" in target.read_text(encoding="utf-8")
    assert (target.parent / "assets" / "shot.png").exists()
    assert not source.exists()


def test_migrate_legacy_knowledge_archive_moves_document_center_notes(tmp_path: Path) -> None:
    source = tmp_path / "WPS协作（PC_Web端）" / "release_x" / "咨询类" / "问题.md"
    _write_note(
        source,
        product_line="WPS协作（PC_Web端）",
        feature_point="文档中心-云文档-预览跑版",
        ticket_type="咨询类",
    )

    result = migrate_legacy_knowledge_archive(tmp_path)

    target = tmp_path / "文档中心" / "V7" / "release_x" / "咨询类" / "问题.md"
    assert result.migrated_count == 1
    assert target.exists()
    assert "issue_product: \"文档中心\"" in target.read_text(encoding="utf-8")
    assert not source.exists()


def test_migrate_legacy_knowledge_archive_reports_unmapped_notes(tmp_path: Path) -> None:
    source = tmp_path / "WPS Comate" / "exp-v1.5.22" / "咨询类" / "问题.md"
    _write_note(
        source,
        product_line="WPS Comate",
        feature_point="未明确",
    )

    result = migrate_legacy_knowledge_archive(tmp_path)

    assert result.migrated_count == 0
    assert result.skipped_count == 1
    assert source.exists()
    assert not (tmp_path / "文档中台").exists()
    assert not (tmp_path / "文档中心").exists()


def test_migrate_legacy_knowledge_archive_moves_wps_collab_private_notes(tmp_path: Path) -> None:
    source = tmp_path / "私网WPS协作" / "release_dc_v7.0.2504b.20250424" / "咨询类" / "问题.md"
    _write_note(
        source,
        product_line="私网WPS协作",
        feature_point="暂时不支持该产品线匹配",
        ticket_type="咨询类",
        ticket_version="release_dc_v7.0.2504b.20250424",
    )

    result = migrate_legacy_knowledge_archive(tmp_path)

    target = tmp_path / "WPS协作（泛）" / "协作-私网" / "V7" / "release_dc_v7.0.2504b.20250424" / "咨询类" / "问题.md"
    assert result.migrated_count == 1
    assert target.exists()
    assert "issue_product: \"WPS协作（泛）/协作-私网\"" in target.read_text(encoding="utf-8")


def test_migrate_legacy_knowledge_archive_uses_title_fallback_for_wps_collab_notes(tmp_path: Path) -> None:
    source = tmp_path / "未提供" / "未提供" / "咨询类" / "WPS协作密码自助找回功能咨询.md"
    _write_note(
        source,
        product_line="未提供",
        feature_point="未明确",
        ticket_type="咨询类",
        ticket_version="未提供",
        title="WPS协作密码自助找回功能咨询",
    )

    result = migrate_legacy_knowledge_archive(tmp_path)

    target = tmp_path / "WPS协作（泛）" / "协作-私网" / "V7" / "未提供" / "咨询类" / "WPS协作密码自助找回功能咨询.md"
    assert result.migrated_count == 1
    assert target.exists()


def test_migrate_legacy_knowledge_archive_rebuilds_unmapped_notes_from_local_todo(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "未提供" / "未提供" / "排查类" / "访问ksops报404错误.md"
    _write_note(
        source,
        product_line="未提供",
        feature_point="未明确",
        ticket_type="排查类",
        ticket_version="未提供",
        title="访问ksops报404错误",
    )

    todo = TodoItem(
        id="todo-ksops",
        title="访问ksops报404错误",
        current_summary="访问ksops服务时返回404，网关为 mics-gateway。",
        status=TodoStatus.DONE,
        completed_at="2026-07-23T17:53:44",
        updated_at="2026-07-24T16:49:36",
        summary_fields=TicketSummaryFields(
            product_line="私有云文档",
            issue_product="文档中心/V7",
            ticket_type="排查类",
            ticket_version="release_dc_v7.0.2512.20251225",
            feature_point="文档中心-运维-ksops登录跳转失败",
            root_cause="环境问题",
            root_cause_desc="客户环境加固导致无法访问。",
        ),
        conclusion=TodoConclusion(content="客户环境加固了，导致无法访问。", updated_at="2026-07-23T17:53:44"),
    )

    monkeypatch.setattr(
        migration_module,
        "_lookup_todo_for_note",
        lambda archive_root, frontmatter: (todo, "title=访问ksops报404错误"),
    )

    result = migrate_legacy_knowledge_archive(tmp_path)

    target = tmp_path / "文档中心" / "V7" / "release_dc_v7.0.2512.20251225" / "排查类" / "访问ksops报404错误.md"
    assert result.migrated_count == 1
    assert result.skipped_count == 0
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert 'issue_product: "文档中心"' in content
    assert 'ticket_version: "release_dc_v7.0.2512.20251225"' in content
    assert "访问ksops服务时返回404" in content
    assert not source.exists()


def test_migrate_legacy_knowledge_archive_removes_orphan_legacy_root(tmp_path: Path) -> None:
    source = tmp_path / "未提供" / "未提供" / "咨询类" / "文档中台Excel在线浏览及API对接说明咨询.md"
    _write_note(
        source,
        product_line="未提供",
        feature_point="文档中台-PUB-功能咨询-接口文档-对接指导咨询",
        ticket_type="咨询类",
        ticket_version="未提供",
        title="文档中台Excel在线浏览及API对接说明咨询",
    )
    orphan_wiki = tmp_path / "未提供" / "_wiki" / "未提供 Wiki 索引.md"
    orphan_wiki.parent.mkdir(parents=True, exist_ok=True)
    orphan_wiki.write_text("- stale link", encoding="utf-8")

    result = migrate_legacy_knowledge_archive(tmp_path)

    assert result.migrated_count == 1
    assert not (tmp_path / "未提供").exists()
