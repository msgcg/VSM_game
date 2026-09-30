import asyncio
import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from simulator.models import EndlessChallenge, ScenarioNode
from simulator.views import sanitize_tts_text, classify_speaker_persona

class Command(BaseCommand):
    help = "Предварительное кэширование реплик пассажиров и сценариев для мгновенного TTS отклика (0 сек)"

    def handle(self, *args, **options):
        self.stdout.write("Запуск предварительного кэширования аудиофайлов TTS ВСМ «Белый кречет»...")
        
        try:
            import edge_tts
        except ImportError:
            self.stderr.write("Пакет edge_tts не найден. Кэширование пропущено.")
            return

        cache_dir = settings.BASE_DIR / 'simulator' / 'static' / 'simulator' / 'audio' / 'tts_cache'
        cache_dir.mkdir(parents=True, exist_ok=True)

        items_to_cache = []
        seen_texts = set()

        def extract_items(source_queryset, is_node=True):
            for obj in source_queryset:
                raw = obj.dialogue_text
                if not raw:
                    continue
                clean = sanitize_tts_text(raw)
                if not clean or clean in seen_texts:
                    continue
                seen_texts.add(clean)

                title = obj.title if is_node else getattr(obj, 'title', '')
                _, _, actual_voice, rate, pitch = classify_speaker_persona(
                    obj.character_name, obj.character_role, title, clean
                )

                sig = f"{actual_voice}_{rate}_{pitch}_{clean}".encode('utf-8')
                h = hashlib.md5(sig).hexdigest()
                items_to_cache.append((clean, actual_voice, rate, pitch, h))

        extract_items(ScenarioNode.objects.filter(scenario__is_active=True), is_node=True)
        extract_items(EndlessChallenge.objects.all(), is_node=False)

        self.stdout.write(f"Найдено уникальных реплик для кэширования: {len(items_to_cache)}")

        cached_count = 0
        skipped_count = 0
        error_count = 0

        async def cache_item(clean, voice, rate, pitch, h):
            nonlocal cached_count, skipped_count, error_count
            out_file = cache_dir / f"{h}.mp3"

            if out_file.exists() and out_file.stat().st_size > 0:
                skipped_count += 1
                return

            try:
                comm = edge_tts.Communicate(clean, voice=voice, rate=rate, pitch=pitch)
                await comm.save(str(out_file))
                if out_file.exists() and out_file.stat().st_size > 0:
                    cached_count += 1
                else:
                    if out_file.exists():
                        out_file.unlink(missing_ok=True)
                    error_count += 1
            except Exception:
                if out_file.exists():
                    out_file.unlink(missing_ok=True)
                error_count += 1

        async def run_all():
            batch_size = 5
            for i in range(0, len(items_to_cache), batch_size):
                batch = items_to_cache[i:i + batch_size]
                await asyncio.gather(*(cache_item(*t) for t in batch))
                await asyncio.sleep(0.3)

        asyncio.run(run_all())

        self.stdout.write(self.style.SUCCESS(
            f"Кэширование завершено! Уже в кэше: {skipped_count}, успешно создано: {cached_count}, ошибок/пропущено: {error_count}"
        ))
