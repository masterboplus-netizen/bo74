-- Миграция 028: размер щита (Ш×В×Г) для коммуникаций
ALTER TABLE room_comms ADD COLUMN size TEXT;
