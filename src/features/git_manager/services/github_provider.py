import requests

from src.features.git_manager.services.git_provider import GitProvider, PullRequestResult
from src.features.git_manager.services.provider_detector import parse_owner_repo

_API = "https://api.github.com"


class GitHubProvider(GitProvider):
    @property
    def name(self) -> str:
        return "github"

    def validate_token(self, token: str) -> bool:
        response = requests.get(
            f"{_API}/user",
            headers=_headers(token),
            timeout=10,
        )
        return response.status_code == 200

    def create_pull_request(
        self,
        token: str,
        remote_url: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> PullRequestResult:
        parsed = parse_owner_repo(remote_url)
        if not parsed:
            raise ValueError(f"Não foi possível extrair owner/repo de: {remote_url}")

        owner, repo = parsed
        response = requests.post(
            f"{_API}/repos/{owner}/{repo}/pulls",
            headers=_headers(token),
            json={"title": title, "body": body, "head": head_branch, "base": base_branch},
            timeout=15,
        )
        if response.status_code not in (200, 201):
            body = response.json()
            errors = body.get("errors", [])
            detail = "; ".join(e.get("message", str(e)) for e in errors) if errors else ""
            msg = body.get("message", "")
            full = msg + (f" — {detail}" if detail else "")

            if "No commits between" in full:
                raise RuntimeError(
                    "Branches idênticas — não há commits novos para abrir PR."
                )
            if "pull request already exists" in full.lower():
                raise RuntimeError("PR já existe para esta branch.")
            raise RuntimeError(f"Erro ao criar PR ({response.status_code}): {full}")

        data = response.json()
        return PullRequestResult(
            url=data["html_url"],
            number=data["number"],
            provider="github",
        )


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
