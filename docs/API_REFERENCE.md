# API_REFERENCE: внутренний и официальный API KeyCRM

Карта двух API аккаунта `your-account`: внутренний `https://your-account.api.keycrm.app` (572 маршрута из SPA-бандла v33.0.10) и официальный `https://openapi.keycrm.app/v1`. Все данные сверены с `endpoints.json`, `server.py`, `keycrm_client.py` и живыми ответами от 2026-11-01. Матрица проверки статусов - в [ENDPOINTS_STATUS.md](ENDPOINTS_STATUS.md).

## Прежде чем читать таблицы: опасные эндпоинты

**Никогда не вызывать.**

```
POST /batch/leads/execute/remove
     ?filters[lead_ids]=<id>
     &column_ids=1,2,3,10,11,12,13
     &pipeline_id=1
     body {}
```

Параметры идут в query string, тело пустое. Фронт KeyCRM всегда прикладывает `column_ids` и `pipeline_id`. Если `filters[lead_ids]` не совпал точно (пустой, другой формат, чужой id), сервер удаляет **все карточки перечисленных колонок**. Это не ошибка клиента, это поведение эндпоинта.

Реальный инцидент 01.11.2026: 26 карточек воронки удалены, восстановлены из снимка канбана (26 из 26). Правила: [INCIDENT.md](INCIDENT.md).

**Что заблокировано в MCP-сервере:**

- `leads(action="remove")` не делает HTTP-запрос, возвращает `{"ok": false}` с объяснением;
- `crm_api` блокирует путь `/batch/leads/execute/remove` целиком;
- `crm_api` блокирует любой `/batch/...` с `column_ids` в `query`.

**Правило:** карточки воронки удаляются только вручную в интерфейсе KeyCRM. Через API - никогда, ни одним инструментом.

Безопасные удаления: `DELETE /tasks/{id}`, `DELETE /clients/{id}`, `POST /batch/orders/execute/remove` с телом `{"ids":[...]}` (асинхронно). И только по явному id, после проверки, что удаляется ровно нужный объект.

Перед любым экспериментом с записью сохранить локальный снимок: инструмент `crm_snapshot` (в `server.py`) выгружает карточки, заказы, товары, клиентов, статусы и настройки в `keycrm-mcp/backups/`. Снимок канбана, сделанный за 26 секунд до инцидента, и позволил восстановить карточки.

## Каналы и авторизация

| Канал | База | Авторизация | Что даёт |
|---|---|---|---|
| internal | `https://<домен>.api.keycrm.app` | `POST /auth/login` с `{username, password}` -> `access_token` (24 ч) + `refresh_token` | всё, что умеет веб-интерфейс: 572 маршрута, id в выдаче - id CRM |
| official | `https://openapi.keycrm.app/v1` | `Authorization: Bearer <api_token>`, токен достаётся из `GET /config/api-client` | документированный API, стабильные фильтры `filter[field]`, лимит 20 запросов/мин |

Внутренний лимит в аккаунте: `request_limit: 120` у API-клиента `your-account-default-app` (id `00000000-0000-0000-0000-000000000000`). Токены кешируются в памяти процесса: при 401 клиент делает refresh, при 429 ждёт `Retry-After` и повторяет до 3 раз.

## Каталог 572 маршрутов

- Источник: `endpoints.json`, вытащен из бандла `app.js` build v33.0.10.
- Формат записи: `{имя клиентского метода: {method, path, file}}`.
- Группировка: первый сегмент пути. Такая же группировка у `crm_endpoints`.
- Всего групп: **41** (включая служебные админские и `{uuid}`).
- Методы: GET 200, POST 221, PUT 92, DELETE 51, PATCH 8.

### Сводка по группам

Проверено - сколько GET без path-параметров реально вызывалось в матрице статусов (подробности и ошибки - в [ENDPOINTS_STATUS.md](ENDPOINTS_STATUS.md)).

| Группа | Маршрутов | Назначение | Проверено |
|---|---|---|---|
| `orders` | 55 | заказы, статусы, теги, листы отправки, трекинг | 6, все ok |
| `leads` | 25 | воронки, статусы, карточки | 4: 2 ok, 2 нужны параметры |
| `clients` | 30 | клиенты, компании, контакты, дубли, адреса | 7: 5 ok, 2 нужны параметры |
| `catalog` | 31 | товары, категории, офферы, публикации | 4, все ok |
| `stocks` | 19 | остатки, движения, инвентаризация, склады | 5, все ok |
| `finance` | 55 | счета, платежи, кассы, фискализация, курсы | 12: 10 ok, 2 server-error |
| `delivery` | 63 | службы доставки, накладные, центры упаковки | 15: 13 ok, 1 нужны параметры, 1 server-error |
| `config` | 55 | настройки, кастомные поля, документы, экспорт | 12: 10 ok, 1 нужны параметры, 1 not-found |
| `conversations` | 42 | чаты, каналы, сообщения | 6, все ok |
| `batch` | 36 | массовые операции по сущностям (опасные) | 0, только POST |
| `communications` | 21 | комментарии, звонки, шаблоны | 3, все ok |
| `auth` | 20 | вход, профиль, сессии, 2FA | 4, все ok |
| `tasks` | 8 | задачи | 3, все ok |
| `sources` | 10 | источники заказов и лидов, формы | 1 ok |
| `users` | 8 | пользователи и роли | 3, все ok |
| `suppliers` | 6 | поставщики | 1 ok |
| `manufacturing` | 7 | производство | 2, все ok |
| `loyalty` | 9 | программы лояльности и уровни | 1 ok |
| `automations` | 6 | триггеры автоматизаций | 1 ok |
| `billing` | 6 | подписка KeyCRM: баланс, счета, списания | 4, все ok |
| `ad-accounts` | 6 | рекламные кабинеты Facebook | 3: 1 ok, 2 нужны параметры |
| `widgets` | 6 | виджеты | 1 ok |
| `tenant` | 4 | пинг, бэкап, восстановление | 1 ok |
| `import` | 4 | импорт данных | 2: 1 ok, 1 нужны параметры |
| `auditing` | 6 | журнал аудита: все изменения и по сущностям | 1 ok |
| `file-storage` | 11 | файлы и вложения | 2: оба нужны параметры |
| `test-api` | 6 | тестовые ручки каналов, сообщений, платежей | 0, только POST |
| `callback` | 3 | OAuth callback провайдеров | 0 |
| `initialize` | 1 | OAuth инициализация | 0 |
| `redirect` | 1 | OAuth redirect | 0 |
| `result` | 1 | OAuth result | 0 |
| `demo` | 1 | служебный демо-тенант | 0 |
| `email` | 1 | служебная замена email | 0 |
| `sync` | 1 | `systemAdminSync` из отдельного админ-клиента | 1: not-found (404) |
| `commands` | 2 | служебные команды производства и заказов | 0 |
| `{uuid}` | 1 | служебный `systemAdminTenant` | 0 |
| `activate_nfr` | 1 | служебный, активация NFR | 0 |
| `balance` | 1 | служебный, баланс | 0 |
| `rate_channel` | 1 | служебный, rate channel | 0 |
| `restore_tenant` | 1 | служебное восстановление тенанта | 0 |
| `toggle_api_token` | 1 | служебное переключение API-токена | 0 |

