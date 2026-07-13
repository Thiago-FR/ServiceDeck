import re

PROVIDERS = {
    "github.com": "github",
    "gitlab.com": "gitlab",
    "bitbucket.org": "bitbucket",
}


def detect_provider(remote_url: str) -> str | None:
    for host, name in PROVIDERS.items():
        if host in remote_url:
            return name
    return None


def parse_owner_repo(remote_url: str) -> tuple[str, str] | None:
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\\.]+?)(?:\.git)?$",
        r"gitlab\.com[:/]([^/]+)/([^/\\.]+?)(?:\.git)?$",
        r"bitbucket\.org[:/]([^/]+)/([^/\\.]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote_url)
        if match:
            return match.group(1), match.group(2)
    return None
