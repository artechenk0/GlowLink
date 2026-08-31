# Technical

`GlowLinkApplication` координирует три Protocol-порта: BLE, screen и config repository. Он
владеет сериализующим `asyncio.Lock`, auto-connect, monitor resolution и единственным sync-loop.
Bootstrap создаёт Bleak session, MSS grabber и atomic JSON store.

Desktop использует один `AsyncBridge`. Color picker обслуживается одним latest-value worker;
каждый sync получает отдельный stop token. Bridge при закрытии отменяет задачи, дожидается их,
останавливает thread и закрывает event loop.

`config.json` записывается со `schema_version = 1`; файл без версии считается v1. Каждое поле
валидируется отдельно, unknown keys игнорируются. Старые раздельные файлы не читаются.

Проверка включает domain/adapter/application/presentation тесты, AST dependency test, Ruff,
strict mypy, build/install smoke и ручной прогон на физической ленте.