## Заказы: group `orders` (55)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/orders` | список заказов; на этом аккаунте пуст, читать через официальный `/order` |
| POST | `/orders` | создать заказ |
| GET | `/orders/{order_id}` | один заказ целиком |
| PUT | `/orders/{order_id}` | обновить заказ |
| POST | `/orders/{order_id}/status/{status_id}` | сменить статус |
| GET | `/orders/statuses` | статусы заказов |
| POST | `/orders/statuses` | создать статус |
| PUT | `/orders/statuses/{status}` | обновить статус |
| PATCH | `/orders/statuses/{status}` | частично обновить статус |
| DELETE | `/orders/statuses/{status}` | удалить статус |
| POST | `/orders/statuses/reorder` | изменить порядок статусов |
| GET | `/orders/groups` | группы статусов |
| GET | `/orders/tags` | теги заказов |
| POST | `/orders/tags` | создать тег |
| PUT | `/orders/tags/{tag}` | обновить тег |
| PATCH | `/orders/tags/{tag}` | частично обновить тег |
| DELETE | `/orders/tags/{tag}` | удалить тег |
| GET | `/orders/totals` | сводные итоги заказов |
| GET | `/orders/client/{client_id}` | заказы клиента |
| GET | `/orders/client/{client_id}/details` | заказы клиента с деталями |
| GET | `/orders/company/{company_id}` | заказы компании |
| POST | `/orders/merge` | объединить заказы |
| POST | `/orders/{order}/copy` | копировать заказ |
| POST | `/orders/{order}/assigned` | синхронизировать менеджеров заказа |
| PUT | `/orders/{order}/marketing` | UTM-метки заказа |
| PUT | `/orders/{order}/shipping` | данные доставки заказа |
| GET | `/orders/{order}/expenses` | расходы заказа |
| GET | `/orders/{order}/shipping-history` | история доставки |
| POST | `/orders/{order}/shipping-history/sync` | синхронизировать историю доставки |
| PUT | `/orders/{order_id}/client` | привязать клиента к заказу |
| GET | `/orders/{order_id}/loyalty` | лояльность по заказу |
| POST | `/orders/{order}/tags` | синхронизировать теги заказа |
| POST | `/orders/{order}/tags/{tag}` | повесить тег |
| POST | `/orders/{order}/tags/{tag}/detach` | снять тег |
| POST | `/orders/{order_id}/discount` | включить или выключить скидку |
| POST | `/orders/{order_id}/products` | добавить товар в заказ |
| PUT | `/orders/{order_id}/products/{product_id}` | обновить товар в заказе |
| DELETE | `/orders/{order_id}/products/{product_id}` | убрать товар из заказа |
| POST | `/orders/{order_id}/products/{product_id}/copy` | копировать товар в заказе |
| GET | `/orders/{order_id}/products/{product_id}/shipment-type` | тип отгрузки товара |
| PUT | `/orders/{order_id}/products/{product_id}/shipment-type` | задать тип отгрузки товара |
| DELETE | `/orders/{order_id}/products/{product_id}/shipment-type` | убрать тип отгрузки |
| POST | `/orders/{order}/tracking/add` | добавить трек-номер |
| DELETE | `/orders/{order}/tracking` | удалить трек-номер |
| GET | `/orders/shipping-list` | листы отправки |
| POST | `/orders/shipping-list/{id}` | добавить заказ в лист отправки |
| GET | `/orders/shipping-list/{id}` | один лист отправки |
| PUT | `/orders/shipping-list/{id}` | обновить лист отправки |
| DELETE | `/orders/shipping-list/{id}` | удалить лист отправки |
| GET | `/orders/shipping-list/orders/{id}` | заказы листа отправки |
| GET | `/orders/shipping-list/{id}/print` | печать листа |
| GET | `/orders/shipping-list/{id}/print-shipments` | печать отправок листа |
| PUT | `/orders/{order_id}/source/mark-as-shipped` | отметить заказ как отгруженный у источника |
| PUT | `/orders/{order_id}/source/sync` | синхронизировать заказ с источником |
| POST | `/orders/sync` | синхронизировать отсутствующий у источника заказ |

## Воронки и карточки: group `leads` (25)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/leads` | список карточек; на аккаунте отдаёт 15 на страницу по умолчанию, внутренний API понимает `per_page` |
| POST | `/leads` | создать карточку: `status_id`, `communicate_at`, `currency_code` обязательны |
| GET | `/leads/{id}` | карточка целиком |
| PUT | `/leads/{id}` | обновить карточку, в том числе `status_id` для переноса |
| POST | `/leads/{id}/copy` | копировать карточку |
| POST | `/leads/merge/{from_id}/{to_id}` | слить две карточки |
| POST | `/leads/{id}/products` | добавить товар в карточку |
| PUT | `/leads/{id}/order` | превратить карточку в заказ |
| GET | `/leads/pipelines` | воронки; без `leads=true|false` отдаёт 500 |
| POST | `/leads/pipelines` | создать воронку |
| PUT | `/leads/pipelines/{id}` | обновить воронку |
| DELETE | `/leads/pipelines/{id}` | удалить воронку |
| POST | `/leads/pipelines/reorder` | порядок воронок |
| GET | `/leads/pipelines/desk` | канбан по воронке по умолчанию |
| GET | `/leads/pipelines/desk/{id}` | канбан конкретной воронки |
| GET | `/leads/statuses/{id}` | статусы воронки |
| POST | `/leads/statuses` | создать статус воронки |
| PUT | `/leads/statuses/{id}` | обновить статус |
| DELETE | `/leads/statuses/{id}` | удалить статус |
| PUT | `/leads/statuses/{id}/reorder` | порядок статусов |
| GET | `/leads/statuses/{id}/cards` | карточки статуса |
| GET | `/leads/by-client/{client_id}` | карточки клиента |
| GET | `/leads/by-company/{company_id}` | карточки компании |
| GET | `/leads/by-contact/{contact_id}` | карточки контакта; на тестовой карточке вернул пусто, нужно проверить |
| GET | `/leads/identify` | найти карточку по телефону или email; без параметра 422 |

## Клиенты: group `clients` (30)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/clients` | список клиентов; на аккаунте 0 записей |
| POST | `/clients` | создать клиента (`full_name` обязателен) |
| GET | `/clients/{id}` | клиент целиком |
| PUT | `/clients/{id}` | обновить клиента |
| DELETE | `/clients/{id}` | удалить клиента |
| GET | `/clients/search` | поиск по имени, телефону, email |
| GET | `/clients/list` | список для слияния |
| GET | `/clients/config` | конфиг раздела клиентов |
| GET | `/clients/duplicates` | поиск дублей |
| POST | `/clients/{id}/duplicates` | слить дубли |
| DELETE | `/clients/{id}/duplicates/{cloneId}` | убрать дубль |
| POST | `/clients/from-contact` | создать клиента из контакта |
| PUT | `/clients/contacts/{id}` | обновить контакт |
| PUT | `/clients/contacts/{id}/assign/{client_id}` | привязать контакт к клиенту |
| PUT | `/clients/contacts/{id}/switch/{client_id}` | переключить контакт на другого клиента |
| GET | `/clients/company` | список компаний |
| POST | `/clients/company` | создать компанию |
| GET | `/clients/company/{id}` | компания |
| PUT | `/clients/company/{id}` | обновить компанию |
| DELETE | `/clients/company/{id}` | удалить компанию |
| GET | `/clients/company/search` | поиск компаний |
| GET | `/clients/company-list/{companyId}` | клиенты компании |
| POST | `/clients/company/{company_id}/client` | привязать клиента к компании |
| GET | `/clients/{id}/shipping-address` | адреса доставки клиента |
| POST | `/clients/{id}/shipping-address` | добавить адрес |
| PUT | `/clients/{id}/shipping-address/{address_id}` | обновить адрес |
| DELETE | `/clients/{id}/shipping-address/{address_id}` | удалить адрес |
| POST | `/clients/{client_id}/profiles` | добавить профиль |
| PUT | `/clients/{client_id}/profiles/{profile_id}` | обновить профиль |
| DELETE | `/clients/{client_id}/profiles/{profile_id}` | удалить профиль |

