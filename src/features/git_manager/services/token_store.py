import keyring

_APP = "ServiceDeck"


class TokenStore:
    def save(self, provider: str, token: str) -> None:
        keyring.set_password(_APP, provider, token)

    def load(self, provider: str) -> str:
        return keyring.get_password(_APP, provider) or ""

    def clear(self, provider: str) -> None:
        try:
            keyring.delete_password(_APP, provider)
        except keyring.errors.PasswordDeleteError:
            pass
