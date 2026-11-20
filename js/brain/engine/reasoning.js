export function buildPlan(intents, context) {
  const actions = [];
  const errors = [];
  for (const intent of intents) {
    if (intent.intent === 'unknown') {
      errors.push('Не понял фразу. Попробуйте переформулировать.');
      continue;
    }
    actions.push({ tool: intent.intent, payload: intent.slots });
  }
  if (errors.length > 0) return { status: 'error', errors };
  return { status: 'ok', actions };
}
