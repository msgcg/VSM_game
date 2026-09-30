import os
import sys
import shutil
import re
import tempfile
import subprocess
from pathlib import Path
from django.conf import settings


class WhisperVulkanService:
    """
    Универсальный локальный движок распознавания речи Whisper (ggml / whisper.cpp).
    - Windows: аппаратно-ускоренный запуск через Vulkan GPU (NVIDIA RTX/GTX, AMD, Intel Arc).
    - Linux / Docker / macOS: автоматическое обнаружение системного whisper-cli / whisper.cpp
      или переменной окружения WHISPER_BIN_PATH.
    - При отсутствии исполняемого бинарника или модели под текущую ОС безопасно отключается,
      делегируя распознавание встроенному Web Speech API браузера или облачному шлюзу.
    """

    _BASE_DIR = Path(settings.BASE_DIR)

    @classmethod
    def get_bin_path(cls) -> Path | None:
        """
        Универсальный поиск исполняемого бинарника whisper-cli для текущей операционной системы.
        """
        # 1. Проверяем явную переменную окружения
        env_bin = os.environ.get("WHISPER_BIN_PATH")
        if env_bin:
            p = Path(env_bin)
            if p.exists() and (sys.platform == "win32" or os.access(p, os.X_OK)):
                return p

        # 2. Локальный Windows-бандл с Vulkan-ускорением (только для платформы Windows)
        if sys.platform == "win32":
            win_bin = cls._BASE_DIR / "simulator" / "bin" / "whisper_vulkan" / "whisper-cli.exe"
            if win_bin.exists():
                return win_bin

        # 3. Поиск системной утилиты в PATH (Linux, macOS, Docker)
        for cmd in ["whisper-cli", "whisper.cpp", "whisper"]:
            found = shutil.which(cmd)
            if found:
                return Path(found)

        # 4. Стандартные пути Linux / контейнеров
        for cand in [
            "/usr/local/bin/whisper-cli",
            "/usr/bin/whisper-cli",
            cls._BASE_DIR / "simulator" / "bin" / "whisper_linux" / "whisper-cli",
        ]:
            cand_p = Path(cand)
            if cand_p.exists() and os.access(cand_p, os.X_OK):
                return cand_p

        return None

    @classmethod
    def get_model_path(cls) -> Path | None:
        """
        Универсальный поиск ggml-моделей (приоритет: small -> base -> custom).
        """
        env_model = os.environ.get("WHISPER_MODEL_PATH")
        if env_model:
            p = Path(env_model)
            if p.exists() and p.stat().st_size > 10 * 1024 * 1024:
                return p

        search_dirs = [
            cls._BASE_DIR / "simulator" / "bin" / "whisper_vulkan" / "models",
            cls._BASE_DIR / "models",
            cls._BASE_DIR / "simulator" / "models",
            Path("/opt/whisper/models"),
            Path("/usr/local/share/whisper/models"),
            Path("/app/models"),
            Path.home() / ".cache" / "whisper",
        ]

        # 1. Приоритет качественной модели small
        for s_dir in search_dirs:
            if s_dir.exists():
                small_model = s_dir / "ggml-small.bin"
                if small_model.exists() and small_model.stat().st_size > 100 * 1024 * 1024:
                    return small_model

        # 2. Быстрая компактная модель base
        for s_dir in search_dirs:
            if s_dir.exists():
                base_model = s_dir / "ggml-base.bin"
                if base_model.exists() and base_model.stat().st_size > 20 * 1024 * 1024:
                    return base_model

        # 3. Любая ggml-*.bin модель в найденных директориях
        for s_dir in search_dirs:
            if s_dir.exists():
                for bin_file in s_dir.glob("ggml-*.bin"):
                    if bin_file.stat().st_size > 10 * 1024 * 1024:
                        return bin_file

        return None

    @classmethod
    def is_available(cls) -> bool:
        """Проверяет доступность бинарника whisper-cli и ggml-модели под текущую ОС"""
        bin_p = cls.get_bin_path()
        model_p = cls.get_model_path()
        return bool(bin_p and model_p)

    @classmethod
    def transcribe(cls, audio_bytes: bytes, language: str = "ru") -> dict:
        """
        Транскрибирует аудиопоток проводника (webm, ogg, wav, mp3) в русский текст.
        Возвращает: {"ok": bool, "text": str, "engine": "whisper_vulkan", ...}
        """
        if not audio_bytes:
            return {"ok": False, "error": "Аудиоданные не переданы", "text": ""}

        bin_path = cls.get_bin_path()
        model_path = cls.get_model_path()
        if not bin_path or not model_path:
            return {
                "ok": False,
                "error": "Локальный модуль Whisper не сконфигурирован для текущей ОС",
                "text": ""
            }

        # Безопасное относительное или абсолютное представление путей для whisper.cpp
        try:
            rel_bin = str(bin_path.relative_to(cls._BASE_DIR))
        except ValueError:
            rel_bin = str(bin_path)

        try:
            rel_model = str(model_path.relative_to(cls._BASE_DIR))
        except ValueError:
            rel_model = str(model_path)

        model_tag = "whisper_small" if "small" in model_path.name.lower() else "whisper_base"

        # Временная папка для транскодированного WAV
        temp_dir = cls._BASE_DIR / "simulator" / "bin" / "whisper_vulkan" / "tmp"
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            temp_dir = Path(tempfile.gettempdir())

        # Временный 16kHz mono WAV файл с ASCII именем
        import uuid
        uid = uuid.uuid4().hex[:10]
        wav_path = temp_dir / f"rec_{uid}.wav"
        try:
            rel_wav = str(wav_path.relative_to(cls._BASE_DIR))
        except ValueError:
            rel_wav = str(wav_path)

        try:
            # 1. Транскодируем входной аудиопоток в 16kHz mono WAV через FFmpeg
            ffmpeg_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(rel_wav),
                "-y"
            ]
            proc_ff = subprocess.Popen(
                ffmpeg_cmd,
                cwd=str(cls._BASE_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            _, ff_err = proc_ff.communicate(input=audio_bytes, timeout=10)
            if proc_ff.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size < 100:
                return {
                    "ok": False,
                    "error": f"Ошибка декодирования аудио: {ff_err.decode('utf-8', errors='ignore')[:150]}",
                    "text": ""
                }

            # 2. Запуск whisper-cli с аппаратно-ускоренным выводом и русским контекстным промптом ВСМ
            cpu_threads = min(os.cpu_count() or 4, 8)
            whisper_cmd = [
                rel_bin,
                "-m", rel_model,
                "-l", language,
                "-nt",
                "-f", rel_wav,
                "--prompt", "Поезд ВСМ Белый кречет, проводник, пассажир, вагон, билет, паспорт, регламент, магистраль, чай, багаж, безопасность, машинист, СКНБ, станция, кондиционер.",
                "-bs", "2",
                "-bo", "2",
                "-sns",
                "-t", str(cpu_threads)
            ]

            proc_w = subprocess.Popen(
                whisper_cmd,
                cwd=str(cls._BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout_data, stderr_data = proc_w.communicate(timeout=20)

            if proc_w.returncode != 0:
                err_msg = stderr_data.decode('utf-8', errors='ignore')[:200]
                return {
                    "ok": False,
                    "error": f"Ошибка Whisper Vulkan (код {proc_w.returncode}): {err_msg}",
                    "text": ""
                }

            # 3. Извлекаем распознанный текст из stdout / stderr
            raw_text = stdout_data.decode('utf-8', errors='ignore').strip()
            if not raw_text:
                # Если в stdout пусто, ищем строки транскрипта в stderr (без служебных префиксов)
                lines = []
                for line in stderr_data.decode('utf-8', errors='ignore').splitlines():
                    clean_l = line.strip()
                    if clean_l and not any(clean_l.startswith(p) for p in [
                        "ggml", "whisper", "system_info", "main:", "load time", "fallbacks",
                        "mel time", "sample time", "encode time", "decode time", "batchd time",
                        "prompt time", "total time"
                    ]):
                        lines.append(clean_l)
                raw_text = " ".join(lines).strip()

            # Очищаем текст от технического мусора
            cleaned = re.sub(r'\[.*?\]', '', raw_text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            return {
                "ok": True,
                "text": cleaned,
                "engine": f"whisper_vulkan_{model_tag}",
                "model": model_tag
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": f"Сбой локального модуля Whisper: {exc}",
                "text": ""
            }
        finally:
            # Очищаем временный файл записи
            if wav_path.exists():
                try:
                    wav_path.unlink()
                except Exception:
                    pass
