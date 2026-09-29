-- 022_measure_method.sql — инструмент для замеров (дальномер/рулетка/нивелир)
-- laser    — лазерный дальномер (ручной)
-- roulette — рулетка
-- level    — лазерный нивелир (штатив, горизонталь)

ALTER TABLE rooms ADD COLUMN measure_method TEXT DEFAULT 'laser';
