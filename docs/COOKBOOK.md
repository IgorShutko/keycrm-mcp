# COOKBOOK: рецепты на Python для KeyCRM

Готовые скрипты через `keycrm_client.py`. Все рецепты безопасны: чтение, создание, обновление, отчёты и выгрузки. Удаление - только задачи, клиента или заказа по явному id.

Что нельзя делать через API: удалять карточки воронки. Подробности и инцидент 01.11.2026 - в [INCIDENT.md](INCIDENT.md) и в начале [API_REFERENCE.md](API_REFERENCE.md).

## Как запускать

Все примеры рассчитаны на venv проекта. Заголовок каждого скрипта:

```python
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJ = r"C:\path\to\keycrm-mcp"
sys.path.insert(0, PROJ)

from keycrm_client import client, dumps
from server import audit as crm_audit, report as crm_report
from tools_files import files as crm_files

def report_data(**kwargs):
    """Вызвать report() из MCP-сервера и вернуть его data."""
    return json.loads(crm_report(**kwargs))["data"]

def audit_data(**kwargs):
    """Вызвать audit() из MCP-сервера и вернуть его data."""
    return json.loads(crm_audit(**kwargs))["data"]

def files_data(**kwargs):
    """Вызвать files() из tools_files и вернуть его data."""
    return json.loads(crm_files(**kwargs))["data"]

c = client()
```

`report`, `audit` и `files` - те же функции, что отдают MCP-инструменты, только вызываются напрямую и возвращают JSON-строку. Рецепты 12, 13 и 20 используют их вместо ручных циклов: логика уже живёт в сервере, дублировать её не нужно.

Запуск:

```powershell
cd C:\path\to\keycrm-mcp
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe my_recipe.py
```

`.env` подхватывается автоматически из папки проекта. Вывод в консоли Windows может выглядеть кракозябрами: это кодировка терминала, данные в UTF-8 корректны.

Чтение проверено на живом аккаунте: рецепты 1-4 и 9-16 прогнаны 2026-11-01, документы в рецепте 18 - 2026-11-02, история в рецепте 20 - 2026-11-02, цифры в тексте - их вывод. Создание и обновление (рецепты 5-8) сверены с кодом сервера и рабочим телом API, безопасное удаление (рецепт 17) проверять только на своём тестовом объекте. Рецепт 19 (файлы) живым прогоном не подтверждён: на аккаунте 0 заказов. Перед первым запуском на проде сделайте `crm_snapshot`.

---

## 1. Проверить связь и лимиты

```python
profile = c.internal("GET", "/auth/profile")
api_client = c.internal("GET", "/config/api-client")
orders = c.official("GET", "/order", params={"limit": 1})

print("аккаунт:", c.domain)
print("пользователь:", profile.get("full_name"), "владелец:", profile.get("is_owner"))
print("API-клиент:", api_client.get("name"), "лимит:", api_client.get("request_limit"))
print("заказов в аккаунте:", orders.get("total"))
```


То же через CLI:

```powershell
.\.venv\Scripts\python.exe crm_cli.py status
```

## 2. Снимок аккаунта перед записью

Повторяет `crm_snapshot` из MCP-сервера: локальный JSON, в CRM ничего не меняет.

```python
from pathlib import Path

base = Path(PROJ) / "backups"
base.mkdir(parents=True, exist_ok=True)

cards = c.internal_pages("/leads", {"per_page": 50}, max_items=2000, page_size=50)
orders = c.official_pages("/order", {}, max_items=500)
pipelines = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
pipelines = pipelines.get("data") if isinstance(pipelines, dict) else pipelines

snapshot = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "domain": c.domain,
    "counts": {"cards": len(cards), "orders": len(orders)},
    "cards": cards,
    "orders": orders,
    "products": c.internal("GET", "/catalog/products", params={"per_page": 50}),
    "clients": c.internal("GET", "/clients", params={"per_page": 50}),
    "users": c.internal("GET", "/users"),
    "sources": c.internal("GET", "/sources", params={"users": 0}),
    "pipelines": pipelines,
    "order_statuses": c.internal("GET", "/orders/statuses", params={"with_disabled": 1}),
    "settings": c.internal("GET", "/config/settings/"),
}

path = base / f"crm_snapshot_{datetime.now():%Y%m%d_%H%M%S}.json"
path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(path, path.stat().st_size, "bytes")
```

