# CODE_MAP_AUTO.md — авто-карта колбэков

> Сгенерировано: `python3 tools/map_scan.py`
> Не редактировать руками.

## Роутеры (handlers/commands/callbacks/*)

| Файл | try_handle |
|---|---|
| estimates.py | 1 |
| finance.py | 1 |
| kpi.py | 1 |
| misc.py | 1 |
| objects.py | 1 |
| personal.py | 1 |
| reports.py | 1 |
| tasks.py | 1 |

## Text-домены (handlers/commands/text/*)

- `text/crm.py`
- `text/fallback.py`
- `text/finances.py`
- `text/misc.py`
- `text/objects.py`
- `text/personal.py`
- `text/rooms.py`
- `text/tasks.py`

## ⚠️ Кнопки БЕЗ обработчика (0)

Все кнопки имеют обработчики ✅

## Реестр callback_data (379 префиксов)

| Префикс | Кнопки | Обработчики |
|---|---|---|
| `activity_call` | — | crm.py:92, crm.py:92 |
| `activity_list` | crm.py:182, crm.py:223, crm.py:182 | crm.py:122, crm.py:124, crm.py:122 |
| `activity_meeting` | crm.py:180, crm.py:180 | crm.py:92, crm.py:92 |
| `activity_note` | crm.py:181, crm.py:181 | crm.py:92, crm.py:92 |
| `activity_plan` | crm.py:179, crm.py:179 | crm.py:108, crm.py:109, crm.py:108 |
| `add_expense` | add_menu.py:23, add_menu.py:76, tasks.py:20 | add_menu.py:47, add_menu.py:47 |
| `add_object` | add_menu.py:21, tasks.py:18, add_menu.py:21 | add_menu.py:29, add_menu.py:29 |
| `add_task` | add_menu.py:22, add_menu.py:63, tasks.py:19 | add_menu.py:39, add_menu.py:39 |
| `by_assignee` | _legacy.py:170, tasks.py:140, tasks.py:156 | tasks.py:98, tasks.py:98 |
| `byassigned` | tasks.py:107, tasks.py:107 | tasks.py:120, tasks.py:123, tasks.py:120 |
| `cables` | — | rooms.py:4572, rooms_pre_1_1_20261005_165618.py:4170, rooms_pre_1_1_20261005_165850.py:4170 |
| `cables_add` | rooms.py:6062, rooms_pre_1_1_20261005_165618.py:5452, rooms_pre_1_1_20261005_165850.py:5452 | rooms.py:6074, rooms.py:6075, rooms_pre_1_1_20261005_165618.py:5464 |
| `cables_del` | — | rooms.py:6127, rooms.py:6128, rooms_pre_1_1_20261005_165618.py:5517 |
| `cables_group` | rooms.py:6097, rooms_pre_1_1_20261005_165618.py:5487, rooms_pre_1_1_20261005_165850.py:5487 | rooms.py:6109, rooms.py:6110, rooms_pre_1_1_20261005_165618.py:5499 |
| `cables_list` | rooms.py:3273, rooms.py:5192, rooms.py:6086 | rooms.py:6042, rooms.py:6043, rooms_pre_1_1_20261005_165618.py:5432 |
| `cal_day` | — | tasks.py:505, tasks.py:506, tasks.py:507 |
| `cal_ignore` | tasks.py:815, tasks.py:820, tasks.py:821 | tasks.py:493, tasks.py:493 |
| `cal_nav` | — | tasks.py:497, tasks.py:498, tasks.py:497 |
| `cal_quick` | — | tasks.py:505, tasks.py:511, tasks.py:505 |
| `cat` | choose_expense.py:101, choose_expense.py:102, choose_expense.py:103 | choose_expense.py:119, bot.py:230, bot.py:100 |
| `choose_obj` | — | bot.py:231, bot.py:101 |
| `choose_obj_add_task_none_none_none` | choose_expense.py:91, choose_expense.py:91 | — |
| `client` | crm.py:65, crm.py:103, crm.py:117 | crm.py:137, crm.py:139, crm.py:137 |
| `comm` | rooms.py:2361, rooms.py:2361 | rooms.py:4643, rooms_pre_1_1_20261005_165618.py:4235, rooms_pre_1_1_20261005_165850.py:4235 |
| `comm_add` | rooms.py:2534, rooms.py:2628, rooms.py:5738 | rooms.py:2287, rooms.py:2288, rooms_pre_1_1_20261005_165618.py:2286 |
| `comm_del` | rooms.py:2588, rooms_pre_1_1_20261005_165618.py:2558, rooms_pre_1_1_20261005_165850.py:2558 | rooms.py:2350, rooms.py:2351, rooms_pre_1_1_20261005_165618.py:2349 |
| `comm_delok` | rooms.py:2360, rooms.py:2360 | rooms.py:2368, rooms.py:2369, rooms.py:2368 |
| `comm_edit` | rooms.py:2565, rooms.py:2566, rooms.py:2570 | rooms.py:2389, rooms.py:2390, rooms_pre_1_1_20261005_165618.py:2366 |
| `comm_group` | rooms.py:2584, rooms.py:2587, rooms_pre_1_1_20261005_165618.py:2554 | rooms.py:2453, rooms.py:2454, rooms_pre_1_1_20261005_165618.py:2423 |
| `comm_group_set` | rooms.py:2498, rooms_pre_1_1_20261005_165618.py:2468, rooms_pre_1_1_20261005_165850.py:2468 | rooms.py:2441, rooms.py:2442, rooms_pre_1_1_20261005_165618.py:2411 |
| `comm_group_unset` | rooms.py:2585, rooms_pre_1_1_20261005_165618.py:2555, rooms_pre_1_1_20261005_165850.py:2555 | rooms.py:2431, rooms.py:2432, rooms_pre_1_1_20261005_165618.py:2401 |
| `comm_show` | rooms.py:2408, rooms.py:2469, rooms.py:2485 | rooms.py:2345, rooms.py:2346, rooms_pre_1_1_20261005_165618.py:2344 |
| `comm_skip` | — | rooms.py:2415, rooms.py:2417, rooms_pre_1_1_20261005_165618.py:2392 |
| `comm_skip_diameter` | rooms.py:5645, rooms.py:5645 | — |
| `comm_skip_voltage` | rooms.py:5656, rooms.py:5656 | — |
| `comm_type` | rooms.py:2291, rooms_pre_1_1_20261005_165618.py:2290, rooms_pre_1_1_20261005_165850.py:2290 | rooms.py:2303, rooms.py:2304, rooms_pre_1_1_20261005_165618.py:2302 |
| `comm_wall` | rooms.py:2311, rooms.py:2312, rooms.py:2313 | rooms.py:2327, rooms.py:2328, rooms_pre_1_1_20261005_165618.py:2326 |
| `confirmdate` | — | bot.py:232, bot.py:102 |
| `confirmdate_no` | tasks.py:44, tasks.py:44 | tasks.py:914, tasks.py:914 |
| `confirmdate_yes` | tasks.py:43, tasks.py:43 | tasks.py:888, tasks.py:888 |
| `crm_client_add` | crm.py:14, crm.py:50, crm.py:66 | crm.py:189, crm.py:189 |
| `crm_clients` | crm.py:48, crm.py:185, crm.py:393 | crm.py:57, crm.py:57 |
| `crm_deal_add` | crm.py:26, crm.py:51, crm.py:84 | crm.py:199, crm.py:199 |
| `crm_deal_client` | crm.py:163, crm.py:207, crm.py:163 | crm.py:293, crm.py:294, crm.py:293 |
| `crm_deal_new_client` | crm.py:209, crm.py:209 | crm.py:272, crm.py:272 |
| `crm_deals` | crm.py:49, crm.py:250, crm.py:266 | crm.py:74, crm.py:74 |
| `crm_new_client_for_deal` | crm.py:30, crm.py:185, crm.py:30 | crm.py:279, crm.py:279 |
| `crm_phone_edit` | crm.py:314, crm.py:335, crm.py:66 | crm.py:320, crm.py:320 |
| `crm_phone_edit_back` | crm.py:325, crm.py:325 | crm.py:330, crm.py:330 |
| `crm_phone_pick` | crm.py:79, crm.py:79 | crm.py:305, crm.py:306, crm.py:305 |
| `crm_skip_address` | crm.py:315, crm.py:336, crm.py:346 | crm.py:351, crm.py:351 |
| `crm_skip_phone` | crm.py:288, crm.py:511, crm.py:44 | crm.py:341, crm.py:341 |
| `crm_skip_source` | crm.py:356, crm.py:118, crm.py:356 | crm.py:361, crm.py:361 |
| `deal` | crm.py:83, crm.py:184, crm.py:265 | crm.py:217, crm.py:219, crm.py:217 |
| `deal_status` | crm.py:245, crm.py:246, crm.py:247 | crm.py:255, crm.py:257, crm.py:255 |
| `dur_days` | tasks.py:551, tasks.py:552, tasks.py:553 | tasks.py:565, tasks.py:566, tasks.py:565 |
| `est` | — | estimates.py:15, estimates.py:15 |
| `est_all` | estimates.py:1150, estimates.py:1150 | estimates.py:169, estimates.py:169 |
| `est_allmat` | — | estimates.py:900, estimates.py:902, estimates.py:900 |
| `est_allwork` | — | estimates.py:851, estimates.py:853, estimates.py:851 |
| `est_buy` | — | estimates.py:738, estimates.py:740, estimates.py:738 |
| `est_bykind` | estimates.py:1152, estimates.py:1292, estimates.py:1152 | estimates.py:1254, estimates.py:1254 |
| `est_cmp` | estimates.py:248, estimates.py:248 | — |
| `est_cmp_a` | estimates.py:1174, estimates.py:1174 | estimates.py:1187, estimates.py:1188, estimates.py:1187 |
| `est_cmp_b` | estimates.py:1196, estimates.py:1196 | estimates.py:1209, estimates.py:1210, estimates.py:1209 |
| `est_compare` | estimates.py:1153, estimates.py:1198, estimates.py:1244 | estimates.py:1168, estimates.py:1168 |
| `est_csv` | estimates.py:247, estimates.py:247 | estimates.py:267, estimates.py:269, estimates.py:267 |
| `est_dash` | estimates.py:1145, estimates.py:1145 | estimates.py:135, estimates.py:135 |
| `est_export` | estimates.py:245, estimates.py:245 | estimates.py:451, estimates.py:453, estimates.py:451 |
| `est_export_all` | estimates.py:1146, estimates.py:1146 | estimates.py:100, estimates.py:100 |
| `est_extra` | _legacy.py:316, estimates.py:512, _legacy.py:316 | estimates.py:478, estimates.py:483, estimates.py:478 |
| `est_extra_add` | estimates.py:494, estimates.py:494 | estimates.py:480, estimates.py:503, estimates.py:505 |
| `est_import` | estimates.py:1151, estimates.py:1151 | _legacy.py:74, _legacy.py:74 |
| `est_kind` | estimates.py:1269, estimates.py:1269 | estimates.py:1282, estimates.py:1283, estimates.py:1282 |
| `est_kpi` | estimates.py:249, estimates.py:249 | estimates.py:384, estimates.py:386, estimates.py:384 |
| `est_kpi_masters` | estimates.py:1147, estimates.py:1147 | estimates.py:83, estimates.py:83 |
| `est_kpi_objs` | estimates.py:1148, estimates.py:1148 | estimates.py:49, estimates.py:49 |
| `est_kpi_red` | estimates.py:1149, estimates.py:1149 | estimates.py:66, estimates.py:66 |
| `est_month` | — | estimates.py:19, estimates.py:21, estimates.py:19 |
| `est_object` | _legacy.py:264, estimates.py:41, estimates.py:299 | estimates.py:237, estimates.py:239, estimates.py:237 |
| `est_object_floors` | — | estimates.py:947, estimates.py:949, estimates.py:947 |
| `est_object_rooms` | — | estimates.py:987, estimates.py:989, estimates.py:987 |
| `est_pdf` | estimates.py:246, estimates.py:246 | estimates.py:421, estimates.py:423, estimates.py:421 |
| `est_per` | estimates.py:313, estimates.py:314, estimates.py:315 | estimates.py:328, estimates.py:329, estimates.py:328 |
| `est_period` | estimates.py:251, estimates.py:354, estimates.py:251 | estimates.py:307, estimates.py:309, estimates.py:307 |
| `est_price_edit_mat` | estimates.py:555, estimates.py:555 | estimates.py:591, estimates.py:592, estimates.py:591 |
| `est_price_edit_work` | estimates.py:578, estimates.py:578 | estimates.py:616, estimates.py:617, estimates.py:616 |
| `est_prices` | estimates.py:252, estimates.py:557, estimates.py:580 | estimates.py:522, estimates.py:527, estimates.py:522 |
| `est_prices_mat` | estimates.py:531, estimates.py:606, estimates.py:531 | estimates.py:524, estimates.py:545, estimates.py:547 |
| `est_prices_work` | estimates.py:532, estimates.py:631, estimates.py:532 | estimates.py:524, estimates.py:568, estimates.py:570 |
| `est_room` | estimates.py:1009, estimates.py:1037, estimates.py:1051 | estimates.py:213, estimates.py:215, estimates.py:213 |
| `est_room_mat` | estimates.py:227, estimates.py:227 | estimates.py:1101, estimates.py:1103, estimates.py:1101 |
| `est_room_per` | estimates.py:229, estimates.py:1092, estimates.py:229 | estimates.py:1022, estimates.py:1024, estimates.py:1022 |
| `est_room_sess` | estimates.py:1049, estimates.py:1049 | estimates.py:1062, estimates.py:1063, estimates.py:1062 |
| `est_room_work` | estimates.py:228, estimates.py:228 | estimates.py:1122, estimates.py:1124, estimates.py:1122 |
| `est_rules` | estimates.py:250, estimates.py:250 | estimates.py:363, estimates.py:365, estimates.py:363 |
| `est_sched` | estimates.py:681, estimates.py:681 | estimates.py:641, estimates.py:646, estimates.py:641 |
| `est_sched_add` | estimates.py:658, estimates.py:659, estimates.py:658 | estimates.py:643, estimates.py:668, estimates.py:669 |
| `est_search` | estimates.py:1154, estimates.py:1154 | estimates.py:200, estimates.py:200 |
| `est_setstatus` | estimates.py:809, estimates.py:809 | estimates.py:821, estimates.py:822, estimates.py:821 |
| `est_status` | — | estimates.py:786, estimates.py:788, estimates.py:786 |
| `est_where` | estimates.py:729, estimates.py:729 | estimates.py:690, estimates.py:695, estimates.py:690 |
| `est_where_mat` | estimates.py:703, estimates.py:703 | estimates.py:692, estimates.py:716, estimates.py:717 |
| `exp_type_object` | _legacy.py:397, crm.py:554, _legacy.py:397 | objects.py:24, objects.py:25, objects.py:24 |
| `exp_type_personal` | _legacy.py:396, _legacy.py:396 | personal.py:80, personal.py:81, personal.py:80 |
| `finobj` | finance.py:69, finance.py:69 | finance.py:25, finance.py:25 |
| `floor` | rooms.py:2824, rooms.py:2842, rooms.py:3028 | rooms.py:2932, rooms.py:2933, rooms.py:4583 |
| `floor_estimate` | estimates.py:974, rooms.py:3116, estimates.py:974 | rooms.py:2831, rooms.py:2833, rooms.py:2831 |
| `floor_export` | rooms.py:3117, rooms.py:3117 | rooms.py:2807, rooms.py:2809, rooms.py:2807 |
| `floor_group_new` | rooms.py:3078, rooms.py:5112, rooms_pre_1_1_20261005_165618.py:2946 | rooms.py:2955, rooms.py:2956, rooms_pre_1_1_20261005_165618.py:2823 |
| `floor_group_phase` | rooms.py:2980, rooms.py:2981, rooms_pre_1_1_20261005_165618.py:2848 | rooms.py:2990, rooms.py:2991, rooms_pre_1_1_20261005_165618.py:2858 |
| `floor_group_purpose` | rooms.py:2960, rooms_pre_1_1_20261005_165618.py:2828, rooms_pre_1_1_20261005_165850.py:2828 | rooms.py:2972, rooms.py:2973, rooms_pre_1_1_20261005_165618.py:2840 |
| `floor_groups` | rooms.py:2961, rooms.py:2982, rooms.py:3002 | rooms.py:2950, rooms.py:2951, rooms_pre_1_1_20261005_165618.py:2818 |
| `floor_kitchen` | rooms.py:3077, rooms.py:5938, rooms.py:5948 | rooms.py:4578, rooms.py:5997, rooms.py:5998 |
| `floor_kitchen_add` | rooms.py:6015, rooms_pre_1_1_20261005_165618.py:5405, rooms_pre_1_1_20261005_165850.py:5405 | rooms.py:5881, rooms.py:5882, rooms_pre_1_1_20261005_165618.py:5271 |
| `floor_kitchen_all` | rooms.py:6019, rooms_pre_1_1_20261005_165618.py:5409, rooms_pre_1_1_20261005_165850.py:5409 | rooms.py:5965, rooms.py:5966, rooms_pre_1_1_20261005_165618.py:5355 |
| `floor_rename` | rooms.py:3120, rooms_pre_1_1_20261005_165618.py:2986, rooms_pre_1_1_20261005_165850.py:2986 | — |
| `floor_rooms` | rooms.py:3115, rooms_pre_1_1_20261005_165618.py:2983, rooms_pre_1_1_20261005_165850.py:2983 | rooms.py:2944, rooms.py:2945, rooms_pre_1_1_20261005_165618.py:2812 |
| `group` | rooms.py:3321, rooms.py:3339, rooms.py:3367 | rooms.py:3526, rooms.py:3528, rooms.py:4621 |
| `group_new` | rooms.py:3604, rooms_pre_1_1_20261005_165618.py:3373, rooms_pre_1_1_20261005_165850.py:3373 | rooms.py:3616, rooms.py:3617, rooms_pre_1_1_20261005_165618.py:3385 |
| `group_panel_pick` | rooms.py:3562, rooms.py:3565, rooms.py:5118 | rooms.py:3448, rooms.py:3449, rooms.py:3448 |
| `group_panel_set` | rooms.py:3481, rooms.py:3481 | rooms.py:3493, rooms.py:3494, rooms.py:3493 |
| `group_panel_unset` | rooms.py:3563, rooms.py:3563 | rooms.py:3506, rooms.py:3507, rooms.py:3506 |
| `group_phase` | rooms.py:3641, rooms.py:3642, rooms_pre_1_1_20261005_165618.py:3410 | rooms.py:3656, rooms.py:3657, rooms_pre_1_1_20261005_165618.py:3425 |
| `group_purpose` | rooms.py:3620, rooms_pre_1_1_20261005_165618.py:3389, rooms_pre_1_1_20261005_165850.py:3389 | rooms.py:3633, rooms.py:3634, rooms_pre_1_1_20261005_165618.py:3402 |
| `group_routes` | rooms.py:3320, rooms.py:3430, rooms.py:3558 | rooms.py:3346, rooms.py:3347, rooms_pre_1_1_20261005_165618.py:3197 |
| `group_routes_auto` | rooms.py:3365, rooms_pre_1_1_20261005_165618.py:3216, rooms_pre_1_1_20261005_165850.py:3216 | rooms.py:3297, rooms.py:3298, rooms_pre_1_1_20261005_165618.py:3148 |
| `group_routes_clear` | rooms.py:3366, rooms_pre_1_1_20261005_165618.py:3217, rooms_pre_1_1_20261005_165850.py:3217 | rooms.py:3328, rooms.py:3329, rooms_pre_1_1_20261005_165618.py:3179 |
| `kpi_masters` | kpi.py:15, kpi.py:15 | kpi.py:26, kpi.py:26 |
| `kpi_objects` | kpi.py:16, kpi.py:16 | kpi.py:44, kpi.py:44 |
| `kpi_red` | kpi.py:17, kpi.py:17 | kpi.py:62, kpi.py:62 |
| `menu_add` | add_menu.py:34, keyboards.py:16, objects.py:98 | add_menu.py:17, add_menu.py:17 |
| `menu_back` | _legacy.py:179, _legacy.py:398, add_menu.py:24 | tasks.py:58, tasks.py:58 |
| `menu_crm` | crm.py:67, crm.py:85, crm.py:194 | crm.py:39, crm.py:39 |
| `menu_dashboard` | keyboards.py:15, keyboards.py:15, onboarding.py:30 | misc.py:39, misc.py:39 |
| `menu_estimates` | _legacy.py:88, _legacy.py:256, _legacy.py:266 | estimates.py:1143, estimates.py:1143 |
| `menu_finance` | finance.py:42, objects.py:66, keyboards.py:9 | finance.py:14, finance.py:14 |
| `menu_help` | keyboards.py:17, misc.py:148, keyboards.py:17 | misc.py:52, misc.py:52 |
| `menu_kpi` | estimates.py:58, estimates.py:75, estimates.py:92 | kpi.py:10, kpi.py:10 |
| `menu_objects` | keyboards.py:7, objects.py:24, rooms.py:4260 | _legacy.py:105, _legacy.py:105 |
| `menu_personal` | misc.py:33, personal.py:75, keyboards.py:13 | personal.py:18, personal.py:18 |
| `menu_reports` | reports.py:49, reports.py:63, reports.py:76 | reports.py:25, reports.py:25 |
| `menu_tasks` | tasks.py:37, tasks.py:47, tasks.py:76 | _legacy.py:117, _legacy.py:117 |
| `my_tasks` | _legacy.py:169, _legacy.py:169 | tasks.py:68, tasks.py:68 |
| `newexp_obj` | objects.py:111, objects.py:111 | add_menu.py:68, add_menu.py:69, add_menu.py:68 |
| `newtask_obj` | objects.py:96, objects.py:96 | add_menu.py:55, add_menu.py:56, add_menu.py:55 |
| `obj` | objects.py:65, objects.py:136, crm.py:435 | objects.py:142, rooms.py:4376, rooms.py:4378 |
| `obj_archive` | — | rooms.py:4270, rooms.py:4271, rooms.py:4270 |
| `obj_archive_list` | objects.py:49, rooms.py:4290, objects.py:49 | rooms.py:4251, rooms.py:4251 |
| `obj_del` | objects.py:82, objects.py:82 | rooms.py:5820, rooms.py:5821, rooms_pre_1_1_20261005_165618.py:5210 |
| `obj_delok` | rooms.py:5825, rooms_pre_1_1_20261005_165618.py:5215, rooms_pre_1_1_20261005_165850.py:5215 | rooms.py:5839, rooms.py:5840, rooms_pre_1_1_20261005_165618.py:5229 |
| `obj_elec` | objects.py:67, rooms.py:3119, rooms.py:3191 | rooms.py:3230, rooms.py:3231, rooms.py:4308 |
| `obj_elec_cost` | estimates.py:253, objects.py:68, estimates.py:253 | rooms.py:4356, rooms.py:4358, rooms_pre_1_1_20261005_165618.py:3921 |
| `obj_elec_labor` | objects.py:69, objects.py:69 | rooms.py:3215, rooms.py:3216, rooms.py:3215 |
| `obj_elec_pdf` | objects.py:72, objects.py:72 | rooms.py:6683, rooms.py:6684, rooms.py:6683 |
| `obj_elec_set` | rooms.py:3189, rooms.py:3190, rooms_pre_1_1_20261005_165618.py:3055 | rooms.py:3202, rooms.py:3203, rooms_pre_1_1_20261005_165618.py:3068 |
| `obj_elec_setup` | rooms.py:3272, rooms_pre_1_1_20261005_165618.py:3123, rooms_pre_1_1_20261005_165850.py:3123 | rooms.py:3186, rooms.py:3187, rooms_pre_1_1_20261005_165618.py:3052 |
| `obj_est_csv` | objects.py:70, objects.py:70 | rooms.py:6773, rooms.py:6774, rooms_pre_1_1_20261005_165618.py:6042 |
| `obj_floor` | — | rooms.py:4583, rooms_pre_1_1_20261005_165618.py:4181, rooms_pre_1_1_20261005_165850.py:4181 |
| `obj_floor_add` | rooms.py:2866, rooms.py:3030, rooms_pre_1_1_20261005_165618.py:2898 | rooms.py:2903, rooms.py:2904, rooms_pre_1_1_20261005_165618.py:2783 |
| `obj_floor_type` | rooms.py:2857, rooms.py:2858, rooms.py:2859 | rooms.py:2878, rooms.py:2879, rooms.py:2878 |
| `obj_floor_type_more` | rooms.py:2917, rooms.py:2917 | rooms.py:2854, rooms.py:2855, rooms.py:2854 |
| `obj_floors` | objects.py:65, rooms.py:2896, rooms.py:2918 | rooms.py:2848, rooms.py:2849, rooms.py:4302 |
| `obj_rename` | objects.py:80, objects.py:80 | rooms.py:5853, rooms.py:5854, rooms_pre_1_1_20261005_165618.py:5243 |
| `obj_spec` | objects.py:71, objects.py:71 | rooms.py:4314, rooms.py:4315, rooms_pre_1_1_20261005_165618.py:3927 |
| `obj_unarchive` | — | rooms.py:4282, rooms.py:4283, rooms.py:4282 |
| `objexp_cat` | objects.py:43, objects.py:44, objects.py:45 | objects.py:53, objects.py:55, objects.py:53 |
| `objexp_obj` | objects.py:128, objects.py:128 | objects.py:33, objects.py:35, objects.py:33 |
| `objfin` | objects.py:78, objects.py:78 | objects.py:101, objects.py:101 |
| `objphotos` | reports.py:111, objects.py:79, photos.py:185 | objects.py:111, objects.py:111 |
| `objtasks` | objects.py:77, tasks.py:214, objects.py:77 | objects.py:88, objects.py:88 |
| `objtasks_none` | tasks.py:218, tasks.py:218 | objects.py:72, objects.py:72 |
| `opening` | — | rooms.py:4649, rooms_pre_1_1_20261005_165618.py:4241, rooms_pre_1_1_20261005_165850.py:4241 |
| `opening_add` | rooms.py:2658, rooms.py:5785, rooms_pre_1_1_20261005_165618.py:2628 | rooms.py:2666, rooms.py:2667, rooms_pre_1_1_20261005_165618.py:2636 |
| `opening_del` | rooms.py:2743, rooms_pre_1_1_20261005_165618.py:2713, rooms_pre_1_1_20261005_165850.py:2713 | rooms.py:2772, rooms.py:2773, rooms_pre_1_1_20261005_165618.py:2742 |
| `opening_edit` | rooms.py:2741, rooms.py:2742, rooms_pre_1_1_20261005_165618.py:2711 | rooms.py:2752, rooms.py:2753, rooms_pre_1_1_20261005_165618.py:2722 |
| `opening_show` | rooms.py:2657, rooms.py:2765, rooms.py:5806 | rooms.py:2724, rooms.py:2725, rooms_pre_1_1_20261005_165618.py:2694 |
| `opening_type` | rooms.py:2670, rooms_pre_1_1_20261005_165618.py:2640, rooms_pre_1_1_20261005_165850.py:2640 | rooms.py:2682, rooms.py:2683, rooms_pre_1_1_20261005_165618.py:2652 |
| `opening_wall` | rooms.py:2690, rooms.py:2691, rooms.py:2692 | rooms.py:2706, rooms.py:2707, rooms_pre_1_1_20261005_165618.py:2676 |
| `openings` | — | rooms.py:4649, rooms_pre_1_1_20261005_165618.py:4241, rooms_pre_1_1_20261005_165850.py:4241 |
| `openings_list` | rooms.py:480, rooms.py:2671, rooms.py:2694 | rooms.py:2642, rooms.py:2643, rooms_pre_1_1_20261005_165618.py:2612 |
| `panel` | misc.py:75, rooms.py:3561, rooms.py:5422 | rooms.py:4554, rooms.py:7856, rooms.py:7857 |
| `panel_add` | rooms.py:6330, rooms_pre_1_1_20261005_165618.py:5676, rooms_pre_1_1_20261005_165850.py:5676 | rooms.py:7837, rooms.py:7838, rooms_pre_1_1_20261005_165618.py:6931 |
| `panel_add_type` | rooms.py:7841, rooms.py:7842, rooms.py:7843 | rooms.py:7810, rooms.py:7811, rooms_pre_1_1_20261005_165618.py:6904 |
| `panel_auto` | rooms.py:7897, rooms_pre_1_1_20261005_165618.py:6991, rooms_pre_1_1_20261005_165850.py:6991 | rooms.py:7488, rooms.py:7489, rooms_pre_1_1_20261005_165618.py:6697 |
| `panel_child_add` | rooms.py:6467, rooms_pre_1_1_20261005_165618.py:5813, rooms_pre_1_1_20261005_165850.py:5813 | rooms.py:6501, rooms.py:6502, rooms_pre_1_1_20261005_165618.py:5847 |
| `panel_child_type` | rooms.py:6504, rooms.py:6505, rooms.py:6506 | rooms.py:6478, rooms.py:6479, rooms_pre_1_1_20261005_165618.py:5824 |
| `panel_children` | rooms.py:6508, rooms.py:7894, rooms_pre_1_1_20261005_165618.py:5854 | rooms.py:6447, rooms.py:6448, rooms_pre_1_1_20261005_165618.py:5793 |
| `panel_comp` | misc.py:76, rooms.py:7518, rooms.py:7556 | rooms.py:7732, rooms.py:7733, rooms_pre_1_1_20261005_165618.py:6827 |
| `panel_comp_add` | rooms.py:7752, rooms.py:7752 | rooms.py:7719, rooms.py:7720, rooms.py:7719 |
| `panel_comp_curve_set` | rooms.py:7702, rooms.py:7703, rooms.py:7704 | rooms.py:7660, rooms.py:7661, rooms.py:7660 |
| `panel_comp_del` | rooms.py:7612, rooms_pre_1_1_20261005_165618.py:6821, rooms_pre_1_1_20261005_165850.py:6821 | rooms.py:7541, rooms.py:7542, rooms_pre_1_1_20261005_165618.py:6750 |
| `panel_comp_item` | rooms.py:5393, rooms.py:7534, rooms.py:7750 | rooms.py:7563, rooms.py:7564, rooms_pre_1_1_20261005_165618.py:6772 |
| `panel_comp_price` | rooms.py:7611, rooms_pre_1_1_20261005_165618.py:6820, rooms_pre_1_1_20261005_165850.py:6820 | rooms.py:7526, rooms.py:7527, rooms_pre_1_1_20261005_165618.py:6735 |
| `panel_comp_rating_manual` | rooms.py:7713, rooms.py:7713 | rooms.py:7642, rooms.py:7643, rooms.py:7642 |
| `panel_comp_rating_set` | rooms.py:7679, rooms.py:7709, rooms.py:7679 | rooms.py:7618, rooms.py:7619, rooms.py:7618 |
| `panel_comp_type` | rooms.py:7722, rooms.py:7723, rooms.py:7724 | rooms.py:7688, rooms.py:7689, rooms.py:7688 |
| `panel_del` | rooms.py:7908, rooms_pre_1_1_20261005_165618.py:7001, rooms_pre_1_1_20261005_165850.py:7001 | rooms.py:7788, rooms.py:7789, rooms_pre_1_1_20261005_165618.py:6882 |
| `panel_est_csv` | rooms.py:7904, rooms_pre_1_1_20261005_165618.py:6997, rooms_pre_1_1_20261005_165850.py:6997 | rooms.py:6729, rooms.py:6730, rooms_pre_1_1_20261005_165618.py:5998 |
| `panel_groups` | rooms.py:7907, rooms_pre_1_1_20261005_165618.py:7000, rooms_pre_1_1_20261005_165850.py:7000 | rooms.py:6342, rooms.py:6343, rooms_pre_1_1_20261005_165618.py:5688 |
| `panel_input` | rooms.py:6383, rooms.py:7896, rooms_pre_1_1_20261005_165618.py:5729 | rooms.py:6419, rooms.py:6420, rooms_pre_1_1_20261005_165618.py:5765 |
| `panel_input_set` | rooms.py:6381, rooms_pre_1_1_20261005_165618.py:5727, rooms_pre_1_1_20261005_165850.py:5727 | rooms.py:6393, rooms.py:6394, rooms_pre_1_1_20261005_165618.py:5739 |
| `panel_input_type` | rooms.py:6433, rooms.py:6434, rooms.py:6435 | rooms.py:6373, rooms.py:6374, rooms_pre_1_1_20261005_165618.py:5719 |
| `panel_montage` | rooms.py:7900, rooms_pre_1_1_20261005_165618.py:6994, rooms_pre_1_1_20261005_165850.py:6994 | rooms.py:6577, rooms.py:6578, rooms_pre_1_1_20261005_165618.py:5923 |
| `panel_pdf` | rooms.py:7903, rooms.py:7903 | rooms.py:6652, rooms.py:6653, rooms.py:6652 |
| `panel_routes` | rooms.py:3432, rooms.py:6238, rooms.py:6543 | rooms.py:6551, rooms.py:6552, rooms_pre_1_1_20261005_165618.py:5897 |
| `panel_routes_auto` | rooms.py:6572, rooms.py:7899, rooms_pre_1_1_20261005_165618.py:5918 | rooms.py:6519, rooms.py:6520, rooms_pre_1_1_20261005_165618.py:5865 |
| `panel_spec` | rooms.py:7902, rooms_pre_1_1_20261005_165618.py:6996, rooms_pre_1_1_20261005_165850.py:6996 | rooms.py:6609, rooms.py:6610, rooms_pre_1_1_20261005_165618.py:5955 |
| `panel_stats` | rooms.py:7906, rooms_pre_1_1_20261005_165618.py:6999, rooms_pre_1_1_20261005_165850.py:6999 | rooms.py:7757, rooms.py:7758, rooms_pre_1_1_20261005_165618.py:6851 |
| `panel_total` | rooms.py:7901, rooms_pre_1_1_20261005_165618.py:6995, rooms_pre_1_1_20261005_165850.py:6995 | rooms.py:6594, rooms.py:6595, rooms_pre_1_1_20261005_165618.py:5940 |
| `panels` | — | rooms.py:4554, rooms_pre_1_1_20261005_165618.py:4152, rooms_pre_1_1_20261005_165850.py:4152 |
| `panels_list` | objects.py:66, rooms.py:5423, rooms.py:7802 | rooms.py:6296, rooms.py:6297, rooms_pre_1_1_20261005_165618.py:5642 |
| `personal_add` | personal.py:44, personal.py:44 | personal.py:69, personal.py:69 |
| `personal_all` | personal.py:48, personal.py:48 | personal.py:58, personal.py:58 |
| `personal_cat` | personal.py:87, personal.py:88, personal.py:89 | misc.py:23, misc.py:24, misc.py:23 |
| `personal_month` | personal.py:47, personal.py:47 | personal.py:47, personal.py:47 |
| `personal_today` | personal.py:45, personal.py:45 | personal.py:25, personal.py:25 |
| `personal_week` | personal.py:46, personal.py:46 | personal.py:36, personal.py:36 |
| `photo_obj` | photos.py:491, photos.py:491 | photos.py:508, photos.py:510, bot.py:227 |
| `photo_stage` | — | photos.py:538, photos.py:540, bot.py:228 |
| `photo_stage_after` | photos.py:525, photos.py:525 | — |
| `photo_stage_before` | photos.py:523, photos.py:523 | — |
| `photo_stage_document` | photos.py:526, photos.py:526 | — |
| `photo_stage_progress` | photos.py:524, photos.py:524 | — |
| `photo_task` | photos.py:559, photos.py:559 | photos.py:575, photos.py:577, bot.py:229 |
| `photo_task_none` | photos.py:555, photos.py:555 | — |
| `photofilt` | — | photos.py:159, bot.py:225, photos.py:159 |
| `photofilt_asgn` | photos.py:385, photos.py:385 | — |
| `photofilt_assignees` | objects.py:135, objects.py:135 | — |
| `photofilt_date` | photos.py:283, photos.py:283 | — |
| `photofilt_dates` | objects.py:133, objects.py:133 | — |
| `photofilt_last` | objects.py:131, objects.py:131 | — |
| `photofilt_task` | photos.py:232, photos.py:232 | — |
| `photofilt_tasks` | objects.py:132, objects.py:132 | — |
| `photofilt_upl` | photos.py:327, photos.py:327 | — |
| `photofilt_uploaders` | objects.py:134, objects.py:134 | — |
| `photopage` | photos.py:141, photos.py:141 | photos.py:425, photos.py:428, bot.py:224 |
| `plumb` | rooms.py:5360, rooms.py:7046, rooms.py:7203 | rooms.py:4566, rooms.py:7135, rooms.py:7137 |
| `plumb_add` | rooms.py:7052, rooms_pre_1_1_20261005_165618.py:6320, rooms_pre_1_1_20261005_165850.py:6320 | rooms.py:7080, rooms.py:7081, rooms_pre_1_1_20261005_165618.py:6348 |
| `plumb_add_type` | rooms.py:7083, rooms.py:7084, rooms.py:7085 | rooms.py:7057, rooms.py:7058, rooms_pre_1_1_20261005_165618.py:6325 |
| `plumb_cost` | rooms.py:7168, rooms_pre_1_1_20261005_165618.py:6421, rooms_pre_1_1_20261005_165850.py:6421 | rooms.py:7474, rooms.py:7475, rooms_pre_1_1_20261005_165618.py:6683 |
| `plumb_cost_obj` | estimates.py:254, rooms.py:7049, rooms_pre_1_1_20261005_165618.py:6318 | rooms.py:7460, rooms.py:7461, rooms_pre_1_1_20261005_165618.py:6669 |
| `plumb_csv_obj` | rooms.py:7051, rooms_pre_1_1_20261005_165618.py:6319, rooms_pre_1_1_20261005_165850.py:6319 | rooms.py:7420, rooms.py:7421, rooms_pre_1_1_20261005_165618.py:6629 |
| `plumb_del` | rooms.py:7173, rooms_pre_1_1_20261005_165618.py:6426, rooms_pre_1_1_20261005_165850.py:6426 | rooms.py:7099, rooms.py:7100, rooms_pre_1_1_20261005_165618.py:6367 |
| `plumb_labor_obj` | rooms.py:7050, rooms.py:7050 | rooms.py:7120, rooms.py:7121, rooms.py:7120 |
| `plumb_list` | objects.py:73, rooms.py:5361, rooms.py:6722 | rooms.py:7026, rooms.py:7027, rooms_pre_1_1_20261005_165618.py:6295 |
| `plumb_pdf_obj` | objects.py:74, objects.py:74 | rooms.py:6706, rooms.py:6707, rooms.py:6706 |
| `plumb_point_add` | rooms.py:7317, rooms.py:7317 | rooms.py:7322, rooms.py:7323, rooms.py:7322 |
| `plumb_point_set` | rooms.py:7336, rooms.py:7336 | rooms.py:7341, rooms.py:7342, rooms.py:7341 |
| `plumb_point_unset` | — | rooms.py:7353, rooms.py:7354, rooms.py:7353 |
| `plumb_points` | rooms.py:7169, rooms.py:7337, rooms_pre_1_1_20261005_165618.py:6422 | rooms.py:7307, rooms.py:7308, rooms_pre_1_1_20261005_165618.py:6560 |
| `plumb_route` | rooms.py:5267, rooms.py:7200, rooms_pre_1_1_20261005_165618.py:4826 | rooms.py:7270, rooms.py:7272, rooms_pre_1_1_20261005_165618.py:6523 |
| `plumb_route_del` | rooms.py:7301, rooms_pre_1_1_20261005_165618.py:6554, rooms_pre_1_1_20261005_165850.py:6554 | rooms.py:7247, rooms.py:7248, rooms_pre_1_1_20261005_165618.py:6500 |
| `plumb_route_new` | rooms.py:7167, rooms.py:7202, rooms_pre_1_1_20261005_165618.py:6420 | rooms.py:7207, rooms.py:7208, rooms_pre_1_1_20261005_165618.py:6460 |
| `plumb_route_pipe` | rooms.py:7212, rooms.py:7213, rooms.py:7214 | rooms.py:7230, rooms.py:7231, rooms_pre_1_1_20261005_165618.py:6483 |
| `plumb_routes` | rooms.py:5266, rooms.py:7166, rooms.py:7219 | rooms.py:7179, rooms.py:7180, rooms_pre_1_1_20261005_165618.py:6432 |
| `plumb_spec` | rooms.py:7170, rooms_pre_1_1_20261005_165618.py:6423, rooms_pre_1_1_20261005_165850.py:6423 | rooms.py:7380, rooms.py:7381, rooms_pre_1_1_20261005_165618.py:6589 |
| `plumb_water` | rooms.py:7048, rooms_pre_1_1_20261005_165618.py:6317, rooms_pre_1_1_20261005_165850.py:6317 | rooms.py:7365, rooms.py:7366, rooms_pre_1_1_20261005_165618.py:6574 |
| `prefix` | — | map_scan.py:58 |
| `prices` | — | rooms.py:4560, rooms_pre_1_1_20261005_165618.py:4158, rooms_pre_1_1_20261005_165850.py:4158 |
| `prices_history` | document.py:80, rooms.py:6841, rooms_pre_1_1_20261005_165618.py:6110 | rooms.py:6858, rooms.py:6859, rooms_pre_1_1_20261005_165618.py:6127 |
| `prices_import` | document.py:79, objects.py:76, rooms.py:6867 | rooms.py:6816, rooms.py:6817, rooms_pre_1_1_20261005_165618.py:6085 |
| `receipt_cat` | receipt.py:156, receipt.py:157, receipt.py:158 | receipt.py:171, bot.py:240, receipt.py:171 |
| `receipt_obj` | receipt.py:128, receipt.py:128 | receipt.py:143, bot.py:239, receipt.py:143 |
| `receipt_save` | receipt.py:91, receipt.py:91 | receipt.py:116, bot.py:238, receipt.py:116 |
| `receipt_show` | receipt.py:212, receipt.py:212 | receipt.py:223, bot.py:241, receipt.py:223 |
| `recognize_receipt` | photos.py:493, receipt.py:45, photos.py:493 | bot.py:237 |
| `report_choose_object` | reports.py:35, reports.py:35 | reports.py:82, reports.py:82 |
| `report_closed_month` | reports.py:30, reports.py:30 | reports.py:55, reports.py:55 |
| `report_closed_week` | reports.py:29, reports.py:29 | reports.py:55, reports.py:56, reports.py:55 |
| `report_obj` | reports.py:88, reports.py:108, reports.py:109 | reports.py:97, reports.py:99, reports.py:97 |
| `report_open` | reports.py:31, reports.py:31 | reports.py:69, reports.py:69 |
| `report_summary` | — | reports.py:41, reports.py:42, reports.py:41 |
| `report_summary_all` | reports.py:34, reports.py:34 | — |
| `report_summary_month` | reports.py:32, reports.py:32 | — |
| `report_summary_week` | reports.py:33, reports.py:33 | — |
| `room` | misc.py:28, rooms.py:455, rooms.py:576 | rooms.py:4676, rooms.py:4678, rooms_pre_1_1_20261005_165618.py:4268 |
| `room_add` | rooms.py:456, rooms.py:3155, rooms_pre_1_1_20261005_165618.py:456 | rooms.py:4434, rooms.py:4435, rooms_pre_1_1_20261005_165618.py:4047 |
| `room_comms` | rooms.py:481, rooms.py:2292, rooms.py:2315 | rooms.py:2282, rooms.py:2283, rooms.py:4643 |
| `room_del` | rooms.py:490, rooms_pre_1_1_20261005_165618.py:489, rooms_pre_1_1_20261005_165850.py:489 | rooms.py:4483, rooms.py:4484, rooms_pre_1_1_20261005_165618.py:4081 |
| `room_delok` | rooms.py:4493, rooms_pre_1_1_20261005_165618.py:4091, rooms_pre_1_1_20261005_165850.py:4091 | rooms.py:4501, rooms.py:4502, rooms_pre_1_1_20261005_165618.py:4099 |
| `room_estimate` | rooms.py:485, rooms.py:485 | rooms.py:3714, rooms.py:3715, bot.py:244 |
| `room_export` | rooms.py:487, rooms.py:3917, rooms.py:3967 | rooms.py:3975, rooms.py:3976, rooms.py:4637 |
| `room_export_csv` | rooms.py:3983, rooms.py:4106, rooms_pre_1_1_20261005_165618.py:3700 | rooms.py:3952, rooms.py:3953, rooms_pre_1_1_20261005_165618.py:3669 |
| `room_export_dxf` | rooms.py:3980, rooms.py:4002, rooms_pre_1_1_20261005_165618.py:3697 | rooms.py:3942, rooms.py:3943, rooms_pre_1_1_20261005_165618.py:3659 |
| `room_export_json` | rooms.py:3981, rooms.py:4170, rooms_pre_1_1_20261005_165618.py:3698 | rooms.py:3947, rooms.py:3948, rooms_pre_1_1_20261005_165618.py:3664 |
| `room_export_pdf` | rooms.py:3982, rooms_pre_1_1_20261005_165618.py:3699, rooms_pre_1_1_20261005_165850.py:3699 | rooms.py:3957, rooms_pre_1_1_20261005_165618.py:3674, rooms_pre_1_1_20261005_165850.py:3674 |
| `room_groups` | rooms.py:488, rooms.py:3566, rooms.py:3621 | rooms.py:3577, rooms.py:3578, rooms.py:4621 |
| `room_height` | — | rooms.py:4666, rooms_pre_1_1_20261005_165618.py:4258, rooms_pre_1_1_20261005_165850.py:4258 |
| `room_height_ask` | rooms.py:4833, rooms.py:4850, rooms_pre_1_1_20261005_165618.py:4425 | rooms.py:4940, rooms.py:4941, rooms_pre_1_1_20261005_165618.py:4513 |
| `room_height_same` | rooms.py:618, rooms_pre_1_1_20261005_165618.py:617, rooms_pre_1_1_20261005_165850.py:617 | rooms.py:4996, rooms_pre_1_1_20261005_165618.py:4569, rooms_pre_1_1_20261005_165850.py:4569 |
| `room_height_same_start` | rooms.py:4948, rooms_pre_1_1_20261005_165618.py:4521, rooms_pre_1_1_20261005_165850.py:4521 | rooms.py:4957, rooms.py:4958, rooms_pre_1_1_20261005_165618.py:4530 |
| `room_height_three_start` | rooms.py:4832, rooms.py:4949, rooms_pre_1_1_20261005_165618.py:4424 | rooms.py:4984, rooms.py:4985, rooms_pre_1_1_20261005_165618.py:4557 |
| `room_measures` | rooms.py:478, rooms.py:1173, rooms.py:1206 | rooms.py:4516, rooms.py:4517, rooms_pre_1_1_20261005_165618.py:4114 |
| `room_objects` | rooms.py:482, rooms_pre_1_1_20261005_165618.py:482, rooms_pre_1_1_20261005_165850.py:482 | rooms.py:4521, rooms.py:4522, rooms_pre_1_1_20261005_165618.py:4119 |
| `room_photos` | rooms.py:484, rooms_pre_1_1_20261005_165618.py:484, rooms_pre_1_1_20261005_165850.py:484 | rooms.py:4539, rooms.py:4540, rooms_pre_1_1_20261005_165618.py:4137 |
| `room_plan` | rooms.py:3737, rooms.py:3916, rooms.py:3927 | rooms.py:3861, rooms.py:3862, rooms.py:4631 |
| `room_progress` | rooms.py:479, rooms_pre_1_1_20261005_165618.py:479, rooms_pre_1_1_20261005_165850.py:479 | rooms.py:4511, rooms.py:4512, rooms_pre_1_1_20261005_165618.py:4109 |
| `room_rename` | rooms.py:489, rooms_pre_1_1_20261005_165618.py:488, rooms_pre_1_1_20261005_165850.py:488 | rooms.py:4411, rooms.py:4412, rooms_pre_1_1_20261005_165618.py:4024 |
| `room_report` | — | rooms.py:4626, rooms_pre_1_1_20261005_165618.py:4218, rooms_pre_1_1_20261005_165850.py:4218 |
| `room_report_electric` | rooms.py:3738, rooms_pre_1_1_20261005_165618.py:3455, rooms_pre_1_1_20261005_165850.py:3455 | rooms.py:3757, rooms.py:3758, rooms_pre_1_1_20261005_165618.py:3474 |
| `room_report_painter` | rooms.py:3741, rooms_pre_1_1_20261005_165618.py:3458, rooms_pre_1_1_20261005_165850.py:3458 | rooms.py:3762, rooms_pre_1_1_20261005_165618.py:3479, rooms_pre_1_1_20261005_165850.py:3479 |
| `room_report_pdf` | rooms.py:3743, rooms_pre_1_1_20261005_165618.py:3460, rooms_pre_1_1_20261005_165850.py:3460 | rooms.py:3762, rooms_pre_1_1_20261005_165618.py:3479, rooms_pre_1_1_20261005_165850.py:3479 |
| `room_report_plumbing` | rooms.py:3739, rooms_pre_1_1_20261005_165618.py:3456, rooms_pre_1_1_20261005_165850.py:3456 | rooms.py:3762, rooms_pre_1_1_20261005_165618.py:3479, rooms_pre_1_1_20261005_165850.py:3479 |
| `room_report_spec` | rooms.py:3742, rooms_pre_1_1_20261005_165618.py:3459, rooms_pre_1_1_20261005_165850.py:3459 | rooms.py:3762, rooms_pre_1_1_20261005_165618.py:3479, rooms_pre_1_1_20261005_165850.py:3479 |
| `room_report_tiler` | rooms.py:3740, rooms_pre_1_1_20261005_165618.py:3457, rooms_pre_1_1_20261005_165850.py:3457 | rooms.py:3762, rooms_pre_1_1_20261005_165618.py:3479, rooms_pre_1_1_20261005_165850.py:3479 |
| `room_reports` | rooms.py:486, rooms.py:3771, rooms.py:3841 | rooms.py:3731, rooms.py:3732, rooms.py:4626 |
| `room_start` | rooms.py:470, rooms.py:472, rooms.py:474 | rooms.py:4661, rooms.py:4662, rooms_pre_1_1_20261005_165618.py:4253 |
| `room_tasks` | rooms.py:483, rooms_pre_1_1_20261005_165618.py:483, rooms_pre_1_1_20261005_165850.py:483 | rooms.py:4526, rooms.py:4527, rooms_pre_1_1_20261005_165618.py:4124 |
| `room_total_walls` | rooms.py:4868, rooms.py:4869, rooms.py:4870 | rooms.py:3679, rooms.py:3680, rooms.py:3679 |
| `room_type` | rooms.py:24, rooms.py:25, rooms.py:26 | rooms.py:4463, rooms.py:4464, rooms_pre_1_1_20261005_165618.py:4063 |
| `rooms_list_obj` | rooms.py:27, rooms.py:491, rooms.py:4456 | rooms.py:4428, rooms.py:4429, rooms_pre_1_1_20261005_165618.py:4041 |
| `route` | rooms.py:3363, rooms.py:3380, rooms.py:3399 | rooms.py:3439, rooms.py:3441, rooms_pre_1_1_20261005_165618.py:3290 |
| `route_del` | rooms.py:6232, rooms_pre_1_1_20261005_165618.py:5622, rooms_pre_1_1_20261005_165850.py:5622 | rooms.py:3417, rooms.py:3418, rooms_pre_1_1_20261005_165618.py:3268 |
| `route_edit_len` | rooms.py:6230, rooms_pre_1_1_20261005_165618.py:5620, rooms_pre_1_1_20261005_165850.py:5620 | rooms.py:3372, rooms.py:3373, rooms_pre_1_1_20261005_165618.py:3223 |
| `route_edit_type` | rooms.py:6231, rooms_pre_1_1_20261005_165618.py:5621, rooms_pre_1_1_20261005_165850.py:5621 | rooms.py:3387, rooms.py:3388, rooms_pre_1_1_20261005_165618.py:3238 |
| `route_set_type` | rooms.py:3394, rooms.py:3395, rooms.py:3396 | rooms.py:3406, rooms.py:3407, rooms_pre_1_1_20261005_165618.py:3257 |
| `setassigned` | tasks.py:431, tasks.py:432, tasks.py:431 | tasks.py:448, tasks.py:451, tasks.py:448 |
| `setdate` | tasks.py:258, tasks.py:259, tasks.py:260 | tasks.py:733, tasks.py:733 |
| `setduration` | tasks.py:264, tasks.py:264 | tasks.py:479, tasks.py:481, tasks.py:479 |
| `setprio` | tasks.py:273, tasks.py:274, tasks.py:275 | tasks.py:768, tasks.py:768 |
| `setrange` | tasks.py:263, tasks.py:263 | tasks.py:465, tasks.py:467, tasks.py:465 |
| `setrole` | onboarding.py:54 | onboarding.py:80, onboarding.py:82 |
| `skip_photo` | tasks.py:159, tasks.py:159 | tasks.py:169, bot.py:226, tasks.py:169 |
| `task` | _legacy.py:167, tasks.py:46, tasks.py:88 | tasks.py:680, tasks.py:680 |
| `taskaddprog` | tasks.py:413, tasks.py:413 | tasks.py:374, tasks.py:375, tasks.py:374 |
| `taskaddprogskip` | misc.py:93, misc.py:93 | tasks.py:355, tasks.py:356, tasks.py:355 |
| `taskassign` | tasks.py:238, tasks.py:238 | tasks.py:422, tasks.py:424, tasks.py:422 |
| `taskdate` | tasks.py:232, tasks.py:232 | tasks.py:689, tasks.py:689 |
| `taskdate_manual` | tasks.py:265, tasks.py:265 | — |
| `taskdel` | tasks.py:248, tasks.py:248 | tasks.py:642, tasks.py:642 |
| `taskdelconfirm` | tasks.py:652, tasks.py:652 | tasks.py:660, tasks.py:661, tasks.py:660 |
| `taskdelhard` | tasks.py:244, tasks.py:244 | tasks.py:627, tasks.py:628, tasks.py:627 |
| `taskdelhardconfirm` | tasks.py:634, tasks.py:634 | tasks.py:614, tasks.py:615, tasks.py:614 |
| `taskdone` | tasks.py:247, tasks.py:247 | tasks.py:588, tasks.py:588 |
| `taskjournal` | tasks.py:237, tasks.py:382, misc.py:116 | tasks.py:389, tasks.py:390, tasks.py:389 |
| `tasknodate` | tasks.py:235, tasks.py:235 | tasks.py:717, tasks.py:718, tasks.py:717 |
| `taskprio` | tasks.py:239, tasks.py:239 | tasks.py:759, tasks.py:759 |
| `taskrename` | tasks.py:240, tasks.py:240 | tasks.py:781, tasks.py:781 |
| `taskrestore` | tasks.py:243, tasks.py:243 | tasks.py:600, tasks.py:601, tasks.py:600 |
| `tasks_archive_list` | _legacy.py:177, tasks.py:245, tasks.py:622 | tasks.py:26, tasks.py:26 |
| `tasks_byobj` | _legacy.py:178, tasks.py:117, _legacy.py:178 | tasks.py:14, tasks.py:14 |
| `unknown_as_client` | fallback.py:49, fallback.py:49 | crm.py:502, crm.py:502 |
| `unknown_as_expense` | fallback.py:51, fallback.py:51 | crm.py:535, crm.py:535 |
| `unknown_as_object` | fallback.py:48, fallback.py:48 | crm.py:400, crm.py:400 |
| `unknown_as_personal` | fallback.py:52, fallback.py:52 | crm.py:563, crm.py:563 |
| `unknown_as_task` | fallback.py:50, fallback.py:50 | crm.py:516, crm.py:516 |
| `unknown_cancel` | crm.py:453, crm.py:528, fallback.py:53 | crm.py:590, crm.py:590 |
| `unknown_object_create_confirmed` | crm.py:451, crm.py:451 | crm.py:481, crm.py:481 |
| `unknown_task_obj` | crm.py:526, crm.py:526 | crm.py:595, crm.py:596, crm.py:595 |
| `wall_niche` | — | rooms.py:4655, rooms_pre_1_1_20261005_165618.py:4247, rooms_pre_1_1_20261005_165850.py:4247 |
| `wall_niche_count` | rooms.py:923, rooms.py:924, rooms.py:925 | rooms.py:1439, rooms.py:1440, rooms_pre_1_1_20261005_165618.py:1438 |
| `wall_niche_plane_irr` | rooms.py:1044, rooms.py:2175, rooms_pre_1_1_20261005_165618.py:1043 | rooms.py:1476, rooms.py:1477, rooms_pre_1_1_20261005_165618.py:1475 |
| `wall_niche_plane_rect` | rooms.py:1043, rooms.py:2174, rooms_pre_1_1_20261005_165618.py:1042 | rooms.py:1452, rooms.py:1453, rooms_pre_1_1_20261005_165618.py:1451 |
| `wall_round` | — | rooms.py:4655, rooms_pre_1_1_20261005_165618.py:4247, rooms_pre_1_1_20261005_165850.py:4247 |
| `wall_round_angle` | rooms.py:860, rooms.py:861, rooms.py:862 | rooms.py:1370, rooms.py:1371, rooms.py:1381 |
| `wall_round_angle_deg` | rooms.py:863, rooms_pre_1_1_20261005_165618.py:862, rooms_pre_1_1_20261005_165850.py:862 | rooms.py:1419, rooms.py:1420, rooms_pre_1_1_20261005_165618.py:1418 |
| `wall_round_flag` | — | rooms.py:1256, rooms.py:1257, rooms_pre_1_1_20261005_165618.py:1255 |
| `wall_round_flag_hidden` | rooms.py:672, rooms_pre_1_1_20261005_165618.py:671, rooms_pre_1_1_20261005_165850.py:671 | — |
| `wall_round_flag_niche` | rooms.py:669, rooms_pre_1_1_20261005_165618.py:668, rooms_pre_1_1_20261005_165850.py:668 | — |
| `wall_round_flag_rounded` | rooms.py:670, rooms_pre_1_1_20261005_165618.py:669, rooms_pre_1_1_20261005_165850.py:669 | — |
| `wall_round_flag_wavy` | rooms.py:671, rooms_pre_1_1_20261005_165618.py:670, rooms_pre_1_1_20261005_165850.py:670 | — |
| `wall_round_flags_done` | rooms.py:673, rooms_pre_1_1_20261005_165618.py:672, rooms_pre_1_1_20261005_165850.py:672 | rooms.py:1271, rooms.py:1272, rooms_pre_1_1_20261005_165618.py:1270 |
| `wall_round_open_door` | rooms.py:824, rooms.py:2139, rooms.py:2267 | rooms.py:1352, rooms.py:1353, rooms_pre_1_1_20261005_165618.py:1351 |
| `wall_round_open_vent` | rooms.py:825, rooms.py:2140, rooms.py:2268 | rooms.py:1356, rooms.py:1357, rooms_pre_1_1_20261005_165618.py:1355 |
| `wall_round_open_win` | rooms.py:823, rooms.py:2138, rooms.py:2266 | rooms.py:1348, rooms.py:1349, rooms_pre_1_1_20261005_165618.py:1347 |
| `wall_round_openings_done` | rooms.py:826, rooms.py:1719, rooms.py:1734 | rooms.py:1360, rooms.py:1361, rooms_pre_1_1_20261005_165618.py:1359 |
| `wall_round_plane_straight` | rooms.py:762, rooms_pre_1_1_20261005_165618.py:761, rooms_pre_1_1_20261005_165850.py:761 | rooms.py:1300, rooms.py:1301, rooms_pre_1_1_20261005_165618.py:1299 |
| `wall_round_plane_wavy` | rooms.py:763, rooms_pre_1_1_20261005_165618.py:762, rooms_pre_1_1_20261005_165850.py:762 | rooms.py:1310, rooms.py:1311, rooms_pre_1_1_20261005_165618.py:1309 |
| `wall_round_reset` | rooms.py:1495, rooms_pre_1_1_20261005_165618.py:1494, rooms_pre_1_1_20261005_165850.py:1494 | rooms.py:1238, rooms.py:1239, rooms_pre_1_1_20261005_165618.py:1237 |
| `wall_round_skip` | rooms.py:674, rooms_pre_1_1_20261005_165618.py:673, rooms_pre_1_1_20261005_165850.py:673 | rooms.py:1280, rooms.py:1281, rooms_pre_1_1_20261005_165618.py:1279 |
| `wall_round_start` | rooms.py:1172, rooms.py:2117, rooms.py:5506 | rooms.py:1232, rooms.py:1233, rooms_pre_1_1_20261005_165618.py:1231 |
| `works` | rooms.py:5299, rooms.py:6974, rooms.py:6990 | rooms.py:6997, rooms.py:6999, rooms_pre_1_1_20261005_165618.py:6266 |
| `works_add` | rooms.py:6889, rooms_pre_1_1_20261005_165618.py:6158, rooms_pre_1_1_20261005_165850.py:6158 | rooms.py:6915, rooms.py:6916, rooms_pre_1_1_20261005_165618.py:6184 |
| `works_add_type` | rooms.py:6918, rooms.py:6919, rooms.py:6920 | rooms.py:6895, rooms.py:6896, rooms_pre_1_1_20261005_165618.py:6164 |
| `works_del` | rooms.py:7019, rooms_pre_1_1_20261005_165618.py:6288, rooms_pre_1_1_20261005_165850.py:6288 | rooms.py:6942, rooms.py:6943, rooms_pre_1_1_20261005_165618.py:6211 |
| `works_edit_price` | rooms.py:7018, rooms_pre_1_1_20261005_165618.py:6287, rooms_pre_1_1_20261005_165850.py:6287 | rooms.py:6981, rooms.py:6982, rooms_pre_1_1_20261005_165618.py:6250 |
| `works_edit_qty` | rooms.py:7017, rooms_pre_1_1_20261005_165618.py:6286, rooms_pre_1_1_20261005_165850.py:6286 | rooms.py:6963, rooms.py:6964, rooms_pre_1_1_20261005_165618.py:6232 |
| `works_list` | objects.py:75, rooms.py:5331, rooms.py:6908 | rooms.py:6873, rooms.py:6874, rooms_pre_1_1_20261005_165618.py:6142 |
