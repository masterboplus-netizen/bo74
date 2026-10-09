-- 049_task_soft_delete.sql
-- Soft delete задач: удаление в архив с восстановлением

ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(deleted_at);
