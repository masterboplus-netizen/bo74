-- 019_room_type.sql — тип помещения (черновая / чистовая / промежуточная)
-- rough  — черновая (замеры от стяжки/голых стен)
-- mid    — промежуточная (частично отделана)
-- finish — чистовая (замеры от финишной отделки)

ALTER TABLE rooms ADD COLUMN room_type TEXT DEFAULT 'rough';
