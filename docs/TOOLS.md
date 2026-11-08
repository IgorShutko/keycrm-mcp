# TOOLS: справочник по инструментам keycrm-mcp

24 инструмента: 15 основных (`server.py`: `crm_status`, `crm_capabilities`, `crm_snapshot`, `crm_endpoints`, `crm_api` + 9 сущностей, отчёт и `audit`), 8 доменных (`tools_domains.py`) и 1 отдельный (`tools_files.py`: `files`). Все описания и параметры сверены с кодом, примеры ответов - реальные ответы сервера на аккаунте `your-account` от 2026-11-01 и 02.11.2026, сокращённые до сути.

Живые проверки: `test_smoke.py` (92), `test_domains.py` (90), `test_actions.py` (83 action, 78 ok, 5 честных ошибок). Матрица по action - в [ACTION_MATRIX.md](ACTION_MATRIX.md), машинный результат - `ACTION_MATRIX.json` рядом.

## Общие правила

**Формат ответа.** Каждый инструмент возвращает JSON-строку:

```json
{"ok": true, "data": ...}
{"ok": false, "error": {"status": 500, "api": "internal", "message": "Server Error", "body": {...}}}
```

`status: 0` и `api: "auth"` - локальная ошибка авторизации, HTTP-ответа не было. Исключения наружу не вылетают никогда.

**Пагинация.** `limit` и `page` есть у списков. `limit` режется сверху до 50 в основных инструментах и доменных списках, `crm_endpoints` - до 200. Ответ списка обычно несёт `meta`: `current_page`, `last_page`, `per_page`, `total`. Внутренний API понимает `per_page`, а не `limit`; готовые инструменты (`leads.list` без фильтров, `clients`, `products`, `conversations`) уже передают `per_page`, поэтому `limit` у них работает. В сырых запросах через `crm_api` передавайте `per_page`, иначе получите дефолтную страницу (15 записей).

**Фильтры.** В основных инструментах (`orders`, `leads`) `filters` - это словарь, который превращается в query-параметры KeyCRM:

```json
{"status_id": [1, 2], "created_between": ["2026-10-01", "2026-11-01"]}
```

превращается в `filter[status_id]=1,2` и `filter[created_between]=2026-10-01,2026-11-01`. Списки соединяются через запятую, `true/false` идут как `1/0`, `null` пропускается.

В доменных инструментах (`finance`, `delivery`, `publications`, `stocks`) `filters` уходят **без** обёртки `filter[...]`, ключи пишутся как есть: `{"filter[warehouse_id]": 1}` или `{"filter[status]": "new"}`.

**Компактные проекции.** Списки возвращаются не целиком, только значимые поля:

| Инструмент | Поля строки |
|---|---|
| `orders.list` | id, status_id, grand_total, payment_status, client_id, manager_id, source_id, created_at, ordered_at, products_total |
| `leads.list` | id, title, status_id, pipeline_id, manager_id, currency_code, products_total, communicate_at, created_at, is_finished, contact.full_name, contact.phone |
| `clients.list` | id, full_name, phone, email, orders_count, orders_sum, manager_id, created_at |
| `products.list` | id, name, sku, quantity, in_reserve, min_price, max_price, category_id, is_archived, has_offers |
| `tasks.list` | id, name, description, status, priority, scheduled_at, assigned_to_id, type, created_at |
| `conversations.list` | id, client_id, contact_id, channel_id, last_message_at, unread_count, status, assignee_id |
| `users.list` | id, full_name, email, role_id, status, is_owner |

Вложенные поля в выдаче `leads.list` остаются плоскими ключами с точкой: `"contact.full_name"`, `"contact.phone"`. Обращаться к ним в Python нужно как `row["contact.phone"]`, а не `row["contact"]["phone"]`.

**Деньги.** В карточках воронки `products_total` приходит в минорных единицах: карточка с суммой 22 500 грн отдаёт `products_total: 22500000`. В каталоге `min_price` и `max_price` - в гривнах (`22500`). Сверяйте поле с полем, не смешивайте.

**Действие.** У 17 инструментов первый параметр - `action` (строка, регистр не важен). Неизвестный action возвращает ошибку `ValueError: unknown action '<...>'` внутри `{"ok": false}`.

---

## 1. crm_status

Проверка связи и сводка аккаунта. Параметров нет. С него начинается любая сессия.

Что возвращает: домен, обе базы API, профиль владельца токена, статус официального канала (`channels.official = "ok"`), API-клиент с `request_limit`, счётчики `orders`, `cards`, `clients`, `products`, `users`.

```json
{}
```

Реальный ответ (2026-11-01):

```json
{
 "ok": true,
 "data": {
  "domain": "your-account",
  "internal_api": "https://your-account.api.keycrm.app",
  "official_api": "https://openapi.keycrm.app/v1",
  "profile": {"id": 4, "full_name": "Owner Name", "email": "owner@example.com", "role_id": 1, "is_owner": true, "status": "active"},
  "channels": {"official": "ok"},
  "official_sample_users": 1,
  "api_client": {"id": "00000000-0000-0000-0000-000000000000", "name": "your-account-default-app", "request_limit": 120, "is_active": 1},
  "counters": {"orders": 0, "cards": 32, "clients": 0, "products": 3, "users": 3}
 }
}
```

Особенности:

- Счётчик `orders` считается через официальный API (внутренний `GET /orders` на этом аккаунте пуст), `cards`, `clients`, `products` и `users` - через внутренний.
- Если официальный канал сломан, в `channels.official` будет строка `error: ...`, а не исключение: остальные счётчики придут.
- Счётчик карточек на 2026-11-01 равен 32; в `demo/status.json` лежит более старый снимок (59). Данные аккаунта меняются, это нормально.

---

## 2. crm_capabilities

Что аккаунт умеет прямо сейчас. Параметров нет. Второй обязательный вызов после `crm_status`.

Возвращает: `account`, `root_is_active`, `modules` (какие модули включены), `plan_general` (таймзона, страна, компания), `api_request_limit`, `api_client_name` и `known_issues` - список известных сломанных или опасных маршрутов.

```json
{}
```

Реальный ответ (2026-11-01, сокращённо):

```json
{
 "ok": true,
 "data": {
  "account": "your-account",
  "root_is_active": false,
  "modules": {
   "orders": {"is_active": false},
   "leads": {"is_active": true},
   "conversations": {"is_active": false},
   "products": {"present": true},
   "manufacturing": {"is_active": false},
   "companies": {"is_active": false}
  },
  "plan_general": {"timezone": "Europe/Kiev", "country": "ua", "company_name": "your-account"},
  "api_request_limit": 120,
  "api_client_name": "your-account-default-app",
  "known_issues": [
   "tasks create works with body name/priority/type/description/status/scheduled_at/assigned_to_id/period/settings; complete = PUT /tasks/{id} {\"id\", \"status\":\"done\"}",
   "DANGER: POST /batch/leads/execute/remove?... deletes ALL cards of the selected status columns when the id filter is not matched exactly. Card removal is blocked in this MCP server, delete cards in the KeyCRM UI only",
   "GET /orders on the internal API returns an empty list, orders are read via official /order",
   "internal list endpoints ignore 'limit' and use per_page (max 50)",
   "orderBy is accepted but mostly ignored: only /stocks really sorts, /orders, /clients, /users and the field:asc format return 500. Sort in code, not in the API",
   "product list is briefly cached, a deleted product can appear for a few seconds"
  ]
 }
}
```

Особенности:

