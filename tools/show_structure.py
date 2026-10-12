"""Структура файла: номер | отступ | код. Использование:
   python3 tools/show_structure.py <file> <from> <to>"""
import sys
path, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
lines = open(path, encoding="utf-8").read().split("\n")
for i, ln in enumerate(lines[a-1:b], start=a):
    indent = len(ln) - len(ln.lstrip(" "))
    print(f"{i:4d} | {indent:2d} | {ln.strip()[:80]}")
