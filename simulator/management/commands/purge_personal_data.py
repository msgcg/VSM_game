import os
import shutil
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from django.conf import settings
from simulator.models import (
    ConductorProfile,
    TrainingSession,
    EndlessShiftSession,
    Notification,
    ConductorAchievement,
    ConductorCompetencyScore,
    Scenario,
    RegulationDocument,
)


class Command(BaseCommand):
    help = "Полная очистка базы данных от персональных пользовательских данных, игровых сессий и токенов"

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-clean-template',
            action='store_true',
            help='Скопировать очищенную базу данных в db.sqlite3.clean',
        )

    def handle(self, *args, **options):
        self.stdout.write("Начало очистки базы данных от персональных данных...")

        user_count = User.objects.count()
        profile_count = ConductorProfile.objects.count()
        session_count = TrainingSession.objects.count()
        endless_count = EndlessShiftSession.objects.count()
        notif_count = Notification.objects.count()

        # Удаление игровых сессий и уведомлений
        TrainingSession.objects.all().delete()
        EndlessShiftSession.objects.all().delete()
        Notification.objects.all().delete()
        ConductorAchievement.objects.all().delete()
        ConductorCompetencyScore.objects.all().delete()

        # Удаление профилей и пользователей
        ConductorProfile.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write(
            f"Удалено: пользователей={user_count}, профилей={profile_count}, "
            f"сессий={session_count}, сессий карусели={endless_count}, уведомлений={notif_count}"
        )

        # Проверка сохранения эталонных каталогов
        sc_count = Scenario.objects.count()
        reg_count = RegulationDocument.objects.count()
        self.stdout.write(f"Сохранены эталонные каталоги: сценариев={sc_count}, нормативных документов={reg_count}")

        # Сжатие и физическая зачистка страниц SQLite (если вне транзакции)
        try:
            self.stdout.write("Выполнение VACUUM базы данных SQLite...")
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
        except Exception:
            pass

        db_path = settings.DATABASES['default']['NAME']
        clean_template_path = os.path.join(settings.BASE_DIR, 'db.sqlite3.clean')

        if options.get('create_clean_template') and os.path.exists(str(db_path)):
            try:
                shutil.copyfile(str(db_path), clean_template_path)
                self.stdout.write(f"Создан чистый эталонный шаблон: {clean_template_path}")
            except Exception as e:
                self.stderr.write(f"Ошибка копирования шаблона: {e}")

        self.stdout.write(self.style.SUCCESS("База данных успешно очищена от персональных данных!"))