- Ходит в `GET /config/settings/` (со слешем на конце), это другой путь, чем у инструмента `settings` (`/config/settings`). Оба работают.
- `known_issues` - методичка для модели: если маршрут в списке, не тратить на него попытки. Полный текст предупреждения об удалении карточек - в [INCIDENT.md](INCIDENT.md).
- Если модуль выключен (`orders`, `conversations`), это не значит, что данные недоступны: чтение может работать, просто раздел не активен в аккаунте.

## 3. crm_snapshot

Локальный снимок аккаунта в JSON. Вызывать перед любой рискованной операцией с записью. В CRM ничего не пишет, только читает и сохраняет файл.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `folder` | str | `keycrm-mcp/backups` | куда сохранить файл |

Что попадает в снимок: `cards` (внутренний `/leads`, до 2000), `orders` (официальный `/order`, до 500), `products`, `clients`, `users`, `sources`, `pipelines`, `pipeline_statuses`, `order_statuses`, `settings`, плюс `created_at`, `domain` и `counts`.

```json
{}
```

Ответ: `{"ok": true, "data": {"file": "<путь к файлу>", "bytes": <размер файла>, "counts": {"": 42, "orders": 0}}}`. Файл называется `crm_snapshot_YYYYmmdd_HHMMSS.json` и лежит в `keykrm-mcp/backups/`, если папка не задана.

Зачем: именно по такому снимку канбана 01.11.2026 восстановили 26 удалённых карточек. Снимок не заменяет бэкап KeyCRM: вложения файлов и история изменений в него не попадают. Папку `backups/` не коммитить.

**Секреты маскируются.** Перед записью файла `crm_snapshot` рекурсивно заменяет значения ключей, в имени которых есть `token`, `password`, `secret`, `api_key`, `api-key`, `auth_key`, `auth-key`, `authorization`, `session`, `cookie`, на `"***"`. Проверено: ни одного JWT в файле. При этом телефоны, суммы и переписка остаются как есть: снимок всё равно чувствительный, его нельзя выкладывать наружу.

## 4. orders

Заказы. `list` ходит в официальный API, остальное - во внутренний.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `order_id` | int | - | get, update, set_status, add_product, update_product, remove_product, add_tag, remove_tag |
| `limit` | int | 20 | list, максимум 50 |
| `page` | int | 1 | list |
| `filters` | dict | - | list, в формате KeyCRM |
| `include` | str | - | list, что подтянуть в официальном ответе |
| `data` | dict | - | create, update, add_product, update_product |
| `product_id` | int | - | update_product, remove_product |
| `tag_id` | int | - | add_tag, remove_tag |
| `status_id` | int | - | set_status |
| `ids` | list[int] | - | remove |
| `include_disabled` | bool | false | statuses, tags |

Действия:

| action | Метод и путь | Что делает |
|---|---|---|
| `list` | GET official `/order` | список с фильтрами и пагинацией |
| `get` | GET `/orders/{order_id}` | полный заказ: клиент, товары, оплаты, доставка, теги |
| `create` | POST `/orders` | создать; нужны `source_id`, `buyer` и `products[]` |
| `update` | PUT `/orders/{order_id}` | частичное обновление |
| `set_status` | POST `/orders/{order_id}/status/{status_id}` | сменить статус |
| `add_product` | POST `/orders/{order_id}/products` | добавить товар |
| `update_product` | PUT `/orders/{order_id}/products/{product_id}` | изменить строку заказа |
| `remove_product` | DELETE `/orders/{order_id}/products/{product_id}` | убрать товар |
| `add_tag` | POST `/orders/{order_id}/tags/{tag_id}` | повесить тег |
| `remove_tag` | POST `/orders/{order_id}/tags/{tag_id}/detach` | снять тег |
| `remove` | POST `/batch/orders/execute/remove` | удалить заказы по `ids[]`, асинхронно |
| `statuses` | GET `/orders/statuses` | 19 статусов аккаунта; `include_disabled` покажет скрытые |
| `groups` | GET `/orders/groups` | 6 групп статусов |
| `totals` | GET `/orders/totals` | сводные итоги, на этом аккаунте `[]` |
| `tags` | GET `/orders/tags` | теги заказов, на 2026-11-01 пусто |
| `sources` | GET `/sources` | источники заказов, 9 штук |

Пример: список за 2 дня.

```json
{"action": "list", "limit": 5, "filters": {"created_between": ["2026-10-30", "2026-11-01"]}}
```

Реальный ответ сейчас (заказов в аккаунте нет, `counters.orders = 0`):

```json
{"ok": true, "data": {"orders": [], "meta": {"current_page": 1, "last_page": 1, "per_page": 5, "total": 0}}}
```

Пример: создать заказ.

```json
{
 "action": "create",
 "data": {
  "source_id": 1,
  "buyer": {"full_name": "Иван Петренко", "phone": "+380501112233"},
  "products": [{"name": "Аудит", "price": 22500, "quantity": 1}]
 }
}
```

Пример: статусы (сокращённо, реальные данные).

```json
[
 {"id": 1, "name": "Новый", "alias": "new", "group_id": 1, "is_active": true, "is_closing_order": false},
 {"id": 12, "name": "Выполнен", "alias": "completed", "group_id": 5, "is_active": true, "is_closing_order": true},
 {"id": 19, "name": "Отменен", "alias": "canceled", "group_id": 6, "is_active": true, "is_closing_order": true}
]
```

Ошибки и пометки:

- `list` возвращает пустой список не из-за фильтров: в аккаунте `orders = 0`. Внутренний `GET /orders` тоже пуст, поэтому список идёт через официальный API.
- `remove` ставит задачу в очередь: заказ пропадает из списка через 2-5 секунд.
- `statuses` без `include_disabled` не покажет выключенные статусы; в аккаунте все 19 включены.
- Официальный ответ по `/order` содержит `grand_total`; проверять, в гривнах он или в минорных единицах, нужно на живом заказе. Сейчас заказов нет, поле не подтверждено.

---

## 5. leads

Карточки воронки: лиды, сделки, заявки.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `lead_id` | int | - | get, update, move, complete, add_product, copy |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `filters` | dict | - | list; без фильтров идёт внутренний API, с фильтрами - официальный |
| `include` | str | - | list, get |
| `data` | dict | - | create, update, complete, add_product |
| `status_id` | int | - | move |
| `pipeline_id` | int | - | desk |
| `ids` | list[int] | - | remove |

Действия:

| action | Метод и путь | Что делает |
|---|---|---|
| `list` | GET `/leads` (internal) или official `/pipelines/cards` при наличии `filters` | список карточек |
| `get` | GET `/leads/{lead_id}` | полная карточка: contact, source, products, payments |
| `create` | POST `/leads` | создать; обязательны `status_id`, `communicate_at`, `currency_code` |
| `update` | PUT `/leads/{lead_id}` | частичное обновление |
| `move` | PUT `/leads/{lead_id}` с `{"status_id": N}` | перенос между статусами и воронками |
| `pipelines` | GET `/leads/pipelines?leads=false` + статусы каждой воронки | воронки с их статусами |
| `desk` | GET `/leads/pipelines/desk` или `/desk/{pipeline_id}` | канбан: статусы с карточками |
| `complete` | PUT `/leads/{lead_id}/order` | превратить карточку в заказ |
| `add_product` | POST `/leads/{lead_id}/products` | добавить товар в карточку |
| `copy` | POST `/leads/{lead_id}/copy` | копия карточки |
| `remove` | заблокирован | удаление карточек через API отключено на уровне сервера, см. предупреждение ниже |

Пример: карточки статуса 1, по 2 на страницу.

```json
{"action": "list", "limit": 2, "filters": {"status_id": 1}}
```

Реальный ответ: пусто, в статусе "Новий лід" сейчас нет карточек.

