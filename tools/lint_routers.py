#!/usr/bin/env python3
"""Линтер роутеров: висячие return, дубли if, структурные баги.

Использование:
    python3 tools/lint_routers.py <file.py> [<file.py> ...]
"""
import ast
import sys
from pathlib import Path


def analyze(path):
    src = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    src_lines = src.splitlines()

    routers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name in (
            "try_handle", "handle_callback", "handle_text"
        ):
            routers.append(node)

    if not routers:
        return None

    issues = []

    for fn in routers:
        fn_body_indent = 4
        for i, stmt in enumerate(fn.body):
            # return после try/except на уровне тела функции
            if isinstance(stmt, ast.Try):
                for j in range(i + 1, len(fn.body)):
                    s2 = fn.body[j]
                    if isinstance(s2, ast.Return):
                        line = src_lines[s2.lineno - 1]
                        indent = len(line) - len(line.lstrip())
                        val = s2.value
                        is_true = isinstance(val, ast.Constant) and val.value is True
                        if indent == fn_body_indent and is_true:
                            has_if = any(isinstance(s, ast.If) for s in fn.body[:j])
                            if has_if:
                                issues.append({
                                    "line": s2.lineno,
                                    "type": "hanging_return_true",
                                    "text": line.strip(),
                                    "msg": "return True после try/except на уровне try_handle — сработает для ЛЮБОГО callback"
                                })
                        break
            # return True вне if (но в теле try_handle) — БАГ, если выше были if.
            # return False вне if — норма (финальный "не моё").
            if isinstance(stmt, ast.Return):
                val = stmt.value
                is_true = isinstance(val, ast.Constant) and val.value is True
                if is_true:
                    has_if = any(isinstance(s, ast.If) for s in fn.body[:i])
                    if has_if:
                        line = src_lines[stmt.lineno - 1]
                        indent = len(line) - len(line.lstrip())
                        if indent == fn_body_indent:
                            issues.append({
                                "line": stmt.lineno,
                                "type": "hanging_return_true",
                                "text": line.strip(),
                                "msg": "return True вне if, но в теле try_handle — сработает для ЛЮБОГО callback"
                            })

    # Дубли if data == / startswith
    ifs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "data":
                if test.comparators and isinstance(test.comparators[0], ast.Constant):
                    ifs.append((node.lineno, "eq", test.comparators[0].value))
            if isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute):
                if test.func.attr == "startswith" and isinstance(test.func.value, ast.Name):
                    if test.func.value.id == "data" and test.args and isinstance(test.args[0], ast.Constant):
                        ifs.append((node.lineno, "prefix", test.args[0].value))

    seen = {}
    for ln, kind, val in ifs:
        key = (kind, val)
        if key in seen:
            issues.append({
                "line": ln, "type": "duplicate_if",
                "text": f'if data {"==" if kind == "eq" else ".startswith"} "{val}"',
                "msg": f"дубль: уже на строке {seen[key]}"
            })
        else:
            seen[key] = ln

    return {"file": path, "routers": [r.name for r in routers], "issues": issues}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total = 0
    for path in sys.argv[1:]:
        try:
            result = analyze(path)
        except Exception as e:
            print(f"\n📄 {path}: ОШИБКА {e}")
            continue
        if not result:
            continue
        print(f"\n📄 {result['file']}")
        print(f"   роутеры: {', '.join(result['routers'])}")
        if not result["issues"]:
            print("   ✅ чисто")
            continue
        for iss in result["issues"]:
            total += 1
            print(f"   ⚠️  L{iss['line']}: [{iss['type']}] {iss['msg']}")
            print(f"       → {iss['text']}")
    print(f"\n═══ Итого проблем: {total}")


if __name__ == "__main__":
    main()
