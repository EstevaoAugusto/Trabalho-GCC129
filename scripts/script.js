// 1. Seleciona os elementos principais
const messageArea = document.getElementById('messageArea');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');

// 2. ESTADO GLOBAL DO PEDIDO
let currentOrder = []; 
let orderStatus = "aguardando_pedido"; 
let statusInterval = null; // Para guardar o timer de atualização de status

// 3. BASE DE CONHECIMENTO (MENU E AÇÕES)
const menuItems = {
    "espresso": { name: "Espresso", price: 5.00 },
    "latte": { name: "Latte Clássico", price: 12.00 },
    "cappuccino": { name: "Cappuccino", price: 10.00 },
    "mochaccino": { name: "Mochaccino", price: 14.00 },
    "pão de queijo": { name: "Pão de Queijo", price: 4.50 },
    "brownie": { name: "Brownie de Chocolate", price: 8.00 }
};

const knowledgeBase = {
    // Ações chave (sempre em minúsculas)
    "menu": "Temos **Espresso**, **Latte**, **Cappuccino**, **Mochaccino**, **Pão de Queijo** e **Brownie**. O que gostaria de adicionar?",
    "macchiato": "O Macchiato é um shot de espresso 'manchado' com uma pequena colher de espuma de leite. É forte e pequeno! (Não está no menu, mas posso sugerir um Latte).",
    "forma de pagamento": "Aceitamos Pix, cartão de crédito/débito e dinheiro.",
    "adicionar": "Qual item do menu você deseja adicionar ao seu pedido?",
    
    // Comando de Ação
    "carrinho": "show_cart_action",
    "finalizar": "finalize_order_action",
    "status": "check_status_action",

    // Resposta Padrão
    "default": "Desculpe, não entendi. Você pode pedir itens como **Latte** ou **Pão de Queijo**, ou perguntar pelo **Menu**."
};

/**
 * Funções de Lógica do Pedido
 */

function updateOrderStatus() {
    let nextStatus;
    const current = orderStatus;

    if (current === "aguardando_pedido") {
        nextStatus = "em_preparo";
        createMessage("🚨 <strong>ATUALIZAÇÃO:</strong> Seu pedido de #" + currentOrder.length + " itens acabou de entrar na fila de preparo!", 'bot');
    } else if (current === "em_preparo") {
        nextStatus = "pronto_para_retirada";
        createMessage("🎉 <strong>SEU PEDIDO ESTÁ PRONTO!</strong> 🎉 Por favor, retire no balcão de atendentes.", 'bot');
        clearInterval(statusInterval); // Para a atualização
    } else {
        nextStatus = "finalizado";
    }
    orderStatus = nextStatus;
}

function processOrderAction(action) {
    if (action === "show_cart_action") {
        if (currentOrder.length === 0) {
            return "Seu carrinho está vazio. Adicione um item, como um Latte!";
        }
        const total = currentOrder.reduce((sum, item) => sum + item.price, 0).toFixed(2);
        let cartItems = "<strong>🧾 SEU CARRINHO:</strong><br>";
        currentOrder.forEach(item => {
            cartItems += `• ${item.name} (R$ ${item.price.toFixed(2)})<br>`;
        });
        cartItems += `<br><strong>TOTAL: R$ ${total}</strong>. Deseja **Finalizar**?`;
        return cartItems;

    } else if (action === "finalize_order_action") {
        if (currentOrder.length === 0) {
            return "Você não pode finalizar um pedido vazio! Adicione algo primeiro.";
        }
        if (orderStatus !== "aguardando_pedido") {
            return "Seu pedido já está em andamento. Verifique o **Status**!";
        }
        
        // Simulação da imagem de registro + Início do Timer de Status
        const imageUrl = "https://i.imgur.com/gK9mD3w.png"; // Substitua pela sua imagem de confirmação
        const message = `✔️ Seu pedido (R$ ${currentOrder.reduce((sum, item) => sum + item.price, 0).toFixed(2)}) foi <strong>REGISTRADO!</strong>. Ele será preparado agora. <br><br><strong>Acompanhe o status!</strong>`;
        
        // Envia a mensagem com a imagem simulada
        createMessage(`${message}<br><img src="${imageUrl}" style="max-width: 100%; border-radius: 8px; margin-top: 10px;" alt="Pedido Registrado">`, 'bot');
        
        orderStatus = "em_preparo";
        // Define o timer para atualizar o status (2x: Preparo e Pronto)
        statusInterval = setInterval(updateOrderStatus, 7000); // Atualiza a cada 7 segundos (simulação)
        
        return null; // A mensagem já foi enviada

    } else if (action === "check_status_action") {
        if (orderStatus === "aguardando_pedido") {
            return "Seu pedido ainda não foi finalizado. Peça para **Finalizar** quando quiser.";
        }
        if (orderStatus === "em_preparo") {
            return "Seu pedido está sendo preparado pela equipe do Barista. Quase lá!";
        }
        if (orderStatus === "pronto_para_retirada") {
            return "Seu pedido está pronto no balcão! Não demore para buscar seu café! 😋";
        }
        return `O status atual do seu pedido é: <strong>${orderStatus.toUpperCase()}</strong>.`;
    }
}


/**
 * Funções de Utilitário do Chat
 */

function createMessage(text, type) {
    if (text.trim() === '') return;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type === 'user' ? 'user-message' : 'bot-message');
    messageDiv.innerHTML = text;
    messageArea.appendChild(messageDiv);
    messageArea.scrollTop = messageArea.scrollHeight;
}

function getBotResponse(userText) {
    const normalizedText = userText.toLowerCase().trim();

    // 1. TENTA ADICIONAR ITENS AO CARRINHO (se não estiver finalizado)
    if (orderStatus === "aguardando_pedido") {
        for (const itemKey in menuItems) {
            if (normalizedText.includes(itemKey)) {
                currentOrder.push(menuItems[itemKey]);
                return `Item adicionado! **${menuItems[itemKey].name}** (R$ ${menuItems[itemKey].price.toFixed(2)}) foi para o carrinho. Seu pedido tem ${currentOrder.length} itens.`;
            }
        }
    }


    // 2. VERIFICA AÇÕES E COMANDOS ESPECÍFICOS
    for (const key in knowledgeBase) {
        if (normalizedText.includes(key)) {
            const response = knowledgeBase[key];
            if (response.endsWith("_action")) {
                // Se for uma ação, executa a função de pedido
                return processOrderAction(response);
            }
            return response; // Resposta de conhecimento simples
        }
    }
    
    // 3. Resposta Padrão
    return knowledgeBase["default"];
}

function sendMessage() {
    const userText = userInput.value;
    if (userText.trim() === '') return;

    createMessage(userText, 'user');
    userInput.value = '';

    setTimeout(() => {
        const botResponse = getBotResponse(userText);
        if (botResponse) { // Evita criar mensagem se o processamento da ação já enviou
            createMessage(botResponse, 'bot');
        }
    }, 500);
}

// 4. Adiciona event listeners para Envio (Botão e Enter)
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// 5. Adiciona a funcionalidade de clique nos botões de sugestão
document.querySelectorAll('.suggestion-button').forEach(button => {
    button.addEventListener('click', function() {
        userInput.value = button.textContent;
        sendMessage(); 
    });
});