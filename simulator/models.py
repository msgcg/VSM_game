from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Competency(models.Model):
    """Компетенции проводника высокоскоростного поезда"""
    code = models.CharField(max_length=50, unique=True, verbose_name="Код компетенции")
    title = models.CharField(max_length=150, verbose_name="Название компетенции")
    description = models.TextField(verbose_name="Описание компетенции")
    icon = models.CharField(max_length=50, default="award", verbose_name="Иконка")
    color = models.CharField(max_length=30, default="#1c6389", verbose_name="Фирменный цвет")

    class Meta:
        verbose_name = "Компетенция"
        verbose_name_plural = "Компетенции"

    def __str__(self):
        return self.title


class ConductorProfile(models.Model):
    """Профиль проводника ВСМ"""
    RANKS = [
        ('trainee', 'Стажер-проводник ВСМ'),
        ('conductor', 'Проводник ВСМ 2 класса'),
        ('senior_conductor', 'Старший стюард ВСМ 1 класса'),
        ('instructor', 'Инструктор поездных бригад ВСМ'),
        ('master', 'Мастер высокоскоростного сервиса'),
    ]

    TRAINING_TRACKS = [
        ('all', 'Универсальная подготовка (Все классы)'),
        ('economy', 'Проводник Эконом-класса (Стандарт)'),
        ('comfort', 'Проводник Комфорт-класса'),
        ('business', 'Стюард Бизнес и Первого класса'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="conductor_profile")
    badge_number = models.CharField(max_length=30, default="VSM-0402", verbose_name="Табельный номер")
    full_name = models.CharField(max_length=150, verbose_name="ФИО сотрудника")
    depot = models.CharField(max_length=150, default="Москва-Октябрьская ВСМ (Северо-Западная дирекция)", verbose_name="Депо приписки")
    brigade = models.CharField(max_length=50, default="Поездная бригада № 1", verbose_name="Поездная бригада")
    rank = models.CharField(max_length=50, choices=RANKS, default='conductor', verbose_name="Квалификационный ранг")
    training_track = models.CharField(max_length=30, choices=TRAINING_TRACKS, default='all', verbose_name="Специализация обучения")
    level = models.PositiveIntegerField(default=1, verbose_name="Уровень")
    experience_points = models.PositiveIntegerField(default=350, verbose_name="Очки опыта (XP)")
    
    # Репутационные метрики проводника
    loyalty_rating = models.FloatField(default=88.5, verbose_name="Рейтинг лояльности (%)")
    safety_rating = models.FloatField(default=96.0, verbose_name="Рейтинг безопасности (%)")
    service_rating = models.FloatField(default=90.0, verbose_name="Рейтинг сервиса (%)")
    
    # Статистика рейсов
    shifts_completed = models.PositiveIntegerField(default=5, verbose_name="Завершенных смен / ситуаций")
    perfect_shifts = models.PositiveIntegerField(default=3, verbose_name="Безупречных смен")
    avatar = models.CharField(max_length=100, default="avatar_1.svg", verbose_name="Аватар")
    is_example = models.BooleanField(default=False, verbose_name="Тестовый аккаунт для примера")
    crew_members = models.ManyToManyField('self', symmetrical=True, blank=True, verbose_name="Члены поездного экипажа (коллеги/друзья)")

    # Корпоративный ID и личные ключи доступа к диалоговому ИИ
    sber_id = models.CharField(max_length=100, blank=True, default="", verbose_name="Корпоративный ID проводника")
    sber_client_id = models.CharField(max_length=120, blank=True, default="", verbose_name="Client ID платформы ИИ")
    sber_client_secret = models.CharField(max_length=120, blank=True, default="", verbose_name="Client Secret платформы ИИ")
    sber_access_token = models.TextField(blank=True, default="", verbose_name="Индивидуальный OAuth Access Token")
    sber_refresh_token = models.TextField(blank=True, default="", verbose_name="Индивидуальный OAuth Refresh Token")
    sber_auth_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Личный ключ авторизации платформы ИИ")
    sber_scope = models.CharField(max_length=100, blank=True, default="GIGACHAT_API_PERS", verbose_name="Scope авторизации")
    salutespeech_auth_key = models.CharField(max_length=255, blank=True, default="", verbose_name="Ключ авторизации речевого комплекса")

    def get_sber_client_id(self):
        if self.sber_client_id:
            return self.sber_client_id
        if self.sber_auth_key:
            try:
                import base64
                dec = base64.b64decode(self.sber_auth_key).decode('utf-8', errors='ignore')
                if ':' in dec:
                    return dec.split(':', 1)[0]
            except Exception:
                pass
        return ""

    def get_sber_client_secret(self):
        if self.sber_client_secret:
            return self.sber_client_secret
        if self.sber_auth_key:
            try:
                import base64
                dec = base64.b64decode(self.sber_auth_key).decode('utf-8', errors='ignore')
                if ':' in dec:
                    return dec.split(':', 1)[1]
            except Exception:
                pass
        return ""

    def get_track_progress(self):
        """Возвращает прогресс квалификации проводника по каждому классу обслуживания"""
        completed_ids = set(
            self.sessions.filter(status='completed').values_list('scenario_id', flat=True)
        )
        tracks_info = [
            ('economy', 'Эконом-класс (Стандарт)', 'shield-check', '#00d2ff'),
            ('comfort', 'Комфорт-класс', 'smile', '#10b981'),
            ('business', 'Бизнес и Первый класс', 'crown', '#f59e0b'),
        ]
        result = {}
        for code, title, icon, color in tracks_info:
            class_scenarios = Scenario.objects.filter(is_active=True, service_class__in=[code, 'all'])
            total = class_scenarios.count()
            passed = class_scenarios.filter(id__in=completed_ids).count()
            pct = int((passed / total * 100)) if total > 0 else 0
            result[code] = {
                'code': code,
                'title': title,
                'icon': icon,
                'color': color,
                'total': total,
                'passed': passed,
                'percentage': pct,
                'is_certified': pct >= 75,
                'is_active': (self.training_track == code),
            }
        return result

    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    def get_crew_synergy(self):
        members = self.crew_members.all()
        if not members.exists():
            return int((self.loyalty_rating + self.safety_rating + self.service_rating) / 3)
        total_rating = sum((m.loyalty_rating + m.safety_rating + m.service_rating) / 3 for m in members)
        my_rating = (self.loyalty_rating + self.safety_rating + self.service_rating) / 3
        return int((total_rating + my_rating) / (members.count() + 1))

    def add_to_crew(self, other_conductor):
        if other_conductor and other_conductor != self:
            self.crew_members.add(other_conductor)

    def remove_from_crew(self, other_conductor):
        if other_conductor:
            self.crew_members.remove(other_conductor)

    def is_in_crew(self, other_conductor):
        if not other_conductor:
            return False
        return self.crew_members.filter(id=other_conductor.id).exists()

    def reset_progress(self):
        self.experience_points = 100
        self.level = 1
        self.rank = 'trainee'
        self.loyalty_rating = 85.0
        self.safety_rating = 95.0
        self.service_rating = 85.0
        self.shifts_completed = 0
        self.perfect_shifts = 0
        self.save()
        self.sessions.all().delete()
        self.endless_sessions.all().delete()
        self.achievements.all().delete()
        for comp_score in self.competencies.all():
            comp_score.score = 50
            comp_score.save()

    class Meta:
        verbose_name = "Профиль проводника"
        verbose_name_plural = "Профили проводников"

    def __str__(self):
        return f"{self.full_name} [{self.badge_number}] — {self.get_rank_display()}"

    def add_xp(self, xp_amount):
        """Начисление опыта с расчетом ранга и уровня"""
        self.experience_points += xp_amount
        # Каждые 500 XP — новый уровень
        new_level = (self.experience_points // 500) + 1
        self.level = new_level

        if self.level >= 10:
            self.rank = 'master'
        elif self.level >= 7:
            self.rank = 'instructor'
        elif self.level >= 4:
            self.rank = 'senior_conductor'
        elif self.level >= 2:
            self.rank = 'conductor'
        else:
            self.rank = 'trainee'
        self.save()

    def get_progress_to_next_level(self):
        current_level_base = (self.level - 1) * 500
        current_progress = self.experience_points - current_level_base
        percentage = min(100, max(0, int((current_progress / 500) * 100)))
        needed = 500 - current_progress
        return {
            'progress_xp': current_progress,
            'needed_xp': max(0, needed),
            'percentage': percentage,
        }


class ConductorCompetencyScore(models.Model):
    """Баллы проводника по конкретной компетенции"""
    profile = models.ForeignKey(ConductorProfile, on_delete=models.CASCADE, related_name="competencies")
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=50, verbose_name="Уровень развития (0-100)")

    class Meta:
        unique_together = ('profile', 'competency')
        verbose_name = "Оценка компетенции"
        verbose_name_plural = "Оценки компетенций"

    def __str__(self):
        return f"{self.profile.full_name} — {self.competency.title}: {self.score} pts"


class Achievement(models.Model):
    """Достижения (ачивки) проводников ВСМ"""
    RARITY = [
        ('common', 'Обычное'),
        ('rare', 'Редкое'),
        ('epic', 'Эпическое'),
        ('legendary', 'Легендарное'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Код ачивки")
    title = models.CharField(max_length=150, verbose_name="Название достижения")
    description = models.TextField(verbose_name="Условие получения")
    icon_name = models.CharField(max_length=50, default="award", verbose_name="Иконка")
    badge_color = models.CharField(max_length=30, default="#082a99", verbose_name="Цвет плашки")
    xp_reward = models.PositiveIntegerField(default=200, verbose_name="Награда (XP)")
    rarity = models.CharField(max_length=30, choices=RARITY, default='rare', verbose_name="Редкость")

    class Meta:
        verbose_name = "Достижение"
        verbose_name_plural = "Достижения"

    def __str__(self):
        return f"{self.title} ({self.get_rarity_display()})"


class ConductorAchievement(models.Model):
    """Связь проводника с разблокированным достижением"""
    profile = models.ForeignKey(ConductorProfile, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(default=timezone.now, verbose_name="Разблокировано")

    class Meta:
        unique_together = ('profile', 'achievement')
        verbose_name = "Полученное достижение"
        verbose_name_plural = "Полученные достижения"

    def __str__(self):
        return f"{self.profile.full_name} -> {self.achievement.title}"


class Scenario(models.Model):
    """Сценарий тренажера ВСМ (ситуационная задача)"""
    CATEGORIES = [
        ('conflict', 'Конфликт и претензии пассажиров'),
        ('medical', 'Медицинский инцидент и первая помощь'),
        ('safety', 'Пожарная тревога и безопасность'),
        ('anti_terror', 'Антитеррористический регламент'),
        ('tech_failure', 'Технический сбой и климат'),
        ('vip_service', 'Премиальный VIP-сервис 400 км/ч'),
    ]

    DIFFICULTIES = [
        ('easy', 'Базовый (Стандарт)'),
        ('medium', 'Повышенный (Бизнес)'),
        ('hard', 'Стрессовый (400 км/ч)'),
        ('extreme', 'Критический инцидент'),
    ]

    SERVICE_CLASSES = [
        ('economy', 'Эконом-класс (Стандарт)'),
        ('comfort', 'Комфорт-класс'),
        ('business', 'Бизнес и Первый класс'),
        ('all', 'Общепоездной регламент / ПТЭ'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название сценария")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-слаг")
    category = models.CharField(max_length=50, choices=CATEGORIES, default='conflict', verbose_name="Категория")
    difficulty = models.CharField(max_length=30, choices=DIFFICULTIES, default='medium', verbose_name="Сложность")
    service_class = models.CharField(max_length=30, choices=SERVICE_CLASSES, default='all', verbose_name="Класс обслуживания")
    
    # Контекст рейса ВСМ
    train_speed = models.PositiveIntegerField(default=360, verbose_name="Скорость поезда (км/ч)")
    train_number = models.CharField(max_length=50, default="№ 702 «Белый кречет» Москва — Санкт-Петербург", verbose_name="Поезд")
    location_name = models.CharField(max_length=150, default="Перегон Новая Тверь — Логовежь, 218 км", verbose_name="Локация перегона")
    car_info = models.CharField(max_length=150, default="Вагон № 2 (Бизнес-класс)", verbose_name="Класс вагона")
    
    description = models.TextField(verbose_name="Краткое описание вводной")
    briefing = models.TextField(verbose_name="Подробный вводный инструктаж")
    regulation_reference = models.TextField(verbose_name="Нормативный регламент / Ссылка на стандарты ВСМ")
    background_image = models.CharField(max_length=100, default="vsm_train_exterior.jpg", verbose_name="Фоновое изображение")
    
    base_xp = models.PositiveIntegerField(default=250, verbose_name="Базовый XP за прохождение")
    time_limit_default = models.PositiveIntegerField(default=30, verbose_name="Таймер по умолчанию (сек)")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок вывода")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def get_service_class_badge(self):
        badges = {
            'economy': {'label': 'Эконом-класс', 'code': 'economy', 'css_class': 'vsm-badge-track-economy', 'icon': 'shield-check', 'color': 'border-sky-500/40 bg-sky-950/50 text-sky-300', 'dot': 'bg-sky-400'},
            'comfort': {'label': 'Комфорт-класс', 'code': 'comfort', 'css_class': 'vsm-badge-track-comfort', 'icon': 'smile', 'color': 'border-emerald-500/40 bg-emerald-950/50 text-emerald-300', 'dot': 'bg-emerald-400'},
            'business': {'label': 'Бизнес-класс', 'code': 'business', 'css_class': 'vsm-badge-track-business', 'icon': 'crown', 'color': 'border-amber-500/40 bg-amber-950/50 text-amber-300', 'dot': 'bg-amber-400'},
            'all': {'label': 'Общепоездной', 'code': 'all', 'css_class': 'vsm-badge-track-all', 'icon': 'train', 'color': 'border-indigo-500/40 bg-indigo-950/50 text-indigo-300', 'dot': 'bg-indigo-400'},
        }
        return badges.get(self.service_class, badges['all'])


class ScenarioNode(models.Model):
    """Узел интерактивного диалогового дерева сценария"""
    MOODS = [
        ('calm', 'Спокойное'),
        ('irritated', 'Раздраженное / Агрессивное'),
        ('panicked', 'Паника / Испуг'),
        ('critical', 'Критическое состояние здоровья'),
        ('formal', 'Деловое / Протокольное'),
    ]

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="nodes")
    node_key = models.CharField(max_length=50, verbose_name="Ключ узла (например, start)")
    title = models.CharField(max_length=150, verbose_name="Заголовок этапа")
    
    character_name = models.CharField(max_length=100, default="Пассажир", verbose_name="Имя субъекта")
    character_role = models.CharField(max_length=100, default="Пассажир бизнес-класса", verbose_name="Роль субъекта")
    character_mood = models.CharField(max_length=50, choices=MOODS, default='irritated', verbose_name="Состояние / Тон")
    
    dialogue_text = models.TextField(verbose_name="Реплика пассажира / Сообщение системы")
    narrative_context = models.TextField(blank=True, verbose_name="Оперативная обстановка (пульт, датчики, салон)")
    time_limit_seconds = models.PositiveIntegerField(default=25, verbose_name="Лимит времени на решение (сек)")
    
    is_terminal = models.BooleanField(default=False, verbose_name="Финальный узел (конец сценария)")
    is_success = models.BooleanField(default=False, verbose_name="Успешный финал")
    resolution_report = models.TextField(blank=True, verbose_name="Экспертный разбор действий и ошибок")
    timeout_next_node_key = models.CharField(max_length=50, blank=True, default="", verbose_name="Узел при истечении времени")
    timeout_penalty = models.IntegerField(default=15, verbose_name="Штраф при таймауте")

    class Meta:
        unique_together = ('scenario', 'node_key')
        verbose_name = "Узел сценария"
        verbose_name_plural = "Узлы сценариев"

    def __str__(self):
        return f"{self.scenario.title} -> [{self.node_key}] {self.title}"


class ScenarioChoice(models.Model):
    """Вариант решения проводника в текущем узле"""
    AUDIO_CUES = [
        ('neutral', 'Обычный тон (Клик)'),
        ('success', 'Успешное действие (Сигнал согласия)'),
        ('warning', 'Предупреждение (Внимание)'),
        ('emergency', 'Тревога (Критическая ошибка)'),
    ]

    node = models.ForeignKey(ScenarioNode, on_delete=models.CASCADE, related_name="choices")
    choice_text = models.CharField(max_length=350, verbose_name="Действие проводника / Реплика")
    tactical_hint = models.CharField(max_length=250, blank=True, verbose_name="Тактическая мысль / Регламентная логика")
    next_node_key = models.CharField(max_length=50, verbose_name="Ключ следующего узла")
    
    # Влияние выбора на шкалы в реальном времени
    loyalty_impact = models.IntegerField(default=0, verbose_name="Изменение лояльности")
    safety_impact = models.IntegerField(default=0, verbose_name="Изменение безопасности")
    service_impact = models.IntegerField(default=0, verbose_name="Изменение качества сервиса")
    stress_impact = models.IntegerField(default=5, verbose_name="Изменение стресса (+ / -)")
    
    # Очки компетенций
    competency = models.ForeignKey(Competency, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Компетенция")
    competency_points = models.IntegerField(default=10, verbose_name="Очки компетенции")
    
    feedback_toast = models.CharField(max_length=300, blank=True, verbose_name="Моментальная обратная связь")
    audio_cue = models.CharField(max_length=30, choices=AUDIO_CUES, default='neutral', verbose_name="Звуковой отклик")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок вывода")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Вариант выбора проводника"
        verbose_name_plural = "Варианты выбора проводника"

    def __str__(self):
        return f"[{self.node.node_key}] -> {self.choice_text[:60]}"


class TrainingSession(models.Model):
    """Сессия прохождения обучающего сценария проводником"""
    STATUSES = [
        ('in_progress', 'В процессе прохождения'),
        ('completed', 'Успешно завершен'),
        ('failed', 'Провален (нарушение регламента ВСМ)'),
        ('timeout', 'Провален по таймеру'),
    ]

    conductor = models.ForeignKey(ConductorProfile, on_delete=models.CASCADE, related_name="sessions")
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="sessions")
    current_node = models.ForeignKey(ScenarioNode, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Текущие показатели сессии
    current_loyalty = models.IntegerField(default=75, verbose_name="Лояльность (%)")
    current_safety = models.IntegerField(default=95, verbose_name="Безопасность (%)")
    current_service = models.IntegerField(default=80, verbose_name="Качество сервиса (%)")
    current_stress = models.IntegerField(default=20, verbose_name="Уровень стресса (%)")
    
    elapsed_seconds = models.PositiveIntegerField(default=0, verbose_name="Затрачено секунд")
    status = models.CharField(max_length=30, choices=STATUSES, default='in_progress', verbose_name="Статус сессии")
    is_success = models.BooleanField(default=False, verbose_name="Успешный итог")
    final_score = models.IntegerField(default=0, verbose_name="Итоговый счет")
    earned_xp = models.IntegerField(default=0, verbose_name="Заработанный XP")
    
    # Лог действий проводника (для разбора "Черного ящика")
    session_log = models.JSONField(default=list, verbose_name="Лог принятых решений")
    debrief_feedback = models.JSONField(default=dict, blank=True, verbose_name="Обучающий экспертный разбор")
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Начало")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Завершение")

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Обучающая сессия"
        verbose_name_plural = "Обучающие сессии"

    def __str__(self):
        return f"{self.conductor.full_name} | {self.scenario.title} ({self.get_status_display()})"


class EndlessChallenge(models.Model):
    """Задача для карусели бесконечных скоростных решений (от легких к сложным)"""
    DIFFICULTIES = [
        (1, 'Уровень 1: Штатный сервис (250 км/ч)'),
        (2, 'Уровень 2: Напряженная посадка (300 км/ч)'),
        (3, 'Уровень 3: Конфликты и сбои (350 км/ч)'),
        (4, 'Уровень 4: Высокий стресс (380 км/ч)'),
        (5, 'Уровень 5: Критический экстрим (400 км/ч)'),
    ]

    SERVICE_CLASSES = [
        ('economy', 'Эконом-класс (Стандарт)'),
        ('comfort', 'Комфорт-класс'),
        ('business', 'Бизнес и Первый класс'),
        ('all', 'Общепоездной регламент / ПТЭ'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Код задачи")
    title = models.CharField(max_length=200, verbose_name="Название задачи")
    category = models.CharField(max_length=50, default="service", verbose_name="Категория")
    difficulty_level = models.PositiveIntegerField(default=1, choices=DIFFICULTIES, verbose_name="Уровень сложности")
    service_class = models.CharField(max_length=30, choices=SERVICE_CLASSES, default='all', verbose_name="Класс обслуживания")
    
    train_speed = models.PositiveIntegerField(default=300, verbose_name="Скорость (км/ч)")
    car_info = models.CharField(max_length=100, default="Вагон № 3 (Комфорт)", verbose_name="Вагон")
    character_name = models.CharField(max_length=100, default="Пассажир", verbose_name="Имя субъекта")
    character_role = models.CharField(max_length=100, default="Пассажир", verbose_name="Роль")
    character_mood = models.CharField(max_length=50, default="neutral", verbose_name="Тон/Настроение")
    
    situation_text = models.TextField(verbose_name="Описание ситуации на борту")
    dialogue_text = models.TextField(blank=True, verbose_name="Реплика персонажа / Вызов системы")
    timer_seconds = models.PositiveIntegerField(default=20, verbose_name="Таймер на решение (сек)")
    regulation_reference = models.TextField(verbose_name="Пункт правил / Отраслевой регламент ВСМ")
    competency_code = models.CharField(max_length=50, default="service_etiquette", verbose_name="Код ключевой компетенции")
    
    # Список вариантов решений (JSON: text, hint, is_correct, loyalty_delta, safety_delta, service_delta, stress_delta, feedback)
    choices_data = models.JSONField(default=list, verbose_name="Варианты решений")
    source_type = models.CharField(max_length=30, default='carousel', choices=[('carousel', 'Задача карусели'), ('scenario', 'Из сценария ВСМ')], verbose_name="Источник задачи")
    source_scenario = models.ForeignKey('Scenario', on_delete=models.SET_NULL, null=True, blank=True, related_name='carousel_challenges', verbose_name="Связанный сценарий")

    CATEGORIES = [
        ('service', 'Сервис и стандарты обслуживания'),
        ('conflict', 'Конфликт и претензии пассажиров'),
        ('medical', 'Медицинский инцидент и первая помощь'),
        ('safety', 'Пожарная тревога и безопасность'),
        ('anti_terror', 'Антитеррористический регламент'),
        ('tech', 'Технический регламент и ПТЭ'),
        ('tech_failure', 'Технический сбой и климат'),
        ('vip_service', 'Премиальный VIP-сервис 400 км/ч'),
    ]

    def get_category_display(self):
        cat_map = dict(self.CATEGORIES)
        cat_map.update({
            'service_etiquette': 'Сервисный этикет ВСМ',
            'emergency_medical': 'Первая помощь и медицина',
            'safety_regulations': 'Безопасность движения и ПТЭ',
            'vsm_tech_protocols': 'Технические протоколы ВСМ',
        })
        return cat_map.get(self.category, self.category.replace('_', ' ').capitalize())

    def get_cover_image(self):
        """Возвращает тематическое железнодорожное изображение для карточки экспресс-кейса"""
        if self.source_scenario and self.source_scenario.background_image:
            bg = self.source_scenario.background_image
            if not bg.startswith('train_interior_') and not bg.startswith('station_'):
                return bg
        
        code = (self.code or '').lower()
        title = (self.title or '').lower()
        text = (self.situation_text or '').lower()
        cat = (self.category or '').lower()
        full = f"{code} {title} {cat} {text}"
        
        # 1. Маломобильные пассажиры, инвалидная коляска, доступная среда (МГН)
        if any(k in full for k in ['маломобильн', 'инвалид', 'колясочн', 'кресло-коляск', 'кресле-коляск', 'мгн', 'подъемник', 'пандус', 'wheelchair', 'mobility']):
            return 'sc_mobility_assist.jpg'
        # 2. Домашние животные, питомцы, переноски, собака, кошка, аллергия на шерсть
        if any(k in full for k in ['питом', 'животн', 'собак', 'кошк', 'кошач', 'собач', 'хорек', 'хорёк', 'переноск', 'pet', 'carrier']):
            return 'sc_pet_carrier.jpg'
        # 3. Посадка на платформе, проверка билета/паспорта, опоздание к дверям, забытые вещи на перроне
        if any(k in full for k in ['посадк', 'перрон', 'платформ', 'опоздавш', 'документ', 'паспорт', 'проездн', 'без билет', 'отстал', 'вокзал']):
            return 'sc_platform_boarding.jpg'
        # 4. Пожар, задымление, вейп, сигареты
        if any(k in full for k in ['пожар', 'дым', 'курен', 'вейп', 'огнетуш', 'возгоран', 'запах гари', 'smoke', 'fire']):
            return 'sc_smoke_alarm.jpg'
        # 5. Кардиология, медицина, обморок, скорая помощь
        if any(k in full for k in ['сердц', 'инфаркт', 'пульс', 'аптечк', 'врач', 'медиц', 'сознан', 'аллерг', 'анафилак', 'травм', 'эпилепс', 'давлен', 'cardiac', 'medical', 'первая помощь', 'реанимац', 'дефибрил']):
            return 'sc_cardiac_emergency.jpg'
        # 6. Дети, младенцы, несовершеннолетние
        if any(k in full for k in ['ребенок', 'ребёнк', 'дети', 'детск', 'младен', 'малыш', 'несовершеннолет', 'child']):
            return 'sc_child_care.jpg'
        # 7. Антитеррор, бесхозные предметы
        if any(k in full for k in ['бесхоз', 'подозрительн', 'террор', 'забытый', 'оставленн', 'коробка с проводами', 'unattended', 'briefcase', 'antiterror']):
            return 'sc_unattended_bag.jpg'
        # 8. Крупногабаритный багаж, чемоданы, велосипеды
        if any(k in full for k in ['багаж', 'чемодан', 'проход', 'велосипед', 'ручная кладь', 'luggage', 'oversized']):
            return 'sc_oversized_luggage.jpg'
        # 9. СКНБ, буксы, тележки, датчики перегрева
        if any(k in full for k in ['скнб', 'букс', 'перегрев буксы', 'датчик скнб', 'sknb']):
            return 'sc_sknb_sensor.jpg'
        # 10. Пантограф, токоприемник, контактная сеть
        if any(k in full for k in ['пантограф', 'токоприем', 'обледен', 'контактн', 'напряжен', 'сеть', 'pantograph']):
            return 'sc_pantograph.jpg'
        # 11. Санузел, туалет, вакуумная система
        if any(k in full for k in ['туалет', 'санузел', 'вакуум', 'засор', 'toilet', 'fram3']):
            return 'sc_vacuum_toilet.jpg'
        # 12. Бистро, ресторан, горячее питание, кофе
        if any(k in full for k in ['бистро', 'вагон-ресторан', 'кафе', 'буфет', 'рацион питания', 'горячее блюдо', 'bistro']):
            return 'sc_bistro_bar.jpg'
        # 13. Мультимедиа, розетка 220V, блок розеток, USB, зарядка
        if any(k in full for k in ['розетк', 'мультимед', 'монитор', 'зарядк', 'пауэрбанк', 'power', 'outlet']):
            return 'vsm_train_equipment.jpg'
        # 14. Дрон, виадук, мост
        if any(k in full for k in ['дрон', 'виадук', 'мост', 'препятстви', 'drone']):
            return 'sc_drone_viaduct.jpg'
        # 15. Кабина машиниста, служебные двери, герметичность дверей
        if any(k in full for k in ['кабин', 'машинист', 'дверь в служеб', 'cab_door', 'intrusion', 'уплотнен', 'герметич', 'door_seal']):
            return 'sc_cab_door.jpg'
        # 16. Климат, кондиционер, вентиляция, замыкание на корпус
        if any(k in full for k in ['замыкан', 'электропит', 'обесточ', 'кондиционер', 'климат', 'вентиляц', 'жар', 'духот', 'fault', 'ground_fault']):
            return 'sc_ground_fault.jpg'
        # 17. Телефонные разговоры, тихая зона, шум в салоне
        if any(k in full for k in ['телефон', 'наушник', 'тихая зона', 'громк', 'speaker']):
            return 'vsm_cabin_passengers.jpg'
        # 18. Повышение класса обслуживания, классы ВСМ
        if any(k in full for k in ['повышен', 'апгрейд', 'класс обслуж', 'upgrade']):
            return 'vsm_classes_overview.jpg'
        # 19. Рассадка, схема мест, овербукинг
        if any(k in full for k in ['рассадк', 'схема', 'овербук', 'двойная продажа']):
            return 'vsm_classes_schemes.jpg'
        # 20. Хвостовые сигналы, экстерьер состава, скорость
        if any(k in full for k in ['хвостов', 'сигнал', 'поезд снаружи', 'скорост', 'tail_signal', 'exterior']):
            return 'vsm_train_exterior.jpg'
        # 21. Билеты, опечатки, паспорта, конфликт
        if any(k in full for k in ['билет', 'опечатка', 'фамили', 'бизнес-класс', 'бизнес', 'купэ', 'пересад', 'место занято', 'conflict', 'vip']):
            return 'sc_business_conflict.jpg'
        
        cat_fallbacks = {
            'medical': 'sc_cardiac_emergency.jpg',
            'safety': 'sc_smoke_alarm.jpg',
            'anti_terror': 'sc_unattended_bag.jpg',
            'tech': 'sc_sknb_sensor.jpg',
            'tech_failure': 'sc_ground_fault.jpg',
            'conflict': 'sc_business_conflict.jpg',
            'vip_service': 'vsm_classes_overview.jpg',
            'service': 'vsm_cabin_passengers.jpg',
            'tickets': 'sc_platform_boarding.jpg',
            'luggage': 'sc_oversized_luggage.jpg',
            'mobility': 'sc_mobility_assist.jpg',
            'pets': 'sc_pet_carrier.jpg',
        }
        return cat_fallbacks.get(cat, 'vsm_train_exterior.jpg')

    class Meta:
        ordering = ['difficulty_level', 'id']
        verbose_name = "Задача бесконечной карусели"
        verbose_name_plural = "Задачи бесконечной карусели"

    def __str__(self):
        return f"[Ур. {self.difficulty_level}] {self.title}"

    def get_service_class_badge(self):
        badges = {
            'economy': {'label': 'Эконом-класс', 'code': 'economy', 'css_class': 'vsm-badge-track-economy', 'icon': 'shield-check', 'color': 'border-sky-500/40 bg-sky-950/50 text-sky-300', 'dot': 'bg-sky-400'},
            'comfort': {'label': 'Комфорт-класс', 'code': 'comfort', 'css_class': 'vsm-badge-track-comfort', 'icon': 'smile', 'color': 'border-emerald-500/40 bg-emerald-950/50 text-emerald-300', 'dot': 'bg-emerald-400'},
            'business': {'label': 'Бизнес-класс', 'code': 'business', 'css_class': 'vsm-badge-track-business', 'icon': 'crown', 'color': 'border-amber-500/40 bg-amber-950/50 text-amber-300', 'dot': 'bg-amber-400'},
            'all': {'label': 'Общепоездной', 'code': 'all', 'css_class': 'vsm-badge-track-all', 'icon': 'train', 'color': 'border-indigo-500/40 bg-indigo-950/50 text-indigo-300', 'dot': 'bg-indigo-400'},
        }
        return badges.get(self.service_class, badges['all'])


class EndlessShiftSession(models.Model):
    """Сессия режима «Бесконечная смена: Карусель решений»"""
    STATUSES = [
        ('active', 'На линии (активна)'),
        ('completed', 'Смена сдана (успешно)'),
        ('failed', 'Сход с линии (провал лояльности/безопасности)'),
    ]

    SERVICE_CLASSES = [
        ('all', 'Смешанный рейс ВСМ-1 (Все классы)'),
        ('economy', 'Смена в Эконом-классе (Стандарт)'),
        ('comfort', 'Смена в Комфорт-классе'),
        ('business', 'Смена в Бизнес и Первом классе'),
    ]

    conductor = models.ForeignKey(ConductorProfile, on_delete=models.CASCADE, related_name="endless_sessions")
    service_class = models.CharField(max_length=30, choices=SERVICE_CLASSES, default='all', verbose_name="Класс вагона смены")
    shift_number = models.PositiveIntegerField(default=1, verbose_name="Номер смены")
    target_challenges_count = models.PositiveIntegerField(default=8, verbose_name="План смены (рейс)")
    current_streak = models.PositiveIntegerField(default=0, verbose_name="Текущая серия верных решений")
    max_streak = models.PositiveIntegerField(default=0, verbose_name="Максимальный стрик (рекорд)")
    challenges_solved = models.PositiveIntegerField(default=0, verbose_name="Решено ситуаций")
    mistakes_count = models.PositiveIntegerField(default=0, verbose_name="Количество ошибок")
    is_perfect = models.BooleanField(default=True, verbose_name="Безупречная смена")
    total_score = models.PositiveIntegerField(default=0, verbose_name="Суммарный счет")
    earned_xp = models.PositiveIntegerField(default=0, verbose_name="Заработанный XP")
    
    current_speed = models.PositiveIntegerField(default=260, verbose_name="Текущая скорость поезда")
    current_loyalty = models.IntegerField(default=85, verbose_name="Лояльность (%)")
    current_safety = models.IntegerField(default=95, verbose_name="Безопасность (%)")
    current_service = models.IntegerField(default=85, verbose_name="Сервис (%)")
    current_stress = models.IntegerField(default=15, verbose_name="Стресс (%)")
    
    status = models.CharField(max_length=30, choices=STATUSES, default='active', verbose_name="Статус смены")
    solved_challenge_ids = models.JSONField(default=list, verbose_name="ID решенных задач")
    history_log = models.JSONField(default=list, verbose_name="История решений смены")
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Начало")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Завершение")

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Сессия бесконечной смены"
        verbose_name_plural = "Сессии бесконечных смен"

    @property
    def multiplier(self):
        """Динамический множитель комбо очков в зависимости от серии верных решений"""
        if self.current_streak >= 15:
            return 5.0
        elif self.current_streak >= 10:
            return 3.5
        elif self.current_streak >= 6:
            return 2.5
        elif self.current_streak >= 3:
            return 1.8
        elif self.current_streak >= 1:
            return 1.2
        return 1.0

    def __str__(self):
        return f"{self.conductor.full_name} | Бесконечная смена ({self.challenges_solved} задач, стрик {self.max_streak})"



class RegulationDocument(models.Model):
    """Официальный нормативно-справочный документ ВСМ, хранящийся в БД"""
    key = models.CharField(max_length=60, unique=True, verbose_name="Уникальный ключ документа")
    title = models.CharField(max_length=255, verbose_name="Название документа")
    subtitle = models.CharField(max_length=255, blank=True, verbose_name="Подзаголовок / Номер распоряжения")
    order_number = models.CharField(max_length=100, blank=True, verbose_name="Номер нормативного акта")
    category = models.CharField(max_length=50, default="standard", verbose_name="Категория регламента")
    badge = models.CharField(max_length=100, default="Стандарт ВСМ", verbose_name="Текст плашки")
    badge_color = models.CharField(max_length=30, default="#082a99", verbose_name="Цвет плашки")
    icon = models.CharField(max_length=50, default="book-open", verbose_name="Иконка")
    description = models.TextField(verbose_name="Аннотация и назначение")
    content_markdown = models.TextField(verbose_name="Структурированный текст регламента")
    chapters_data = models.JSONField(default=list, verbose_name="Список глав и разделов")
    file_base64 = models.TextField(blank=True, verbose_name="Base64 бинарного PDF файла")
    file_name = models.CharField(max_length=150, default="document.pdf", verbose_name="Имя файла для скачивания")
    file_size_display = models.CharField(max_length=50, default="150 КБ", verbose_name="Отображаемый размер")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок вывода")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Нормативный документ (БД)"
        verbose_name_plural = "Нормативные документы (БД)"

    def __str__(self):
        return f"{self.title} ({self.key})"


class Notification(models.Model):
    """Уведомления проводника о событиях, вызовах и сгорающих баллах"""
    TYPES = [
        ('scenario', 'Новый сценарий'),
        ('challenge', 'Скоростной челлендж'),
        ('points_expiring', 'Сгорающие баллы'),
        ('achievement', 'Новое достижение'),
        ('system', 'Системное оповещение'),
    ]

    conductor = models.ForeignKey(ConductorProfile, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Текст оповещения")
    notification_type = models.CharField(max_length=50, choices=TYPES, default='system', verbose_name="Тип")
    link = models.CharField(max_length=255, blank=True, verbose_name="Ссылка для перехода")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Время получения")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return f"{self.conductor.full_name}: {self.title}"


