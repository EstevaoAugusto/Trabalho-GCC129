    document.addEventListener("DOMContentLoaded", () => {
        const loginView = document.getElementById("login-view");
        const mainView = document.getElementById("main-view");
        const loginForm = document.getElementById("login-form");
        const loginError = document.getElementById("login-error");
        const userEmailSpan = document.getElementById("user-email");

        const chatForm = document.getElementById("chat-form");
        const chatInput = document.getElementById("chat-input");
        const chatMessages = document.getElementById("chat-messages");

        const iaResponse = document.getElementById("ia-response");
        const iaSuggestion = document.getElementById("ia-suggestion");
        const parsedItemsList = document.getElementById("parsed-items-list");
        const btnConfirmOrder = document.getElementById("btn-confirm-order");
        const btnCancelOrder = document.getElementById("btn-cancel-order");

        const postSuggestionButtons = document.getElementById("post-suggestion-buttons");
        const btnAddMore = document.getElementById("btn-add-more");
        const btnFinalizePostSuggestion = document.getElementById("btn-finalize-post-suggestion");
        const btnCancelPostSuggestion = document.getElementById("btn-cancel-post-suggestion");

        const orderStatusList = document.getElementById("order-status-list");

        const API_URL = "http://localhost:8000";
        let token = null;
        let ws = null;
        let currentParsedItems = [];
        let currentOrders = {};
        let currentItemSuggestion = null;
        let currentMenu = [];

        const STATUS_MAP = {
            0: "Recebido",
            1: "Em Produção",
            2: "Cancelado",
            3: "Pronto"
        };

        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            loginError.textContent = "";
            const email = document.getElementById("login-email").value;
            const password = document.getElementById("login-password").value;

            try {
                const formData = new URLSearchParams();
                formData.append("username", email);
                formData.append("password", password);

                const response = await fetch(`${API_URL}/users/token`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: formData
                });

                if (!response.ok) {
                    throw new Error("E-mail ou senha inválidos.");
                }

                const data = await response.json();
                token = data.access_token;
                
                // Buscar dados do usuário
                const userResponse = await fetch(`${API_URL}/users/me`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                const userData = await userResponse.json();
                
                if (userData.cargo !== 'cliente') {
                    throw new Error("Acesso negado. Esta área é apenas para clientes.");
                }

                userEmailSpan.textContent = userData.email;
                loginView.classList = "view inactive login"
                mainView.classList = "view active main"

                connectWebSocket();
            } catch (err) {
                loginError.textContent = err.message;
            }
        });

        function connectWebSocket() {
            ws = new WebSocket(`ws://localhost:8000/ws/${token}`);

            ws.onopen = () => {
                console.log("WebSocket conectado (Cliente).");
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log("WS Recebido (Cliente):", message);

                if (message.type === "status_update") {
                    updateOrderStatus(message.data);
                }
                else if (message.type === "menu") {
                    currentMenu = message.data || [];
                    let menuText = "Olá! Bem-vindo ao CoffeeNet! 😊\nNosso cardápio de hoje é:\n\n";
                    if (message.data && message.data.length > 0) {
                        message.data.forEach(product => {
                        if (product.em_promocao && product.preco_promocional != null) {
                            menuText += `- ${product.nome} (Promoção: R$ ${product.preco_promocional.toFixed(2)})\n`; // Mostra preço promo e risca o normal
                        } else {
                            menuText += `- ${product.nome} (R$ ${product.preco.toFixed(2)})\n`; // Mostra preço normal
                        }
                        });
                        menuText += "\nO que você gostaria de pedir?";
                    } else {
                        menuText = "Olá! Bem-vindo ao CoffeeNet! 😊\nDesculpe, estamos sem produtos no momento.";
                    }
                    addMessageToChat(menuText, "bot");
                    
                    const initialBotMessage = chatMessages.querySelector('.message.bot');
                    if (initialBotMessage && initialBotMessage.textContent.startsWith("Olá! O que você gostaria")) {
                        initialBotMessage.remove(); // Remove só se for a genérica
                    }
                }
                else if (message.type === "active_orders") {
                    orderStatusList.innerHTML = ""; 
                    if (message.data && message.data.length > 0) {
                        message.data.forEach(order => renderOrderCard(order));
                    }
                }
            };

            ws.onclose = () => {
                console.log("WebSocket desconectado (Cliente).");
            };

            ws.onerror = (err) => {
                console.error("WebSocket erro (Cliente):", err);
            };
        }
        
        
        function addMessageToChat(text, sender) {
            const msgDiv = document.createElement("div");
            msgDiv.className = `message ${sender}`;
            msgDiv.textContent = text;
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function handleIAResponse(data) {
            // Sempre mostra a recomendação de texto da IA
            addMessageToChat(data.recommendation, "bot");
            
            currentParsedItems = data.parsed_items || [];

            updateParsedItemsDisplay();

            iaResponse.classList.remove('hidden');

            suggestionButtons.classList.add('hidden');
            confirmButtons.classList.add('hidden');
            postSuggestionButtons.classList.add('hidden');
            chatForm.classList.add('hidden');
            chatInput.disabled = true; // Desabilita input enquanto espera ação

            // Decide quais botões mostrar baseado na 'intent'
            if (data.intent === "suggest" && data.suggested_item) {
                // IA fez uma sugestão específica
                currentItemSuggestion = data.suggested_item; // Guarda a sugestão
                suggestionButtons.classList.remove('hidden'); // Mostra botões SIM/NÃO/CANCELAR
            } else if (data.intent === "confirm" && currentParsedItems.length > 0) {
                // IA entendeu o pedido, não fez sugestão OU usuário já respondeu à sugestão
                confirmButtons.classList.remove('hidden'); // Mostra botões FINALIZAR/CANCELAR

                chatForm.classList.remove('hidden');   
                chatInput.disabled = false;
                chatInput.focus();
            } else {   
                // Mostra a mensagem da IA (já feito antes)
                
                // Garante que o input do chat esteja visível e habilitado
                chatForm.classList.remove('hidden'); 
                chatInput.disabled = false;
                chatInput.focus(); 

                if (currentParsedItems.length > 0) {
                    // Se AINDA TEM itens no carrinho, MANTENHA o bloco iaResponse visível
                    iaResponse.classList.remove('hidden'); 
                    // E mostre os botões de Finalizar/Cancelar para dar uma saída ao usuário
                    confirmButtons.classList.remove('hidden'); 
                } else {
                    // Se o carrinho está VAZIO e a IA pediu pra clarificar, aí sim esconde o bloco
                    iaResponse.classList.add('hidden'); 
                }
                
                suggestionButtons.classList.add('hidden');
                postSuggestionButtons.classList.add('hidden');
            }
        }

        function updateParsedItemsDisplay() {
            parsedItemsList.innerHTML = ""; 
            if (currentParsedItems.length > 0) {
                currentParsedItems.forEach(item => {
                    const li = document.createElement("li");
                    if (item.is_promo) {
                        li.textContent = `${item.quantidade}x ${item.nome} (Promo! R$ ${item.preco.toFixed(2)})`;
                    } else {
                        li.textContent = `${item.quantidade}x ${item.nome} (R$ ${item.preco.toFixed(2)})`; 
                    }
                    parsedItemsList.appendChild(li);
                });
                // Mostra o bloco de resposta se tiver itens (pode ter sido escondido no 'clarify')
                iaResponse.classList.remove('hidden'); 
            } else {
                // Esconde o bloco de resposta se a lista de itens ficar vazia (ex: após cancelar)
                iaResponse.classList.add('hidden'); 
            }
        }


        const suggestionButtons = document.getElementById("suggestion-buttons");
        const btnAcceptSuggestion = document.getElementById("btn-accept-suggestion");
        const btnRejectSuggestion = document.getElementById("btn-reject-suggestion");
        const btnCancelSuggestion = document.getElementById("btn-cancel-suggestion");

        btnAcceptSuggestion.addEventListener("click", () => {
            if (currentItemSuggestion) {
                const addedItemName = currentItemSuggestion.nome;
                // Adiciona o item sugerido à lista
                // Verifica se o item já existe para incrementar a quantidade
                let found = false;
                currentParsedItems = currentParsedItems.map(item => {
                    if (item.produto_id === currentItemSuggestion.produto_id) {
                        item.quantidade += currentItemSuggestion.quantidade;
                        found = true;
                    }
                    return item;
                });
                if (!found) {
                    currentParsedItems.push(currentItemSuggestion);
                }
                
                currentItemSuggestion = null; // Limpa a sugestão atual
                updateParsedItemsDisplay(); // Atualiza a lista na tela
                
                addMessageToChat(`Ok, adicionei ${addedItemName} ao seu pedido. O que deseja fazer agora?`, "bot");
                
                suggestionButtons.classList.add('hidden');
                postSuggestionButtons.classList.remove('hidden');
            }
        });

        btnRejectSuggestion.addEventListener("click", () => {
            currentItemSuggestion = null;

            addMessageToChat("Ok, sem o item extra. O que deseja fazer agora?", "bot");
            suggestionButtons.classList.add('hidden');
            postSuggestionButtons.classList.remove('hidden'); 
        });

        btnCancelSuggestion.addEventListener("click", () => {
            resetOrderProcess();
        });

        btnAddMore.addEventListener("click", () => {
            addMessageToChat("Ok, pode adicionar mais itens ou digite 'finalizar'.", "bot");
            postSuggestionButtons.classList.add('hidden'); 
            chatForm.classList.remove('hidden');        
            chatInput.disabled = false;
            chatInput.focus();
            confirmButtons.classList.remove('hidden');     // Mostra botões Finalizar/Cancelar originais
        });

        btnFinalizePostSuggestion.addEventListener("click", () => {
            postSuggestionButtons.classList.add('hidden'); // Esconde botões intermediários
            confirmOrderAndSend();                      // Chama a função de finalizar
        });

        btnCancelPostSuggestion.addEventListener("click", () => {
            postSuggestionButtons.classList.add('hidden'); // Esconde botões intermediários
            resetOrderProcess();                        // Chama a função de resetar
        });


        const confirmButtons = document.getElementById("confirm-buttons");

        btnConfirmOrder.addEventListener("click", async () => {
            confirmOrderAndSend(); 
        });

        btnCancelOrder.addEventListener("click", () => {
            resetOrderProcess();
        });
        
        async function confirmOrderAndSend() {
            iaResponse.classList.add('hidden'); 
            confirmButtons.classList.add('hidden');
            postSuggestionButtons.classList.add('hidden');
            chatForm.classList.remove('hidden');
            chatInput.disabled = false;

            if (currentParsedItems.length === 0) {
                addMessageToChat("Seu pedido está vazio. Digite algo para pedir.", "bot");
                return;
            }

            try {
                const itemsToSend = currentParsedItems.map(item => ({
                    produto_id: item.produto_id,
                    quantidade: item.quantidade 
                }));

                const response = await fetch(`${API_URL}/orders/confirm`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({ items: itemsToSend })
                });

                if (response.status === 409) {
                    const errorData = await response.json();
                    throw new Error(`Erro de estoque: ${errorData.detail}`);
                }
                
                if (!response.ok) {
                    let errorMsg = "Erro ao confirmar pedido.";
                    try {
                        const errData = await response.json();
                        errorMsg = errData.detail || errorMsg;
                    } catch(e) {  }
                    throw new Error(errorMsg);
                }

                const newOrder = await response.json();
                addMessageToChat("Seu pedido foi confirmado e enviado para a cozinha! 🎉", "bot");
                renderOrderCard(newOrder); // Mostra o card do pedido em andamento
                
                // Limpa o estado para um novo pedido
                currentParsedItems = []; 
                currentItemSuggestion = null;

            } catch (err) {
                addMessageToChat(`😥 Erro: ${err.message}`, "bot");
                // Volta a mostrar os botões de confirmar/cancelar para tentar de novo
                if (currentParsedItems.length > 0) {
                    confirmButtons.classList.remove('hidden'); 
                    iaResponse.classList.remove('hidden');
                }
                chatForm.classList.add('hidden'); // Esconde input em caso de erro
                chatInput.disabled = true;
                postSuggestionButtons.classList.add('hidden');
            }
        }

        const newChatFormListener = async (e) => { // Cria uma função nomeada
            e.preventDefault();
            const originalText = chatInput.value; // Guarda o texto original
            const text = originalText.trim().toLowerCase();
            if (!text) return;

            if (text === "cardapio" || text === "cardápio" || text === "menu") {
                addMessageToChat(originalText, "user"); 
                chatInput.value = "";

                // Formata e mostra o cardápio que já temos guardado
                let menuText = "Claro! Nosso cardápio atual é:\n\n";
                if (currentMenu && currentMenu.length > 0) {
                    currentMenu.forEach(product => {
                        if (product.em_promocao && product.preco_promocional != null) {
                            menuText += `- ${product.nome} (Promoção: R$ ${product.preco_promocional.toFixed(2)})\n`;
                        } else {
                            menuText += `- ${product.nome} (R$ ${product.preco.toFixed(2)})\n`;
                        }
                    });
                    menuText += "\nO que mais deseja pedir?";
                } else {
                    menuText = "Desculpe, parece que estamos sem produtos no momento.";
                }
                addMessageToChat(menuText, "bot"); 

                chatInput.disabled = false;
                chatForm.classList.remove('hidden');

                return; 
            }

            // Verifica se o usuário quer finalizar (APENAS se os botões de confirmação estiverem visíveis)
            if (!confirmButtons.classList.contains('hidden') && ["finalizar", "confirmar", "só isso", "eh so isso", "é só isso", "nao", "não"].includes(text)) {
                if (currentParsedItems.length > 0) {
                    addMessageToChat(originalText, "user"); 
                    chatInput.value = "";
                    confirmOrderAndSend(); 
                } else {
                    addMessageToChat("Seu pedido está vazio. Digite algo para pedir ou cancele.", "bot");
                }
                return;
            }

            // Se não for finalizar, continua com a chamada normal para /chat
            addMessageToChat(originalText, "user"); // Usa o valor original
            chatInput.value = "";
            chatInput.disabled = true;
            chatForm.classList.add('hidden'); // Esconde o form enquanto processa

            try {
                const response = await fetch(`${API_URL}/orders/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        text: originalText,
                        current_items: currentParsedItems.map(item => ({
                            produto_id: item.produto_id,
                            quantidade: item.quantidade
                        }))
                    })
                });

                if (!response.ok) {
                    let errorMsg = "Erro ao processar pedido.";
                    try {
                        const errData = await response.json();
                        errorMsg = errData.detail || errorMsg;
                    } catch(e) {}
                    throw new Error(errorMsg);
                }

                const data = await response.json();
                handleIAResponse(data);

            } catch (err) {
                addMessageToChat(`Erro: ${err.message}`, "bot");
                chatInput.disabled = false;
                chatForm.classList.remove('hidden');
            }
        };

        chatForm.addEventListener('submit', newChatFormListener);
        
        function resetOrderProcess() {
            currentParsedItems = [];
            currentItemSuggestion = null;
            updateParsedItemsDisplay(); 
            suggestionButtons.classList.add('hidden');
            confirmButtons.classList.add('hidden');
            postSuggestionButtons.classList.add('hidden');
            chatForm.classList.remove('hidden');
            chatInput.disabled = false;
            addMessageToChat("Pedido cancelado. Você pode começar de novo se quiser.", "bot");
        }

        
        function renderOrderCard(order) {
            let card = document.getElementById(`order-card-${order.id}`);
            if (!card) {
                card = document.createElement("div");
                card.className = "order-card";
                card.id = `order-card-${order.id}`;
                orderStatusList.prepend(card);
            }
            
            const itemsHtml = order.itens.map(item => 
                `<li>${item.quantidade}x ${item.produto.nome} (R$ ${item.preco_no_momento.toFixed(2)})</li>`
            ).join('');
            
            card.innerHTML = `
                <h3>Pedido #${order.id}</h3>
                <div id="status-display-${order.id}" class="order-card-status status-${order.status}">
                    ${STATUS_MAP[order.status]}
                </div>
                <ul>${itemsHtml}</ul>
                <p>Total: R$ ${order.total.toFixed(2)}</p>
            `;
            
            currentOrders[order.id] = order;

            // Se o pedido estiver Pronto ou Cancelado, remove depois de um tempo
            if (order.status === 2 || order.status === 3) {
                setTimeout(() => {
                    card.style.opacity = '0';
                    setTimeout(() => card.remove(), 500);
                }, 10000);
            }
        }
        
        function updateOrderStatus(order) {
            renderOrderCard(order);
            
            const statusText = STATUS_MAP[order.status];
            if (order.status !== 0) { // Não notifica "Recebido"
                addMessageToChat(`O status do seu Pedido #${order.id} foi atualizado para: ${statusText}`, "bot");
            }
        }
    });