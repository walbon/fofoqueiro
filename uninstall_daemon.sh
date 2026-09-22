#!/usr/bin/env bash
# Fofoqueiro - Desinstalador do Daemon (systemd e tmux)
# Remove o service systemd, para a sessão tmux e limpa configurações opcionais.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="fofoqueiro-worker"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SESSION_NAME="fofoqueiro"

echo "🗑️  Desinstalando daemon do Fofoqueiro..."
echo "📁 Pasta do projeto: $PROJECT_DIR"

# 1. Parar e desabilitar service systemd (se existir)
if command -v systemctl >/dev/null 2>&1 && [ -f "$SERVICE_FILE" ]; then
    echo "🛑 Parando service systemd: $SERVICE_NAME"
    sudo systemctl stop "$SERVICE_NAME" || true
    echo "🚫 Desabilitando inicialização automática"
    sudo systemctl disable "$SERVICE_NAME" || true
    echo "🗑️  Removendo arquivo de serviço: $SERVICE_FILE"
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "✅ Service systemd removido."
else
    echo "ℹ️  Nenhum service systemd encontrado em $SERVICE_FILE"
fi

# 2. Parar sessão tmux (se existir)
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🛑 Parando sessão tmux: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Sessão tmux encerrada."
else
    echo "ℹ️  Nenhuma sessão tmux ativa com nome '$SESSION_NAME'."
fi

# 3. (Opcional) Reverter alterações no firewall ufw feitas pelo install_daemon.sh
if command -v ufw >/dev/null 2>&1; then
    echo "🔒 Verificando regras de ufw relacionadas ao Fofoqueiro..."
    # Remove a regra que permite localhost:8501 (comentada com "Fofoqueiro Streamlit")
    sudo ufw delete allow from 127.0.0.1 to any port 8501 comment "Fofoqueiro Streamlit" 2>/dev/null || true
    echo "✅ Regras ufw do Fofoqueiro removidas (se existiam)."
    # Não revertemos as políticas padrão (default deny incoming, allow outgoing) para não quebrar outras configurações.
else
    echo "ℹ️  ufw não encontrado; pulando reversão de firewall."
fi

# 4. Remover logs antigos? (opcional, deixar decision ao usuário)
echo ""
echo "⚠️  Os arquivos de log (fofoqueiro.log, worker.log) e o diretório .venv foram mantidos."
echo "    Se quiser removê-los também, execute manualmente:"
echo "      rm -f fofoqueiro.log worker.log"
echo "      rm -rf .venv"
echo ""

echo "========================================="
echo "   ✅ Desinstalação do daemon concluída!"
echo "========================================="
echo ""
echo "O projeto Fofoqueiro permanece intacto em $PROJECT_DIR."
echo "Para usar novamente, execute:"
echo "  ./start.sh   # inicia worker + web via tmux"
echo "  ./stop.sh    # para a sessão tmux"
echo ""
echo "Logs podem ser consultados com:"
echo "  tail -f fofoqueiro.log"
echo "========================================="