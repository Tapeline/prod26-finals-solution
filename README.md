# αlphaβet

Корпоративная платформа для A/B тестирования.

![](https://gitlab.prodcontest.com/2026-final-users/backend/yt.redstone.mail/badges/main/pipeline.svg)
![](https://gitlab.prodcontest.com/2026-final-users/backend/yt.redstone.mail/badges/main/coverage.svg)

## Документация

Документация к проекту развёрнута помощью mkdocs и GitLab Pages и доступна
по [этой ссылке](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/).

В случае проблем с просмотром, исходники документации в формате Markdown находятся
в [/docs/docs](docs/docs).

## Требуемые артефакты проверки:

- Runbook запуска и проверки: "Приступая к проверке / Запуск проекта":
    - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/getting_started/01-start/)
    - .md файл `docs/docs/getting_started/01-start.md`
- Тестовые сценарии и данные:
    - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/getting_started/01-start/)
    - .md файл `docs/docs/getting_started/01-start.md`
- Архитектурный пакет диаграмм:
    - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/diagram/c4/)
    - .md файл `docs/docs/diagram/c4.md`
- Отчёт по тестированию:
    - Файлы с тестами: `sys-tests/tests`, `alphabet-backend/tests`
    - Инструкция по запуску: 
        - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/automation)
        - .md файл `docs/docs/automation.md`
    - Отчёт по покрытию в GitLab CI: [![](https://gitlab.prodcontest.com/2026-final-users/backend/yt.redstone.mail/badges/main/coverage.svg)](https://gitlab.prodcontest.com/2026-final-users/backend/yt.redstone.mail/-/jobs)
- Набор подтверждений наблюдаемости и эксплуатационной готовности:
    - Lint/format:
        - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/automation)
        - .md файл `docs/docs/automation.md`
    - Примеры метрик и структурированных логов
        - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/ops-examples)
        - .md файл `docs/docs/ops-examples.md`
- Матрица соответствия:
    - [На развёрнутой документации](https://yt-redstone-mail-e7ec37.pages.prodcontest.com/compliance-matrix/)
    - .md файл `docs/docs/compliance-matrix.md`
