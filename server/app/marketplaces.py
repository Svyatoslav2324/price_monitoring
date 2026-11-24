from urllib.parse import urlsplit

# Names match marketplaces.name; IDs are assigned by the database.
DOMAINS = {
    "Ozon": "ozon.ru",
    "Wildberries": "wildberries.ru",
    "AliExpress": "aliexpress.ru",
    "Yandex Market": "market.yandex.ru",
}


def marketplace_for(url):
    parts = urlsplit(url)
    host = parts.hostname or ""
    if (parts.scheme in ("https", "http") and parts.username is None and
            parts.port in (None, 80, 443) and len(url) <= 255):
        for name, domain in DOMAINS.items():
            if host == domain or host.endswith("." + domain):
                if name == "Ozon" and (host not in (domain, "www." + domain, "m." + domain)
                                       or not parts.path.startswith("/product/")):
                    break
                return name
    raise ValueError("Укажите ссылку на карточку товара поддерживаемого маркетплейса")
