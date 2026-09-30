#!/bin/sh
set -e

echo "=== Запуск симулятора ВСМ «Белый кречет» в Linux-контейнере ==="

# Директива FRESH_DB: принудительный сброс ТОЛЬКО при явном указании FRESH_DB=1
if [ "$FRESH_DB" = "1" ] || [ "$RESET_DB" = "1" ]; then
    echo "Активирована директива FRESH_DB=1: очистка базы данных и восстановление чистой эталонной БД..."
    rm -f /app/db.sqlite3 /app/db.sqlite3-journal /app/db.sqlite3-wal 2>/dev/null || true
    if [ -f "/app/db.sqlite3.clean" ]; then
        cp /app/db.sqlite3.clean /app/db.sqlite3
        echo "База данных восстановлена из эталонного образа."
    fi
elif [ ! -f "/app/db.sqlite3" ] && [ -f "/app/db.sqlite3.clean" ]; then
    echo "Инициализация базы данных из чистого эталона сборки образа..."
    cp /app/db.sqlite3.clean /app/db.sqlite3
fi

# Применение миграций базы данных (сохраняет существующие аккаунты и прогресс смен)
echo "Применение миграций Django..."
python manage.py migrate --noinput

# Проверка наличия данных в базе (если база абсолютно пуста — засеиваем эталонные данные)
echo "Проверка наличия сценариев и регламентов ВСМ..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vsm_config.settings')
django.setup()
from simulator.models import Scenario, RegulationDocument
if not Scenario.objects.exists() or not RegulationDocument.objects.exists():
    print('Справочники ВСМ пусты. Запуск инициализации сценариев и регламентов...')
    from django.core.management import call_command
    call_command('seed_vsm_data')
    call_command('seed_regulations')
    print('Данные успешно инициализированы. Пользовательские аккаунты сохранены.')
else:
    print(f'Обнаружено {Scenario.objects.count()} сценариев и {RegulationDocument.objects.count()} регламентов ВСМ. База готова.')
"

# Диагностика и проверка доступности аппаратного ускорения Vulkan GPU
echo "=== Диагностика среды Vulkan и GPU ==="
if command -v vulkaninfo >/dev/null 2>&1; then
    vulkaninfo --summary 2>/dev/null | grep -E "deviceName|driverVersion|apiVersion" || echo "Vulkan: среда готова, устройство ожидает передачи хост-GPU."
else
    echo "Утилита vulkaninfo не найдена."
fi

# Проверка готовности бортового модуля Whisper GGML
if [ -x "/usr/local/bin/whisper-cli" ]; then
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vsm_config.settings')
django.setup()
from simulator.services.whisper_service import WhisperVulkanService
bin_path = WhisperVulkanService.get_bin_path()
model_path = WhisperVulkanService.get_model_path()
avail = WhisperVulkanService.is_available()
print(f'Бортовой модуль Whisper GGML: готов={avail} [бинарник: {bin_path}, модель: {model_path}]')
"
else
    echo "Бортовой модуль Whisper: автономное распознавание отключено, используется Web Speech API браузера."
fi

# Сборка статических файлов
echo "Сборка статических файлов..."
python manage.py collectstatic --noinput --clear || true

echo "Сервер готов к работе на порту 8000."
exec "$@"