```json
{"ok": true, "data": {"leads": [], "meta": {"current_page": 1, "last_page": 1, "per_page": 2, "total": 0}}}
```

Пример: последние карточки без фильтров.

```json
{"action": "list", "limit": 2}
```

Возвращает ровно 2 строки, реальный ответ:

```json
{
 "leads": [
  {"id": 2, "title": "Тестова картка", "status_id": 8, "pipeline_id": 1, "manager_id": 5, "currency_code": "UAH", "products_total": 22500000, "communicate_at": "2026-10-20T19:27:01.000000Z", "created_at": "2026-10-20T19:12:01.000000Z", "is_finished": true, "contact.full_name": "тест"},
  {"id": 1, "title": "Тестова картка", "status_id": 8, "pipeline_id": 1, "manager_id": 5, "currency_code": "UAH", "products_total": 22500, "communicate_at": "2026-10-20T19:56:51.000000Z", "created_at": "2026-10-20T18:56:51.000000Z", "is_finished": true, "contact.full_name": "Owner Name"}
 ],
 "meta": {"current_page": 1, "last_page": 21, "per_page": 2, "": 42}
}
```

Пример: создать сделку.

```json
{
 "action": "create",
 "data": {
  "title": "Заявка с сайта",
  "pipeline_id": 1,
  "status_id": 1,
  "source_id": 1,
  "communicate_at": "2026-11-10 12:00:00",
  "currency_code": "UAH",
  "contact": {"full_name": "Иван Петренко", "phone": "+380501112299"}
 }
}
```

Пример: воронки (реальный ответ, сокращённо - статусов в воронке 15).

```json
[
 {
  "id": 1,
  "title": "Продажі",
  "lead_type": "lead",
  "statuses": [
   {"id": 1, "title": "Новий лід", "alias": "new", "is_final": false, "position": 0, "leads_count": 0},
   {"id": 4, "title": "Оплачено", "alias": "successful", "is_final": true, "position": 0, "leads_count": 0}
  ]
 }
]
```

Ошибки и пометки:

- `list` без `filters` идёт во внутренний `/leads` и передаёт туда `per_page`, поэтому `limit` работает: `{"limit": 2}` даёт 2 строки и `meta.per_page = 2`.
- `list` с `filters` идёт в официальный `/pipelines/cards`, там фильтры через `filter[...]` и работают корректно.
- `create` на этом аккаунте работает, `move` тоже.
- `products_total` в карточке - минорные единицы. Для 22 500 грн приходит 22 500 000, но есть карточки и с 22500: значения в базе неоднородны, проверяйте конкретную запись.
- `get` принимает `include` (например `"contact,source"`), внутренний API отдаёт больше полей, чем список.

> **ВНИМАНИЕ. `leads action="remove"` заблокирован.** Удаление карточек в KeyCRM работает через `POST /batch/leads/execute/remove?filters[lead_ids]=...&column_ids=...&pipeline_id=...`, и если фильтр по id не совпал точно, сервер удаляет все карточки перечисленных колонок. 01.11.2026 так удалили 26 реальных карточек (восстановлены). Поэтому инструмент возвращает `{"ok": false}` с объяснением, а `crm_api` блокирует этот путь и любые batch-запросы с `column_ids`. Карточки удаляются только вручную в интерфейсе KeyCRM.

---

## 6. clients

Покупатели. На этом аккаунте справочник клиентов пуст (`counters.clients = 0`), рабочие контакты живут внутри карточек воронки.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `client_id` | int | - | get, update, delete, orders, leads |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `search` | str | - | search: имя, телефон или email |
| `data` | dict | - | create, update |

Действия: `list`, `get`, `create` (`full_name` обязателен), `update`, `delete`, `search`, `orders` (история заказов клиента), `leads` (карточки клиента).

```json
{"action": "list", "limit": 5}
```

Сейчас: `{"clients": [], "meta": {"current_page": 1, "last_page": 1, "per_page": 5, "total": 0}}`.

Пример создания:

```json
{"action": "create", "data": {"full_name": "Иван Петренко", "phone": "+380501112233", "email": "ivan@example.com"}}
```

Ошибки и пометки:

- `search` ходит в `GET /clients/search?query=`. На пустом справочнике возвращает пустой список, что выглядит как "клиент не найден". Ищите телефон в карточках воронки: `leads.list` отдаёт `contact.phone`.
- Телефон в интерфейсе KeyCRM хранит в `profiles`, а не в поле `phone`. Если `list` отдаёт клиента без телефона, смотреть `get`.
- `orders` и `leads` на пустом справочнике вернут пустые структуры.

---

## 7. products

Каталог товаров со складскими остатками.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `product_id` | int | - | get, update, delete |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `search` | str | - | list: поиск по названию, передаётся в API |
| `data` | dict | - | create (`name` обязателен), update |

Действия: `list`, `get`, `create`, `update`, `delete`, `categories` (дерево), `warehouses` (склады из `/stocks/warehouses`).

Пример:

```json
{"action": "list", "limit": 3, "search": "Старт"}
```

Реальный ответ (3 товара, полный список аккаунта):

```json
{
 "ok": true,
 "data": {
  "products": [
   {"id": 3, "name": "Старт", "sku": "TP-START", "quantity": 0, "in_reserve": 0, "min_price": 22500, "max_price": 22500, "is_archived": false, "has_offers": false},
   {"id": 2, "name": "Легкий пакет", "sku": "TP-LIGHT", "quantity": 0, "in_reserve": 0, "min_price": 10000, "max_price": 10000, "is_archived": false, "has_offers": false},
   {"id": 1, "name": "Аудит", "sku": "TP-AUDIT", "quantity": 0, "in_reserve": 0, "min_price": 0, "max_price": 0, "is_archived": false, "has_offers": false}
  ],
  "meta": {"current_page": 1, "last_page": 1, "per_page": 3, "total": 3}
 }
}
```

Склады:

```json
[{"id": 1, "name": "Основний", "is_active": true, "is_default": true}]
```

Ошибки и пометки:

- В docstring упомянут action `search`, но в коде отдельной ветки нет: `search` работает как параметр `list`, а `{"action": "search"}` вернёт `unknown action`.
- `quantity` и `in_reserve` - штуки; `min_price` и `max_price` - гривны (22500 = 22 500 грн). Для товаров с `has_offers: true` цены живут в офферах, отдельного списка офферов в этом инструменте нет, только через `crm_api`.
- `categories` возвращает дерево из `/catalog/categories/tree`; на этом аккаунте категорий нет.
- Список товаров ненадолго кешируется: удалённый товар может ещё несколько секунд появляться в выдаче. Не считать это ошибкой.

---

## 8. tasks

Задачи. Создание работает: `POST /tasks` принимает полное тело, инструмент собирает его сам из удобных параметров.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `task_id` | int | - | get, update, complete, delete |
| `limit` | int | 20 | list, максимум 50 |
| `page` | int | 1 | list |
| `tab` | str | `"actual"` | list: `actual` (открытые) или `closed` |
| `mine` | bool | true | list: только свои задачи |
| `entity_type` | str | - | for_entity: `lead`, `order`, `client`, `task` |
| `entity_id` | int | - | for_entity |
| `data` | dict | - | create (полное тело), update |
| `title` | str | - | create: уходит в `name` |
| `description` | str | - | create |
| `assigned_to_id` | int | - | create; по умолчанию владелец токена |
| `scheduled_at` | str | - | create; ISO, по умолчанию завтра |
| `priority` | int | 1 | create |
| `task_type` | str | `"task"` | create, уходит в `type` |

Действия: `list`, `get`, `for_entity`, `expired_count`, `create`, `update`, `complete`, `delete`.

