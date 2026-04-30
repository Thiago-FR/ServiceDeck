#!/bin/bash

cd "$(dirname "$0")"
APP_DIR=$(pwd)

# Cenário 1: script está dentro de _internal/ do pacote de release
#   estrutura: ServiceDeck/ ← executável, _internal/setup.sh ← este script
if [ -f "${APP_DIR}/../ServiceDeck" ]; then
    EXEC_PATH="$(realpath "${APP_DIR}/../ServiceDeck")"
    ICON_PATH="${APP_DIR}/app/assets/icon.png"
    DESKTOP_DIR="$(realpath "${APP_DIR}/..")"

# Cenário 2: dev após build local com PyInstaller
#   estrutura: projeto/dist/ServiceDeck/ServiceDeck + _internal/
elif [ -f "${APP_DIR}/dist/ServiceDeck/ServiceDeck" ]; then
    EXEC_PATH="${APP_DIR}/dist/ServiceDeck/ServiceDeck"
    ICON_PATH="${APP_DIR}/app/assets/icon.png"
    DESKTOP_DIR="${APP_DIR}"

# Cenário 3: executável na mesma pasta que o script (release extraído na raiz)
elif [ -f "${APP_DIR}/ServiceDeck" ]; then
    EXEC_PATH="${APP_DIR}/ServiceDeck"
    ICON_PATH="${APP_DIR}/_internal/app/assets/icon.png"
    DESKTOP_DIR="${APP_DIR}"

else
    echo "ERRO: Executável 'ServiceDeck' não encontrado."
    echo "Certifique-se de que este script está dentro do pacote correto."
    exit 1
fi

echo "Configurando o atalho para o executável em: ${EXEC_PATH}"
echo "Usando o ícone em: ${ICON_PATH}"

cat > "${DESKTOP_DIR}/ServiceDeck.desktop" << EOL
[Desktop Entry]
Version=1.0
Name=ServiceDeck
Comment=Gerenciador de Microserviços
Type=Application
Terminal=false
Exec="${EXEC_PATH}"
Icon=${ICON_PATH}
Categories=Development;Utility;
EOL

chmod +x "${DESKTOP_DIR}/ServiceDeck.desktop"

# Instala no menu de aplicativos do sistema
mkdir -p ~/.local/share/applications
cp "${DESKTOP_DIR}/ServiceDeck.desktop" ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true

echo ""
echo "Lançador criado em: ${DESKTOP_DIR}/ServiceDeck.desktop"
echo "Ícone instalado no menu de aplicativos do sistema."