Снимок не содержит вложений файлов и истории изменений. Папку `backups/` не коммитить.

## 3. Справочники: статусы, источники, воронки, команда

```python
def as_list(payload):
    """API отдаёт то список, то конверт {"data": [...]}; приводим к списку."""
    if isinstance(payload, dict):
        return payload.get("data") or []
    return payload or []

order_statuses = as_list(c.internal("GET", "/orders/statuses"))
order_groups = as_list(c.internal("GET", "/orders/groups"))
sources = as_list(c.internal("GET", "/sources", params={"users": 0}))
users = as_list(c.internal("GET", "/users"))
pipelines = as_list(c.internal("GET", "/leads/pipelines", params={"leads": "false"}))

print("статусов заказов:", len(order_statuses))
print("групп статусов:", len(order_groups))
print("источников:", len(sources))
print("пользователей:", len(users))

for p in pipelines:
    statuses = as_list(c.internal("GET", f"/leads/statuses/{p['id']}"))
    final = sum(1 for s in statuses if s.get("is_final"))
    print(f"воронка {p['id']} {p['title']}: статусов {len(statuses)}, финальных {final}")
```


`/leads/pipelines` без параметра `leads` отдаёт 500, поэтому `params={"leads": "false"}` обязателен.

## 4. Найти карточку по телефону

`/leads/identify` на этом аккаунте вернул пусто даже для существующего телефона, поэтому ищем перебором карточек. Телефон контакта заполнен не всегда: у части карточек он лежит в `manager_comment`.

```python
def digits(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())

def find_cards_by_phone(phone, max_items=2000):
    target = digits(phone)
    cards = c.internal_pages("/leads", {"per_page": 50}, max_items=max_items, page_size=50)
    hits = []
    for card in cards:
        contact_phone = digits((card.get("contact") or {}).get("phone"))
        comment = digits(card.get("manager_comment"))
        if target and (target in contact_phone or target in comment):
            hits.append(card)
    return hits

for card in find_cards_by_phone("+380501234567"):
    print(card["id"], card.get("status_id"), card.get("title"), card.get("manager_comment", "")[:80])
```

Карточки в выдаче `internal_pages("/leads")` содержат вложенный `contact` (с `phone`) и `manager_comment`. Список отдаёт по 15 на страницу, если не передать `per_page`.

## 5. Создать задачу

```python
me = c.internal("GET", "/auth/profile")
body = {
    "name": "Позвонить по заявке",
    "priority": 1,
    "type": "task",
    "description": "Уточнить бюджет и сроки",
    "status": "open",
    "scheduled_at": "2026-11-05T10:00:00.000Z",
    "assigned_to_id": me["id"],
    "tasked": None,
    "attachments": [],
    "period": {"time": 0, "duration": "days"},
    "checklist": [],
    "settings": {"allow_editing": False},
}
task = c.internal("POST", "/tasks", body=body)
print("создана задача", task.get("id"))
```

Список задач идёт через `/tasks/search`, не через `/tasks`:

```python
params = {"per_page": 20, "page": 1, "filters[tasks]": "own", "filters[tab]": "actual"}
rows = c.internal("GET", "/tasks/search", params=params).get("data", [])
for t in rows:
    print(t["id"], t.get("name"), t.get("status"), t.get("scheduled_at"))
```

## 6. Завершить или удалить задачу

```python
def complete_task(task_id):
    return c.internal("PUT", f"/tasks/{task_id}", body={"id": task_id, "status": "done"})

def delete_task(task_id):
    return c.internal("DELETE", f"/tasks/{task_id}")

# сначала убедиться, что это нужная задача
task = c.internal("GET", f"/tasks/{123}")
print(task.get("name"))
# complete_task(123)
# delete_task(123)
```

