#!/bin/bash

cd "$(dirname "$0")"
APP_DIR=$(pwd)

# Funciona em dois cenários:
# 1. Dev rodando da raiz do projeto após build local → dist/ServiceDeck/ServiceDeck
# 2. Usuário que baixou o release e extraiu → ServiceDeck (está na mesma pasta)
if [ -f "${APP_DIR}/ServiceDeck" ]; then
    EXEC_PATH="${APP_DIR}/ServiceDeck"
else
    EXEC_PATH="${APP_DIR}/dist/ServiceDeck/ServiceDeck"
fi

ICON_PATH="${APP_DIR}/app/assets/icon.png"

echo "Configurando o atalho para o executável em: ${EXEC_PATH}"
echo "Usando o ícone em: ${ICON_PATH}"

cat > ServiceDeck.desktop << EOL
[Desktop Entry]
Version=1.0
Name=ServiceDeck
Comment=Gerenciador de Microserviços
Type=Application
Terminal=false
Exec=${EXEC_PATH}
Icon=${ICON_PATH}
Categories=Development;Utility;
EOL

chmod +x ServiceDeck.desktop

echo ""
echo "Lançador 'ServiceDeck.desktop' criado com sucesso!"
echo "Você já pode usar este arquivo para iniciar a aplicação."
