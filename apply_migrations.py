"""Применение миграций БД Бо."""
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
DB_PATH = WORKSPACE / "bo72.db"
MIGRATIONS_DIR = WORKSPACE / "migrations"
BACKUP_DIR = WORKSPACE / "backups"

# 001 пропускаем — она уже в текущей БД
SKIP = {"001_initial.sql"}


def backup_db():
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"bo72_pre_migrations_{ts}.db"
    shutil.copy2(DB_PATH, backup)
    print(f"✅ Бэкап: {backup.name} ({backup.stat().st_size / 1024:.1f} KB)")
    return backup


def apply_migration(conn, path: Path) -> tuple:
    """Возвращает (ok, skipped, error)."""
    sql = path.read_text(encoding="utf-8")
    c = conn.cursor()
    statements = []
    current = []
    for line in sql.split("\n"):
        s = line.strip()
        if s.startswith("--") or not s:
            continue
        current.append(line)
        if s.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))

    applied = 0
    skipped = 0
    for stmt in statements:
        stmt_strip = stmt.strip().rstrip(";")
        if not stmt_strip:
            continue
        try:
            c.execute(stmt_strip)
            applied += 1
        except sqlite3.OperationalError as e:
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                skipped += 1
            else:
                return (False, skipped, f"{e}\n>>> {stmt_strip[:100]}")
    conn.commit()
    return (True, skipped, f"{applied} применено, {skipped} пропущено")


def main():
    if not DB_PATH.exists():
        print(f"❌ БД не найдена: {DB_PATH}")
        sys.exit(1)

    print(f"📦 БД: {DB_PATH.name}")
    print(f"📂 Миграций: {len(list(MIGRATIONS_DIR.glob('*.sql')))}")
    print()
    
    backup_db()
    print()

    conn = sqlite3.connect(str(DB_PATH))
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    results = []

    for path in files:
        if path.name in SKIP:
            print(f"⏭️  {path.name} — пропуск (уже в БД)")
            continue
        print(f"🔄 {path.name}...")
        ok, skipped, msg = apply_migration(conn, path)
        if not ok:
            print(f"❌ {path.name}: {msg}")
            conn.close()
            print(f"\n⚠️ Остановлено. Бэкап в backups/")
            sys.exit(1)
        print(f"✅ {path.name}: {msg}")
        results.append((path.name, msg))

    conn.close()
    print(f"\n🎉 Готово! Применено миграций: {len(results)}")


if __name__ == "__main__":
    main()