`complete` и `delete` безопасны: работают по одному id. Перед удалением прочитать задачу и проверить название.

## 7. Создать карточку воронки

Создание работает и проверено. Удаление карточек через API заблокировано, поэтому создавайте только то, что действительно нужно.

```python
lead_body = {
    "title": "Заявка с сайта",
    "pipeline_id": 1,
    "status_id": 1,
    "source_id": 1,
    "communicate_at": "2026-11-10 12:00:00",
    "currency_code": "UAH",
    "manager_comment": "Создано скриптом",
    "contact": {"full_name": "Иван Петренко", "phone": "+380501112299"},
}
lead = c.internal("POST", "/leads", body=lead_body)
print("карточка", lead.get("id"), lead.get("status_id"))
```

Обязательны `status_id`, `communicate_at` и `currency_code`. `pipeline_id` по умолчанию первая воронка.

## 8. Перенести карточку в другой статус

```python
lead_id = 4
new_status_id = 2

before = c.internal("GET", f"/leads/{lead_id}")
print("было:", before.get("status_id"), (before.get("status") or {}).get("title"))

c.internal("PUT", f"/leads/{lead_id}", body={"status_id": new_status_id})

after = c.internal("GET", f"/leads/{lead_id}")
print("стало:", after.get("status_id"), (after.get("status") or {}).get("title"))
```

`PUT` принимает частичное тело. Проверять результат лучше повторным `GET`: ответ на `PUT` может быть неполным.

## 9. Обновить карточку

```python
lead_id = 4
patch = {"manager_comment": "Клиент просил КП до пятницы"}
result = c.internal("PUT", f"/leads/{lead_id}", body=patch)
print(result.get("manager_comment"))
```

Кастомные поля обновляются через `custom_field_values` в теле карточки. Точный формат на этом аккаунте не проверялся: сначала сделайте снимок (`crm_snapshot`), потом пробуйте на одной карточке. Если API ответит 422, смотреть `error.body` с перечнем полей.

## 10. Живая воронка и конверсия

Ниже ручной вариант на сырых вызовах, чтобы было видно, откуда берутся числа. Если ручная логика не нужна, то же самое отдаёт `report_data(kind="funnel")` из рецептов 12-13.

```python
raw = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
pipelines = raw.get("data") if isinstance(raw, dict) else raw
cards = c.official_pages("/pipelines/cards", {}, max_items=500)

by_pipeline = {}
for card in cards:
    by_pipeline.setdefault(str(card.get("pipeline_id")), []).append(card)

for p in pipelines:
    statuses = c.internal("GET", f"/leads/statuses/{p['id']}")
    statuses = statuses.get("data", statuses) if isinstance(statuses, dict) else statuses
    pipe_cards = by_pipeline.get(str(p["id"]), [])
    total = len(pipe_cards)
    counter = Counter(str(card.get("status_id")) for card in pipe_cards)
    closed = sum(counter.get(str(s.get("id")), 0) for s in statuses if s.get("is_final"))
    print(f"{p['title']}: карточек {total}, закрыто {closed}, "
          f"доля {round(closed * 100 / total, 1) if total else 0}%")
    for s in statuses:
        n = counter.get(str(s.get("id")), 0)
        print(f"  {s.get('title')}: {n}")
```


## 11. Сводка по карточкам за неделю

```python
date_from = "2026-10-26"
date_to = "2026-11-01"
params = {"filter[created_between]": f"{date_from},{date_to}"}
cards = c.official_pages("/pipelines/cards", params, max_items=500)

status_names = {}
raw = c.internal("GET", "/leads/pipelines", params={"leads": "false"})
pipelines = raw.get("data") if isinstance(raw, dict) else raw
for p in pipelines:
    rows = c.internal("GET", f"/leads/statuses/{p['id']}")
    rows = rows.get("data") if isinstance(rows, dict) else rows
    status_names.update({str(s["id"]): s.get("title") for s in rows})

counter = Counter(str(card.get("status_id")) for card in cards)
print("карточек за период:", len(cards))
for status_id, n in counter.most_common():
    print(f"  {status_names.get(status_id, status_id)}: {n}")

total_sum = sum(float(card.get("products_total") or 0) for card in cards)
print("сумма products_total:", total_sum)
```

