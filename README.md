# URL Shortener

Сервис коротких ссылок на Flask и SQLite. Есть веб-форма, REST API, редирект по коду и админ-панель со статистикой переходов (IP, гео, устройство, браузер, ОС).

## Установка

```bash
pip install -r requirements.txt
cp config.example.py config.py
```

В `config.py` укажите свои значения:

| Параметр | Назначение |
|---|---|
| `DOMAIN` | домен, отображаемый в интерфейсе |
| `BASE_URL` | база для генерации коротких ссылок; если пусто, берётся из запроса |
| `DATABASE` | путь к файлу SQLite |
| `HOST`, `PORT` | адрес и порт сервера |
| `SHORT_CODE_LENGTH` | длина автогенерируемого кода |
| `ADMIN_PATH` | адрес админ-панели |
| `GEO_API_URL` | сервис определения геолокации по IP |

`config.py` и база данных в репозиторий не попадают (см. `.gitignore`).

## Запуск

```bash
python app.py
```

Для продакшена:

```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

База создаётся автоматически при первом запуске.

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/shorten` | создать ссылку: `{"url": "...", "custom_code": "..."}` |
| GET | `/api/stats/<code>` | статистика по одной ссылке |
| GET | `/api/urls` | последние 100 ссылок |
| GET | `/<code>` | редирект на оригинальный URL |
| GET | `/api/admin/stats` | сводная статистика |
| GET | `/api/admin/logs/<code>` | лог переходов |
| DELETE | `/api/admin/delete/<code>` | удалить ссылку |
| DELETE | `/api/admin/delete-zero-clicks` | удалить ссылки без переходов |
| DELETE | `/api/admin/delete-all-links` | удалить все ссылки |

Пример:

```bash
curl -X POST http://localhost:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/long/path","custom_code":"demo"}'
```

Пользовательский код — от 3 до 20 символов. Переходы ботов и prefetch-запросы в статистику не пишутся, повторные клики с одного IP в течение 2 секунд считаются дублем.

## Развёртывание на сервере

Скрипты `setup_production.sh` (gunicorn) и `setup_simple.sh` (встроенный сервер Flask) создают systemd-сервис `url-shortener`. Перед запуском проверьте пути `APP_DIR` и `LOG_DIR` внутри скриптов.

```bash
chmod +x setup_production.sh
./setup_production.sh
```

Пример конфигурации Nginx:

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Заголовки `X-Real-IP` и `X-Forwarded-For` нужны, чтобы в логах переходов был реальный IP клиента.

## Структура

```
app.py                 приложение и API
admin_panel.html       шаблон админ-панели
config.example.py      пример конфигурации
requirements.txt       зависимости
setup_production.sh    установка systemd-сервиса с gunicorn
setup_simple.sh        установка systemd-сервиса без gunicorn
url-shortener.service  пример unit-файла
```

## Ограничения

Админ-панель и API администрирования не защищены авторизацией — закрывайте их на уровне Nginx (basic auth, ограничение по IP) или задавайте неочевидный `ADMIN_PATH`. Rate limiting не реализован.

## Лицензия

MIT
