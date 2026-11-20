import { db } from '../api/supabase.js';
export async function executeActions(plan, context) {
  const results = [];
  for (const action of plan.actions) {
    try {
      let result;
      const tenant_id = context.tenant_id || 1;
      if (action.tool === 'add_task') {
        result = await db.from('tasks').insert([{ title: action.payload.title, status: 'open', priority: 'medium', tenant_id }]).select();
        results.push({ status: 'ok', message: `Задача создана: ${action.payload.title}` });
      } else if (action.tool === 'add_expense') {
        result = await db.from('finance').insert([{ amount: action.payload.amount || 0, category: action.payload.category, type: 'expense', date: new Date().toISOString(), tenant_id }]).select();
        results.push({ status: 'ok', message: `Расход добавлен: ${action.payload.amount}` });
      } else if (action.tool === 'create_object') {
        result = await db.from('objects').insert([{ name: action.payload.name, tenant_id }]).select();
        results.push({ status: 'ok', message: `Объект создан: ${action.payload.name}` });
      } else {
        results.push({ status: 'error', message: `Инструмент ${action.tool} не реализован` });
      }
    } catch (error) {
      results.push({ status: 'error', message: error.message });
    }
  }
  return { status: 'completed', results };
}
