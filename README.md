# Fofoqueiro – Agregador de Inteligência & Notícias

Um agregador de inteligência focado em tecnologia e segurança que extrai e sintetiza conteúdos mantendo o idioma original (sem tradução), das seguintes fontes:

- 🧡 **Hacker News** — Top stories resumidas objetivamente via API Firebase
- 🛡️ **Linux CVEs** — Boletins oficiais de segurança (RSS: Ubuntu USN, Red Hat RHSA, Amazon Linux ALAS, Kernel Releases, CISA Advisories) com **filtro por temas** (gpu, kvm, nvme, etc.)
- 📖 **LWN.net** — Artigos do Linux Weekly News via RSS
- 🔒 **linux-cve-announce** — CVEs do kernel Linux extraídas do mailing list (Openwall/MARC), com **filtro por temas** extraídos do título (ex: KVM, arm64, nv)

Toda a sumarização é feita via **IA** usando padrão **OpenAI-compatible** (`/chat/completions`) com prompts neutros e objetivos. Sem chave (`IA_API_KEY` vazio), o worker coleta normalmente em **modo offline** e marca resumos como indisponíveis.

---

## 🛠️ Arquitetura

O projeto é dividido em **dois processos** utilizando **SQLite** (modo WAL) como banco de dados unificado:

| Componente | Descrição |
|---|---|
| `worker.py` *(Background Process)* | Executa periodicamente a coleta de dados de todas as fontes paralelamente via `ThreadPoolExecutor`. Garante execução atômica via `fcntl.flock` (evita concorrência). Dedupica registros no SQLite. Envia itens pendentes para o **9router** gerar resumos objetivos no idioma original. |
| `app.py` *(Streamlit Interface)* | Interface web visual responsiva com layout ultracompacto em grade (2 colunas) e preview direto de resumos. Filtros por fonte, busca por palavras-chave e adição dinâmica de subreddits. Monitoramento lateral do histórico de execuções do worker. |

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
Cria sessão `fofoqueiro` com 2 janelas:
- `worker` → roda `python3 worker.py` em background
- `web` → roda `streamlit run app.py --server.port 8501 --server.headless true`

Ou manualmente em terminais separados:
- **Worker (Daemon Background)**: `python3 worker.py`
- **Interface Web (Streamlit)**: `streamlit run app.py`

### 3. Parar
```bash
./stop.sh
```

### Acessar
```bash
http://localhost:8501
```

### Logs em tempo real
```bash
tail -f fofoqueiro.log
```

---

## ⚙️ Configuração

As configurações estão em `config.py` e `.env`:

| Variável | Descrição | Default |
|---|---|---|
| `IA_BASE_URL` | Endpoint da API de sumarização (OpenAI-compatible: 9router, Ollama, LM Studio, vLLM) | `http://127.0.0.1:20128/v1` |
| `IA_API_KEY` | Chave de autenticação (deixar vazio = modo offline, armazena sem resumo IA) | — |
| `IA_MODEL` | Modelo LLM utilizado | `free` |
| `THEME_KEYWORDS` | Palavras-chave para filtrar CVEs relevantes (ambas fontes: linux-cve-announce e feeds CVE) | `["gpu","kvm","nvme"]` |
| `WORKER_INTERVAL_MINUTES` | Intervalo entre coletas (em minutos) | `60` |
| `DEFAULT_SUBREDDITS` | Subreddits monitorados (agora sem Reddit ativo) | `linux, netsec, programming, technology` |
| `LWN_RSS_URL` | URL do RSS do LWN.net | `https://lwn.net/headlines/rss` |

**Como ajustar o filtro de temas:**
Edite `THEME_KEYWORDS` em `config.py`. Exemplo:
```python
THEME_KEYWORDS = ["gpu", "kvm", "nvme", "arm", "drm", "usb"]
```
- O filtro atua no **CVEFetcher** (busca título + resumo)
- E no **LinuxCVEAnnounceFetcher** (extrai tags do título antes de `Fix`/`Add` etc.)
- Palavras-chave em **maiúscula/minúscula** são ignoradas (comparação `.lower()`)

Para desabilitar o filtro (mostrar todos os CVEs):
```python
THEME_KEYWORDS = []
```

---

## 📁 Estrutura

```
Fofoqueira/
├── app.py                 # Interface Streamlit
├── worker.py              # Daemon de coleta (background)
├── config.py              # Configurações centrais
├── database.py            # SQLite: init, queries, toggle_starred
├── ai_service.py          # Sumarização via 9router
├── fetchers/
│   ├── HNFetcher          # Hacker News (API Firebase)
│   ├── CVEFetcher         # RSS feeds de segurança (com filtro de tema)
│   ├── LWNFetcher         # LWN.net RSS
│   └── LinuxCVEAnnounceFetcher  # Mailing list linux-cve-announce (com filtro de tema)
├── fofoqueiro.db          # Banco SQLite (WAL mode)
├── .env                   # Credenciais (IA_API_KEY)
├── install_daemon.sh      # Instalador completo (venv, service, firewall)
├── start.sh               # Iniciar worker + web via tmux
├── stop.sh                # Parar tudo (tmux, systemd, processos)
├── requirements.txt       # Dependências Python
└── user_feeds.json        # Subreddits extras do usuário (opcional)
```

---

## 🔒 Segurança

- **Bind local**: Streamlit escuta apenas em `127.0.0.1:8501`
- **Firewall (ufw)**: `install_daemon.sh` configura regra para porta 8501 somente localhost
- **Favoritos**: Botão de estrela (⭐/☆) para marcar/notas relevantes; filtro `is_starred` no banco
- **Sem autenticação de usuário** (exposto apenas na rede local)

---

## 📦 Dependências

```
streamlit>=1.30.0
feedparser>=6.0.10
httpx>=0.26.0
schedule>=1.2.1
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
```

---

## 🛠️ Histórico de Commits Recentes

| Hash | Assunto |
|---|---|
| `7d54082` | feat: add theme keyword filtering to CVEFetcher (title+summary) |
| `5a4e849` | feat: simplify tag extraction in linux-cve fetcher, remove rigid verb regex |
| `f6b6eb0` | docs: update README with LWN, linux-cve-announce, scripts, and architecture |
| `41464b0` | feat: remove Reddit source, add LWN and linux-cve-announce to sidebar sources |
| `f00920d` | feat: add LWN.net and linux-cve-announce fetchers with theme filtering |
| `08ed526` | feat: suporte a arquivamento, filtro 'nao interessa' e remocao de subreddits (v2) |
| `6617550` | feat: add daemon installer with path auto-detection, stop script, dynamic start.sh |
| `5cba9ef` | feat: implement favorite functionality (star button, is_starred column, toggle_starred function, config updates) |
| `08ed526` | ... |

---

