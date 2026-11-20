export function applyRules(text) {
  const intents = [];
  const t = text.toLowerCase();
  const taskMatch = t.match(/(?:создай|добавь|надо|нужно|поставь)\s*задачу\s*(.+)/i);
  if (taskMatch) {
    intents.push({ intent: 'add_task', confidence: 0.9, slots: { title: taskMatch[1].trim() } });
    return intents;
  }
  const expenseMatch = t.match(/(?:потратил|купил|оплатил|расход)\s*(?:(\d+)\s*(?:руб|р|₽|тысяч)?)?\s*(?:на\s+)?(.+)/i);
  if (expenseMatch) {
    intents.push({ intent: 'add_expense', confidence: 0.85, slots: { amount: expenseMatch[1] ? parseInt(expenseMatch[1]) : null, category: expenseMatch[2] ? expenseMatch[2].trim() : 'Прочее' } });
    return intents;
  }
  const objectMatch = t.match(/(?:создай|добавь)\s*объект\s+(.+)/i);
  if (objectMatch) {
    intents.push({ intent: 'create_object', confidence: 0.9, slots: { name: objectMatch[1].trim() } });
    return intents;
  }
  return [{ intent: 'unknown', confidence: 0.1, slots: { raw: text } }];
}