## Каталог: group `catalog` (31)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/catalog/products` | список товаров |
| POST | `/catalog/products` | создать товар |
| GET | `/catalog/products/{product_id}` | товар целиком |
| PUT | `/catalog/products/{product_id}` | обновить товар |
| DELETE | `/catalog/products/{product_id}` | удалить товар |
| POST | `/catalog/products/{id}/archive` | архивировать товар |
| POST | `/catalog/products/popular` | популярные товары |
| GET | `/catalog/products/statuses` | статусы товаров |
| POST | `/catalog/products/statuses` | создать статус товара |
| PUT | `/catalog/products/statuses/{id}` | обновить статус товара |
| POST | `/catalog/products/statuses/reorder` | порядок статусов товаров |
| GET | `/catalog/categories/tree` | дерево категорий |
| POST | `/catalog/categories` | создать категорию |
| PUT | `/catalog/categories/{category}` | обновить категорию |
| DELETE | `/catalog/categories/{category}` | удалить категорию |
| GET | `/catalog/products/{product_id}/offers` | офферы товара |
| POST | `/catalog/products/{product_id}/offers` | создать оффер |
| PUT | `/catalog/products/{product_id}/offers` | обновить офферы |
| GET | `/catalog/products/{product_id}/offers/{id}` | один оффер |
| DELETE | `/catalog/products/{product_id}/offers/{id}` | удалить оффер |
| POST | `/catalog/products/{product_id}/offers/{offer_id}/archive` | архивировать оффер |
| PUT | `/catalog/products/{product_id}/offers/properties` | сгенерировать свойства офферов |
| GET | `/catalog/customer-products/{parent_type}/{parent_id}` | товары клиента или заказа |
| PUT | `/catalog/customer-products/{id}` | обновить товар клиента |
| DELETE | `/catalog/customer-products/{id}` | удалить товар клиента |
| GET | `/catalog/product-kits/{subject_type}/{subject_id}` | комплекты |
| PUT | `/catalog/product-kits/{subject_type}/{subject_id}` | сохранить комплект |
| GET | `/catalog/publications` | публикации на маркетплейсах; на аккаунте пусто |
| GET | `/catalog/publications/{publication_id}/variations` | вариации публикации |
| POST | `/catalog/publications/load` | загрузить публикации |
| POST | `/catalog/publications/{publication_id}/sync` | синхронизировать публикацию |

## Склад: group `stocks` (19)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/stocks` | остатки по офферам |
| GET | `/stocks/stat` | итоги: количество, закупочная цена, цена |
| GET | `/stocks/filters_data` | границы фильтров таблицы остатков |
| GET | `/stocks/{offer_id}/history` | история движений оффера |
| GET | `/stocks/movements` | движения склада |
| GET | `/stocks/movements/{movement_id}` | одно движение |
| GET | `/stocks/inventories/{movement}` | строки инвентаризации движения |
| POST | `/stocks/inventory/batch` | создать приход |
| POST | `/stocks/inventory/batch/{movement_id}` | обновить приход |
| POST | `/stocks/inventory/revert/{movement_id}` | отменить движение |
| POST | `/stocks/inventory/stocktaking` | создать инвентаризацию |
| POST | `/stocks/inventory/stocktaking/{movement_id}` | обновить инвентаризацию |
| POST | `/stocks/inventory/transfer` | создать перемещение |
| POST | `/stocks/inventory/transfer/{movement_id}` | обновить перемещение |
| GET | `/stocks/warehouses` | склады |
| POST | `/stocks/warehouses` | создать склад |
| PUT | `/stocks/warehouses/{id}` | обновить склад |
| DELETE | `/stocks/warehouses/{id}` | удалить склад |
| POST | `/stocks/warehouses/{id}` | деактивировать склад |

## Задачи: group `tasks` (8)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/tasks` | прямой список задач; инструмент `tasks.list` ходит в `/tasks/search` с фильтрами |
| POST | `/tasks` | создать задачу; работает, тело ниже |
| GET | `/tasks/{id}` | одна задача |
| PUT | `/tasks/{id}` | обновить задачу; завершение - `{"id": <id>, "status": "done"}` |
| DELETE | `/tasks/{id}` | удалить задачу (безопасно) |
| GET | `/tasks/search` | список и поиск задач: `per_page`, `page`, `filters[tasks]=own|all`, `filters[tab]=actual|closed` |
| GET | `/tasks/expired-count` | число просроченных, на 2026-11-01 равно 0 |
| GET | `/tasks/{type}/{id}` | задачи объекта (заказ, лид, клиент) |

Рабочее тело `POST /tasks`, которое собирает MCP-инструмент:

```json
{
 "name": "Позвонить по заявке",
 "priority": 1,
 "type": "task",
 "description": "Уточнить бюджет",
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

Неполное тело без этих полей может вернуть ошибку валидации. Форма `{"title": ..., "due_at": ...}` не подходит: API ждёт `name` и `scheduled_at`.

## Переписки: group `conversations` (42)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/conversations` | список переписок; на аккаунте 0 |
| POST | `/conversations` | создать переписку |
| GET | `/conversations/{id}` | одна переписка |
| PUT | `/conversations/{id}` | обновить переписку |
| GET | `/conversations/{id}/messages` | сообщения переписки |
| POST | `/conversations/{id}/messages` | отправить сообщение |
| PUT | `/conversations/{id}/messages/{message_id}` | редактировать сообщение |
| DELETE | `/conversations/{id}/messages/{message_id}` | удалить сообщение |
| GET | `/conversations/{id}/messages/for_message/{message_id}` | контекст вокруг сообщения |
| GET | `/conversations/{id}/messages/for_ticket/{ticket_id}` | сообщения тикета |
| POST | `/conversations/{id}/messages/{message_id}/reaction` | реакция на сообщение |
| GET | `/conversations/unread` | непрочитанные |
| GET | `/conversations/by-client/{client_id}` | переписки клиента |
| GET | `/conversations/by-contact/{contact_id}` | переписки контакта |
| GET | `/conversations/by-phone` | переписки по телефону |
| GET | `/conversations/by-channel/{channel_id}/stats` | статистика канала |
| GET | `/conversations/messages/by_client/{id}` | сообщения клиента |
| GET | `/conversations/messages/by_lead/{id}` | сообщения карточки |
| GET | `/conversations/channels` | каналы |
| POST | `/conversations/channels` | подключить канал |
| PUT | `/conversations/channels/{id}` | обновить канал |
| DELETE | `/conversations/channels/{id}` | удалить канал |
| POST | `/conversations/channels/{id}/extend-rate` | продлить лимит канала |
| GET | `/conversations/channels/marketplace` | каналы маркетплейсов |
| GET | `/conversations/tags` | теги переписок |
| POST | `/conversations/tags` | создать тег |
| PUT | `/conversations/tags/{tag}` | обновить тег |
| PATCH | `/conversations/tags/{tag}` | частично обновить тег |
| DELETE | `/conversations/tags/{tag}` | удалить тег |
| POST | `/conversations/{id}/tags` | синхронизировать теги переписки |
| POST | `/conversations/{id}/tags/{tag}` | повесить тег |
| POST | `/conversations/{id}/tags/{tag}/detach` | снять тег |
| GET | `/conversations/tickets/{ticket_id}` | тикет |
| GET | `/conversations/private-viber/{session}/check` | проверка сессии Viber |
| POST | `/conversations/private-viber/info` | информация по Viber |
| POST | `/conversations/private-viber/initialize` | инициализировать Viber |
| POST | `/conversations/private-viber/{session}/activate` | активировать сессию Viber |
| GET | `/conversations/private-whatsapp/{session}/check` | проверка сессии WhatsApp |
| POST | `/conversations/private-whatsapp/info` | информация по WhatsApp |
| POST | `/conversations/private-whatsapp/initialize` | инициализировать WhatsApp |
| POST | `/conversations/private-whatsapp/{session}/activate` | активировать сессию WhatsApp |
| GET | `/conversations/telegram-client/{session}/validate` | проверка сессии Telegram |

