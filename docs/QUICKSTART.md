# QUICKSTART: keycrm-mcp за 10 минут

MCP-сервер для аккаунта `your-account.keycrm.app`. Даёт MCP-клиенту (Claude Desktop, Claude Code, любой другой) прямой доступ к заказам, карточкам воронки, клиентам, каталогу, задачам, перепискам, финансам, складу, настройкам, вложениям и печатным документам.

Что внутри:

- 24 инструмента: 15 основных из `server.py` (включая `crm_status`, `crm_capabilities`, `crm_snapshot`, `crm_endpoints`, `crm_api`, `audit`), 8 доменных из `tools_domains.py` (финансы, доставка, публикации, склад, комментарии, кастомные поля, документы, автоматизации) и `files` из `tools_files.py` для вложений заказов. Полный справочник - в [TOOLS.md](TOOLS.md).
- Локальные бэкапы: `crm_snapshot` сохраняет карточки, заказы, товары, клиентов, статусы и настройки в `keycrm-mcp/backups/`. Вызывать перед любой рискованной операцией.
- Два канала к одному аккаунту: внутренний API `https://<домен>.api.keycrm.app` (572 маршрута, те же, что у веб-интерфейса) и официальный `https://openapi.keycrm.app/v1`.
- Универсальный `crm_api` для любого маршрута и `crm_endpoints` для поиска по каталогу.
- Предохранители: удаление карточек воронки заблокировано на уровне сервера, опасные batch-запросы тоже. Подробности в разделе "Опасные эндпоинты" и в [INCIDENT.md](INCIDENT.md).
- Документы и файлы: `documents` рендерит Twig-шаблон на демо-данных и сохраняет настоящий PDF в `exports/`; `files` грузит вложения заказов чанками и скачивает их. Шаблонов печати в аккаунте 0, поэтому `print` и `attach` отвечают `templates: 0`.

Проверено на этом аккаунте 2026-11-01, файлы и документы - 2026-11-02. Все цифры ниже - реальные ответы сервера на эти даты.

## 1. Что нужно

| Компонент | Версия / путь |
|---|---|
| Python | 3.13.15 в `.venv` этого проекта |
| Зависимости | `mcp>=1.2,<2`, `httpx>=0.27`, `python-dotenv>=1.0` (`requirements.txt`) |
| ОС | Windows (в репозитории есть `run.cmd`), на Linux/macOS те же команды без `.exe` |
| Доступ | email + пароль владельца аккаунта KeyCRM и/или API-токен |

Ниже `C:\path\to\keycrm-mcp` это папка, куда вы склонировали репозиторий.

## 2. Установка

```powershell
cd C:\path\to\keycrm-mcp

# venv + зависимости (если папку переносили или .venv нет)
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

Если `uv` не стоит:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`run.cmd` делает то же самое сам: создаёт `.venv`, ставит зависимости, запускает `server.py`.

## 3. Настройки: `.env`

Файл `.env` лежит рядом с `keycrm_client.py`, читается автоматически при импорте. Шаблон - `.env.example`.

```
KEYCRM_DOMAIN=
KEYCRM_EMAIL=...
KEYCRM_PASSWORD=...
KEYCRM_API_TOKEN=...      # необязательно
```

| Переменная | Обязательна | Зачем |
|---|---|---|
| `KEYCRM_DOMAIN` | да | поддомен аккаунта, для `your-account.keycrm.app` пишется `your-account` |
| `KEYCRM_EMAIL` | да для внутреннего API | логин владельца, уходит в `POST /auth/login` |
| `KEYCRM_PASSWORD` | да для внутреннего API | пароль того же пользователя |
| `KEYCRM_API_TOKEN` | нет | Bearer-токен официального API. Если пусто, сервер сам достаёт его из `GET /config/api-client` |
| `KEYCRM_OPENAPI_BASE` | нет | переопределить базу официального API (по умолчанию `https://openapi.keycrm.app/v1`) |
| `KEYCRM_APP_ORIGIN` | нет | Origin/Referer для внутреннего API (по умолчанию `https://<домен>.keycrm.app`) |

