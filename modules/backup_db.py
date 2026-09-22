"""Автобэкап базы данных Бо 7.4 — копия + git commit + push"""
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


WORKSPACE = Path("/home/runner/workspace")
BACKUP_DIR = WORKSPACE / "backups"
DB_PATH = WORKSPACE / "bo72.db"


def make_backup():
    """Создаёт копию БД в папке backups/"""
    BACKUP_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    backup_path = BACKUP_DIR / f"bo72_{date_str}.db"

    if not DB_PATH.exists():
        print(f"⚠️ БД не найдена: {DB_PATH}")
        return None

    shutil.copy2(DB_PATH, backup_path)
    size_kb = backup_path.stat().st_size / 1024
    print(f"✅ Бэкап создан: {backup_path.name} ({size_kb:.1f} KB)")
    return backup_path


def git_commit_and_push(message: str) -> bool:
    """Коммитит ТОЛЬКО базу и её бэкап, пушит в GitHub"""
    try:
        # git add — только БД и её бэкап-копия
        result = subprocess.run(
            ["git", "add", "bo72.db", "backups/"],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"⚠️ git add: {result.stderr}")
            return False

        # git commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                print("ℹ️ Нечего коммитить")
                return True
            print(f"⚠️ git commit: {result.stderr}")
            return False

        # git push
        result = subprocess.run(
            ["git", "push"],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"⚠️ git push: {result.stderr}")
            return False

        print("✅ Запушено в GitHub")
        return True
    except Exception as e:
        print(f"❌ Ошибка git: {e}")
        return False


def run_daily_backup():
    """Основная функция: создать бэкап + закоммитить + запушить"""
    print(f"\n🕒 Автобэкап БД: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    backup_path = make_backup()
    if not backup_path:
        return

    # Удаляем старые бэкапы (старше 30 дней)
    deleted = 0
    for old_backup in BACKUP_DIR.glob("bo72_*.db"):
        try:
            file_date_str = old_backup.stem.replace("bo72_", "")
            file_date = datetime.strptime(file_date_str, "%Y%m%d")
            if (datetime.now() - file_date).days > 30:
                old_backup.unlink()
                deleted += 1
        except Exception:
            pass
    if deleted:
        print(f"🗑️ Удалено старых бэкапов: {deleted}")

    # Git
    date_str = datetime.now().strftime("%Y-%m-%d")
    git_commit_and_push(f"backup: БД на {date_str}")


async def send_daily_backup(context):
    """Обёртка для job_queue — запускает бэкап в фоне"""
    try:
        run_daily_backup()
    except Exception as e:
        print(f"❌ Ошибка автобэкапа: {e}")


async def backup_now_command(update, context):
    """Команда /backup_now для ручного запуска бэкапа"""
    await update.message.reply_text("🔄 Запускаю бэкап БД...")
    try:
        run_daily_backup()
        await update.message.reply_text(
            "✅ Бэкап создан и запушен в GitHub.\n"
            "📁 Смотри папку `backups/` в репо."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
