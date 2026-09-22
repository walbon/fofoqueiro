#!/usr/bin/env bash
# Fofoqueiro – Instalador Automático do Daemon
# Detecta a própria pasta como raiz do projeto e configura tudo com caminhos corretos.

set -euo pipefail

###############################################################################
# 1. Detecta a pasta do projeto (onde este script reside)
###############################################################################
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
SERVICE_NAME="fofoqueiro-worker"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SESSION_NAME="fofoqueiro"

echo "📁 Pasta do projeto detectada: $PROJECT_DIR"

# Confere se realmente é o Fofoqueiro
if [ ! -f "$PROJECT_DIR/worker.py" ] || [ ! -f "$PROJECT_DIR/app.py" ]; then
    echo "❌ worker.py/app.py não encontrados em $PROJECT_DIR"
    echo "   Rode este script de dentro da pasta do Fofoqueiro."
    exit 1
fi

###############################################################################
# 2. Cria venv + instala dependências
###############################################################################
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Criando ambiente virtual..."
    python3 -m venv "$VENV_DIR"
fi

echo "📦 Instalando dependências..."
"$VENV_PIP" install --upgrade pip
"$VENV_PIP" install -r "$PROJECT_DIR/requirements.txt"

###############################################################################
# 3. Garante .env
###############################################################################
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  .env não encontrado. Copiando .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  Edite $PROJECT_DIR/.env e preencha IA_API_KEY."
fi

###############################################################################
# 4. Instala service systemd (usa caminho detectado)
###############################################################################
if command -v systemctl >/dev/null 2>&1; then
    echo "🛠️  Instalando service systemd em $SERVICE_FILE..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Fofoqueiro Worker Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON $PROJECT_DIR/worker.py
Restart=always
RestartSec=10
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo "✅ Service systemd instalado: $SERVICE_NAME"
else
    echo "⚠️  systemctl não disponível. Usará tmux via start.sh."
fi

###############################################################################
# 5. Firewall (ufw) – porta 8000 só localhost
###############################################################################
if command -v ufw >/dev/null 2>&1; then
    echo "🔒 Configurando firewall ufw..."
    sudo ufw default deny incoming || true
    sudo ufw default allow outgoing || true
    sudo ufw allow from 0.0.0.0 to any port 8000 comment "Fofoqueiro Streamlit" || true
    sudo ufw --force enable || true
    echo "✅ Firewall: somente localhost acessa 8000."
else
    echo "⚠️  ufw não encontrado. Opcional: sudo apt install ufw"
fi

###############################################################################
# 6. Cria start.sh dinâmico (caminho detectado)
###############################################################################
cat > "$PROJECT_DIR/start.sh" <<EOF
#!/usr/bin/env bash
# Fofoqueiro - Iniciar Daemon via tmux (caminhos detectados automaticamente)
PROJECT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="\$PROJECT_DIR/.venv/bin/python"
STREAMLIT_BIN="\$PROJECT_DIR/.venv/bin/streamlit"
SESSION_NAME="$SESSION_NAME"

cd "\$PROJECT_DIR" || exit 1

# Verifica se a sessão já existe
if tmux has-session -t "\$SESSION_NAME" 2>/dev/null; then
    echo "⚠️ A sessão tmux '\$SESSION_NAME' já está em execução."
    echo "Acompanhe: tmux attach -t \$SESSION_NAME"
    echo "Ou logs: tail -f \$PROJECT_DIR/fofoqueiro.log"
    exit 0
fi

echo "🚀 Iniciando Fofoqueiro (Worker + Web) no tmux..."

# 1. Worker em background
tmux new-session -d -s "\$SESSION_NAME" -n "worker" "cd '\$PROJECT_DIR' && '\$VENV_PYTHON' worker.py"

# 2. Interface Web Streamlit (só localhost)
tmux new-window -t "\$SESSION_NAME" -n "web" "cd '\$PROJECT_DIR' && '\$STREAMLIT_BIN' run app.py --server.address 0.0.0.0 --server.port 8000 --server.headless true" # FIXED_BIND
# OLD: tmux new-window -t "\$SESSION_NAME" -n "web" "cd '\$PROJECT_DIR' && '\$STREAMLIT_BIN' run app.py --server.address 127.0.0.1 --server.port 8000 --server.headless true"

echo "✅ Fofoqueiro rodando em segundo plano no tmux (sessão '\$SESSION_NAME')!"
echo "📱 Acesse a interface Web: http://localhost:8000"
echo "📜 Logs em tempo real: tail -f \$PROJECT_DIR/fofoqueiro.log"
echo "🖥️  Conecte ao terminal tmux: tmux attach -t \$SESSION_NAME"
EOF
chmod +x "$PROJECT_DIR/start.sh"
echo "✅ start.sh regenerado com caminho dinâmico."

###############################################################################
# 7. Resumo final
###############################################################################
echo ""
echo "========================================="
echo "   ✅ Fofoqueiro instalado com sucesso!"
echo "========================================="
echo ""
echo "📂 Projeto: $PROJECT_DIR"
echo "🐍 Python:  $VENV_PYTHON"
echo "📡 Service: systemd → $SERVICE_NAME | tmux → $SESSION_NAME"
echo "🔒 Firewall: porta 8000 somente localhost"
echo ""
echo "▶️ Iniciar daemon (coleta em background):"
echo "   systemctl start $SERVICE_NAME    # se systemd"
echo "   # ou sem systemd:"
echo "   $VENV_PYTHON $PROJECT_DIR/worker.py"
echo ""
echo "🌐 Interface web:"
echo "   $PROJECT_DIR/start.sh            # worker + web via tmux"
echo "   http://localhost:8000"
echo ""
echo "📜 Logs: tail -f $PROJECT_DIR/fofoqueiro.log"
echo "========================================="
