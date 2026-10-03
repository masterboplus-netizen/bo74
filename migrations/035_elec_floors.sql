-- Привязка групп к помещению (этажу)
ALTER TABLE elec_groups ADD COLUMN floor_id INTEGER;
ALTER TABLE elec_supply ADD COLUMN floor_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_groups_floor ON elec_groups(floor_id);