`products_total` приходит в минорных единицах: 22 500 000 = 225 000 грн. Делите на 100 перед отчётом в гривнах и проверяйте конкретные карточки, значения в базе неоднородны.

## 12. Нагрузка по менеджерам

Одной строкой через `report(kind="managers")`, без ручных циклов по карточкам.

```python
data = report_data(kind="managers")
print("карточек всего:", data["cards"])
for row in data["managers"]:
    print(row["manager_id"], row["name"],
          "карточек", row["cards"],
          "закрыто", row["closed"],
          "активно", row["active"],
          "сумма", row["products_total"],
          "конверсия", row["conversion_percent"], "%")
```


Что помнить:

- `conversion_percent` - доля закрытых карточек (финальный статус) от всех карточек менеджера. Это не конверсия в оплату: финальные статусы включают отказы, спам и дубли.
- `products_total` в минорных единицах: 22 545 000 = 225 450 грн.
- Срез живой, `date_from` и `date_to` на него не влияют. Строки отсортированы по числу карточек.

## 13. Зависшие карточки

Тоже через `report`, без собственных циклов. Параметр `days` (по умолчанию 7) задаёт порог простоя.

```python
data = report_data(kind="stale", days=7)
print("порог, дней:", data["days"], "найдено:", data["cards"])
for card in data["stale_cards"]:
    print(card["days_stale"], "дн.",
          card["id"], card["title"],
          "статус", card["status_id"],
          "менеджер", card["manager_id"],
          card["updated_at"])
```

Реальный ответ 2026-11-01: `{"kind": "stale", "days": 7, "cards": 0, "stale_cards": []}`. Пусто потому, что после восстановления карточек 01.11.2026 у всех свежий `updated_at`, а не потому что механика не работает. С `days=30` тоже пусто.

Что помнить:

- В выборку попадают только активные карточки: финальные статусы пропускаются.
- Простой считается по `updated_at`, при его отсутствии - по `status_changed_at` или `created_at`.
- `days` меньше 1 поднимается до 1, дробное значение режется до целого.
- Строки отсортированы по `days_stale` по убыванию, в каждой: `id`, `title`, `status_id`, `manager_id`, `updated_at`, `days_stale`.

## 14. Выгрузить карточки в CSV

```python
rows = c.internal_pages("/leads", {"per_page": 50}, max_items=2000, page_size=50)
path = Path(PROJ) / "leads.csv"
fields = ["id", "title", "status_id", "pipeline_id", "manager_id", "currency_code",
          "products_total", "created_at", "is_finished"]

with path.open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.writer(fh, delimiter=";")
    writer.writerow(fields + ["contact_name", "contact_phone"])
    for card in rows:
        contact = card.get("contact") or {}
        writer.writerow([card.get(f) for f in fields] + [contact.get("full_name"), contact.get("phone")])

print(path, len(rows), "строк")
```

`encoding="utf-8-sig"` и `;` нужны, чтобы Excel открыл файл без танцев с кодировкой.

## 15. Выгрузить заказы в CSV

```python
orders = c.official_pages("/order", {}, max_items=500)
path = Path(PROJ) / "orders.csv"
fields = ["id", "status_id", "grand_total", "payment_status", "client_id",
          "manager_id", "source_id", "created_at", "ordered_at", "products_total"]

with path.open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=fields, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(orders)

print(path, len(orders), "строк")
```

На 2026-11-01 заказов в аккаунте 0, файл будет пустым с заголовком. Список заказов читается только официальным API: внутренний `GET /orders` пуст.

## 16. Выручка и средний чек за 30 дней

```python
start = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
end = datetime.now(timezone.utc).date().isoformat()
params = {"filter[created_between]": f"{start},{end}"}
orders = c.official_pages("/order", params, max_items=500)

total = sum(float(o.get("grand_total") or 0) for o in orders)
print("заказов:", len(orders))
print("выручка:", round(total, 2))
print("средний чек:", round(total / len(orders), 2) if orders else 0)
```

