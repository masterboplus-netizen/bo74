# CODE_MAP — карта кода Бо 7.7

## core/comms.py
COMM_TYPES (строка 5) — типы: water_cold, water_hot, sewer, drain, heating, gas, vent, plumb_sink, plumb_toilet, plumb_bath, plumb_shower, plumb_radiator, plumb_washer, plumb_dishwasher, elec_panel, и др.

Функции: add_comm, get_comm, get_comms, update_comm, delete_comm, format_comm, get_comm_type_label

## core/plumbing_panels.py
- PANEL_TYPES, MOUNT_TYPES, PIPE_PRICES_DEFAULT, PIPE_LABELS, PLUMB_CONSUMABLE_PRICES
- PLUMB_COMM_TYPES — типы для сантехники
- create_panel, get_panel, get_panels, update_panel, delete_panel
- create_route, get_routes_by_panel, delete_route, format_route
- assign_point_to_panel — ЗАГЛУШКА (не работает)
- get_points_of_panel — читает через plumbing_routes.to_point_id
- get_available_plumb_points — все plumb-точки объекта

## interfaces/telegram/rooms.py
- handle_rooms_callback (~4224) — главный роутер
- handle_panels_callback (~5716) — щиты ЭОМ
- handle_groups_callback (~3138) — группы ЭОМ
- handle_cables_callback (~5511) — кабели
- handle_comm_callback (~2279) — коммуникации комнат
- _show_comms_list (~2487) — список точек
- handle_floors_callback — помещения
- handle_obj_elec_callback — ЭОМ объекта
- handle_wall_round_callback — обход стен
- handle_export_callback — экспорт

## Миграции
- 040 elec_routes, 041 component_prices, 042 plumbing, 043 object_works, 044 price_imports
