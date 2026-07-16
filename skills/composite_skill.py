"""
简易复合 Skill：顺序执行 pipeline，$var 引用上一步输出
"""
from __future__ import annotations
import json, re
from typing import Any

def composite_skill(
    pipeline: list[dict], stop_on_failure: bool = True,
    data_root: str | None = None, output_dir: str | None = None
) -> dict:
    if not pipeline or not isinstance(pipeline, list):
        raise ValueError("pipeline 必须是非空列表")

    context: dict[str, Any] = {}
    steps: list[dict] = []
    ok = True

    for idx, step in enumerate(pipeline):
        name = step.get("name", f"step{idx+1:02d}")
        skill = step.get("skill")
        inp = {}; failed = False

        # 变量插值
        for k, v in (step.get("input") or {}).items():
            if isinstance(v, str) and v.startswith("$"):
                ref = v[1:]
                # 支持点号路径: $content.content
                parts = ref.split(".")
                val = context
                try:
                    for p in parts:
                        if isinstance(val, dict):
                            val = val[p]
                        else:
                            raise KeyError(p)
                    inp[k] = val
                except (KeyError, TypeError):
                    steps.append({"name": name, "skill": skill, "status": "error",
                                  "error": f"变量 '{ref}' 未找到"})
                    failed = True; break
            else:
                inp[k] = v
        if failed:
            ok = False; break

        # 调用 run_skill_safe
        from b2_enhanced_run_skill import run_skill_safe
        r = run_skill_safe(skill, inp, data_root, output_dir)
        out_var = step.get("output_var", f"r{idx+1:02d}")
        entry = {"name": name, "skill": skill, "status": r["status"]}
        if r["status"] == "success":
            context[out_var] = r["output"]
        else:
            entry["error"] = r.get("error")
            ok = False
        steps.append(entry)
        if not ok and stop_on_failure:
            break

    return {"pipeline_status": "success" if ok and all(s["status"] == "success" for s in steps) else "error",
            "steps": steps, "context_keys": list(context.keys())}
