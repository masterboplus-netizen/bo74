
import { renderChat } from './screens/chat.js';
const chatBtn = document.createElement('button');
chatBtn.textContent = '💬 Чат с Мозгом';
chatBtn.style.cssText = 'position:fixed; bottom:80px; right:20px; z-index:9999; background:#007aff; color:#fff; border:none; padding:12px 20px; border-radius:30px; font-weight:bold; box-shadow:0 4px 12px rgba(0,0,0,0.5);';
document.body.appendChild(chatBtn);

const chatContainer = document.createElement('div');
chatContainer.style.cssText = 'position:fixed; inset:0; z-index:10000; display:none;';
document.body.appendChild(chatContainer);

chatBtn.onclick = () => {
  chatContainer.style.display = 'block';
  renderChat(chatContainer);
};