## Комментарии, звонки, шаблоны: group `communications` (21)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/communications/comments/{type}/{id}` | комментарии объекта |
| POST | `/communications/comments/{type}/{id}` | добавить комментарий |
| GET | `/communications/comments/{type}/{id}/{commentId}` | один комментарий |
| PUT | `/communications/comments/{id}` | редактировать комментарий |
| DELETE | `/communications/comments/{id}` | удалить комментарий (мягко) |
| GET | `/communications/calls` | звонки |
| GET | `/communications/calls/{id}` | один звонок |
| PUT | `/communications/calls/{id}` | обновить звонок |
| GET | `/communications/call-routes` | правила маршрутизации звонков |
| POST | `/communications/call-routes` | создать правило |
| PUT | `/communications/call-routes/{id}` | обновить правило |
| DELETE | `/communications/call-routes/{id}` | удалить правило |
| GET | `/communications/call-routes/call-url/{id}` | URL звонка по правилу |
| POST | `/communications/call-routes/suspend` | приостановить правило |
| POST | `/communications/call-routes/trigger` | запустить правило |
| GET | `/communications/templates` | шаблоны сообщений |
| POST | `/communications/templates` | создать шаблон |
| PUT | `/communications/templates/{template}` | обновить шаблон |
| PATCH | `/communications/templates/{template}` | частично обновить шаблон |
| DELETE | `/communications/templates/{template}` | удалить шаблон |
| POST | `/communications/templates/render/{template}` | отрендерить шаблон |

## Финансы: group `finance` (55)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/finance/bills` | счета |
| POST | `/finance/bills` | создать счет |
| PUT | `/finance/bills/{id}` | обновить счет |
| DELETE | `/finance/bills/{id}` | удалить счет |
| PUT | `/finance/bills/transfer` | перевод между счетами |
| PUT | `/finance/bills/{id}/balance-adjustment` | корректировка баланса |
| PUT | `/finance/bills/{id}/change-status` | сменить статус счета |
| GET | `/finance/payments` | платежи; на аккаунте 500 (серверная ошибка) |
| POST | `/finance/payments` | создать платеж |
| PUT | `/finance/payments/{id}` | обновить платеж |
| PUT | `/finance/payments/{id}/cancel` | отменить платеж |
| GET | `/finance/payments/config` | конфиг формы оплаты |
| POST | `/finance/payments/expenses` | платеж-расход |
| GET | `/finance/expense-types` | типы расходов |
| POST | `/finance/expense-types` | создать тип расхода |
| PUT | `/finance/expense-types/{expense_type}` | обновить тип расхода |
| PATCH | `/finance/expense-types/{expense_type}` | частично обновить тип |
| DELETE | `/finance/expense-types/{expense_type}` | удалить тип расхода |
| GET | `/finance/payment-methods` | способы оплаты |
| POST | `/finance/payment-methods` | создать способ оплаты |
| PUT | `/finance/payment-methods/{payment_method}` | обновить способ |
| PATCH | `/finance/payment-methods/{payment_method}` | частично обновить способ |
| DELETE | `/finance/payment-methods/{payment_method}` | удалить способ |
| GET | `/finance/payment-gateways` | платежные шлюзы |
| POST | `/finance/payment-gateways` | подключить шлюз |
| PUT | `/finance/payment-gateways/{id}` | обновить шлюз |
| DELETE | `/finance/payment-gateways/{id}` | удалить шлюз |
| POST | `/finance/payment-gateways/{id}/invoice` | выставить счет через шлюз |
| POST | `/finance/payment-gateways/{id}/drop_invoice/{payment_id}` | отменить счет шлюза |
| POST | `/finance/payment-gateways/{integration}/accounts` | счета интеграции шлюза |
| POST | `/finance/payment-gateways/novapay-business/init/accounts` | NovaPay Business: счета |
| POST | `/finance/payment-gateways/novapay-business/init/auth` | NovaPay Business: авторизация |
| POST | `/finance/payment-gateways/novapay-business/init/clients` | NovaPay Business: клиенты |
| GET | `/finance/currency-rates` | курсы валют |
| POST | `/finance/currency-rates` | обновить курс |
| GET | `/finance/currency-rates/common` | общие курсы |
| POST | `/finance/currency-rates/refresh` | пересчитать курсы |
| GET | `/finance/transactions` | банковские транзакции; на аккаунте 500 |
| GET | `/finance/transactions/config` | конфиг импорта транзакций |
| GET | `/finance/transactions/unlinked` | непривязанные транзакции |
| POST | `/finance/transactions/{id}/archive` | архивировать транзакцию |
| GET | `/finance/fiscals` | фискальные чеки |
| POST | `/finance/fiscals` | создать чек |
| PUT | `/finance/fiscals/{id}` | обновить чек |
| DELETE | `/finance/fiscals/{id}` | удалить чек |
| POST | `/finance/fiscals/auth` | авторизация кассы |
| POST | `/finance/fiscals/{id}/{action}` | смена кассы |
| POST | `/finance/fiscals/{register}/fiscal/{payment}` | фискализировать платеж |
| PUT | `/finance/fiscals/fiscal/{payment}` | отменить фискализацию |
| GET | `/finance/fiscals/fiscal/{payment}` | проверить чек по платежу |
| GET | `/finance/fiscals/{id}/print/{uuid}` | печать чека |
| GET | `/finance/fiscal/{id}/callback` | callback фискализации (GET) |
| POST | `/finance/fiscal/{id}/callback` | callback фискализации (POST) |
| GET | `/finance/{id}/callback` | callback платежного шлюза (GET) |
| POST | `/finance/{id}/callback` | callback платежного шлюза (POST) |

