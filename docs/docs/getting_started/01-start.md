# Запуск проекта

## Предусловия

- Должен быть установлен Docker + Docker Compose
  - Должны быть свободны порты: `5432`, `8123`, `1025`, `8025`, `6379`, `8000`, `8001`
    (для autotest) или `80` (для обычного деплоя).

## Конфигурация

!!! note
    Не рекомендуется изменять уже существующие параметры в `alphabet.yml`,
    так как они подобраны таким образом, чтобы упрощать тестирование.

Если необходимо, измените значения в конфигурации (`alphabet-backend/alphabet.yml`).

## Старт контейнеров

```sh 
docker compose up -d --build
```

Затем проверка готовности:

```sh
curl -X 'GET' \
  'http://localhost:80/ready' \
  -H 'accept: text/plain'
```

Готовый сервис должен ответить `ready`.

- На `localhost:80/api` будет развёрнуто API.
  - На `localhost:80` — Identity-Aware Proxy (IAP)
  - На `localhost:80/mailpit` — веб-интерфейс тестового SMTP сервера

## Размещение тестовых данных

Для того чтобы поместить тестовые данные, выполните пост-запросы.

Очистка:

```sh
curl -X 'POST' \
  'http://localhost/_internal/data/clear' \
  -H 'accept: text/plain' \ 
  -d ''
```

Размещение:

```
curl -X 'POST' \
  'http://localhost/_internal/data/seed' \
  -H 'accept: text/plain' \
  -d ''
```
