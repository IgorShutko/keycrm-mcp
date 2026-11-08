
# KeyCRM API - внутренний контракт и реверс-инжиниринг

> Официальный OpenAPI описан в документации вендора. Эта заметка про другой, недокументированный слой: внутренний API, который вызывает сам веб-интерфейс keyCRM. Он шире официального и ведёт себя иначе в авторизации, пагинации и сортировке. Всё ниже проверено на живом аккаунте в ноябре 2026, а не пересказано из справки.

## 🎯 TL;DR

- Два канала к одному аккаунту: внутренний `https://<домен>.api.keycrm.app` (логин и пароль владельца, 24 часа на access-токен) и официальный `https://openapi.keycrm.app/v1` (Bearer API-ключ, лимит 20 запросов в минуту).
- Карта внутреннего API: **572 маршрута в 41 группе**, вытащены из бандла SPA `app.js` сборки v33.0.10. Официальный OpenAPI при этом содержит только 43 пути и 59 операций.
- API-ключ официального канала лежит в самом аккаунте: `GET /config/api-client` отдаёт поле `api_token`, отдельно его создавать не нужно.
- `orderBy` в ответе 200 не значит, что сортировка применилась: на `/catalog/products`, `/leads` и `/tasks` порядок одинаков для asc и desc. Реально сортирует только `/stocks`.
- Официальный API лучше внутреннего для справочников и денег: `/order/status` (19 статусов), `/order/payment-method` (5), `/order/expense-type` (8), `/offers/stocks`, `/storage`, `/calls`, `/custom-fields`.
- Внутренний список заказов `GET /orders` на этом тенанте пустой даже когда заказы существуют: читать заказы нужно официальным `GET /order`.

## Два канала: что чем закрывать

| | Внутренний API | Официальный OpenAPI |
|---|---|---|
| База | `https://<домен>.api.keycrm.app` | `https://openapi.keycrm.app/v1` |
| Авторизация | `POST /auth/login` с username и password, дальше `Authorization: Bearer <access_token>` | `Authorization: Bearer <api_token>` |
| Время жизни токена | 24 часа, есть `refresh_token` и `POST /auth/refresh` | бессрочный ключ аккаунта |
| Лимит | около 120 запросов в минуту на аккаунт | 20 запросов в минуту на ключ |
| Покрытие | всё, что умеет веб-интерфейс: 572 маршрута | только документированные сущности, 59 операций |
| Когда брать | лиды и воронки, задачи, комментарии, файлы, документы, настройки, аудит, справочники доставки | заказы, покупатели, товары и остатки, платежи, каталог, справочники заказа |

Практическое правило: читаем и пишем заказы, покупателей и каталог официальным каналом, всё остальное внутренним. Официальный API ещё и честнее валидирует: значения кастомных полей типа select принимает массивом строк и молча игнорирует неверную метку, внутренний PUT в таких случаях отвечает 200 и не меняет данные.

## Авторизация внутреннего API

Схема ровно та, что использует SPA:

```
POST https://<домен>.api.keycrm.app/auth/login
Content-Type: application/json

{"username": "<e-mail>", "password": "<пароль>"}
```

Ответ содержит `access_token`, `refresh_token` и `expires_in` около 86400 секунд. Дальше каждый запрос идёт с `Authorization: Bearer <access_token>`. Заголовки, которые фронт прикладывает и которые полезно повторять: `UserLocale: ru`, `Origin` и `Referer` вида `https://<домен>.keycrm.app/`. Без них часть ручек отвечает так же, но с ними поведение совпадает с интерфейсом.

Официальный ключ ищется через внутренний API: `GET /config/api-client` возвращает объект с полями `id`, `name`, `api_token`, `request_limit`, `is_active`. На проверенном аккаунте `request_limit` был 120, а не 20 из справки: 20 относится к публичному ключу, поэтому лимиты стоит перепроверять на своём аккаунте.

## Контракт списков

- Пагинация: `page` и `per_page`, максимум 50. Параметр `limit` внутренние списки в основном игнорируют, кроме отдельных ручек вроде `/catalog/products`, где работает именно `per_page`.
- Фильтры: `filters[имя_поля]=значение`, несколько значений через запятую. Пример: `/leads?filters[status_id]=1,2&per_page=50`.
- Поиск: `query`, не `search`. Официальный API ищет через `filter[...]`.
- Дата: `filters[created_between]=2026-10-01,2026-11-01`.
- Форматов ответа списков три: Laravel-пагинация с `meta`, объект с `data` без `meta` и голый массив. Парсер должен поддерживать все три.
- `orderBy` принимается, но не применяется на `/catalog/products`, `/leads`, `/tasks`; 500 даёт на `/orders`, `/clients`, `/users`, `/suppliers`, `/stocks/movements`, `/communications/calls`, `/sources`, `/orders/statuses`. Формат `field:asc` ломает везде, где сортировка вообще работает. Сортировать надо в коде.

## Где внутренний API врёт или ломается