Пароль и токен дают полный доступ к аккаунту. `.env` не коммитить, в git не добавлять.

## 4. Первая проверка без MCP

```powershell
.\.venv\Scripts\python.exe crm_cli.py status
```

Живой ответ на 2026-11-01 (полный профиль сокращён до ключевых полей):

```json
{
 "domain": "your-account",
 "profile": {"id": 4, "full_name": "Owner Name", "email": "owner@example.com", "is_owner": true},
 "official_token": true
}
```

Если ответ такой, оба канала живы. Официальный токен находится через внутренний API, поэтому `status` проверяет сразу оба.

Что ещё умеет CLI:

```powershell
.\.venv\Scripts\python.exe crm_cli.py get "/leads?limit=3"
.\.venv\Scripts\python.exe crm_cli.py official GET /pipelines
.\.venv\Scripts\python.exe crm_cli.py search-endpoints tags
.\.venv\Scripts\python.exe crm_cli.py post /leads "{\"status_id\":1,\"communicate_at\":\"2026-11-10 12:00:00\",\"currency_code\":\"UAH\"}"
```

Команда `post` пишет в CRM. Для проверки сначала используйте `status`, `get` и `official GET`.

## 5. Подключение к Claude Desktop

1. Открыть `%APPDATA%\Claude\claude_desktop_config.json`. Если файла нет - создать.
2. Добавить сервер (готовый вариант лежит в `claude_desktop_config.json` проекта):

```json
{
  "mcpServers": {
    "keycrm": {
      "command": "C:\\path\\to\\keycrm-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\keycrm-mcp\\server.py"
      ]
    }
  }
}
```

3. Полностью перезапустить Claude Desktop (не просто закрыть окно).
4. В списке MCP-инструментов появится `keycrm`: 24 инструмента, первый - `crm_status`.

Пути должны быть абсолютными. Если переносите папку, правится только `command` и `args`.

## 6. Подключение к Claude Code

```powershell
claude mcp add keycrm -- "C:\path\to\keycrm-mcp\.venv\Scripts\python.exe" "C:\path\to\keycrm-mcp\server.py"
```

Проверка: `claude mcp list` показывает `keycrm`, в сессии команда `/mcp` показывает статус соединения.

## 7. Первый запрос

Начинать сессию с `crm_status`: он проверяет оба канала и отдаёт счётчики. Живой ответ (2026-11-01):

```json
{
 "ok": true,
 "data": {
  "domain": "your-account",
  "internal_api": "https://your-account.api.keycrm.app",
  "official_api": "https://openapi.keycrm.app/v1",
  "profile": {"id": 4, "full_name": "Owner Name", "role_id": 1, "is_owner": true, "status": "active"},
  "channels": {"official": "ok"},
  "api_client": {"id": "00000000-0000-0000-0000-000000000000", "name": "your-account-default-app", "request_limit": 120, "is_active": 1},
  "counters": {"orders": 0, "cards": 32, "clients": 0, "products": 3, "users": 3}
 }
}
```

Дальше можно спрашивать обычным текстом:

```
Покажи карточки воронки за неделю с разбивкой по статусам.
Найди в карточках телефон +380501234567 и покажи, на каком статусе сделка.
Сделай сводку по лидам за октябрь по менеджерам.
Какие статусы заказов есть в аккаунте?
```

Модель сама выберет инструмент и action. Если она промахнулась, подскажите точный action: `orders` -> `statuses`, `leads` -> `pipelines`, `report` -> `kind="leads"`.

Второй обязательный вызов - `crm_capabilities`: он показывает активные модули аккаунта, лимит API и список известных сломанных маршрутов, чтобы модель не тратила попытки на мёртвые эндпоинты. Реальный ответ на 2026-11-01: модуль `leads` активен, `orders`, `conversations`, `manufacturing`, `companies` выключены, `api_request_limit` 120.

