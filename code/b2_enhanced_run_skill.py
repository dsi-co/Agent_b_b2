"""
b2_enhanced_run_skill.py — 简易增强版 B2 Skill 模块
===============================================

简易增强点:
  1. 简易错误分类: SkillError + error_code
  2. 简易风险等级: LOW / MEDIUM / HIGH + 超时限制
  3. 简易复合 Skill: pipeline 顺序执行 + $变量引用
  4. 简易限流: 滑动窗口
"""
from __future__ import annotations

import argparse, importlib, inspect, json, sys, time, threading
from pathlib import Path
from typing import Any
from common.io_utils import read_json, write_json, append_jsonl
from common.logging_utils import now_iso
from common.path_utils import DEFAULT_DATA_ROOT, bootstrap_project_root, resolve_cli_path
from common.schemas import make_skill_result

bootstrap_project_root()

# ═══════════════════════════════════════════════
# 1. 简易错误分类（3 大类 + 错误码）
# ═══════════════════════════════════════════════

ERR_CODES = {
    # INPUT
    "MISSING_PARAM": "INPUT-001", "INVALID_TYPE": "INPUT-002",
    "INVALID_VALUE": "INPUT-003", "FILE_NOT_FOUND": "INPUT-404",
    # EXEC
    "TIMEOUT": "EXEC-001", "RUNTIME": "EXEC-002",
    "PERMISSION": "EXEC-403", "COMPOSITE_STEP": "EXEC-010",
    # SYS
    "UNKNOWN_SKILL": "SYS-404", "RATE_LIMIT": "SYS-429",
}

class SkillError(Exception):
    def __init__(self, code_key: str, message: str, details: dict | None = None):
        self.code = ERR_CODES.get(code_key, "SYS-000")
        self.code_key = code_key
        self.msg = message
        self.details = details or {}
        super().__init__(f"[{self.code}] {message}")
    def to_dict(self):
        return {"code": self.code, "message": self.msg, "details": self.details}

# ═══════════════════════════════════════════════
# 2. 简易风险等级
# ═══════════════════════════════════════════════

class RiskLevel:
    LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"

RISK_CONFIG = {
    "calculator":         (RiskLevel.LOW,    60, 999),
    "format_converter":   (RiskLevel.LOW,    60, 999),
    "file_reader":        (RiskLevel.MEDIUM, 30, 60),
    "table_analyzer":     (RiskLevel.MEDIUM, 30, 60),
    "local_file_search":  (RiskLevel.MEDIUM, 30, 60),
    "local_file_search_enhanced": (RiskLevel.MEDIUM, 60, 30),
    "code_executor":      (RiskLevel.HIGH,   10, 10),
    "composite_skill":    (RiskLevel.HIGH,   30, 10),
}

# ═══════════════════════════════════════════════
# 3. 简易限流器
# ═══════════════════════════════════════════════

_lock = threading.Lock()
_call_log: dict[str, list[float]] = {}

def check_rate_limit(skill: str, max_per_min: int):
    if max_per_min >= 999:
        return
    now = time.monotonic()
    with _lock:
        log = _call_log.setdefault(skill, [])
        log[:] = [t for t in log if now - t < 60]
        if len(log) >= max_per_min:
            raise SkillError("RATE_LIMIT", f"'{skill}' 超过限流 ({max_per_min}/min)")
        log.append(now)

# ═══════════════════════════════════════════════
# 4. Skill 注册
# ═══════════════════════════════════════════════

SKILL_MODULES = {
    "calculator": "skills.calculator",
    "file_reader": "skills.file_reader",
    "local_file_search": "skills.local_file_search",
    "local_file_search_enhanced": "skills.local_file_search_enhanced",
    "table_analyzer": "skills.table_analyzer",
    "format_converter": "skills.format_converter",
    "code_executor": "skills.code_executor",
    "composite_skill": "skills.composite_skill",
}

def run_skill(skill: str, inp: dict, data_root: str = None, outdir: str = None) -> dict:
    if skill not in SKILL_MODULES:
        raise SkillError("UNKNOWN_SKILL", f"未知 skill: '{skill}'")
    risk, timeout, rate = RISK_CONFIG.get(skill, (RiskLevel.MEDIUM, 30, 60))
    check_rate_limit(skill, rate)

    mod = importlib.import_module(SKILL_MODULES[skill])
    func = getattr(mod, skill)
    kwargs = dict(inp)

    # 传入框架参数
    sig = inspect.signature(func)
    if "data_root" in sig.parameters:
        kwargs["data_root"] = data_root or str(DEFAULT_DATA_ROOT)
    if "output_dir" in sig.parameters:
        kwargs["output_dir"] = outdir

    # 高风险提示
    if risk == RiskLevel.HIGH:
        print(f"[!] 高风险 skill '{skill}' (timeout={timeout}s, 限流={rate}/min)", file=sys.stderr)

    # 超时执行
    start = time.perf_counter()
    if timeout < 60:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(1) as ex:
            fut = ex.submit(func, **kwargs)
            try:
                out = fut.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise SkillError("TIMEOUT", f"'{skill}' 执行超时 ({timeout}s)")
    else:
        out = func(**kwargs)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    return make_skill_result(skill, "success", inp, out, None, elapsed)

