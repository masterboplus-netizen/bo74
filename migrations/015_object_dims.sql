-- 015: Точные габариты объектов + зоны обслуживания

-- === ТОЧНЫЕ ГАБАРИТЫ (каталог / факт / упаковка) ===
ALTER TABLE room_objects ADD COLUMN dim_catalog_length REAL;
ALTER TABLE room_objects ADD COLUMN dim_catalog_width REAL;
ALTER TABLE room_objects ADD COLUMN dim_catalog_height REAL;

ALTER TABLE room_objects ADD COLUMN dim_actual_length REAL;
ALTER TABLE room_objects ADD COLUMN dim_actual_width REAL;
ALTER TABLE room_objects ADD COLUMN dim_actual_height REAL;

ALTER TABLE room_objects ADD COLUMN dim_shipping_length REAL;
ALTER TABLE room_objects ADD COLUMN dim_shipping_width REAL;
ALTER TABLE room_objects ADD COLUMN dim_shipping_height REAL;

-- === ВЫПИРАНИЯ (люк, консоль, ручки) ===
ALTER TABLE room_objects ADD COLUMN dim_front_protrusion REAL;
ALTER TABLE room_objects ADD COLUMN dim_top_protrusion REAL;
ALTER TABLE room_objects ADD COLUMN dim_side_protrusion REAL;

-- === ЗАЗОРЫ ДЛЯ ВСТРАИВАНИЯ ===
ALTER TABLE room_objects ADD COLUMN clearance_front REAL DEFAULT 0.02;
ALTER TABLE room_objects ADD COLUMN clearance_top REAL DEFAULT 0.02;
ALTER TABLE room_objects ADD COLUMN clearance_sides REAL DEFAULT 0.01;

-- === МОНТАЖ / ОБСЛУЖИВАНИЕ ===
ALTER TABLE room_objects ADD COLUMN is_builtin INTEGER DEFAULT 0;
ALTER TABLE room_objects ADD COLUMN opening_direction TEXT;
ALTER TABLE room_objects ADD COLUMN cable_length REAL;
ALTER TABLE room_objects ADD COLUMN hose_length REAL;

-- === ЗОНЫ ОБСЛУЖИВАНИЯ (сколько места надо оставить) ===
ALTER TABLE room_objects ADD COLUMN service_zone_front REAL DEFAULT 0;
ALTER TABLE room_objects ADD COLUMN service_zone_side REAL DEFAULT 0;
ALTER TABLE room_objects ADD COLUMN service_zone_top REAL DEFAULT 0;

-- === ДЕМОНТАЖ (что снять первым) ===
ALTER TABLE room_objects ADD COLUMN needs_removal INTEGER DEFAULT 0;
ALTER TABLE room_objects ADD COLUMN blocking_objects TEXT;
ALTER TABLE room_objects ADD COLUMN removable_by INTEGER;

-- === ТИП ФАКТИЧЕСКОГО РАЗМЕРА ===
ALTER TABLE room_objects ADD COLUMN dim_source TEXT;
ALTER TABLE room_objects ADD COLUMN dim_notes TEXT;

CREATE INDEX IF NOT EXISTS idx_roomobj_builtin ON room_objects(is_builtin);
CREATE INDEX IF NOT EXISTS idx_roomobj_removal ON room_objects(needs_removal);
