#!/usr/bin/env python3
import sys
import argparse
from supabase import create_client

SUPABASE_URL = "https://ruomhtlvyqmaqhqqsfqn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1b21odGx2eXFtYXFocXFzZnFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzOTQwMjUsImV4cCI6MjEwODk3MDAyNX0.7FWm5KVmMqyVxNjXMhcGhgzb6nD8aLfie7cxBlohIO4"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_incident(project_id, title, symptom, solution, lesson, steps_list, session_id=None):
    # 1. Создаем сам инцидент
    res = supabase.table('worklog_incidents').insert([{
        'project_id': project_id,
        'title': title,
        'symptom': symptom,
        'solution': solution,
        'lesson': lesson,
        'session_id': session_id
    }]).execute()
    
    if not res.data:
        print("❌ ОШИБКА: Не удалось создать инцидент")
        sys.exit(1)
        
    incident_id = res.data[0]['id']
    print(f"✅ Инцидент создан (ID: {incident_id})")
    
    # 2. Добавляем шаги
    if steps_list:
        steps_payload = []
        for idx, step_str in enumerate(steps_list, 1):
            parts = step_str.split('|')
            action = parts[0] if len(parts) > 0 else ''
            result = parts[1] if len(parts) > 1 else ''
            steps_payload.append({
                'incident_id': incident_id,
                'step_number': idx,
                'action': action.strip(),
                'result': result.strip()
            })
        
        supabase.table('worklog_incident_steps').insert(steps_payload).execute()
        print(f"✅ Добавлено шагов: {len(steps_payload)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True, help="Проект (например, kheraborina)")
    parser.add_argument('--title', required=True, help="Краткое название ошибки")
    parser.add_argument('--symptom', required=True, help="Симптом (что именно сломалось)")
    parser.add_argument('--solution', required=True, help="Что помогло")
    parser.add_argument('--lesson', default='', help="Урок (что делать в будущем)")
    parser.add_argument('--session', default=None, help="ID сессии (если есть)")
    parser.add_argument('--steps', nargs='+', default=[], help="Шаги в формате 'Действие|Результат'")
    args = parser.parse_args()
    
    save_incident(args.project, args.title, args.symptom, args.solution, args.lesson, args.steps, args.session)
