-- 020_room_height_points.sql — высота потолка в 3 точках (низ/центр/верх)
-- Нужно для учёта кривизны потолка (is_wavy для комнаты)

ALTER TABLE rooms ADD COLUMN height_bottom REAL;
ALTER TABLE rooms ADD COLUMN height_middle REAL;
ALTER TABLE rooms ADD COLUMN height_top REAL;
