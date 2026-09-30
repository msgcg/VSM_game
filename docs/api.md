# Спецификация REST API v1 и OpenAPI 3.0

Интерактивный комплекс ВСМ-1 предоставляет программный интерфейс REST API v1 для интеграции с внешними системами ВСМ, мобильными терминалами проводников (ММТ/УКЭБ) и корпоративными LMS-платформами.

## Документация и схема

- **Интерактивный Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **Схема OpenAPI 3.0.3**: [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

Все запросы и ответы API передаются в формате `application/json` в кодировке UTF-8.

## Сводная таблица эндпоинтов

| Метод | Эндпоинт | Назначение | Формат ответа |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/profile/` | Получение профиля текущего проводника, звания, депо и сводных показателей. | `{"profile": {...}}` |
| `GET` | `/api/v1/scenarios/` | Каталог сценарных кейсов с фильтрацией по категории и сложности. | `{"scenarios": [...]}` |
| `GET` | `/api/v1/scenario/{slug}/` | Детальная карточка сценария и параметры первого диалогового узла. | `{"scenario": {...}}` |
| `POST`| `/api/v1/simulation/start/{slug}/` | Инициализация новой симуляционной сессии рейса. | `{"session_id": int, "metrics": {...}}` |
| `POST`| `/api/v1/simulation/{id}/choose/` | Фиксация принятого проводником решения или действия с оборудованием. | `{"metrics": {...}, "next_node": {...}}` |
| `POST`| `/api/v1/simulation/{id}/timeout/` | Обработка истечения таймера на скорости 400 км/ч (штраф за промедление). | `{"penalty": -15, "metrics": {...}}` |
| `GET` | `/api/v1/simulation/{id}/debrief/` | Получение итогового дебрифинга по 4-шаговой модели ВСМ. | `{"steps": [...], "recommendations": [...]}` |
| `GET` | `/api/v1/analytics/` | Данные матрицы компетенций, SVG-радара и выявленных зон роста. | `{"radar_data": [...], "growth_areas": [...]}` |
| `GET` | `/api/v1/notifications/` | Список уведомлений проводника и счетчик непрочитанных сообщений. | `{"notifications": [...], "unread_count": int}` |
| `POST`| `/api/v1/notifications/` | Отметка о прочтении отдельного уведомления (`id`) или всех сообщений (`all: true`). | `{"status": "ok", "unread_count": int}` |
| `GET` | `/api/v1/leaderboard/` | Рейтинговая таблица проводников ВСМ с фильтрацией по депо и рангу. | `{"leaderboard": [...]}` |
| `GET` | `/api/v1/regulations/{doc_key}/` | Метаданные стандарта СТО ВСМ, оглавление и текст статьи из базы данных. | `{"title": str, "chapters": [...]}` |

## Примеры использования API

### 1. Получение профиля проводника

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/profile/" \
     -H "Accept: application/json"
```

Пример ответа:
```json
{
  "profile": {
    "username": "ivanov_vsm",
    "full_name": "Иванов Алексей Петрович",
    "rank": "Старший стюард ВСМ 1 класса",
    "depo": "Северо-Западный филиал (СПб)",
    "level": 4,
    "xp": 3450,
    "xp_to_next": 4000,
    "flawless_shifts": 12,
    "avg_csi": 88.4,
    "avg_safety": 96.1
  }
}
```

### 2. Запуск симуляционной сессии

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/start/business-seat-conflict/" \
     -H "Content-Type: application/json"
```

Пример ответа:
```json
{
  "session_id": 42,
  "scenario_slug": "business-seat-conflict",
  "speed_kmh": 400,
  "timer_seconds": 18,
  "metrics": {
    "loyalty": 75,
    "safety": 95,
    "stress": 20
  },
  "current_node": {
    "id": 101,
    "speaker": "Пассажир 1-го класса",
    "dialogue_text": "Почему на моем месте сидит посторонний человек с собакой?! Я опаздываю на совещание!",
    "choices": [
      {
        "id": 201,
        "text": "Принести извинения за неудобство, проверить билеты обоих пассажиров и предложить приоритетную пересадку в купе-сьют."
      },
      {
        "id": 202,
        "text": "Потребовать от владельца собаки немедленно покинуть салон 1 класса."
      }
    ]
  }
}
```

### 3. Выбор варианта действия

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/42/choose/" \
     -H "Content-Type: application/json" \
     -d '{"choice_id": 201}'
```

Пример ответа:
```json
{
  "session_id": 42,
  "metrics": {
    "loyalty": 88,
    "safety": 95,
    "stress": 15
  },
  "feedback": "Верно: соблюден шаг 1 ролевой модели (Признать ситуацию) и пункт 4.2 СТО ВСМ 03.011-2026.",
  "is_terminal": false,
  "next_node": {
    "id": 102,
    "speaker": "Пассажир 1-го класса",
    "dialogue_text": "Благодарю за оперативность. Вариант со сьютом меня полностью устраивает.",
    "choices": []
  }
}
```

### 4. Получение обучающего дебрифинга

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/simulation/42/debrief/"
```

Пример ответа:
```json
{
  "session_id": 42,
  "status": "passed",
  "score": 92,
  "xp_earned": 150,
  "four_steps_evaluation": [
    {"step": 1, "title": "Признать ситуацию", "result": "passed", "comment": "Эмпатия проявлена корректно."},
    {"step": 2, "title": "Обозначить правило", "result": "passed", "comment": "Ссылка на СТО ВСМ 03.011-2026 точная."},
    {"step": 3, "title": "Предложить решение", "result": "passed", "comment": "Предложена регламентная пересадка."},
    {"step": 4, "title": "Заверить", "result": "passed", "comment": "Пассажир выразил удовлетворенность."}
  ],
  "competency_deltas": {
    "conflict_resolution": 6.5,
    "service_etiquette": 4.0
  }
}
```

### 5. Получение данных матрицы компетенций и радара

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/"
```

Пример ответа:
```json
{
  "radar_labels": [
    "Разрешение конфликтов",
    "Безопасность 400 км/ч",
    "Неотложная помощь",
    "Сервисный этикет",
    "Оборудование вагона",
    "Скорость решений"
  ],
  "radar_scores": [88, 92, 70, 85, 80, 90],
  "benchmark": 85,
  "readiness_index": 84.1,
  "growth_areas": [
    {
      "competency": "emergency_medical",
      "title": "Неотложная помощь",
      "delta": 15,
      "recommended_scenario": "medical-hypotension-faint"
    }
  ]
}
```
