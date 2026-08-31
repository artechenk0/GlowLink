# Стандарт разработки

## Структура и архитектура

Пакет Python расположен в `app/src/ledsetup/`, тесты — в `app/tests/`, desktop-ресурсы — в
`app/src/ledsetup/web/`.

Держите точки входа и UI-адаптеры в `cli.py`, `gui.py`, `gui_api.py`, `gui_bridge.py` и `web/`.
Сценарий, общий для нескольких интерфейсов, выносите в модуль приложения. Кадры LEDnetWF
находятся в `protocol.py`, BLE/GATT-транспорт — в `ble.py`, удерживаемые соединения — в
`session.py`, системная интеграция — в адаптерах, например `capture.py` и `paths.py`.

Зависимости направлены вниз: UI → сценарии приложения → домен → системные адаптеры. UI не
обращается к `BleakClient`, GATT или UUID напрямую.

## Код и проверки

Работайте из `app/` с Python 3.11+:

```powershell
python -m pip install -e ".[test]"
python -m pytest
python -m ruff check src tests
python -m mypy src
python -m ledsetup --help
```

Используйте четыре пробела, type annotations в production-коде, `snake_case`, `PascalCase`,
`UPPER_SNAKE_CASE` и строки до 100 символов.

Добавляйте unit-тесты в `app/tests/test_<module>.py`. Для BLE и экрана используйте `fake_ble.py`
и `fake_screen.py`, поэтому автоматические тесты не требуют оборудования. Интеграционные тесты
проверяют границы между сценариями и адаптерами через фейки.

## Изменения и pull request

Одна ветка и один pull request решают одну логическую задачу. Не смешивайте функциональное
изменение с несвязанным рефакторингом. Следуйте [Gitflow](gitflow.md); в Codex ветки имеют
префикс `codex/`.

В PR укажите поведение, связанную issue, выполненные проверки и ограничения. Для GUI приложите
скриншот. Для BLE укажите модель устройства, команды и результат ручной проверки.