## Доставка: group `delivery` (63)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/delivery/delivery-services` | подключенные службы доставки; на аккаунте пусто |
| POST | `/delivery/delivery-services` | подключить службу |
| PUT | `/delivery/delivery-services/{delivery_service}` | обновить службу |
| PATCH | `/delivery/delivery-services/{delivery_service}` | частично обновить службу |
| DELETE | `/delivery/delivery-services/{delivery_service}` | удалить службу |
| GET | `/delivery/prep-centers` | центры упаковки |
| POST | `/delivery/prep-centers` | создать центр |
| PUT | `/delivery/prep-centers/{id}` | обновить центр |
| DELETE | `/delivery/prep-centers/{id}` | удалить центр |
| GET | `/delivery/prep-centers/active` | активные центры |
| GET | `/delivery/prep-centers/{id}/check` | проверка центра |
| GET | `/delivery/prep-centers/{id}/materials` | материалы центра |
| GET | `/delivery/prep-centers/{id}/products` | товары центра |
| GET | `/delivery/prep-centers/{id}/sender` | отправитель центра |
| POST | `/delivery/prep-centers/warehouses` | склады центров |
| POST | `/delivery/prep-centers/{id}/offers/{order_id}` | офферы для заказа |
| POST | `/delivery/prep-centers/{id}/send/{order_id}` | отправить заказ в центр |
| POST | `/delivery/prep-centers/{prepCenterRequest}/tracking` | трекинг запроса центра |
| GET | `/delivery/shipment-templates` | шаблоны накладных |
| POST | `/delivery/shipment-templates` | создать шаблон |
| PUT | `/delivery/shipment-templates/{shipment_template}` | обновить шаблон |
| PATCH | `/delivery/shipment-templates/{shipment_template}` | частично обновить шаблон |
| DELETE | `/delivery/shipment-templates/{shipment_template}` | удалить шаблон |
| GET | `/delivery/addresses/suggest` | подсказки адресов; на аккаунте 500 |
| GET | `/delivery/novaposhta/warehouse` | отделения Новой Почты |
| GET | `/delivery/novaposhta/location` | города Новой Почты |
| GET | `/delivery/novaposhta/street` | улицы Новой Почты |
| POST | `/delivery/novaposhta/create-shipment/{order}` | создать накладную НП |
| POST | `/delivery/novaposhta/shipment-price/{order}` | рассчитать стоимость НП |
| GET | `/delivery/novaposhta/print/{order}` | печать накладной НП |
| GET | `/delivery/novaposhta_international/warehouse` | отделения НП International |
| POST | `/delivery/novaposhta_international/create-shipment/{order}` | накладная НП International |
| POST | `/delivery/novaposhta_international/shipment-price/{order}` | стоимость НП International |
| GET | `/delivery/novaposhta_international/print/{order}` | печать НП International |
| GET | `/delivery/ukrposhta/warehouse` | отделения Укрпошты |
| GET | `/delivery/ukrposhta/location` | города Укрпошты |
| POST | `/delivery/ukrposhta/create-shipment/{order}` | накладная Укрпошты |
| POST | `/delivery/ukrposhta/shipment-price/{order}` | стоимость Укрпошты |
| GET | `/delivery/ukrposhta/print/{order}` | печать Укрпошты |
| GET | `/delivery/meest_express/warehouse` | отделения Meest Express |
| GET | `/delivery/meest_express/location` | города Meest Express |
| POST | `/delivery/meest_express/create-shipment/{order}` | накладная Meest Express |
| POST | `/delivery/meest_express/shipment-price/{order}` | стоимость Meest Express |
| GET | `/delivery/meest_express/print/{order}` | печать Meest Express |
| GET | `/delivery/rozetka/init/{source}` | инициализация Rozetka |
| POST | `/delivery/rozetka/create-shipment/{order}` | накладная Rozetka |
| GET | `/delivery/rozetka/print/{order}` | печать Rozetka |
| GET | `/delivery/rozetka_delivery/warehouse` | отделения Rozetka Delivery |
| GET | `/delivery/rozetka_delivery/location` | города Rozetka Delivery |
| POST | `/delivery/rozetka_delivery/create-shipment/{order}` | накладная Rozetka Delivery |
| GET | `/delivery/rozetka_delivery/print/{order}` | печать Rozetka Delivery |
| POST | `/delivery/dhl_express/create-shipment/{order}` | накладная DHL Express |
| POST | `/delivery/dhl_express/shipment-price/{order}` | стоимость DHL Express |
| GET | `/delivery/dhl_express/print/{order}` | печать DHL Express |
| POST | `/delivery/fedex/create-shipment/{order}` | накладная FedEx |
| POST | `/delivery/fedex/shipment-price/{order}` | стоимость FedEx |
| POST | `/delivery/fedex/upload-image` | загрузить изображение FedEx |
| GET | `/delivery/fedex/print/{order}` | печать FedEx |
| POST | `/delivery/ups/create-shipment/{order}` | накладная UPS |
| POST | `/delivery/ups/shipment-price/{order}` | стоимость UPS |
| GET | `/delivery/ups/print/{order}` | печать UPS |
| GET | `/delivery/services/{id}/tracking/callback` | трекинг службы (GET) |
| POST | `/delivery/services/{id}/tracking/callback` | трекинг службы (POST) |

## Настройки: group `config` (55)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/config/settings` | все настройки аккаунта (20 ключей) |
| PUT | `/config/settings/general` | общие настройки |
| PUT | `/config/settings/orders` | настройки заказов |
| PUT | `/config/settings/products` | настройки товаров |
| PUT | `/config/settings/leads` | настройки воронок |
| PUT | `/config/settings/companies` | настройки компаний |
| PUT | `/config/settings/currencies` | валюты |
| PUT | `/config/settings/delivery_status_toggles` | переключатели статусов доставки |
| PUT | `/config/settings/external_integrations` | внешние интеграции |
| PUT | `/config/settings/loyalty_programs` | программы лояльности |
| PUT | `/config/settings/manufacturing` | настройки производства |
| PUT | `/config/settings/notifications` | уведомления |
| PUT | `/config/settings/shipment` | настройки отгрузки |
| PUT | `/config/settings/suppliers` | поставщики |
| GET | `/config/api-client` | API-клиент аккаунта, здесь же `api_token` |
| POST | `/config/api-client` | создать API-клиент |
| PUT | `/config/api-client/refresh-api-token` | перевыпустить API-токен |
| GET | `/config/countries` | страны |
| DELETE | `/config/currency/{code}/deleted` | удалить удалённую валюту из корзины |
| GET | `/config/custom-fields` | кастомные поля |
| POST | `/config/custom-fields` | создать поле |
| PUT | `/config/custom-fields/{id}` | обновить поле |
| DELETE | `/config/custom-fields/{id}` | удалить поле |
| POST | `/config/custom-fields/reorder` | порядок полей |
| GET | `/config/custom-fields/{model_id}/{model}/values` | значения полей объекта |
| POST | `/config/custom-fields/{field}/options` | создать опцию |
| PUT | `/config/custom-fields/{field}/options/{id}` | обновить опцию |
| DELETE | `/config/custom-fields/{field}/options/{id}` | удалить опцию |
| PUT | `/config/fields/all` | все поля |
| PUT | `/config/fields/tables` | поля таблиц |
| GET | `/config/documents` | шаблоны документов |
| POST | `/config/documents` | создать шаблон |
| PUT | `/config/documents/{id}` | обновить шаблон |
| DELETE | `/config/documents/{id}` | удалить шаблон |
| GET | `/config/documents/by-scope/{scope}` | шаблоны по области |
| POST | `/config/documents/attach/{template}/{scope}/{model_id}` | прикрепить документ |
| POST | `/config/documents/preview` | превью документа (HTML) |
| POST | `/config/documents/preview-pdf` | превью документа (PDF) |
| GET | `/config/documents/print/{template}/{scope}/{model_id}` | печать документа |
| GET | `/config/export` | задания экспорта |
| POST | `/config/export` | создать экспорт |
| PUT | `/config/export/{id}` | обновить экспорт |
| DELETE | `/config/export/{id}` | удалить экспорт |
| GET | `/config/export/formats` | форматы экспорта |
| GET | `/config/filter-profiles` | сохраненные фильтры; без `list=leads|orders|clients` отдаёт 500 |
| POST | `/config/filter-profiles` | создать фильтр |
| DELETE | `/config/filter-profiles/{id}` | удалить фильтр |
| GET | `/config/print` | шаблоны печати |
| POST | `/config/print` | создать шаблон печати |
| PUT | `/config/print/{id}` | обновить шаблон печати |
| DELETE | `/config/print/{id}` | удалить шаблон печати |
| GET | `/config/static` | статические справочники |
| GET | `/config/post` | сервисы доставки писем |
| POST | `/config/surveys/{survey}` | сохранить ответ опроса |
| GET | `/config/external-integrations/neuron/call-url` | URL интеграции Neuron |

