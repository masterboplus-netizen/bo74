import { normalizeText } from '../nlu/normalize.js';
import { applyRules } from '../nlu/rules.js';
import { parseWithGroq } from '../nlu/groq.js';

export async function understand(text, context) {
  const cleanText = normalizeText(text);
  let intents = applyRules(cleanText);
  if (intents.length === 0 || intents[0].intent === 'unknown') {
    console.log('[Мозг] Правила не справились, спрашиваю Groq...');
    const groqIntents = await parseWithGroq(cleanText);
    if (groqIntents && groqIntents.length > 0) intents = groqIntents;
  }
  return intents;
}