Третий полезный вызов - `crm_snapshot`: локальный JSON-снимок карточек, заказов, товаров, клиентов, статусов и настроек в `keycrm-mcp/backups/`. Стоит вызывать перед любой операцией с записью, особенно массовой. В CRM при этом ничего не меняется. Креды в файле маскируются (ключи с `token`, `password`, `secret`, `api_key`, `auth_key`, `authorization`, `session`, `cookie` заменяются на `***`), но телефоны, суммы и переписка остаются как есть: снимок чувствительный, наружу его не выкладывать.

Четвёртый - `audit`: история изменений аккаунта. Фильтры: все события (`list`), по объекту (`by_entity`, `entity_type` = `order`, `lead`, `task`, `manufacturing` + `entity_id`), по менеджеру (`by_manager` + `manager_id`). На 02.11.2026 в аккаунте 1139 событий.

## 8. Опасные эндпоинты

Этот раздел читать до любых экспериментов с записью.

**Инцидент 01.11.2026.** При параллельном реверс-инжиниринге удалили 26 реальных карточек воронки, восстановили из снимка канбана (26 из 26). Виновник - `POST /batch/leads/execute/remove` с параметрами в query string:

```
POST /batch/leads/execute/remove
     ?filters[lead_ids]=<id>
     &column_ids=1,2,3,10,11,12,13
     &pipeline_id=1
     body {}
```

Если `filters[lead_ids]` не совпал точно (пустой, другой формат, чужой id), сервер удаляет **все карточки** из перечисленных колонок `column_ids`. Это не ошибка клиента, это поведение эндпоинта. Пострадали статусы 1, 2, 10, 12.

Что сделано:

1. `leads(action="remove")` заблокирован: возвращает `{"ok": false}` с объяснением, HTTP-запрос не уходит.
2. `crm_api` блокирует путь `/batch/leads/execute/remove` целиком.
3. `crm_api` блокирует любой `/batch/...` запрос, в `query` которого есть `column_ids`: такой запрос может задеть все карточки выбранных колонок.
4. Правило: карточки воронки удаляются **только вручную в интерфейсе KeyCRM**. Через API - никогда.
5. Перед любой рискованной операцией вызывать `crm_snapshot`: локальный снимок карточек и статусов в `backups/`. Именно такой снимок позволил восстановить удалённое 01.11.2026.

Безопасные удаления, которые разрешены: `DELETE /tasks/{id}` (`tasks action="delete"`), `DELETE /clients/{id}` (`clients action="delete"`), `POST /batch/orders/execute/remove` с телом `{"ids":[...]}` (`orders action="remove"`, асинхронно). Перед каждым - проверить, что удаляется ровно нужный объект.

Полный отчёт: [INCIDENT.md](INCIDENT.md) в рабочей папке.

## 9. Проверка полным тестом

`test_smoke.py` поднимает сервер по stdio, как Claude Desktop, и прогоняет все инструменты на живых данных.

```powershell
.\.venv\Scripts\python.exe test_smoke.py
```

Сейчас в нём 92 проверки: добавились `files`, `documents` (превью HTML, PDF, поведение без шаблонов) и `audit`. `test_domains.py` делает 90 проверок доменных инструментов.

Третий прогон - `test_actions.py`: read-only обход всех action, 83 проверки, 78 ok и 5 честных ошибок (finance payments/transactions 500, delivery suggest 500, stocks inventories 404 без движения, files list_order 404 без заказа). Результат - [ACTION_MATRIX.md](ACTION_MATRIX.md), машинный вариант - `ACTION_MATRIX.json` в этой же папке.

```powershell
.\.venv\Scripts\python.exe test_actions.py
```

Важно: тест пишет в CRM. Он создаёт тестового клиента, товар и заказ, потом удаляет их; счётчики возвращаются к базовым. Создание карточки воронки выключено по умолчанию, потому что удаление карточек через API заблокировано. Включается так:

```powershell
$env:KEYCRM_TEST_LEADS = "1"
.\.venv\Scripts\python.exe test_smoke.py
```

После включения в аккаунте останется тестовая карточка, её придётся удалить руками.

## 10. Диагностика

Все ошибки инструменты возвращают в одном формате, без исключений наружу:

```json
{"ok": false, "error": {"status": 500, "api": "internal", "message": "Server Error", "body": {...}}}
```

