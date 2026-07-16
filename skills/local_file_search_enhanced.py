"""
简易增强版 local_file_search：支持更多文件类型 + 正则搜索 + 大小写开关
"""
from __future__ import annotations
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from skills import resolve_data_path

EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".yaml", ".yml", ".html", ".xml", ".log"}

def local_file_search_enhanced(
    query: str, root_dir: str = "docs", file_types: list[str] | None = None,
    use_regex: bool = False, case_sensitive: bool = False, top_k: int = 10,
    snippet_radius: int = 80, max_depth: int = 5, *,
    data_root: str | None = None,
) -> dict:
    if not query or not query.strip():
        raise ValueError("query 不能为空")
    search_root, data_root_path = resolve_data_path(root_dir, data_root)
    if not search_root.is_dir():
        raise FileNotFoundError(f"目录不存在: {root_dir}")

    exts = {f".{e.lstrip('.')}" for e in (file_types or ["txt", "md"])}
    bad = exts - EXTENSIONS
    if bad:
        raise ValueError(f"不支持的类型: {bad}。支持: {sorted(EXTENSIONS)}")

    flags = 0 if case_sensitive else re.IGNORECASE
    if use_regex:
        pattern = re.compile(query, flags)
    else:
        terms = [re.escape(t) for t in query.strip().split()]
        pattern = re.compile("|".join(terms), flags)

    def search_file(fp: Path):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
            matches = pattern.findall(text)
            if not matches:
                return None
            # 摘要片段
            pos = text.lower().find(list(matches)[0].lower()) if matches else -1
            start = max(0, pos - snippet_radius)
            end = min(len(text), pos + snippet_radius) if pos >= 0 else snippet_radius
            snippet = ("..." if start > 0 else "") + text[start:end].replace("\n", " ").strip() + ("..." if end < len(text) else "")
            return {
                "path": fp.relative_to(data_root_path).as_posix(),
                "score": len(matches),
                "snippet": snippet,
                "size_kb": round(fp.stat().st_size / 1024, 1),
            }
        except Exception:
            return None

    files = [p for p in search_root.rglob("*") if p.is_file() and p.suffix.lower() in exts
             and (max_depth <= 0 or len(p.relative_to(search_root).parents) <= max_depth)]
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(search_file, files):
            if r:
                results.append(r)
    results.sort(key=lambda x: (-x["score"], x["path"]))
    return {"results": results[:top_k], "stats": {"total": len(files), "matched": len(results)}}
