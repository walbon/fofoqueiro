#!/usr/bin/env bash
# Fofoqueiro - Iniciar Daemon via tmux (caminho detectado automaticamente)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
STREAMLIT_BIN="$PROJECT_DIR/.venv/bin/streamlit"
SESSION_NAME="fofoqueiro"

cd "$PROJECT_DIR" || exit 1

# Verifica se a sessão já existe
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️ A sessão tmux '$SESSION_NAME' já está em execução."
    echo "Acompanhe: tmux attach -t $SESSION_NAME"
    echo "Ou logs: tail -f $PROJECT_DIR/fofoqueiro.log"
    exit 0
fi

echo "🚀 Iniciando Fofoqueiro (Worker + Web) no tmux..."

# 1. Worker em background
tmux new-session -d -s "$SESSION_NAME" -n "worker" "cd '$PROJECT_DIR' && '$VENV_PYTHON' worker.py"

# 2. Interface Web Streamlit (só localhost)
tmux new-window -t "$SESSION_NAME" -n "web" "cd '$PROJECT_DIR' && '$STREAMLIT_BIN' run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true"

echo "✅ Fofoqueiro rodando em segundo plano no tmux (sessão '$SESSION_NAME')!"
echo "📱 Acesse a interface Web: http://localhost:8501"
echo "📜 Logs em tempo real: tail -f $PROJECT_DIR/fofoqueiro.log"
echo "🖥️  Conecte ao terminal tmux: tmux attach -t $SESSION_NAME"
