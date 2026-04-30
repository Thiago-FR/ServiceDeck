# ServiceDeck

Gerenciador de microserviços com interface gráfica. Permite iniciar, monitorar e abrir no editor todos os seus serviços a partir de um único lugar.

## Download

| Plataforma | Link |
|------------|------|
| Linux .deb | [ServiceDeck.deb](https://github.com/Thiago-FR/ServiceDeck/releases/latest/download/ServiceDeck.deb) |
| Linux .tar.gz | [ServiceDeck-linux.tar.gz](https://github.com/Thiago-FR/ServiceDeck/releases/latest/download/ServiceDeck-linux.tar.gz) |
| Windows    | [ServiceDeck-windows.zip](https://github.com/Thiago-FR/ServiceDeck/releases/latest/download/ServiceDeck-windows.zip) |

## Como usar

### Linux

**Opção 1 — .deb (recomendado para Ubuntu/Debian):**

```bash
sudo dpkg -i ServiceDeck.deb
```

Ou duplo clique no arquivo `.deb` para instalar pela Central de Programas.

**Opção 2 — tar.gz:**

```bash
tar -xzf ServiceDeck-linux.tar.gz
cd ServiceDeck
./ServiceDeck
```

> **Opcional:** rode `bash _internal/setup.sh` para criar um atalho na área de trabalho e instalar no menu de aplicativos do sistema.

### Windows

1. Extrair o `.zip`
2. Entrar na pasta `ServiceDeck`
3. Executar `ServiceDeck.exe`

> **Aviso do Windows SmartScreen:** como o executável não possui assinatura digital, o Windows pode exibir um aviso de segurança. Clique em **"Mais informações" → "Executar assim mesmo"** para prosseguir. Isso é normal para aplicações open source distribuídas sem certificado pago.

---

## Desenvolvimento

### Pré-requisitos

```bash
python -m venv .venv
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Rodar sem build

```bash
python main.py
```

Ou use o script que gerencia o venv automaticamente:

```bash
./run.sh
```

### Gerar build

**Linux:**
```bash
pyinstaller ServiceDeck.spec && bash setup.sh
```

**Windows:**
```bash
pyinstaller ServiceDeck_windows.spec
```

## Melhorias futuras

**Médio prazo:**

| Ideia | Por quê |
|-------|---------|
| **Perfis/grupos de serviços** | Dev tem projeto A com 4 serviços e projeto B com 6 — hoje precisa reconfigurar tudo ao trocar |
| **Auto-detect mais stacks** | Detectar `Makefile`, `docker-compose.yml`, `Cargo.toml`, `pyproject.toml` e sugerir o comando adequado |
| **System tray** | Minimizar para a bandeja em vez de fechar — app fica rodando sem ocupar taskbar |
| **Botão copiar log** | Simples, mas útil pra debugar |

**Futuro:**

| Ideia | Por quê |
|-------|---------|
| **Verificação de atualização** | Checar no GitHub Releases se tem versão nova e avisar o usuário |
| **Porta detectada automaticamente** | Quando o serviço sobe, mostrar em qual porta está respondendo |

---

### Publicar nova versão

```bash
git tag v1.0.0
git push origin v1.0.0
```

O GitHub Actions irá compilar automaticamente para Linux e Windows e publicar os executáveis na aba [Releases](https://github.com/Thiago-FR/ServiceDeck/releases).
