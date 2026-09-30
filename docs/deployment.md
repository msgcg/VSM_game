# Инструкция по развертыванию и запуску

Интерактивный комплекс ВСМ-1 «Белый кречет» поддерживает три варианта развертывания:

1. Запуск готового Docker-образа в 1 команду из Docker Hub.
2. Локальная сборка и запуск через Docker Compose.
3. Локальный запуск в виртуальном окружении Python (venv).

---

## Вариант 1: Запуск готового образа из Docker Hub в 1 команду (Рекомендуемый)

Для быстрого запуска без необходимости сборки исходного кода выполните:

```bash
docker run -d -p 8000:8000 --name vsm-simulator msgcg/vsm-simulator:latest
```

После выполнения команды контейнер автоматически:

- Инициализирует изолированную среду Linux с поддержкой кириллических шрифтов DejaVu.
- Развернет чистую эталонную базу данных с официальными регламентами ВСМ, нормативной базой и 20 сценарными кейсами.
- Запустит веб-сервер на порту 8000.

Адреса для доступа в браузере:

- Главный пульт проводника: [http://localhost:8000/](http://localhost:8000/)
- Документация Swagger UI: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- Спецификация OpenAPI: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

Управление контейнером:

```bash
# Просмотр логов работы сервера
docker logs -f vsm-simulator

# Остановка контейнера
docker stop vsm-simulator

# Удаление контейнера
docker rm vsm-simulator
```

---

## Вариант 2: Локальная сборка через Docker Compose

Подходит для разработки и тестирования локальных изменений:

```bash
# Сборка образа и запуск в фоновом режиме
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f web

# Остановка комплекса
docker compose down
```

---

## Вариант 3: Локальный запуск через виртуальное окружение Python (venv)

### Системные требования

- Python 3.12 или новее
- Git
- Операционная система: Windows 10/11, Linux (Ubuntu 22.04+) или macOS

### Пошаговые команды

```powershell
# 1. Клонирование репозитория
git clone https://github.com/msgcg/VSM_game.git
cd VSM_game

# 2. Создание и активация виртуального окружения
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Для Windows PowerShell
# source .venv/bin/activate     # Для Linux / macOS

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Применение миграций базы данных
python manage.py migrate

# 5. Запуск веб-сервера разработки
python manage.py runserver 127.0.0.1:8000
```

После старта откройте в браузере: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Конфигурация переменных окружения (.env)

Файл конфигурации `.env` создается в корне проекта при необходимости использования внешних сервисов:

```env
# AI Platform (LLM)
GIGACHAT_CLIENT_ID=your_client_id_here
GIGACHAT_CLIENT_SECRET=your_client_secret_here
GIGACHAT_AUTH_KEY=your_base64_auth_key_here
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat-Max

# Corporate ID OAuth 2.0
SBER_ID_CLIENT_ID=your_sber_id_client_id
SBER_ID_CLIENT_SECRET=your_sber_id_client_secret
SBER_ID_REDIRECT_URI=http://127.0.0.1:8000/auth/sber/callback/
```

*Примечание: для автономной работы и тестирования комплекс содержит встроенные отказоустойчивые модули и мок-провайдеры, поэтому указание внешних ключей не является строго обязательным.*

---

## Тестирование системы

Комплекс покрыт набором из 75 автоматических тестов:

- Логика симулятора, таймеры и таймауты.
- 4-шаговый дебрифинг ВСМ.
- Отдача регламентов из базы данных (SQLite base64).
- Все эндпоинты REST API v1 и валидность схемы OpenAPI 3.0.3.
- Интерактивный генеративный диалог и физика вагона.

Запуск тестового набора:

```bash
python manage.py test simulator
```

Ожидаемый результат: `Ran 75 tests. OK`.
