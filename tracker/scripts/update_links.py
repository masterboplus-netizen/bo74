#!/usr/bin/env python3
import os

PROJECTS = {
    "bo-web": {
        "local_path": "~/workspace/bo-web",
        "repo_url": "https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main",
        "extensions": [".js", ".html", ".css", ".json"]
    },
    "worklog": {
        "local_path": "~/workspace/worklog-app",
        "repo_url": "https://raw.githubusercontent.com/masterboplus-netizen/worklog/main",
        "extensions": [".js", ".html", ".css", ".json"]
    },
    "bo74": {
        "local_path": "~/workspace",
        "repo_url": "https://raw.githubusercontent.com/masterboplus-netizen/bo74/main",
        "extensions": [".py", ".md"]
    }
}

# Новая папка для деревьев файлов
TREES_PATH = "tracker/file_trees"

def update_links():
    os.makedirs(TREES_PATH, exist_ok=True)

    for project_name, config in PROJECTS.items():
        local_path = os.path.expanduser(config["local_path"])
        repo_url = config["repo_url"]
        extensions = config["extensions"]

        if not os.path.exists(local_path):
            print(f"⚠️ Папка не найдена: {local_path}, пропускаем {project_name}")
            continue

        links = []
        for root, dirs, files in os.walk(local_path):
            # Игнорируем лишние папки
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'tracker']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, local_path)
                    rel_path = rel_path.replace("\\", "/")
                    link = f"{repo_url}/{rel_path}"
                    links.append(link)

        output_file = os.path.join(TREES_PATH, f"code_links_{project_name}.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"=== ССЫЛКИ НА КОД: {project_name} ===\n")
            f.write(f"Всего файлов: {len(links)}\n")
            f.write("=" * 40 + "\n\n")
            for link in sorted(links):
                f.write(link + "\n")
        
        print(f"✅ Ссылки для {project_name}: {output_file} ({len(links)} файлов)")

if __name__ == "__main__":
    update_links()
