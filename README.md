# ☕ CoffeeNet - Atendimento Inteligente para Cafeterias

Bem-vindo ao **CoffeeNet!** Um sistema distribuído que usa Inteligência Artificial para melhorar o atendimento, aumentar as vendas e deixar os clientes mais satisfeitos no contexto de Cafeicultura.

---

## 😥 A "Dor" — Problemas que acontecem em cafeterias

Identificamos três gargalos principais no atendimento:

* 💸 **Vendas Perdidas:** O barista, na correria, esquece de oferecer promoções ou produtos complementares (upsell), diminuindo o ticket médio.
* 😟 **Cliente Ansioso:** O cliente (especialmente em pedidos online) não sabe o status do seu pedido ("Na fila?", "Preparando?"), gerando uma experiência ruim.
* 🤯 **Cozinha Confusa:** Comandas de papel e comunicação verbal causam erros, atrasos na produção e dificultam a gestão.

## ✨ A Solução — O que o CoffeeNet resolve

* **Chatbot Inteligente:** Anota pedidos usando IA (spaCy) e sugere itens baseado no histórico do cliente e promoções (Gemini).
* **Status em Tempo Real:** O cliente vê o status ("Recebido", "Em Produção", "Pronto") mudar automaticamente na tela.
* **Cozinha Organizada:** O pedido é enviado instantaneamente para um painel digital (Kanban), eliminando erros de comunicação.

---

## 🤓 Como Funciona? (A Mágica por Trás dos Panos)

Explicando como as peças se encaixam, focando nos conceitos da disciplina:

### Por que isso é um Sistema Distribuído?

Nosso sistema não é um programa único. Ele é um **conjunto de peças independentes** (programas menores) que precisam conversar pela rede para funcionar. Pense numa banda:

* O **Backend Principal (FastAPI)** é o vocalista: ele comanda o show, fala com o público (Frontends) e diz o que os outros músicos devem fazer.
* O **Banco de Dados (PostgreSQL)** é o baterista: ele guarda o ritmo e a memória de tudo.
* A **IA (spaCy)** é o guitarrista especialista: ele só faz uma coisa (entender texto), mas faz muito bem.

Eles são programas separados, rodando em "caixas" (contêineres Docker) diferentes, e se comunicam por chamadas de rede (HTTP, SQL). Isso *é* um sistema distribuído.

### As Nossas Duas IAs (Os "Cérebros"):

A gente usa duas IAs diferentes, como o professor pediu:

1. **IA 1: O "Tradutor" (spaCy / NLU)**

   * **O que é?** É a nossa **IA local, que roda dentro do Docker**. Usamos a biblioteca **spaCy**, que é uma ferramenta padrão de mercado para Processamento de Linguagem Natural (NLU).
   * **Como funciona?** Ela não é só um `if/else`. Ela carrega um **modelo de machine learning** (`pt_core_news_sm`) treinado para entender a estrutura do português. Quando o usuário digita "dois cafés e um pão de queijo", a função dela é "traduzir" essa bagunça humana para dados que o computador entende, algo como: `[{produto_id: 1, qtd: 2}, {produto_id: 3, qtd: 1}]`.
   * **Por que as `Keywords` são importantes?** As `keywords` (que a gente cadastra no painel da cozinha, tipo "pão de queijo, paozinho") são a *ponte*. Elas dizem ao spaCy quais palavras no texto do cliente devem ser mapeadas para um produto real no nosso banco de dados.

2. **IA 2: O "Vendedor Inteligente" (Gemini)**

   * **O que é?** É a IA "criativa" e externa (do Google, roda na nuvem).
   * **Como funciona?** O nosso Backend Principal pega o pedido "traduzido" pela IA 1 (ex: `[{cafe, 2}]`), busca seu histórico no banco (ex: "cliente sempre pede pão de queijo") e as promoções ativas. Aí, ele monta um **prompt gigante** (uma ordem) para o Gemini, mais ou menos assim: "MISSÃO: O cliente pediu 2 cafés, mas esqueceu o pão de queijo (que é favorito dele). Confirme o café e sugira o pão de queijo. Responda APENAS como um barista."
   * O Gemini, então, *gera* o texto da resposta que você vê no chat (ex: "Beleza! 2 cafés anotados. Notei que você esqueceu seu pão de queijo hoje... quer adicionar?"). Ele não sabe o que é um produto ou preço, ele só segue a missão que nosso backend deu.

