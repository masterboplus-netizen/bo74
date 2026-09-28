-- 007: Расширения объектов (дома, ЖК, земля, владение)

ALTER TABLE objects ADD COLUMN object_type TEXT DEFAULT 'apartment';
ALTER TABLE objects ADD COLUMN ownership_type TEXT DEFAULT 'client';
ALTER TABLE objects ADD COLUMN area_total REAL;
ALTER TABLE objects ADD COLUMN area_living REAL;
ALTER TABLE objects ADD COLUMN floors INTEGER;
ALTER TABLE objects ADD COLUMN year_built INTEGER;
ALTER TABLE objects ADD COLUMN wall_type TEXT;
ALTER TABLE objects ADD COLUMN foundation TEXT;
ALTER TABLE objects ADD COLUMN cadastral_number TEXT;
ALTER TABLE objects ADD COLUMN city TEXT;
ALTER TABLE objects ADD COLUMN district TEXT;
ALTER TABLE objects ADD COLUMN metro TEXT;
ALTER TABLE objects ADD COLUMN geo_lat REAL;
ALTER TABLE objects ADD COLUMN geo_lon REAL;
ALTER TABLE objects ADD COLUMN land_area REAL;
ALTER TABLE objects ADD COLUMN has_gas INTEGER DEFAULT 0;
ALTER TABLE objects ADD COLUMN has_water INTEGER DEFAULT 0;
ALTER TABLE objects ADD COLUMN has_electric INTEGER DEFAULT 0;
ALTER TABLE objects ADD COLUMN has_sewer INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(object_type);
CREATE INDEX IF NOT EXISTS idx_objects_ownership ON objects(ownership_type);
CREATE INDEX IF NOT EXISTS idx_objects_city ON objects(city);

-- Юниты в здании (ЖК, офисные центры)
CREATE TABLE IF NOT EXISTS building_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    unit_number TEXT,
    floor INTEGER,
    section TEXT,
    area REAL,
    rooms_count INTEGER,
    owner_id INTEGER,
    status TEXT DEFAULT 'empty',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(building_id, unit_number)
);
CREATE INDEX IF NOT EXISTS idx_units_building ON building_units(building_id);
CREATE INDEX IF NOT EXISTS idx_units_status ON building_units(status);

-- Земельные участки
CREATE TABLE IF NOT EXISTS land_plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    cadastral_number TEXT,
    area_sqm REAL,
    category TEXT,
    permitted_use TEXT,
    has_electric INTEGER DEFAULT 0,
    has_gas INTEGER DEFAULT 0,
    has_water INTEGER DEFAULT 0,
    has_sewer INTEGER DEFAULT 0,
    distance_to_city INTEGER,
    geo_lat REAL,
    geo_lon REAL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_land_object ON land_plots(object_id);
CREATE INDEX IF NOT EXISTS idx_land_cadastral ON land_plots(cadastral_number);
