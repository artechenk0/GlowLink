# Contributing

Используйте Python 3.11+ и запускайте из `app/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest
python -m ruff check src tests
python -m mypy src
```

Начинайте с актуальной `main` и создавайте ветку по типу работы:
`feat/<short-task>`, `fix/<short-task>`, `docs/<short-task>`, `refactor/<short-task>`,
`test/<short-task>` или `chore/<short-task>`. Не отправляйте изменения напрямую в `main`:
каждое изменение попадает в неё только через pull request.

Одна ветка и один PR соответствуют одной логической задаче. Не смешивайте функциональное
изменение и несвязанный рефакторинг. Перед открытием PR обновите ветку от `main`, выполните
обязательные проверки и убедитесь, что diff относится только к задаче.

PR описывает пользовательское поведение, связанные issue, выполненные проверки и ограничения.
Для GUI приложите скриншот; для BLE укажите модель устройства, команды и результат ручной
проверки. Обновляйте README, compatibility-матрицу, protocol notes и ADR, когда меняется их
предмет. Дополнительные правила находятся в [AGENTS.md](AGENTS.md).