Проверить единицы `grand_total` на первом живом заказе: в карточках `products_total` приходит в минорных единицах, у заказов поле не подтверждено.

## 17. Удалить задачу, клиента или заказ по id

Только эти три сущности. Карточки воронки не удаляются через API ни при каких условиях.

```python
def delete_task(task_id):
    task = c.internal("GET", f"/tasks/{task_id}")
    print("удаляю задачу:", task.get("name"))
    return c.internal("DELETE", f"/tasks/{task_id}")

def delete_client(client_id):
    client_row = c.internal("GET", f"/clients/{client_id}")
    print("удаляю клиента:", client_row.get("full_name"))
    return c.internal("DELETE", f"/clients/{client_id}")

def delete_order(order_id):
    # batch-удаление заказов асинхронное: из списка пропадёт через 2-5 секунд
    return c.internal("POST", "/batch/orders/execute/remove", body={"ids": [order_id]})
```

Правила: сначала прочитать объект и убедиться, что id и имя те, что нужно; перед серией удалений сделать снимок (`crm_snapshot`); после удаления перечитать список. Никаких `batch/leads/...` в коде быть не должно.

## 18. Документы: HTML и настоящий PDF

Шаблонов печати в аккаунте 0, поэтому единственный рабочий путь - `preview` и `preview_pdf`: сервер рендерит Twig-строку на демо-данных. `type`: `order`, `lead`, `client`, `delivery`, `warehouse`, `general`.

```python
twig = ("<html><body><h1>Order {{ model.id }}</h1>"
        "<p>Total: {{ model.grand_total }}</p></body></html>")
body = {"type": "order", "structure": twig}

# HTML-превью на демо-данных
view = c.internal("POST", "/config/documents/preview", body=body)
print(view.get("view"))

# Настоящий PDF: сохраняем байты, а не обрезанный текст
response = c.internal_bytes("POST", "/config/documents/preview-pdf", body=body)
exports = Path(PROJ) / "exports"
exports.mkdir(exist_ok=True)
pdf = exports / f"document_{int(datetime.now().timestamp())}.pdf"
pdf.write_bytes(response.content)
print(pdf, len(response.content), response.headers.get("content-type"))
```

Реальный вывод 2026-11-02: HTML `Order 1111`, `Total: 170`; PDF размером 10 286 байт, начинается с `%PDF-1.7`. Заголовок `content-type` при этом врёт и говорит `text/html`, ориентироваться на сигнатуру файла.

Демо-данные: у `order` и `delivery` `model.id = 1111`, у `lead` 181900, у `warehouse` 10001. У `client` поля `id` нет: доступны `full_name`, `phones`, `emails`, `company`, `manager`, `birthday`, `note`, иначе API вернёт 400. У `general` подстановка не выполнилась, `{{ model.id }}` вернулся как есть.

`print` и `attach` при нуле шаблонов возвращают `{"templates": 0, "message": ...}`, а не ошибку. `attach` ходит GET, хотя в `endpoints.json` записан POST.

## 19. Файлы заказа: загрузить, скачать, удалить

Инструмент `files` из `tools_files.py`: multipart-чанки по 1 МБ, лимит 250 МБ на заказ.

```python
# 1. проверка лимита перед загрузкой
print(files_data(action="validate", order_id=123, path=r"C:\temp\contract.pdf"))

# 2. загрузка: чанки и multipart инструмент делает сам
print(files_data(action="attach_order", order_id=123,
                 path=r"C:\temp\contract.pdf", filename="contract.pdf"))

# 3. вложения заказа
print(files_data(action="list_order", order_id=123))

# 4. скачать файл по file_id в keycrm-mcp/exports/
print(files_data(action="download", file_id=42))

# 5. открепить от объекта или удалить файл целиком
print(files_data(action="detach", attachment_id=7))
print(files_data(action="delete_file", file_id=42))
```

