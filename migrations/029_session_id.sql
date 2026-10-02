-- 029: session_id во все замеры
-- Все замеры привязаны к конкретной сессии

-- room_measures
ALTER TABLE room_measures ADD COLUMN session_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_measures_session ON room_measures(session_id);

-- openings
ALTER TABLE openings ADD COLUMN session_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_openings_session ON openings(session_id);

-- wall_niches
ALTER TABLE wall_niches ADD COLUMN session_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_niches_session ON wall_niches(session_id);

-- room_comms
ALTER TABLE room_comms ADD COLUMN session_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_comms_session ON room_comms(session_id);
