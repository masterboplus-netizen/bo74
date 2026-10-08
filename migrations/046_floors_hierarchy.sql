-- 046_floors_hierarchy.sql
-- Фундамент: иерархия помещений + привязка щитов к помещениям

-- 1. Иерархия floors
ALTER TABLE floors ADD COLUMN parent_id INTEGER DEFAULT NULL;
ALTER TABLE floors ADD COLUMN type TEXT DEFAULT 'floor';
ALTER TABLE floors ADD COLUMN sort_order INTEGER DEFAULT 0;

-- 2. elec_panels — привязка к помещению
ALTER TABLE elec_panels ADD COLUMN floor_id INTEGER DEFAULT NULL;

-- 3. Индексы
CREATE INDEX IF NOT EXISTS idx_floors_parent ON floors(parent_id);
CREATE INDEX IF NOT EXISTS idx_floors_type ON floors(type);
CREATE INDEX IF NOT EXISTS idx_elec_panels_floor ON elec_panels(floor_id);
