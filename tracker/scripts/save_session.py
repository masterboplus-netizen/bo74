#!/usr/bin/env python3
import sys
import os
import argparse
from supabase import create_client

SUPABASE_URL = "https://ruomhtlvyqmaqhqqsfqn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1b21odGx2eXFtYXFocXFzZnFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzOTQwMjUsImV4cCI6MjEwODk3MDAyNX0.7FWm5KVmMqyVxNjXMhcGhgzb6nD8aLfie7cxBlohIO4"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TREES_PATH = "tracker/trees"

def find_or_create_phase(project_id, phase_name):
    res = supabase.table('worklog_phases').select('id').eq('project_id', project_id).eq('name', phase_name).execute()
    if res.data: return res.data[0]['id']
    print(f"⚠️ Эпик/модуль не найден: {phase_name}. Создаем новый...")
    res = supabase.table('worklog_phases').insert([{'name': phase_name, 'project_id': project_id, 'order_num': 99, 'type': 'phase'}]).execute()
    return res.data[0]['id'] if res.data else None

def find_or_create_task(phase_id, task_name, status):
    res = supabase.table('worklog_tasks').select('id').eq('phase_id', phase_id).eq('name', task_name).execute()
    if res.data:
        supabase.table('worklog_tasks').update({'status': status}).eq('id', res.data[0]['id']).execute()
        return res.data[0]['id']
    print(f"⚠️ Задача не найдена: {task_name}. Создаем новую...")
    res = supabase.table('worklog_tasks').insert([{'phase_id': phase_id, 'name': task_name, 'status': status}]).execute()
    return res.data[0]['id'] if res.data else None

def generate_tree(project_id):
    phases = supabase.table('worklog_phases').select('id, name, order_num, parent_id, type').eq('project_id', project_id).eq('is_archived', False).order('order_num').execute().data
    tasks = supabase.table('worklog_tasks').select('id, phase_id, name, status').eq('is_archived', False).execute().data
    subtasks = supabase.table('worklog_subtasks').select('id, task_id, name, status').execute().data
    
    tasks_by_phase = {}
    for t in tasks: tasks_by_phase.setdefault(t['phase_id'], []).append(t)
    subtasks_by_task = {}
    for st in subtasks: subtasks_by_task.setdefault(st['task_id'], []).append(st)
    
    lines = [f"=== ИЕРАРХИЯ ПРОЕКТА: {project_id} ===\n"]
    for p in phases:
        if p['parent_id'] is not None: continue
        lines.append(f"📁 МОДУЛЬ: {p['name']}")
        epics = [e for e in phases if e['parent_id'] == p['id']]
        if not epics:
            for t in tasks_by_phase.get(p['id'], []):
                status_icon = "✅" if t['status'] == 'done' else "🔄"
                lines.append(f"   {status_icon} Задача: {t['name']}")
                for st in subtasks_by_task.get(t['id'], []):
                    sub_status = "✅" if st['status'] == 'done' else "🔄"
                    lines.append(f"      {sub_status} Подзадача: {st['name']}")
        else:
            for e in epics:
                lines.append(f"   📂 ЭПИК: {e['name']}")
                for t in tasks_by_phase.get(e['id'], []):
                    status_icon = "✅" if t['status'] == 'done' else "🔄"
                    lines.append(f"      {status_icon} Задача: {t['name']}")
                    for st in subtasks_by_task.get(t['id'], []):
                        sub_status = "✅" if st['status'] == 'done' else "🔄"
                        lines.append(f"         {sub_status} Подзадача: {st['name']}")
        lines.append("")
    os.makedirs(TREES_PATH, exist_ok=True)
    path = os.path.join(TREES_PATH, f"worklog_tree_{project_id}.txt")
    with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(lines))
    print(f"✅ Дерево обновлено: {path}")

def generate_tags_tree():
    tags = supabase.table('worklog_tags').select('name, category, color').order('name').execute().data
    lines = ["=== СПРАВОЧНИК ТЕГОВ ===\n"]
    for t in tags:
        cat = t.get('category', 'без категории')
        lines.append(f"🏷️ {t['name']} (категория: {cat})")
    os.makedirs(TREES_PATH, exist_ok=True)
    path = os.path.join(TREES_PATH, "tags_tree.txt")
    with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(lines))
    print(f"✅ Дерево тегов обновлено: {path}")

def validate_tags(tags_list):
    if not tags_list: return
    allowed_tags = supabase.table('worklog_tags').select('name').execute().data
    allowed_names = {t['name'] for t in allowed_tags}
    for tag in tags_list:
        if tag not in allowed_names:
            print(f"❌ ОШИБКА: Тег '{tag}' не найден в справочнике.")
            print(f"Доступные теги: {', '.join(sorted(allowed_names))}")
            sys.exit(1)