- `GET /order`, `/pipelines/cards`, `/leads/pipelines` - это пути официального API, во внутреннем они отдают 404. Внутренний список заказов - `/orders`, карточки - `/leads`, воронки - `/leads/pipelines?leads=false`.
- `GET /orders` на аккаунте вернул `total: 0`, хотя созданный заказ читался по `GET /orders/{id}`. Причина не установлена, поэтому заказы читаем официальным `/order`.
- 500 на чтение: `/finance/payments`, `/finance/transactions`, `/delivery/addresses/suggest`, а также `GET /config/filter-profiles` без параметра `list` (`list=leads`, `orders` или `clients`).
- Модули выключены на уровне тенанта: `orders.is_active=false`, `conversations.is_active=false`, `companies.is_active=false`, `suppliers.use_suppliers=false`, `loyalty_programs=null`. Пустые списки в этих разделах не означают потерю данных.
- Список товаров коротко кэшируется: удалённый товар может ещё несколько секунд отдаваться в списке, при этом `GET /catalog/products/{id}` уже 404.
- `batch/leads/execute/remove` опасен: при несовпадении `filters[lead_ids]` удаляет все карточки выбранных колонок. Подробности и регламент - в [INCIDENT.md](INCIDENT.md).
- `POST /tasks` исторически отдавал 500 из-за поля `attachments`: нужен пустой массив, а не `null`. Рабочее тело: `name`, `priority`, `type`, `description`, `status`, `scheduled_at`, `assigned_to_id`, `attached`, `period`, `settings`.

## Официальный API: чем закрывает дыры

Проверенные живые ручки: `GET /calls`, `/custom-fields`, `/companies`, `/offers`, `/offers/stocks`, `/storage` (файлы), `/payments/external-transactions`, справочники `/order/source` (9 источников), `/order/status` (19 статусов), `/order/tag`, `/order/payment-method` (5), `/order/expense-type` (8), `/order/delivery-service`, `/order/product-status`, `/buyer`, `/products/categories`, `/pipelines`, `/pipelines/{id}/statuses`, `/pipelines/cards`, `/users`.

Не существуют: `/storages`, `/payments`, `/sources`, `/statuses`, `/tags`, `/webhooks`. Рабочие пути для тех же сущностей: `/storage`, `/payments/external-transactions`, `/order/source`, `/order/status`, `/order/tag`.

## Что пригодилось из внутреннего API

- `GET /auditing/all` и `/auditing/lead/{id}` - журнал изменений: кто, что и когда менял. Это единственный способ восстановить историю значений кастомных полей.
- `GET /config/custom-fields` и `GET /config/custom-fields/{id}/lead/values` - определения полей и значения конкретной карточки.
- `GET /delivery/{carrier}/location|warehouse|street` - справочники Новой Почты, Укрпошты и Rozetka Delivery. Параметры различаются: у НП и Укрпошты склады ищутся по `location_ref` (у Укрпошты это `id` из locations), у Rozetka - по `query`.
- `GET /stocks/stat`, `/stocks/movements`, `/stocks/warehouses` - складская аналитика и остатки.
- `GET /config/documents/preview` и `preview-pdf` - рендер документов по Twig-шаблону. Шаблонов печати в аккаунте нет, `print` и `attach` отдают 404, а `preview-pdf` возвращает настоящий PDF при неверном `content-type: text/html`.
- `POST /file-storage/attach/order/{id}` - загрузка файлов чанками по 1 МБ, лимит 250 МБ на заказ. Удаление заказа не удаляет файлы, чистить нужно отдельно.

## Как повторить разведку

1. Бандл SPA лежит на S3: `https://keycrm.s3.de.io.cloud.ovh.net/builds/<версия>/js/app.<hash>.js`. Для v33.0.10 это `app.6c73ad04.js`, около 3,5 МБ.
2. Маршруты вытаскиваются регуляркой по объекту вида `имя:["метод","/путь"]`. Их и есть 572.
3. Авторизация и заголовки видны в том же бандле в функции `AuthLogin` и интерсепторе axios.
4. Для проверки ручек достаточно `curl` или `httpx` с Bearer-токеном; логин живёт 24 часа, этого хватает на сессию разведки.

## Карта маршрутов по группам

Всего 572 маршрута в 41 группах. Полная карта с путями и методами лежит в [`endpoints.json`](../endpoints.json), человекочитаемая версия - в [API_REFERENCE.md](API_REFERENCE.md). Ниже только распределение по группам, чтобы понимать, где искать.

| Группа | Маршрутов |
|---|---|
| activate_nfr | 1 |
| ad-accounts | 6 |
| auditing | 6 |
| auth | 20 |
| automations | 6 |
| balance | 1 |
| batch | 36 |
| billing | 6 |
| callback | 3 |
| catalog | 31 |
| clients | 30 |
| commands | 2 |
| communications | 21 |
| config | 55 |
| conversations | 42 |
| delivery | 63 |
| demo | 1 |
| email | 1 |
| file-storage | 11 |
| finance | 55 |
| import | 4 |
| initialize | 1 |
| leads | 25 |
| loyalty | 9 |
| manufacturing | 7 |
| orders | 55 |
| rate_channel | 1 |
| redirect | 1 |
| restore_tenant | 1 |
| result | 1 |
| sources | 10 |
| stocks | 19 |
| suppliers | 6 |
| sync | 1 |
| tasks | 8 |
| tenant | 4 |
| test-api | 6 |
| toggle_api_token | 1 |
| users | 8 |
| widgets | 6 |
| {uuid} | 1 |

## 📎 Источники

- [`endpoints.json`](../endpoints.json) - карта 572 внутренних маршрутов, вытащенная из бандла v33.0.10
- [API_REFERENCE.md](API_REFERENCE.md) - карта по группам, официальный API и маппинг сущностей
- [`keycrm_client.py`](../keycrm_client.py) - рабочий клиент: логин, refresh, ретраи, пагинация
