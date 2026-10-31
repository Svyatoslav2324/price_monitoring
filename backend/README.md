# Backend: мониторинг цен на маркетплейсах

Django 5.2 + Django REST Framework + PostgreSQL. Сейчас подключён **Wildberries**; Ozon и Яндекс Маркет
добавляются отдельными модулями (см. «Как добавить маркетплейс»).

## Запуск локально

Нужны Python 3.12+ и запущенный PostgreSQL.

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # прописать POSTGRES_PASSWORD
createdb -U postgres price_monitoring
python manage.py migrate
python manage.py createsuperuser  # для /admin/, по желанию

python manage.py runserver        # API: http://localhost:8000/api/
python manage.py run_price_worker # воркер проверки цен, во втором терминале
```

Тесты: `python manage.py test` гоняет их на Postgres; `python manage.py test --settings=config.settings_test` —
на SQLite в памяти, без БД.

> ⚠️ API Wildberries (`card.wb.ru`) отвечает **403 на запросы не из РФ**. Сервер и воркер должны работать
> с российского IP, иначе добавить товар не получится (ответ 502).

## Структура

```
backend/
├── config/                     # settings, корневые urls, wsgi
└── modules/
    ├── accounts/               # регистрация, вход, токены
    ├── products/               # товары, история цен, загрузка карточки (services.py)
    ├── tracking/               # отслеживания пользователя + воркер (worker.py)
    │   └── management/commands/run_price_worker.py
    └── marketplaces/           # интеграции, без моделей
        ├── base.py             # контракт: ProductSnapshot, ошибки
        ├── registry.py         # URL -> нужный маркетплейс
        ├── errors.py           # ошибки маркетплейсов -> HTTP
        └── wildberries/        # клиент WB + свои роуты
```

Модули зависят друг от друга только в одну сторону: `tracking → products → marketplaces`.
`accounts` ни от кого не зависит.

## API

Базовый путь — `/api/`. Ответы в JSON, цены — числа в рублях (`23999.0`).
Авторизация: заголовок `Authorization: Token <token>`. Без него все роуты, кроме помеченных 🔓, отвечают `401`.

### Служебное

| Метод | Путь | Описание |
|---|---|---|
| GET 🔓 | `/api/health/` | Проверка живости: `{"status": "ok"}` |
| — | `/admin/` | Django admin (только staff) |

### Аккаунт — `modules/accounts`

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| POST 🔓 | `/api/auth/register/` | `{username, password}` | `201 {token, user}` |
| POST 🔓 | `/api/auth/login/` | `{username, password}` | `200 {token, user}` / `400` неверные данные |
| POST | `/api/auth/logout/` | — | `204`, токен удаляется |
| GET | `/api/auth/me/` | — | `{id, username, date_joined}` |

### Отслеживания — `modules/tracking`

Отслеживание — подписка пользователя на цену товара с желаемой ценой и частотой проверки.

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/trackings/` | Список своих отслеживаний, товар вложен |
| POST | `/api/trackings/` | Добавить: `{url, check_interval, target_price}` |
| GET | `/api/trackings/{id}/` | Одно отслеживание |
| PATCH | `/api/trackings/{id}/` | Изменить `status` (`active`/`paused`), `check_interval`, `target_price` |
| DELETE | `/api/trackings/{id}/` | Удалить (`204`). Товар и его история остаются |

Пример ответа:

```json
{
  "id": 1,
  "product": {
    "id": 1, "marketplace": "wildberries", "marketplace_name": "Wildberries",
    "external_id": "169684889", "url": "https://www.wildberries.ru/catalog/169684889/detail.aspx",
    "title": "Sony / Наушники WH-1000XM5", "current_price": 23999.0, "in_stock": true,
    "last_checked_at": "2026-11-01T12:00:00+03:00", "last_error": ""
  },
  "status": "active", "check_interval": 60, "target_price": 21000.0,
  "target_reached_at": null, "created_at": "…", "updated_at": "…"
}
```

`POST /api/trackings/` при новом товаре сразу запрашивает карточку с маркетплейса. Возможные ответы:

| Код | Когда |
|---|---|
| `201` | Отслеживание создано |
| `400` | Неподдерживаемый маркетплейс, кривая ссылка, `target_price <= 0`, недопустимый `check_interval` |
| `404` | Товара нет на маркетплейсе |
| `409` | Пользователь уже отслеживает этот товар |
| `502` | Маркетплейс недоступен или заблокировал запрос |

### Товары — `modules/products`

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/products/{id}/` | Товар + `tracking: {id, target_price, status}` текущего пользователя |
| GET | `/api/products/{id}/history/?days=30` | Точки цены `[{price, checked_at}]` за `days` дней (1–365, по умолчанию 30) |

### Маркетплейсы — `modules/marketplaces`

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/marketplaces/` | Поддерживаемые маркетплейсы: `[{code, name, hosts}]` |
| GET | `/api/marketplaces/wildberries/products/{nm_id}/` | Живой предпросмотр карточки WB по артикулу, в БД не сохраняется |

