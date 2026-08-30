# LEDSetup

LEDSetup управляет одной аналоговой RGB-лентой Zengge LEDnetWF по Bluetooth Low Energy из
Windows. Лента получает один общий цвет; адресные ленты, сегменты и подсветка периметра не
поддерживаются. Полные границы продукта — в [product scope](docs/product-scope.md).

## Требования и запуск

- Windows с Bluetooth LE;
- Python 3.12+;
- совместимый контроллер и аналоговая RGB-лента.

```powershell
cd app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
ledsetup
```

Нажмите **«Найти ленту»**, выберите устройство и подключитесь. Приложение сохраняет BLE-адрес,
а не рекламируемое имя: имя может меняться. Если контроллер занят, закройте ZENGGE и отключите
его в настройках Windows.

## Командная строка

```powershell
ledsetup scan
ledsetup color 255 40 40
ledsetup off
ledsetup sync --monitor 1
ledsetup gatt
```

После `scan` используется сохранённый адрес; для разового вызова передайте
`--address E4:98:BB:6B:1A:AC`. `sync` передаёт средний цвет выбранного монитора на всю ленту и
не является Ambilight. Остановите его кнопкой окна или `Ctrl+C`.

RGB и `off` визуально проверены на Smartbuy `SBL-RGBW-KIT-75`; `on` и `color --hsv` остаются
экспериментальными. Статус устройств — в [матрице совместимости](docs/device-compatibility.md),
низкоуровневые данные — в [заметках протокола](docs/protocol-notes.md).

## Разработка и лицензия

Выполняйте `python -m pytest`, `python -m ruff check src tests` и `python -m mypy src` из
`app/`. Правила участия — в [CONTRIBUTING.md](CONTRIBUTING.md). Проект лицензирован по
[MIT](LICENSE).
