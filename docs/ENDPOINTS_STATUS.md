# KeyCRM API: матрица статусов 572 маршрутов

Тенант: `your-account` (`https://your-account.api.keycrm.app`).
Источник каталога: `keycrm-mcp/endpoints.json` (извлечён из SPA-бандла v33.0.10).
Дата прогона: 2026-11-01. Исполнитель: агент verifier. Режим: только чтение.

## Метод

- Авторизация: `POST /auth/login` (email + password из `keycrm-mcp/.env`), далее `Authorization: Bearer <access_token>`.
- Проверялись только GET-маршруты без path-параметров: **105 из 572**.
- GET-маршруты с `{param}` и все методы записи (POST/PUT/PATCH/DELETE) не вызывались, помечены `needs-params`.
- Последовательные запросы с паузой 0.35 с, без параллелизма. 429 за оба прохода не встретился.
- Два прохода: первый через `KeyCrm`-клиент, второй raw `httpx` с точными кодами (200/201/204). Классификация совпала, у `GET /tenant/ping` уточнён код 204.
- Ошибка валидации 400/422 трактуется как «маршрут существует, нужны параметры» (`needs-params`).
- Статусы: `ok` (2xx), `needs-params` (маршрут есть, требует параметров), `not-found` (404), `server-error` (5xx), `auth-required` (401), `unknown` (прочее).

## ОПАСНО: массовые batch-операции (DANGEROUS)

Отдельный класс маршрутов, которые нельзя вызывать для аудита и нельзя давать инструменту без ручного подтверждения: `POST /batch/{domain}/execute/*`. Параметры у них идут в query string (`filters[...]`, `column_ids`, `pipeline_id`), тело пустое.

Для `POST /batch/leads/execute/remove` при несовпадении `filters[lead_ids]` (пустой, лишний, не тот формат) сервер трактует запрос как «удалить все карточки перечисленных колонок». В пойманном UI-запросе `column_ids` был пустой строкой; опасны варианты с заполненным `column_ids` при неточном или пустом фильтре.

Инцидент 2026-11-01: вызов `POST /batch/leads/execute/remove` с заполненным `column_ids` и без точного `filters[lead_ids]` удалил 26 реальных карточек воронки. Восстановлены через `POST /leads` (новые id), старые id и аудит-история потеряны.

Правило: ни один `batch/*/execute/*` не вызывается в read-only проверках; удаление и массовые изменения только вручную в UI. Из этого документа нельзя брать этот маршрут в инструменты MCP.

Всего таких маршрутов в каталоге: 35. Все они не вызывались и помечены `DANGEROUS` в столбце заметки полной матрицы.

| Метод | Путь | Имя в каталоге | Особый риск |
|---|---|---|---|
| POST | `/batch/clients/execute/export` | batchClientsExport | массовое изменение |
| POST | `/batch/clients/execute/manager` | batchClientsManager | массовое изменение |
| POST | `/batch/clients/execute/remove` | batchClientsRemove | удаление пачкой |
| POST | `/batch/companies/execute/export` | batchCompaniesExport | массовое изменение |
| POST | `/batch/companies/execute/manager` | batchCompaniesManager | массовое изменение |
| POST | `/batch/companies/execute/remove` | batchCompaniesRemove | удаление пачкой |
| POST | `/batch/conversations/execute/assign` | batchConversationsAssign | массовое изменение |
| POST | `/batch/conversations/execute/close` | batchConversationsClose | массовое изменение |
| POST | `/batch/conversations/execute/remove_assignment` | batchConversationsRemoveAssignment | массовое изменение |
| POST | `/batch/leads/execute/assign_to` | batchLeadsAssignTo | массовое изменение |
| POST | `/batch/leads/execute/export` | batchLeadsExport | массовое изменение |
| POST | `/batch/leads/execute/pipeline` | batchLeadsPipeline | массовое изменение |
| POST | `/batch/leads/execute/remove` | batchLeadsRemove | удаление пачкой |
| POST | `/batch/leads/execute/status` | batchLeadsStatus | массовое изменение |
| POST | `/batch/manufacturing/execute/print` | batchManufacturingPrint | массовое изменение |
| POST | `/batch/manufacturing/execute/producer` | batchManufacturingProducer | массовое изменение |
| POST | `/batch/manufacturing/execute/remove` | batchManufacturingRemove | удаление пачкой |
| POST | `/batch/manufacturing/execute/status` | batchManufacturingStatus | массовое изменение |
| POST | `/batch/orders/execute/export` | batchOrdersExport | массовое изменение |
| POST | `/batch/orders/execute/list` | batchOrdersList | массовое изменение |
| POST | `/batch/orders/execute/manager` | batchOrdersManager | массовое изменение |
| POST | `/batch/orders/execute/print` | batchOrdersPrint | массовое изменение |
| POST | `/batch/orders/execute/remove` | batchOrdersRemove | удаление пачкой |
| POST | `/batch/orders/execute/shipping_date` | batchOrdersShippingDate | массовое изменение |
| POST | `/batch/orders/execute/status` | batchOrdersStatus | массовое изменение |
| POST | `/batch/orders/execute/tags` | batchOrdersTags | массовое изменение |
| POST | `/batch/products/execute/archive` | batchProductsArchive | массовое изменение |
| POST | `/batch/products/execute/category` | batchProductsCategory | массовое изменение |
| POST | `/batch/products/execute/export` | batchProductsExport | массовое изменение |
| POST | `/batch/products/execute/remove` | batchProductsRemove | удаление пачкой |
| POST | `/batch/publications/execute/create_products` | batchPublicationsCreateProducts | массовое изменение |
| POST | `/batch/publications/execute/remove` | batchPublicationsRemove | удаление пачкой |
| POST | `/batch/tasks/execute/assign_to` | batchTasksAssignTo | массовое изменение |
| POST | `/batch/tasks/execute/complete` | batchTasksComplete | массовое изменение |
| POST | `/batch/tasks/execute/scheduled` | batchTasksScheduled | массовое изменение |

## Сводка

| Показатель | Значение |
|---|---|
| Всего маршрутов в каталоге | 572 |
| Проверено GET без path-параметров | 105 |
| ok (2xx) | 89 |
| needs-params (маршрут есть, нужны параметры) | 11 |
| not-found (404) | 2 |
| server-error (5xx) | 3 |
| unknown | 0 |
| auth-required (401) | 0 |
| Не вызывались: GET с path-параметром | 95 |
| Не вызывались: методы записи | 372 |
| Опасные `batch/*/execute/*` (DANGEROUS, не вызывались) | 35 |

Методы в каталоге: DELETE 51, GET 200, PATCH 8, POST 221, PUT 92.

## Сводка по группам

Группа = первый сегмент пути (так же группирует `crm_endpoints` в MCP-сервере).

| Группа | Всего | Проверено | ok | needs-params | not-found | server-error | Не вызывались |
|---|---|---|---|---|---|---|---|
| activate_nfr | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| ad-accounts | 6 | 3 | 1 | 2 | 0 | 0 | 3 |
| auditing | 6 | 1 | 1 | 0 | 0 | 0 | 5 |
| auth | 20 | 4 | 4 | 0 | 0 | 0 | 16 |
| automations | 6 | 1 | 1 | 0 | 0 | 0 | 5 |
| balance | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| batch | 36 | 0 | 0 | 0 | 0 | 0 | 36 |
| billing | 6 | 4 | 4 | 0 | 0 | 0 | 2 |
| callback | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| catalog | 31 | 4 | 4 | 0 | 0 | 0 | 27 |
| clients | 30 | 7 | 5 | 2 | 0 | 0 | 23 |
| commands | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| communications | 21 | 3 | 3 | 0 | 0 | 0 | 18 |
| config | 55 | 12 | 10 | 1 | 1 | 0 | 43 |
| conversations | 42 | 6 | 6 | 0 | 0 | 0 | 36 |
| delivery | 63 | 15 | 13 | 1 | 0 | 1 | 48 |
| demo | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| email | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| file-storage | 11 | 2 | 0 | 2 | 0 | 0 | 9 |
| finance | 55 | 12 | 10 | 0 | 0 | 2 | 43 |
| import | 4 | 2 | 1 | 1 | 0 | 0 | 2 |
| initialize | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| leads | 25 | 4 | 2 | 2 | 0 | 0 | 21 |
| loyalty | 9 | 1 | 1 | 0 | 0 | 0 | 8 |
| manufacturing | 7 | 2 | 2 | 0 | 0 | 0 | 5 |
| orders | 55 | 6 | 6 | 0 | 0 | 0 | 49 |
| rate_channel | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| redirect | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| restore_tenant | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| result | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| sources | 10 | 1 | 1 | 0 | 0 | 0 | 9 |
| stocks | 19 | 5 | 5 | 0 | 0 | 0 | 14 |
| suppliers | 6 | 1 | 1 | 0 | 0 | 0 | 5 |
| sync | 1 | 1 | 0 | 0 | 1 | 0 | 0 |
| tasks | 8 | 3 | 3 | 0 | 0 | 0 | 5 |
| tenant | 4 | 1 | 1 | 0 | 0 | 0 | 3 |
| test-api | 6 | 0 | 0 | 0 | 0 | 0 | 6 |
| toggle_api_token | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| users | 8 | 3 | 3 | 0 | 0 | 0 | 5 |
| widgets | 6 | 1 | 1 | 0 | 0 | 0 | 5 |
| {uuid} | 1 | 0 | 0 | 0 | 0 | 0 | 1 |

## Проблемные маршруты (проверенные отдельно)

| Маршрут | HTTP | Что выяснено |
|---|---|---|
| `GET /leads/pipelines` | 500 без параметров, 200 с параметром | нужен `leads=true|false`; MCP-сервер вызывает с `leads=false`, это рабочий путь |
| `GET /config/filter-profiles` | 500 без параметров, 200 с параметром | нужен `list=leads|orders|clients` (видно в бандле: `listFilterProfiles(e)` -> params `{list:e}`) |
| `GET /finance/payments` | 500 | 500 и с пустыми параметрами, и с limit/page/from-to/date_from/date_to/filter[]; страница финансов в UI-захватах этот вызов не делала, успешный ответ не подтверждён |
| `GET /finance/transactions` | 500 | то же, что payments |
| `GET /delivery/addresses/suggest` | 500 | 500 с `query=Київ` и `q=Київ`, вероятно не настроен провайдер адресов |
| `GET /sync` | 404 | в бандле это `systemAdminSync` из отдельного админ-клиента, путь не от корня API тенанта; из каталога вызвать нельзя |
| `GET /config/external-integrations/neuron/call-url` | 404 | маршрут есть в бандле, но на тенанте не активирован |

