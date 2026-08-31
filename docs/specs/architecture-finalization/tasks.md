# Tasks and verification

## Задачи и проверки

- [x] Канонизировать DTO, ошибки, AppConfig и три внешних порта.
- [x] Реализовать и подключить `GlowLinkApplication` во всех presentation entry points.
- [x] Удалить параллельные use cases, DTO, legacy stores и re-export фасады.
- [x] Сделать config schema tolerant и атомарным.
- [x] Сериализовать BLE и исправить color/sync lifecycle desktop.
- [x] Добавить тест архитектурных границ и поведенческие тесты.
- [x] Синхронизировать ADR и architecture docs.
- [ ] Выполнить hardware checklist и перевести спецификацию в `verified`.

## Реализация

Application facade, bootstrap и три порта являются единственным runtime-путём. Desktop timers
и потоки на каждое действие заменены задачами одного bridge. Unified config получил schema v1.

Выполнено из `app/`:

- `python -m pytest -q`: 67 passed;
- `python -m ruff check src tests`: passed;
- `python -m ruff format --check src tests`: passed;
- `python -m mypy src`: passed;
- `python -m build`: sdist и wheel собраны;
- установка wheel в отдельный venv и `ledsetup --help`: passed.

## Результаты проверки

| Критерий или задача | Доказательство | Статус |
| --- | --- | --- |
| Границы слоёв | `tests/test_architecture.py` | Пройдено |
| Application и config | fake-port и config-store tests | Пройдено |
| Desktop color/sync lifecycle | `test_web_ui.py` | Пройдено |
| Физическая лента | [hardware checklist](../../hardware-tests/architecture-finalization.md) | Ожидает прогона |

## Синхронизированная документация

`docs/architecture.md`, ADR 0005/0006/0007, ADR index, README и CHANGELOG.