## Пользователи: group `users` (8)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/users` | участники команды |
| POST | `/users` | пригласить пользователя |
| PUT | `/users/{id}` | обновить пользователя |
| GET | `/users/roles` | роли |
| POST | `/users/roles` | создать роль |
| PUT | `/users/roles/{id}` | обновить роль |
| DELETE | `/users/roles/{id}` | удалить роль |
| GET | `/users/permissions` | справочник прав |

Роли и права читаются справочно. Связи роль -> права в API нет: `/users/roles` и `/users/permissions` - два независимых списка, сопоставлять вручную. `permissions_count` в проекции роли на этом аккаунте не приходит.

## Источники: group `sources` (10)

Внутренний API. В официальном `/sources` не существует (404), конфиг источников читается только POST-ручками, простого GET конфига нет.

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/sources` | источники заказов и лидов |
| POST | `/sources` | создать источник |
| PUT | `/sources/{source_id}` | обновить источник |
| DELETE | `/sources/{source_id}` | удалить источник |
| POST | `/sources/config/shop-listing` | конфиг выгрузки в магазин |
| POST | `/sources/config/shop-listing/{source_id}` | конфиг выгрузки для источника |
| POST | `/sources/leads/{driver}/forms` | формы лидов драйвера |
| POST | `/sources/leads/{driver}/forms/{form_id}/fields` | поля формы |
| POST | `/sources/leads/{driver}/pages` | страницы драйвера |
| POST | `/sources/preauthorize/{driver}` | преавторизация драйвера |

## Массовые операции: group `batch` (36)

> **Осторожно.** Вся группа меняет данные пачкой. `POST /batch/leads/execute/remove` опасен и заблокирован в MCP-сервере, см. начало документа. Остальные batch-маршруты проверяйте на одном объекте.

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/batch/{domain}/list` | список доступных batch-операций домена |
| POST | `/batch/clients/execute/export` | экспорт клиентов |
| POST | `/batch/clients/execute/manager` | сменить менеджера клиентов |
| POST | `/batch/clients/execute/remove` | удалить клиентов |
| POST | `/batch/companies/execute/export` | экспорт компаний |
| POST | `/batch/companies/execute/manager` | сменить менеджера компаний |
| POST | `/batch/companies/execute/remove` | удалить компании |
| POST | `/batch/conversations/execute/assign` | назначить переписки |
| POST | `/batch/conversations/execute/close` | закрыть переписки |
| POST | `/batch/conversations/execute/remove_assignment` | снять назначение |
| POST | `/batch/leads/execute/assign_to` | назначить карточки менеджеру |
| POST | `/batch/leads/execute/export` | экспорт карточек |
| POST | `/batch/leads/execute/pipeline` | перенести карточки в другую воронку |
| POST | `/batch/leads/execute/remove` | **ОПАСНО: удаление карточек по колонкам, заблокировано** |
| POST | `/batch/leads/execute/status` | сменить статус карточек |
| POST | `/batch/manufacturing/execute/print` | печать производственных заданий |
| POST | `/batch/manufacturing/execute/producer` | назначить исполнителя |
| POST | `/batch/manufacturing/execute/remove` | удалить задания |
| POST | `/batch/manufacturing/execute/status` | сменить статус заданий |
| POST | `/batch/orders/execute/export` | экспорт заказов |
| POST | `/batch/orders/execute/list` | список заказов пачкой |
| POST | `/batch/orders/execute/manager` | сменить менеджера заказов |
| POST | `/batch/orders/execute/print` | печать заказов |
| POST | `/batch/orders/execute/remove` | удалить заказы, асинхронно |
| POST | `/batch/orders/execute/shipping_date` | сменить дату отгрузки |
| POST | `/batch/orders/execute/status` | сменить статус заказов |
| POST | `/batch/orders/execute/tags` | проставить теги заказам |
| POST | `/batch/products/execute/archive` | архивировать товары |
| POST | `/batch/products/execute/category` | сменить категорию товаров |
| POST | `/batch/products/execute/export` | экспорт товаров |
| POST | `/batch/products/execute/remove` | удалить товары |
| POST | `/batch/publications/execute/create_products` | создать товары публикаций |
| POST | `/batch/publications/execute/remove` | удалить публикации |
| POST | `/batch/tasks/execute/assign_to` | назначить задачи |
| POST | `/batch/tasks/execute/complete` | закрыть задачи |
| POST | `/batch/tasks/execute/scheduled` | перенести срок задач |

## Вход и профиль: group `auth` (20)

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/auth/login` | вход по email и паролю, отдаёт `access_token` и `refresh_token` |
| POST | `/auth/refresh` | обновить токен |
| POST | `/auth/logout` | выйти |
| POST | `/auth/verify` | подтвердить токен |
| POST | `/auth/forgot-password` | запросить сброс пароля |
| POST | `/auth/reset-password` | сбросить пароль |
| POST | `/auth/login-via-account` | вход через связанный аккаунт |
| POST | `/auth/impressionate` | войти от имени пользователя (админ) |
| GET | `/auth/profile` | профиль текущего пользователя |
| PUT | `/auth/profile` | обновить профиль |
| PUT | `/auth/profile/change-password` | сменить пароль |
| GET | `/auth/profile/sessions` | активные сессии |
| DELETE | `/auth/profile/sessions/{id}` | закрыть сессию |
| GET | `/auth/profile/qr` | QR-код для 2FA |
| POST | `/auth/profile/enable_2fa` | включить 2FA |
| POST | `/auth/profile/disable_2fa` | выключить 2FA |
| POST | `/auth/profile/device-token` | токен устройства для пушей |
| GET | `/auth/profile/notifications/count` | число уведомлений |
| GET | `/auth/profile/notifications/list/{group}` | список уведомлений группы |
| PUT | `/auth/profile/notifications` | отметить уведомления прочитанными |

## Автоматизации: group `automations` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/automations/triggers` | триггеры; на аккаунте 7 |
| POST | `/automations/triggers` | создать триггер |
| PUT | `/automations/triggers/{id}` | обновить триггер |
| DELETE | `/automations/triggers/{id}` | удалить триггер |
| POST | `/automations/triggers/{id}/copy` | копировать триггер |
| PUT | `/automations/triggers/{id}/toggle` | включить или выключить триггер |

## Лояльность: group `loyalty` (9)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/loyalty` | программы лояльности |
| POST | `/loyalty` | создать программу |
| PUT | `/loyalty/{id}` | обновить программу |
| DELETE | `/loyalty/{id}` | удалить программу |
| PUT | `/loyalty/{id}/toggle` | включить или выключить программу |
| POST | `/loyalty/{program}/levels` | создать уровень |
| PUT | `/loyalty/{program}/levels/{id}` | обновить уровень |
| DELETE | `/loyalty/{program}/levels/{id}` | удалить уровень |
| GET | `/loyalty/client/{clientId}/by/source/{sourceId}` | скидка клиента по источнику |