Пример списка:

```json
{"action": "list", "limit": 5, "tab": "actual", "mine": true}
```

Пример создания:

```json
{
 "action": "create",
 "title": "Позвонить по заявке",
 "description": "Уточнить бюджет и сроки",
 "assigned_to_id": 4,
 "scheduled_at": "2026-11-05T10:00:00.000Z",
 "priority": 1
}
```

Сервер собирает такое тело:

```json
{
 "name": "Позвонить по заявке",
 "priority": 1,
 "type": "task",
 "description": "Уточнить бюджет и сроки",
 "status": "open",
 "scheduled_at": "2026-11-05T10:00:00.000Z",
 "assigned_to_id": 4,
 "tasked": null,
 "attachments": [],
 "period": {"time": 0, "duration": "days"},
 "checklist": [],
 "settings": {"allow_editing": false}
}
```

Если параметров мало или нужны нестандартные поля, передайте готовое тело через `data` - оно уйдёт в API как есть.

Завершение и удаление:

```json
{"action": "complete", "task_id": 123}
{"action": "delete", "task_id": 123}
```

`complete` делает `PUT /tasks/{id}` с телом `{"id": <id>, "status": "done"}`. `delete` делает `DELETE /tasks/{id}`, это безопасное удаление по id.

Ответ `list` (сокращённо, проекция `TASKS_COMPACT`): `tasks` плюс `meta`. Поля строки: id, name, description, status, priority, scheduled_at, assigned_to_id, type, created_at. На 2026-11-01 список пуст (`total: 0`), `expired_count` тоже 0: тестовые задачи убрали.

---

## 9. conversations

Переписки в каналах (Viber, Telegram, WhatsApp, чат на сайте).

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | всегда |
| `conversation_id` | int | - | get, messages, send |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `data` | dict | - | send |

Действия: `list`, `get`, `messages`, `unread`, `send` (POST `/conversations/{id}/messages`).

```json
{"action": "list", "limit": 5}
```

Сейчас переписок нет:

```json
{"conversations": [], "meta": {"current_page": 1, "last_page": 1, "per_page": 5, "total": 0}}
```

`send` реально отправляет сообщение клиенту в канал. Нужен текст в `data`, формат тела смотреть через `crm_api` на существующем канале: подтверждённого примера на этом аккаунте нет. Отправка не проверялась, сначала проверяйте на себе.

---

## 10. audit

История изменений аккаунта (`/auditing`). Только чтение.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `action` | str | `"list"` | `list`, `by_entity`, `by_manager` |
| `limit` | int | 20 | list, максимум 50 |
| `page` | int | 1 | list |
| `entity_id` | int | - | by_entity |
| `entity_type` | str | `"order"` | by_entity: `order`, `lead`, `task`, `manufacturing` |
| `manager_id` | int | - | by_manager |

`list` идёт в `GET /auditing/all` с `per_page` и `page`, отдаёт компактные записи и `meta`.

```json
{"action": "list", "limit": 5}
```

Реальный ответ 02.11.2026 (сокращённо, всего 1139 записей):

```json
{
 "ok": true,
 "data": {
  "items": [
   {
    "_id": "6ae7b9015f1d11ff740e53ba",
    "action": "model_was_deleted",
    "model_type": "client",
    "model_ids": [31],
    "created_at": "2026-11-01T22:11:13.562000Z",
    "initiator": {"type": "manager", "id": 4, "label": "Owner Name"},
    "subject": {"type": "client", "id": 31, "label": "MCP TEST CLIENT"}
   }
  ],
  "meta": {"current_page": 1, "last_page": 228, "per_page": 5, "total": 1139}
 }
}
```

Поля записи: `_id` (id события), `action` (`model_was_created`, `model_was_deleted`, `attribute_was_updated` и т.п.), `model_type` (`order`, `lead`, `task`, `client`, ...), `model_ids`, `created_at` в UTC, `initiator` (`{type, id, label}`), `subject` (`{type, id, label}`).

`by_entity` идёт в `GET /auditing/{entity_type}/{entity_id}` и возвращает сырой пагинированный ответ внутреннего API, без компактной проекции: в строках есть `context.changes` с парами `old`/`new`.

```json
{"action": "by_entity", "entity_type": "order", "entity_id": 1}
```

Реальный ответ: 6 записей по заказу 1, последняя - удаление. Строки содержат изменения атрибутов (`source_id`, `status_id`, `payment_status`, товары и т.п.).

`by_manager` идёт в `GET /auditing/manager/{manager_id}`, тоже сырой пагинированный ответ.

```json
{"action": "by_manager", "manager_id": 5}
```

Реальный ответ: 416 записей, 15 на страницу, 28 страниц. В строках `attribute_was_updated` с `context.changes[].attribute` и `values.old/new`.

Пометки:

- `list` отдаёт только компактные поля, без `context.changes`. За деталями конкретного события идите в `by_entity` или в `crm_api GET /auditing/all`.
- `by_manager` и `by_entity` не режут ответ и не поднимают `limit`: это сырые эндпоинты, объём зависит от истории.
- Событий много: 1139 по аккаунту и 416 по одному менеджеру. Фильтров по дате у инструмента нет, листайте `page` или фильтруйте результат в коде по `created_at`.

## 11. users

Команда и роли. Только чтение.

| action | Путь | Что возвращает |
|---|---|---|
| `list` | GET `/users` | 3 участника |
| `roles` | GET `/users/roles` | 7 ролей |
| `permissions` | GET `/users/permissions` | справочник прав |

```json
{"action": "list"}
```

Реальный ответ:

```json
[
 {"id": 2, "full_name": "keyCRM Bot", "email": "bot@blueprint_for_new_tenants.keycrm.app", "role_id": 1, "status": "active", "is_owner": false},
 {"id": 4, "full_name": "Owner Name", "email": "owner@example.com", "role_id": 1, "status": "active", "is_owner": true},
 {"id": 5, "full_name": "Manager Name", "role_id": 2, "status": "active", "is_owner": false}
]
```

У третьего пользователя поля `email` нет: проекция выкидывает отсутствующие ключи.

`roles` режет до `id` и `name` (поля `permissions_count` в живом ответе нет, поэтому его в строке не будет).

---

## 12. settings

Срез `GET /config/settings`.

| Параметр | Тип | По умолчанию | Когда нужен |
|---|---|---|---|
| `section` | str | `""` | имя раздела; пусто - весь объект |

Реальные ключи аккаунта (20): `ai`, `allowed_fields`, `companies`, `conversations`, `currencies`, `general`, `has_payment_gateways`, `is_active`, `leads`, `limits`, `manufacturing`, `notifications`, `order_fields`, `orders`, `products`, `schedule_delete_at`, `shipment`, `sources_count`, `suppliers`, `tables`.

```json
{"section": "general"}
```

Реальный ответ:

```json
{
 "ok": true,
 "data": {
  "general": {
   "timezone": "Europe/Kiev",
   "country": "ua",
   "company_name": "your-account",
   "company_picture": {"thumbnail": null},
   "working_hours": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "startTime": "10:00", "endTime": "17:00"}],
   "enable_notifications": false
  }
 }
}
```

Особенности:

- Без `section` возвращается весь объект, он большой. В модель лучше отдавать срез.
- Неизвестный раздел вернёт `{"section": null}` без ошибки.
- `order_fields` и `allowed_fields` - самые тяжёлые разделы.

---

## 13. report

