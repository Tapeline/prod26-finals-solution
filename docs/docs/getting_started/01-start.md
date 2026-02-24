# Запуск проекта

## Предусловия

- Должен быть установлен Docker + Docker Compose
- Должны быть свободны порты: `5432`, `8123`, `1025`, `8025`, `6379`, `8000`, `8001`

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

<!--

## Регистрация первого пользователя

Так как Alphabet использует IAP для аутентификации запросов, то он не хранит
учётные данные пользователя, кроме IAP ID и Email для соотнесения IAP пользователей
со своей базой. Для того чтобы создать первого администратора, нужно воспользоваться
эндпоинтом `POST /_internal/new-user`. Например, создадим его с почтой `admin@t.ru`:

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/_internal/new-user' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{"email": "admin@t.ru", "role": "admin"}'
    ```

=== "Swagger"

    В `http://localhost:80/docs` сделаем запрос на эндпоинт:

    ```json
    {"email": "admin@t.ru", "role": "admin"}
    ```

После создания пользователя, его необходимо будет активировать. Сделать это
можно двумя способами:

Первый: через заголовки, в обход IAP (только для тестов).
    
Предположим, что у этого пользователя IAP ID = `admin`:

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/accounts/activate' \
      -H 'accept: application/json' \
      -H 'X-User-Id: admin' \
      -H 'X-User-Email: admin@t.ru'
    ```

=== "Swagger"

    В `http://localhost:80/docs` сначала авторизуемся с данными:

    - `iap_user_id` = `admin`
    - `iap_user_email` = `admin@t.ru`

    Затем запрос на эндпоинт.

Второй вариант — через IAP. Заходим через IAP в сервис (`http://localhost:8001`),
выбираем из предложенных предустановленных пользователей (либо добавляем своего в
`config.toml` IAP и перезапускаем его):

- Admin: `iap id = admin, email = admin@t.ru`
- Experimenter: `iap id = exp, email = exp@t.ru`
- Approver: `iap id = approver, email = approver@t.ru`
- Viewer: `iap id = viewer, email = viewer@t.ru`

После чего (если это новый, ранее не активированный аккаунт), откроется окно
активации. Нажатием на кнопку Activate account происходит активация.

При активации сервис связывает данные IAP (IAP ID) с пользователем в своей
базе данных с помощью e-mail.

Проверить, активирован ли аккаунт, можно просто попробовав запросить профиль
со своим IAP ID и Email. Если сервис отвечает "не найден", то пользователь
ещё действительно не активирован.

-->