# Technical

`Session.is_connected` остаётся источником состояния. UI получает готовое поле `connected` через
UI-адаптер и не работает с BLE/GATT напрямую.
