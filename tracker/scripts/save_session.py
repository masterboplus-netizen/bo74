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
    if res.data:
        return res.data[0]['id']
    print(f"⚠️ Эпик/модуль не найден: {phase_name}. Создаем новый...")
    res = supabase.table('worklog_phases').insert([{
        'name': phase_name, 'project_id': project_id, 'order_num': 99, 'type': 'phase'
    }]).execute()
    return res.data[0]['id'] if res.data else None

def find_or_create_task(phase_id, task_name, status):
    res = supabase.table('worklog_tasks').select('id').eq('phase_id', phase_id).eq('name', task_name).execute()
    if res.data:
        supabase.table('worklog_tasks').update({'status': status}).eq('id', res.data[0]['id']).execute()
        return res.data[0]['id']
    print(f"⚠️ Задача не найдена: {task_name}. Создаем новую...")
    res = supabase.table('worklog_tasks').insert([{
        'phase_id': phase_id, 'name': task_name, 'status': status
    }]).execute()
    return res.data[0]['id'] if res.data else None

def generate_tree(project_id):
    phases = supabase.table('worklog_phases').select('id, name, order_num, parent_id, type').eq('project_id', project_id).eq('is_archived', False).order('order_num').execute().data
    tasks = supabase.table('worklog_tasks').select('id, phase_id, name, status').execute().data
    tasks_by_phase = {}
    for t in tasks: tasks_by_phase.setdefault(t['phase_id'], []).append(t)
    
    lines = [f"=== ИЕРАРХИЯ ПРОЕКТА: {project_id} ===\n"]
    for p in phases:
        if p['parent_id'] is not None: continue
        lines.append(f"📁 МОДУЛЬ: {p['name']}")
        epics = [e for e in phases if e['parent_id'] == p['id']]
        if not epics:
            for t in tasks_by_phase.get(p['id'], []):
                status_icon = "✅" if t['status'] == 'done' else "🔄"
                lines.append(f"   {status_icon} Задача: {t['name']}")
        else:
            for e in epics:
                lines.append(f"   📂 ЭПИК: {e['name']}")
                for t in tasks_by_phase.get(e['id'], []):
                    status_icon = "✅" if t['status'] == 'done' else "🔄"
                    lines.append(f"      {status_icon} Задача: {t['name']}")
        lines.append("")

    os.makedirs(TREES_PATH, exist_ok=True)
    path = os.path.join(TREES_PATH, f"worklog_tree_{project_id}.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"✅ Дерево обновлено: {path}")


def generate_incidents_dump():
    try:
        incidents = supabase.table('worklog_incidents').select('*').order('id').execute().data
        if not incidents:
            return
            
        lines = ["=== ЖУРНАЛ ИНЦИДЕНТОВ ===\n"]
        for inc in incidents:
            lines.append(f"--- ИНЦИДЕНТ #{inc['id']}: {inc['title']} ---")
            lines.append(f"Дата: {inc['created_at'][:10]} | Проект: {inc['project_id']}")
            if inc.get('symptom'): lines.append(f"Симптом: {inc['symptom']}")
            
            steps = supabase.table('worklog_incident_steps').select('*').eq('incident_id', inc['id']).order('step_number').execute().data
            if steps:
                lines.append("Шаги диагностики:")
                for st in steps:
                    lines.append(f"  {st['step_number']}. {st['action']} -> {st['result']}")
            
            if inc.get('solution'): lines.append(f"Решение: {inc['solution']}")
            if inc.get('lesson'): lines.append(f"Урок: {inc['lesson']}")
            lines.append("-" * 50 + "\n")
            
        with open('tracker/incidents_dump.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"⚠️ Ошибка при создании дампа инцидентов: {e}")

def save_session(date, start, end, project, note, events, screens, tasks_list, subtasks_list, tags_list, errors_count=0):
    base_date_str = date.replace('-', '')
    existing = supabase.table('worklog_sessions').select('id').like('id', f's_{base_date_str}_%').execute()
    existing_ids = [s['id'] for s in existing.data]
    counter = 1
    while f"s_{base_date_str}_{counter}" in existing_ids: counter += 1
    session_id = f"s_{base_date_str}_{counter}"

    if not tags_list:
        print("❌ ОШИБКА: Укажите хотя бы один тег через --tags (например: #fix #ui)")
        sys.exit(1)
        
    if not tasks_list:
        print("❌ ОШИБКА: Укажите хотя бы одну задачу через --tasks (Фаза:Задача:Статус)")
        sys.exit(1)

    tasks_payload = []
    for task_str in tasks_list:
        parts = task_str.split(':')
        if len(parts) < 3: continue
        phase_name, task_name, status = parts[0], parts[1], parts[2]
        phase_id = find_or_create_phase(project, phase_name)
        if not phase_id: continue
        task_id = find_or_create_task(phase_id, task_name, status)
        if not task_id: continue
        
        task_obj = {"phase": phase_name, "task": task_name, "status": status, "subtasks": []}
        
        # Ищем подзадачи, которые относятся к этой фазе и задаче
        for sub_str in subtasks_list:
            sparts = sub_str.split('|')
            if len(sparts) >= 3:
                s_phase, s_task, s_name = sparts[0], sparts[1], sparts[2]
                s_status = sparts[3] if len(sparts) > 3 else 'done'
                if s_phase.strip() == phase_name.strip() and s_task.strip() == task_name.strip():
                    task_obj["subtasks"].append({"name": s_name.strip(), "status": s_status.strip()})
        
        tasks_payload.append(task_obj)

    payload = {
        "session_id": session_id, "project_id": project, "date": date,
        "start_time": start, "end_time": end, "duration_min": None,
        "events": events, "screens": screens, "note": note,
        "allow_create": False, "tasks": tasks_payload, "tags": tags_list, "errors_count": errors_count
    }

    try:
        res = supabase.rpc('save_worklog_session', {'payload': payload}).execute()
        print(f"✅ УСПЕХ: Сессия {session_id} записана: {res.data}")
        generate_tree(project)
        generate_incidents_dump()
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
    parser.add_argument('--tags', nargs='+', default=[], help="Список тегов, например: #fix #ui")
    parser.add_argument('--errors', type=int, default=0, help="Количество инцидентов (ошибок) за сессию")
    args = parser.parse_args()
    save_session(args.date, args.start, args.end, args.project, args.note, args.events, args.screens, args.tasks, args.subtasks, args.tags, args.errors)
