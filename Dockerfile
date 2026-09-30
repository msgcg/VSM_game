# Multi-stage / optimized slim image for VSM Conductor Simulator
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    WHISPER_BIN_PATH=/usr/local/bin/whisper-cli \
    WHISPER_MODEL_PATH=/opt/whisper/models/ggml-base.bin \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics

WORKDIR /app

# Системные пакеты: FFmpeg для ASR, шрифты, dos2unix, curl, ca-certificates
# и аппаратные библиотеки Vulkan (libvulkan1, mesa-vulkan-drivers, vulkan-tools, libvulkan-dev, glslc, cmake)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libvulkan-dev \
    glslc \
    libvulkan1 \
    mesa-vulkan-drivers \
    vulkan-tools \
    libjpeg-dev \
    zlib1g-dev \
    fonts-dejavu-core \
    curl \
    ca-certificates \
    ffmpeg \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Аргументы для сборки GGML моделей (по умолчанию base, можно передать "base small")
ARG WHISPER_MODELS="base"

# Автоматическая сборка/установка whisper.cpp с поддержкой аппаратного ускорения Vulkan GPU
RUN mkdir -p /tmp/spirv-headers /tmp/whisper-src /opt/whisper/models && \
    echo "Установка пакета SPIRV-Headers для CMake..." && \
    (curl -f -sSLk "https://github.com/KhronosGroup/SPIRV-Headers/archive/refs/heads/main.tar.gz" | tar -xz -C /tmp/spirv-headers --strip-components=1 && \
     cmake -B /tmp/spirv-headers/build -S /tmp/spirv-headers -DCMAKE_INSTALL_PREFIX=/usr/local && \
     cmake --install /tmp/spirv-headers/build && \
     rm -rf /tmp/spirv-headers || true) && \
    echo "Сборка whisper-cli с поддержкой Vulkan GPU..." && \
    (curl -f -sSLk "https://github.com/ggerganov/whisper.cpp/archive/refs/tags/b5130.tar.gz" | tar -xz -C /tmp/whisper-src --strip-components=1 && \
     cd /tmp/whisper-src && \
     cmake -B build -DGGML_VULKAN=1 -DCMAKE_BUILD_TYPE=Release && \
     cmake --build build --config Release --target whisper-cli -j$(nproc) && \
     cp build/bin/whisper-cli /usr/local/bin/whisper-cli && \
     (cp build/bin/*.so* /usr/local/lib/ 2>/dev/null || true) && \
     (cp build/src/*.so* /usr/local/lib/ 2>/dev/null || true) && \
     (cp build/ggml/src/*.so* /usr/local/lib/ 2>/dev/null || true) && \
     chmod +x /usr/local/bin/whisper-cli && \
     ldconfig && \
     echo "Успешно собран нативный whisper-cli с Vulkan") || \
    (echo "Резервная установка стандартного Linux whisper-cli..." && \
     mkdir -p /tmp/whisper && \
     curl -f -sSLk "https://github.com/ggerganov/whisper.cpp/releases/download/b5130/whisper-bin-ubuntu-x64.tar.gz" | tar -xz -C /tmp/whisper && \
     cp /tmp/whisper/whisper-bin-ubuntu-x64/whisper-cli /usr/local/bin/whisper-cli && \
     chmod +x /usr/local/bin/whisper-cli && \
     (cp /tmp/whisper/whisper-bin-ubuntu-x64/*.so* /usr/local/lib/ 2>/dev/null || true) && \
     ldconfig && rm -rf /tmp/whisper) && \
    rm -rf /tmp/whisper-src && \
    for model in $WHISPER_MODELS; do \
        echo "Загрузка GGML модели: ggml-${model}.bin..." && \
        (curl -f -sSLk -o "/opt/whisper/models/ggml-${model}.bin" \
         "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-${model}.bin" || \
         curl -f -sSLk -o "/opt/whisper/models/ggml-${model}.bin" \
         "https://ggml.ggerganov.com/ggml-model-whisper-${model}.bin"); \
    done

# Установка Python-зависимостей
COPY requirements.txt /app/
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt

# Копирование исходного кода проекта
COPY . /app/

# Создание рабочих директорий
RUN mkdir -p /app/staticfiles /app/media /app/simulator/bin/whisper_vulkan/tmp

# Нормализация окончаний строк и прав на запуск entrypoint скрипта
RUN dos2unix /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Создание чистой эталонной базы данных ВСМ внутри образа при сборке
RUN python manage.py migrate --noinput && \
    python manage.py seed_vsm_data && \
    python manage.py seed_regulations && \
    python manage.py purge_personal_data --create-clean-template && \
    cp /app/db.sqlite3 /app/db.sqlite3.clean


EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