Агрегированный отчёт. Пять `kind`: `sales` и `leads` считают за период, `funnel`, `managers` и `stale` дают живой срез текущего состояния и даты игнорируют.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `kind` | str | `"sales"` | `"sales"` (заказы), `"leads"` (карточки за период), `"funnel"` (живая воронка), `"managers"` (нагрузка по менеджерам), `"stale"` (зависшие карточки) |
| `date_from` | str | сегодня минус 30 дней | начало периода, только для sales и leads |
| `date_to` | str | сегодня | конец периода, только для sales и leads |
| `max_items` | int | 500 | предел строк, максимум 500, для sales и leads |
| `group_by` | str | `"status"` | для sales: `status`, `manager`, `payment`; для leads: `status`, `manager`, `pipeline` |
| `days` | int | 7 | только для stale: порог простоя в днях, минимум 1 |

`kind="sales"` считает по официальным заказам: `orders`, `revenue` (сумма `grand_total`), `avg_check`, `buckets` с `label`, `count`, `sum`.

`kind="leads"` считает по карточкам официального `/pipelines/cards`: `cards`, `products_total_sum`, `finished`, `active`, `buckets`.

`kind="funnel"` строит живую воронку без периода: карточки по каждому статусу каждой воронки, доля закрытых, конверсия в процентах. Данные берутся с канбана (`/leads/pipelines` + `/leads/statuses/{id}` + официальный `/pipelines/cards`), `group_by` игнорируется.

```json
{"kind": "funnel"}
```

Реальный ответ на 2026-11-01 (сокращённо, статусов в воронке 15):

```json
{
 "ok": true,
 "data": {
  "kind": "funnel",
  "": 42,
  "pipelines": [
   {
    "pipeline_id": 1,
    "pipeline": "Продажі",
    "": 42,
    "closed": 32,
    "active": 26,
    "conversion_percent": 55.2,
    "statuses": [
     {"status_id": 1, "title": "Новий лід", "is_final": false, "cards": 11, "share_percent": 19.0},
     {"status_id": 8, "title": "Не лід: спам, тест, дубль", "is_final": true, "cards": 17, "share_percent": 29.3}
    ]
   }
  ]
 }
}
```

Конверсия здесь считается как доля закрытых карточек (`is_final`) от всех карточек воронки. Это не конверсия продаж: в закрытые попадают и отказы.

`kind="managers"` показывает нагрузку по менеджерам: сколько карточек у каждого, сколько закрыто и активно, сумма `products_total`, процент закрытых. Читает живые карточки внутренним `/leads` (до 2000), финальные статусы определяет по `/leads/statuses/{id}`, сортирует по числу карточек. Период не используется.

```json
{"kind": "managers"}
```

Реальный ответ на 2026-11-01:

```json
{
 "ok": true,
 "data": {
  "kind": "managers",
  "": 42,
  "managers": [
   {
    "manager_id": 5,
    "name": "Manager Name",
    "": 42,
    "closed": 32,
    "active": 26,
    "products_total": 22545000.0,
    "conversion_percent": 55.2
   }
  ]
 }
}
```

`kind="stale"` ищет активные карточки, которые не обновлялись дольше `days` дней (по умолчанию 7). Берёт `updated_at`, при его отсутствии `status_changed_at` или `created_at`, финальные статусы пропускает, сортирует по `days_stale` по убыванию. Период не используется.

```json
{"kind": "stale", "days": 7}
```

Реальный ответ на 2026-11-01:

```json
{"ok": true, "data": {"kind": "stale", "days": 7, "cards": 0, "stale_cards": []}}
```

Пусто не потому, что механика сломана: после восстановления карточек 01.11.2026 у всех стоит свежий `updated_at`. С `days: 30` ответ тоже пустой.

Формат строки `stale_cards`, когда они появятся:

```json
{"id": 61, "title": "Заявка с сайта", "status_id": 1, "manager_id": 5, "updated_at": "2026-10-20T19:12:01.000000Z", "days_stale": 12}
```

```json
{"kind": "leads", "date_from": "2026-10-01", "date_to": "2026-11-01", "group_by": "status"}
```

Реальный ответ из `demo/report_leads.json` (сокращённо, аккаунт на 2026-11-01):

```json
{
 "ok": true,
 "data": {
  "kind": "leads",
  "period": {"from": "2026-10-01", "to": "2026-11-01"},
  "cards": 54,
  "products_total_sum": 22545000.0,
  "finished": 32,
  "active": 22,
  "group_by": "status",
  "buckets": {
   "1": {"label": "Новий лід", "count": 7, "sum": 0.0},
   "8": {"label": "Не лід: спам, тест, дубль", "count": 17, "sum": 22545000.0}
  },
  "truncated": false
 }
}
```

Сейчас по продажам (заказов нет):

```json
{"ok": true, "data": {"kind": "sales", "period": {"from": "2026-10-02", "to": "2026-11-01"}, "orders": 0, "revenue": 0, "avg_check": 0, "group_by": "status", "buckets": {}, "truncated": false}}
```

Ошибки и пометки:

- `max_items` больше 500 режется до 500. Флаг `truncated: true` означает, что данных больше, чем попало в отчёт.
- `kind="funnel"` игнорирует `date_from`, `date_to`, `group_by` и `max_items` работает только как предел числа карточек, а не периода. Это срез текущего состояния, а не отчёт за период.
- `kind="managers"` и `kind="stale"` тоже живой срез: `date_from`, `date_to`, `group_by`, `max_items` на них не влияют. `managers` читает до 2000 карточек внутренним `/leads`, `stale` тоже смотрит живые карточки и параметр `days`.
- `days` меньше 1 поднимается до 1. Дробное значение приводится к целому.
- `managers` возвращает `products_total` в минорных единицах (22 545 000 = 225 450 грн) и `conversion_percent` как долю закрытых, а не оплаченных.
- Суммы берутся как есть из API, без пересчёта единиц: `products_total_sum` в минорных единицах (22 545 000 = 225 450 грн по карточкам). `revenue` по заказам на нулевой выборке не проверить, нужно проверить на первом живом заказе.
- Названия статусов и менеджеров подтягиваются внутренним API; если справочник недоступен, в `label` будет `status 8` или `manager 5`.

---

## 14. crm_api

Сырой запрос в любой маршрут внутреннего или официального API. Аварийный выход, когда готового инструмента нет.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `method` | str | `"GET"` | GET/POST/PUT/PATCH/DELETE, регистр не важен |
| `path` | str | `"/auth/profile"` | путь от корня, ведущий `/` добавляется сам |
| `query` | dict | - | query-параметры как есть, для официального API ключи вида `filter[status_id]` |
| `body` | dict | - | JSON-тело для POST/PUT/PATCH |
| `api` | str | `"internal"` | `internal` или `official` |

```json
{"method": "GET", "path": "/orders/statuses", "api": "internal"}
{"method": "GET", "path": "/order", "query": {"limit": 5, "filter[status_id]": 1}, "api": "official"}
```

Ответ - полный сырой JSON API, без компактной проекции. Официальный лимит 20 запросов в минуту, внутренний терпит 120.

Перед вызовом найдите маршрут через `crm_endpoints`, иначе легко получить 404. Для записи сначала проверьте метод и тело на тестовом объекте: `crm_api` не валидирует данные и не убирает за собой.

**Про `orderBy`.** Параметр принимается, но сортирует только `/stocks`. На `/catalog/products`, `/leads`, `/tasks` он молча игнорируется: `asc` и `desc` дают одинаковый дефолтный порядок. На `/orders`, `/clients`, `/users`, `/suppliers`, `/stocks/movements`, `/communications/calls`, `/sources`, `/orders/statuses` любой `orderBy` даёт 500. Формат `field:asc` ломает везде. Сортировать результат в коде.

Встроенные предохранители (после инцидента 01.11.2026):