def run_skill_with_errors(skill: str, inp: dict, data_root: str = None, outdir: str = None) -> dict:
    """带异常捕获的 run_skill，将常见异常转为对应错误码"""
    try:
        return run_skill(skill, inp, data_root, outdir)
    except SkillError:
        raise
    except FileNotFoundError as e:
        raise SkillError("FILE_NOT_FOUND", f"文件未找到: {e}")
    except PermissionError as e:
        raise SkillError("PERMISSION", str(e))
    except Exception as e:
        raise SkillError("RUNTIME", f"{type(e).__name__}: {e}")

def run_skill_safe(skill: str, inp: dict, data_root: str = None, outdir: str = None) -> dict:
    """安全执行：任何异常都转为标准化 dict 返回"""
    try:
        return run_skill_with_errors(skill, inp, data_root, outdir)
    except SkillError as e:
        return make_skill_result(skill, "error", inp, None, e.to_dict(), 0)
    except Exception as e:
        return make_skill_result(skill, "error", inp, None,
            {"code": "SYS-000", "message": f"{type(e).__name__}: {e}", "details": {}}, 0)

# ═══════════════════════════════════════════════
# 5. 简易复合 Skill
# ═══════════════════════════════════════════════

def run_composite(pipeline: list[dict], data_root: str = None, outdir: str = None) -> dict:
    """顺序执行 pipeline，$var 引用上一步输出"""
    context = {}
    steps = []
    ok = True
    for idx, step in enumerate(pipeline):
        name = step.get("name", f"step{idx+1}")
        skill = step.get("skill")
        inp = dict(step.get("input", {}))
        out_var = step.get("output_var", f"r{idx+1}")
        if not skill:
            steps.append({"name": name, "status": "error", "error": "缺少 skill 字段"})
            ok = False; break

        # 变量替换（支持点号路径：$c.content）
        for k, v in inp.items():
            if isinstance(v, str) and v.startswith("$"):
                ref = v[1:]
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
                    steps.append({"name": name, "status": "error", "error": f"未找到变量 ${ref}"})
                    ok = False; break
        if not ok:
            break

        result = run_skill_safe(skill, inp, data_root, outdir)
        if result["status"] == "success":
            context[out_var] = result["output"]
        steps.append({"name": name, "skill": skill, "status": result["status"],
                       "error": result.get("error")})
        if result["status"] != "success":
            ok = False
            break

    return {"pipeline_status": "success" if ok else "error", "steps": steps,
            "context_keys": list(context.keys())}

# ═══════════════════════════════════════════════
# 6. CLI
# ═══════════════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(description="B2 简易增强版")
    p.add_argument("--skill", help="Skill 名称")
    p.add_argument("--input", help="输入 JSON 路径")
    p.add_argument("--outdir", help="输出目录")
    p.add_argument("--data_root")
    p.add_argument("--list", action="store_true", help="列出所有 Skill")
    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list:
        for s, mod in sorted(SKILL_MODULES.items()):
            risk, timeout, rate = RISK_CONFIG.get(s, (RiskLevel.MEDIUM, 30, 60))
            print(f"  {s:30s} risk={risk:6s} timeout={timeout}s  rate={rate}/min  [{mod}]")
        return 0
    if not args.skill:
        print("使用 --skill 指定 Skill 名称（--list 查看所有）", file=sys.stderr); return 1

    inp_path = resolve_cli_path(args.input)
    outdir = resolve_cli_path(args.outdir) if args.outdir else None
    inp = read_json(inp_path)
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    if args.skill == "composite_skill":
        result = run_composite(inp.get("pipeline", inp), args.data_root, str(outdir) if outdir else None)
        result = make_skill_result("composite_skill", result["pipeline_status"], inp, result, None, 0)
    else:
        result = run_skill_safe(args.skill, inp, args.data_root, str(outdir) if outdir else None)

    if outdir:
        path = outdir / f"{args.skill}_result.json"
        write_json(result, path)
        append_jsonl({"timestamp": now_iso(), "skill": args.skill, "status": result["status"],
                       "path": str(path)}, outdir / "skill_run.jsonl")
        print(path)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2

if __name__ == "__main__":
    raise SystemExit(main())
