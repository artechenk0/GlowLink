# Упрощённый Gitflow

LEDSetup использует одну постоянную ветку — `main`. Она содержит стабильный код и должна быть
защищена в GitHub: прямые push не допускаются, изменения попадают в неё только через pull
request с успешным CI.

| Ветка | Когда использовать | Откуда создаётся | Куда вливается |
| --- | --- | --- | --- |
| `feature/<task>` | Новая возможность. | `main` | `main` |
| `fix/<task>` | Исправление ошибки. | `main` | `main` |
| `docs/<task>`, `refactor/<task>`, `test/<task>`, `chore/<task>` | Техническая задача соответствующего типа. | `main` | `main` |
| `release/vX.Y.Z` | Подготовка релиза, если она требует отдельного PR. | `main` | `main` |
| `hotfix/vX.Y.Z` | Срочное исправление уже опубликованной версии. | `main` | `main` |

## Обычная работа

Создайте короткоживущую ветку от актуальной `main`, например `feature/device-status`, и
откройте pull request обратно в `main`. Одна ветка и один PR соответствуют одной задаче.

## Релиз

Перед первым запуском включите в GitHub **Settings → Actions → General → Workflow permissions →
Allow GitHub Actions to create and approve pull requests**. Это позволяет workflow создавать PR
через встроенный `GITHUB_TOKEN`; отдельный секрет не нужен.

1. Запустите workflow **Prepare release** из `main` и укажите версию `X.Y.Z` без префикса `v`.
   Он создаст `release/vX.Y.Z` и pull request, обновляющий `app/pyproject.toml`, версию CLI и
   changelog. Проверьте и влейте этот PR.
2. После merge в `main` создайте и отправьте аннотированный тег на этот commit:

   ```powershell
   git checkout main
   git pull --ff-only
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

Push тега запускает release workflow. Он проверяет соответствие тега версии в
`app/pyproject.toml`, повторяет проверки, собирает wheel и sdist на Windows и создаёт GitHub
Release с этими файлами. При несовпадении тега и версии публикация не начнётся.

Для срочного исправления создайте `hotfix/vX.Y.Z` от `main`, внесите минимальную правку,
влейте её через PR в `main` и выпустите соответствующий тег.
