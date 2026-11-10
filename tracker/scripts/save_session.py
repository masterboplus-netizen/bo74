#!/usr/bin/env python3
import sys
import argparse
from supabase import create_client

SUPABASE_URL = "https://ruomhtlvyqmaqhqqsfqn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1b21odGx2eXFtYXFocXFzZnFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzOTQwMjUsImV4cCI6MjEwODk3MDAyNX0.7FWm5KVmMqyVxNjXMhcGhgzb6nD8aLfie7cxBlohIO4"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_or_create_phase(project_id, phase_name):
    # 1. Ищем эпик или модуль
    res = supabase.table('worklog_phases').select('id, name, parent_id').eq('project_id', project_id).eq('name', phase_name).execute()
    if res.data:
        return res.data[0]['id']
    
    # 2. Если не нашли — создаем как модуль (parent_id = null)
    print(f"⚠️ Эпик/модуль не найден: {phase_name}. Создаем новый...")
    res = supabase.table('worklog_phases').insert([{
        'name': phase_name,
        'project_id': project_id,
        'order_num': 99,
        'type': 'phase'
    }]).execute()
    if res.data:
        return res.data[0]['id']
    return None

def find_or_create_task(phase_id, task_name, status):
    # 1. Ищем задачу в этой фазе
    res = supabase.table('worklog_tasks').select('id').eq('phase_id', phase_id).eq('name', task_name).execute()
    if res.data:
        # Обновляем статус, если нашли
        supabase.table('worklog_tasks').update({'status': status}).eq('id', res.data[0]['id']).execute()
        return res.data[0]['id']
    
    # 2. Если не нашли — создаем
    print(f"⚠️ Задача не найдена: {task_name}. Создаем новую...")
    res = supabase.table('worklog_tasks').insert([{
        'phase_id': phase_id,
        'name': task_name,
        'status': status
    }]).execute()
    if res.data:
        return res.data[0]['id']
    return None

def save_session(date, start, end, project, note, events, screens, tasks_list):
    base_date_str = date.replace('-', '')
    existing = supabase.table('worklog_sessions').select('id').like('id', f's_{base_date_str}_%').execute()
    existing_ids = [s['id'] for s in existing.data]
    counter = 1
    while f"s_{base_date_str}_{counter}" in existing_ids:
        counter += 1
    session_id = f"s_{base_date_str}_{counter}"

    tasks_payload = []
    for task_str in tasks_list:
        parts = task_str.split(':')
        if len(parts) < 3:
            print(f"⚠️ Пропущена задача (неверный формат): {task_str}")
            continue
        phase_name, task_name, status = parts[0], parts[1], parts[2]
        phase_id = find_or_create_phase(project, phase_name)
        if not phase_id:
            print(f"❌ Не удалось создать/найти фазу: {phase_name}")
            continue
        task_id = find_or_create_task(phase_id, task_name, status)
        if not task_id:
            print(f"❌ Не удалось создать/найти задачу: {task_name}")
            continue
        tasks_payload.append({"phase": phase_name, "task": task_name, "status": status})

    payload = {
        "session_id": session_id,
        "project_id": project,
        "date": date,
        "start_time": start,
        "end_time": end,
        "duration_min": None,
        "events": events,
        "screens": screens,
        "note": note,
        "allow_create": False, # Уже создали вручную
        "tasks": tasks_payload
    }

    try:
        res = supabase.rpc('save_worklog_session', {'payload': payload}).execute()
        print(f"✅ УСПЕХ: Сессия {session_id} записана: {res.data}")
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
    args = parser.parse_args()

    save_session(args.date, args.start, args.end, args.project, args.note, args.events, args.screens, args.tasks)