## Параметрические ловушки (проверено отдельно, вне матрицы)

| Вход | Маршруты | Поведение |
|---|---|---|
| `orderBy=field:asc` (формат с двоеточием) | `/catalog/products`, `/leads` | 500, сервер не валидирует формат сортировки |
| `orderBy=field` (+ `direction`) | `/catalog/products`, `/leads`, `/tasks` | 200 |
| `orderBy` с любым значением | `/orders`, `/clients`, `/users` | 500; `direction` без `orderBy` работает |
| `leads=true` или `leads=false` | `/leads/pipelines` | без параметра 500 |
| `list=leads`, `list=orders` или `list=clients` | `/config/filter-profiles` | без параметра 500 |

## Полная матрица

`status` в строках без вызова означает, что маршрут не вызывался по правилам read-only режима, а не то, что он сломан. Префикс `DANGEROUS` в заметке означает массовую batch-операцию, которую нельзя вызывать без ручного подтверждения.

| # | Группа | Метод | Путь | Имя в каталоге | Статус | Заметка |
|---|---|---|---|---|---|---|
| 1 | activate_nfr | POST | `/activate_nfr/{id}/{uuid}` | systemAdminActivateNfr | needs-params | не вызывался: метод записи (режим только чтение) |
| 2 | ad-accounts | GET | `/ad-accounts` | advertisementsAdAccountsList | ok | 200 list[1] |
| 3 | ad-accounts | POST | `/ad-accounts` | advertisementsAdAccountsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 4 | ad-accounts | GET | `/ad-accounts/facebook/accounts` | advertisementsAdAccountsFacebookAccounts | needs-params | The given data was invalid. \| ad_account_id: Поле ad account id обязательно для заполнения. |
| 5 | ad-accounts | GET | `/ad-accounts/facebook/datasets` | advertisementsAdAccountsFacebookDatasets | needs-params | The given data was invalid. \| ad_account_id: Поле ad account id обязательно для заполнения. \| facebook_ad_account_id: Поле facebook ad account id обязательно для заполнения. |
| 6 | ad-accounts | DELETE | `/ad-accounts/{id}` | advertisementsAdAccountsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 7 | ad-accounts | PUT | `/ad-accounts/{id}` | advertisementsAdAccountsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 8 | auditing | GET | `/auditing/all` | auditingAll | ok | 200 object(current_page,data,first_page_url,from) |
| 9 | auditing | GET | `/auditing/lead/{id}` | auditingByLead | needs-params | не вызывался: path-параметр в маршруте |
| 10 | auditing | GET | `/auditing/manager/{id}` | auditingByManager | needs-params | не вызывался: path-параметр в маршруте |
| 11 | auditing | GET | `/auditing/manufacturing/{id}` | auditingByManufacturing | needs-params | не вызывался: path-параметр в маршруте |
| 12 | auditing | GET | `/auditing/order/{id}` | auditingByOrder | needs-params | не вызывался: path-параметр в маршруте |
| 13 | auditing | GET | `/auditing/task/{id}` | auditingByTask | needs-params | не вызывался: path-параметр в маршруте |
| 14 | auth | POST | `/auth/forgot-password` | authForgotPassword | needs-params | не вызывался: метод записи (режим только чтение) |
| 15 | auth | POST | `/auth/impressionate` | authImpressionate | needs-params | не вызывался: метод записи (режим только чтение) |
| 16 | auth | POST | `/auth/login` | authLogin | needs-params | не вызывался: метод записи (режим только чтение) |
| 17 | auth | POST | `/auth/login-via-account` | authLoginViaAccount | needs-params | не вызывался: метод записи (режим только чтение) |
| 18 | auth | POST | `/auth/logout` | authLogout | needs-params | не вызывался: метод записи (режим только чтение) |
| 19 | auth | GET | `/auth/profile` | authProfileGet | ok | 200 object(id,first_name,last_name,email) |
| 20 | auth | PUT | `/auth/profile` | authProfileUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 21 | auth | PUT | `/auth/profile/change-password` | authProfileChangePassword | needs-params | не вызывался: метод записи (режим только чтение) |
| 22 | auth | POST | `/auth/profile/device-token` | authProfileDeviceToken | needs-params | не вызывался: метод записи (режим только чтение) |
| 23 | auth | POST | `/auth/profile/disable_2fa` | authProfileDisable2fa | needs-params | не вызывался: метод записи (режим только чтение) |
| 24 | auth | POST | `/auth/profile/enable_2fa` | authProfileEnable2fa | needs-params | не вызывался: метод записи (режим только чтение) |
| 25 | auth | PUT | `/auth/profile/notifications` | authProfileNotificationsMarkAsRead | needs-params | не вызывался: метод записи (режим только чтение) |
| 26 | auth | GET | `/auth/profile/notifications/count` | authProfileNotificationsCount | ok | 200 object(events,system) |
| 27 | auth | GET | `/auth/profile/notifications/list/{group}` | authProfileNotificationsList | needs-params | не вызывался: path-параметр в маршруте |
| 28 | auth | GET | `/auth/profile/qr` | authProfileQr | ok | 200 object(image,code) |
| 29 | auth | GET | `/auth/profile/sessions` | authProfileSessionsList | ok | 200 list[83] |
| 30 | auth | DELETE | `/auth/profile/sessions/{id}` | authProfileSessionsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 31 | auth | POST | `/auth/refresh` | authRefresh | needs-params | не вызывался: метод записи (режим только чтение) |
| 32 | auth | POST | `/auth/reset-password` | authResetPassword | needs-params | не вызывался: метод записи (режим только чтение) |
| 33 | auth | POST | `/auth/verify` | authVerify | needs-params | не вызывался: метод записи (режим только чтение) |
| 34 | automations | GET | `/automations/triggers` | automationsTriggersList | ok | 200 list[7] |
| 35 | automations | POST | `/automations/triggers` | automationsTriggersCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 36 | automations | DELETE | `/automations/triggers/{id}` | automationsTriggersDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 37 | automations | PUT | `/automations/triggers/{id}` | automationsTriggersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 38 | automations | POST | `/automations/triggers/{id}/copy` | automationsTriggersCopy | needs-params | не вызывался: метод записи (режим только чтение) |
| 39 | automations | PUT | `/automations/triggers/{id}/toggle` | automationsTriggersToggle | needs-params | не вызывался: метод записи (режим только чтение) |
| 40 | balance | POST | `/balance/{id}/{uuid}` | systemAdminBalance | needs-params | не вызывался: метод записи (режим только чтение) |
| 41 | batch | POST | `/batch/clients/execute/export` | batchClientsExport | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 42 | batch | POST | `/batch/clients/execute/manager` | batchClientsManager | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 43 | batch | POST | `/batch/clients/execute/remove` | batchClientsRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 44 | batch | POST | `/batch/companies/execute/export` | batchCompaniesExport | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 45 | batch | POST | `/batch/companies/execute/manager` | batchCompaniesManager | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 46 | batch | POST | `/batch/companies/execute/remove` | batchCompaniesRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 47 | batch | POST | `/batch/conversations/execute/assign` | batchConversationsAssign | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 48 | batch | POST | `/batch/conversations/execute/close` | batchConversationsClose | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 49 | batch | POST | `/batch/conversations/execute/remove_assignment` | batchConversationsRemoveAssignment | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 50 | batch | POST | `/batch/leads/execute/assign_to` | batchLeadsAssignTo | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 51 | batch | POST | `/batch/leads/execute/export` | batchLeadsExport | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 52 | batch | POST | `/batch/leads/execute/pipeline` | batchLeadsPipeline | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 53 | batch | POST | `/batch/leads/execute/remove` | batchLeadsRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 54 | batch | POST | `/batch/leads/execute/status` | batchLeadsStatus | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 55 | batch | POST | `/batch/manufacturing/execute/print` | batchManufacturingPrint | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 56 | batch | POST | `/batch/manufacturing/execute/producer` | batchManufacturingProducer | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 57 | batch | POST | `/batch/manufacturing/execute/remove` | batchManufacturingRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 58 | batch | POST | `/batch/manufacturing/execute/status` | batchManufacturingStatus | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 59 | batch | POST | `/batch/orders/execute/export` | batchOrdersExport | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 60 | batch | POST | `/batch/orders/execute/list` | batchOrdersList | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 61 | batch | POST | `/batch/orders/execute/manager` | batchOrdersManager | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 62 | batch | POST | `/batch/orders/execute/print` | batchOrdersPrint | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 63 | batch | POST | `/batch/orders/execute/remove` | batchOrdersRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 64 | batch | POST | `/batch/orders/execute/shipping_date` | batchOrdersShippingDate | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 65 | batch | POST | `/batch/orders/execute/status` | batchOrdersStatus | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 66 | batch | POST | `/batch/orders/execute/tags` | batchOrdersTags | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 67 | batch | POST | `/batch/products/execute/archive` | batchProductsArchive | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 68 | batch | POST | `/batch/products/execute/category` | batchProductsCategory | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 69 | batch | POST | `/batch/products/execute/export` | batchProductsExport | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 70 | batch | POST | `/batch/products/execute/remove` | batchProductsRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 71 | batch | POST | `/batch/publications/execute/create_products` | batchPublicationsCreateProducts | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 72 | batch | POST | `/batch/publications/execute/remove` | batchPublicationsRemove | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 73 | batch | POST | `/batch/tasks/execute/assign_to` | batchTasksAssignTo | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 74 | batch | POST | `/batch/tasks/execute/complete` | batchTasksComplete | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 75 | batch | POST | `/batch/tasks/execute/scheduled` | batchTasksScheduled | needs-params | DANGEROUS, не вызывался: массовая batch-операция. не вызывался: метод записи (режим только чтение) |
| 76 | batch | GET | `/batch/{domain}/list` | batchList | needs-params | не вызывался: path-параметр в маршруте; проверено через GET /batch/leads/list: отдаёт actions (список batch-действий), не лиды |
| 77 | billing | GET | `/billing` | billingBalance | ok | 200 object(sources,ordersCount,leadsCount,messagesCount) |
| 78 | billing | GET | `/billing/check` | billingCheck | ok | 200 object(active) |
| 79 | billing | POST | `/billing/checkout` | billingCheckoutForm | needs-params | не вызывался: метод записи (режим только чтение) |
| 80 | billing | POST | `/billing/checkout/complete` | billingCheckoutComplete | needs-params | не вызывался: метод записи (режим только чтение) |
| 81 | billing | GET | `/billing/invoices` | billingInvoices | ok | 200 object(current_page,data,first_page_url,from) |
| 82 | billing | GET | `/billing/payments` | billingPayments | ok | 200 object(current_page,data,first_page_url,from) |
| 83 | callback | POST | `/callback/pumb` | systemOauthCallbackPumb | needs-params | не вызывался: метод записи (режим только чтение) |
| 84 | callback | GET | `/callback/{provider}` | systemOauthCallbackGet | needs-params | не вызывался: path-параметр в маршруте |
| 85 | callback | POST | `/callback/{provider}` | systemOauthCallbackPost | needs-params | не вызывался: метод записи (режим только чтение) |
| 86 | catalog | POST | `/catalog/categories` | productsCatalogCategoriesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 87 | catalog | GET | `/catalog/categories/tree` | productsCatalogCategoriesList | ok | 200 list[0] |
| 88 | catalog | DELETE | `/catalog/categories/{category}` | productsCatalogCategoriesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 89 | catalog | PUT | `/catalog/categories/{category}` | productsCatalogCategoriesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 90 | catalog | DELETE | `/catalog/customer-products/{id}` | productsCatalogCustomerProductsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 91 | catalog | PUT | `/catalog/customer-products/{id}` | productsCatalogCustomerProductsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 92 | catalog | GET | `/catalog/customer-products/{parent_type}/{parent_id}` | productsCatalogCustomerProductsList | needs-params | не вызывался: path-параметр в маршруте |
| 93 | catalog | GET | `/catalog/product-kits/{subject_type}/{subject_id}` | productsCatalogProductKitsIndex | needs-params | не вызывался: path-параметр в маршруте |
| 94 | catalog | PUT | `/catalog/product-kits/{subject_type}/{subject_id}` | productsCatalogProductKitsUpsert | needs-params | не вызывался: метод записи (режим только чтение) |
| 95 | catalog | GET | `/catalog/products` | productsCatalogProductsList | ok | 200 object(current_page,data,first_page_url,from); orderBy=name (+direction) 200, orderBy=name:asc даёт 500 (сервер не валидирует формат) |
| 96 | catalog | POST | `/catalog/products` | productsCatalogProductsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 97 | catalog | POST | `/catalog/products/popular` | productsCatalogProductsPopular | needs-params | не вызывался: метод записи (режим только чтение) |
| 98 | catalog | GET | `/catalog/products/statuses` | productsCatalogProductsProductsStatusesIndex | ok | 200 list[7] |
| 99 | catalog | POST | `/catalog/products/statuses` | productsCatalogProductsProductsStatusesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 100 | catalog | POST | `/catalog/products/statuses/reorder` | productsCatalogProductsProductsStatusesReorder | needs-params | не вызывался: метод записи (режим только чтение) |
| 101 | catalog | PUT | `/catalog/products/statuses/{id}` | productsCatalogProductsProductsStatusesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 102 | catalog | POST | `/catalog/products/{id}/archive` | productsCatalogProductsArchive | needs-params | не вызывался: метод записи (режим только чтение) |
| 103 | catalog | DELETE | `/catalog/products/{product_id}` | productsCatalogProductsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 104 | catalog | GET | `/catalog/products/{product_id}` | productsCatalogProductsView | needs-params | не вызывался: path-параметр в маршруте |
| 105 | catalog | PUT | `/catalog/products/{product_id}` | productsCatalogProductsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 106 | catalog | GET | `/catalog/products/{product_id}/offers` | productsCatalogProductsOffersList | needs-params | не вызывался: path-параметр в маршруте |
| 107 | catalog | POST | `/catalog/products/{product_id}/offers` | productsCatalogProductsOffersCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 108 | catalog | PUT | `/catalog/products/{product_id}/offers` | productsCatalogProductsOffersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 109 | catalog | PUT | `/catalog/products/{product_id}/offers/properties` | productsCatalogProductsOffersGenerate | needs-params | не вызывался: метод записи (режим только чтение) |
| 110 | catalog | DELETE | `/catalog/products/{product_id}/offers/{id}` | productsCatalogProductsOffersDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 111 | catalog | GET | `/catalog/products/{product_id}/offers/{id}` | productsCatalogProductsOffersDetails | needs-params | не вызывался: path-параметр в маршруте |
| 112 | catalog | POST | `/catalog/products/{product_id}/offers/{offer_id}/archive` | productsCatalogProductsOffersArchive | needs-params | не вызывался: метод записи (режим только чтение) |
| 113 | catalog | GET | `/catalog/publications` | productsCatalogPublicationsList | ok | 200 object(publications,is_available,expires_at) |
| 114 | catalog | POST | `/catalog/publications/load` | productsCatalogPublicationsLoad | needs-params | не вызывался: метод записи (режим только чтение) |
| 115 | catalog | POST | `/catalog/publications/{publication_id}/sync` | productsCatalogPublicationsSync | needs-params | не вызывался: метод записи (режим только чтение) |
| 116 | catalog | GET | `/catalog/publications/{publication_id}/variations` | productsCatalogPublicationsVariationsList | needs-params | не вызывался: path-параметр в маршруте |
| 117 | clients | GET | `/clients` | clientsList | ok | 200 object(current_page,data,first_page_url,from); любой orderBy (id, full_name) даёт 500, direction без orderBy работает |
| 118 | clients | POST | `/clients` | clientsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 119 | clients | GET | `/clients/company` | clientsCompanyIndex | ok | 200 object(current_page,data,first_page_url,from) |
| 120 | clients | POST | `/clients/company` | clientsCompanyCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 121 | clients | GET | `/clients/company-list/{companyId}` | clientsByCompany | needs-params | не вызывался: path-параметр в маршруте |
| 122 | clients | GET | `/clients/company/search` | clientsCompanySearch | ok | 200 object(current_page,data,first_page_url,from) |
| 123 | clients | POST | `/clients/company/{company_id}/client` | clientsCompanyClientAttach | needs-params | не вызывался: метод записи (режим только чтение) |
| 124 | clients | DELETE | `/clients/company/{id}` | clientsCompanyDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 125 | clients | GET | `/clients/company/{id}` | clientsCompanyView | needs-params | не вызывался: path-параметр в маршруте |
| 126 | clients | PUT | `/clients/company/{id}` | clientsCompanyUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 127 | clients | GET | `/clients/config` | clientsConfig | ok | 200 object(sum_max,count_max) |
| 128 | clients | PUT | `/clients/contacts/{id}` | clientsContactsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 129 | clients | PUT | `/clients/contacts/{id}/assign/{client_id}` | clientsContactsAssign | needs-params | не вызывался: метод записи (режим только чтение) |
| 130 | clients | PUT | `/clients/contacts/{id}/switch/{client_id}` | clientsContactsSwitch | needs-params | не вызывался: метод записи (режим только чтение) |
| 131 | clients | GET | `/clients/duplicates` | clientsSearchDuplicates | needs-params | The given data was invalid. \| full_name: Поле полное имя обязательно для заполнения. |
| 132 | clients | POST | `/clients/from-contact` | clientsFromContact | needs-params | не вызывался: метод записи (режим только чтение) |
| 133 | clients | GET | `/clients/list` | clientsMergeList | needs-params | The given data was invalid. \| ids: Поле ids обязательно для заполнения. |
| 134 | clients | GET | `/clients/search` | clientsSearch | ok | 200 object(current_page,data,first_page_url,from) |
| 135 | clients | POST | `/clients/{client_id}/profiles` | clientsProfilesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 136 | clients | DELETE | `/clients/{client_id}/profiles/{profile_id}` | clientsProfilesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 137 | clients | PUT | `/clients/{client_id}/profiles/{profile_id}` | clientsProfilesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 138 | clients | DELETE | `/clients/{id}` | clientsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 139 | clients | GET | `/clients/{id}` | clientsView | needs-params | не вызывался: path-параметр в маршруте |
| 140 | clients | PUT | `/clients/{id}` | clientsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 141 | clients | POST | `/clients/{id}/duplicates` | clientsMerge | needs-params | не вызывался: метод записи (режим только чтение) |
| 142 | clients | DELETE | `/clients/{id}/duplicates/{cloneId}` | clientsDropDuplicates | needs-params | не вызывался: метод записи (режим только чтение) |
| 143 | clients | GET | `/clients/{id}/shipping-address` | clientsShippingAddressAll | needs-params | не вызывался: path-параметр в маршруте |
| 144 | clients | POST | `/clients/{id}/shipping-address` | clientsShippingAddressCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 145 | clients | DELETE | `/clients/{id}/shipping-address/{address_id}` | clientsShippingAddressDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 146 | clients | PUT | `/clients/{id}/shipping-address/{address_id}` | clientsShippingAddressUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 147 | commands | POST | `/commands/manufacturing` | commandsExecuteManufacturing | needs-params | не вызывался: метод записи (режим только чтение) |
| 148 | commands | POST | `/commands/orders` | commandsExecuteOrders | needs-params | не вызывался: метод записи (режим только чтение) |
| 149 | communications | GET | `/communications/call-routes` | communicationsCallsRoutesList | ok | 200 list[0] |
| 150 | communications | POST | `/communications/call-routes` | communicationsCallsRoutesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 151 | communications | GET | `/communications/call-routes/call-url/{id}` | communicationsCallsRoutesCallUrl | needs-params | не вызывался: path-параметр в маршруте |
| 152 | communications | POST | `/communications/call-routes/suspend` | communicationsCallsRoutesSuspend | needs-params | не вызывался: метод записи (режим только чтение) |
| 153 | communications | POST | `/communications/call-routes/trigger` | communicationsCallsRoutesTrigger | needs-params | не вызывался: метод записи (режим только чтение) |
| 154 | communications | DELETE | `/communications/call-routes/{id}` | communicationsCallsRoutesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 155 | communications | PUT | `/communications/call-routes/{id}` | communicationsCallsRoutesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 156 | communications | GET | `/communications/calls` | communicationsCallsList | ok | 200 object(current_page,data,first_page_url,from) |
| 157 | communications | GET | `/communications/calls/{id}` | communicationsCallsView | needs-params | не вызывался: path-параметр в маршруте |
| 158 | communications | PUT | `/communications/calls/{id}` | communicationsCallsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 159 | communications | DELETE | `/communications/comments/{id}` | communicationsCommentsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 160 | communications | PUT | `/communications/comments/{id}` | communicationsCommentsEdit | needs-params | не вызывался: метод записи (режим только чтение) |
| 161 | communications | GET | `/communications/comments/{type}/{id}` | communicationsCommentsList | needs-params | не вызывался: path-параметр в маршруте |
| 162 | communications | POST | `/communications/comments/{type}/{id}` | communicationsCommentsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 163 | communications | GET | `/communications/comments/{type}/{id}/{commentId}` | communicationsCommentsListForId | needs-params | не вызывался: path-параметр в маршруте |
| 164 | communications | GET | `/communications/templates` | communicationsTemplatesIndex | ok | 200 object(data) |
| 165 | communications | POST | `/communications/templates` | communicationsTemplatesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 166 | communications | POST | `/communications/templates/render/{template}` | communicationsTemplatesRendered | needs-params | не вызывался: метод записи (режим только чтение) |
| 167 | communications | DELETE | `/communications/templates/{template}` | communicationsTemplatesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 168 | communications | PATCH | `/communications/templates/{template}` | communicationsTemplatesUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 169 | communications | PUT | `/communications/templates/{template}` | communicationsTemplatesUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 170 | config | GET | `/config/api-client` | configApiClientIndex | ok | 200 object(id,name,api_token,request_limit) |
| 171 | config | POST | `/config/api-client` | configApiClientCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 172 | config | PUT | `/config/api-client/refresh-api-token` | configApiClientRefreshApiToken | needs-params | не вызывался: метод записи (режим только чтение) |
| 173 | config | GET | `/config/countries` | configSettingsCountriesList | ok | 200 list[256] |
| 174 | config | DELETE | `/config/currency/{code}/deleted` | configCurrencyDeleted | needs-params | не вызывался: метод записи (режим только чтение) |
| 175 | config | GET | `/config/custom-fields` | configCustomFieldsIndex | ok | 200 list[12] |
| 176 | config | POST | `/config/custom-fields` | configCustomFieldsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 177 | config | POST | `/config/custom-fields/reorder` | configCustomFieldsReorder | needs-params | не вызывался: метод записи (режим только чтение) |
| 178 | config | POST | `/config/custom-fields/{field}/options` | configCustomFieldsOptionsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 179 | config | DELETE | `/config/custom-fields/{field}/options/{id}` | configCustomFieldsOptionsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 180 | config | PUT | `/config/custom-fields/{field}/options/{id}` | configCustomFieldsOptionsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 181 | config | DELETE | `/config/custom-fields/{id}` | configCustomFieldsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 182 | config | PUT | `/config/custom-fields/{id}` | configCustomFieldsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 183 | config | GET | `/config/custom-fields/{model_id}/{model}/values` | configCustomFieldsValues | needs-params | не вызывался: path-параметр в маршруте |
| 184 | config | GET | `/config/documents` | configDocumentsList | ok | 200 list[0] |
| 185 | config | POST | `/config/documents` | configDocumentsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 186 | config | POST | `/config/documents/attach/{template}/{scope}/{model_id}` | configDocumentsAttachAction | needs-params | не вызывался: метод записи (режим только чтение) |
| 187 | config | GET | `/config/documents/by-scope/{scope}` | configDocumentsByScope | needs-params | не вызывался: path-параметр в маршруте |
| 188 | config | POST | `/config/documents/preview` | configDocumentsPreview | needs-params | не вызывался: метод записи (режим только чтение) |
| 189 | config | POST | `/config/documents/preview-pdf` | configDocumentsPreviewPdf | needs-params | не вызывался: метод записи (режим только чтение) |
| 190 | config | GET | `/config/documents/print/{template}/{scope}/{model_id}` | configDocumentsPrintAction | needs-params | не вызывался: path-параметр в маршруте |
| 191 | config | DELETE | `/config/documents/{id}` | configDocumentsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 192 | config | PUT | `/config/documents/{id}` | configDocumentsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 193 | config | GET | `/config/export` | configExportList | ok | 200 list[1] |
| 194 | config | POST | `/config/export` | configExportCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 195 | config | GET | `/config/export/formats` | configExportFormats | ok | 200 object(csv,xlsx) |
| 196 | config | DELETE | `/config/export/{id}` | configExportDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 197 | config | PUT | `/config/export/{id}` | configExportUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 198 | config | GET | `/config/external-integrations/neuron/call-url` | configExternalIntegrationsNeuronCallUrl | not-found | 404 на тенанте: интеграция Neuron не активирована либо маршрут недоступен |
| 199 | config | PUT | `/config/fields/all` | configFieldsAll | needs-params | не вызывался: метод записи (режим только чтение) |
| 200 | config | PUT | `/config/fields/tables` | configFieldsTables | needs-params | не вызывался: метод записи (режим только чтение) |
| 201 | config | GET | `/config/filter-profiles` | configFilterProfilesList | needs-params | обязателен query-параметр list=leads\|orders\|clients (без него 500), с list=leads 200 |
| 202 | config | POST | `/config/filter-profiles` | configFilterProfilesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 203 | config | DELETE | `/config/filter-profiles/{id}` | configFilterProfilesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 204 | config | GET | `/config/post` | configStaticPostServices | ok | 200 list[24] |
| 205 | config | GET | `/config/print` | configPrintList | ok | 200 list[2] |
| 206 | config | POST | `/config/print` | configPrintCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 207 | config | DELETE | `/config/print/{id}` | configPrintDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 208 | config | PUT | `/config/print/{id}` | configPrintUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 209 | config | GET | `/config/settings` | configSettingsList | ok | 200 object(products,general,currencies,shipment) |
| 210 | config | PUT | `/config/settings/companies` | configSettingsUpdateCompanies | needs-params | не вызывался: метод записи (режим только чтение) |
| 211 | config | PUT | `/config/settings/currencies` | configSettingsUpdateCurrencies | needs-params | не вызывался: метод записи (режим только чтение) |
| 212 | config | PUT | `/config/settings/delivery_status_toggles` | configSettingsUpdateDeliveryStatusToggles | needs-params | не вызывался: метод записи (режим только чтение) |
| 213 | config | PUT | `/config/settings/external_integrations` | configSettingsUpdateExternalIntegrations | needs-params | не вызывался: метод записи (режим только чтение) |
| 214 | config | PUT | `/config/settings/general` | configSettingsUpdateGeneral | needs-params | не вызывался: метод записи (режим только чтение) |
| 215 | config | PUT | `/config/settings/leads` | configSettingsUpdateLeads | needs-params | не вызывался: метод записи (режим только чтение) |
| 216 | config | PUT | `/config/settings/loyalty_programs` | configSettingsUpdateLoyaltyPrograms | needs-params | не вызывался: метод записи (режим только чтение) |
| 217 | config | PUT | `/config/settings/manufacturing` | configSettingsUpdateManufacturing | needs-params | не вызывался: метод записи (режим только чтение) |
| 218 | config | PUT | `/config/settings/notifications` | configSettingsUpdateNotifications | needs-params | не вызывался: метод записи (режим только чтение) |
| 219 | config | PUT | `/config/settings/orders` | configSettingsUpdateOrders | needs-params | не вызывался: метод записи (режим только чтение) |
| 220 | config | PUT | `/config/settings/products` | configSettingsUpdateProducts | needs-params | не вызывался: метод записи (режим только чтение) |
| 221 | config | PUT | `/config/settings/shipment` | configSettingsUpdateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 222 | config | PUT | `/config/settings/suppliers` | configSettingsUpdateSuppliers | needs-params | не вызывался: метод записи (режим только чтение) |
| 223 | config | GET | `/config/static` | configStaticList | ok | 200 object(timezones,currencies,units) |
| 224 | config | POST | `/config/surveys/{survey}` | configSurveysStoreResult | needs-params | не вызывался: метод записи (режим только чтение) |
| 225 | conversations | GET | `/conversations` | conversationsList | ok | 200 object(current_page,data,first_page_url,from) |
| 226 | conversations | POST | `/conversations` | conversationsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 227 | conversations | GET | `/conversations/by-channel/{channel_id}/stats` | conversationsByChannelStats | needs-params | не вызывался: path-параметр в маршруте |
| 228 | conversations | GET | `/conversations/by-client/{client_id}` | conversationsByClient | needs-params | не вызывался: path-параметр в маршруте |
| 229 | conversations | GET | `/conversations/by-contact/{contact_id}` | conversationsByContact | needs-params | не вызывался: path-параметр в маршруте |
| 230 | conversations | GET | `/conversations/by-phone` | conversationsByPhone | ok | 200 list[0] |
| 231 | conversations | GET | `/conversations/channels` | conversationsChannelsList | ok | 200 list[0] |
| 232 | conversations | POST | `/conversations/channels` | conversationsChannelsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 233 | conversations | GET | `/conversations/channels/marketplace` | conversationsChannelsMarketplace | ok | 200 list[0] |
| 234 | conversations | DELETE | `/conversations/channels/{id}` | conversationsChannelsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 235 | conversations | PUT | `/conversations/channels/{id}` | conversationsChannelsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 236 | conversations | POST | `/conversations/channels/{id}/extend-rate` | conversationsChannelsExtendRate | needs-params | не вызывался: метод записи (режим только чтение) |
| 237 | conversations | GET | `/conversations/messages/by_client/{id}` | conversationsMessagesByClient | needs-params | не вызывался: path-параметр в маршруте |
| 238 | conversations | GET | `/conversations/messages/by_lead/{id}` | conversationsMessagesByLead | needs-params | не вызывался: path-параметр в маршруте |
| 239 | conversations | POST | `/conversations/private-viber/info` | conversationsPrivateViberInfo | needs-params | не вызывался: метод записи (режим только чтение) |
| 240 | conversations | POST | `/conversations/private-viber/initialize` | conversationsPrivateViberInitialize | needs-params | не вызывался: метод записи (режим только чтение) |
| 241 | conversations | POST | `/conversations/private-viber/{session}/activate` | conversationsPrivateViberActivate | needs-params | не вызывался: метод записи (режим только чтение) |
| 242 | conversations | GET | `/conversations/private-viber/{session}/check` | conversationsPrivateViberCheck | needs-params | не вызывался: path-параметр в маршруте |
| 243 | conversations | POST | `/conversations/private-whatsapp/info` | conversationsPrivateWhatsappInfo | needs-params | не вызывался: метод записи (режим только чтение) |
| 244 | conversations | POST | `/conversations/private-whatsapp/initialize` | conversationsPrivateWhatsappInitialize | needs-params | не вызывался: метод записи (режим только чтение) |
| 245 | conversations | POST | `/conversations/private-whatsapp/{session}/activate` | conversationsPrivateWhatsappActivate | needs-params | не вызывался: метод записи (режим только чтение) |
| 246 | conversations | GET | `/conversations/private-whatsapp/{session}/check` | conversationsPrivateWhatsappCheck | needs-params | не вызывался: path-параметр в маршруте |
| 247 | conversations | GET | `/conversations/tags` | conversationsTagsIndex | ok | 200 list[0] |
| 248 | conversations | POST | `/conversations/tags` | conversationsTagsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 249 | conversations | DELETE | `/conversations/tags/{tag}` | conversationsTagsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 250 | conversations | PATCH | `/conversations/tags/{tag}` | conversationsTagsUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 251 | conversations | PUT | `/conversations/tags/{tag}` | conversationsTagsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 252 | conversations | GET | `/conversations/telegram-client/{session}/validate` | conversationsTelegramClientValidate | needs-params | не вызывался: path-параметр в маршруте |
| 253 | conversations | GET | `/conversations/tickets/{ticket_id}` | conversationsTicketsView | needs-params | не вызывался: path-параметр в маршруте |
| 254 | conversations | GET | `/conversations/unread` | conversationsUnread | ok | 200 list[0] |
| 255 | conversations | GET | `/conversations/{id}` | conversationsView | needs-params | не вызывался: path-параметр в маршруте |
| 256 | conversations | PUT | `/conversations/{id}` | conversationsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 257 | conversations | GET | `/conversations/{id}/messages` | conversationsMessagesList | needs-params | не вызывался: path-параметр в маршруте |
| 258 | conversations | POST | `/conversations/{id}/messages` | conversationsMessagesReply | needs-params | не вызывался: метод записи (режим только чтение) |
| 259 | conversations | GET | `/conversations/{id}/messages/for_message/{message_id}` | conversationsMessagesForMessage | needs-params | не вызывался: path-параметр в маршруте |
| 260 | conversations | GET | `/conversations/{id}/messages/for_ticket/{ticket_id}` | conversationsMessagesForTicket | needs-params | не вызывался: path-параметр в маршруте |
| 261 | conversations | DELETE | `/conversations/{id}/messages/{message_id}` | conversationsMessagesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 262 | conversations | PUT | `/conversations/{id}/messages/{message_id}` | conversationsMessagesEdit | needs-params | не вызывался: метод записи (режим только чтение) |
| 263 | conversations | POST | `/conversations/{id}/messages/{message_id}/reaction` | conversationsMessagesReaction | needs-params | не вызывался: метод записи (режим только чтение) |
| 264 | conversations | POST | `/conversations/{id}/tags` | conversationsSyncTags | needs-params | не вызывался: метод записи (режим только чтение) |
| 265 | conversations | POST | `/conversations/{id}/tags/{tag}` | conversationsAttachTag | needs-params | не вызывался: метод записи (режим только чтение) |
| 266 | conversations | POST | `/conversations/{id}/tags/{tag}/detach` | conversationsDetachTag | needs-params | не вызывался: метод записи (режим только чтение) |
| 267 | delivery | GET | `/delivery/addresses/suggest` | deliveryAddressingSuggest | server-error | 500 с query=Київ и q=Київ; вероятно не настроен провайдер адресов |
| 268 | delivery | GET | `/delivery/delivery-services` | deliveryDeliveryServicesIndex | ok | 200 object(data) |
| 269 | delivery | POST | `/delivery/delivery-services` | deliveryDeliveryServicesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 270 | delivery | DELETE | `/delivery/delivery-services/{delivery_service}` | deliveryDeliveryServicesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 271 | delivery | PATCH | `/delivery/delivery-services/{delivery_service}` | deliveryDeliveryServicesUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 272 | delivery | PUT | `/delivery/delivery-services/{delivery_service}` | deliveryDeliveryServicesUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 273 | delivery | POST | `/delivery/dhl_express/create-shipment/{order}` | deliveryDhlExpressCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 274 | delivery | GET | `/delivery/dhl_express/print/{order}` | deliveryDhlExpressPrint | needs-params | не вызывался: path-параметр в маршруте |
| 275 | delivery | POST | `/delivery/dhl_express/shipment-price/{order}` | deliveryDhlExpressShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 276 | delivery | POST | `/delivery/fedex/create-shipment/{order}` | deliveryFedexCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 277 | delivery | GET | `/delivery/fedex/print/{order}` | deliveryFedexPrint | needs-params | не вызывался: path-параметр в маршруте |
| 278 | delivery | POST | `/delivery/fedex/shipment-price/{order}` | deliveryFedexShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 279 | delivery | POST | `/delivery/fedex/upload-image` | deliveryFedexUploadImage | needs-params | не вызывался: метод записи (режим только чтение) |
| 280 | delivery | POST | `/delivery/meest_express/create-shipment/{order}` | deliveryMeestExpressCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 281 | delivery | GET | `/delivery/meest_express/location` | deliveryMeestExpressSearchLocation | ok | 200 list[0] |
| 282 | delivery | GET | `/delivery/meest_express/print/{order}` | deliveryMeestExpressPrint | needs-params | не вызывался: path-параметр в маршруте |
| 283 | delivery | POST | `/delivery/meest_express/shipment-price/{order}` | deliveryMeestExpressShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 284 | delivery | GET | `/delivery/meest_express/warehouse` | deliveryMeestExpressSearchWarehouse | ok | 200 list[0] |
| 285 | delivery | POST | `/delivery/novaposhta/create-shipment/{order}` | deliveryNovaposhtaCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 286 | delivery | GET | `/delivery/novaposhta/location` | deliveryNovaposhtaSearchLocation | ok | 200 list[0] |
| 287 | delivery | GET | `/delivery/novaposhta/print/{order}` | deliveryNovaposhtaPrint | needs-params | не вызывался: path-параметр в маршруте |
| 288 | delivery | POST | `/delivery/novaposhta/shipment-price/{order}` | deliveryNovaposhtaShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 289 | delivery | GET | `/delivery/novaposhta/street` | deliveryNovaposhtaSearchStreet | ok | 200 list[0] |
| 290 | delivery | GET | `/delivery/novaposhta/warehouse` | deliveryNovaposhtaSearchWarehouse | ok | 200 list[0] |
| 291 | delivery | POST | `/delivery/novaposhta_international/create-shipment/{order}` | deliveryNovaposhtaInternationalCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 292 | delivery | GET | `/delivery/novaposhta_international/print/{order}` | deliveryNovaposhtaInternationalPrint | needs-params | не вызывался: path-параметр в маршруте |
| 293 | delivery | POST | `/delivery/novaposhta_international/shipment-price/{order}` | deliveryNovaposhtaInternationalShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 294 | delivery | GET | `/delivery/novaposhta_international/warehouse` | deliveryNovaposhtaInternationalSearchWarehouse | ok | 200 list[0] |
| 295 | delivery | GET | `/delivery/prep-centers` | deliveryPrepCentersIndex | ok | 200 object(current_page,data,first_page_url,from) |
| 296 | delivery | POST | `/delivery/prep-centers` | deliveryPrepCentersCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 297 | delivery | GET | `/delivery/prep-centers/active` | deliveryPrepCentersActive | ok | 200 list[0] |
| 298 | delivery | POST | `/delivery/prep-centers/warehouses` | deliveryPrepCentersWarehouses | needs-params | не вызывался: метод записи (режим только чтение) |
| 299 | delivery | DELETE | `/delivery/prep-centers/{id}` | deliveryPrepCentersDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 300 | delivery | PUT | `/delivery/prep-centers/{id}` | deliveryPrepCentersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 301 | delivery | GET | `/delivery/prep-centers/{id}/check` | deliveryPrepCentersCheck | needs-params | не вызывался: path-параметр в маршруте |
| 302 | delivery | GET | `/delivery/prep-centers/{id}/materials` | deliveryPrepCentersMaterials | needs-params | не вызывался: path-параметр в маршруте |
| 303 | delivery | POST | `/delivery/prep-centers/{id}/offers/{order_id}` | deliveryPrepCentersOffers | needs-params | не вызывался: метод записи (режим только чтение) |
| 304 | delivery | GET | `/delivery/prep-centers/{id}/products` | deliveryPrepCentersProducts | needs-params | не вызывался: path-параметр в маршруте |
| 305 | delivery | POST | `/delivery/prep-centers/{id}/send/{order_id}` | deliveryPrepCentersSend | needs-params | не вызывался: метод записи (режим только чтение) |
| 306 | delivery | GET | `/delivery/prep-centers/{id}/sender` | deliveryPrepCentersSender | needs-params | не вызывался: path-параметр в маршруте |
| 307 | delivery | POST | `/delivery/prep-centers/{prepCenterRequest}/tracking` | deliveryPrepCentersTracking | needs-params | не вызывался: метод записи (режим только чтение) |
| 308 | delivery | POST | `/delivery/rozetka/create-shipment/{order}` | deliveryRozetkaCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 309 | delivery | GET | `/delivery/rozetka/init/{source}` | deliveryRozetkaInit | needs-params | не вызывался: path-параметр в маршруте |
| 310 | delivery | GET | `/delivery/rozetka/print/{order}` | deliveryRozetkaPrint | needs-params | не вызывался: path-параметр в маршруте |
| 311 | delivery | POST | `/delivery/rozetka_delivery/create-shipment/{order}` | deliveryRozetkaDeliveryCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 312 | delivery | GET | `/delivery/rozetka_delivery/location` | deliveryRozetkaDeliverySearchLocation | ok | 200 list[100] |
| 313 | delivery | GET | `/delivery/rozetka_delivery/print/{order}` | deliveryRozetkaDeliveryPrint | needs-params | не вызывался: path-параметр в маршруте |
| 314 | delivery | GET | `/delivery/rozetka_delivery/warehouse` | deliveryRozetkaDeliverySearchWarehouse | ok | 200 list[100] |
| 315 | delivery | GET | `/delivery/services/{id}/tracking/callback` | deliveryTrackingCallbackGet | needs-params | не вызывался: path-параметр в маршруте |
| 316 | delivery | POST | `/delivery/services/{id}/tracking/callback` | deliveryTrackingCallbackPost | needs-params | не вызывался: метод записи (режим только чтение) |
| 317 | delivery | GET | `/delivery/shipment-templates` | deliveryShipmentTemplatesIndex | ok | 200 list[0] |
| 318 | delivery | POST | `/delivery/shipment-templates` | deliveryShipmentTemplatesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 319 | delivery | DELETE | `/delivery/shipment-templates/{shipment_template}` | deliveryShipmentTemplatesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 320 | delivery | PATCH | `/delivery/shipment-templates/{shipment_template}` | deliveryShipmentTemplatesUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 321 | delivery | PUT | `/delivery/shipment-templates/{shipment_template}` | deliveryShipmentTemplatesUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 322 | delivery | POST | `/delivery/ukrposhta/create-shipment/{order}` | deliveryUkrposhtaCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 323 | delivery | GET | `/delivery/ukrposhta/location` | deliveryUkrposhtaSearchLocation | ok | 200 list[0] |
| 324 | delivery | GET | `/delivery/ukrposhta/print/{order}` | deliveryUkrposhtaPrint | needs-params | не вызывался: path-параметр в маршруте |
| 325 | delivery | POST | `/delivery/ukrposhta/shipment-price/{order}` | deliveryUkrposhtaShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 326 | delivery | GET | `/delivery/ukrposhta/warehouse` | deliveryUkrposhtaSearchWarehouse | needs-params | The given data was invalid. \| location_ref: Поле location ref обязательно для заполнения. |
| 327 | delivery | POST | `/delivery/ups/create-shipment/{order}` | deliveryUpsCreateShipment | needs-params | не вызывался: метод записи (режим только чтение) |
| 328 | delivery | GET | `/delivery/ups/print/{order}` | deliveryUpsPrint | needs-params | не вызывался: path-параметр в маршруте |
| 329 | delivery | POST | `/delivery/ups/shipment-price/{order}` | deliveryUpsShipmentPrice | needs-params | не вызывался: метод записи (режим только чтение) |
| 330 | demo | GET | `/demo/{email}` | systemAdminDemo | needs-params | не вызывался: path-параметр в маршруте |
| 331 | email | POST | `/email/{uuid}` | systemAdminReplaceEmail | needs-params | не вызывался: метод записи (режим только чтение) |
| 332 | file-storage | POST | `/file-storage` | storageUpload | needs-params | не вызывался: метод записи (режим только чтение) |
| 333 | file-storage | POST | `/file-storage/attach/{model}/{id}` | storageAttach | needs-params | не вызывался: метод записи (режим только чтение) |
| 334 | file-storage | POST | `/file-storage/attach/{model}/{id}/validate` | storageAttachValidate | needs-params | не вызывался: метод записи (режим только чтение) |
| 335 | file-storage | DELETE | `/file-storage/detach/{attachment}` | storageDetach | needs-params | не вызывался: метод записи (режим только чтение) |
| 336 | file-storage | GET | `/file-storage/media/download` | storageMediaDownload | needs-params | Missing url to download |
| 337 | file-storage | GET | `/file-storage/remote` | storageRemoteThumbnail | needs-params | Bad Request |
| 338 | file-storage | POST | `/file-storage/temp-upload/{group}` | storageTempUpload | needs-params | не вызывался: метод записи (режим только чтение) |
| 339 | file-storage | GET | `/file-storage/thumbnails/{path}` | storageThumbnail | needs-params | не вызывался: path-параметр в маршруте |
| 340 | file-storage | DELETE | `/file-storage/{file}` | storageDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 341 | file-storage | GET | `/file-storage/{file}` | storageDownload | needs-params | не вызывался: path-параметр в маршруте |
| 342 | file-storage | GET | `/file-storage/{file}/view` | storageView | needs-params | не вызывался: path-параметр в маршруте |
| 343 | finance | GET | `/finance/bills` | financeBillsList | ok | 200 list[0] |
| 344 | finance | POST | `/finance/bills` | financeBillsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 345 | finance | PUT | `/finance/bills/transfer` | financeBillsTransfer | needs-params | не вызывался: метод записи (режим только чтение) |
| 346 | finance | DELETE | `/finance/bills/{id}` | financeBillsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 347 | finance | PUT | `/finance/bills/{id}` | financeBillsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 348 | finance | PUT | `/finance/bills/{id}/balance-adjustment` | financeBillsBalanceAdjustment | needs-params | не вызывался: метод записи (режим только чтение) |
| 349 | finance | PUT | `/finance/bills/{id}/change-status` | financeBillsChangeStatus | needs-params | не вызывался: метод записи (режим только чтение) |
| 350 | finance | GET | `/finance/currency-rates` | financeCurrencyRatesList | ok | 200 list[1] |
| 351 | finance | POST | `/finance/currency-rates` | financeCurrencyRatesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 352 | finance | GET | `/finance/currency-rates/common` | financeCurrencyRatesCommon | ok | 200 object(AED,AFN,ALL,AMD) |
| 353 | finance | POST | `/finance/currency-rates/refresh` | financeCurrencyRatesRefresh | needs-params | не вызывался: метод записи (режим только чтение) |
| 354 | finance | GET | `/finance/expense-types` | financeExpenseTypesList | ok | 200 object(data) |
| 355 | finance | POST | `/finance/expense-types` | financeExpenseTypesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 356 | finance | DELETE | `/finance/expense-types/{expense_type}` | financeExpenseTypesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 357 | finance | PATCH | `/finance/expense-types/{expense_type}` | financeExpenseTypesUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 358 | finance | PUT | `/finance/expense-types/{expense_type}` | financeExpenseTypesUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 359 | finance | GET | `/finance/fiscal/{id}/callback` | financeFiscalsCallbackGet | needs-params | не вызывался: path-параметр в маршруте |
| 360 | finance | POST | `/finance/fiscal/{id}/callback` | financeFiscalsCallback | needs-params | не вызывался: метод записи (режим только чтение) |
| 361 | finance | GET | `/finance/fiscals` | financeFiscalsList | ok | 200 list[0] |
| 362 | finance | POST | `/finance/fiscals` | financeFiscalsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 363 | finance | POST | `/finance/fiscals/auth` | financeFiscalsAuth | needs-params | не вызывался: метод записи (режим только чтение) |
| 364 | finance | GET | `/finance/fiscals/fiscal/{payment}` | financeFiscalsCheck | needs-params | не вызывался: path-параметр в маршруте |
| 365 | finance | PUT | `/finance/fiscals/fiscal/{payment}` | financeFiscalsCancel | needs-params | не вызывался: метод записи (режим только чтение) |
| 366 | finance | DELETE | `/finance/fiscals/{id}` | financeFiscalsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 367 | finance | PUT | `/finance/fiscals/{id}` | financeFiscalsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 368 | finance | GET | `/finance/fiscals/{id}/print/{uuid}` | financeFiscalsPrint | needs-params | не вызывался: path-параметр в маршруте |
| 369 | finance | POST | `/finance/fiscals/{id}/{action}` | financeFiscalsShift | needs-params | не вызывался: метод записи (режим только чтение) |
| 370 | finance | POST | `/finance/fiscals/{register}/fiscal/{payment}` | financeFiscalsFiscalize | needs-params | не вызывался: метод записи (режим только чтение) |
| 371 | finance | GET | `/finance/payment-gateways` | financePaymentGatewaysList | ok | 200 list[0] |
| 372 | finance | POST | `/finance/payment-gateways` | financePaymentGatewaysStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 373 | finance | POST | `/finance/payment-gateways/novapay-business/init/accounts` | financePaymentGatewaysNovapayBusinessAccounts | needs-params | не вызывался: метод записи (режим только чтение) |
| 374 | finance | POST | `/finance/payment-gateways/novapay-business/init/auth` | financePaymentGatewaysNovapayBusinessAuth | needs-params | не вызывался: метод записи (режим только чтение) |
| 375 | finance | POST | `/finance/payment-gateways/novapay-business/init/clients` | financePaymentGatewaysNovapayBusinessClients | needs-params | не вызывался: метод записи (режим только чтение) |
| 376 | finance | DELETE | `/finance/payment-gateways/{id}` | financePaymentGatewaysDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 377 | finance | PUT | `/finance/payment-gateways/{id}` | financePaymentGatewaysUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 378 | finance | POST | `/finance/payment-gateways/{id}/drop_invoice/{payment_id}` | financePaymentGatewaysDropInvoice | needs-params | не вызывался: метод записи (режим только чтение) |
| 379 | finance | POST | `/finance/payment-gateways/{id}/invoice` | financePaymentGatewaysInvoice | needs-params | не вызывался: метод записи (режим только чтение) |
| 380 | finance | POST | `/finance/payment-gateways/{integration}/accounts` | financePaymentGatewaysAccounts | needs-params | не вызывался: метод записи (режим только чтение) |
| 381 | finance | GET | `/finance/payment-methods` | financePaymentMethodsList | ok | 200 object(data) |
| 382 | finance | POST | `/finance/payment-methods` | financePaymentMethodsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 383 | finance | DELETE | `/finance/payment-methods/{payment_method}` | financePaymentMethodsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 384 | finance | PATCH | `/finance/payment-methods/{payment_method}` | financePaymentMethodsUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 385 | finance | PUT | `/finance/payment-methods/{payment_method}` | financePaymentMethodsUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 386 | finance | GET | `/finance/payments` | financePaymentsList | server-error | 500 при пустых параметрах, limit, page, from/to, date_from/date_to, filter[]; стабильно 500 |
| 387 | finance | POST | `/finance/payments` | financePaymentsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 388 | finance | GET | `/finance/payments/config` | financePaymentsConfig | ok | 200 object(min,max,payments,expenses) |
| 389 | finance | POST | `/finance/payments/expenses` | financePaymentsExpensesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 390 | finance | PUT | `/finance/payments/{id}` | financePaymentsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 391 | finance | PUT | `/finance/payments/{id}/cancel` | financePaymentsCancel | needs-params | не вызывался: метод записи (режим только чтение) |
| 392 | finance | GET | `/finance/transactions` | financeTransactionsList | server-error | 500 при пустых параметрах, limit, page, from/to, date_from/date_to, filter[]; стабильно 500 |
| 393 | finance | GET | `/finance/transactions/config` | financeTransactionsConfig | ok | 200 object(date_min,date_max,min,max) |
| 394 | finance | GET | `/finance/transactions/unlinked` | financeTransactionsUnlinked | ok | 200 list[0] |
| 395 | finance | POST | `/finance/transactions/{id}/archive` | financeTransactionsArchive | needs-params | не вызывался: метод записи (режим только чтение) |
| 396 | finance | GET | `/finance/{id}/callback` | financePaymentGatewaysCallbackGet | needs-params | не вызывался: path-параметр в маршруте |
| 397 | finance | POST | `/finance/{id}/callback` | financePaymentGatewaysCallback | needs-params | не вызывался: метод записи (режим только чтение) |
| 398 | import | GET | `/import` | importList | ok | 200 object(current_page,data,first_page_url,from) |
| 399 | import | POST | `/import` | importParse | needs-params | не вызывался: метод записи (режим только чтение) |
| 400 | import | GET | `/import/preview` | importPreview | needs-params | The given data was invalid. \| file_id: Поле file id обязательно для заполнения. |
| 401 | import | POST | `/import/{id}` | importRevert | needs-params | не вызывался: метод записи (режим только чтение) |
| 402 | initialize | POST | `/initialize/{provider}` | systemOauthInitialize | needs-params | не вызывался: метод записи (режим только чтение) |
| 403 | leads | GET | `/leads` | leadsIndex | ok | 200 object(current_page,data,first_page_url,from); orderBy=created_at (+direction) 200, но orderBy=created_at:asc даёт 500 (сервер не валидирует формат) |
| 404 | leads | POST | `/leads` | leadsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 405 | leads | GET | `/leads/by-client/{client_id}` | leadsListByClient | needs-params | не вызывался: path-параметр в маршруте |
| 406 | leads | GET | `/leads/by-company/{company_id}` | leadsListByCompany | needs-params | не вызывался: path-параметр в маршруте |
| 407 | leads | GET | `/leads/by-contact/{contact_id}` | leadsListByContact | needs-params | не вызывался: path-параметр в маршруте |
| 408 | leads | GET | `/leads/identify` | leadsListByIdentify | needs-params | The given data was invalid. \| phone: Поле Телефон обязательно для заполнения, когда E-mail адрес не указано. \| email: Поле E-mail адрес обязательно для заполнения, когда Телефон не указано. |
| 409 | leads | POST | `/leads/merge/{from_id}/{to_id}` | leadsMerge | needs-params | не вызывался: метод записи (режим только чтение) |
| 410 | leads | GET | `/leads/pipelines` | leadsPipelinesList | needs-params | обязателен query-параметр leads=true\|false (без него 500), с leads=false 200 list[1] |
| 411 | leads | POST | `/leads/pipelines` | leadsPipelinesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 412 | leads | GET | `/leads/pipelines/desk` | leadsPipelinesDeskDefault | ok | 200 list[7] |
| 413 | leads | GET | `/leads/pipelines/desk/{id}` | leadsPipelinesDesk | needs-params | не вызывался: path-параметр в маршруте |
| 414 | leads | POST | `/leads/pipelines/reorder` | leadsPipelinesReorder | needs-params | не вызывался: метод записи (режим только чтение) |
| 415 | leads | DELETE | `/leads/pipelines/{id}` | leadsPipelinesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 416 | leads | PUT | `/leads/pipelines/{id}` | leadsPipelinesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 417 | leads | POST | `/leads/statuses` | leadsStatusesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 418 | leads | DELETE | `/leads/statuses/{id}` | leadsStatusesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 419 | leads | GET | `/leads/statuses/{id}` | leadsStatusesList | needs-params | не вызывался: path-параметр в маршруте |
| 420 | leads | PUT | `/leads/statuses/{id}` | leadsStatusesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 421 | leads | GET | `/leads/statuses/{id}/cards` | leadsStatusesCards | needs-params | не вызывался: path-параметр в маршруте |
| 422 | leads | PUT | `/leads/statuses/{id}/reorder` | leadsStatusesReorder | needs-params | не вызывался: метод записи (режим только чтение) |
| 423 | leads | GET | `/leads/{id}` | leadsShow | needs-params | не вызывался: path-параметр в маршруте |
| 424 | leads | PUT | `/leads/{id}` | leadsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 425 | leads | POST | `/leads/{id}/copy` | leadsCopy | needs-params | не вызывался: метод записи (режим только чтение) |
| 426 | leads | PUT | `/leads/{id}/order` | leadsComplete | needs-params | не вызывался: метод записи (режим только чтение) |
| 427 | leads | POST | `/leads/{id}/products` | leadsAddProduct | needs-params | не вызывался: метод записи (режим только чтение) |
| 428 | loyalty | GET | `/loyalty` | loyaltyProgramsList | ok | 200 list[0] |
| 429 | loyalty | POST | `/loyalty` | loyaltyProgramsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 430 | loyalty | GET | `/loyalty/client/{clientId}/by/source/{sourceId}` | loyaltyClientDiscount | needs-params | не вызывался: path-параметр в маршруте |
| 431 | loyalty | DELETE | `/loyalty/{id}` | loyaltyProgramsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 432 | loyalty | PUT | `/loyalty/{id}` | loyaltyProgramsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 433 | loyalty | PUT | `/loyalty/{id}/toggle` | loyaltyProgramsToggle | needs-params | не вызывался: метод записи (режим только чтение) |
| 434 | loyalty | POST | `/loyalty/{program}/levels` | loyaltyLevelsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 435 | loyalty | DELETE | `/loyalty/{program}/levels/{id}` | loyaltyLevelsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 436 | loyalty | PUT | `/loyalty/{program}/levels/{id}` | loyaltyLevelsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 437 | manufacturing | GET | `/manufacturing` | manufacturingIndex | ok | 200 object(current_page,data,first_page_url,from) |
| 438 | manufacturing | GET | `/manufacturing/new-count` | manufacturingNewCount | ok | 200 object(total) |
| 439 | manufacturing | PUT | `/manufacturing/viewed` | manufacturingViewed | needs-params | не вызывался: метод записи (режим только чтение) |
| 440 | manufacturing | GET | `/manufacturing/{id}` | manufacturingView | needs-params | не вызывался: path-параметр в маршруте |
| 441 | manufacturing | PUT | `/manufacturing/{id}` | manufacturingUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 442 | manufacturing | POST | `/manufacturing/{id}/split` | manufacturingSplit | needs-params | не вызывался: метод записи (режим только чтение) |
| 443 | manufacturing | GET | `/manufacturing/{parent_id}/children` | manufacturingChildren | needs-params | не вызывался: path-параметр в маршруте |
| 444 | orders | GET | `/orders` | ordersList | ok | 200 object(data,links,meta); любой orderBy (id, created_at) даёт 500, direction без orderBy работает |
| 445 | orders | POST | `/orders` | ordersCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 446 | orders | GET | `/orders/client/{client_id}` | ordersByClient | needs-params | не вызывался: path-параметр в маршруте |
| 447 | orders | GET | `/orders/client/{client_id}/details` | ordersByClientDetails | needs-params | не вызывался: path-параметр в маршруте |
| 448 | orders | GET | `/orders/company/{company_id}` | ordersByCompany | needs-params | не вызывался: path-параметр в маршруте |
| 449 | orders | GET | `/orders/groups` | ordersGroupsIndex | ok | 200 object(data) |
| 450 | orders | POST | `/orders/merge` | ordersMerge | needs-params | не вызывался: метод записи (режим только чтение) |
| 451 | orders | GET | `/orders/shipping-list` | ordersShippingListsList | ok | 200 object(current_page,data,first_page_url,from) |
| 452 | orders | GET | `/orders/shipping-list/orders/{id}` | ordersShippingListsByList | needs-params | не вызывался: path-параметр в маршруте |
| 453 | orders | DELETE | `/orders/shipping-list/{id}` | ordersShippingListsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 454 | orders | GET | `/orders/shipping-list/{id}` | ordersShippingListsShow | needs-params | не вызывался: path-параметр в маршруте |
| 455 | orders | POST | `/orders/shipping-list/{id}` | ordersShippingListsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 456 | orders | PUT | `/orders/shipping-list/{id}` | ordersShippingListsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 457 | orders | GET | `/orders/shipping-list/{id}/print` | ordersShippingListsPrint | needs-params | не вызывался: path-параметр в маршруте |
| 458 | orders | GET | `/orders/shipping-list/{id}/print-shipments` | ordersShippingListsPrintShipments | needs-params | не вызывался: path-параметр в маршруте |
| 459 | orders | GET | `/orders/statuses` | ordersStatusesIndex | ok | 200 object(data) |
| 460 | orders | POST | `/orders/statuses` | ordersStatusesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 461 | orders | POST | `/orders/statuses/reorder` | ordersReorder | needs-params | не вызывался: метод записи (режим только чтение) |
| 462 | orders | DELETE | `/orders/statuses/{status}` | ordersStatusesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 463 | orders | PATCH | `/orders/statuses/{status}` | ordersStatusesUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 464 | orders | PUT | `/orders/statuses/{status}` | ordersStatusesUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 465 | orders | POST | `/orders/sync` | ordersSourceSyncMissing | needs-params | не вызывался: метод записи (режим только чтение) |
| 466 | orders | GET | `/orders/tags` | ordersTagsIndex | ok | 200 object(data) |
| 467 | orders | POST | `/orders/tags` | ordersTagsStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 468 | orders | DELETE | `/orders/tags/{tag}` | ordersTagsDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 469 | orders | PATCH | `/orders/tags/{tag}` | ordersTagsUpdatePatch | needs-params | не вызывался: метод записи (режим только чтение) |
| 470 | orders | PUT | `/orders/tags/{tag}` | ordersTagsUpdatePut | needs-params | не вызывался: метод записи (режим только чтение) |
| 471 | orders | GET | `/orders/totals` | ordersTotals | ok | 200 list[0] |
| 472 | orders | GET | `/orders/{order_id}` | ordersView | needs-params | не вызывался: path-параметр в маршруте |
| 473 | orders | PUT | `/orders/{order_id}` | ordersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 474 | orders | PUT | `/orders/{order_id}/client` | ordersClientUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 475 | orders | POST | `/orders/{order_id}/discount` | ordersToggleDiscount | needs-params | не вызывался: метод записи (режим только чтение) |
| 476 | orders | GET | `/orders/{order_id}/loyalty` | ordersGetLoyalty | needs-params | не вызывался: path-параметр в маршруте |
| 477 | orders | POST | `/orders/{order_id}/products` | ordersProductsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 478 | orders | DELETE | `/orders/{order_id}/products/{product_id}` | ordersProductsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 479 | orders | PUT | `/orders/{order_id}/products/{product_id}` | ordersProductsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 480 | orders | POST | `/orders/{order_id}/products/{product_id}/copy` | ordersProductsCopy | needs-params | не вызывался: метод записи (режим только чтение) |
| 481 | orders | DELETE | `/orders/{order_id}/products/{product_id}/shipment-type` | ordersProductsShipmentTypeDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 482 | orders | GET | `/orders/{order_id}/products/{product_id}/shipment-type` | ordersProductsShipmentTypeIndex | needs-params | не вызывался: path-параметр в маршруте |
| 483 | orders | PUT | `/orders/{order_id}/products/{product_id}/shipment-type` | ordersProductsShipmentTypeStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 484 | orders | PUT | `/orders/{order_id}/source/mark-as-shipped` | ordersSourceMarkAsShipped | needs-params | не вызывался: метод записи (режим только чтение) |
| 485 | orders | PUT | `/orders/{order_id}/source/sync` | ordersSourceSyncExisting | needs-params | не вызывался: метод записи (режим только чтение) |
| 486 | orders | POST | `/orders/{order_id}/status/{status_id}` | ordersAttachStatus | needs-params | не вызывался: метод записи (режим только чтение) |
| 487 | orders | POST | `/orders/{order}/assigned` | ordersSyncAssigned | needs-params | не вызывался: метод записи (режим только чтение) |
| 488 | orders | POST | `/orders/{order}/copy` | ordersCopy | needs-params | не вызывался: метод записи (режим только чтение) |
| 489 | orders | GET | `/orders/{order}/expenses` | ordersExpenses | needs-params | не вызывался: path-параметр в маршруте |
| 490 | orders | PUT | `/orders/{order}/marketing` | ordersUtmTags | needs-params | не вызывался: метод записи (режим только чтение) |
| 491 | orders | PUT | `/orders/{order}/shipping` | ordersShipping | needs-params | не вызывался: метод записи (режим только чтение) |
| 492 | orders | GET | `/orders/{order}/shipping-history` | ordersShippingHistory | needs-params | не вызывался: path-параметр в маршруте |
| 493 | orders | POST | `/orders/{order}/shipping-history/sync` | ordersShippingHistorySync | needs-params | не вызывался: метод записи (режим только чтение) |
| 494 | orders | POST | `/orders/{order}/tags` | ordersSyncTags | needs-params | не вызывался: метод записи (режим только чтение) |
| 495 | orders | POST | `/orders/{order}/tags/{tag}` | ordersAttachTag | needs-params | не вызывался: метод записи (режим только чтение) |
| 496 | orders | POST | `/orders/{order}/tags/{tag}/detach` | ordersDetachTag | needs-params | не вызывался: метод записи (режим только чтение) |
| 497 | orders | DELETE | `/orders/{order}/tracking` | ordersDeleteTrackingCode | needs-params | не вызывался: метод записи (режим только чтение) |
| 498 | orders | POST | `/orders/{order}/tracking/add` | ordersAddTrackingCode | needs-params | не вызывался: метод записи (режим только чтение) |
| 499 | rate_channel | POST | `/rate_channel/{uuid}/{channel_id}` | systemAdminRateChannel | needs-params | не вызывался: метод записи (режим только чтение) |
| 500 | redirect | GET | `/redirect/{provider}/{session_id}` | systemOauthRedirect | needs-params | не вызывался: path-параметр в маршруте |
| 501 | restore_tenant | POST | `/restore_tenant/{id}` | systemAdminRestoreTenant | needs-params | не вызывался: метод записи (режим только чтение) |
| 502 | result | GET | `/result/{provider}/{session_id}` | systemOauthResult | needs-params | не вызывался: path-параметр в маршруте |
| 503 | sources | GET | `/sources` | sourcesList | ok | 200 list[9] |
| 504 | sources | POST | `/sources` | sourcesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 505 | sources | POST | `/sources/config/shop-listing` | sourcesConfigShopListing | needs-params | не вызывался: метод записи (режим только чтение) |
| 506 | sources | POST | `/sources/config/shop-listing/{source_id}` | sourcesConfigShopListingBySource | needs-params | не вызывался: метод записи (режим только чтение) |
| 507 | sources | POST | `/sources/leads/{driver}/forms` | sourcesLeadsForms | needs-params | не вызывался: метод записи (режим только чтение) |
| 508 | sources | POST | `/sources/leads/{driver}/forms/{form_id}/fields` | sourcesLeadsFields | needs-params | не вызывался: метод записи (режим только чтение) |
| 509 | sources | POST | `/sources/leads/{driver}/pages` | sourcesLeadsPages | needs-params | не вызывался: метод записи (режим только чтение) |
| 510 | sources | POST | `/sources/preauthorize/{driver}` | sourcesConfigPreauthorize | needs-params | не вызывался: метод записи (режим только чтение) |
| 511 | sources | DELETE | `/sources/{source_id}` | sourcesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 512 | sources | PUT | `/sources/{source_id}` | sourcesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 513 | stocks | GET | `/stocks` | stocksList | ok | 200 object(current_page,data,first_page_url,from) |
| 514 | stocks | GET | `/stocks/filters_data` | stocksFiltersData | ok | 200 object(in_reserve,available_quantity) |
| 515 | stocks | GET | `/stocks/inventories/{movement}` | stocksInventoriesList | needs-params | не вызывался: path-параметр в маршруте |
| 516 | stocks | POST | `/stocks/inventory/batch` | stocksReceiptCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 517 | stocks | POST | `/stocks/inventory/batch/{movement_id}` | stocksReceiptUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 518 | stocks | POST | `/stocks/inventory/revert/{movement_id}` | stocksMovementCancel | needs-params | не вызывался: метод записи (режим только чтение) |
| 519 | stocks | POST | `/stocks/inventory/stocktaking` | stocksStocktakingCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 520 | stocks | POST | `/stocks/inventory/stocktaking/{movement_id}` | stocksStocktakingUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 521 | stocks | POST | `/stocks/inventory/transfer` | stocksTransferCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 522 | stocks | POST | `/stocks/inventory/transfer/{movement_id}` | stocksTransferUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 523 | stocks | GET | `/stocks/movements` | stocksMovementsList | ok | 200 object(current_page,data,first_page_url,from) |
| 524 | stocks | GET | `/stocks/movements/{movement_id}` | stocksMovementsView | needs-params | не вызывался: path-параметр в маршруте |
| 525 | stocks | GET | `/stocks/stat` | stocksStat | ok | 200 object(quantity,purchased_price,price) |
| 526 | stocks | GET | `/stocks/warehouses` | stocksWarehousesList | ok | 200 object(data) |
| 527 | stocks | POST | `/stocks/warehouses` | stocksWarehousesStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 528 | stocks | DELETE | `/stocks/warehouses/{id}` | stocksWarehousesDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 529 | stocks | POST | `/stocks/warehouses/{id}` | stocksWarehousesDeactivate | needs-params | не вызывался: метод записи (режим только чтение) |
| 530 | stocks | PUT | `/stocks/warehouses/{id}` | stocksWarehousesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 531 | stocks | GET | `/stocks/{offer_id}/history` | stocksHistory | needs-params | не вызывался: path-параметр в маршруте |
| 532 | suppliers | GET | `/suppliers` | suppliersIndex | ok | 200 object(current_page,data,first_page_url,from) |
| 533 | suppliers | POST | `/suppliers` | suppliersStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 534 | suppliers | DELETE | `/suppliers/{id}` | suppliersDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 535 | suppliers | GET | `/suppliers/{id}` | suppliersShow | needs-params | не вызывался: path-параметр в маршруте |
| 536 | suppliers | PUT | `/suppliers/{id}` | suppliersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 537 | suppliers | GET | `/suppliers/{id}/orders` | suppliersOrders | needs-params | не вызывался: path-параметр в маршруте |
| 538 | sync | GET | `/sync` | systemAdminSync | not-found | 404: маршрут systemAdminSync принадлежит другому base URL (админ-клиент), не корню API тенанта |
| 539 | tasks | GET | `/tasks` | tasksIndex | ok | 200 list[0]; orderBy=created_at (+direction) 200 |
| 540 | tasks | POST | `/tasks` | tasksStore | needs-params | не вызывался: метод записи (режим только чтение) |
| 541 | tasks | GET | `/tasks/expired-count` | tasksExpiredCount | ok | 200 object(count) |
| 542 | tasks | GET | `/tasks/search` | tasksSearch | ok | 200 object(current_page,data,first_page_url,from) |
| 543 | tasks | DELETE | `/tasks/{id}` | tasksDestroy | needs-params | не вызывался: метод записи (режим только чтение) |
| 544 | tasks | GET | `/tasks/{id}` | tasksView | needs-params | не вызывался: path-параметр в маршруте |
| 545 | tasks | PUT | `/tasks/{id}` | tasksUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 546 | tasks | GET | `/tasks/{type}/{id}` | tasksTasked | needs-params | не вызывался: path-параметр в маршруте |
| 547 | tenant | POST | `/tenant/backup` | tenantBackup | needs-params | не вызывался: метод записи (режим только чтение) |
| 548 | tenant | GET | `/tenant/ping` | tenantPing | ok | 204 empty; тело пустое, это норма для ping |
| 549 | tenant | POST | `/tenant/restore` | tenantRestore | needs-params | не вызывался: метод записи (режим только чтение) |
| 550 | tenant | GET | `/tenant/user-info/{code}` | tenantUserInfo | needs-params | не вызывался: path-параметр в маршруте |
| 551 | test-api | POST | `/test-api/channels/create` | testApiChannelsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 552 | test-api | POST | `/test-api/contacts/create` | testApiContactsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 553 | test-api | POST | `/test-api/conversations/create` | testApiConversationsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 554 | test-api | POST | `/test-api/messages/create` | testApiMessagesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 555 | test-api | POST | `/test-api/mock/messages/received` | testApiMockMessagesReceived | needs-params | не вызывался: метод записи (режим только чтение) |
| 556 | test-api | POST | `/test-api/payments/external/create` | testApiPaymentsExternalCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 557 | toggle_api_token | POST | `/toggle_api_token/{uuid}` | systemAdminToggleApiToken | needs-params | не вызывался: метод записи (режим только чтение) |
| 558 | users | GET | `/users` | usersList | ok | 200 list[3]; любой orderBy (id, first_name) даёт 500, direction без orderBy работает |
| 559 | users | POST | `/users` | usersCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 560 | users | GET | `/users/permissions` | usersPermissionsList | ok | 200 list[42] |
| 561 | users | GET | `/users/roles` | usersRolesList | ok | 200 list[7] |
| 562 | users | POST | `/users/roles` | usersRolesCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 563 | users | DELETE | `/users/roles/{id}` | usersRolesDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 564 | users | PUT | `/users/roles/{id}` | usersRolesUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 565 | users | PUT | `/users/{id}` | usersUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 566 | widgets | GET | `/widgets` | widgetsList | ok | 200 list[0] |
| 567 | widgets | POST | `/widgets` | widgetsCreate | needs-params | не вызывался: метод записи (режим только чтение) |
| 568 | widgets | DELETE | `/widgets/{id}` | widgetsDelete | needs-params | не вызывался: метод записи (режим только чтение) |
| 569 | widgets | GET | `/widgets/{id}` | widgetsView | needs-params | не вызывался: path-параметр в маршруте |
| 570 | widgets | PUT | `/widgets/{id}` | widgetsUpdate | needs-params | не вызывался: метод записи (режим только чтение) |
| 571 | widgets | PUT | `/widgets/{id}/toggle` | widgetsToggle | needs-params | не вызывался: метод записи (режим только чтение) |
| 572 | {uuid} | GET | `/{uuid}` | systemAdminTenant | needs-params | не вызывался: path-параметр в маршруте |

## Оговорки

- В `endpoints.json` нет поля `group`, есть `file` (имя chunk-файла). Группа выведена как первый сегмент пути, как это делает `endpoints_catalog.py`.
- Каталог собран из бандла одной выборкой и смешивает два axios-клиента (основной API и админ-клиент): у 15 маршрутов `systemAdmin*` / `systemOauth*` путь записан от корня без своего base URL. Для `/sync` это подтверждено 404.
- Валидационные сообщения API приходят на русском и содержат `|`, в таблице они экранированы.
- Данные не изменялись: ни одного POST/PUT/PATCH/DELETE запроса на этом прогоне не было.