Что помнить:

- Живой прогон не сделан: на аккаунте 0 заказов, прикреплять не к чему. Код и протокол чанков сверены с `tools_files.py`, загрузка заявлена проверенной при разработке модуля.
- Удаление заказа **не удаляет** его файлы. Сироты чистить `delete_file` по `file_id`.
- `delete_file` каскадно снимает привязки: файл исчезает из карточек, где был прикреплён.
- `attach_order` принимает `path` или `content_base64`; без них вернёт `path or content_base64 is required`.
- Скачанный файл получает расширение `.bin`, реальный тип смотреть в `content_type` ответа.

## 20. Кто что менял: история изменений

Через `audit`, без ручных запросов к `/auditing`.

```python
# последние изменения по всему аккаунту
data = audit_data(action="list", limit=10)
print("всего событий:", data["meta"]["total"])
for row in data["items"]:
    initiator = row.get("initiator") or {}
    print(row["created_at"], row["action"], row["model_type"],
          row["model_ids"], "->", initiator.get("label"))

# что делал конкретный менеджер
events = audit_data(action="by_manager", manager_id=5)
print("событий менеджера 5:", events.get("total"))
for row in events.get("data", [])[:5]:
    changes = (row.get("context") or {}).get("changes") or []
    print(row.get("created_at"), row.get("action"), [c.get("attribute") for c in changes])

# история одного объекта
order_events = audit_data(action="by_entity", entity_type="order", entity_id=1)
print("событий по заказу 1:", order_events.get("total"))
```

Реальные цифры 2026-11-02: 1139 событий по аккаунту, 416 по менеджеру 5, 6 по заказу 1. `list` отдаёт компактные поля (`action`, `model_type`, `model_ids`, `created_at`, `initiator`, `subject`), а `by_manager` и `by_entity` - сырые записи с `context.changes` (старое и новое значение атрибута).

Что помнить: у `audit` нет фильтра по дате, только `page`; сырые `by_manager` и `by_entity` не режут объём и не слушают `limit`. Для выборки за период фильтруйте `created_at` в коде.

## 21. Полезное через CLI

```powershell
# живые данные без скрипта
.\.venv\Scripts\python.exe crm_cli.py get "/orders/statuses"
.\.venv\Scripts\python.exe crm_cli.py get "/leads?per_page=5"
.\.venv\Scripts\python.exe crm_cli.py official GET /pipelines

# поиск маршрута перед вызовом
.\.venv\Scripts\python.exe crm_cli.py search-endpoints comments

# создание карточки (тело JSON, кавычки экранируются)
.\.venv\Scripts\python.exe crm_cli.py post /leads "{\"status_id\":1,\"communicate_at\":\"2026-11-10 12:00:00\",\"currency_code\":\"UAH\"}"
```

CLI ходит теми же путями, что и MCP-сервер, но без предохранителей: `crm_api`-блокировки живут в сервере, а `crm_cli.py` вызывает транспорт напрямую. Опасные эндпоинты не вызывать ни через CLI, ни через Python.

## Шпаргалка по подводным камням

| Место | Что помнить |
|---|---|
| пагинация internal | `per_page`, не `limit`; максимум 50 |
| пагинация official | `limit` и `page`, лимит 20 запросов/мин |
| orderBy | сортирует только `/stocks`; на большинстве списков игнорируется, а на `/orders`, `/clients`, `/users` и других даёт 500. Сортировать в коде |
| деньги | `products_total` в карточках - минорные единицы, `min_price` в каталоге - гривны |
| контакты | телефон в `contact.phone`, часто пустой; fallback на `manager_comment` |
| карточки | удаление запрещено, только UI |
| задачи | `POST /tasks` работает, тело из рецепта 5 |
| заказы | читать официальным `/order`, внутренний `/orders` пуст |
| клиенты | справочник пуст, контакты живут в карточках |
| финансы | `/finance/payments` и `/finance/transactions` отдают 500 |
| ошибки | всегда JSON `{"ok": false, "error": {...}}`, смотреть `status` и `message` |
