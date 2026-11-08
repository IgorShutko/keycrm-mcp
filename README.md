# keycrm-mcp

Неофициальный MCP-сервер для [KeyCRM](https://keycrm.app) (`<ваш-аккаунт>.keycrm.app`), не связан с вендором. Даёт Claude (Desktop, Code, любой MCP-клиент) прямой доступ к заказам, лидам, клиентам, товарам, задачам, чатам, настройкам и отчётам.

Реверс-инжиниринг сделан по живому аккаунту: 24 типизированных инструмента (15 ядро + 9 доменных) плюс универсальный доступ к 572 внутренним эндпоинтам. Как восстанавливался внутренний API: [docs/REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md).

> Внимание: 01.11.2026 во время реверса через опасный batch-эндпоинт было удалено 26 карточек воронки, все восстановлены из снимка. Правила безопасности и разбор: [docs/INCIDENT.md](docs/INCIDENT.md).

## Как устроено

Два независимых канала к одному аккаунту, сервер сам выбирает нужный:

| Канал | База | Авторизация | Что даёт |
|---|---|---|---|
| internal | `https://<домен>.api.keycrm.app` | email + пароль -> `access_token` (24 ч) + `refresh_token` | всё, что умеет веб-интерфейс: 572 эндпоинта |
| official | `https://openapi.keycrm.app/v1` | Bearer `api_token` (находится автоматически через `/config/api-client`) | документированный API, стабильные фильтры, лимит 20 запросов/мин |

Токены кешируются в памяти процесса, при 401 сервер сам перелогинивается, при 429 ждёт и повторяет.

## Установка

```powershell
cd C:\path\to\keycrm-mcp

# venv уже создан и зависимости стоят. Если переносите папку:
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

Настройки лежат в `.env`:

```
KEYCRM_DOMAIN=
KEYCRM_EMAIL=...
KEYCRM_PASSWORD=...
KEYCRM_API_TOKEN=...      # необязательно, сервер достанет сам
```

## Подключение к Claude Desktop

Открыть `%APPDATA%\Claude\claude_desktop_config.json` и добавить:

```json
{
  "mcpServers": {
    "keycrm": {
      "command": "C:\\path\\to\\keycrm-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\keycrm-mcp\\server.py"]
    }
  }
}
```

Перезапустить Claude Desktop. В списке инструментов появится `keycrm`.

## Подключение к Claude Code

```powershell
claude mcp add -s user keycrm -- "C:\path\to\keycrm-mcp\.venv\Scripts\python.exe" "C:\path\to\keycrm-mcp\server.py"
claude mcp get keycrm     # Status: Connected
```

Для non-interactive сессий Claude Code добавьте правило `mcp__keycrm__*` в `permissions.allow` файла `~/.claude/settings.json`, иначе вызовы будут заблокированы.

## CLI без MCP

Если MCP-клиента нет, а надо быстро из скрипта или терминала:

```powershell
.\.venv\Scripts\python.exe crm_cli.py status
.\.venv\Scripts\python.exe crm_cli.py get "/leads?limit=3"
.\.venv\Scripts\python.exe crm_cli.py official GET /pipelines
.\.venv\Scripts\python.exe crm_cli.py post /leads "{\"status_id\":1,\"communicate_at\":\"2026-11-10 12:00:00\",\"currency_code\":\"UAH\"}"
.\.venv\Scripts\python.exe crm_cli.py search-endpoints tags
.\.venv\Scripts\python.exe crm_cli.py check
```

`check` показывает счётчики и остатки тестовых объектов (MCP TEST) по карточкам, клиентам, заказам, задачам и товарам. Удобно после экспериментов.

## Пример живого отчёта

`demo/report_leads.json` собран этим сервером на реальных данных: 54 карточки за октябрь, 32 закрыты, 22 в работе, разбивка по статусам воронки.

```json
"cards": 54, "finished": 32, "active": 22,
"buckets": {"1": {"label": "Новий лід", "count": 7}, "8": {"label": "Не лід: спам, тест, дубль", "count": 17}}
```

## Инструменты

| Инструмент | Действия |
|---|---|
| `crm_status` | профиль, каналы, счётчики заказов/лидов/клиентов/товаров. С него начинать сессию |
| `orders` | `list`, `get`, `create`, `update`, `set_status`, `add_payment`, `expenses`, `set_marketing`, `add_product`, `update_product`, `remove_product`, `add_tag`, `remove_tag`, `remove`, `statuses`, `groups`, `totals`, `tags`, `sources` |
| `leads` | `list`, `get`, `create`, `update`, `move`, `pipelines`, `desk`, `complete`, `add_product`, `copy`, `remove` |
| `clients` | `list`, `get`, `create`, `update`, `delete`, `search`, `set_profile`, `orders`, `leads` (phone/email пишутся через profiles) |
| `products` | `list`, `get`, `create`, `update`, `delete`, `categories`, `warehouses` |
| `tasks` | `list`, `get`, `search`, `expired_count`, `create`, `update`, `complete`, `delete` |
| `conversations` | `list`, `get`, `messages`, `unread`, `send` |
| `users` | `list`, `roles`, `permissions` |
| `audit` | `list`, `by_entity` (order/lead/task/manufacturing), `by_manager` - история изменений |
| `settings` | срез `config/settings`: `general`, `orders`, `products`, `leads`, ... |
| `report` | `kind="sales" \| "leads" \| "funnel" \| "managers" \| "stale"`: выручка, воронка с конверсией, нагрузка менеджеров, зависшие карточки |
| `crm_capabilities` | активные модули аккаунта, лимиты, список известных проблем и опасных мест |
| `crm_snapshot` | локальный JSON-бэкап карточек, заказов, товаров, клиентов, справочников в `backups/`. Делать перед рискованными операциями |
| `crm_api` | сырой запрос в любой эндпоинт обоих API (с защитой от опасных batch-путей) |
| `crm_endpoints` | поиск по каталогу 572 внутренних маршрутов |

Доменные инструменты (`tools_domains.py`, читают живые справочники):

| Инструмент | Действия |
|---|---|
| `finance` | `bills`, `accounts`, `payments`, `payment_config`, `expense_types`, `payment_methods`, `payment_gateways`, `currency_rates`, `rates_common`, `fiscals`, `transactions`, `billing`, `billing_invoices`, `billing_payments` |
| `delivery` | `services`, `prep_centers`, `prep_centers_active`, `shipment_templates`, `warehouses`, `locations`, `streets`, `suggest`, `price`, `print` (без создания отправлений) |
| `publications` | `list`, `variations` (маркетплейсы) |
| `stocks` | `list`, `movements`, `movement`, `inventories`, `warehouses`, `stat`, `filters`, `history` |
| `comments` | `list`, `add`, `edit`, `delete` по lead/order/client/deal |
| `custom_fields` | `list`, `field`, `values` |
| `documents` | `list`, `by_scope`, `preview` (Twig), `preview_pdf` (сохраняет PDF в `exports/`), `print`, `attach` |
| `files` | `list_order`, `validate`, `attach_order` (multipart, 250 МБ, чанки), `download`, `detach`, `delete_file` |
| `automations` | `list`, `get` (триггеры, только чтение) |

## Примеры

```
Покажи мои заказы за октябрь, статус и сумму.
Создай сделку в воронке 1: Иван, +380501234567, бюджет 5000, следующий контакт 10.11.
Передвинь карточку 63 в статус "Квалификация".
Какой у нас средний чек и выручка за последние 30 дней?
Найди клиента по телефону 0501234567 и покажи его историю заказов.
Сделай воронку: сколько карточек в каждом статусе и какая конверсия.
```

Модель сама разберётся с action и параметрами, JSON-схемы инструментов это описывают.

## Что проверено

`test_smoke.py` поднимает сервер по stdio, как это делает Claude Desktop, и прогоняет 92 проверки: все инструменты на реальных данных, плюс полный цикл create/update/delete для клиента, товара и заказа с уборкой мусора в конце.

`test_domains.py` проверяет 8 доменных инструментов: 90 проверок, включая error-пути и цикл комментария.

```powershell
.\.venv\Scripts\python.exe test_smoke.py
.\.venv\Scripts\python.exe test_domains.py
```

## Ограничения этого аккаунта

- Задачи: создание работает, но тело специфичное (`name`, `priority`, `type`, `description`, `status`, `scheduled_at`, `assigned_to_id`, `period`, `settings`). Инструмент `tasks(action="create")` собирает его сам. Завершение: `PUT /tasks/{id}` с `{"id":..., "status":"done"}`.
- **Удаление карточек воронки заблокировано намеренно.** Рабочий формат `POST /batch/leads/execute/remove?filters[lead_ids]=..&column_ids=..&pipeline_id=..` при несовпадении id удаляет все карточки выбранных статусов. Это уже привело к потере 26 карточек (восстановлены). Карточки удаляйте вручную в KeyCRM UI.
- Внутренний `GET /orders` возвращает пустой список, поэтому `orders.list` ходит в официальный API.
- `batch`-удаление заказов асинхронное: объект исчезает через 2-5 секунд.
- Официальный API отдаёт UTC и лимит 20 запросов/мин; внутренний терпит 120.
- Дубли и внутренние особенности: клиентский телефон в интерфейсе живёт в `profiles`, а не в поле `phone`.
- Модуль заказов и чатов в аккаунте выключен (`is_active=false`), данных по ним нет: часть инструментов проверена на пустых коллекциях, а не на строках.
- `GET /finance/payments` и `/finance/transactions` отдают 500 на стороне KeyCRM, `/delivery/addresses/suggest` тоже 500. Справочники перевозчиков живые: `locations` по query, `warehouses` по `location_ref` (у Укрпошты это `id` из locations), `streets` у НП по query + location_ref.
- Статус по всем action: [docs/ACTION_MATRIX.md](docs/ACTION_MATRIX.md), 83 проверки, 78 ok, 5 честных ошибок.

## Файлы

```
server.py             MCP-сервер (FastMCP, stdio), 21 инструмент
tools_domains.py      доменные инструменты: finance/delivery/stocks/documents/... (register(mcp))
tools_files.py        вложения заказов: upload/attach/download/detach (register(mcp))
keycrm_client.py      транспорт: логин, токены, ретраи, пагинация
endpoints_catalog.py  поиск по каталогу маршрутов
endpoints.json        572 эндпоинта, вытащены из бандла v33.0.10
crm_cli.py            CLI для скриптов без MCP
test_smoke.py         end-to-end проверка через stdio (92 проверки)
test_domains.py       проверка доменных инструментов (90 проверок)
test_actions.py       read-only прогон всех action (83 проверки, docs/ACTION_MATRIX.md)
docs/                 QUICKSTART, TOOLS, API_REFERENCE, COOKBOOK, INCIDENT, ENDPOINTS_STATUS
exports/              скачанные файлы и PDF (создаётся по запросу)
backups/              локальные снапшоты CRM (создаётся crm_snapshot)
demo/                 примеры живых ответов сервера
run.cmd               запуск для Windows
run_all.cmd           все проверки: smoke + domains + actions + гигиена аккаунта
.env                  доступы (не коммитить)
```

## Безопасность

`.env` содержит пароль и API-токен аккаунта. Файл локальный, в git не добавляйте. Если токен утечёт: Настройки -> API в KeyCRM -> перевыпустить. `crm_snapshot` маскирует ключи с token/password/secret/api_key/auth_key в бэкапе, но остальные данные (телефоны, суммы, переписка) пишутся как есть: храните папку `backups/` локально.

## Как это реверсили

Фронт KeyCRM это Vue SPA. Авторизация: `POST https://<домен>.api.keycrm.app/auth/login` с `{username, password}` возвращает `access_token` и `refresh_token`, дальше обычный `Authorization: Bearer`. Из бандла `app.js` (build v33.0.10) вытащена карта маршрутов вида `name:["method","/path"]`, это и есть `endpoints.json`. Официальный ключ нашёлся в `GET /config/api-client` и работает на `openapi.keycrm.app/v1`.

## Лицензия

MIT. Внутренний API keyCRM недокументирован и может измениться с любой сборкой SPA. Используйте на свой риск и сначала на тестовом аккаунте.
