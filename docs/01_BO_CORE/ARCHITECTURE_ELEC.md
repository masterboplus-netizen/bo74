# ARCHITECTURE ELEC — Ядро ЭОМ и правила UI

> **Дата:** 2026-10-25
> **Проект:** Бо 8.1 (Ядро)

## 1. ЯДРО ЭОМ (Базовое)

### core/elec.py
- Питание объекта (legacy) — set_supply, get_supply
- Группы — create_group, get_groups, get_groups_by_floor, get_groups_by_room
- Привязка точек — assign_comm_to_group, unassign_point_from_group
- Расчёты — calc_current, pick_breaker, pick_cable, auto_fill_group
- Фазы L1/L2/L3 — calc_balance, auto_pick_phase, assign_phases_by_load
- Формат — format_group, format_elec_full, format_phase_distribution
- Кухня — get_kitchen_equipment, create_kitchen_group
- Кабели — add_cable, get_cables_by_object, get_cables_by_group, get_cable_summary

### core/elec_panels.py
- Щиты — CRUD (create_panel, get_panel, get_panels, update_panel, delete_panel)
- Связи щит-щит — link_panels, get_parent_panel, get_child_panels, get_panel_links
- Дерево щитов — get_panel_tree(object_id)
- Связь группа-щит — assign_group_to_panel, unassign_group_from_panel, get_groups_by_panel
- Нагрузка — calc_panel_load, calc_object_total_load
- Формат — format_panel, format_panel_short, get_panel_summary

## 2. ЯДРО ЭОМ: ИЕРАРХИЯ И АВТОКОМПЛЕКТАЦИЯ

### core/elec_rules.py
- DEFAULT_RULES — правила по умолчанию
- get_rules(object_id) — правила с переопределениями
- set_rule, reset_rules, list_overrides, format_rules

### core/elec_panels.py (расширение)
- Вводной автомат: set_input_breaker, get_input_breaker
- Компоненты: add_component, get_components, delete_component, clear_auto_components
- Автокомплектация: autocomplete_panel, recalc_panel, get_panel_stats
- Селективность: check_selectivity, format_selectivity
- Иерархия: add_child_panel, set_panel_link_breaker, get_children_tree

### Миграции
- 034 — базовый ЭОМ (elec_supply, elec_groups, elec_cables)
- 035 — floor_id, phase_l1/l2/l3
- 036 — привязка групп к этажу (legacy)
- 037 — Щиты ЭОМ (elec_panels, elec_panel_links)
- 038 — elec_panel_components + поля вводного
- 039 — расширение elec_panel_links

## 3. ТРАССЫ ЭОМ

### core/elec_routes.py
- CRUD: create_route, get_route, get_routes_by_object, delete_route
- Расчёт: calc_distance_m, calc_route_length_from_panel
- Авто: auto_routes_for_group, auto_routes_for_panel
- Формат: format_route, summarize_routes_by_cable

### Миграция 040 — elec_routes
- Связи: panel_id, group_id, from_point_id, to_point_id
- Параметры: cable_type, length_m, route_type, waypoints (JSON), is_manual

## 4. ЦЕНЫ И СМЕТЫ ЭОМ

### core/elec_prices.py
- get_component_price, get_price_info, set_component_price
- calc_object_panels_cost, calc_object_montage_cost, calc_object_elec_total
- Заглушки: fetch_marketplace_prices, import_prices_from_csv

### core/elec_routes.py (смета монтажа)
- calc_route_cost — кабель + расходники
- calc_montage_cost_by_group, calc_montage_cost_by_panel

### core/elec_panels.py (смета щита)
- calc_component_price, calc_panel_cost, get_panel_cost_breakdown

### Миграция 041
- elec_panel_components: price_unit, price_source, price_updated_at
- component_prices: component_type, rating, poles, brand, price

## 5. ПРАВИЛА UI (STYLE_GUIDE)

Все UI-сообщения в interfaces/telegram/ должны следовать этим правилам:
- Без разметки *...*, **...**, _..._
- Списки нумерованные (если однотипные)
- Разделитель — « · »
- Эмодзи в БД — НЕ хранятся (только в UI)
- Кнопки — эмодзи + текст, нумерация если много
- Один эмодзи в заголовке

**Конец ARCHITECTURE_ELEC.md**