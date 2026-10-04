-- Переводим elec_groups на floor_id (привязка к щиту этажа)
-- 1. Убедимся что floor_id есть (может уже быть)
-- 2. Создаём дефолтное помещение для объектов без помещений и привязываем группы

-- Привязываем все группы без floor_id к дефолтному этажу их объекта
UPDATE elec_groups
SET floor_id = (
    SELECT id FROM floors
    WHERE floors.object_id = elec_groups.object_id
    ORDER BY floor_number, id LIMIT 1
)
WHERE floor_id IS NULL;
