"""core.stages — этапы ремонта (справочник + этапы объекта)."""
from core.db import fetchone, fetchall, commit


def add_stage(code, name, description=None, order_num=0, typical_days=None):
    return commit(
        """INSERT INTO work_stages (code, name, description, order_num, typical_days)
           VALUES (?, ?, ?, ?, ?)""",
        (code, name, description, order_num, typical_days)
    )


def get_stage(stage_id):
    row = fetchone("SELECT * FROM work_stages WHERE id = ?", (stage_id,))
    return dict(row) if row else None


def get_stages():
    rows = fetchall("SELECT * FROM work_stages ORDER BY order_num, id")
    return [dict(r) for r in rows]


def update_stage(stage_id, **kwargs):
    allowed = {"code", "name", "description", "order_num", "typical_days"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(stage_id)
    commit(f"UPDATE work_stages SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_stage(stage_id):
    commit("DELETE FROM work_stages WHERE id = ?", (stage_id,))
    return True


# === ЭТАПЫ ОБЪЕКТА ===

def add_object_stage(object_id, stage_id, status='pending'):
    return commit(
        """INSERT INTO object_stages (object_id, stage_id, status)
           VALUES (?, ?, ?)""",
        (object_id, stage_id, status)
    )


def get_object_stages(object_id):
    rows = fetchall(
        """SELECT os.*, ws.name as stage_name, ws.code as stage_code
           FROM object_stages os
           LEFT JOIN work_stages ws ON os.stage_id = ws.id
           WHERE os.object_id = ?
           ORDER BY ws.order_num""",
        (object_id,)
    )
    return [dict(r) for r in rows]


def update_object_stage(stage_row_id, **kwargs):
    allowed = {"status", "started_at", "completed_at", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(stage_row_id)
    commit(f"UPDATE object_stages SET {', '.join(fields)} WHERE id = ?", params)
    return True


def import_stages_from_spec():
    """Импорт этапов из core/spec.py (WORK_STAGES)."""
    from core.spec import WORK_STAGES
    count = 0
    for i, (code, (name, days)) in enumerate(WORK_STAGES.items(), start=1):
        add_stage(code=code, name=name, order_num=i, typical_days=days)
        count += 1
    return count
