"""
简易沙箱代码执行：import 白名单 + 超时控制 + stdout 捕获
"""
from __future__ import annotations
import ast, sys, threading, traceback
from io import StringIO

SAFE_IMPORTS = {"math", "json", "re", "random", "collections", "itertools",
                "functools", "statistics", "decimal", "datetime", "typing", "textwrap", "string"}

def code_executor(code: str, timeout_s: float = 5.0, variables: dict | None = None) -> dict:
    if not code or not isinstance(code, str):
        raise ValueError("code 必须是非空字符串")
    timeout_s = min(max(timeout_s, 1), 30)

    # AST 安全检查：禁止 exec/eval/open
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return {"stdout": "", "result": None, "execution_success": False, "error": f"语法错误: {e}"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("exec", "eval", "compile", "open", "__import__"):
                return {"stdout": "", "result": None, "execution_success": False,
                        "error": f"禁止使用 {node.func.id}()"}
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]]
            for m in mods:
                if m and m not in SAFE_IMPORTS:
                    return {"stdout": "", "result": None, "execution_success": False,
                            "error": f"禁止导入 '{m}'。允许: {sorted(SAFE_IMPORTS)}"}

    # 构建安全环境
    safe_builtins = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
    safe_globals = {"__builtins__": {k: safe_builtins[k] for k in safe_builtins
                     if k not in ("exec", "eval", "compile", "open", "__import__")}}
    safe_globals["__builtins__"]["__import__"] = lambda name, *a: (_ for _ in ()).throw(ImportError(f"禁止 {name}"))
    safe_locals = dict(variables or {})

    # 执行
    out = StringIO()
    old = sys.stdout; sys.stdout = out
    err, result = [None], [None]
    done = threading.Event()
    def run():
        try:
            exec(compile(tree, "<sandbox>", "exec"), safe_globals, safe_locals)
            result[0] = safe_locals.get("result")
        except Exception as e:
            err[0] = f"{type(e).__name__}: {e}"
        finally:
            done.set()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    sys.stdout = old
    if t.is_alive():
        return {"stdout": out.getvalue(), "result": None, "execution_success": False,
                "error": f"执行超时 ({timeout_s}s)"}
    return {"stdout": out.getvalue(), "result": result[0],
            "execution_success": err[0] is None, "error": err[0]}
