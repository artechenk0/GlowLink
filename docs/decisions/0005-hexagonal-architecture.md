# 0005. Hexagonal Architecture / Ports & Adapters

Статус: Superseded by [0007](0007-lightweight-layered-architecture.md)
Дата: 2026-08-31

## Контекст

В старой структуре BLE, захват экрана, persistence и presentation были доступны через
корневые модули и могли смешиваться в сценариях.

## Решение

Канонической структурой являются `domain`, `application`, `adapters`, `presentation` и
`bootstrap`. Application зависит только от Protocol-портов, конкретные реализации создаются в
`bootstrap/composition_root.py`, а корневые модули сохраняются как совместимые фасады на период
миграции.

## Последствия

Domain и application тестируются без BLE, mss, webview и Windows. CLI и GUI используют одни
use cases. Полное удаление фасадов допускается после миграции внешних потребителей и hardware
проверки BLE-сценариев.
