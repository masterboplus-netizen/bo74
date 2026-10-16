#!/usr/bin/env python3
"""Сканер карты колбэков Бо 7.7.

Проходит по handlers/commands/ и interfaces/telegram/, собирает:
- Реестр callback_data: где формируется (кнопка) и где обрабатывается (роутер).
- Список try_handle (роутеры) в callbacks/*.
- Список text-доменов (text/*.py).
- Кнопки без обработчиков (потенциальные баги).

Использование:
    python3 tools/map_scan.py > docs/CODE_MAP_AUTO.md
"""
import re
from pathlib import Path

ROOTS = [Path("handlers/commands"), Path("interfaces/telegram"), Path(".")]


def scan_files():
    skip_dirs = {".venv", "venv", "worklog-app", "node_modules", ".git", "__pycache__", "tests"}
    for root in ROOTS:
        if not root.exists():
            continue
        for py in sorted(root.rglob("*.py")):
            parts = set(py.parts)
            if parts & skip_dirs:
                continue
            if ".bak" in py.name:
                continue
            yield py


def collect_callbacks():
    btn, handler = {}, {}
    for py in scan_files():
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r'callback_data=f?["\']([a-z_]+)', line):
                raw = m.group(1).rstrip("_")
                if raw:
                    btn.setdefault(raw, []).append((py.name, i))
            for m in re.finditer(r'data\s*==\s*["\']([a-z_]+)', line):
                raw = m.group(1).rstrip("_")
                if raw:
                    handler.setdefault(raw, []).append((py.name, i))
            for m in re.finditer(r'data\.startswith\(["\']([a-z_]+)', line):
                raw = m.group(1).rstrip("_")
                if raw:
                    handler.setdefault(raw, []).append((py.name, i))
            # Роутинг через replace("prefix_", "")
            for m in re.finditer(r'data\.replace\(["\']([a-z_]+)', line):
                raw = m.group(1).rstrip("_")
                if raw:
                    handler.setdefault(raw, []).append((py.name, i))
            # bot.py: CallbackQueryHandler(..., pattern="^prefix")
            for m in re.finditer(r'pattern=["\']\^?([a-z_|()\\.^$]+)', line):
                raw = m.group(1)
                # Берём только простой префикс (первое слово до | или ( или $)
                raw = re.split(r'[|()$\\]', raw)[0]
                if raw and raw.isascii() and raw.strip('_'):
                    handler.setdefault(raw.rstrip('_'), []).append((py.name, i))
    return btn, handler


def collect_routers():
    out = []
    cb_dir = Path("handlers/commands/callbacks")
    if cb_dir.exists():
        for py in sorted(cb_dir.glob("*.py")):
            n = py.read_text(encoding="utf-8").count("async def try_handle")
            if n:
                out.append((py.name, n))
    return out


def collect_text_domains():
    txt = Path("handlers/commands/text")
    if not txt.exists():
        return []
    return sorted(p.name for p in txt.glob("*.py") if p.name != "__init__.py")


def find_holes(btn, handler):
    """Кнопки без обработчика (потенциальные баги)."""
    holes = []
    for p in sorted(btn):
        matched = False
        for h in handler:
            if h == p or h.startswith(p + "_") or p.startswith(h + "_"):
                matched = True
                break
        if not matched:
            holes.append((p, btn[p][:2]))
    return holes


def main():
    btn, handler = collect_callbacks()
    routers = collect_routers()
    texts = collect_text_domains()
    holes = find_holes(btn, handler)

    print("# CODE_MAP_AUTO.md — авто-карта колбэков\n")
    print("> Сгенерировано: `python3 tools/map_scan.py`")
    print("> Не редактировать руками.\n")

    print("## Роутеры (handlers/commands/callbacks/*)\n")
    print("| Файл | try_handle |")
    print("|---|---|")
    for name, n in routers:
        print(f"| {name} | {n} |")

    print("\n## Text-домены (handlers/commands/text/*)\n")
    for name in texts:
        print(f"- `text/{name}`")

    print(f"\n## ⚠️ Кнопки БЕЗ обработчика ({len(holes)})\n")
    if holes:
        print("| Префикс | Где формируется |")
        print("|---|---|")
        for p, locs in holes:
            loc_s = ", ".join(f"{f}:{l}" for f, l in locs)
            print(f"| `{p}` | {loc_s} |")
    else:
        print("Все кнопки имеют обработчики ✅")

    all_prefixes = sorted(set(btn) | set(handler))
    print(f"\n## Реестр callback_data ({len(all_prefixes)} префиксов)\n")
    print("| Префикс | Кнопки | Обработчики |")
    print("|---|---|---|")
    for p in all_prefixes:
        b = btn.get(p, [])
        h = handler.get(p, [])
        b_s = ", ".join(f"{f}:{l}" for f, l in b[:3]) or "—"
        h_s = ", ".join(f"{f}:{l}" for f, l in h[:3]) or "—"
        print(f"| `{p}` | {b_s} | {h_s} |")


if __name__ == "__main__":
    main()