## Политики

**Доступ**
- Пользователь видит и меняет только свои отслеживания; чужой `id` → `404` (не `403`, чтобы не выдавать, что запись есть).
- Товар (`/api/products/{id}/…`) доступен, только если пользователь его отслеживает.
- Товар общий для всех: одна карточка и одна история цен на всех подписчиков, маркетплейс опрашивается один раз.

**Аутентификация**
- Логин: 3–32 символа, `A-Z a-z 0-9 _ . -`, без учёта регистра при проверке на уникальность.
- Пароль: не короче 6 символов и не из списка популярных паролей.
- Токен один на пользователя и бессрочный; `logout` удаляет его, то есть выходит на всех устройствах.

**Лимиты запросов** (DRF throttling)

| Кто / что | Лимит |
|---|---|
| Аноним | 60/мин |
| Авторизованный пользователь | 600/мин |
| `register`, `login` | 10/мин на IP |
| Предпросмотр маркетплейса | 30/мин |

Счётчики живут в кэше Django (по умолчанию в памяти процесса). При нескольких процессах gunicorn
подключите общий кэш (Redis) в `CACHES`, иначе лимит считается на каждый процесс отдельно.

**Статусы отслеживания**

| Статус | Кто ставит | Смысл |
|---|---|---|
| `active` | клиент / воркер | Проверяется по расписанию |
| `paused` | клиент | Не проверяется |
| `error` | воркер | Товар пропал с маркетплейса. Воркер продолжает проверять и вернёт `active`, когда товар появится |

Временные сбои (таймаут, 5xx, 429) статус не меняют: текст ошибки пишется в `product.last_error`,
проверка повторится на следующем цикле.

**Проверка цен (воркер)**
- `check_interval`: `60` (каждый час), `360` (раз в 6 часов), `1440` (раз в день).
- Если товар отслеживают несколько человек, он проверяется с самым частым из их интервалов.
- История пишется при каждой проверке, когда товар в наличии. Нет в наличии → `in_stock=false`, `current_price=null`.
- Когда цена опускается до `target_price` или ниже, у отслеживания ставится `target_reached_at` (один раз).
  При изменении `target_price` флаг сбрасывается. Доставки уведомлений пока нет: событие пишется в лог (`worker.py`).
- Безопасно запускать несколько воркеров: товары захватываются через `SELECT … FOR UPDATE SKIP LOCKED`.
- `run_price_worker --once` выполняет одну итерацию; удобно для cron или systemd timer.

**Wildberries**
- Принимаются ссылки `wildberries.ru` / `wb.ru` вида `/catalog/<артикул>/…`.
- Цена — минимальная по размерам, со скидкой продавца (`sizes[].price.product`), без скидки WB-кошелька.
- Регион доставки задаётся в `WB_DEST` (по умолчанию Москва) и влияет на цену и наличие.
- До 3 попыток на запрос с паузой 1 с и 2 с; повторяются только 429, 5xx и сетевые ошибки.

## Как добавить маркетплейс

1. `modules/marketplaces/<code>/client.py` с `CODE`, `NAME`, `HOSTS`, `PRODUCT_URL`, `parse_url(url)` и
   `fetch(external_id) -> ProductSnapshot`. Ошибки — `ProductNotFound` / `MarketplaceError` из `base.py`.
2. Добавить модуль в `PROVIDERS` в `registry.py`.
3. При необходимости свои роуты в `<code>/urls.py` и подключить их в `marketplaces/urls.py`.

Модели, воркер и API трогать не нужно.

## Продакшен

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=<случайная строка> DJANGO_ALLOWED_HOSTS=api.example.com \
CORS_ALLOWED_ORIGINS=https://example.com
python manage.py migrate && python manage.py collectstatic --noinput
gunicorn config.wsgi -w 4 -b 0.0.0.0:8000
python manage.py run_price_worker   # отдельный процесс (systemd / supervisor)
```

- TLS, HSTS и редирект на HTTPS настраиваются на reverse-proxy (nginx). Django доверяет `X-Forwarded-Proto`.
- При `DJANGO_DEBUG=0` без `DJANGO_SECRET_KEY` приложение не стартует.

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DJANGO_DEBUG` | `0` | `1` — режим разработки |
| `DJANGO_SECRET_KEY` | — | Обязательна при `DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Через запятую |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origin фронтенда |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | `price_monitoring/postgres/—/localhost/5432` | Подключение к БД |
| `WB_DEST` | `-1257786` | Регион доставки WB |
| `WB_TIMEOUT` | `10` | Таймаут запроса к WB, с |
| `WORKER_BATCH_SIZE` | `20` | Сколько товаров воркер берёт за итерацию |
| `WORKER_IDLE_SECONDS` | `30` | Пауза, когда проверять нечего |
| `LOG_LEVEL` | `INFO` | Уровень логов |