- путь `/batch/leads/execute/remove` блокируется целиком, независимо от метода и параметров;
- любой `/batch/...` запрос с `column_ids` в `query` блокируется: такой запрос может задеть все карточки выбранных колонок;
- блокировка возвращается как `{"ok": false, "error": {"message": "blocked: ..."}}`, запрос в KeyCRM не уходит.

Удаление карточек воронки через `crm_api` невозможно по задумке. Остальные batch-операции (статусы, теги, менеджеры заказов) доступны, но проверяйте их сначала на одном объекте.

---

## 15. crm_endpoints

Поиск по каталогу 572 внутренних маршрутов из SPA-бандла v33.0.10. Только чтение, в сеть не ходит.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `query` | str | `""` | подстрока в пути или имени клиентского метода, регистр не важен |
| `group` | str | `""` | группа = первый сегмент пути, например `finance` |
| `limit` | int | 40 | сколько вернуть, максимум 200 |

```json
{"query": "tags", "limit": 10}
```

Реальный ответ (сокращённо):

```json
{
 "ok": true,
 "data": {
  "count": 2,
  "endpoints": [
   {"name": "ordersTagsIndex", "method": "GET", "path": "/orders/tags", "group": "orders"},
   {"name": "ordersTagsStore", "method": "POST", "path": "/orders/tags", "group": "orders"}
  ]
 }
}
```

Полная карта групп и маршрутов - в [API_REFERENCE.md](API_REFERENCE.md).

---

## 16. finance

Финансы. Только чтение: инструмент принципиально не создаёт и не двигает деньги.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"bills"` | см. таблицу |
| `limit` | int | 20 | списки, максимум 50 |
| `page` | int | 1 | списки |
| `filters` | dict | - | уходят как есть, без `filter[...]` |
| `currency` | str | - | только для `rates_common`, например `"USD,UAH"` |

Действия: `bills` (он же `accounts`), `payments`, `payment_config`, `expense_types`, `payment_methods`, `payment_gateways`, `currency_rates`, `rates_common`, `fiscals`, `transactions`, `transactions_config`, `transactions_unlinked`, `billing`, `billing_invoices`, `billing_payments`.

```json
{"action": "bills"}
```

Реальный ответ (счетов нет):

```json
{"ok": true, "data": {"bills": [], "meta": {}}}
```

Пометки:

- `payments` и `transactions` на этом аккаунте отвечают 500 на стороне KeyCRM. Инструмент вернёт `{"ok": false, "error": {"status": 500, ...}}`, это не баг MCP.
- `billing` - баланс аккаунта и тариф, `billing_invoices` / `billing_payments` - счета и списания.
- `currency_rates` - таблица курсов, `rates_common` - общие курсы; `currency="USD,UAH"` оставит только запрошенные коды и покажет `missing` для отсутствующих.

---

## 17. delivery

Доставка: подключённые службы, центры упаковки, шаблоны, поиск отделений, расчёт и печать накладной. Отправку не создаёт.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"services"` | см. таблицу |
| `service` | str | - | `novaposhta`, `novaposhta_international`, `ukrposhta`, `meest_express`, `rozetka`, `rozetka_delivery`, `dhl_express`, `fedex`, `ups` |
| `query` | str | - | город/улица для `locations`, `streets`, `suggest`; для `warehouses` у Rozetka Delivery |
| `location_ref` | str | - | ref населённого пункта из `locations`: у Новой Почты поле `Ref` (uuid), у Укрпошты `id` (число) |
| `order_id` | int | - | для `price` и `print` |
| `limit` | int | 20 | списки |
| `page` | int | 1 | списки |
| `filters` | dict | - | как есть |
| `data` | dict | - | тело для `price` |

| action | Что нужно | Что делает |
|---|---|---|
| `services` | - | подключённые службы, на аккаунте пусто |
| `prep_centers` | `limit`, `page`, `filters` | центры упаковки |
| `prep_centers_active` | - | активные центры |
| `shipment_templates` | - | шаблоны накладных |
| `locations` | `service` + `query` | города и населённые пункты |
| `warehouses` | `service` + `location_ref` (НП, НП International, Укрпошта, Meest Express) или `query` (Rozetka Delivery) | отделения и склады |
| `streets` | только `novaposhta`: `query` + `location_ref` | улицы |
| `suggest` | `query` | подсказки адресов; на этом тенанте 500, использовать `locations` |
| `price` | `service` + `order_id` + `data` | расчёт стоимости, сухой прогон |
| `print` | `service` + `order_id` | накладная, возвращается превью текста |

```json
{"action": "services"}
{"action": "locations", "service": "novaposhta", "query": "Київ"}
{"action": "warehouses", "service": "novaposhta", "location_ref": "e718a680-4b33-11e4-ab6d-005056801329"}
{"action": "streets", "service": "novaposhta", "query": "Хрещатик", "location_ref": "e718a680-4b33-11e4-ab6d-005056801329"}
```

Реальный ответ по службам (не подключены):

```json
{"ok": true, "data": {"services": [], "meta": {}}}
```

Реальные цифры справочников 02.11.2026 (запрос `query=Київ`):

| Сервис | `locations` | `warehouses` | Чем связывать |
|---|---|---|---|
| `novaposhta` | 250 записей | 100 | `Ref` из `locations` -> `location_ref` |
| `ukrposhta` | 10 записей | 500 | `id` из `locations` -> `location_ref` |
| `rozetka_delivery` | 15 записей | 100 | без `location_ref`, `warehouses` берёт `query` |

Пример записи `locations` Новой Почты:

```json
{"Ref": "e718a680-4b33-11e4-ab6d-005056801329", "Present": "м. Київ, Київська обл.", "MainDescription": "Київ", "Area": "Київська", "Region": "", "SettlementTypeCode": "місто"}
```

Пример записи `warehouses` Новой Почты по этому `Ref`:

```json
{"Ref": "1ec09d88-e1c2-11e3-8c4a-0050568002cf", "Description": "Відділення №1: вул. ...", "ShortAddress": "Київ, вул. ...", "Number": "1", "CityRef": "...", "TypeOfWarehouse": "..."}
```

Улицы Новой Почты (`streets`) отдают `SettlementStreetRef`, `SettlementStreetDescription`, `StreetsTypeDescription`, `SettlementRef`, `Present`. На `query=Хрещатик` с тем же `location_ref` пришло 2 записи.

Укрпошта: в `locations` поля `id`, `name`, `type`, `district_name`, `region_name`, `present`; в `warehouses` - `id`, `postcode`, `street`, `details`, `city_id`, `name`. У `rozetka_delivery` в `locations` uuid и `code_katottg`, в `warehouses` - `id`, `public_name`, координаты, флаги выдачи.

Ошибки и пометки:

- `warehouses` для Новой Почты, НП International, Укрпошты и Meest Express без `location_ref` возвращает `ValueError: 'location_ref' is required for this action`. Сначала `locations`, потом `warehouses`.
- `streets` есть только у `novaposhta`. У `ukrposhta` и `meest_express` доступны `warehouse` и `location`, у `rozetka_delivery` - `warehouse` и `location`. Неверная комбинация даёт `ValueError` с перечнем допустимых служб.
- `suggest` отвечает 500 (провайдер адресов не настроен). Для поиска города использовать `locations`.
- `price` - сухой прогон: считает стоимость, накладную не создаёт.
- `print` возвращает обрезанный текст документа (первые символы), бинарный PDF в модель не отдаётся.

---

## 18. publications

Публикации каталога на маркетплейсах.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | `list` или `variations` |
| `publication_id` | int | - | для `variations` |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `filters` | dict | - | как есть |

```json
{"action": "list"}
```

Сейчас маркетплейсы не подключены:

