from .copymanga import CopyMangaAdapter
from .registry import register_adapter


def register_builtin_adapters() -> None:
    register_adapter(CopyMangaAdapter())