### A Mágica do Tempo Real (WebSockets)

* **Qual o problema?** Em uma API normal (HTTP), o seu navegador (cliente) tem que *perguntar* pro servidor se algo mudou. (Ex: "Meu pedido tá pronto?", "Não." ... "E agora?", "Não."). Isso é lento e gasta recursos.
* **A Solução (WebSocket):** Pense no WebSocket como um **walkie-talkie** ou uma ligação de telefone. O cliente e o servidor abrem um "túnel" de comunicação e deixam ele aberto.
* **Como usamos:** Quando a Cozinha aperta o botão "Pronto", o Backend Principal usa esse "túnel" para *avisar* (empurrar a informação) na mesma hora pro navegador do Cliente: "EI, SEU PEDIDO #5 FICOU PRONTO!". É por isso que o status muda na tela do cliente sem ele precisar dar F5. O mesmo vale para o pedido novo que aparece na tela da Cozinha.

---

## 🚀 Como Rodar o Projeto (Guia para o Time de Front-end)

O backend (API, DB, IA 1) tá todo "encaixotado" no Docker. O frontend (HTML/JS/CSS) roda localmente na sua máquina.

### Pré-requisitos

* Git
* Docker e Docker Compose (instalados e rodando)

### 1. Clonar o Repositório

```bash
git clone [URL_DO_NOSSO_REPOSITORIO_GIT]
cd coffeenet
```

### 2. Configurar Variáveis de Ambiente (Obrigatório)

Isso é crucial, senão a IA 2 (Gemini) não funciona.

Vá para a pasta backend/.

Crie um arquivo chamado `.env` (copiando do `env.example` se tiver um, ou criando do zero).

Cole o conteúdo abaixo nele, substituindo `SUA_CHAVE_API_VEM_AQUI` pela sua chave do Gemini:

```ini
# /coffeenet/backend/.env

# --- Chave da IA (OBRIGATÓRIO) ---
GEMINI_API_KEY=SUA_CHAVE_API_VEM_AQUI

# --- Configuração da Aplicação ---
IA_1_NLU_URL=http://ia_1_nlu:8001
SECRET_KEY=uma_chave_secreta_muito_forte_e_dificil_de_adivinhar_0123456789
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# --- Configuração Centralizada do Banco de Dados ---
POSTGRES_USER=coffeenet
POSTGRES_PASSWORD=supersecret
POSTGRES_DB=coffeenet_db
DB_HOST=db
DB_PORT=5432 # Porta INTERNA do Docker

# --- URL do Banco (Gerada automaticamente) ---
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:${DB_PORT}/${POSTGRES_DB}
```

### 3. Subir o Backend (Docker)

Volte para a pasta raiz do projeto (/coffeenet).

Limpe instalações antigas (se houver):

```bash
sudo docker compose down -v
```

Construa as imagens e suba os serviços (isso pode demorar um pouco na primeira vez):

```bash
sudo docker compose up --build
```

Aguarde até os logs se estabilizarem. Você verá o `seed.py` rodar (criando usuários/produtos) e as mensagens de "Uvicorn running" e "Cliente Gemini inicializado". O backend está no ar.

### 4. Rodar o Frontend (Servidor Local)

Você não pode simplesmente abrir o `index.html` (o navegador vai bloquear). Você precisa de um servidor local.

**Opção A: VS Code (Recomendado)**

* Instale a extensão "Live Server".
* Abra a pasta `frontend_client/`, clique com o botão direito no `index.html` e "Open with Live Server".
* Abra a pasta `frontend_kitchen/` (em outra janela), clique com o botão direito no `index.html` e "Open with Live Server".

**Opção B: Terminal Python**

Terminal 1 (Cliente):

```bash
cd frontend_client/
python -m http.server 8080
# Acesse http://localhost:8080
```

Terminal 2 (Cozinha):

```bash
cd frontend_kitchen/
python -m http.server 8081
# Acesse http://localhost:8081
```


### 🔑 Acesso e Testes

* Cliente: [cliente@teste.com](mailto:cliente@teste.com) | Senha: 123
* Cozinha: [cozinha@teste.com](mailto:cozinha@teste.com) | Senha: 123

### 🛠️ Próximos Passos

* **Frontend:** Evoluir a interface (design, usabilidade, componentes).
* **Documentação:** Finalizar a Modelagem de Ameaças e a Visão Final Pós-Mitigação para o professor.
