# Fofoqueiro – Agregador de Inteligência & Notícias

Um agregador de inteligência focado em tecnologia e segurança que extrai e sintetiza conteúdos mantendo o idioma original (sem tradução), das seguintes fontes:

- 🧡 **Hacker News** — Top stories resumidas objetivamente
- 🛡️ **Linux CVEs** — Boletins oficiais de segurança (Canonical USN, Red Hat RHSA, Amazon Linux ALAS, Kernel Releases, CISA Advisories)
- 📖 **LWN.net** — Artigos do Linux Weekly News via RSS
- 🔒 **linux-cve-announce** — CVEs do kernel Linux extraídas do mailing list (Openwall/MARC), com **filtro por temas** relevantes (drm, gpu, usb, sched, networking, pci, etc.)

Toda a sumarização é feita via **9router** com prompts neutros e objetivos.

---

## 🛠️ Arquitetura

O projeto é dividido em **três componentes** utilizando **SQLite** (modo WAL) como banco unificado:

| Componente | Descrição |
|---|---|
| `worker.py` | Daemon que coleta notícias de todas as fontes em paralelo via `ThreadPoolExecutor`, deduplica e envia para o **9router** gerar resumos. Execução atômica via `fcntl.flock`. |
| `app.py` | Interface Streamlit com grid de cards, filtros por fonte/busca/favoritos, e botões de ação (⭐ favoritar, 📦 arquivar, ❌ ignorar). |
| `config.py` | Configurações centralizadas: URLs, subreddits, temas de filtro, intervalo do worker. |

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
│   ├── CVEFetcher         # RSS feeds de segurança
│   ├── LWNFetcher         # LWN.net RSS
│   └── LinuxCVEAnnounceFetcher  # Mailing list linux-cve-announce
├── fofoqueiro.db          # Banco SQLite (WAL mode)
├── .env                   # Credenciais (NINEROUTER_API_KEY)
├── install_daemon.sh      # Instalador completo (venv, service, firewall)
├── start.sh               # Iniciar worker + web via tmux
├── stop.sh                # Parar tudo (tmux, systemd, processos)
├── requirements.txt       # Dependências Python
└── user_feeds.json        # Subreddits extras do usuário
```

---

## 🚀 Como Usar

### Instalação Automática (recomendado)
```bash
cd /srv/user/AI/projetos/Fofoqueira
./install_daemon.sh
# Seguir instruções: configura venv, dependências, systemd, firewall
```

### Iniciar / Parar via Tmux
```bash
./start.sh      # Worker + Streamlit em background
./stop.sh       # Encerra tudo (tmux, systemd, processos órfãos)
```

### Manualmente
```bash
# Worker (background)
python3 worker.py

# Interface Web
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

### Logs
```bash
tail -f fofoqueiro.log      # Logs do worker
```

---

## ⚙️ Configuração

As configurações estão em `config.py` e `.env`:

| Variável | Descrição | Default |
|---|---|---|
| `NINEROUTER_BASE_URL` | Endpoint da API de sumarização | `http://127.0.0.1:20128/v1` |
| `NINEROUTER_API_KEY` | Chave de autenticação 9router | — |
| `NINEROUTER_MODEL` | Modelo LLM utilizado | `free` |
| `WORKER_INTERVAL_MINUTES` | Intervalo entre coletas | `60` |
| `DEFAULT_SUBREDDITS` | Subreddits monitorados | `linux, netsec, programming, technology` |
| `THEME_KEYWORDS` | Palavras-chave para filtrar CVEs relevantes | `drm, gpu, usb, sched, networking...` |

---

## 🔒 Segurança

- **Bind local**: Streamlit escuta apenas em `127.0.0.1:8501`
- **Firewall (ufw)**: `install_daemon.sh` configura regra para porta 8501
- **Favoritos**: Funcionalidade de estrela (⭐) para marcar notícias relevantes
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