## Производство: group `manufacturing` (7)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/manufacturing` | производственные задания |
| GET | `/manufacturing/new-count` | число новых заданий |
| GET | `/manufacturing/{id}` | одно задание |
| GET | `/manufacturing/{parent_id}/children` | дочерние задания |
| POST | `/manufacturing/{id}/split` | разделить задание |
| PUT | `/manufacturing/{id}` | обновить задание |
| PUT | `/manufacturing/viewed` | отметить просмотренным |

## Поставщики: group `suppliers` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/suppliers` | поставщики |
| POST | `/suppliers` | создать поставщика |
| GET | `/suppliers/{id}` | один поставщик |
| PUT | `/suppliers/{id}` | обновить поставщика |
| DELETE | `/suppliers/{id}` | удалить поставщика |
| GET | `/suppliers/{id}/orders` | заказы поставщика |

## Импорт: group `import` (4)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/import` | задания импорта |
| POST | `/import` | загрузить и разобрать файл |
| GET | `/import/preview` | превью импорта |
| POST | `/import/{id}` | откатить импорт |

## Файлы: group `file-storage` (11)

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/file-storage` | загрузить файл |
| POST | `/file-storage/temp-upload/{group}` | временная загрузка |
| POST | `/file-storage/attach/{model}/{id}` | прикрепить файл к объекту |
| POST | `/file-storage/attach/{model}/{id}/validate` | проверить прикрепление |
| DELETE | `/file-storage/detach/{attachment}` | открепить файл |
| GET | `/file-storage/{file}` | скачать файл |
| GET | `/file-storage/{file}/view` | посмотреть файл |
| DELETE | `/file-storage/{file}` | удалить файл |
| GET | `/file-storage/thumbnails/{path}` | превью |
| GET | `/file-storage/media/download` | скачать медиа |
| GET | `/file-storage/remote` | превью удаленного файла |

## Подписка KeyCRM: group `billing` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/billing` | баланс аккаунта, тариф и расход лимитов |
| GET | `/billing/check` | проверка биллинга |
| GET | `/billing/invoices` | счета на оплату подписки |
| GET | `/billing/payments` | списания подписки |
| POST | `/billing/checkout` | форма оплаты |
| POST | `/billing/checkout/complete` | завершить оплату |

## Рекламные кабинеты: group `ad-accounts` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/ad-accounts` | подключенные рекламные кабинеты |
| POST | `/ad-accounts` | подключить кабинет |
| PUT | `/ad-accounts/{id}` | обновить кабинет |
| DELETE | `/ad-accounts/{id}` | удалить кабинет |
| GET | `/ad-accounts/facebook/accounts` | кабинеты Facebook |
| GET | `/ad-accounts/facebook/datasets` | датасеты Facebook |

## Виджеты: group `widgets` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/widgets` | виджеты |
| POST | `/widgets` | создать виджет |
| GET | `/widgets/{id}` | один виджет |
| PUT | `/widgets/{id}` | обновить виджет |
| PUT | `/widgets/{id}/toggle` | включить или выключить |
| DELETE | `/widgets/{id}` | удалить виджет |

## Аккаунт: group `tenant` (4)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/tenant/ping` | проверка живости тенанта |
| GET | `/tenant/user-info/{code}` | пользователь по коду |
| POST | `/tenant/backup` | бэкап тенанта |
| POST | `/tenant/restore` | восстановление тенанта |

## Журнал аудита: group `auditing` (6)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/auditing/all` | все изменения аккаунта; здесь видно `model_was_deleted` |
| GET | `/auditing/lead/{id}` | история карточки |
| GET | `/auditing/order/{id}` | история заказа |
| GET | `/auditing/manager/{id}` | действия менеджера |
| GET | `/auditing/manufacturing/{id}` | история производственного задания |
| GET | `/auditing/task/{id}` | история задачи |

## Служебные группы

Маршруты из этих групп вызываются фронтом и админкой KeyCRM, для агентской работы почти не нужны. Админские пути вида `systemAdmin*` рассчитаны на отдельный админ-клиент и от API тенанта могут не работать.

| Группа | Метод | Путь | Назначение |
|---|---|---|---|
| `commands` | POST | `/commands/orders` | служебная команда по заказам |
| `commands` | POST | `/commands/manufacturing` | служебная команда по производству |
| `test-api` | POST | `/test-api/channels/create` | создать тестовый канал |
| `test-api` | POST | `/test-api/contacts/create` | создать тестовый контакт |
| `test-api` | POST | `/test-api/conversations/create` | создать тестовую переписку |
| `test-api` | POST | `/test-api/messages/create` | создать тестовое сообщение |
| `test-api` | POST | `/test-api/mock/messages/received` | сымитировать входящее сообщение |
| `test-api` | POST | `/test-api/payments/external/create` | создать тестовый внешний платеж |
| `callback` | GET | `/callback/{provider}` | OAuth callback провайдера |
| `callback` | POST | `/callback/{provider}` | OAuth callback провайдера |
| `callback` | POST | `/callback/pumb` | OAuth callback PUMB |
| `initialize` | POST | `/initialize/{provider}` | OAuth инициализация |
| `redirect` | GET | `/redirect/{provider}/{session_id}` | OAuth redirect |
| `result` | GET | `/result/{provider}/{session_id}` | OAuth result |
| `demo` | GET | `/demo/{email}` | демо-тенант |
| `email` | POST | `/email/{uuid}` | замена email тенанта |
| `sync` | GET | `/sync` | `systemAdminSync`; через API тенанта отдаёт 404 |
| `{uuid}` | GET | `/{uuid}` | `systemAdminTenant`, тенант по uuid |
| `activate_nfr` | POST | `/activate_nfr/{id}/{uuid}` | активация NFR |
| `balance` | POST | `/balance/{id}/{uuid}` | баланс тенанта (админский) |
| `rate_channel` | POST | `/rate_channel/{uuid}/{channel_id}` | rate channel (админский) |
| `restore_tenant` | POST | `/restore_tenant/{id}` | восстановление тенанта (админский) |
| `toggle_api_token` | POST | `/toggle_api_token/{uuid}` | переключение API-токена (админский) |

## Официальный API `openapi.keycrm.app/v1`

Документированный API. Авторизация: `Authorization: Bearer <api_token>`. Токен лежит в настройках аккаунта и доступен через внутренний `GET /config/api-client`; MCP-сервер достаёт его сам, если не задан `KEYCRM_API_TOKEN`.

Лимит: 20 запросов в минуту (по документации KeyCRM). Фильтры: `filter[field]=value`, период - `filter[created_between]=2026-10-01,2026-11-01`. Пагинация: `limit` и `page`.

Конверт ответа списка (реальные поля, проверено на `/users`, `/products`, `/pipelines/cards`):

```json
{
 "current_page": 1,
 "data": [],
 "first_page_url": "...",
 "from": null,
 "last_page": 1,
 "last_page_url": "...",
 "links": [],
 "next_page_url": null,
 "path": "https://openapi.keycrm.app/v1/...",
 "per_page": 15,
 "prev_page_url": null,
 "to": null,
 "total": 0
}
```

Маршруты, которые использует MCP-сервер:

| Метод | Путь | Где в коде | Что даёт |
|---|---|---|---|
| GET | `/order` | `orders.list`, `report(kind="sales")`, счётчик в `crm_status` | заказы с фильтрами и пагинацией |
| GET | `/pipelines/cards` | `leads.list` с фильтрами, `report(kind="leads")` | карточки воронки |
| GET | `/pipelines` | `report(kind="leads")` | воронки |
| GET | `/pipelines/{id}/statuses` | `report(kind="leads")` | статусы воронки |
| GET | `/users` | `crm_status` (проверка канала) | пользователи |
| GET | `/products` | проверено вручную | товары |
| GET | `/buyer` | проверено вручную, на аккаунте пусто | покупатели |

