export function normalizeText(text) {
  if (!text) return '';
  let t = text.trim().toLowerCase().replace(/\s+/g, ' ');
  const numbers = {'один':'1','два':'2','три':'3','четыре':'4','пять':'5','шесть':'6','семь':'7','восемь':'8','девять':'9','десять':'10','двадцать':'20','тридцать':'30','сорок':'40','пятьдесят':'50'};
  for (const [word, num] of Object.entries(numbers)) t = t.replace(new RegExp(`\\b${word}\\b`, 'g'), num);
  return t;
}
