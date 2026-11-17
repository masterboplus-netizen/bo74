# Инвентаризация: css/layout.css

**Дата:** 14.11.2026  
**Файл:** `css/layout.css`  
**Статус:** Полный исходный слепок (879 строк). Порядок правил сохранен 1-в-1.  
**Правило:** Запрещено менять порядок функций и удалять существующие блоки.

---

## Блок 1. Дашборд и кнопки
- `.topbar` (sticky, flex, z-index)
- `.logo`
- `.btn-icon`, `.btn-icon:active`
- `#content` (padding, flex)

## Блок 2. Загрузка
- `#loading`
- `.spinner`
- `@keyframes spin` *(битый фрагмент `to { transform: rotate(360deg); }`)*

## Блок 3. Секции и прогресс-бары
- `.section`, `.section-title`, `.pbar-row`, `.pbar-name`, `.pbar-track`, `.pbar-fill`, `.pbar-pct`
- `.empty`, `.empty-icon`, `.footer`
- `#content` (max-width 720px)

## Блок 4. Вкладки и Дневник
- `.tab.tab-active`, `.tab:active`
- `#content-diary`
- `.period-filter`, `.lbl-date`, `.lbl-dow`
- `.section-title` (margin-top)

## Блок 5. Футер, цели и аналитика
- `.footer-line`, `.footer-authors`
- `.edit-goal`
- `@keyframes fadeIn` *(битый)*, `@keyframes slideUp` *(битый)*
- `#goal-input`
- `.analytics-sheet`, `.trend-up`, `.trend-down`, `.trend-neutral`
- `.logo`, `.logo-icon`

## Блок 6. Sticky-шапка и табы
- `.topbar` (sticky z-index)
- `.tab.tab-active`, `.tab svg`
- `body` (padding-bottom)

## Блок 7. Проекты и Активность
- `#content-projects`
- `#content-activity` (три переопределения подряд)
- `#content-activity h2`

## Блок 8. Экран загрузки с логотипом
- `#loading` (flex)
- `#loading .spinner`
- `#loading::before`, `#loading::after`
- `#loading .loading-footer`

## Блок 9. Меню и фильтры
- `.tab svg` (размеры)
- `#content...` (padding-bottom 0)
- `.lbl-date`, `.lbl-dow`
- `#content...` (padding-top 16px)
- `div[style*="justify-content"]` (центровка)
- `.top-filter-row` + `nth-child(1..4)` + `.active`

## Блок 10. Тултипы
- `.floating-tooltip`, `.floating-tooltip::after`

## Блок 11. Фиксы пустоты и скролла (каша)
- `#content-activity` (убираем отступ внизу)
- `#content-activity` (min-height calc)
- `#loading` (display: none)
- `html, body` (overflow: hidden)
- `#dashboard` (height 100%)
- `#content...` (overflow-y auto)
- `#content-activity` (min-height: 0)
- `body` (height 100vh)
- `#dashboard` (height calc)
- `#content...` (overflow-y auto)
- `body` (overflow: auto) — *откат*
- `#dashboard` (overflow: visible)
- `#content...` (overflow-y visible)
- `html, body` (overflow: auto) — *откат*
- `#dashboard` (overflow: visible)
- `#content...` (overflow-y visible)

## Блок 12. Анимации колец (очень много дублей)
- Множество `@keyframes pulse` без имен
- `@keyframes breathe`, `@keyframes ring-breathe`
- Битые фрагменты `100% { ... }` без объявления `@keyframes`

## Блок 13. Сейф (Крутилки и Пин-пад)
- `#scroll-pin-screen` (и `.active`)
- `.scroll-wheels-container::before`
- `.scroll-wheel` (и `::-webkit-scrollbar`)
- `.wheel-item`, `.wheel-item.active`, `.wheel-spacer`
- `#scroll-pin-screen` (жесткий фикс)
- `#safe-dial-container`
- `#scroll-pin-screen` (touch-action)
- `#scroll-pin-screen` (слепой сейф)
- `#safe-dial-rotator`
- `#safe-dial-lens`, `.active`
- `#safe-timer`
- `.segmented-control` (и `.segmented-control button`) — *файл обрывается на этой строке*

---

## Известные проблемы исходного файла
1. **Битые `@keyframes`** — отсутствуют заголовки `@keyframes name { ... }`, остались только блоки `to {...}`.
2. **Конфликт фиксов скролла** — блок 11 содержит 3 цикла "фикс → откат", из-за чего глобальный скролл в итоге разрешен (`overflow: auto`), что и дает "уход в пустоту".
3. **Дубли `#content-activity`** — 5 разных определений.
4. **Обрыв файла** — последняя строка `.segmented-control { display: flex;` не закрыта.

## Что делаем дальше
- [ ] Патчим Блок 11 (фиксы скролла): убираем откаты, оставляем `overflow: hidden` для `body` и `overflow-y: auto` для вкладок.
- [ ] Оставляем Блок 13 (Сейф) без изменений.
- [ ] Чистим битые `@keyframes` (Блок 2, 5, 12) — **не меняя порядок**, просто добавляем заголовки, чтобы анимации заработали.