```json
{"ok": true, "data": {"publications": [], "meta": {"current_page": 1, "last_page": 1, "per_page": 15, "total": 0}}}
```

Синхронизация и загрузка публикаций намеренно не вынесены в инструмент: это вытолкнуло бы товары на живой маркетплейс. Если очень нужно - через `crm_api`, но осторожно.

---

## 19. stocks

Склад: остатки по офферам, движения, инвентаризации, статистика.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | см. таблицу |
| `offer_id` | int | - | для `history` |
| `movement_id` | int | - | для `movement`, `inventories` |
| `search` | str | - | только для `list` |
| `limit` | int | 20 | списки |
| `page` | int | 1 | списки |
| `filters` | dict | - | как есть, например `{"filter[warehouse_id]": 1}` |

Действия: `list`, `movements`, `movement`, `inventories`, `warehouses`, `stat`, `filters`, `history`.

```json
{"action": "stat"}
```

Реальный ответ:

```json
{"ok": true, "data": {"quantity": {"positive": "0.000", "negative": "0.000"}, "purchased_price": {"positive": "0.0000000000", "negative": "0.0000000000"}, "price": {"positive": "0.0000000000", "negative": "0.0000000000"}}}
```

`warehouses` в этом инструменте только читает; запись складов - через `crm_api` (`POST /stocks/warehouses`).

---

## 20. comments

Комментарии к объектам CRM. Единственный доменный инструмент, который пишет по делу (комментарии безвредны).

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | `list`, `add`, `edit`, `delete` |
| `entity_type` | str | `"lead"` | `lead`, `order`, `client`, `deal` |
| `entity_id` | int | - | id объекта, для list и add |
| `comment_id` | int | - | для edit и delete |
| `message` | str | - | текст комментария |
| `tone` | str | `"normal"` | тон, по умолчанию normal |
| `limit` | int | 20 | list |
| `page` | int | 1 | list |
| `data` | dict | - | полное тело, если нужны нестандартные поля |

```json
{"action": "list", "entity_type": "lead", "entity_id": 4, "limit": 10}
```

```json
{"action": "add", "entity_type": "lead", "entity_id": 4, "message": "Клиент просил КП до пятницы"}
```

Пометки: `delete` ставит мягкий флаг удаления, строка остаётся в базе. Проверенного ответа на добавление в этой сессии нет: перед массовым использованием проверьте на одной карточке.

---

## 21. custom_fields

Кастомные поля: определения и значения.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | `list`, `field`, `values` |
| `model` | str | - | `lead`, `order`, `client` |
| `entity_id` | int | - | для `values` вместе с `model` |
| `field_id` | int | - | для `field` |

```json
{"action": "list", "model": "lead"}
```

Реальный ответ (12 полей, сокращённо):

```json
[
 {"id": 1, "name": "Сегмент", "uuid": "LD_1001", "model": "lead", "type": "select", "required": true, "position": 1},
 {"id": 9, "name": "Середній чек, грн", "uuid": "LD_1009", "model": "lead", "type": "number", "required": false, "position": 9}
]
```

`values` требует `entity_id` и `model`: `{"action": "values", "model": "lead", "entity_id": 4}`. Порядок в пути нестандартный: `/config/custom-fields/{entity_id}/{model}/values`, инструмент его соблюдает.

---

## 22. documents

Печатные документы: шаблоны, превью, печать. В аккаунте 0 шаблонов, поэтому рабочий путь только `preview` и `preview_pdf`: сервер рендерит Twig-шаблон на демо-данных и отдаёт готовый HTML или PDF.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | `list`, `by_scope`, `export_template`, `export_formats`, `print_layouts`, `preview`, `preview_pdf`, `print`, `attach` |
| `scope` | str | - | `order`, `lead`, `client` |
| `template_id` | int | - | для `print` и `attach`; сейчас бесполезен, шаблонов нет |
| `model_id` | int | - | id заказа/лида/клиента для `print` и `attach` |
| `data` | dict | - | для preview: `{"type": "...", "structure": "<Twig-строка>"}` |

`type` в `data`: `order`, `lead`, `client`, `delivery`, `warehouse`, `general`. `structure` теперь Twig-строка (раньше можно было передать dict или список, они сериализовались в JSON, сейчас ожидается строка шаблона).

```json
{"action": "list"}
{"action": "by_scope", "scope": "order"}
```

Реальные ответы: шаблонов нет.

```json
{"ok": true, "data": []}
```

Экспортные шаблоны и раскладки печати (это отдельные справочники, не Twig-документы):

```json
{"action": "export_template"}
{"action": "export_formats"}
{"action": "print_layouts"}
```

Реальный ответ `export_template`: один шаблон `default` в формате `xlsx` с 52 колонками (от `product_sku` и `client_name` до `grand_total`, `utm_*` и `product_discount`), у каждой колонки `name`, `position`, `global_position`, `is_active`.

```json
{
 "ok": true,
 "data": [
  {
   "id": 1,
   "title": "default",
   "format": "xlsx",
   "structure": [
    {"name": "product_sku", "position": 0, "global_position": 1, "is_active": true},
    {"name": "grand_total", "position": 20, "global_position": 21, "is_active": true},
    {"name": "product_discount", "position": 51, "global_position": 52, "is_active": true}
   ],
   "status": true
  }
 ]
}
```

Реальный ответ `export_formats`: `{"csv": "csv", "xlsx": "xlsx"}`.

Реальный ответ `print_layouts`: две раскладки, обе `type: table`, `format: A4`, `orientation: portrait`:

```json
[
 {"id": 1, "title": "Плитка (old)", "type": "table", "format": "A4", "print_type": "table"},
 {"id": 2, "title": "Таблица", "type": "table", "format": "A4", "print_type": "table"}
]
```

`export_template`, `export_formats` и `print_layouts` - только чтение справочников. Скачать сам xlsx через инструмент нельзя: это отдельные ручки `/config/export`, `/config/export/formats`, `/config/print`.

Пример рендера HTML:

```json
{
 "action": "preview",
 "data": {
  "type": "order",
  "structure": "<html><body><h1>Order {{ model.id }}</h1><p>Total: {{ model.grand_total }}</p></body></html>"
 }
}
```

Реальный ответ: демо-модель подставила id 1111 и сумму 170.

```json
{"ok": true, "data": {"view": "<html><body><h1>Order 1111</h1><p>Total: 170</p></body></html>"}}
```

Пример PDF:

```json
{
 "action": "preview_pdf",
 "data": {
  "type": "order",
  "structure": "<html><body><h1>Doc {{ model.id }}</h1></body></html>"
 }
}
```

Реальный ответ (файл создан на проверке 02.11.2026 и удалён после проверки):

```json
{
 "ok": true,
 "data": {
  "file": "...\\keycrm-mcp\\exports\\document_preview_1793570868.pdf",
  "bytes": 10286,
  "content_type": "text/html; charset=UTF-8",
  "note": "PDF is saved to disk, content-type header is wrong on this server"
 }
}
```

Проверено: файл действительно PDF, начинается с `%PDF-1.7`, размер 10 286 байт. Сервер врёт в `content-type` и отдаёт `text/html`, поэтому ориентироваться на расширение и сигнатуру файла, а не на заголовок.

Печать и прикрепление при нуле шаблонов:

```json
{"action": "print", "template_id": 1, "scope": "order", "model_id": 1}
```

```json
{"ok": true, "data": {"templates": 0, "message": "no document templates on this account, use preview or preview_pdf instead", "raw_status": 404}}
```

```json
{"action": "attach", "template_id": 1, "scope": "order", "model_id": 1, "data": {}}
```

