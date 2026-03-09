from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AdapterError(Exception):
    """Base exception for adapter failures."""


class AdapterUpstreamError(AdapterError):
    """Raised when upstream source returns invalid or unusable responses."""


@dataclass
class AdapterSearchResult:
    item_id: str
    title: str
    cover: str = ""
    author: str = ""
    group_word: str = "default"
    meta: dict | None = None


@dataclass
class AdapterUpdate:
    update_id: str
    title: str
    url: str


@dataclass
class SearchPage:
    page: int
    total: int
    items: list[AdapterSearchResult]


class SourceAdapter(Protocol):
    code: str
    name: str

    def search(self, query: str, page: int) -> SearchPage: ...

    def list_updates(self, item_id: str, item_meta: dict | None = None) -> list[AdapterUpdate]: ...

    def healthcheck(self) -> bool: ...
