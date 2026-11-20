import { MasterBossBrain } from '../brain/index.js';
export function renderChat(container) {
  container.innerHTML = `
    <div style="display:flex; flex-direction:column; height:100%; background:#000; color:#fff; font-family:sans-serif;">
      <div id="chat-messages" style="flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:10px;">
        <div style="align-self:center; color:#888; font-size:12px; margin-bottom:10px;">Чат с Мозгом</div>
      </div>
      <div style="padding:10px; background:#111; border-top:1px solid #333; display:flex; gap:10px;">
        <input id="chat-input" type="text" placeholder="Напиши или скажи..." style="flex:1; padding:12px; border-radius:20px; border:none; background:#222; color:#fff; outline:none;">
        <button id="chat-mic" style="background:#333; color:#fff; border:none; width:44px; height:44px; border-radius:50%; cursor:pointer;">🎤</button>
        <button id="chat-send" style="background:#007aff; color:#fff; border:none; padding:0 20px; border-radius:20px; cursor:pointer; font-weight:bold;">→</button>
      </div>
    </div>`;
  const messagesDiv = container.querySelector('#chat-messages');
  const input = container.querySelector('#chat-input');
  const btnSend = container.querySelector('#chat-send');
  const btnMic = container.querySelector('#chat-mic');
  function addMessage(text, isUser) {
    const div = document.createElement('div');
    div.style.cssText = `max-width:80%; padding:12px 16px; border-radius:16px; font-size:14px; line-height:1.4; ${isUser ? 'align-self:flex-end; background:#007aff; color:#fff; border-bottom-right-radius:4px;' : 'align-self:flex-start; background:#333; color:#fff; border-bottom-left-radius:4px;'}`;
    div.textContent = text;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
  async function sendText() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMessage(text, true);
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'chat-loading';
    loadingDiv.style.cssText = 'align-self:flex-start; color:#888; font-style:italic; padding:10px;';
    loadingDiv.textContent = 'Мозг думает...';
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    try {
      const result = await MasterBossBrain.handle(text, { tenant_id: 1 });
      document.getElementById('chat-loading')?.remove();
      if (result.status === 'ok' || result.status === 'completed') {
        const msg = result.results ? result.results.map(r => r.message).join(', ') : 'Готово';
        addMessage('✅ ' + msg, false);
      } else if (result.status === 'error') {
        addMessage('⚠️ ' + (result.errors ? result.errors.join(', ') : 'Ошибка'), false);
      } else {
        addMessage('🤔 ' + JSON.stringify(result), false);
      }
    } catch (err) {
      document.getElementById('chat-loading')?.remove();
      addMessage('❌ Ошибка сети', false);
    }
  }
  btnSend.onclick = sendText;
  input.onkeypress = (e) => { if (e.key === 'Enter') sendText(); };
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.interimResults = false;
    btnMic.onclick = () => { btnMic.style.background = '#da3633'; recognition.start(); };
    recognition.onresult = (event) => { input.value = event.results[0][0].transcript; sendText(); };
    recognition.onend = () => { btnMic.style.background = '#333'; };
  } else {
    btnMic.style.display = 'none';
  }
}
