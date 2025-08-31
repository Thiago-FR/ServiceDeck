#!/bin/bash

# --- CORREÇÃO CRÍTICA ---
# Garante que todos os comandos seguintes sejam executados a partir
# do diretório onde o próprio script está localizado.
cd "$(dirname "$0")"

# Pega o caminho absoluto para o diretório do app, já estando nele.
APP_DIR=$(pwd)

# Define os caminhos completos para o executável e o ícone
EXEC_PATH="${APP_DIR}/dist/ServiceDeck/ServiceDeck"
ICON_PATH="${APP_DIR}/app/assets/icon.png"



echo "Configurando o atalho para o executável em: ${EXEC_PATH}"
echo "Usando o ícone em: ${ICON_PATH}"

# Cria o arquivo .desktop com os caminhos corretos
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

# Dá permissão de execução ao lançador
chmod +x ServiceDeck.desktop

echo ""
echo "Lançador 'ServiceDeck.desktop' criado com sucesso!"
echo "Você já pode usar este arquivo para iniciar a aplicação."

