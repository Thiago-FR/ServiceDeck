from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PullRequestResult:
    url: str
    number: int
    provider: str


class GitProvider(ABC):
    @abstractmethod
    def validate_token(self, token: str) -> bool: ...

    @abstractmethod
    def create_pull_request(
        self,
        token: str,
        remote_url: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> PullRequestResult: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
