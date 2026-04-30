# ServiceDeck

Gerenciador de microserviços com interface gráfica. Permite iniciar, monitorar e abrir no editor todos os seus serviços a partir de um único lugar.

## Download

| Plataforma | Link |
|------------|------|
| Linux      | [ServiceDeck-linux.tar.gz](https://github.com/Thiago-FR/ServiceDeck/releases/latest/download/ServiceDeck-linux.tar.gz) |
| Windows    | [ServiceDeck-windows.zip](https://github.com/Thiago-FR/ServiceDeck/releases/latest/download/ServiceDeck-windows.zip) |

## Como usar

### Linux

```bash
# Extrair
tar -xzf ServiceDeck-linux.tar.gz

# Entrar na pasta
cd ServiceDeck

# (Opcional) Criar atalho no sistema
bash setup.sh

# Executar diretamente
./ServiceDeck
```

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

### Gerar build

**Linux:**
```bash
pyinstaller ServiceDeck.spec && bash setup.sh
```

**Windows:**
```bash
pyinstaller ServiceDeck_windows.spec
```

### Publicar nova versão

```bash
git tag v1.0.0
git push origin v1.0.0
```

O GitHub Actions irá compilar automaticamente para Linux e Windows e publicar os executáveis na aba [Releases](https://github.com/Thiago-FR/ServiceDeck/releases).
