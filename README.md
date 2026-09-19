# Fofoqueiro – Agregador de Inteligência & Notícias

Um agregador de inteligência focado em tecnologia e segurança que extrai e sintetiza conteúdos mantendo o idioma original (sem tradução), das seguintes fontes:
- 🧡 **Hacker News** (Top stories resumidas objetivamente)
- 🤖 **Reddit / Comunidade Tech** (Posts de subreddits configuráveis como `r/linux`, `r/netsec`, `r/programming`, `r/technology`)
- 🛡️ **Linux Security & CVEs** (Boletins oficiais de segurança e vulnerabilidades de distribuidores e kernel: Canonical USN, Red Hat RHSA, Amazon Linux ALAS, Linux Kernel Releases e CISA Advisories)

Toda a sumarização é feita via **9router** com prompts neutros e objetivos.

---

## 🛠️ Arquitetura do Sistema

O projeto é dividido em **dois processos independentes** utilizando **SQLite** (com modo WAL ativado) como banco de dados unificado:

1. **`worker.py`** *(Background Process)*:
   - Executa periodicamente a coleta de dados de todas as fontes paralelamente via `ThreadPoolExecutor`.
   - Garante execução atômica via `fcntl.flock` (evita concorrência).
   - Dedupica registros no SQLite.
   - Envia itens pendentes para o **9router** gerar resumos objetivos no idioma original.
   
2. **`app.py`** *(Streamlit Interface)*:
   - Interface web visual responsiva com layout ultracompacto em grade (2 colunas) e preview direto de resumos.
   - Filtros por fonte, busca por palavras-chave e adição dinâmica de subreddits.
   - Monitoramento lateral do histórico de execuções do worker.

---

## 🚀 Como Executar

### 1. Instalar as Dependências
```bash
cd /srv/user/AI/projetos/Fofoqueira
pip install -r requirements.txt
```

### 2. Iniciar via Script Automatizado (Tmux)
```bash
./start.sh
```

Ou manualmente em terminais separados:
- **Worker (Daemon Background)**: `python3 worker.py`
- **Interface Web (Streamlit)**: `streamlit run app.py`

---

## ⚙️ Configurações
As credenciais e rotas do 9router estão configuradas em `config.py`:
- **Endpoint 9router**: `http://127.0.0.1:20128/v1`
- **Modelo LLM**: `free`
