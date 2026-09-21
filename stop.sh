#!/usr/bin/env bash
# Fofoqueiro - Parar Daemon (tmux + systemd)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_NAME="fofoqueiro"
SERVICE_NAME="fofoqueiro-worker"

echo "🛑 Parando Fofoqueiro..."

# 1. Para sessão tmux, se existir
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Sessão tmux '$SESSION_NAME' encerrada."
else
    echo "ℹ️  Sessão tmux '$SESSION_NAME' não estava ativa."
fi

# 2. Para service systemd, se existir
if command -v systemctl >/dev/null 2>&1 && systemctl list-units --all 2>/dev/null | grep -q "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
    echo "✅ Service systemd '$SERVICE_NAME' parado."
fi

# 3. Mata processos worker/streamlit órfãos do projeto
pkill -f "$PROJECT_DIR/worker.py" 2>/dev/null && echo "✅ worker.py finalizado." || true
pkill -f "streamlit.*$PROJECT_DIR/app.py" 2>/dev/null && echo "✅ Streamlit finalizado." || true

# 4. Remove lock (se sobrou)
if [ -f "$PROJECT_DIR/worker.lock" ]; then
    rm -f "$PROJECT_DIR/worker.lock"
    echo "✅ worker.lock removido."
fi

echo "🎉 Fofoqueiro parado. Nada rodando."