```json
{"ok": true, "data": {"templates": 0, "message": "no document templates on this account, attach is unavailable"}}
```

Демо-данные по типам (подставляются вместо `model.*`):

| type | Что подставляется |
|---|---|
| `order` | `model.id = 1111`, `model.grand_total = 170` |
| `lead` | `model.id = 181900` |
| `delivery` | `model.id = 1111` |
| `warehouse` | `model.id = 10001` |
| `client` | полей `id` нет; доступны `full_name`, `phones`, `emails`, `company`, `manager`, `birthday`, `note` |
| `general` | подстановка не выполнилась: `{{ model.id }}` вернулся как есть, нужно проверить отдельно |

Пометки:

- `attach` теперь ходит GET на `/config/documents/attach/{template}/{scope}/{model_id}`. В `endpoints.json` записан POST, это ошибка каталога: рабочий метод - GET.
- `print` и `attach` при отсутствии шаблонов больше не валятся исключением, а возвращают `templates: 0` и текст-подсказку.
- `preview_pdf` сохраняет настоящий PDF в `keycrm-mcp/exports/`, а не обрезанную голову текста.
- Шаблоны документов через инструмент не создаются и не редактируются: только чтение и рендер.
- Для `type: "client"` шаблон с `{{ model.id }}` упадёт с 400 `Key "id" for array with keys "full_name, birthday, company, manager, note, phones, emails" does not exist`. Обращаться к существующим полям.

---

## 23. files

Вложения заказов (`file-storage`). Загрузка идёт multipart-чанками по 1 МБ, лимит 250 МБ на заказ.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list_order"` | `list_order`, `validate`, `attach_order`, `download`, `detach`, `delete_file` |
| `order_id` | int | - | list_order, validate, attach_order |
| `path` | str | - | локальный файл для attach_order и validate |
| `filename` | str | - | имя в CRM, по умолчанию имя локального файла |
| `mime` | str | - | MIME-тип, по умолчанию угадывается по имени |
| `content_base64` | str | - | содержимое файла вместо `path` |
| `file_id` | int | - | download, delete_file |
| `attachment_id` | int | - | detach |

| action | Метод и путь | Что делает |
|---|---|---|
| `list_order` | GET `/orders/{order_id}`, поле `attachments` | вложения заказа |
| `validate` | POST `/file-storage/attach/order/{order_id}/validate` с `{"total": размер}` | проверка лимита перед загрузкой |
| `attach_order` | POST `/file-storage/attach/order/{order_id}` multipart | загрузка файла |
| `download` | GET `/file-storage/{file_id}` | скачать файл в `keycrm-mcp/exports/` |
| `detach` | DELETE `/file-storage/detach/{attachment_id}` | открепить вложение от объекта |
| `delete_file` | DELETE `/file-storage/{file_id}` | удалить сам файл, каскадно снимает вложения |

Пример загрузки из локального файла:

```json
{"action": "attach_order", "order_id": 123, "path": "C:\\temp\\contract.pdf", "filename": "contract.pdf"}
```

Пример загрузки из base64:

```json
{"action": "attach_order", "order_id": 123, "filename": "note.txt", "mime": "text/plain", "content_base64": "0J/RgNC40LLQtdGC"}
```

Ответ загрузки по коду инструмента: `{"chunks": 1, "bytes": 12345, "result": <ответ API>}`. Точную форму `result` снять не удалось: на аккаунте сейчас 0 заказов, вложение создавать не к чему. Загрузка заявлена рабочей в описании модуля и проверена при разработке, но этот прогон её не воспроизводил.

Пример скачивания:

```json
{"action": "download", "file_id": 42}
```

Ответ по коду: `{"file": "...\\exports\\file_42_<timestamp>.bin", "bytes": <размер>, "content_type": "<тип>"}`. Файл сохраняется в `keycrm-mcp/exports/` с расширением `.bin`, тип смотреть в `content_type`.

Открепление и удаление:

```json
{"action": "detach", "attachment_id": 7}
{"action": "delete_file", "file_id": 42}
```

Ответы: `{"detached": 7}` и `{"deleted": 42}`.

Пометки:

- Удаление заказа **не удаляет** его файлы. После удаления заказов остаются сироты, чистить только `delete_file` по `file_id`. Такой чистки в batch-удалении заказов нет.
- `delete_file` каскадно удаляет привязки: файл исчезает и из карточек, где был прикреплён.
- `validate` перед загрузкой считает размер локального `path` и спрашивает сервер про лимит. Без `path` размер 0.
- Если нет ни `path`, ни `content_base64`, `attach_order` вернёт `ValueError: path or content_base64 is required`.
- Загрузка и удаление файлов - реальные записи. Сначала `crm_snapshot`, потом одна проверка на тестовом заказе.

---

## 24. automations

Триггеры автоматизаций. Только чтение: создание и переключение меняют живое поведение CRM, поэтому не вынесены.

| Параметр | Тип | По умолчанию | Смысл |
|---|---|---|---|
| `action` | str | `"list"` | `list` или `get` |
| `trigger_id` | int | - | для `get` |
| `event` | str | - | локальный фильтр по событию |
| `group` | str | - | локальный фильтр по группе |
| `is_active` | bool | - | локальный фильтр по активности |

```json
{"action": "list", "is_active": true}
```

Реальный ответ: 7 триггеров, все `event: "change_lead_status"`, `group: "lead"`, все включены. Первый (сокращённо):

```json
{
 "count": 7,
 "triggers": [
  {
   "id": 1,
   "name": "Очікує відповіді +1 день: лайтовий пуш",
   "event": "change_lead_status",
   "group": "lead",
   "matching_type": "all",
   "is_active": true,
   "period": {"when": "delayed", "delayed_time": 1, "delayed_duration": "days"}
  }
 ]
}
```

---

## Сводная таблица

| Инструмент | Пишет в CRM | Официальный API | Главное ограничение |
|---|---|---|---|
| `crm_status` | нет | да | счётчики зависят от обоих каналов |
| `crm_capabilities` | нет | нет | модули и известные проблемы аккаунта |
| `crm_snapshot` | нет (пишет файл) | да | секреты маскируются, но телефоны и суммы остаются |
| `orders` | да | list только | заказов в аккаунте нет, `remove` асинхронный |
| `leads` | да | list с фильтрами | удаление карточек заблокировано навсегда |
| `clients` | да | нет | справочник клиентов пуст |
| `products` | да | нет | `action: "search"` отсутствует |
| `tasks` | да | нет | `create` работает; `delete` безопасен, `complete` через `status: done` |
| `conversations` | да (send) | нет | отправка не проверена |
| `audit` | нет | нет | сырые by_manager и by_entity, фильтра по дате нет |
| `users` | нет | нет | - |
| `settings` | нет | нет | без `section` ответ огромный |
| `report` | нет | да | 5 kind; суммы в минорных единицах |
| `crm_api` | как вызвать | да | без валидации и уборки |
| `crm_endpoints` | нет | нет | только каталог, не ответы |
| `finance` | нет | нет | payments и transactions отдают 500 |
| `delivery` | нет | нет | службы не подключены; warehouses требуют location_ref, suggest 500 |
| `publications` | нет | нет | маркетплейсы не подключены |
| `stocks` | нет | нет | запись только через `crm_api` |
| `comments` | да | нет | добавление не проверено |
| `custom_fields` | нет | нет | значений без entity_id не получить |
| `documents` | нет (рендер) | нет | шаблонов 0; preview, PDF, экспорт-шаблон и раскладки печати |
| `files` | да (загрузка, удаление) | нет | удаление заказа не чистит файлы, нужен delete_file |
| `automations` | нет | нет | чтение только |
