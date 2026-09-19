#!/usr/bin/env bash
# Fofoqueiro - Iniciar Daemon via tmux

PROJECT_DIR="/srv/user/AI/projetos/Fofoqueira"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
STREAMLIT_BIN="$PROJECT_DIR/.venv/bin/streamlit"
SESSION_NAME="fofoqueiro"

cd "$PROJECT_DIR" || exit 1

# Verifica se a sessão já existe
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "⚠️ A sessão tmux '$SESSION_NAME' já está em execução."
    echo "Para acompanhar, use: tmux attach -t $SESSION_NAME"
    echo "Ou veja o log: tail -f $PROJECT_DIR/fofoqueiro.log"
    exit 0
fi

echo "🚀 Iniciando Fofoqueiro (Worker + Web) no tmux..."

# 1. Cria a sessão com a janela do Worker
tmux new-session -d -s "$SESSION_NAME" -n "worker" "cd '$PROJECT_DIR' && '$VENV_PYTHON' worker.py"

# 2. Cria a segunda janela com a interface Streamlit
tmux new-window -t "$SESSION_NAME" -n "web" "cd '$PROJECT_DIR' && '$STREAMLIT_BIN' run app.py --server.port 8501 --server.headless true"

echo "✅ Fofoqueiro rodando em segundo plano no tmux (sessão '$SESSION_NAME')!"
echo ""
echo "📱 Acesse a interface Web: http://localhost:8501"
echo "📜 Acompanhe os logs em tempo real: tail -f $PROJECT_DIR/fofoqueiro.log"
echo "🖥️  Conecte ao terminal tmux: tmux attach -t $SESSION_NAME"
