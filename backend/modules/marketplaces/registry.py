from urllib.parse import urlsplit

from .base import UnsupportedURL
from .wildberries import client as wildberries

# Новый маркетплейс = новый модуль-клиент + строка здесь
PROVIDERS = {p.CODE: p for p in (wildberries,)}


def get_provider(code: str):
    return PROVIDERS[code]


def resolve(url: str):
    """URL товара -> (provider, external_id). Бросает UnsupportedURL."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsupportedURL("Вставьте полную ссылку, начиная с https://")

    host = parts.hostname.lower().removeprefix("www.")
    for provider in PROVIDERS.values():
        if any(host == h or host.endswith("." + h) for h in provider.HOSTS):
            external_id = provider.parse_url(url)
            if not external_id:
                raise UnsupportedURL(f"Не удалось распознать ссылку на товар {provider.NAME}")
            return provider, external_id

    names = ", ".join(p.NAME for p in PROVIDERS.values())
    raise UnsupportedURL(f"Этот маркетплейс пока не поддерживается. Доступны: {names}")
