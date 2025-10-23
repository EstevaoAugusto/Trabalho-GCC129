document.addEventListener("DOMContentLoaded", () => {
    const loginView = document.getElementById("login-view");
    const mainView = document.getElementById("main-view");
    const loginForm = document.getElementById("login-form");
    const loginError = document.getElementById("login-error");
    const userEmailSpan = document.getElementById("user-email");
    
    const containers = {
        0: document.getElementById("container-0"), // Recebido
        1: document.getElementById("container-1"), // Em Produção
    };
    
    const counters = {
         0: document.querySelector("#col-recebido h2"),
         1: document.querySelector("#col-em-producao h2"),
    };
    
    const baseCounterText = {
         0: "Recebidos",
         1: "Em Produção"
    };

    const productView = document.getElementById("product-view");
    const btnGotoProducts = document.getElementById("btn-goto-products");
    const btnBackToKanban = document.getElementById("btn-back-to-kanban");
    const btnAddNewProduct = document.getElementById("btn-add-new-product");
    const productForm = document.getElementById("product-form");
    const productFormTitle = document.getElementById("form-title");
    const productIdInput = document.getElementById("product-id");
    const productNameInput = document.getElementById("product-nome");
    const productPriceInput = document.getElementById("product-preco");
    const productCategoryInput = document.getElementById("product-categoria");
    const productKeywordsInput = document.getElementById("product-keywords");
    const productStockInput = document.getElementById("product-estoque");
    const btnSaveProduct = document.getElementById("btn-save-product");
    const btnCancelEdit = document.getElementById("btn-cancel-edit");
    const productListBody = document.getElementById("product-list-body");
    const promotionModal = document.getElementById("promotion-modal");
    const promoProductIdInput = document.getElementById("promo-product-id");
    const promoPriceInput = document.getElementById("promo-price");
    const btnSavePromotion = document.getElementById("btn-save-promotion");
    const btnCancelPromotion = document.getElementById("btn-cancel-promotion");

    const API_URL = "http://localhost:8000";
    let token = null;
    let ws = null;
    let currentProducts = [];

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

            const userResponse = await fetch(`${API_URL}/users/me`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const userData = await userResponse.json();
            
            if (userData.cargo !== 'cozinheiro') {
                 throw new Error("Acesso negado. Esta área é apenas para a cozinha.");
            }

            userEmailSpan.textContent = userData.email;
            loginView.classList.remove("active");
            mainView.classList.add("active");

            connectWebSocket();

        } catch (err) {
            loginError.textContent = err.message;
        }
    });
    
    function connectWebSocket() {
        ws = new WebSocket(`ws://localhost:8000/ws/${token}`);

        ws.onopen = () => {
            console.log("WebSocket conectado (Cozinha).");
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log("WS Recebido (Cozinha):", message);

            if (message.type === "initial_state") {
                message.data.forEach(order => renderOrderCard(order));
                updateCounters();
            } else if (message.type === "new_order") {
                renderOrderCard(message.data);
                 updateCounters();
            } else if (message.type === "status_update") {
                handleStatusUpdate(message.data);
                 updateCounters();
            }
        };

        ws.onclose = () => {
            console.log("WebSocket desconectado (Cozinha).");
        };

        ws.onerror = (err) => {
            console.error("WebSocket erro (Cozinha):", err);
        };
    }
    
    function renderOrderCard(order) {
        // ignora pedidos prontos ou cancelados
        if (order.status > 1) return;
        
        const container = containers[order.status];
        if (!container) return;
        
        let card = document.getElementById(`order-card-${order.id}`);
        if (!card) {
            card = document.createElement("div");
            card.className = "order-card";
            card.id = `order-card-${order.id}`;
        }
        
        const itemsHtml = order.itens.map(item => 
            `<li>${item.quantidade}x ${item.produto.nome}</li>`
        ).join('');
        
        // Botões de ação baseados no status
        let actionsHtml = '';
        if (order.status === 0) { // Recebido
            actionsHtml = `
                <button class="btn-producao" data-id="${order.id}" data-status="1">Iniciar Produção</button>
            `;
        } else if (order.status === 1) { // Em Produção
             actionsHtml = `
                <button class="btn-pronto" data-id="${order.id}" data-status="3">Pronto</button>
            `;
        }
        
         actionsHtml += `
            <button class="btn-cancelar" data-id="${order.id}" data-status="2">Cancelar</button>
        `;
        
        card.innerHTML = `
            <h3>Pedido #${order.id} <small>(Cliente ${order.usuario_id})</small></h3>
            <p>Horário: ${new Date(order.created_at).toLocaleTimeString()}</p>
            <ul>${itemsHtml}</ul>
            <div class="card-actions">
                ${actionsHtml}
            </div>
        `;
        
        container.appendChild(card);
    }
    
    function handleStatusUpdate(order) {
        const card = document.getElementById(`order-card-${order.id}`);
        
        if (order.status === 2 || order.status === 3) {
            // Pedido Cancelado ou Pronto: remove do painel
            if (card) {
                card.style.opacity = '0';
                setTimeout(() => {
                    card.remove();
                    updateCounters();
                }, 500);
            }
        } else {
            // move o card para a coluna correta (ex: de 0 para 1)
            if (card) card.remove();
            renderOrderCard(order);
        }
    }
    
    function updateCounters() {
        for (const status in containers) {
            const count = containers[status].children.length;
            counters[status].textContent = `${baseCounterText[status]} (${count})`;
        }
    }
    
    // --- 4. AÇÕES (MUDAR STATUS) ---
    
    // Delegação de eventos no painel principal
    mainView.addEventListener("click", (e) => {
        if (e.target.tagName !== "BUTTON") return;
        
        const orderId = e.target.dataset.id;
        const newStatus = e.target.dataset.status;
        
        if (orderId && newStatus) {
            updateOrderStatus(orderId, newStatus);
        }
    });
    
    async function updateOrderStatus(orderId, status) {
        try {
            const response = await fetch(`${API_URL}/orders/${orderId}/status`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ status: parseInt(status) })
            });
            
            if (!response.ok) {
                throw new Error("Falha ao atualizar status.");
            }
            
            // NÃO fazemos nada na UI aqui.
            // O backend vai enviar a atualização via WebSocket
            // e o `ws.onmessage` vai cuidar de mover o card.
            // Isso garante que todas as cozinhas fiquem sincronizadas.
            console.log(`Atualização de status enviada para pedido ${orderId}`);
            
        } catch (err) {
            console.error(err.message);
        }
    }


    btnGotoProducts.addEventListener("click", () => {
        mainView.classList.remove("active");
        productView.classList.add("active");
        productForm.classList.add("hidden");
        promotionModal.classList.add("hidden");
        loadProducts(); 
    });

    btnBackToKanban.addEventListener("click", () => {
        productView.classList.remove("active");
        mainView.classList.add("active");
    });

    async function loadProducts() {
        try {
            const response = await fetch(`${API_URL}/products/`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!response.ok) throw new Error("Falha ao carregar produtos.");

            currentProducts = await response.json();
            renderProductList(currentProducts);
        } catch (err) {
            console.error(err.message);
            alert(`Erro: ${err.message}`); // Feedback para o usuário
        }
    }

    function renderProductList(products) {
        productListBody.innerHTML = ""; // Limpa a tabela
        products.forEach(product => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${product.nome}</td>
                <td>R$ ${product.preco.toFixed(2)}</td>
                <td>${product.quantidade_estoque}</td>
                <td class="promo-status ${product.em_promocao ? 'active' : 'inactive'}">
                    ${product.em_promocao ? `Sim (R$ ${product.preco_promocional.toFixed(2)})` : 'Não'}
                </td>
                <td>
                    <button class="btn-edit" data-id="${product.id}">✏️ Editar</button>
                    <button class="btn-delete" data-id="${product.id}">🗑️ Excluir</button>
                    ${product.em_promocao
                        ? `<button class="btn-unpromote" data-id="${product.id}">❌ Despromover</button>`
                        : `<button class="btn-promote" data-id="${product.id}">⭐ Promover</button>`
                    }
                </td>
            `;
            productListBody.appendChild(tr);
        });
    }

    btnAddNewProduct.addEventListener("click", () => {
        productFormTitle.textContent = "Adicionar Novo Produto";
        productIdInput.value = ""; // Limpa ID (indica criação)
        productForm.reset(); // Limpa campos do formulário
        productForm.classList.remove("hidden"); // Mostra o formulário
    });

    btnCancelEdit.addEventListener("click", () => {
        productForm.classList.add("hidden"); // Esconde o formulário
    });

    productForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const productId = productIdInput.value;
        const isEditing = !!productId; // Se tem ID, está editando

        const productData = {
            nome: productNameInput.value,
            preco: parseFloat(productPriceInput.value),
            categoria: productCategoryInput.value || null, // Envia null se vazio
            keywords: productKeywordsInput.value,
            quantidade_estoque: parseInt(productStockInput.value)
        };

        const url = isEditing ? `${API_URL}/products/${productId}` : `${API_URL}/products/`;
        const method = isEditing ? "PUT" : "POST";

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(productData)
            });

             if (!response.ok) {
                 let errorMsg = `Falha ao ${isEditing ? 'atualizar' : 'criar'} produto.`;
                 try {
                     const errData = await response.json();
                     errorMsg = errData.detail || errorMsg;
                 } catch (e) {}
                 throw new Error(errorMsg);
             }

            productForm.classList.add("hidden"); // Esconde form
            loadProducts(); // Recarrega a lista

        } catch (err) {
             console.error(err.message);
             alert(`Erro: ${err.message}`);
        }
    });

    productListBody.addEventListener("click", async (e) => {
        const target = e.target;
        const productId = target.dataset.id;

        if (!productId) return; // Não clicou num botão com data-id

        if (target.classList.contains("btn-edit")) {
            const product = currentProducts.find(p => p.id == productId);
            if (product) {
                productFormTitle.textContent = "Editar Produto";
                productIdInput.value = product.id;
                productNameInput.value = product.nome;
                productPriceInput.value = product.preco;
                productCategoryInput.value = product.categoria || "";
                productKeywordsInput.value = product.keywords || "";
                productStockInput.value = product.quantidade_estoque;
                productForm.classList.remove("hidden");
            }
        }
        else if (target.classList.contains("btn-delete")) {
            const product = currentProducts.find(p => p.id == productId);
            if (confirm(`Tem certeza que deseja excluir o produto "${product?.nome || productId}"?`)) {
                try {
                    const response = await fetch(`${API_URL}/products/${productId}`, {
                        method: "DELETE",
                        headers: { "Authorization": `Bearer ${token}` }
                    });
                    if (!response.ok) throw new Error("Falha ao excluir produto.");
                    loadProducts();
                } catch (err) {
                    console.error(err.message);
                    alert(`Erro: ${err.message}`);
                }
            }
        }
        else if (target.classList.contains("btn-promote")) {
             promoProductIdInput.value = productId;
             promoPriceInput.value = ""; // Limpa preço anterior
             promotionModal.classList.remove("hidden");
             promoPriceInput.focus();
        }
        else if (target.classList.contains("btn-unpromote")) {
            const product = currentProducts.find(p => p.id == productId);
             if (confirm(`Desativar promoção do produto "${product?.nome || productId}"?`)) {
                 togglePromotionAPI(productId, false, null);
             }
        }
    });

     btnCancelPromotion.addEventListener("click", () => {
         promotionModal.classList.add("hidden");
     });

     btnSavePromotion.addEventListener("click", () => {
         const productId = promoProductIdInput.value;
         const promoPrice = parseFloat(promoPriceInput.value);

         if (!productId || isNaN(promoPrice) || promoPrice <= 0) {
             alert("Por favor, insira um preço promocional válido.");
             return;
         }
         togglePromotionAPI(productId, true, promoPrice);
         promotionModal.classList.add("hidden");
     });

    async function togglePromotionAPI(productId, activate, promoPrice) {
         const payload = {
             em_promocao: activate,
             preco_promocional: activate ? promoPrice : null
         };
         try {
             const response = await fetch(`${API_URL}/products/${productId}/promotion`, {
                 method: "PUT",
                 headers: {
                     "Content-Type": "application/json",
                     "Authorization": `Bearer ${token}`
                 },
                 body: JSON.stringify(payload)
             });
              if (!response.ok) {
                 let errorMsg = `Falha ao ${activate ? 'ativar' : 'desativar'} promoção.`;
                 try {
                     const errData = await response.json();
                     // Captura erro de validação do Pydantic (ex: preço faltando)
                     if (errData.detail && Array.isArray(errData.detail)) {
                         errorMsg = errData.detail[0].msg || errorMsg;
                     } else {
                          errorMsg = errData.detail || errorMsg;
                     }
                 } catch (e) {}
                 throw new Error(errorMsg);
             }
             loadProducts(); // Recarrega a lista para mostrar o novo status
         } catch (err) {
             console.error(err.message);
             alert(`Erro: ${err.message}`);
         }
    }

    
});