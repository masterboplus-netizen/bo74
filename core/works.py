"""core.works — виды работ (справочник)."""
from core.db import fetchone, fetchall, commit
import json


def add_work_type(code, name, category, unit='м²', norm_hours=None, norm_price=None, tools=None, materials=None):
    tools_json = json.dumps(tools or [], ensure_ascii=False)
    materials_json = json.dumps(materials or [], ensure_ascii=False)
    return commit(
        """INSERT INTO work_types
           (code, name, category, unit, norm_hours, norm_price, tools, materials)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, name, category, unit, norm_hours, norm_price, tools_json, materials_json)
    )


def get_work_type(work_id):
    row = fetchone("SELECT * FROM work_types WHERE id = ?", (work_id,))
    if not row:
        return None
    d = dict(row)
    if d.get('tools'):
        try: d['tools'] = json.loads(d['tools'])
        except: pass
    if d.get('materials'):
        try: d['materials'] = json.loads(d['materials'])
        except: pass
    return d


def get_work_types(category=None):
    if category:
        rows = fetchall("SELECT * FROM work_types WHERE category = ? ORDER BY name", (category,))
    else:
        rows = fetchall("SELECT * FROM work_types ORDER BY category, name")
    return [dict(r) for r in rows]


def update_work_type(work_id, **kwargs):
    allowed = {"code", "name", "category", "unit", "norm_hours", "norm_price"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(work_id)
    commit(f"UPDATE work_types SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_work_type(work_id):
    commit("DELETE FROM work_types WHERE id = ?", (work_id,))
    return True


def import_works_from_json(path):
    """Импорт видов работ из data/works.json."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            add_work_type(
                code=item.get('code') or item.get('name', '').lower().replace(' ', '_'),
                name=item.get('name'),
                category=item.get('category') or 'Прочее',
                unit=item.get('unit') or 'м²',
                norm_hours=item.get('norm_hours'),
                norm_price=item.get('norm_price'),
                tools=item.get('tools'),
                materials=item.get('materials'),
            )
            count += 1
        return count
    except Exception as e:
        print(f"⚠️ import_works: {e}")
        return 0
