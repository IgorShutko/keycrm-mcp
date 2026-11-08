# Action matrix (read-only sweep)

Сгенерировано `test_actions.py` по живому аккаунту. Каждый read-action вызван
через stdio MCP. Ошибки здесь не обязательно баги сервера: часть ручек на этом
тенанте отключена или требует данных (заказов 0, модули выключены).

Проверено: **83**, ok: **78**, ошибок: **5**.

| tool | ok | ошибок |
|---|---|---|
| `audit` | 2 | 0 |
| `automations` | 1 | 0 |
| `clients` | 2 | 0 |
| `comments` | 1 | 0 |
| `conversations` | 2 | 0 |
| `crm_api` | 2 | 0 |
| `crm_capabilities` | 1 | 0 |
| `crm_endpoints` | 2 | 0 |
| `crm_status` | 1 | 0 |
| `custom_fields` | 3 | 0 |
| `delivery` | 14 | 1 |
| `documents` | 5 | 0 |
| `files` | 0 | 1 |
| `finance` | 8 | 2 |
| `leads` | 4 | 0 |
| `orders` | 6 | 0 |
| `products` | 4 | 0 |
| `publications` | 1 | 0 |
| `report` | 5 | 0 |
| `settings` | 2 | 0 |
| `stocks` | 6 | 1 |
| `tasks` | 3 | 0 |
| `users` | 3 | 0 |

## Детали

| tool | action | статус | заметка |
|---|---|---|---|
| `orders` | `list` | ok | dict(orders,meta) |
| `orders` | `statuses` | ok | list[19] |
| `orders` | `groups` | ok | list[6] |
| `orders` | `totals` | ok | list[0] |
| `orders` | `tags` | ok | list[0] |
| `orders` | `sources` | ok | list[9] |
| `leads` | `list` | ok | dict(leads,meta) |
| `leads` | `list_filtered` | ok | dict(leads,meta) |
| `leads` | `pipelines` | ok | list[1] |
| `leads` | `desk` | ok | list[7] |
| `clients` | `list` | ok | dict(clients,meta) |
| `clients` | `search` | ok | dict(current_page,data,first_page_url,from) |
| `products` | `list` | ok | dict(products,meta) |
| `products` | `list_search` | ok | dict(products,meta) |
| `products` | `categories` | ok | list[0] |
| `products` | `warehouses` | ok | list[1] |
| `tasks` | `list` | ok | dict(tasks,meta) |
| `tasks` | `list_closed` | ok | dict(tasks,meta) |
| `tasks` | `expired_count` | ok | dict(count) |
| `conversations` | `list` | ok | dict(conversations,meta) |
| `conversations` | `unread` | ok | list[0] |
| `users` | `list` | ok | list[3] |
| `users` | `roles` | ok | list[7] |
| `users` | `permissions` | ok | list[42] |
| `settings` | `general` | ok | dict(general) |
| `settings` | `orders` | ok | dict(orders) |
| `report` | `sales` | ok | dict(kind,period,orders,revenue) |
| `report` | `leads` | ok | dict(kind,period,cards,products_total_sum) |
| `report` | `funnel` | ok | dict(kind,cards_total,pipelines) |
| `report` | `managers` | ok | dict(kind,cards,managers) |
| `report` | `stale` | ok | dict(kind,days,cards,stale_cards) |
| `crm_status` | `default` | ok | dict(domain,internal_api,official_api,profile) |
| `crm_capabilities` | `default` | ok | dict(account,root_is_active,modules,plan_general) |
| `crm_endpoints` | `search` | ok | dict(count,endpoints) |
| `crm_endpoints` | `group` | ok | dict(count,endpoints) |
| `crm_api` | `internal_audit` | ok | dict(current_page,data,first_page_url,from) |
| `crm_api` | `official_calls` | ok | dict(current_page,data,first_page_url,from) |
| `audit` | `list` | ok | dict(items,meta) |
| `audit` | `by_manager` | ok | dict(current_page,data,first_page_url,from) |
| `finance` | `payment_config` | ok | dict(min,max,payments,expenses) |
| `finance` | `payment_methods` | ok | list[5] |
| `finance` | `expense_types` | ok | list[10] |
| `finance` | `currency_rates` | ok | list[1] |
| `finance` | `rates_common` | ok | dict(count,rates) |
| `finance` | `fiscals` | ok | dict(fiscals,meta) |
| `finance` | `billing` | ok | dict(sources,ordersCount,leadsCount,messagesCount) |
| `finance` | `bills` | ok | dict(bills,meta) |
| `finance` | `payments` | error | 500 GET /finance/payments is broken on this tenant (500). Order payments are visible |
| `finance` | `transactions` | error | 500 GET /finance/transactions is broken on this tenant (500). Use finance.bills, fin |
| `delivery` | `services` | ok | dict(services,meta) |
| `delivery` | `prep_centers` | ok | dict(prep_centers,meta) |
| `delivery` | `prep_centers_active` | ok | dict(prep_centers) |
| `delivery` | `shipment_templates` | ok | dict(shipment_templates) |
| `delivery` | `locations_np` | ok | dict(locations,meta) |
| `delivery` | `locations_rozetka` | ok | dict(locations,meta) |
| `delivery` | `locations_ukrposhta` | ok | dict(locations,meta) |
| `delivery` | `suggest_np` | error | 500 delivery.suggest is broken on this tenant (500). Use delivery action=locations ( |
| `stocks` | `list` | ok | dict(stocks,meta) |
| `stocks` | `warehouses` | ok | list[1] |
| `stocks` | `stat` | ok | dict(quantity,purchased_price,price) |
| `stocks` | `filters` | ok | dict(in_reserve,available_quantity) |
| `stocks` | `movements` | ok | dict(movements,meta) |
| `stocks` | `inventories` | error | 404 movement 1 not found; list real ids with stocks action=movements |
| `stocks` | `history` | ok | dict(history,meta) |
| `publications` | `list` | ok | dict(publications,meta) |
| `custom_fields` | `list` | ok | list[12] |
| `custom_fields` | `list_lead` | ok | list[12] |
| `custom_fields` | `values` | ok | list[6] |
| `comments` | `list_lead` | ok | dict(comments,total,meta) |
| `documents` | `list` | ok | list[0] |
| `documents` | `by_scope_order` | ok | list[0] |
| `documents` | `export_template` | ok | list[1] |
| `documents` | `export_formats` | ok | dict(csv,xlsx) |
| `documents` | `print_layouts` | ok | list[2] |
| `automations` | `list` | ok | dict(count,triggers) |
| `files` | `list_order_empty` | error | 404 order 1 not found; list real ids with orders action=list |
| `delivery` | `locations_novaposhta_raw` | ok | dict(locations,meta) |
| `delivery` | `warehouses_novaposhta` | ok | dict(warehouses,meta) |
| `delivery` | `streets_novaposhta` | ok | dict(streets,meta) |
| `delivery` | `locations_rozetka_delivery_raw` | ok | dict(locations,meta) |
| `delivery` | `warehouses_rozetka_delivery` | ok | dict(warehouses,meta) |
| `delivery` | `locations_ukrposhta_raw` | ok | dict(locations,meta) |
| `delivery` | `warehouses_ukrposhta` | ok | dict(warehouses,meta) |

## Не покрыто (write-действия)

create/update/delete/move/attach и прочие записи не вызывались в этом прогоне:
они требуют тестовых объектов и покрыты `test_smoke.py` / `test_domains.py`.
