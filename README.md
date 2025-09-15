# 🤖 ChatBot de Riscos de Segurança – Segunda Linha de Defesa

Este projeto implementa um **ChatBot em linguagem natural** para apoiar a **segunda linha de defesa** em segurança cibernética.  
Ele utiliza **RAG (Retrieval-Augmented Generation)** e o modelo **Mistral** rodando via **Ollama + Docker** para consultar e responder perguntas sobre riscos armazenados em um **JSON estruturado**.

---

## 🚀 Arquitetura

- **Ollama + Mistral** → modelo de linguagem rodando localmente em Docker.  
- **Flask** → servidor web que expõe o frontend e recebe as perguntas.  
- **RAG (rag_utils.py)** → conecta a pergunta do usuário à base `dados.json`.  
- **Frontend (templates + static)** → interface simples em HTML/CSS/JS.  

Fluxo:
```
Usuário → Frontend → Flask (app.py) → RAG (rag_utils.py) → Ollama/Mistral → Resposta
```

---

## 📂 Estrutura do Projeto

```
├── app.py               # Servidor Flask
├── rag_utils.py         # Funções de RAG e integração Mistral
├── dados.json           # Base de riscos
├── templates/           # HTML do frontend
├── static/              # CSS e JS
├── requirements.txt     # Dependências Python
└── README.md            # Documentação
```

---

## ⚙️ Instalação e Uso

### 1. Subir o modelo no Docker
Certifique-se que o Ollama está rodando. Para iniciar o **Mistral**:

```bash
docker exec -it ollama ollama run mistral
```

O Ollama ficará disponível em `http://localhost:11434`.

---

### 2. Clonar o projeto
```bash
git clone https://github.com/SEU-USUARIO/chatbot-riscos-seguranca.git
cd chatbot-riscos-seguranca
```

---

### 3. Criar ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

---

### 4. Instalar dependências
```bash
pip install -r requirements.txt
```

---

### 5. Executar o servidor Flask
```bash
python app.py
```

O sistema ficará disponível em:  
👉 http://localhost:8082

---

## 💡 Exemplos de Perguntas

- **Contagem por ano**  
  > "Quantos pontos foram encerrados em 2025?"

- **Filtro por responsável**  
  > "Quais riscos abertos estão sob responsabilidade do Diretor Joaozinho Santos?"

- **Busca por ID**  
  > "Mostre detalhes do risco ID 1005."

---

## 🔧 Customização

- **Base de dados** → edite `dados.json` com os riscos da sua organização.  
- **Configuração do RAG** → `rag_utils.py` contém:
  - Normalização de termos (ex.: `encerrado` ↔ `fechado`)  
  - Filtros estruturados (ano, área, responsável)  
  - Integração com embeddings (`sentence-transformers/all-MiniLM-L6-v2` + `faiss`)  

---

## 📜 Licença
Este projeto está sob a licença **MIT**.
