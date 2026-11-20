import { understand } from './engine/understanding.js';
import { buildPlan } from './engine/reasoning.js';
import { executeActions } from './engine/action.js';

export const MasterBossBrain = {
  plan: async function(text, context = {}) {
    if (!text) return { status: 'error', message: 'Пустой ввод' };
    const intents = await understand(text, context);
    return buildPlan(intents, context);
  },
  execute: async function(plan, context = {}) {
    if (plan.status !== 'ok') return plan;
    return await executeActions(plan, context);
  },
  handle: async function(text, context = {}) {
    const plan = await this.plan(text, context);
    if (plan.status !== 'ok') return plan;
    return await this.execute(plan, context);
  }
};
window.brainTest = async (text) => {
  console.log(`[ТЕСТ] Отправляю в мозг: "${text}"`);
  const result = await MasterBossBrain.handle(text, { tenant_id: 1 });
  console.log('[РЕЗУЛЬТАТ]', result);
  return result;
};
