# Упрощённый Gitflow

GlowLink использует одну постоянную ветку — `main`. Она содержит стабильный код и должна быть
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
через встроенный `GITHUB_TOKEN`; отдельный секрет не нужен. После отправки release-ветки
`Prepare release` явно запускает CI с `workflow_dispatch`, поэтому автоматически созданный PR не
нужно вручную разблокировать для запуска проверки.

1. Запустите workflow **Prepare release** именно из `main` и укажите версию `X.Y.Z` без префикса
   `v`. Он создаст `release/vX.Y.Z` и pull request, обновляющий `app/pyproject.toml`, версию CLI
   и оба changelog (`CHANGELOG.md` и `CHANGELOG.en.md`).
2. Дождитесь CI для release-PR. Ожидаются проверки **Verify (Python 3.12)** и **Build and install
   package**. Проверьте изменения и влейте PR в `main`.
3. После merge в `main` создайте и отправьте аннотированный тег на этот commit:

   ```powershell
   git checkout main
   git pull --ff-only
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

Push тега запускает release workflow. Он проверяет формат и наличие тега, checkout-ит именно его
commit, проверяет соответствие версии в `app/pyproject.toml`, повторяет quality-проверки, собирает
`GlowLink.exe`, wheel и sdist на Windows и создаёт GitHub Release с этими файлами. Concurrency
группируется по имени тега, поэтому параллельные повторы одного релиза не смешивают артефакты.

Если Release упал после создания тега, исправьте workflow, влейте исправление в `main` и запустите
**Actions → Release → Run workflow**, указав существующий тег `vX.Y.Z`. Ручной retry снова checkout-ит
этот тег, а не последний commit `main`, поэтому новые коммиты после выпуска не попадут в артефакты.

Повтор **Prepare release** безопасен: если корректная `release/vX.Y.Z` уже отправлена, workflow
создаст отсутствующий PR и заново запустит CI. Если ветка занята другой версией или уже существует
тег, workflow завершится с ошибкой и ничего не перезапишет.

CI и Release устанавливают зависимости только из `app/uv.lock` и CI-группы `ci`, включающей test,
build и PyInstaller. Dependabot еженедельно предлагает обновления GitHub Actions и зависимостей;
такие PR нужно проверять обычным CI и принимать отдельно от релизного PR.

Для срочного исправления создайте `hotfix/vX.Y.Z` от `main`, внесите минимальную правку,
влейте её через PR в `main` и выпустите соответствующий тег.