Другие операции официального API (создание заказов, обновление покупателей и т.п.) в MCP-сервере не используются: для записи он ходит во внутренний API. Точный перечень операций - в официальной документации KeyCRM, придумывать пути не нужно.

### Официальный API: что доступно

Проверено GET-запросами 02.11.2026. Все пути ниже отвечают 2xx. Форма ответа - конверт списка из раздела выше, если не указано иное.

| Путь | Что даёт | Живой признак |
|---|---|---|
| `/calls` | звонки | `total: 0` |
| `/custom-fields` | кастомные поля | ответ **списком** без конверта, 12 полей |
| `/companies` | компании | `total: 0` |
| `/offers` | офферы (вариации товаров) | `total: 3` |
| `/offers/stocks` | остатки офферов | `total: 3` |
| `/storage` | файлы и вложения | `total: 3` |
| `/payments/external-transactions` | внешние транзакции | `total: 0` |
| `/order/source` | справочник источников заказов | `total: 9` |
| `/order/status` | справочник статусов заказов | `total: 19` |
| `/order/tag` | справочник тегов | `total: 0` |
| `/order/payment-method` | способы оплаты | `total: 5` |
| `/order/expense-type` | типы расходов | `total: 8` |
| `/order/delivery-service` | службы доставки | `total: 0` |
| `/order/product-status` | статусы товаров | `total: 0` |
| `/buyer` | покупатели | `total: 0` |
| `/products/categories` | категории товаров | `total: 0` |
| `/pipelines/cards` | карточки воронки | `total: 42` |

Не существуют, отвечают 404 с текстом `The route v1/<path> could not be found.`: `/storages`, `/payments`, `/sources`, `/statuses`, `/tags`, `/webhooks`.

Примечания:

- Отдельного вебхук-API нет: `/webhooks` отдаёт 404. Вебхуки и интеграции настраиваются в интерфейсе KeyCRM, не через API.
- Конфиг источников читается только POST-ручками: `/sources/config/shop-listing`, `/sources/config/shop-listing/{id}`, `/sources/leads/{driver}/forms`, `/sources/preauthorize/{driver}`. Простого GET конфига нет, `/sources` в официальном API тоже 404.
- Роли и права читаются справочно: `/users/roles` и `/users/permissions` (внутренний API). Связи роль -> права в API нет: это два независимых справочника, сопоставлять вручную.
- Задач и переписок в официальном API нет, только внутренний.

### Отличия официального API от внутреннего

| Что | internal | official |
|---|---|---|
| id | id CRM | id CRM (те же) |
| деньги | как в вебе, нередко в минорных единицах | в ответах встречаются те же значения, проверять на живом объекте |
| карточка | `GET /leads/{id}` отдаёт вложенный `contact` | `GET /pipelines/cards` отдаёт только `contact_id`, без телефона |
| список карточек | `GET /leads`, 15 по умолчанию, `per_page` | `GET /pipelines/cards`, `limit` работает |
| список заказов | `GET /orders` пуст на этом аккаунте | `GET /order` работает |
| справочники | статусы, группы, теги, источники - внутренние | в официальном API справочники беднее |
| лимит | 120 запросов/мин | 20 запросов/мин |

## Соответствие сущностей

| Сущность | Внутренний API | Официальный API |
|---|---|---|
| Заказ | `/orders`, `/orders/{id}` | `/order` |
| Карточка воронки (лид, сделка) | `/leads`, `/leads/{id}` | `/pipelines/cards` |
| Воронка и статусы | `/leads/pipelines`, `/leads/statuses/{id}` | `/pipelines`, `/pipelines/{id}/statuses` |
| Клиент, покупатель | `/clients`, `/clients/{id}` | `/buyer` |
| Товар | `/catalog/products` | `/products` |
| Пользователь | `/users` | `/users` |
| Источник | `/sources` | нет прямого аналога, читается из заказа или карточки |
| Задача | `/tasks` | нет (только внутренний) |
| Переписка | `/conversations` | нет (только внутренний) |

## Известные проблемы и особенности

Проверено на аккаунте `your-account` 2026-11-01. Матрица по всем 572 маршрутам - в [ENDPOINTS_STATUS.md](ENDPOINTS_STATUS.md).

| Место | Симптом | Причина и обход |
|---|---|---|
| `POST /batch/leads/execute/remove` | удаляет все карточки колонок | **опасно, заблокировано в MCP**. Только ручное удаление в UI |
| `POST /tasks` | ошибка валидации при неполном теле | создание работает: нужны `name`, `priority`, `type`, `status`, `scheduled_at`, `assigned_to_id` и остальные поля тела. MCP-инструмент собирает их сам |
| `GET /orders` (internal) | пустой список | особенность аккаунта. Заказы читаются официальным `GET /order` |
| `POST /batch/orders/execute/remove` | объект пропадает не сразу | операция асинхронная, 2-5 секунд |
| `GET /finance/payments` | 500 | серверная ошибка, подтверждено повторно |
| `GET /finance/transactions` | 500 | то же |
| `GET /config/filter-profiles` | 500 без параметров | нужен `list=leads|orders|clients` |
| `GET /delivery/addresses/suggest` | 500 | провайдер адресов не настроен |
| `GET /leads/pipelines` | 500 без параметров | нужен `leads=true` или `leads=false` |
| `GET /sync` | 404 | путь админ-клиента, от API тенанта недоступен |
| `orderBy` в query | сортирует только `/stocks` | на `/catalog/products`, `/leads`, `/tasks` параметр принимается, но игнорируется: `asc` и `desc` дают одинаковый дефолтный порядок. На `/orders`, `/clients`, `/users`, `/suppliers`, `/stocks/movements`, `/communications/calls`, `/sources`, `/orders/statuses` любой `orderBy` даёт 500. Формат `field:asc` ломает везде. Сортировать в коде |
| внутренние списки | игнорируют `limit` | передавать `per_page`, максимум 50 |
| `/catalog/products` | удалённый товар виден пару секунд | краткий кеш списка, не ошибка |
| `GET /leads/by-contact/{id}` | вернул пусто для существующего контакта | нужно проверить отдельно, возможно другой формат id |
| `GET /tasks` | прямой список может быть пуст | инструмент использует `/tasks/search` с `filters[tasks]` и `filters[tab]` |
| `/clients` | 0 записей | справочник клиентов не заполнен, контакты лежат в карточках |
| оформление `batch` | ждёт `ids[]` в теле | для заказов тело `{"ids":[...]}`, для карточек фронт ещё шлёт `column_ids` в query |

## Как искать нужный маршрут

1. Найти кандидатов через `crm_endpoints`:

```json
{"query": "tags", "limit": 20}
{"group": "finance"}
```

2. Проверить форму ответа безопасным GET через `crm_api`:

```json
{"method": "GET", "path": "/orders/statuses", "api": "internal"}
```

3. Если маршрута нет в готовом инструменте, вызывать `crm_api`, помня про предохранители: `/batch/leads/execute/remove` и любые batch с `column_ids` заблокированы.

4. Полный список путей лежит в `endpoints.json`: формат `{"имя": {"method": ..., "path": ..., "file": ...}}`.

5. Из CLI то же самое без MCP:

```powershell
.\.venv\Scripts\python.exe crm_cli.py get "/orders/statuses"
.\.venv\Scripts\python.exe crm_cli.py official GET /pipelines
.\.venv\Scripts\python.exe crm_cli.py search-endpoints tags
```


