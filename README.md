# Fofoqueiro – Agregador de Inteligência & Notícias

Um agregador de inteligência focado em tecnologia e segurança que extrai, sintetiza e traduz conteúdos das seguintes fontes:
- 🇧🇷 **TabNews** (Notícias e discussões relevantes da comunidade tech BR)
- 🧡 **Hacker News** (Top stories traduzidas e resumidas)
- 🤖 **Reddit** (Posts dos subreddits `r/linux`, `r/netsec`, `r/programming`, `r/technology` e novos subreddits adicionáveis)
- 🛡️ **Linux Kernel CVEs** (Vulnerabilidades e boletins de segurança do Kernel Linux)

Toda a sumarização e tradução é feita via **9router** com prompts neutros e objetivos.

---

## 🛠️ Arquitetura do Sistema

O projeto é dividido em **dois processos independentes** utilizando **SQLite** como banco relacional unificado:

1. **`worker.py`** *(Background Process)*:
   - Executa periodicamente a coleta de dados de todas as fontes.
   - Dedupica registros no SQLite.
   - Envia itens pendentes para o **9router** gerar títulos traduzidos e resumos objetivos.
   
2. **`app.py`** *(Streamlit Interface)*:
   - Interface web visual para navegação.
   - Filtros por fonte, busca por palavras-chave e adição dinâmica de subreddits.
   - Monitoramento das execuções do worker.

---

## 🚀 Como Executar

### 1. Instalar as Dependências
```bash
cd /srv/user/AI/projetos/Fofoqueira
pip install -r requirements.txt
```

### 2. Iniciar o Background Worker (Agendamento & IA)
Em um terminal separado:
```bash
python3 worker.py
```

### 3. Iniciar a Interface Streamlit
Em outro terminal:
```bash
streamlit run app.py
```

---

## ⚙️ Configurações
As credenciais e rotas do 9router estão configuradas em `config.py`:
- **Endpoint 9router**: `http://127.0.0.1:20128/v1`
- **Modelo LLM**: `free`
