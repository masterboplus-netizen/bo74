-- Привязка ЭОМ к помещению (этажу)
ALTER TABLE elec_groups ADD COLUMN floor_id INTEGER;
ALTER TABLE elec_supply ADD COLUMN floor_id INTEGER;

-- Распределение по фазам L1/L2/L3
ALTER TABLE elec_groups ADD COLUMN phase_l1 INTEGER DEFAULT 1;
ALTER TABLE elec_groups ADD COLUMN phase_l2 INTEGER DEFAULT 0;
ALTER TABLE elec_groups ADD COLUMN phase_l3 INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_groups_floor ON elec_groups(floor_id);
CREATE INDEX IF NOT EXISTS idx_groups_phase ON elec_groups(phase_l1, phase_l2, phase_l3);