`status: 0` означает, что HTTP-ответа не было: сеть, таймаут или локальная авторизация.

| Симптом | Причина | Что делать |
|---|---|---|
| `[auth 0] KEYCRM_EMAIL / KEYCRM_PASSWORD are not configured` | пустые логин или пароль | заполнить `.env`, проверить, что файл лежит рядом с `keycrm_client.py` |
| `[auth ...]` на `/auth/login` | неверный email/пароль, 2FA, блокировка | проверить вход в веб-интерфейс, при 2FA завести пароль приложения или использовать API-токен |
| `[internal 401]` один раз и дальше ок | истёк 24-часовой `access_token` | норма: клиент сам делает refresh, при неудаче логинится заново |
| `[official 401]` | токен отозван или перевыпущен | клиент сбрасывает токен и ищет новый через `/config/api-client`. Если не помогло - проверить Настройки -> API в KeyCRM |
| `[auth 0] api_token not found in /config/api-client` | в аккаунте нет API-клиента | создать API-ключ в настройках KeyCRM или задать `KEYCRM_API_TOKEN` |
| `[internal 429]` / `[official 429]` | превышен лимит | клиент ждёт `Retry-After` (максимум 10 с) и повторяет до 3 раз. Дальше - пауза и повторить вручную |
| `network error: ...` | нет сети, VPN, DNS, прокси | проверить `https://your-account.api.keycrm.app` в браузере |
| таймаут около 60 с | тяжёлый список или зависший запрос | уменьшить `limit`, сузить фильтры, повторить |
| `leads action="remove"` вернул `blocked` | предохранитель после инцидента 01.11.2026 | так и должно быть. Карточки удаляются только вручную в интерфейсе |
| `crm_api` вернул `blocked: batch request with column_ids` | предохранитель на опасные batch-запросы | убрать `column_ids` из query или работать через готовый инструмент |
| `orderBy` в query не сортирует | параметр принимается, но работает только на `/stocks`; на `/catalog/products`, `/leads`, `/tasks` молча игнорируется, на `/orders`, `/clients`, `/users`, `/suppliers`, `/stocks/movements`, `/communications/calls`, `/sources`, `/orders/statuses` даёт 500, а `field:asc` ломает везде | сортировать результат в коде |
| удалённый товар ещё несколько секунд в списке | список товаров кратко кешируется | подождать и перечитать |
| внутренний список вернул больше строк, чем просили | внутренний API ждёт `per_page`, а не `limit`; готовые инструменты уже переведены на `per_page`, проблема осталась только в сырых `crm_api`-вызовах | для `crm_api` передавать `per_page` |
| `orders.list` отдаёт пустой список | внутренний `GET /orders` на этом аккаунте пуст | так и задумано: `orders.list` ходит в официальный `/order`. Если и там 0, заказов действительно нет |
| `finance.payments` / `finance.transactions` отвечают 500 | серверная ошибка KeyCRM | читать платежи в интерфейсе. `bills`, `payment_methods`, `currency_rates` работают |
| `settings` или `crm_api GET /config/filter-profiles` отвечают 500 | маршрут требует параметр `list` | передавать `{"list": "leads"}` или не вызывать |
| `delivery.suggest` отвечает 500 | не настроен провайдер адресов | использовать `delivery action="locations"` |
| `delivery warehouses` вернул `'location_ref' is required` | для Новой Почты, Укрпошты и Meest Express отделения ищутся по ref населённого пункта | сначала `locations`, взять `Ref` (НП) или `id` (Укрпошта), потом `warehouses` |
| `tasks.list` пуст | задач в аккаунте нет | не ошибка: список идёт через `/tasks/search` с `filters[tab]` |
| `tasks create` вернул ошибку валидации | неполное тело | передавать `title`, `scheduled_at`, `assigned_to_id` или полное тело через `data` |
| папка `backups/` растёт | каждый `crm_snapshot` пишет новый файл | старые снимки удалять вручную, это локальные файлы |
| `documents preview_pdf` вернул `content_type: text/html` | сервер врёт в заголовке PDF | смотреть на файл: настоящий PDF начинается с `%PDF-1.7` |
| `documents print` / `attach` вернули `templates: 0` | в аккаунте нет шаблонов документов | это норма: использовать `preview` или `preview_pdf` |
| после удаления заказа файлы остались | удаление заказа не чистит вложения | удалять файлы вручную через `files action="delete_file"` |
| `files attach_order` вернул `path or content_base64 is required` | не передано содержимое файла | указать `path` или `content_base64` |
| клиент не находится по телефону через `clients.search` | справочник клиентов аккаунта пуст (`counters.clients = 0`), контакты живут в карточках воронки | искать по карточкам: `contact.phone` в выдаче `leads.list` |
| после `orders.remove` заказ ещё несколько секунд в списке | batch-удаление заказов асинхронное | подождать 2-5 секунд и перечитать |

