from __future__ import annotations

from collections.abc import Iterable

from .base import SourceAdapter

_ADAPTERS: dict[str, SourceAdapter] = {}


def register_adapter(adapter: SourceAdapter) -> None:
    # Registry is keyed by stable source code to keep API payload compact.
    _ADAPTERS[adapter.code] = adapter


def get_adapter(code: str) -> SourceAdapter:
    if code not in _ADAPTERS:
        raise KeyError(f"unsupported source: {code}")
    return _ADAPTERS[code]


def list_adapters() -> Iterable[SourceAdapter]:
    return _ADAPTERS.values()
