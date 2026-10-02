-- 030: Материал стен + координаты
-- Material для стен, координаты 2D/3D

-- material для стен
ALTER TABLE room_measures ADD COLUMN material TEXT;

-- координаты стены (2D)
ALTER TABLE room_measures ADD COLUMN start_x REAL;
ALTER TABLE room_measures ADD COLUMN start_y REAL;
ALTER TABLE room_measures ADD COLUMN end_x REAL;
ALTER TABLE room_measures ADD COLUMN end_y REAL;

-- высота начала и конца (для наклонных)
ALTER TABLE room_measures ADD COLUMN start_z REAL;
ALTER TABLE room_measures ADD COLUMN end_z REAL;

-- 3D-координаты для проёмов
ALTER TABLE openings ADD COLUMN world_x REAL;
ALTER TABLE openings ADD COLUMN world_y REAL;
ALTER TABLE openings ADD COLUMN world_z REAL;

-- 3D-координаты для нишей
ALTER TABLE wall_niches ADD COLUMN world_x REAL;
ALTER TABLE wall_niches ADD COLUMN world_y REAL;
ALTER TABLE wall_niches ADD COLUMN world_z REAL;

-- 3D-координаты для коммуникаций
ALTER TABLE room_comms ADD COLUMN world_x REAL;
ALTER TABLE room_comms ADD COLUMN world_y REAL;
ALTER TABLE room_comms ADD COLUMN world_z REAL;