def save_session(date, start, end, project, note, events, screens, tasks_list, subtasks_list, tags_list, errors_count=0, bugs_list=None):
    base_date_str = date.replace('-', '')
    existing = supabase.table('worklog_sessions').select('id').like('id', f's_{base_date_str}_%').execute()
    existing_ids = {s['id'] for s in existing.data}
    history = supabase.table('worklog_task_history').select('session_id').like('session_id', f's_{base_date_str}_%').execute()
    for h in history.data:
        if h.get('session_id'): existing_ids.add(h['session_id'])
    counter = 1
    while f"s_{base_date_str}_{counter}" in existing_ids: counter += 1
    session_id = f"s_{base_date_str}_{counter}"

    if not tags_list:
        print("❌ ОШИБКА: Укажите хотя бы один тег через --tags")
        sys.exit(1)
    validate_tags(tags_list)
    if not tasks_list:
        print("❌ ОШИБКА: Укажите хотя бы одну задачу через --tasks")
        sys.exit(1)

    tasks_payload = []
    for task_str in tasks_list:
        parts = task_str.split(':')
        if len(parts) < 3: continue
        phase_name, task_name, status = parts[0], parts[1], parts[2]
        task_time = int(parts[3]) if len(parts) > 3 else 0
        
        has_subtasks = False
        for sub_str in subtasks_list:
            sparts = sub_str.split('|')
            if len(sparts) >= 3:
                if sparts[0].strip() == phase_name.strip() and sparts[1].strip() == task_name.strip():
                    has_subtasks = True
                    break
        if has_subtasks: task_time = 0
        
        phase_id = find_or_create_phase(project, phase_name)
        if not phase_id: continue
        task_id = find_or_create_task(phase_id, task_name, status)
        if not task_id: continue
        
        task_obj = {"phase": phase_name, "task": task_name, "status": status, "duration_min": task_time, "subtasks": []}
        
        for sub_str in subtasks_list:
            sparts = sub_str.split('|')
            if len(sparts) >= 3:
                s_phase, s_task, s_name = sparts[0], sparts[1], sparts[2]
                status_time = sparts[3] if len(sparts) > 3 else 'done:0'
                if ':' in status_time:
                    s_status, s_time_str = status_time.split(':')
                    s_time = int(s_time_str)
                else:
                    s_status = status_time
                    s_time = 0
                
                if s_phase.strip() == phase_name.strip() and s_task.strip() == task_name.strip():
                    task_obj["subtasks"].append({"name": s_name.strip(), "status": s_status.strip(), "duration_min": s_time})
        tasks_payload.append(task_obj)

    total_task_time = 0
    for t in tasks_payload:
        total_task_time += t.get('duration_min', 0)
        for st in t.get('subtasks', []):
            total_task_time += st.get('duration_min', 0)

    start_h, start_m = map(int, start.split(':'))
    end_h, end_m = map(int, end.split(':'))
    if end_h < start_h:
        time_diff = (24 * 60 - (start_h * 60 + start_m)) + (end_h * 60 + end_m)
    else:
        time_diff = (end_h * 60 + end_m) - (start_h * 60 + start_m)

    if total_task_time != time_diff:
        print(f"❌ ОШИБКА: Сумма времени задач ({total_task_time} мин) не совпадает с разницей времени сессии ({time_diff} мин).")
        sys.exit(1)

    payload = {
        "session_id": session_id, "project_id": project, "date": date,
        "start_time": start, "end_time": end, "duration_min": total_task_time,
        "events": events, "screens": screens, "note": note,
        "allow_create": False, "tasks": tasks_payload, "tags": tags_list, 
        "errors_count": errors_count, "bugs": []
    }

    try:
        generate_tree(project)
        generate_tags_tree()
        res = supabase.rpc('save_worklog_session', {'payload': payload}).execute()
        print(f"✅ УСПЕХ: Сессия {session_id} записана")
        generate_tree(project)
        generate_tags_tree()
        print(f"\n📄 ДЕРЕВО ПРОЕКТА ГОТОВО: {TREES_PATH}/worklog_tree_{project}.txt")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--note', default='')
    parser.add_argument('--events', type=int, default=0)
    parser.add_argument('--screens', type=int, default=0)
    parser.add_argument('--tasks', nargs='+', default=[])
    parser.add_argument('--subtasks', nargs='+', default=[])
    parser.add_argument('--bugs', nargs='+', default=[])
    parser.add_argument('--tags', nargs='+', default=[])
    parser.add_argument('--errors', type=int, default=0)
    args = parser.parse_args()
    save_session(args.date, args.start, args.end, args.project, args.note, args.events, args.screens, args.tasks, args.subtasks, args.tags, args.errors, args.bugs)
