const SUPABASE_URL = "https://ruomhtlvyqmaqhqqsfqn.supabase.co";
export async function parseWithGroq(text) {
  try {
    const response = await fetch(`${SUPABASE_URL}/functions/v1/brain-parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!response.ok) throw new Error('Ошибка Edge Function');
    const data = await response.json();
    return data.intents || [];
  } catch (err) {
    console.error('[Groq] Ошибка:', err);
    return [];
  }
}
