const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', function(e) {
  if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
  const message = userInput.value.trim();
  if (!message) return;

  appendMessage(`Você: ${message}`, 'user');
  userInput.value = '';

  // Resposta simulada do chatbot
  setTimeout(() => {
    const botReply = `Chatbot: Recebi sua mensagem: "${message}"`;
    appendMessage(botReply, 'bot');
  }, 500);
}

function appendMessage(msg, sender) {
  const messageElem = document.createElement('div');
  messageElem.textContent = msg;
  messageElem.className = sender;
  chatBox.appendChild(messageElem);
  chatBox.scrollTop = chatBox.scrollHeight;
}

