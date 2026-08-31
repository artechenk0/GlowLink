# GlowLink

GlowLink управляет одной аналоговой RGB-подсветкой через BLE-контроллер из
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
а не рекламируемое имя: имя может меняться. Если контроллер занят, закройте другое приложение,
удерживающее Bluetooth-соединение, и отключите его в настройках Windows.

## Установка готовой версии

На странице [Releases](../../releases) скачайте `GlowLink.exe` из раздела Assets и запустите
его двойным кликом. Python и отдельная установка пакета не нужны. Для окна управления требуется
Microsoft Edge WebView2 Runtime; он обычно уже установлен в Windows 10 и 11.

## Командная строка

```powershell
ledsetup scan
ledsetup color 255 40 40
ledsetup off
ledsetup sync --monitor 1
ledsetup gatt
```

После `scan` используется сохранённый адрес; для разового вызова передайте
`--address AA:BB:CC:DD:EE:FF`. `sync` передаёт средний цвет выбранного монитора на всю ленту и
не является Ambilight. Остановите его кнопкой окна или `Ctrl+C`.

RGB и `off` визуально проверены на совместимом аналоговом RGB-контроллере и являются
поддерживаемыми операциями продукта. Статус совместимости — в [матрице](docs/device-compatibility.md),
низкоуровневые данные — в [заметках протокола](docs/protocol-notes.md).

## Разработка и лицензия

Выполняйте `python -m pytest`, `python -m ruff check src tests` и `python -m mypy src` из
`app/`. CLI, menu и GUI используют единый application facade; внешние BLE, screen и storage
реализации подключаются в bootstrap. Подробнее — в [описании архитектуры](docs/architecture.md).
Для изменений поведения и архитектуры следуйте [SDD-гайду](docs/sdd.md). Правила участия — в
[CONTRIBUTING.md](CONTRIBUTING.md). Проект лицензирован по [MIT](LICENSE).
