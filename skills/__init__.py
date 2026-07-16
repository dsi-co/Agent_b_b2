from __future__ import annotations

from pathlib import Path


DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def resolve_data_path(path: str, data_root: str | None = None) -> tuple[Path, Path]:
    root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes data root: {path}") from exc
    return candidate, root
# 注册所有 Skill 模块路径（增强版 B2 使用）
SKILL_MODULES: dict[str, str] = {
    "calculator": "skills.calculator",
    "file_reader": "skills.file_reader",
    "local_file_search": "skills.local_file_search",
    "local_file_search_enhanced": "skills.local_file_search_enhanced",
    "table_analyzer": "skills.table_analyzer",
    "format_converter": "skills.format_converter",
    "code_executor": "skills.code_executor",
    "composite_skill": "skills.composite_skill",
}