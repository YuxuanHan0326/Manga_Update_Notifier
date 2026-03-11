from .copymanga import CopyMangaAdapter
from .kxo import KxoAdapter
from .registry import register_adapter


def register_builtin_adapters() -> None:
    register_adapter(CopyMangaAdapter())
    register_adapter(KxoAdapter())