Лимиты: официальный API - 20 запросов в минуту (по документации KeyCRM), внутренний терпит 120 (`request_limit` в `/config/api-client`). Токены кешируются в памяти процесса, между вызовами инструментов не теряются.

## 11. Где смотреть логи

Сервер работает по stdio: весь лог - это `stderr` процесса, `stdout` занят JSON-RPC.

- Claude Desktop: логи MCP лежат в `%APPDATA%\Claude\logs`, файлы вида `mcp*.log`. Точное имя файла зависит от версии приложения, нужно проверить в своей установке. Там же видно `[keycrm-mcp] tools_domains skipped: ...` или `[keycrm-mcp] tools_files skipped: ...`, если дополнительные инструменты не подгрузились.
- Claude Code: `claude mcp list` для статуса, `claude --debug` для подробного лога, `/mcp` в сессии.
- Ручной запуск, чтобы увидеть ошибку целиком:

```powershell
cd C:\path\to\keycrm-mcp
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe server.py
```

Сервер будет ждать JSON-RPC в stdin. Это нормально: он не CLI, а MCP-сервер.

- Кириллица в консоли Windows отображается кракозябрами при выводе JSON. Это кодировка консоли, не данные: файлы и ответы в UTF-8.

## 12. Файлы проекта

| Файл | Что внутри |
|---|---|
| `server.py` | FastMCP-сервер: 15 основных инструментов, по stdio |
| `tools_domains.py` | 8 доменных инструментов, подключаются из `server.py` автоматически |
| `tools_files.py` | инструмент `files`: вложения заказов, multipart-чанки по 1 МБ, лимит 250 МБ |
| `backups/` | локальные снимки `crm_snapshot`, в git не добавлять |
| `exports/` | локальные файлы: скачанные вложения и PDF из `documents.preview_pdf` |
| `keycrm_client.py` | транспорт: логин, refresh, ретраи 401/429, пагинация, официальный API |
| `endpoints_catalog.py` | загрузка и поиск по каталогу маршрутов |
| `endpoints.json` | 572 внутренних маршрута из SPA-бандла v33.0.10 |
| `crm_cli.py` | CLI для скриптов и отладки без MCP |
| `test_smoke.py` | e2e-проверка через stdio, 92 проверки (с files, documents и audit) |
| `test_domains.py` | проверки доменных инструментов, 90 проверок |
| `test_actions.py` | read-only обход всех action, 83 проверки (78 ok, 5 честных ошибок) |
| `docs/ACTION_MATRIX.md` | матрица action по живому аккаунту, плюс `ACTION_MATRIX.json` |
| `run.cmd` | запуск для Windows |
| `demo/` | реальные ответы сервера (статусы, воронки, отчёт по лидам, `crm_status`) |
| `.env` | доступы, локальный файл |
| `docs/` | QUICKSTART, TOOLS, API_REFERENCE, COOKBOOK, ENDPOINTS_STATUS, INCIDENT |

Дальше: [TOOLS.md](TOOLS.md) - что умеет каждый инструмент, [API_REFERENCE.md](API_REFERENCE.md) - карта 572 маршрутов, [COOKBOOK.md](COOKBOOK.md) - готовые рецепты на Python.
