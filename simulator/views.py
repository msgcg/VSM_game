import os
import json
import base64
import io
import random
import hashlib
import re
import uuid
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, FileResponse, Http404, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.contrib import messages
from django.urls import reverse

from .document_library import (
    REGULATION_DOCUMENTS,
    CONDUCTOR_CHEAT_SHEETS,
    get_document_file_path,
    get_document_pdf_path,
    get_or_create_document_pdf,
    get_document_raw_content,
)
from .forms import ConductorRegistrationForm, ConductorLoginForm
from .models import (
    Scenario,
    ScenarioNode,
    ScenarioChoice,
    TrainingSession,
    ConductorProfile,
    Achievement,
    ConductorAchievement,
    Competency,
    ConductorCompetencyScore,
    EndlessChallenge,
    EndlessShiftSession,
    RegulationDocument,
    Notification,
)
from .services.sber_service import SberAIService


def ensure_conductor_notifications(conductor):
    """Инициализация базовых системных уведомлений проводника при первом входе"""
    if not conductor or conductor.notifications.exists():
        return
    initial_notifications = [
        {
            'title': 'Новый кейс: Анафилактический шок в вагоне-бистро',
            'message': 'Доступен новый интерактивный сценарий на скорости 400 км/ч с отработкой экстренной доврачебной помощи.',
            'notification_type': 'scenario',
            'link': '/scenario/child-anaphylaxis-bistro/',
        },
        {
            'title': 'Скоростной вызов: Безупречный рейс «Белый кречет»',
            'message': 'Завершите скоростную смену в «Карусели решений» без единой ошибки и получите +300 XP.',
            'notification_type': 'challenge',
            'link': '/endless/',
        },
        {
            'title': 'Сгорающие квалификационные баллы',
            'message': 'Внимание! 50 баллов сервисной квалификации сгорят через 48 часов без подтверждения в сценарии.',
            'notification_type': 'points_expiring',
            'link': '/scenarios/',
        },
        {
            'title': 'Повышение квалификации экипажа',
            'message': 'Вам доступна аттестация на квалификационный ранг «Старший стюард ВСМ 1 класса».',
            'notification_type': 'achievement',
            'link': '/profile/',
        },
    ]
    for item in initial_notifications:
        Notification.objects.create(
            conductor=conductor,
            title=item['title'],
            message=item['message'],
            notification_type=item['notification_type'],
            link=item['link'],
            is_read=False
        )


def get_current_conductor(request):
    """Возвращает текущий профиль проводника или None, если пользователь не авторизован"""
    if request.user.is_authenticated and hasattr(request.user, 'conductor_profile'):
        profile = request.user.conductor_profile
        ensure_conductor_notifications(profile)
        return profile
    return None


def get_gamified_stations(conductor_level=1):
    """
    Интерактивно-игровой маршрут ВСМ-1 Москва — Санкт-Петербург (679 км):
    Чем выше уровень проводника — тем дальше открыта станция, выше скорость и статус.
    """
    stations_data = [
        {
            'id': 1,
            'name': 'Москва',
            'subname': 'Ленинградский вокзал',
            'km': 0,
            'required_level': 1,
            'travel_time': '0 мин',
            'speed_limit': '200 км/ч',
            'features': ['Парк формирования поездов', 'Предрейсовый медосмотр', 'Сервисный центр экипировки'],
            'scenarios_here': ['ticket-typo-conflict', 'unattended-briefcase'],
            'carousel_challenges_here': ['ech_child_ticket', 'ech_typo_passport'],
            'bonus_xp': 50,
        },
        {
            'id': 2,
            'name': 'Зеленоград',
            'subname': 'Крюково ВСМ',
            'km': 41,
            'required_level': 2,
            'travel_time': '14 мин',
            'speed_limit': '250 км/ч',
            'features': ['Первый скоростной разгон', 'Контроль посадки УКЭБ', 'Пункт полиции ЛУВДТ'],
            'scenarios_here': ['oversized-bicycle-conflict', 'unaccompanied-child-passenger'],
            'carousel_challenges_here': ['ech_luggage_aisle', 'ech_ticket_left_behind'],
            'bonus_xp': 100,
        },
        {
            'id': 3,
            'name': 'Высоковск',
            'subname': 'Клинский кластер',
            'km': 87,
            'required_level': 3,
            'travel_time': '24 мин',
            'speed_limit': '300 км/ч',
            'features': ['Выход на крейсерский режим', 'Автоматика энергоснабжения 27.5 кВ'],
            'scenarios_here': ['ac-failure-heatwave', 'overbooking-seat-conflict'],
            'carousel_challenges_here': ['ech_phone_shield', 'ech_vape_vestibule'],
            'bonus_xp': 150,
        },
        {
            'id': 4,
            'name': 'Новая Тверь',
            'subname': '168 км трассы',
            'km': 168,
            'required_level': 4,
            'travel_time': '39 мин',
            'speed_limit': '350 км/ч',
            'features': ['Опорный транспортный узел', 'Депо технического обслуживания', 'Бригада скорой помощи'],
            'scenarios_here': ['passenger-missed-train', 'business-class-conflict'],
            'carousel_challenges_here': ['ech_forgotten_laptop', 'ech_overbooking_fast'],
            'bonus_xp': 200,
        },
        {
            'id': 5,
            'name': 'Логовежь',
            'subname': 'Торжокский район',
            'km': 218,
            'required_level': 5,
            'travel_time': '48 мин',
            'speed_limit': '380 км/ч',
            'features': ['Высокоскоростной виадук', 'Диагностический пост КТСМ/СКНБ'],
            'scenarios_here': ['sknb-overheating-alarm', 'chassis-ground-fault'],
            'carousel_challenges_here': ['ech_pet_carrier_rules', 'ech_sknb_warning_car'],
            'bonus_xp': 250,
        },
        {
            'id': 6,
            'name': 'Валдай',
            'subname': 'Валдайская возвышенность',
            'km': 312,
            'required_level': 6,
            'travel_time': '1 ч 06 мин',
            'speed_limit': '400 км/ч',
            'features': ['Сердце магистрали ВСМ', 'Сложный криволинейный рельеф', 'Пункт спасателей СПАС-ВО'],
            'scenarios_here': ['vacuum-toilet-system-failure', 'pantograph-icing-voltage-drop'],
            'carousel_challenges_here': ['ech_epilepsy_fit', 'ech_fire_bridge_quick'],
            'bonus_xp': 300,
        },
        {
            'id': 7,
            'name': 'Великий Новгород',
            'subname': 'Новгородский узел',
            'km': 450,
            'required_level': 7,
            'travel_time': '1 ч 32 мин',
            'speed_limit': '400 км/ч',
            'features': ['Северный пересадочный хаб', 'Пункт оперативного реагирования медицины'],
            'scenarios_here': ['child-anaphylaxis-bistro', 'cardiac-emergency'],
            'carousel_challenges_here': ['ech_cpr_cardiac_max', 'ech_body_ground_fault'],
            'bonus_xp': 400,
        },
        {
            'id': 8,
            'name': 'Санкт-Петербург',
            'subname': 'Главный терминал ВСМ',
            'km': 679,
            'required_level': 8,
            'travel_time': '2 ч 15 мин',
            'speed_limit': 'Конечная станция',
            'features': ['Главный терминал двух столиц', 'Приемка/сдача составов', 'Высшая квалификация проводника'],
            'scenarios_here': ['lost-passport-migration-card', 'security-cab-door-intrusion'],
            'carousel_challenges_here': ['ech_door_seal_breach', 'ech_tail_signal_failure'],
            'bonus_xp': 500,
        },
    ]

    # Словарь русских названий и описаний сценариев для станций
    russian_scenario_meta = {
        'ticket-typo-conflict': {
            'title': 'Опечатка в билете: Конфликт в VIP-купе',
            'description': 'Урегулирование ошибки в фамилии пассажира в соответствии с Отраслевым распоряжением № 852.',
            'difficulty': 'Легкий',
            'difficulty_code': 'easy',
        },
        'unattended-briefcase': {
            'title': 'Бесхозный предмет: Опасная находка в салоне',
            'description': 'Отработка антитеррористического протокола и взаимодействия со службой безопасности на перроне.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'oversized-bicycle-conflict': {
            'title': 'Негабаритный багаж: Велосипед в проходе',
            'description': 'Разрешение конфликтной ситуации при посадке пассажира с неразобранным инвентарем.',
            'difficulty': 'Легкий',
            'difficulty_code': 'easy',
        },
        'unaccompanied-child-passenger': {
            'title': 'Несовершеннолетний без сопровождения на 350 км/ч',
            'description': 'Особый надзор за ребенком в пути следования и передача встречающим на опорной станции.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'ac-failure-heatwave': {
            'title': 'Отказ климат-контроля: +33°C в вагоне при 380 км/ч',
            'description': 'Перезапуск климатической установки, деэскалация возмущения пассажиров и раздача прохладительных напитков.',
            'difficulty': 'Сложный',
            'difficulty_code': 'hard',
        },
        'overbooking-seat-conflict': {
            'title': 'Овербукинг (двойная продажа) места на скорости 390 км/ч',
            'description': 'Применение п. 23 Правил перевозок пассажиров: повышение класса обслуживания без доплаты.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'passenger-missed-train': {
            'title': 'Пассажир отстал от поезда на 1-й минуте стоянки',
            'description': 'Комиссионная опись оставленного багажа по форме ЛУ-72 и отправка служебной телеграммы.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'business-class-conflict': {
            'title': 'Конфликт в бизнес-классе на 380 км/ч: Шумный разговор',
            'description': 'Деликатное замечание VIP-пассажиру, предложение тихой лаунж-зоны и сохранение комфорта вагона.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'sknb-overheating-alarm': {
            'title': 'Тревога СКНБ: Перегрев буксового узла на 400 км/ч',
            'description': 'Срочная связь с машинистом для плавного снижения скорости и предотвращения схода с рельсов.',
            'difficulty': 'Экстремальный',
            'difficulty_code': 'expert',
        },
        'chassis-ground-fault': {
            'title': 'Замыкание подвагонного оборудования на корпус (лампа «Земля»)',
            'description': 'Определение аварийной группы потребителей электрощита вагона при напряжении до 3000В.',
            'difficulty': 'Сложный',
            'difficulty_code': 'hard',
        },
        'vacuum-toilet-system-failure': {
            'title': 'Отказ вакуумной системы санузлов на скорости 400 км/ч',
            'description': 'Диагностика вакуумного компрессора, маршрутизация пассажиров в смежные вагоны и вызов ПЭМ.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'pantograph-icing-voltage-drop': {
            'title': 'Обледенение токоприемника и падение напряжения 27.5 кВ',
            'description': 'Действия экипажа при автоматическом переходе на аварийное аккумуляторное питание.',
            'difficulty': 'Сложный',
            'difficulty_code': 'hard',
        },
        'child-anaphylaxis-bistro': {
            'title': 'Анафилактический шок у ребенка в вагоне-бистро',
            'description': 'Неотложная доврачебная помощь при аллергическом отеке и вызов скорой помощи к станции.',
            'difficulty': 'Экстремальный',
            'difficulty_code': 'expert',
        },
        'cardiac-emergency': {
            'title': 'Остановка сердца: Реанимация на скорости 360 км/ч',
            'description': 'Немедленное применение автоматического наружного дефибриллятора (АНД) и сердечно-легочная реанимация.',
            'difficulty': 'Экстремальный',
            'difficulty_code': 'expert',
        },
        'lost-passport-migration-card': {
            'title': 'Утеря паспорта и миграционной карты пассажиром бизнес-класса',
            'description': 'Оформление временного посадочного талона и координация с транспортной полицией терминала.',
            'difficulty': 'Средний',
            'difficulty_code': 'medium',
        },
        'security-cab-door-intrusion': {
            'title': 'Попытка проникновения в кабину машиниста на 400 км/ч',
            'description': 'Блокировка бронедвери СКУД, вызов поездной охраны и предотвращение угрозы безопасности движения.',
            'difficulty': 'Экстремальный',
            'difficulty_code': 'expert',
        },
    }

    try:
        from .models import Scenario, EndlessChallenge
        db_scenarios = {sc.slug: sc for sc in Scenario.objects.filter(is_active=True)}
        db_challenges = {c.code: c for c in EndlessChallenge.objects.all()}
    except Exception:
        db_scenarios = {}
        db_challenges = {}

    unlocked_stations = []
    current_station = stations_data[0]
    furthest_unlocked_km = 0

    for s in stations_data:
        is_unlocked = conductor_level >= s['required_level']
        s['is_unlocked'] = is_unlocked
        if is_unlocked:
            unlocked_stations.append(s)
            current_station = s
            furthest_unlocked_km = s['km']

        # Формируем список сценариев сектора с полными русскими названиями
        detail_list = []
        for slug in s.get('scenarios_here', []):
            db_sc = db_scenarios.get(slug)
            meta = russian_scenario_meta.get(slug, {})
            title = db_sc.title if db_sc else meta.get('title', slug)
            desc = db_sc.description if db_sc else meta.get('description', f"Отработка действий экипажа на скорости до {s['speed_limit']}")
            diff = db_sc.get_difficulty_display() if db_sc else meta.get('difficulty', 'Средний')
            diff_code = db_sc.difficulty if db_sc else meta.get('difficulty_code', 'medium')
            speed = db_sc.train_speed if db_sc else (380 if s['km'] > 100 else 250)

            detail_list.append({
                'slug': slug,
                'title': title,
                'description': desc,
                'difficulty': diff,
                'difficulty_code': diff_code,
                'speed': speed,
            })
        s['scenarios_detail'] = detail_list

        # Формируем список экспресс-кейсов карусели для данного скоростного участка
        ch_list = []
        for ch_code in s.get('carousel_challenges_here', []):
            ch = db_challenges.get(ch_code)
            if ch:
                ch_list.append({
                    'id': ch.id,
                    'code': ch.code,
                    'title': ch.title,
                    'speed': ch.train_speed,
                    'difficulty_level': ch.difficulty_level,
                    'difficulty_display': ch.get_difficulty_level_display(),
                    'category': ch.get_category_display() if hasattr(ch, 'get_category_display') else getattr(ch, 'category', 'Сервис'),
                    'timer_seconds': ch.timer_seconds,
                    'situation_text': ch.situation_text,
                })
        s['carousel_challenges_detail'] = ch_list

    total_track_km = 679
    total_count = len(stations_data)
    unlocked_count = len(unlocked_stations)

    # Прогресс в процентах длины магистрали (км)
    progress_percentage = min(100, int((furthest_unlocked_km / total_track_km) * 100))

    # Доля рельсовой нити между центрами станций (0..1) для идеального попадания в круг станции
    if total_count > 1 and unlocked_count > 1:
        track_fraction = round((unlocked_count - 1) / (total_count - 1), 4)
    else:
        track_fraction = 0.0

    track_percentage = round(track_fraction * 100, 1)
    track_percentage_css = f"{track_fraction * 100:.2f}"
    station_percentage = min(100, int((unlocked_count / total_count) * 100))

    return {
        'stations': stations_data,
        'unlocked_count': unlocked_count,
        'total_count': total_count,
        'current_station': current_station,
        'furthest_km': furthest_unlocked_km,
        'total_km': total_track_km,
        'progress_percentage': progress_percentage,
        'track_fraction': track_fraction,
        'track_percentage': track_percentage,
        'track_percentage_css': track_percentage_css,
        'station_percentage': station_percentage,
    }


def dashboard(request):
    """Главный пульт управления обучением проводников ВСМ"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect('simulator:login')
    
    # Специализация обучения проводника (эконом / комфорт / бизнес / все)
    selected_track = request.GET.get('track') or conductor.training_track or 'all'
    if selected_track not in ['economy', 'comfort', 'business', 'all']:
        selected_track = 'all'

    # Сценарии
    all_scenarios = Scenario.objects.filter(is_active=True).order_by('order')
    if selected_track != 'all':
        scenarios = all_scenarios.filter(service_class__in=[selected_track, 'all'])
    else:
        scenarios = all_scenarios
    
    # Статистика сессий текущего проводника
    completed_sessions = TrainingSession.objects.filter(
        conductor=conductor,
        status='completed'
    ).select_related('scenario')
    
    completed_scenario_ids = set(completed_sessions.values_list('scenario_id', flat=True))
    
    # Топ-5 лидеров из базы данных
    top_conductors = ConductorProfile.objects.order_by('-experience_points')[:5]
    total_conductors = ConductorProfile.objects.count()
    user_rank = ConductorProfile.objects.filter(experience_points__gt=conductor.experience_points).count() + 1
    
    # Последние достижения
    latest_achievements = ConductorAchievement.objects.filter(
        profile=conductor
    ).select_related('achievement').order_by('-unlocked_at')[:4]
    
    # Компетенции
    competencies = ConductorCompetencyScore.objects.filter(
        profile=conductor
    ).select_related('competency')
    
    # Прогресс уровня
    progress = conductor.get_progress_to_next_level() if conductor else {}

    # Прогресс по специализациям обучения (эконом / комфорт / бизнес)
    track_progress = conductor.get_track_progress() if conductor else {}

    # Статистика бесконечной карусели решений
    endless_sessions = EndlessShiftSession.objects.filter(conductor=conductor)
    endless_best_streak = endless_sessions.order_by('-max_streak').values_list('max_streak', flat=True).first() or 0
    
    # Проверяем синхронизацию сценариев с каруселью решений
    if EndlessChallenge.objects.filter(source_type='scenario').count() == 0:
        sync_scenarios_and_challenges()

    endless_challenges_count = EndlessChallenge.objects.count()
    has_active_endless = endless_sessions.filter(status='active').exists()
    carousel_challenges = EndlessChallenge.objects.all().order_by('difficulty_level', 'id')
    if selected_track != 'all':
        carousel_challenges = carousel_challenges.filter(service_class__in=[selected_track, 'all'])

    # Интерактивно-игровой маршрут ВСМ-1
    route_progress = get_gamified_stations(conductor.level if conductor else 1)

    context = {
        'conductor': conductor,
        'scenarios': scenarios,
        'all_scenarios_count': all_scenarios.count(),
        'carousel_challenges': carousel_challenges,
        'completed_scenario_ids': completed_scenario_ids,
        'top_conductors': top_conductors,
        'total_conductors': total_conductors,
        'user_rank': user_rank,
        'latest_achievements': latest_achievements,
        'competencies': competencies,
        'progress': progress,
        'track_progress': track_progress,
        'selected_track': selected_track,
        'current_track': conductor.training_track,
        'training_tracks': ConductorProfile.TRAINING_TRACKS,
        'total_scenarios_count': scenarios.count(),
        'passed_count': len(completed_scenario_ids),
        'endless_best_streak': endless_best_streak,
        'endless_challenges_count': endless_challenges_count,
        'has_active_endless': has_active_endless,
        'route_progress': route_progress,
        'stations_json': json.dumps(route_progress['stations'], ensure_ascii=False),
    }
    return render(request, 'simulator/dashboard.html', context)


def scenario_list(request):
    """Каталог обучающих сценариев и экспресс-кейсов карусели с фильтрацией по категориям и классам обслуживания"""
    conductor = get_current_conductor(request)
    category = request.GET.get('category', 'all')
    difficulty = request.GET.get('difficulty', 'all')
    mode = request.GET.get('mode', 'all')  # all, scenarios, carousel
    service_class = request.GET.get('service_class') or request.GET.get('track', 'all')
    if service_class not in ['economy', 'comfort', 'business', 'all']:
        service_class = 'all'
    
    scenarios = Scenario.objects.filter(is_active=True)
    if category != 'all':
        scenarios = scenarios.filter(category=category)
    if difficulty != 'all':
        scenarios = scenarios.filter(difficulty=difficulty)
    if service_class != 'all':
        scenarios = scenarios.filter(service_class__in=[service_class, 'all'])
        
    scenarios = scenarios.order_by('order')

    # Экспресс-кейсы карусели
    carousel_challenges = EndlessChallenge.objects.all().order_by('difficulty_level', 'id')
    if category != 'all':
        carousel_challenges = carousel_challenges.filter(category=category)
    if service_class != 'all':
        carousel_challenges = carousel_challenges.filter(service_class__in=[service_class, 'all'])
    
    # Лучшие результаты пользователя
    completed_sessions = TrainingSession.objects.filter(
        conductor=conductor
    ).values('scenario_id', 'status', 'final_score', 'is_success')
    
    scenario_stats = {}
    for s in completed_sessions:
        sid = s['scenario_id']
        if sid not in scenario_stats or s['final_score'] > scenario_stats[sid].get('best_score', 0):
            scenario_stats[sid] = {
                'best_score': s['final_score'],
                'is_success': s['is_success'],
                'status': s['status']
            }
            
    total_count = Scenario.objects.filter(is_active=True).count()
    track_progress = conductor.get_track_progress() if conductor else {}

    context = {
        'conductor': conductor,
        'scenarios': scenarios,
        'carousel_challenges': carousel_challenges,
        'mode': mode,
        'category': category,
        'difficulty': difficulty,
        'service_class': service_class,
        'track_progress': track_progress,
        'current_track': conductor.training_track if conductor else 'all',
        'training_tracks': ConductorProfile.TRAINING_TRACKS,
        'scenario_stats': scenario_stats,
        'total_count': total_count,
    }
    return render(request, 'simulator/scenario_list.html', context)


def scenario_detail(request, slug):
    """Предрейсовый инструктаж перед запуском сценария"""
    conductor = get_current_conductor(request)
    scenario = get_object_or_404(Scenario, slug=slug, is_active=True)
    
    # История попыток по сценарию
    past_sessions = TrainingSession.objects.filter(
        conductor=conductor,
        scenario=scenario
    ).order_by('-started_at')[:5]
    
    context = {
        'conductor': conductor,
        'scenario': scenario,
        'past_sessions': past_sessions,
    }
    return render(request, 'simulator/scenario_detail.html', context)


def start_simulation(request, slug):
    """Инициализация новой сессии симулятора"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect(f"{reverse('simulator:login')}?next={reverse('simulator:scenario_detail', kwargs={'slug': slug})}")
        
    scenario = get_object_or_404(Scenario, slug=slug, is_active=True)
    
    start_node = scenario.nodes.filter(node_key='start').first()
    if not start_node:
        start_node = scenario.nodes.first()
        
    session = TrainingSession.objects.create(
        conductor=conductor,
        scenario=scenario,
        current_node=start_node,
        current_loyalty=75,
        current_safety=95,
        current_service=80,
        current_stress=20,
        status='in_progress',
        is_success=False,
        session_log=[
            {
                'timestamp': timezone.now().strftime('%H:%M:%S'),
                'time': timezone.now().strftime('%H:%M:%S'),
                'type': 'system',
                'node_title': 'Бортовой комплекс ВСМ-1: Начало рейса',
                'message': f'Поезд {scenario.train_number} следует на скорости {scenario.train_speed} км/ч. Начало смены.',
            }
        ]
    )
    return redirect('simulator:simulation_play', session_id=session.id)


def simulation_play(request, session_id):
    """Интерактивный экран симулятора и принятие решений в реальном времени"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect('simulator:login')
        
    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)
    
    if session.status != 'in_progress':
        return redirect('simulator:simulation_result', session_id=session.id)
        
    current_node = session.current_node
    choices = current_node.choices.all().order_by('order')
    
    context = {
        'conductor': conductor,
        'session': session,
        'scenario': session.scenario,
        'current_node': current_node,
        'choices': choices,
        'timer_seconds': current_node.time_limit_seconds,
    }
    return render(request, 'simulator/simulation_play.html', context)


def extract_trip_remarks(session, scenario=None, terminal_node=None, is_success=True, service_class=None):
    """
    Формирует список конкретных замечаний по рейсу ВСМ с дифференцированной
    строгостью оценки в зависимости от класса обслуживания (СТО ВСМ 03.011-2026).

    Классы обслуживания:
    - economy: мягкий аудит. Замечания выносятся только при грубых нарушениях безопасности (safety < 60)
               или критическом срыве диалога (loyalty < 45). Незначительные огрехи в этикете игнорируются.
    - comfort: сбалансированный аудит. Учитывает качество сервиса (service < 55), комфорт и альтернативы (loyalty < 55).
    - business: внимательный премиальный аудит. Учитывает персональный этикет и сервис, но без избыточного буквоедства.
    """
    if not service_class:
        if scenario and hasattr(scenario, 'service_class') and scenario.service_class and scenario.service_class != 'all':
            service_class = scenario.service_class
        elif hasattr(session, 'service_class') and session.service_class and session.service_class != 'all':
            service_class = session.service_class
        elif hasattr(session, 'conductor') and session.conductor and session.conductor.training_track != 'all':
            service_class = session.conductor.training_track
        else:
            service_class = 'economy'

    loyalty = getattr(session, 'current_loyalty', 80)
    safety = getattr(session, 'current_safety', 90)
    service = getattr(session, 'current_service', 85)
    stress = getattr(session, 'current_stress', 20)

    # Пороги строгости в зависимости от класса обслуживания (не строгие, лояльные к проводнику)
    if service_class == 'economy':
        loyalty_threshold = 45
        safety_threshold = 60
        service_threshold = 40
        stress_threshold = 85
    elif service_class == 'comfort':
        loyalty_threshold = 55
        safety_threshold = 68
        service_threshold = 55
        stress_threshold = 78
    else:  # 'business', 'first'
        loyalty_threshold = 65
        safety_threshold = 75
        service_threshold = 65
        stress_threshold = 72

    remarks = []

    # 1. Замечание по исходу рейса (если сценарий провален)
    if not is_success:
        remarks.append({
            'category': 'Безопасность движения',
            'severity': 'major',
            'title': 'Нештатное завершение инцидента на перегоне',
            'description': (
                terminal_node.resolution_report if terminal_node and terminal_node.resolution_report
                else 'Ситуация вышла из-под контроля экипажа, потребовалось вмешательство поездного диспетчера ВСМ.'
            ),
            'regulation_ref': scenario.regulation_reference if scenario and scenario.regulation_reference else 'ПТЭ Железных дорог РФ / СТО ВСМ 03.011-2026'
        })

    # 2. Замечания по безопасности движения
    if safety < safety_threshold:
        remarks.append({
            'category': 'Безопасность',
            'severity': 'moderate' if is_success else 'major',
            'title': 'Снижение индекса транспортной безопасности',
            'description': f'Индекс безопасности в ходе рейса опустился до {safety}%. Требуется более строгое соблюдение регламентов эксплуатации подвижного состава.',
            'regulation_ref': 'Инструкция по обеспечению безопасности пассажиров на ВСМ'
        })

    # 3. Замечания по работе с пассажирами (Лояльность)
    if loyalty < loyalty_threshold:
        if service_class == 'economy':
            desc = f'Индекс лояльности составил {loyalty}%. Зафиксировано повышенное раздражение пассажира, требующее более активного применения техник деэскалации.'
        elif service_class == 'comfort':
            desc = f'Индекс лояльности зафиксирован на уровне {loyalty}%. Пассажир высказал неудовлетворенность решением вопроса комфорта в салоне.'
        else:
            desc = f'Индекс лояльности составил {loyalty}%. В Бизнес-классе ожидается более предупредительное внимание к персоне пассажира.'

        remarks.append({
            'category': 'Коммуникация',
            'severity': 'minor' if service_class == 'economy' else 'moderate',
            'title': 'Недостаточная удовлетворенность пассажира',
            'description': desc,
            'regulation_ref': 'СТО ВСМ 03.011-2026 «Стандарты обслуживания пассажиров»'
        })

    # 4. Замечания по сервису
    if service < service_threshold:
        remarks.append({
            'category': 'Стандарты сервиса',
            'severity': 'minor',
            'title': 'Неполное выполнение сервисного протокола',
            'description': f'Уровень сервиса составил {service}%. Не были предложены предусмотренные стандартом альтернативные варианты помощи пассажиру.',
            'regulation_ref': 'СТО ВСМ 03.013-2026'
        })

    # 5. Проверка журналов на наличие таймаутов (промедление)
    try:
        from simulator.models import SimulationLog
        if hasattr(session, 'logs'):
            timeout_logs = session.logs.filter(conductor_input__icontains='таймаут').exists()
            if timeout_logs:
                remarks.append({
                    'category': 'Регламент времени',
                    'severity': 'minor',
                    'title': 'Задержка принятия решения экипажем',
                    'description': 'Зафиксировано истечение контрольного интервала времени на принятие решения на перегоне скоростного поезда.',
                    'regulation_ref': 'Регламент оперативного реагирования поездной бригады ВСМ'
                })
    except Exception:
        pass

    # 6. Стресс-менеджмент
    if stress > stress_threshold:
        remarks.append({
            'category': 'Стресс-контроль',
            'severity': 'minor',
            'title': 'Высокий уровень эмоциональной нагрузки',
            'description': f'Уровень стресса проводника достиг {stress}%. Рекомендуется использовать алгоритмы эмоциональной саморегуляции при сложных контактах.',
            'regulation_ref': 'Психологический регламент поездного экипажа ВСМ'
        })

    return remarks


def generate_scenario_debrief(session, scenario, terminal_node, is_success):
    """Формирует структурированный обучающий разбор полетов по 4-шаговой модели ВСМ с ведомостью замечаний"""
    loyalty = session.current_loyalty
    safety = session.current_safety
    service = session.current_service
    stress = session.current_stress

    service_class = getattr(scenario, 'service_class', None) or 'economy'
    if service_class == 'all' and hasattr(session, 'conductor') and session.conductor:
        service_class = session.conductor.training_track if session.conductor.training_track != 'all' else 'economy'

    # Пороги шагов с учетом класса (не строгие)
    loyalty_pass_limit = 45 if service_class == 'economy' else (55 if service_class == 'comfort' else 65)
    safety_pass_limit = 60 if service_class == 'economy' else (68 if service_class == 'comfort' else 75)

    step1_status = 'passed' if (is_success or loyalty >= loyalty_pass_limit) else 'failed'
    step1_comment = (
        'Эмпатическое признание проблемы и выслушивание пассажира выполнено корректно.'
        if step1_status == 'passed'
        else 'Не проявлена должная эмпатия, что спровоцировало рост раздражения пассажира.'
    )

    step2_status = 'passed' if (is_success or safety >= safety_pass_limit) else 'failed'
    step2_comment = (
        'Нормативные правила ВСМ (СТО ВСМ / ПТЭ) обозначены спокойно, аргументированно и без давления.'
        if step2_status == 'passed'
        else 'Нарушение норм безопасности или регламент донесен в категоричной/грубой форме.'
    )

    step3_status = 'passed' if is_success else 'failed'
    step3_comment = (
        'Предложено оптимальное регламентное решение проблемы (апгрейд, медпомощь, локализация).'
        if step3_status == 'passed'
        else 'Действие проводника усугубило ситуацию или повлекло угрозу безопасности движения.'
    )

    step4_status = 'passed' if (is_success and loyalty >= (loyalty_pass_limit + 10)) else ('warning' if is_success else 'failed')
    step4_comment = (
        'Пассажир заверен в безопасности, конфликт исчерпан, соблюден этикет.'
        if step4_status == 'passed'
        else ('Инцидент урегулирован, однако завершающий контакт оставил нейтральный или сдержанный осадок.' if is_success else 'Инцидент привел к жалобе или срыву графика движения.')
    )

    steps = [
        {
            'step': 1,
            'name': 'Признать ситуацию',
            'desc': 'Эмпатическое выслушивание и фиксация проблемы пассажира без встречной агрессии',
            'status': step1_status,
            'comment': step1_comment,
        },
        {
            'step': 2,
            'name': 'Обозначить правило',
            'desc': 'Спокойная ссылка на нормы безопасности и стандарты ВСМ без формализма',
            'status': step2_status,
            'comment': step2_comment,
        },
        {
            'step': 3,
            'name': 'Предложить решение',
            'desc': 'Предоставление конструктивной альтернативы по стандартам ВСМ',
            'status': step3_status,
            'comment': step3_comment,
        },
        {
            'step': 4,
            'name': 'Заверить',
            'desc': 'Создание уверенности в комфорте поездки и благодарность за понимание',
            'status': step4_status,
            'comment': step4_comment,
        },
    ]

    report_text = terminal_node.resolution_report if terminal_node and terminal_node.resolution_report else (
        'Сценарий успешно завершен по стандартам обслуживания ВСМ «Белый кречет».'
        if is_success
        else 'Допущены грубые отклонения от регламентов обслуживания и безопасности движения.'
    )

    recommendation = (
        'Закрепите навык в скоростной «Карусели решений» или перейдите к следующему участку маршрута.'
        if is_success
        else 'Изучите соответствующие разделы СТО ВСМ в Базе знаний и повторите кейс.'
    )

    remarks = extract_trip_remarks(session, scenario, terminal_node, is_success, service_class)

    return {
        'is_success': is_success,
        'summary': report_text,
        'regulation_ref': scenario.regulation_reference or 'СТО ВСМ 03.011-2026 / ПТЭ',
        'steps': steps,
        'remarks': remarks,
        'has_remarks': len(remarks) > 0,
        'service_class': service_class,
        'loyalty': loyalty,
        'safety': safety,
        'service': service,
        'stress': stress,
        'recommendation': recommendation,
    }


def process_simulation_decision(session, choice=None, is_timeout=False):
    """Единое ядро обработки сценарных выборов, расчета метрик и дебрифинга"""
    conductor = session.conductor
    scenario = session.scenario
    curr_node = session.current_node

    if is_timeout:
        penalty = getattr(curr_node, 'timeout_penalty', 15) or 15
        session.current_loyalty = max(0, session.current_loyalty - penalty)
        session.current_safety = max(0, session.current_safety - penalty)
        session.current_stress = min(100, session.current_stress + penalty)

        timeout_log = {
            'timestamp': timezone.now().strftime('%H:%M:%S'),
            'type': 'timeout',
            'action': 'Время на принятие решения истекло!',
            'node_title': curr_node.title if curr_node else '',
            'loyalty_impact': -penalty,
            'safety_impact': -penalty,
            'stress_impact': +penalty,
            'explanation': 'На высокой скорости промедление недопустимо.',
        }
        session.session_log.append(timeout_log)

        next_key = getattr(curr_node, 'timeout_next_node_key', '')
        if next_key:
            next_node = scenario.nodes.filter(node_key=next_key).first()
        else:
            next_node = None

        if not next_node:
            session.status = 'failed'
            session.is_success = False
            session.completed_at = timezone.now()
            session.final_score = max(0, int((session.current_loyalty + session.current_safety + session.current_service) / 3))
            debrief = generate_scenario_debrief(session, scenario, curr_node, False)
            session.debrief_feedback = debrief
            session.save()
            return JsonResponse({
                'is_terminal': True,
                'is_timeout': True,
                'is_success': False,
                'is_fail': True,
                'redirect_url': f'/simulation/{session.id}/result/',
                'toast': 'Время на принятие решения истекло! Промедление на скорости 400 км/ч недопустимо.',
                'audio': 'emergency',
                'debrief': debrief,
                'fail_info': {
                    'title': 'Время на принятие решения истекло',
                    'mistake_title': 'Критическое промедление',
                    'action_taken': 'Бездействие проводника / превышение лимита таймера',
                    'tactical_hint': 'Решения на ВСМ требуют оперативной реакции по регламенту.',
                    'dialogue_text': '«Ситуация вышла из-под контроля из-за задержки реакции.»',
                    'character_name': 'Система безопасности ВСМ',
                    'resolution_report': 'ПРОВАЛ: Непринятие решения в отведенный лимит времени создает прямую угрозу безопасности движения высокоскоростного состава.',
                    'mistake_analysis': 'Задержка с принятием мер на высокоскоростной магистрали недопустима.',
                    'recommended_approach': 'При возникновении нештатной ситуации немедленно активировать алгоритм регламента.',
                    'regulation_reference': scenario.regulation_reference or 'СТО ВСМ 03.011-2026',
                    'restart_url': f'/simulation/{scenario.slug}/start/',
                    'result_url': f'/simulation/{session.id}/result/',
                }
            })
    else:
        if not choice:
            return JsonResponse({'error': 'Не указан вариант выбора'}, status=400)

        session.current_loyalty = min(100, max(0, session.current_loyalty + choice.loyalty_impact))
        session.current_safety = min(100, max(0, session.current_safety + choice.safety_impact))
        session.current_service = min(100, max(0, session.current_service + choice.service_impact))
        session.current_stress = min(100, max(0, session.current_stress + choice.stress_impact))

        if choice.competency:
            comp_score_obj, _ = ConductorCompetencyScore.objects.get_or_create(
                profile=conductor,
                competency=choice.competency,
                defaults={'score': 50}
            )
            comp_score_obj.score = min(100, max(0, comp_score_obj.score + (choice.competency_points // 3)))
            comp_score_obj.save()

        log_entry = {
            'timestamp': timezone.now().strftime('%H:%M:%S'),
            'type': 'decision',
            'node_title': curr_node.title if curr_node else '',
            'action': choice.choice_text,
            'tactical_hint': choice.tactical_hint,
            'loyalty_impact': choice.loyalty_impact,
            'safety_impact': choice.safety_impact,
            'service_impact': choice.service_impact,
            'stress_impact': choice.stress_impact,
            'feedback_toast': choice.feedback_toast,
        }
        session.session_log.append(log_entry)
        next_node = scenario.nodes.filter(node_key=choice.next_node_key).first()

    if not next_node or next_node.is_terminal:
        is_success = next_node.is_success if next_node else (session.current_safety >= 70 and session.current_loyalty >= 60)
        session.status = 'completed' if is_success else 'failed'
        session.is_success = is_success
        session.completed_at = timezone.now()

        base_points = int((session.current_loyalty * 0.35) + (session.current_safety * 0.45) + (session.current_service * 0.20))
        stress_penalty = int(session.current_stress * 0.1)
        session.final_score = max(0, base_points - stress_penalty)

        earned_xp = scenario.base_xp if is_success else int(scenario.base_xp * 0.3)
        if session.current_safety >= 95 and session.current_loyalty >= 90:
            earned_xp += 100
        session.earned_xp = earned_xp
        conductor.add_xp(earned_xp)

        conductor.shifts_completed += 1
        if is_success and session.current_safety >= 95 and session.current_loyalty >= 90:
            conductor.perfect_shifts += 1

        conductor.loyalty_rating = round((conductor.loyalty_rating * 0.8) + (session.current_loyalty * 0.2), 1)
        conductor.safety_rating = round((conductor.safety_rating * 0.8) + (session.current_safety * 0.2), 1)
        conductor.service_rating = round((conductor.service_rating * 0.8) + (session.current_service * 0.2), 1)
        conductor.save()

        check_and_unlock_achievements(conductor, session, scenario)

        debrief = generate_scenario_debrief(session, scenario, next_node, is_success)
        session.debrief_feedback = debbrief if 'debbrief' in locals() else debrief
        session.current_node = next_node
        session.save()

        fail_info = None
        if not is_success:
            fail_info = {
                'title': next_node.title if next_node else 'Сценарий провален',
                'mistake_title': 'Неверно выбранное действие проводника',
                'action_taken': choice.choice_text if choice else 'Бездействие / таймаут',
                'tactical_hint': choice.tactical_hint if choice else '',
                'dialogue_text': next_node.dialogue_text if next_node else '',
                'character_name': next_node.character_name if next_node else '',
                'resolution_report': (next_node.resolution_report if next_node and next_node.resolution_report else 'Отклонение от регламентов обслуживания или безопасности.'),
                'mistake_analysis': next_node.resolution_report if next_node and next_node.resolution_report else 'Принятое решение привело к нарушению норм безопасности.',
                'recommended_approach': 'Строго следуйте стандартам ВСМ и алгоритмам действий в нештатных ситуациях.',
                'regulation_reference': scenario.regulation_reference or 'СТО ВСМ 03.011-2026',
                'restart_url': f'/simulation/{scenario.slug}/start/',
                'result_url': f'/simulation/{session.id}/result/',
            }

        return JsonResponse({
            'is_terminal': True,
            'is_success': is_success,
            'is_fail': not is_success,
            'redirect_url': f'/simulation/{session.id}/result/',
            'toast': (choice.feedback_toast if choice else '') or ('Сценарий успешно завершен!' if is_success else 'Сценарий провален.'),
            'audio': (choice.audio_cue if choice else 'emergency') if is_success else 'emergency',
            'debrief': debrief,
            'fail_info': fail_info,
        })

    session.current_node = next_node
    session.save()

    new_choices = []
    for c in next_node.choices.all().order_by('order'):
        new_choices.append({
            'id': c.id,
            'text': c.choice_text,
            'tactical_hint': c.tactical_hint,
            'audio': c.audio_cue,
        })

    return JsonResponse({
        'is_terminal': False,
        'node': {
            'title': next_node.title,
            'character_name': next_node.character_name,
            'character_role': next_node.character_role,
            'character_mood': next_node.get_character_mood_display(),
            'character_mood_code': next_node.character_mood,
            'dialogue_text': next_node.dialogue_text,
            'narrative_context': next_node.narrative_context,
            'time_limit_seconds': next_node.time_limit_seconds,
        },
        'choices': new_choices,
        'toast': choice.feedback_toast if choice else '',
        'audio': choice.audio_cue if choice else 'neutral',
        'current_loyalty': session.current_loyalty,
        'current_safety': session.current_safety,
        'current_service': session.current_service,
        'current_stress': session.current_stress,
    })


@require_POST
def api_choose_action(request, session_id):
    """API-обработчик выбора проводника с обновлением шкал и переходом к узлу"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)

    if session.status != 'in_progress':
        return JsonResponse({'error': 'Сессия уже завершена'}, status=400)

    try:
        data = json.loads(request.body)
        choice_id = data.get('choice_id')
        is_timeout = data.get('is_timeout', False)
    except Exception:
        return JsonResponse({'error': 'Некорректный запрос'}, status=400)

    choice = None
    if choice_id and not is_timeout:
        choice = get_object_or_404(ScenarioChoice, id=choice_id, node=session.current_node)

    return process_simulation_decision(session, choice=choice, is_timeout=is_timeout)


def check_and_unlock_achievements(conductor, session, scenario):
    """Проверка условий получения ачивок проводником"""
    # 1. Первый рейс
    if conductor.shifts_completed >= 1:
        ach = Achievement.objects.filter(code='first_shift').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    # 2. Мастер дипломатии (Бизнес-класс + лояльность >= 90%)
    if scenario.category == 'conflict' and session.is_success and session.current_loyalty >= 90:
        ach = Achievement.objects.filter(code='diplomat_master').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    # 3. Специалист неотложной помощи (Медицина + успех)
    if scenario.category == 'medical' and session.is_success:
        ach = Achievement.objects.filter(code='golden_hour_saver').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    # 4. Страж СПАС-ВО (Пожарная тревога + успех)
    if scenario.category == 'safety' and session.is_success:
        ach = Achievement.objects.filter(code='spas_sentinel').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    # 5. Антитеррористический щит
    if scenario.category == 'anti_terror' and session.is_success:
        ach = Achievement.objects.filter(code='anti_terror_shield').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    # 6. Безупречный сервис 400 км/ч
    if session.is_success and session.current_safety >= 100 and session.current_loyalty >= 95:
        ach = Achievement.objects.filter(code='perfect_service').first()
        if ach:
            ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)


def simulation_result(request, session_id):
    """Дебрифинг / Анализ 'Черного ящика' после завершения сессии"""
    conductor = get_current_conductor(request)
    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)
    scenario = session.scenario
    terminal_node = session.current_node

    if not session.debrief_feedback or 'remarks' not in session.debrief_feedback:
        session.debrief_feedback = generate_scenario_debrief(
            session, scenario, terminal_node, session.is_success
        )
        session.save(update_fields=['debrief_feedback'])

    competency_scores = ConductorCompetencyScore.objects.filter(
        profile=conductor
    ).select_related('competency')

    recent_achievements = ConductorAchievement.objects.filter(
        profile=conductor,
        unlocked_at__gte=session.started_at
    ).select_related('achievement')

    normalized_logs = []
    for item in (session.session_log or []):
        norm = dict(item)
        norm['timestamp'] = norm.get('timestamp') or norm.get('time') or timezone.now().strftime('%H:%M:%S')
        if not norm.get('node_title'):
            if norm.get('turn'):
                norm['node_title'] = f"Раунд {norm['turn']}"
            elif norm.get('type') == 'start':
                norm['node_title'] = "Начало смены в вагоне"
            elif norm.get('type') == 'system':
                norm['node_title'] = "Бортовая система поезда"
            else:
                norm['node_title'] = "Действие проводника"
        if not norm.get('conductor_input') and norm.get('action'):
            norm['conductor_input'] = norm.get('action')
        elif not norm.get('action') and norm.get('conductor_input'):
            norm['action'] = norm.get('conductor_input')
        if not norm.get('tactical_hint'):
            norm['tactical_hint'] = norm.get('feedback') or norm.get('explanation') or norm.get('feedback_toast') or ''
        deltas = norm.get('deltas') if isinstance(norm.get('deltas'), dict) else {}
        if 'loyalty_impact' not in norm or norm['loyalty_impact'] is None:
            norm['loyalty_impact'] = deltas.get('loyalty', 0)
        if 'safety_impact' not in norm or norm['safety_impact'] is None:
            norm['safety_impact'] = deltas.get('safety', 0)
        if 'stress_impact' not in norm or norm['stress_impact'] is None:
            norm['stress_impact'] = deltas.get('stress', 0)
        normalized_logs.append(norm)

    context = {
        'conductor': conductor,
        'session': session,
        'scenario': scenario,
        'terminal_node': terminal_node,
        'debrief': session.debrief_feedback,
        'competency_scores': competency_scores,
        'recent_achievements': recent_achievements,
        'log_items': normalized_logs,
    }
    return render(request, 'simulator/simulation_result.html', context)


def conductor_profile_view(request):
    """Личный профиль и карточка квалификации проводника ВСМ"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect('simulator:login')
    
    # Компетенции
    competency_scores = ConductorCompetencyScore.objects.filter(
        profile=conductor
    ).select_related('competency')
    
    # Все достижения с флагом разблокировки
    all_achievements = Achievement.objects.all()
    unlocked_ids = set(
        ConductorAchievement.objects.filter(profile=conductor).values_list('achievement_id', flat=True)
    )
    
    achievements_display = []
    for a in all_achievements:
        achievements_display.append({
            'achievement': a,
            'unlocked': a.id in unlocked_ids,
        })
        
    # История последних 10 рейсов
    history_sessions = TrainingSession.objects.filter(
        conductor=conductor
    ).select_related('scenario').order_by('-started_at')[:10]
    
    progress = conductor.get_progress_to_next_level()
    
    crew_members = conductor.crew_members.all()
    crew_ids = set(crew_members.values_list('id', flat=True))
    crew_ids.add(conductor.id)
    suggested_crew = ConductorProfile.objects.exclude(id__in=crew_ids).order_by('-experience_points')[:6]
    crew_synergy = conductor.get_crew_synergy()

    track_progress = conductor.get_track_progress()

    context = {
        'conductor': conductor,
        'competency_scores': competency_scores,
        'achievements_display': achievements_display,
        'history_sessions': history_sessions,
        'progress': progress,
        'crew_members': crew_members,
        'suggested_crew': suggested_crew,
        'crew_synergy': crew_synergy,
        'track_progress': track_progress,
        'training_tracks': ConductorProfile.TRAINING_TRACKS,
        'current_track': conductor.training_track,
    }
    return render(request, 'simulator/conductor_profile.html', context)


@require_POST
def api_crew_add(request, profile_id):
    """Добавление сотрудника в поездной экипаж (социальная сеть поездных бригад)"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    other = get_object_or_404(ConductorProfile, id=profile_id)
    if other.id == conductor.id:
        return JsonResponse({'error': 'Нельзя добавить самого себя'}, status=400)
    conductor.add_to_crew(other)
    return JsonResponse({
        'success': True,
        'message': f'{other.full_name} успешно включен в ваш поездной экипаж!',
        'crew_count': conductor.crew_members.count(),
        'synergy': conductor.get_crew_synergy(),
    })


@require_POST
def api_crew_remove(request, profile_id):
    """Исключение сотрудника из состава поездного экипажа"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    other = get_object_or_404(ConductorProfile, id=profile_id)
    conductor.remove_from_crew(other)
    return JsonResponse({
        'success': True,
        'message': f'{other.full_name} исключен из состава экипажа.',
        'crew_count': conductor.crew_members.count(),
        'synergy': conductor.get_crew_synergy(),
    })


@require_POST
def reset_account_data(request):
    """Сброс прогресса, уровней и статистики аккаунта проводника"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect('simulator:login')
    conductor.reset_progress()
    messages.success(request, "Квалификационный прогресс и история смен успешно сброшены. Вы можете начать обучение заново с 1 уровня.")
    return redirect('simulator:profile')


def leaderboard_view(request):
    """Таблица лидеров проводников ВСМ с рейтингами и депо"""
    current_conductor = get_current_conductor(request)
    depot_filter = request.GET.get('depot', 'all')
    account_type = request.GET.get('type', 'all')
    
    conductors_qs = ConductorProfile.objects.all()
    
    total_in_db = conductors_qs.count()
    example_count = conductors_qs.filter(is_example=True).count()
    registered_count = conductors_qs.filter(is_example=False).count()
    
    if depot_filter != 'all':
        conductors_qs = conductors_qs.filter(depot__icontains=depot_filter)
        
    if account_type == 'registered':
        conductors_qs = conductors_qs.filter(is_example=False)
    elif account_type == 'example':
        conductors_qs = conductors_qs.filter(is_example=True)
        
    conductors = conductors_qs.order_by('-experience_points')
    
    crew_ids = set()
    if current_conductor:
        crew_ids = set(current_conductor.crew_members.values_list('id', flat=True))

    conductors_data = []
    for c in conductors:
        conductors_data.append({
            'profile': c,
            'is_in_crew': c.id in crew_ids,
            'is_me': current_conductor and c.id == current_conductor.id,
        })

    # Уникальные депо для фильтра
    depots = [
        ('all', 'Все депо ВСМ'),
        ('Москва', 'Депо Москва-Октябрьская'),
        ('Санкт-Петербург', 'Депо Санкт-Петербург Главный'),
        ('Тверь', 'Депо Новая Тверь'),
        ('Валдай', 'Депо Валдай'),
        ('Новгород', 'Депо Великий Новгород'),
    ]
    
    context = {
        'conductor': current_conductor,
        'current_conductor': current_conductor,
        'conductors': conductors,
        'conductors_data': conductors_data,
        'depot_filter': depot_filter,
        'account_type': account_type,
        'depots': depots,
        'total_in_db': total_in_db,
        'example_count': example_count,
        'registered_count': registered_count,
    }
    return render(request, 'simulator/leaderboard.html', context)


def regulations_guide(request):
    """Интерактивный справочник регламентов и стандартов проводника ВСМ из базы данных"""
    conductor = get_current_conductor(request)
    db_docs = RegulationDocument.objects.filter(is_active=True).order_by('order')
    docs_dict = {}
    if db_docs.exists():
        for d in db_docs:
            docs_dict[d.key] = {
                'key': d.key,
                'title': d.title,
                'subtitle': d.subtitle,
                'badge': d.badge,
                'badge_color': d.badge_color,
                'format': 'PDF' if d.file_base64 else 'MD',
                'size': d.file_size_display,
                'description': d.description,
                'sections_count': len(d.chapters_data) if d.chapters_data else 1,
                'filename': d.file_name,
            }
    else:
        docs_dict = REGULATION_DOCUMENTS

    context = {
        'conductor': conductor,
        'documents_catalog': docs_dict,
        'cheat_sheets': CONDUCTOR_CHEAT_SHEETS,
    }
    return render(request, 'simulator/regulations_guide.html', context)


def download_document(request, doc_key):
    """Безопасная отдача файла нормативного документа из базы данных (PDF)"""
    db_doc = RegulationDocument.objects.filter(key=doc_key, is_active=True).first()
    if db_doc and db_doc.file_base64:
        raw_bytes = base64.b64decode(db_doc.file_base64)
        response = FileResponse(io.BytesIO(raw_bytes), as_attachment=True, filename=db_doc.file_name, content_type='application/pdf')
        return response
    elif db_doc:
        response = HttpResponse(db_doc.content_markdown, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{db_doc.key}_regulations.txt"'
        return response

    file_path = get_or_create_document_pdf(doc_key) or get_document_pdf_path(doc_key) or get_document_file_path(doc_key)
    if not file_path or not os.path.exists(file_path):
        doc_info = REGULATION_DOCUMENTS.get(doc_key)
        if doc_info:
            content = get_document_raw_content(doc_key)
            response = HttpResponse(content, content_type='text/plain; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{doc_key}_regulations.txt"'
            return response
        messages.warning(request, "Запрошенный документ не найден в каталоге.")
        return redirect('simulator:regulations')

    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    return response


def view_pdf_document(request, doc_key):
    """Полноценный внутрибраузерный просмотр PDF-документа из базы данных"""
    db_doc = RegulationDocument.objects.filter(key=doc_key, is_active=True).first()
    if db_doc and db_doc.file_base64:
        raw_bytes = base64.b64decode(db_doc.file_base64)
        response = FileResponse(io.BytesIO(raw_bytes), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{db_doc.file_name}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    elif db_doc:
        return HttpResponse(
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{db_doc.title}</title>"
            f"<style>body{{font-family:sans-serif;padding:24px;line-height:1.6;background:#0d1629;color:#e2e8f0;}}"
            f"h1{{color:#00d2ff;}}h2{{color:#38bdf8;}}p{{color:#cbd5e1;}}pre{{white-space:pre-wrap;}}</style></head>"
            f"<body><h1>{db_doc.title}</h1><pre>{db_doc.content_markdown}</pre></body></html>",
            content_type='text/html; charset=utf-8'
        )

    file_path = get_or_create_document_pdf(doc_key) or get_document_pdf_path(doc_key) or get_document_file_path(doc_key)
    if not file_path or not os.path.exists(file_path):
        doc_info = REGULATION_DOCUMENTS.get(doc_key)
        if doc_info:
            content = get_document_raw_content(doc_key)
            return HttpResponse(
                f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{doc_info['title']}</title>"
                f"<style>body{{font-family:sans-serif;padding:24px;line-height:1.6;background:#0d1629;color:#e2e8f0;}}"
                f"h1{{color:#00d2ff;}}h2{{color:#38bdf8;}}p{{color:#cbd5e1;}}</style></head>"
                f"<body><pre style='white-space:pre-wrap;'>{content}</pre></body></html>",
                content_type='text/html; charset=utf-8'
            )
        raise Http404("PDF-документ не найден")

    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response


def api_document_reader(request, doc_key):
    """API для интерактивной читалки документа в модальном окне браузера из БД"""
    db_doc = RegulationDocument.objects.filter(key=doc_key, is_active=True).first()
    if db_doc:
        pdf_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': doc_key})
        download_url = reverse('simulator:download_document', kwargs={'doc_key': doc_key})
        return JsonResponse({
            'success': True,
            'key': db_doc.key,
            'title': db_doc.title,
            'subtitle': db_doc.subtitle,
            'filename': db_doc.file_name,
            'size': db_doc.file_size_display,
            'format': 'PDF' if db_doc.file_base64 else 'MD',
            'description': db_doc.description,
            'chapters': db_doc.chapters_data or [],
            'content': db_doc.content_markdown,
            'has_pdf': bool(db_doc.file_base64),
            'pdf_url': pdf_url,
            'download_url': download_url,
        })

    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return JsonResponse({'error': 'Документ не найден'}, status=404)

    content = get_document_raw_content(doc_key)
    file_path = get_or_create_document_pdf(doc_key) or get_document_pdf_path(doc_key) or get_document_file_path(doc_key)
    has_pdf = bool(file_path and os.path.exists(file_path))

    pdf_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': doc_key})
    download_url = reverse('simulator:download_document', kwargs={'doc_key': doc_key})

    return JsonResponse({
        'success': True,
        'key': doc_key,
        'title': doc_info['title'],
        'subtitle': doc_info['subtitle'],
        'filename': doc_info.get('pdf_filename', doc_info['filename']),
        'size': doc_info['size'],
        'format': doc_info['format'],
        'description': doc_info['description'],
        'chapters': doc_info['chapters'],
        'content': content,
        'has_pdf': has_pdf,
        'pdf_url': pdf_url,
        'download_url': download_url,
    })


def switch_conductor_profile(request, profile_id):
    """Быстрое переключение профиля проводника для удобства тестирования и демонстрации"""
    target_profile = get_object_or_404(ConductorProfile, id=profile_id)
    login(request, target_profile.user)
    return redirect(request.META.get('HTTP_REFERER', 'simulator:dashboard'))


# =========================================================================
# РЕЖИМ «БЕСКОНЕЧНАЯ КАРУСЕЛЬ РЕШЕНИЙ» (ОТ ЛЕГКИХ К СЛОЖНЫМ: 250 -> 400 КМ/Ч)
# =========================================================================

def sync_scenarios_and_challenges():
    """
    Двусторонняя синхронизация:
    Импорт этапов сюжетных сценариев (ScenarioNode) в банк задач скоростной карусели (EndlessChallenge).
    Позволяет дилеммам из сценариев появляться в карусели решений со статусом source_type='scenario'.
    """
    from .models import Scenario, EndlessChallenge
    scenarios = Scenario.objects.prefetch_related('nodes__choices__competency').all()
    synced_count = 0
    diff_map = {
        'easy': 1,
        'medium': 2,
        'hard': 4,
        'expert': 5,
    }
    cat_comp_map = {
        'conflict': 'conflict_resolution',
        'medical': 'emergency_medical',
        'safety': 'safety_regulations',
        'anti_terror': 'safety_regulations',
        'tech_failure': 'vsm_tech_protocols',
        'vip_service': 'service_etiquette',
    }

    for sc in scenarios:
        for node in sc.nodes.filter(is_terminal=False):
            node_choices = list(node.choices.all())
            if not node_choices:
                continue

            # Определяем целевую сложность
            diff_level = diff_map.get(sc.difficulty, 2)
            if node.node_key != 'start':
                diff_level = min(5, diff_level + 1)

            choices_data = []
            has_correct = False

            for c in node_choices:
                # Проверяем корректность:
                target_node = sc.nodes.filter(node_key=c.next_node_key).first()
                if target_node and target_node.is_terminal:
                    is_corr = target_node.is_success
                else:
                    is_corr = (c.audio_cue == 'success') or (c.safety_impact >= 0 and c.loyalty_impact >= 0 and c.audio_cue != 'emergency')

                if is_corr:
                    has_correct = True

                choices_data.append({
                    'id': c.id,
                    'text': c.choice_text,
                    'hint': c.tactical_hint or ('Действие по регламенту ВСМ' if is_corr else 'Оцените последствия решения'),
                    'is_correct': is_corr,
                    'loyalty_delta': c.loyalty_impact,
                    'safety_delta': c.safety_impact,
                    'service_delta': c.service_impact,
                    'stress_delta': c.stress_impact,
                    'feedback': c.feedback_toast or ('Действие соответствует регламенту ВСМ.' if is_corr else 'Нарушение стандарта обслуживания ВСМ.'),
                })

            # Гарантируем наличие хотя бы одного правильного ответа
            if not has_correct and choices_data:
                best_choice = max(choices_data, key=lambda x: x['safety_delta'] + x['loyalty_delta'])
                best_choice['is_correct'] = True

            challenge_code = f"scnode_{sc.slug}_{node.node_key}"
            category = sc.category

            # Определение компетенции по выборам или категории
            comp_code = next((c.competency.code for c in node_choices if c.competency), None)
            if not comp_code:
                comp_code = cat_comp_map.get(sc.category, 'service_etiquette')

            EndlessChallenge.objects.update_or_create(
                code=challenge_code,
                defaults={
                    'title': f"{sc.title}: {node.title}",
                    'category': category,
                    'difficulty_level': diff_level,
                    'service_class': sc.service_class,
                    'train_speed': sc.train_speed,
                    'car_info': sc.car_info or 'Вагон ВСМ «Белый кречет»',
                    'character_name': node.character_name,
                    'character_role': node.character_role,
                    'character_mood': node.character_mood,
                    'situation_text': node.narrative_context or sc.description,
                    'dialogue_text': node.dialogue_text,
                    'timer_seconds': max(8, min(25, node.time_limit_seconds)),
                    'regulation_reference': sc.regulation_reference or 'Стандарты обслуживания ВСМ «Белый кречет»',
                    'competency_code': comp_code,
                    'choices_data': choices_data,
                    'source_type': 'scenario',
                    'source_scenario': sc,
                }
            )
            synced_count += 1

    return synced_count


def resolve_challenge_persona_and_avatar(name: str, role: str, title: str, text: str):
    """
    Интеллектуальное сопоставление бортового голоса и аватара персонажа:
    - Машинист / кабина / ДНЦ / ПЭМ -> machinist.svg, machinist voice
    - Пульт / щит / СКНБ / датчик / дефибриллятор -> system_monitor.svg, system telemetry voice
    - Дебошир / нетрезвый / буян -> passenger_brawler.svg, male voice
    - Маломобильный / коляска / МГН -> passenger_mobility.svg
    - Медицинский / приступ / больной -> passenger_sick.svg
    - Семья / ребенок / мама -> passenger_parent.svg
    - Пожилой / пенсионер -> passenger_elderly.svg
    - Молодой / студент -> passenger_young.svg
    - Женщина / пассажирка -> passenger_woman.svg, female voice
    - Бизнес / пассажир -> passenger_business.svg, male voice
    """
    n_lower = (name or '').lower()
    r_lower = (role or '').lower()
    t_lower = (title or '').lower()
    txt_lower = (text or '').lower()
    speaker_ctx = f"{n_lower} {r_lower}"
    combined_ctx = f"{n_lower} {r_lower} {t_lower} {txt_lower}"

    # 1. Машинист поезда, кабина, диспетчер, электромеханик ПЭМ (строгий высший приоритет)
    machinist_keywords = ['машинист', 'кабина', 'кабины', 'диспетчер', 'днц', 'электромеханик', 'пэм', 'рация', 'интерком']
    if any(k in speaker_ctx for k in machinist_keywords):
        return {
            'speaker_type': 'machinist',
            'voice_code': 'machinist-radio',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '+10%',
            'pitch': '-20Hz',
            'avatar_img': '/static/simulator/img/machinist.svg',
            'character_mood_default': 'Радиоэфир'
        }

    # 2. Приборы, системы, пульт, электрощит вагона, СКНБ, телеметрия (ТОЛЬКО если сам говорящий — прибор/система!)
    system_keywords = ['дефибриллятор', 'дефибр', 'пульт', 'электрощит', 'электрооборудован', 'скнб', 'система питания', 'датчик', 'телеметри', 'сигнализаци', 'автоинформатор']
    if any(k in speaker_ctx for k in system_keywords):
        return {
            'speaker_type': 'system',
            'voice_code': 'robot-telemetry',
            'actual_voice': 'ru-RU-SvetlanaNeural',
            'rate': '+12%',
            'pitch': '+10Hz',
            'avatar_img': '/static/simulator/img/system_monitor.svg',
            'character_mood_default': 'Телеметрия'
        }

    # 3. Дебоширы, нетрезвые пассажиры, буяны (СТРОГО мужской голос и brawler аватар)
    brawler_keywords = ['нетрезв', 'пьян', 'дебош', 'буян', 'молоток', 'хулиган', 'буйств', 'опьянен', 'нарушитель порядка']
    if any(k in combined_ctx for k in brawler_keywords) or any(k in txt_lower for k in ['налей мне', 'коньяку', 'окно разобью', 'разбивает бокал']):
        return {
            'speaker_type': 'male',
            'voice_code': 'ru-RU-DmitryNeural',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '-4%',
            'pitch': '-10Hz',
            'avatar_img': '/static/simulator/img/passenger_brawler.svg',
            'character_mood_default': 'Раздражен'
        }

    # 4. Маломобильные пассажиры
    if any(k in combined_ctx for k in ['маломобильн', 'колясочн', 'кресло-коляск', 'инвалид', 'мгн', 'подъемник']):
        return {
            'speaker_type': 'male',
            'voice_code': 'ru-RU-DmitryNeural',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '+0%',
            'pitch': '+0Hz',
            'avatar_img': '/static/simulator/img/passenger_mobility.svg',
            'character_mood_default': 'В диалоге'
        }

    # 5. Медицинские экстренные ситуации (сердце, приступ, астма)
    if any(k in combined_ctx for k in ['задых', 'астм', 'аллерг', 'отек', 'квинке', 'сердц', 'приступ', 'давлен', 'плохо', 'инфаркт', 'обморок', 'травм', 'больной', 'медицин']):
        return {
            'speaker_type': 'male',
            'voice_code': 'ru-RU-DmitryNeural',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '-2%',
            'pitch': '-5Hz',
            'avatar_img': '/static/simulator/img/passenger_sick.svg',
            'character_mood_default': 'Требуется помощь'
        }

    # 6. Родитель с ребенком
    if any(k in f"{n_lower} {r_lower} {t_lower}" for k in ['ребенок', 'ребёнк', 'дет', 'малыш', 'младен', 'мама']):
        return {
            'speaker_type': 'female',
            'voice_code': 'ru-RU-SvetlanaNeural',
            'actual_voice': 'ru-RU-SvetlanaNeural',
            'rate': '+0%',
            'pitch': '+0Hz',
            'avatar_img': '/static/simulator/img/passenger_parent.svg',
            'character_mood_default': 'В диалоге'
        }

    # 7. Пожилые пассажиры
    if any(k in f"{n_lower} {r_lower} {t_lower}" for k in ['пожил', 'пенсион', 'дедушк', 'бабушк', 'старик', 'ветеран', 'профессор']):
        return {
            'speaker_type': 'male',
            'voice_code': 'ru-RU-DmitryNeural',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '-5%',
            'pitch': '-15Hz',
            'avatar_img': '/static/simulator/img/passenger_elderly.svg',
            'character_mood_default': 'В диалоге'
        }

    # 8. Студенты / молодежь
    if any(k in f"{n_lower} {r_lower} {t_lower}" for k in ['молод', 'студент', 'парень', 'турист', 'блогер']):
        return {
            'speaker_type': 'male',
            'voice_code': 'ru-RU-DmitryNeural',
            'actual_voice': 'ru-RU-DmitryNeural',
            'rate': '+5%',
            'pitch': '+5Hz',
            'avatar_img': '/static/simulator/img/passenger_young.svg',
            'character_mood_default': 'В диалоге'
        }

    # 9. Женщины (строго по роли/имени или личным репликам)
    female_roles = ['пассажирка', 'женщин', 'девушк', 'мама', 'мать', 'бабушк', 'крылова', 'стюардесса', 'проводница']
    if any(k in speaker_ctx for k in female_roles) or re.search(r'\b(анна|елена|ольга|светлана|екатерина|мария|ирина|наталья)\b', speaker_ctx):
        return {
            'speaker_type': 'female',
            'voice_code': 'ru-RU-SvetlanaNeural',
            'actual_voice': 'ru-RU-SvetlanaNeural',
            'rate': '+0%',
            'pitch': '+0Hz',
            'avatar_img': '/static/simulator/img/passenger_woman.svg',
            'character_mood_default': 'В диалоге'
        }

    # 10. Деловой пассажир по умолчанию
    return {
        'speaker_type': 'male',
        'voice_code': 'ru-RU-DmitryNeural',
        'actual_voice': 'ru-RU-DmitryNeural',
        'rate': '+0%',
        'pitch': '+0Hz',
        'avatar_img': '/static/simulator/img/passenger_business.svg',
        'character_mood_default': 'В диалоге'
    }


def serialize_challenge(challenge, include_answer=False):
    """Сериализация задачи карусели для фронтенда с поддержкой сюжетных источников"""
    choices = []
    for idx, c in enumerate(challenge.choices_data):
        item = {
            'index': idx,
            'text': c.get('text', ''),
            'hint': c.get('hint', ''),
        }
        if include_answer:
            item['is_correct'] = c.get('is_correct', False)
            item['feedback'] = c.get('feedback', '')
            item['loyalty_delta'] = c.get('loyalty_delta', 0)
            item['safety_delta'] = c.get('safety_delta', 0)
            item['service_delta'] = c.get('service_delta', 0)
            item['stress_delta'] = c.get('stress_delta', 0)
        choices.append(item)

    source_type = getattr(challenge, 'source_type', 'carousel')
    source_scenario_title = challenge.source_scenario.title if getattr(challenge, 'source_scenario', None) else None
    source_scenario_slug = challenge.source_scenario.slug if getattr(challenge, 'source_scenario', None) else None

    persona = resolve_challenge_persona_and_avatar(
        challenge.character_name,
        challenge.character_role,
        challenge.title,
        challenge.dialogue_text or challenge.situation_text
    )

    return {
        'id': challenge.id,
        'code': challenge.code,
        'title': challenge.title,
        'category': challenge.category,
        'difficulty_level': challenge.difficulty_level,
        'difficulty_display': challenge.get_difficulty_level_display(),
        'service_class': getattr(challenge, 'service_class', 'all'),
        'service_class_display': challenge.get_service_class_display(),
        'service_class_badge': challenge.get_service_class_badge(),
        'train_speed': challenge.train_speed,
        'car_info': challenge.car_info,
        'character_name': challenge.character_name,
        'character_role': challenge.character_role,
        'character_mood': challenge.character_mood,
        'situation_text': challenge.situation_text,
        'dialogue_text': challenge.dialogue_text,
        'timer_seconds': challenge.timer_seconds,
        'regulation_reference': challenge.regulation_reference,
        'competency_code': challenge.competency_code,
        'choices': choices,
        'source_type': source_type,
        'source_scenario_title': source_scenario_title,
        'source_scenario_slug': source_scenario_slug,
        'speaker_type': persona['speaker_type'],
        'voice_code': persona['voice_code'],
        'actual_voice': persona['actual_voice'],
        'rate': persona['rate'],
        'pitch': persona['pitch'],
        'avatar_img': persona['avatar_img'],
        'character_mood_default': persona['character_mood_default'],
    }


def get_next_challenge_for_session(session, current_challenge_id=None):
    """
    Интеллектуальный подбор следующей задачи по шкале прогрессии сложности и классу вагона:
    - Синхронизирует уровень проводника (1..10) с прогрессом смены (0..8 задач).
    - Учитывает класс вагона смены (Эконом / Комфорт / Бизнес / Общепоездной).
    - К прибытию в Санкт-Петербург сложность возрастает до 4-5 уровня.
    - Исключает зацикливание на одной и той же задаче.
    """
    conductor_level = session.conductor.level if session.conductor else 1
    base_diff = min(3, max(1, (conductor_level + 1) // 3))
    stage_boost = (session.challenges_solved + session.mistakes_count) // 2
    target_diff = min(5, max(1, base_diff + stage_boost))

    # Фильтр по классу вагона смены
    session_class = getattr(session, 'service_class', 'all')
    base_qs = EndlessChallenge.objects.all()
    if session_class and session_class != 'all':
        class_pool = base_qs.filter(service_class__in=[session_class, 'all'])
        if class_pool.exists():
            base_qs = class_pool

    # Список исключений: уже пройденные задачи + текущая задача
    exclude_ids = set(session.solved_challenge_ids or [])
    if current_challenge_id:
        exclude_ids.add(current_challenge_id)

    # 1. Ищем нерешенные задачи целевого уровня
    unsolved_qs = base_qs.filter(
        difficulty_level=target_diff
    ).exclude(id__in=exclude_ids)

    if unsolved_qs.exists():
        return random.choice(list(unsolved_qs))

    # 2. Если в целевом уровне закончились, ищем любые нерешенные задачи с ближайшей сложностью
    all_unsolved = base_qs.exclude(id__in=exclude_ids)
    if all_unsolved.exists():
        candidates = list(all_unsolved)
        min_gap = min(abs(c.difficulty_level - target_diff) for c in candidates)
        best_candidates = [c for c in candidates if abs(c.difficulty_level - target_diff) == min_gap]
        return random.choice(best_candidates)

    # 3. Если абсолютно все задачи пула пройдены — очищаем список, но сохраняем текущую задачу в исключениях
    session.solved_challenge_ids = [current_challenge_id] if current_challenge_id else []
    session.save(update_fields=['solved_challenge_ids'])
    
    fallback_qs = base_qs
    if current_challenge_id:
        fallback_qs = fallback_qs.exclude(id=current_challenge_id)
        if not fallback_qs.exists():
            fallback_qs = base_qs

    target_fallback = fallback_qs.filter(difficulty_level=target_diff)
    if target_fallback.exists():
        return random.choice(list(target_fallback))

    hard_qs = fallback_qs.filter(difficulty_level__gte=4)
    if hard_qs.exists():
        return random.choice(list(hard_qs))
    return fallback_qs.order_by('?').first() or EndlessChallenge.objects.order_by('?').first()


def endless_carousel_view(request):
    """Главный экран бесконечной карусели скоростных решений (250 -> 400 км/ч)"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect(f"{reverse('simulator:login')}?next={reverse('simulator:endless_carousel')}")
    
    # Автоматическая двусторонняя синхронизация задач, если еще не выполнена
    if EndlessChallenge.objects.filter(source_type='scenario').count() == 0:
        sync_scenarios_and_challenges()

    # Личный рекорд текущего проводника в бесконечном режиме
    conductor_sessions = EndlessShiftSession.objects.filter(conductor=conductor)
    best_streak = conductor_sessions.order_by('-max_streak').values_list('max_streak', flat=True).first() or 0
    max_solved = conductor_sessions.order_by('-challenges_solved').values_list('challenges_solved', flat=True).first() or 0
    max_score = conductor_sessions.order_by('-total_score').values_list('total_score', flat=True).first() or 0
    
    # Топ-5 лидеров бесконечного режима среди всех депо
    top_sessions = EndlessShiftSession.objects.select_related('conductor').order_by('-total_score', '-max_streak')[:5]
    
    # Проверка наличия активной сессии
    active_session = conductor_sessions.filter(status='active').first()
    
    # Список уровней сложности для инфо-панели
    difficulty_tiers = [
        {
            'level': 1,
            'title': 'Штатный сервис и посадка',
            'speed': '250 км/ч',
            'timer': '25 сек',
            'desc': 'Проверка билетов, опечатки в паспорте, сервис премиум-класса, провоз ручной клади.',
            'color': '#10b981',
        },
        {
            'level': 2,
            'title': 'Напряженный трафик и багаж',
            'speed': '300 км/ч',
            'timer': '20 сек',
            'desc': 'Опоздавшие пассажиры, забытый багаж, телеграммы на станции, шумные соседи.',
            'color': '#00d2ff',
        },
        {
            'level': 3,
            'title': 'Овербукинг и конфликтология',
            'speed': '350 км/ч',
            'timer': '16 сек',
            'desc': 'Двойные билеты, апгрейд в Бизнес-класс по п. 23 Правил, отказ от пересадки, деэскалация.',
            'color': '#eab308',
        },
        {
            'level': 4,
            'title': 'Высокий стресс и медицина',
            'speed': '380 км/ч',
            'timer': '12 сек',
            'desc': 'Сердечный приступ пассажира, вызов АНД, дебошир в вагоне-бистро, взаимодействие с ЛНП.',
            'color': '#f97316',
        },
        {
            'level': 5,
            'title': 'Критический экстрим ВСМ',
            'speed': '400 км/ч',
            'timer': '9 сек',
            'desc': 'Тревога СКНБ (нагрев букс) на мосту, задымление СПАС-ВО, запрет срыва стоп-крана на 400 км/ч.',
            'color': '#fd033a',
        },
    ]

    total_challenges_count = EndlessChallenge.objects.count()

    context = {
        'conductor': conductor,
        'active_session': active_session,
        'best_streak': best_streak,
        'max_solved': max_solved,
        'max_score': max_score,
        'top_sessions': top_sessions,
        'difficulty_tiers': difficulty_tiers,
        'total_challenges_count': total_challenges_count,
        'conductor_track': conductor.training_track,
        'track_progress': conductor.get_track_progress(),
        'service_classes': EndlessShiftSession.SERVICE_CLASSES,
    }
    return render(request, 'simulator/endless_carousel.html', context)


@csrf_exempt
@require_POST
def api_start_endless_session(request):
    """Старт новой высокоскоростной смены в режиме «Карусель решений» с поддержкой классов обслуживания"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    
    # Синхронизируем сценарии и карусель, если банк задач еще не расширен
    if EndlessChallenge.objects.filter(source_type='scenario').count() == 0:
        sync_scenarios_and_challenges()

    # Закрываем предыдущие активные сессии, если они были брошены
    EndlessShiftSession.objects.filter(conductor=conductor, status='active').update(
        status='failed',
        completed_at=timezone.now()
    )

    # Параметры из запроса (challenge_id или выбранный service_class)
    requested_challenge_id = None
    service_class_input = 'all'
    try:
        if request.body:
            body_data = json.loads(request.body)
            requested_challenge_id = body_data.get('challenge_id')
            service_class_input = body_data.get('service_class') or conductor.training_track or 'all'
    except Exception:
        pass

    if service_class_input not in ['economy', 'comfort', 'business', 'all']:
        service_class_input = conductor.training_track or 'all'
    if service_class_input not in ['economy', 'comfort', 'business', 'all']:
        service_class_input = 'all'

    # Скорость поезда синхронизирована с уровнем проводника
    initial_speed = min(340, 240 + (conductor.level * 15))
    
    # Номер новой смены
    shift_number = conductor.shifts_completed + 1

    session = EndlessShiftSession.objects.create(
        conductor=conductor,
        service_class=service_class_input,
        shift_number=shift_number,
        target_challenges_count=8,
        mistakes_count=0,
        is_perfect=True,
        current_streak=0,
        max_streak=0,
        challenges_solved=0,
        total_score=0,
        earned_xp=0,
        current_speed=initial_speed,
        current_loyalty=85,
        current_safety=95,
        current_service=85,
        current_stress=15,
        status='active',
        solved_challenge_ids=[],
        history_log=[
            {
                'timestamp': timezone.now().strftime('%H:%M:%S'),
                'type': 'system',
                'message': f'Вы заступили на скоростную смену №{shift_number} (Уровень {conductor.level}, {conductor.get_rank_display()}). Поезд «Белый кречет» следует по маршруту Москва — Санкт-Петербург.',
            }
        ]
    )

    first_challenge = None
    if requested_challenge_id:
        first_challenge = EndlessChallenge.objects.filter(id=requested_challenge_id).first()
        if first_challenge:
            session.current_speed = min(400, max(240, first_challenge.train_speed))
            session.save(update_fields=['current_speed'])

    if not first_challenge:
        first_challenge = get_next_challenge_for_session(session)

    if not first_challenge:
        return JsonResponse({'error': 'Банк задач пуст. Запустите seed_vsm_data.'}, status=400)

    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'shift_number': session.shift_number,
        'target_challenges_count': session.target_challenges_count,
        'challenges_solved': session.challenges_solved,
        'mistakes_count': session.mistakes_count,
        'is_perfect': session.is_perfect,
        'conductor_level': conductor.level,
        'conductor_rank': conductor.get_rank_display(),
        'shifts_completed': conductor.shifts_completed,
        'perfect_shifts': conductor.perfect_shifts,
        'current_speed': session.current_speed,
        'current_streak': session.current_streak,
        'max_streak': session.max_streak,
        'total_score': session.total_score,
        'earned_xp': session.earned_xp,
        'current_loyalty': session.current_loyalty,
        'current_safety': session.current_safety,
        'current_service': session.current_service,
        'current_stress': session.current_stress,
        'multiplier': 1.0,
        'challenge': serialize_challenge(first_challenge, include_answer=False),
    })


@csrf_exempt
@require_POST
def api_endless_choose(request, session_id):
    """
    Принятие скоростного решения в карусели:
    - Проверка правильности
    - Расчет стрика и множителя
    - Динамический разгон скорости поезда
    - Мгновенное начисление XP и синхронизация уровня проводника
    - Отслеживание ошибок и статуса безупречности смены
    - При завершении плана (8 задач) — подведение итогов рейса (безупречная / с замечаниями)
    """
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    session = get_object_or_404(EndlessShiftSession, id=session_id, conductor=conductor)

    if session.status != 'active':
        return JsonResponse({'error': 'Смена уже завершена', 'is_terminal': True}, status=400)

    try:
        data = json.loads(request.body)
        challenge_id = data.get('challenge_id')
        choice_index = data.get('choice_index')
        is_timeout = data.get('is_timeout', False)
        message = (data.get('message') or '').strip()
        action = (data.get('action') or '').strip()
        action_title = (data.get('action_title') or '').strip()
        history = data.get('history') or []
    except Exception:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    challenge = get_object_or_404(EndlessChallenge, id=challenge_id)

    # 1. Обработка таймаута
    if is_timeout:
        session.mistakes_count += 1
        session.is_perfect = False
        session.current_streak = 0
        session.current_loyalty = max(0, session.current_loyalty - 20)
        session.current_safety = max(0, session.current_safety - 25)
        session.current_service = max(0, session.current_service - 15)
        session.current_stress = min(100, session.current_stress + 30)
        session.current_speed = max(200, session.current_speed - 25)

        # Обязательно фиксируем задачу в списке пройденных, предотвращая зацикливание
        if challenge.id not in session.solved_challenge_ids:
            session.solved_challenge_ids.append(challenge.id)

        timeout_msg = f'Время на принятие решения истекло! На скорости {session.current_speed} км/ч промедление недопустимо.'
        log_item = {
            'timestamp': timezone.now().strftime('%H:%M:%S'),
            'challenge_id': challenge.id,
            'type': 'timeout',
            'challenge_title': challenge.title,
            'difficulty': challenge.difficulty_level,
            'is_correct': False,
            'message': timeout_msg,
            'regulation': challenge.regulation_reference,
            'loyalty_delta': -20,
            'safety_delta': -25,
            'service_delta': -15,
            'stress_delta': +30,
        }
        session.history_log.append(log_item)

        correct_choice = next((c for c in challenge.choices_data if c.get('is_correct')), None)

        # Проверка критического схода с линии
        if session.current_safety <= 20 or session.current_loyalty <= 20 or session.current_stress >= 95:
            session.status = 'failed'
            session.completed_at = timezone.now()
            session.save()
            endless_remarks = extract_trip_remarks(session, is_success=False, service_class=session.service_class)
            return JsonResponse({
                'is_terminal': True,
                'is_shift_completed': False,
                'is_success': False,
                'reason': 'Критическое падение безопасности рейса или предел стресса проводника. Смена сорвана.',
                'audio': 'emergency',
                'challenge_title': challenge.title,
                'selected_choice_text': 'Таймер истек: решение не принято вовремя',
                'why_wrong': f'На скорости {session.current_speed} км/ч каждая секунда задержки ставит под угрозу безопасность сотен пассажиров и график ВСМ.',
                'explanation': f'На скорости {session.current_speed} км/ч время на принятие решения ограничено нормативом.',
                'regulation': challenge.regulation_reference or 'Регламент действий бригады ВСМ в экстренных ситуациях',
                'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
                'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
                'remarks': endless_remarks,
                'has_remarks': len(endless_remarks) > 0,
                'stats': {
                    'current_loyalty': session.current_loyalty,
                    'current_safety': session.current_safety,
                    'current_service': session.current_service,
                    'current_stress': session.current_stress,
                    'current_speed': session.current_speed,
                    'current_streak': 0,
                    'max_streak': session.max_streak,
                    'challenges_solved': session.challenges_solved,
                    'target_challenges_count': session.target_challenges_count,
                    'mistakes_count': session.mistakes_count,
                    'shift_number': session.shift_number,
                    'is_perfect': False,
                    'total_score': session.total_score,
                    'earned_xp': session.earned_xp,
                    'conductor_level': conductor.level,
                    'shifts_completed': conductor.shifts_completed,
                    'perfect_shifts': conductor.perfect_shifts,
                    'remarks': endless_remarks,
                    'has_remarks': len(endless_remarks) > 0,
                }
            })

        # Проверка завершения маршрута (8 станций) при таймауте
        total_attempts = session.challenges_solved + session.mistakes_count
        if total_attempts >= session.target_challenges_count:
            session.status = 'completed'
            session.completed_at = timezone.now()
            conductor.shifts_completed += 1
            session.save()
            conductor.save()
            endless_remarks = extract_trip_remarks(session, is_success=True, service_class=session.service_class)
            summary_data = {
                'shift_number': session.shift_number,
                'next_shift_number': conductor.shifts_completed + 1,
                'is_perfect': False,
                'mistakes_count': session.mistakes_count,
                'challenges_solved': session.challenges_solved,
                'target_challenges_count': session.target_challenges_count,
                'max_streak': session.max_streak,
                'total_score': session.total_score,
                'earned_xp': session.earned_xp,
                'current_loyalty': session.current_loyalty,
                'current_safety': session.current_safety,
                'current_service': session.current_service,
                'current_stress': session.current_stress,
                'final_speed': session.current_speed,
                'new_total_xp': conductor.experience_points,
                'conductor_level': conductor.level,
                'shifts_completed': conductor.shifts_completed,
                'perfect_shifts': conductor.perfect_shifts,
                'remarks': endless_remarks,
                'has_remarks': len(endless_remarks) > 0,
            }
            return JsonResponse({
                'is_terminal': True,
                'is_shift_completed': True,
                'is_perfect': False,
                'is_correct': False,
                'is_timeout': True,
                'mistakes_count': session.mistakes_count,
                'shift_number': session.shift_number,
                'next_shift_number': conductor.shifts_completed + 1,
                'audio': 'warning',
                'toast': 'Смена сдана с замечаниями в Санкт-Петербурге.',
                'challenge_title': challenge.title,
                'selected_choice_text': 'Таймер истек: решение не принято вовремя',
                'why_wrong': f'На скорости {session.current_speed} км/ч промедление недопустимо! Задержка создает угрозу пассажирам и движению поезда.',
                'explanation': f'На скорости {session.current_speed} км/ч регламенты требуют оперативной реакции.',
                'regulation': challenge.regulation_reference or 'Регламент действий бригады ВСМ (п. 4)',
                'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
                'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
                'summary': summary_data,
                'stats': summary_data,
            })

        session.save()
        next_challenge = get_next_challenge_for_session(session, current_challenge_id=challenge.id)
        return JsonResponse({
            'is_terminal': False,
            'is_resolved': True,
            'status': 'failed',
            'is_correct': False,
            'is_timeout': True,
            'audio': 'emergency',
            'toast': 'Время вышло! Ошибка занесена в отчет смены. Скорость снижена.',
            'challenge_title': challenge.title,
            'selected_choice_text': 'Таймер истек: решение не принято вовремя',
            'why_wrong': f'На скорости {session.current_speed} км/ч промедление недопустимо! Задержка создает угрозу пассажирам и движению поезда.',
            'explanation': f'На высокоскоростной магистрали регламенты требуют оперативной реакции.',
            'regulation': challenge.regulation_reference or 'Регламент действий бригады ВСМ (п. 4)',
            'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
            'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
            'deltas': {
                'loyalty': -20,
                'safety': -25,
                'service': -15,
                'stress': +30,
                'speed': -25,
            },
            'stats': {
                'current_loyalty': session.current_loyalty,
                'current_safety': session.current_safety,
                'current_service': session.current_service,
                'current_stress': session.current_stress,
                'current_speed': session.current_speed,
                'current_streak': session.current_streak,
                'max_streak': session.max_streak,
                'challenges_solved': session.challenges_solved,
                'target_challenges_count': session.target_challenges_count,
                'mistakes_count': session.mistakes_count,
                'shift_number': session.shift_number,
                'is_perfect': False,
                'total_score': session.total_score,
                'earned_xp': session.earned_xp,
                'multiplier': 1.0,
                'conductor_level': conductor.level,
                'shifts_completed': conductor.shifts_completed,
                'perfect_shifts': conductor.perfect_shifts,
            },
            'next_challenge': serialize_challenge(next_challenge, include_answer=False),
        })

    # 2. Обработка решения проводника (кнопка, речь ASR, свободный ввод или инвентарь)
    choices_data = challenge.choices_data
    character_reply = ""
    character_mood = "formal"
    feedback_text = ""
    why_wrong_text = ""
    status = "resolved"
    eval_res = {}

    if choice_index is not None and (0 <= choice_index < len(choices_data)):
        selected_choice = choices_data[choice_index]
        c_text = selected_choice.get('text', '')
        # Оцениваем через evaluate_endless_turn для живой генеративной реакции ИИ
        eval_res = SberAIService.evaluate_endless_turn(
            session=session,
            challenge=challenge,
            conductor_message=c_text,
            dialogue_history=history,
            conductor=conductor
        )
        is_correct = selected_choice.get('is_correct', False)
        status = 'resolved' if is_correct else 'failed'
        character_reply = eval_res.get('character_reply', '') or ("Спасибо за оперативное содействие!" if is_correct else "Это противоречит регламенту!")
        character_mood = eval_res.get('character_mood', 'grateful' if is_correct else 'irritated')
        feedback_text = selected_choice.get('hint', '') or selected_choice.get('feedback', '') or eval_res.get('feedback', '')
        why_wrong_text = selected_choice.get('why_wrong', '') or eval_res.get('why_wrong', '')
        loyalty_delta = selected_choice.get('loyalty_delta', 15 if is_correct else -15)
        safety_delta = selected_choice.get('safety_delta', 10 if is_correct else -10)
        service_delta = selected_choice.get('service_delta', 15 if is_correct else -10)
        stress_delta = selected_choice.get('stress_delta', -10 if is_correct else 15)
    elif message or action:
        eval_res = SberAIService.evaluate_endless_turn(
            session=session,
            challenge=challenge,
            conductor_message=message,
            conductor_action=action,
            dialogue_history=history,
            conductor=conductor
        )
        is_correct = eval_res.get('is_correct', False)
        status = eval_res.get('status', 'resolved' if is_correct else 'failed')
        character_reply = eval_res.get('character_reply', '')
        character_mood = eval_res.get('character_mood', 'formal')
        why_wrong_text = eval_res.get('why_wrong', '')
        feedback_text = eval_res.get('feedback', '')
        loyalty_delta = eval_res.get('loyalty_delta', 15 if is_correct else -15)
        safety_delta = eval_res.get('safety_delta', 10 if is_correct else -10)
        service_delta = eval_res.get('service_delta', 15 if is_correct else -10)
        stress_delta = eval_res.get('stress_delta', -10 if is_correct else 15)

        action_titles = {
            'emergency_brake': 'Срыв стоп-крана',
            'fire_extinguisher': 'Применение огнетушителя ОВП-8',
            'electric_panel': 'Осмотр электрощита и СКНБ',
            'aed_medkit': 'Вскрытие аптечки и АНД',
            'ukeb_scan': 'Проверка по терминалу УКЭБ',
            'tea_service': 'Предложить чай / воду с лимоном',
            'driver_intercom': 'Связь с машинистом по УПС',
            'glass_hammer': 'Взять аварийный молоток'
        }
        disp_action = action_title or action_titles.get(action, action)
        act_title = f"[{disp_action}] " if disp_action else ""
        selected_choice = {
            'text': f"{act_title}{message}".strip() or (f"Действие: [{disp_action}]" if disp_action else "Применение спецсредства"),
            'is_correct': is_correct,
            'loyalty_delta': loyalty_delta,
            'safety_delta': safety_delta,
            'service_delta': service_delta,
            'stress_delta': stress_delta,
            'hint': feedback_text,
            'why_wrong': why_wrong_text
        }
    else:
        return JsonResponse({'error': 'Некорректный запрос: укажите choice_index, message или action'}, status=400)

    # 2.1. Если диалог продолжается (status == 'in_progress'): НЕ завершаем задачу, не переключаем станцию!
    if status == 'in_progress':
        session.current_loyalty = max(0, min(100, session.current_loyalty + loyalty_delta))
        session.current_safety = max(0, min(100, session.current_safety + safety_delta))
        session.current_service = max(0, min(100, session.current_service + service_delta))
        session.current_stress = max(0, min(100, session.current_stress + stress_delta))

        session.history_log.append({
            'timestamp': timezone.now().strftime('%H:%M:%S'),
            'challenge_id': challenge.id,
            'challenge_title': challenge.title,
            'type': 'turn',
            'conductor_turn': message or action or (selected_choice.get('text') if choice_index is not None else ''),
            'character_reply': character_reply,
            'status': 'in_progress',
            'deltas': {
                'loyalty': loyalty_delta,
                'safety': safety_delta,
                'service': service_delta,
                'stress': stress_delta,
            }
        })

        if session.current_safety <= 20 or session.current_loyalty <= 20 or session.current_stress >= 95:
            session.status = 'failed'
            session.completed_at = timezone.now()
            session.save()
            endless_remarks = extract_trip_remarks(session, is_success=False, service_class=session.service_class)
            return JsonResponse({
                'is_terminal': True,
                'is_resolved': False,
                'is_shift_completed': False,
                'is_success': False,
                'reason': 'Критическое падение параметров рейса! Пассажиры или безопасность пострадали.',
                'audio': 'emergency',
                'challenge_title': challenge.title,
                'selected_choice_text': message or action or (selected_choice.get('text') if choice_index is not None else ''),
                'why_wrong': why_wrong_text or 'Нарушение норм безопасности ВСМ.',
                'remarks': endless_remarks,
                'has_remarks': len(endless_remarks) > 0,
                'stats': {
                    'current_loyalty': session.current_loyalty,
                    'current_safety': session.current_safety,
                    'current_service': session.current_service,
                    'current_stress': session.current_stress,
                    'current_speed': session.current_speed,
                    'current_streak': 0,
                    'max_streak': session.max_streak,
                    'challenges_solved': session.challenges_solved,
                    'target_challenges_count': session.target_challenges_count,
                    'mistakes_count': session.mistakes_count,
                    'shift_number': session.shift_number,
                    'is_perfect': False,
                    'total_score': session.total_score,
                    'earned_xp': session.earned_xp,
                    'conductor_level': conductor.level,
                    'shifts_completed': conductor.shifts_completed,
                    'perfect_shifts': conductor.perfect_shifts,
                    'remarks': endless_remarks,
                    'has_remarks': len(endless_remarks) > 0,
                }
            })

        session.save()

        show_hints = eval_res.get('show_hints', False)
        suggested = eval_res.get('suggested_actions', []) if show_hints else []
        if show_hints and not suggested and choices_data:
            suggested = [{'text': c.get('text', ''), 'hint': c.get('hint', '')} for c in choices_data[:3]]

        persona = resolve_challenge_persona_and_avatar(
            challenge.character_name,
            challenge.character_role,
            challenge.title,
            character_reply or challenge.dialogue_text or challenge.situation_text
        )

        return JsonResponse({
            'is_terminal': False,
            'is_resolved': False,
            'status': 'in_progress',
            'character_reply': character_reply,
            'character_mood': character_mood,
            'system_notice': eval_res.get('system_notice', ''),
            'speaker_type': persona['speaker_type'],
            'voice_code': persona['voice_code'],
            'actual_voice': persona['actual_voice'],
            'rate': persona['rate'],
            'pitch': persona['pitch'],
            'feedback': feedback_text,
            'why_wrong': why_wrong_text,
            'show_hints': show_hints,
            'hint_reason': eval_res.get('hint_reason', ''),
            'suggested_actions': suggested,
            'deltas': {
                'loyalty': loyalty_delta,
                'safety': safety_delta,
                'service': service_delta,
                'stress': stress_delta,
            },
            'stats': {
                'current_loyalty': session.current_loyalty,
                'current_safety': session.current_safety,
                'current_service': session.current_service,
                'current_stress': session.current_stress,
                'current_speed': session.current_speed,
                'current_streak': session.current_streak,
                'max_streak': session.max_streak,
                'challenges_solved': session.challenges_solved,
                'target_challenges_count': session.target_challenges_count,
                'mistakes_count': session.mistakes_count,
                'shift_number': session.shift_number,
                'is_perfect': session.is_perfect,
                'total_score': session.total_score,
                'earned_xp': session.earned_xp,
                'multiplier': 1.0,
                'conductor_level': conductor.level,
                'shifts_completed': conductor.shifts_completed,
                'perfect_shifts': conductor.perfect_shifts,
            },
            'challenge_id': challenge.id,
        })

    # Применение дельт
    session.current_loyalty = max(0, min(100, session.current_loyalty + loyalty_delta))
    session.current_safety = max(0, min(100, session.current_safety + safety_delta))
    session.current_service = max(0, min(100, session.current_service + service_delta))
    session.current_stress = max(0, min(100, session.current_stress + stress_delta))

    # Расчет стрика и множителя
    if is_correct:
        session.current_streak += 1
        if session.current_streak > session.max_streak:
            session.max_streak = session.current_streak

        session.challenges_solved += 1

        # Множитель стрика
        multiplier = session.multiplier

        base_points = 100 * challenge.difficulty_level
        added_score = int(base_points * multiplier)
        session.total_score += added_score
        xp_gain = int(added_score * 0.4)
        session.earned_xp += xp_gain

        # Мгновенная синхронизация опыта и уровня проводника!
        conductor.add_xp(xp_gain)

        # Динамический разгон скорости поезда
        target_speed = min(400, 240 + (challenge.difficulty_level * 28) + min(30, session.current_streak * 3))
        session.current_speed = target_speed

        audio_cue = 'success'
        toast_msg = f'Регламент соблюден! +{added_score} очков (Стрик x{multiplier})'

        # Начисление компетенции
        if challenge.competency_code:
            comp = Competency.objects.filter(code=challenge.competency_code).first()
            if comp:
                cs, _ = ConductorCompetencyScore.objects.get_or_create(profile=conductor, competency=comp)
                cs.score = min(100, cs.score + 2)
                cs.save()

        # Проверка ачивки на стрик 10
        if session.current_streak >= 10:
            ach = Achievement.objects.filter(code='carousel_streak_10').first()
            if ach:
                ConductorAchievement.objects.get_or_create(profile=conductor, achievement=ach)

    else:
        # Ошибка
        session.mistakes_count += 1
        session.is_perfect = False
        session.current_streak = 0
        multiplier = 1.0
        session.current_speed = max(200, session.current_speed - 25)
        audio_cue = 'warning'
        toast_msg = 'Ошибка! Нарушение регламента ВСМ. Замечание внесено в журнал смены.'

    # Запоминаем решенную задачу
    if challenge.id not in session.solved_challenge_ids:
        session.solved_challenge_ids.append(challenge.id)

    # Логирование
    session.history_log.append({
        'timestamp': timezone.now().strftime('%H:%M:%S'),
        'challenge_id': challenge.id,
        'challenge_title': challenge.title,
        'difficulty': challenge.difficulty_level,
        'is_correct': is_correct,
        'choice_text': selected_choice.get('text', ''),
        'feedback': selected_choice.get('feedback', ''),
        'regulation': challenge.regulation_reference,
        'loyalty_delta': loyalty_delta,
        'safety_delta': safety_delta,
        'service_delta': service_delta,
        'stress_delta': stress_delta,
    })

    correct_choice = next((c for c in choices_data if c.get('is_correct')), None)

    # 3. Проверка критического схода со смены (критический срыв параметров)
    if session.current_safety <= 20 or session.current_loyalty <= 20 or session.current_stress >= 95:
        session.status = 'failed'
        session.completed_at = timezone.now()
        session.save()
        fail_reason = 'Критическое падение параметров безопасности или лояльности пассажиров. Смена сорвана инцидентом!'
        return JsonResponse({
            'is_terminal': True,
            'is_shift_completed': False,
            'is_success': False,
            'reason': fail_reason,
            'audio': 'emergency',
            'challenge_title': challenge.title,
            'selected_choice_text': selected_choice.get('text', ''),
            'why_wrong': why_wrong_text or 'Накопленные нарушения регламентов привели к критическому срыву рейса.',
            'explanation': selected_choice.get('feedback', '') or fail_reason,
            'regulation': challenge.regulation_reference or 'ПТЭ железных дорог РФ и Стандарты ВСМ',
            'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
            'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
            'stats': {
                'current_loyalty': session.current_loyalty,
                'current_safety': session.current_safety,
                'current_service': session.current_service,
                'current_stress': session.current_stress,
                'current_speed': session.current_speed,
                'current_streak': 0,
                'max_streak': session.max_streak,
                'challenges_solved': session.challenges_solved,
                'target_challenges_count': session.target_challenges_count,
                'mistakes_count': session.mistakes_count,
                'shift_number': session.shift_number,
                'is_perfect': False,
                'total_score': session.total_score,
                'earned_xp': session.earned_xp,
                'multiplier': 1.0,
                'conductor_level': conductor.level,
                'shifts_completed': conductor.shifts_completed,
                'perfect_shifts': conductor.perfect_shifts,
            }
        })

    # 4. Проверка успешного завершения полного маршрута смены (все 8 станций пройдены)
    total_progress = session.challenges_solved + session.mistakes_count
    if total_progress >= session.target_challenges_count:
        session.status = 'completed'
        session.completed_at = timezone.now()
        conductor.shifts_completed += 1

        is_flawless = (session.mistakes_count == 0 and session.current_safety >= 80 and session.current_loyalty >= 75)
        if is_flawless:
            session.is_perfect = True
            conductor.perfect_shifts += 1
            conductor.add_xp(250)  # Премиальный бонус за безупречную смену
        else:
            session.is_perfect = False

        session.save()
        conductor.save()

        summary_data = {
            'shift_number': session.shift_number,
            'next_shift_number': conductor.shifts_completed + 1,
            'is_perfect': session.is_perfect,
            'mistakes_count': session.mistakes_count,
            'challenges_solved': session.challenges_solved,
            'target_challenges_count': session.target_challenges_count,
            'current_streak': session.current_streak,
            'max_streak': session.max_streak,
            'multiplier': session.multiplier,
            'total_score': session.total_score,
            'earned_xp': session.earned_xp,
            'current_loyalty': session.current_loyalty,
            'current_safety': session.current_safety,
            'current_service': session.current_service,
            'current_stress': session.current_stress,
            'final_speed': session.current_speed,
            'new_total_xp': conductor.experience_points,
            'conductor_level': conductor.level,
            'shifts_completed': conductor.shifts_completed,
            'perfect_shifts': conductor.perfect_shifts,
            'remarks': extract_trip_remarks(session, is_success=True, service_class=session.service_class),
            'has_remarks': len(extract_trip_remarks(session, is_success=True, service_class=session.service_class)) > 0,
        }

        return JsonResponse({
            'success': True,
            'is_terminal': True,
            'is_shift_completed': True,
            'is_perfect': session.is_perfect,
            'mistakes_count': session.mistakes_count,
            'shift_number': session.shift_number,
            'next_shift_number': conductor.shifts_completed + 1,
            'is_correct': is_correct,
            'audio': 'success',
            'toast': 'Безупречная смена сдана в Санкт-Петербурге!' if session.is_perfect else 'Смена сдана с замечаниями в Санкт-Петербурге.',
            'feedback': selected_choice.get('feedback', ''),
            'regulation': challenge.regulation_reference or 'Стандарты обслуживания «Белый кречет»',
            'challenge_title': challenge.title,
            'selected_choice_text': selected_choice.get('text', ''),
            'why_wrong': selected_choice.get('feedback', '') or 'Выбранное действие противоречит правилам и стандарту ВСМ.',
            'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
            'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
            'deltas': {
                'loyalty': loyalty_delta,
                'safety': safety_delta,
                'service': service_delta,
                'stress': stress_delta,
            },
            'stats': summary_data,
            'summary': summary_data,
        })


    session.save()
    next_challenge = get_next_challenge_for_session(session, current_challenge_id=challenge.id)

    persona = resolve_challenge_persona_and_avatar(
        challenge.character_name,
        challenge.character_role,
        challenge.title,
        character_reply or challenge.dialogue_text or challenge.situation_text
    )

    return JsonResponse({
        'success': True,
        'is_terminal': False,
        'is_resolved': True,
        'status': 'resolved' if is_correct else 'failed',
        'is_correct': is_correct,
        'audio': audio_cue,
        'toast': toast_msg,
        'character_reply': character_reply,
        'character_mood': character_mood,
        'system_notice': eval_res.get('system_notice', ''),
        'speaker_type': persona['speaker_type'],
        'voice_code': persona['voice_code'],
        'actual_voice': persona['actual_voice'],
        'rate': persona['rate'],
        'pitch': persona['pitch'],
        'feedback': feedback_text or selected_choice.get('hint', ''),
        'regulation': challenge.regulation_reference or 'Стандарты обслуживания «Белый кречет»',
        'challenge_title': challenge.title,
        'selected_choice_text': selected_choice.get('text', ''),
        'why_wrong': why_wrong_text or selected_choice.get('why_wrong', '') or 'Выбранное действие противоречит правилам и стандарту ВСМ.',
        'correct_choice_text': correct_choice.get('text', '') if correct_choice else '',
        'correct_hint': correct_choice.get('hint', '') if correct_choice else '',
        'deltas': {
            'loyalty': loyalty_delta,
            'safety': safety_delta,
            'service': service_delta,
            'stress': stress_delta,
        },
        'stats': {
            'current_loyalty': session.current_loyalty,
            'current_safety': session.current_safety,
            'current_service': session.current_service,
            'current_stress': session.current_stress,
            'current_speed': session.current_speed,
            'current_streak': session.current_streak,
            'max_streak': session.max_streak,
            'challenges_solved': session.challenges_solved,
            'target_challenges_count': session.target_challenges_count,
            'mistakes_count': session.mistakes_count,
            'shift_number': session.shift_number,
            'is_perfect': session.is_perfect,
            'total_score': session.total_score,
            'earned_xp': session.earned_xp,
            'multiplier': multiplier if is_correct else 1.0,
            'conductor_level': conductor.level,
            'shifts_completed': conductor.shifts_completed,
            'perfect_shifts': conductor.perfect_shifts,
        },
        'next_challenge': serialize_challenge(next_challenge, include_answer=False),
    })


@csrf_exempt
@require_POST
def api_endless_finish(request, session_id):
    """Штатное завершение смены проводником («Сдать вагон и получить расчет»): сохранение опыта и прогресса"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    session = get_object_or_404(EndlessShiftSession, id=session_id, conductor=conductor)

    if session.status != 'active':
        return JsonResponse({'error': 'Смена уже закрыта'}, status=400)

    session.status = 'completed'
    session.completed_at = timezone.now()
    conductor.shifts_completed += 1

    # Определение безупречности смены
    is_flawless = (session.challenges_solved >= session.target_challenges_count and session.mistakes_count == 0 and session.current_safety >= 80 and session.current_loyalty >= 75)
    if is_flawless:
        session.is_perfect = True
        conductor.perfect_shifts += 1
        conductor.add_xp(250)
    else:
        session.is_perfect = False

    session.save()
    conductor.save()

    summary_data = {
        'shift_number': session.shift_number,
        'next_shift_number': conductor.shifts_completed + 1,
        'is_perfect': session.is_perfect,
        'mistakes_count': session.mistakes_count,
        'challenges_solved': session.challenges_solved,
        'target_challenges_count': session.target_challenges_count,
        'current_streak': session.current_streak,
        'max_streak': session.max_streak,
        'multiplier': session.multiplier,
        'total_score': session.total_score,
        'earned_xp': session.earned_xp,
        'current_loyalty': session.current_loyalty,
        'current_safety': session.current_safety,
        'current_service': session.current_service,
        'current_stress': session.current_stress,
        'final_speed': session.current_speed,
        'new_total_xp': conductor.experience_points,
        'conductor_level': conductor.level,
        'shifts_completed': conductor.shifts_completed,
        'perfect_shifts': conductor.perfect_shifts,
        'remarks': extract_trip_remarks(session, is_success=True, service_class=session.service_class),
        'has_remarks': len(extract_trip_remarks(session, is_success=True, service_class=session.service_class)) > 0,
    }

    return JsonResponse({
        'success': True,
        'is_shift_completed': True,
        'is_perfect': session.is_perfect,
        'mistakes_count': session.mistakes_count,
        'shift_number': session.shift_number,
        'next_shift_number': conductor.shifts_completed + 1,
        'summary': summary_data,
    })


def api_endless_state(request, session_id):
    """Получение текущего состояния активной сессии карусели при перезагрузке страницы"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)
    session = get_object_or_404(EndlessShiftSession, id=session_id, conductor=conductor)

    # Определяем текущую задачу
    next_challenge = get_next_challenge_for_session(session)

    mult = session.multiplier

    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'status': session.status,
        'shift_number': session.shift_number,
        'target_challenges_count': session.target_challenges_count,
        'challenges_solved': session.challenges_solved,
        'mistakes_count': session.mistakes_count,
        'is_perfect': session.is_perfect,
        'conductor_level': conductor.level,
        'conductor_rank': conductor.get_rank_display(),
        'shifts_completed': conductor.shifts_completed,
        'perfect_shifts': conductor.perfect_shifts,
        'current_speed': session.current_speed,
        'current_streak': session.current_streak,
        'max_streak': session.max_streak,
        'total_score': session.total_score,
        'earned_xp': session.earned_xp,
        'current_loyalty': session.current_loyalty,
        'current_safety': session.current_safety,
        'current_service': session.current_service,
        'current_stress': session.current_stress,
        'multiplier': mult,
        'challenge': serialize_challenge(next_challenge, include_answer=False) if next_challenge else None,
    })


def favicon_ico(request):
    """Отдача favicon.ico для браузеров"""
    favicon_path = os.path.join(settings.BASE_DIR, 'simulator', 'static', 'simulator', 'img', 'favicon.ico')
    if os.path.exists(favicon_path):
        with open(favicon_path, 'rb') as f:
            resp = HttpResponse(f.read(), content_type='image/x-icon')
            resp['Cache-Control'] = 'no-cache, must-revalidate'
            return resp
    return HttpResponse(status=404)


def robots_txt(request):
    """Генерация поискового robots.txt с указанием карты сайта и правил индексации"""
    sitemap_url = request.build_absolute_uri('/sitemap.xml')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /scenarios/\n"
        "Allow: /scenario/\n"
        "Allow: /endless/\n"
        "Allow: /regulations/\n"
        "Allow: /leaderboard/\n"
        "Allow: /analytics/\n"
        "Allow: /api/docs/\n"
        "Allow: /static/\n"
        "Disallow: /admin/\n"
        "Disallow: /api/v1/\n"
        "Disallow: /simulation/\n"
        "Disallow: /switch-profile/\n\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    """Генерация XML-карты сайта sitemap.xml по стандарту sitemaps.org"""
    base_url = request.build_absolute_uri('/').rstrip('/')
    now_str = timezone.now().strftime('%Y-%m-%d')

    # Статические разделы платформы
    static_pages = [
        {'path': '', 'priority': '1.0', 'changefreq': 'daily'},
        {'path': '/scenarios/', 'priority': '0.9', 'changefreq': 'daily'},
        {'path': '/endless/', 'priority': '0.9', 'changefreq': 'daily'},
        {'path': '/regulations/', 'priority': '0.9', 'changefreq': 'weekly'},
        {'path': '/leaderboard/', 'priority': '0.8', 'changefreq': 'daily'},
        {'path': '/analytics/', 'priority': '0.85', 'changefreq': 'daily'},
        {'path': '/profile/', 'priority': '0.7', 'changefreq': 'weekly'},
        {'path': '/api/docs/', 'priority': '0.7', 'changefreq': 'monthly'},
    ]

    # Динамические сценарии ВСМ
    scenarios = Scenario.objects.filter(is_active=True).values('slug')

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for page in static_pages:
        loc = f"{base_url}{page['path']}"
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{loc}</loc>')
        xml_lines.append(f'    <lastmod>{now_str}</lastmod>')
        xml_lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{page["priority"]}</priority>')
        xml_lines.append('  </url>')

    for sc in scenarios:
        loc = f"{base_url}/scenario/{sc['slug']}/"
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{loc}</loc>')
        xml_lines.append(f'    <lastmod>{now_str}</lastmod>')
        xml_lines.append('    <changefreq>weekly</changefreq>')
        xml_lines.append('    <priority>0.8</priority>')
        xml_lines.append('  </url>')

    xml_lines.append('</urlset>')
    xml_content = "\n".join(xml_lines)
    return HttpResponse(xml_content, content_type="application/xml; charset=utf-8")


def manifest_json(request):
    """PWA манифест веб-приложения для установки на мобильные устройства и ПК"""
    manifest_data = {
        "name": "ВСМ-1 «Белый кречет» | Тренажер проводника",
        "short_name": "ВСМ Тренажер",
        "description": "Интерактивный геймифицированный обучающий комплекс для поездных бригад ВСМ-1 Москва — Санкт-Петербург (до 400 км/ч).",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#070c18",
        "theme_color": "#082a99",
        "orientation": "any",
        "lang": "ru-RU",
        "categories": ["education", "games", "productivity"],
        "icons": [
            {
                "src": "/static/simulator/img/vsm_logo.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            },
            {
                "src": "/static/simulator/img/train_krechet.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            }
        ],
        "shortcuts": [
            {
                "name": "Главный пульт",
                "url": "/",
                "description": "Оперативная сводка и карта станций"
            },
            {
                "name": "Карусель решений",
                "url": "/endless/",
                "description": "Бесконечная смена на скорости до 400 км/ч"
            },
            {
                "name": "База знаний и ПТЭ",
                "url": "/regulations/",
                "description": "Регламенты, стандарты и читалка документов"
            }
        ]
    }
    return JsonResponse(manifest_data, json_dumps_params={'ensure_ascii': False, 'indent': 2}, content_type="application/manifest+json; charset=utf-8")


def service_worker_js(request):
    """
    PWA Service Worker: кэширование статических ресурсов, автономная работа и мгновенный отклик.
    Маршрутизируется на /sw.js в корне домена для полного контроля scope '/'.
    """
    sw_code = """// ВСМ-1 «Белый кречет» — PWA Service Worker v1.2
const CACHE_NAME = 'vsm-krechet-v1.2';
const PRECACHE_ASSETS = [
    '/',
    '/static/simulator/css/vsm_style.css',
    '/static/simulator/js/vsm_audio.js',
    '/static/simulator/js/vsm_simulator.js',
    '/static/simulator/img/vsm_logo.svg',
    '/static/simulator/img/train_krechet.png',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRECACHE_ASSETS).catch((err) => {
                console.warn('[VSM SW] Precache warning:', err);
            });
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    // Динамические API запросы, админку и потоковые данные не кэшируем через Service Worker
    if (url.pathname.startsWith('/api/') || 
        url.pathname.startsWith('/admin/') || 
        url.pathname.startsWith('/auth/') ||
        url.pathname.startsWith('/simulation/') ||
        url.pathname.startsWith('/endless/') ||
        url.pathname.includes('/tts/')) {
        return;
    }

    event.respondWith(
        fetch(request)
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200 && request.url.startsWith(self.location.origin)) {
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseToCache);
                    });
                }
                return networkResponse;
            })
            .catch(() => caches.match(request))
    );
});
"""
    response = HttpResponse(sw_code, content_type="application/javascript; charset=utf-8")
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def humans_txt(request):
    """Технические сведения о проекте и команде (humans.txt)"""
    content = (
        "/* TEAM */\n"
        "Project: ВСМ-1 «Белый кречет» — Интерактивный симулятор проводника\n"
        "Platform: Высокоскоростная железнодорожная магистраль Москва — Санкт-Петербург (ВСМ-1)\n"
        "Author: Maxim\n"
        "Role: Lead Developer & Sound Producer\n\n"
        "/* SPECIFICATION & STANDARDS */\n"
        "Высокоскоростной подвижной состав «Белый кречет»\n"
        "Отраслевые регламенты обслуживания на скоростях до 400 км/ч\n\n"
        "/* SITE & TECH STACK */\n"
        "Backend: Python 3.12+, Django 6+\n"
        "Frontend: HTML5, Modern CSS (Grid/Flexbox/Container Queries/Dynamic Viewport Units), Vanilla JavaScript ES6+\n"
        "Audio: Web Audio API (Процедурный синтез скорости и свиста рассекаемого воздуха до 400 км/ч)\n"
        "Design System: VS-Brand Dark Neon Navy, White Krechet Red/Cyan accents\n"
        "Standards: W3C Valid, PWA Standalone, Open Graph, Twitter Cards, Sitemap XML, Robots TXT\n"
        "Speed Profile: 250 - 400 km/h\n"
        "Language: Russian (ru-RU)\n"
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def register_view(request):
    """Регистрация нового проводника в единой базе ВСМ"""
    if request.user.is_authenticated and hasattr(request.user, 'conductor_profile'):
        return redirect('simulator:dashboard')

    example_conductors = ConductorProfile.objects.filter(is_example=True).order_by('-experience_points')

    if request.method == 'POST':
        form = ConductorRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            full_name = form.cleaned_data['full_name'].strip()
            email = form.cleaned_data['email'].strip()
            depot = form.cleaned_data['depot']
            avatar = form.cleaned_data['avatar']
            password = form.cleaned_data['password']

            sber_client_id = form.cleaned_data.get('sber_client_id', '').strip()
            sber_client_secret = form.cleaned_data.get('sber_client_secret', '').strip()
            sber_auth_key = form.cleaned_data.get('sber_auth_key', '').strip()

            # Генерация уникального табельного номера
            badge_number = f"VSM-{random.randint(1000, 9999)}"
            while ConductorProfile.objects.filter(badge_number=badge_number).exists():
                badge_number = f"VSM-{random.randint(1000, 9999)}"

            names = full_name.split(maxsplit=1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            profile = ConductorProfile.objects.create(
                user=user,
                full_name=full_name,
                badge_number=badge_number,
                depot=depot,
                avatar=avatar,
                sber_client_id=sber_client_id,
                sber_client_secret=sber_client_secret,
                sber_auth_key=sber_auth_key,
                rank='trainee',
                level=1,
                experience_points=100,
                loyalty_rating=85.0,
                safety_rating=95.0,
                service_rating=85.0,
                shifts_completed=0,
                perfect_shifts=0,
                is_example=False,
            )

            if sber_auth_key:
                test_res = SberAIService.test_conductor_auth_key(sber_auth_key)
                if test_res.get('ok'):
                    profile.sber_access_token = test_res.get('access_token', '')
                    profile.save(update_fields=['sber_access_token'])
                    messages.success(request, "Ключ успешно проверен! Живой диалоговый ИИ активирован.")
                else:
                    messages.warning(request, f"Ключ сохранен, но проверка шлюза выдала: {test_res.get('error')}. Вы можете обновить его в профиле.")

            # Базовые баллы по компетенциям
            for comp in Competency.objects.all():
                ConductorCompetencyScore.objects.get_or_create(
                    profile=profile,
                    competency=comp,
                    defaults={'score': 55}
                )

            # Автоматический вход под созданной учетной записью
            login(request, user)
            messages.success(
                request,
                f"Поздравляем с зачислением в экипаж ВСМ-1 «Белый кречет», {full_name}! "
                f"Вам присвоен табельный номер: {badge_number}. Успешной и безопасной смены!"
            )
            return redirect('simulator:dashboard')
        else:
            messages.error(request, "Пожалуйста, проверьте правильность заполнения полей формы.")
    else:
        initial = {}
        sber_key_from_session = request.session.pop('pending_sber_auth_key', None)
        if sber_key_from_session:
            initial['sber_auth_key'] = sber_key_from_session
        form = ConductorRegistrationForm(initial=initial)

    context = {
        'form': form,
        'example_conductors': example_conductors,
    }
    return render(request, 'simulator/register.html', context)


def login_view(request):
    """
    Авторизация проводника в обучающем комплексе ВСМ.
    СТРОГОЕ ПРАВИЛО БЕЗОПАСНОСТИ:
    При вводе логина/табельного номера проверяется исключительно его наличие в базе данных ВСМ.
    Никаких автоматических созданий или сохранений новых пользователей здесь не происходит!
    Регистрация выполняется строго через форму регистрации (register_view).
    """
    if request.user.is_authenticated and hasattr(request.user, 'conductor_profile'):
        return redirect('simulator:dashboard')

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        form = ConductorLoginForm(request.POST)
        next_target = request.POST.get('next') or 'simulator:dashboard'
        if form.is_valid():
            username_or_badge = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']

            # 1. Проверяем наличие проводника в БД по логину или табельному номеру
            # (без создания и без изменения данных в БД)
            user_found = User.objects.filter(
                Q(username__iexact=username_or_badge) | Q(conductor_profile__badge_number__iexact=username_or_badge)
            ).select_related('conductor_profile').first()

            if not user_found:
                err_msg = (
                    f"Проводник с логином или табельным номером «{username_or_badge}» не найден в реестре экипажей ВСМ. "
                    f"Пожалуйста, проверьте правильность ввода или пройдите регистрацию нового сотрудника."
                )
                form.add_error(None, err_msg)
                messages.error(request, err_msg)
            else:
                # 2. Пользователь найден — проверяем корректность пароля
                user = authenticate(request, username=user_found.username, password=password)
                if user is not None:
                    login(request, user)
                    full_name = user.conductor_profile.full_name if hasattr(user, 'conductor_profile') else user.username
                    messages.success(request, f"Вход выполнен. Приятной смены, {full_name}!")
                    return redirect(next_target if next_target.startswith('/') else 'simulator:dashboard')
                else:
                    err_msg = f"Неверный логин или пароль проводника: неверный пароль для учетной записи «{user_found.username}». Проверьте раскладку клавиатуры и Caps Lock."
                    form.add_error('password', "Неверный пароль.")
                    messages.error(request, err_msg)
    else:
        form = ConductorLoginForm()

    context = {
        'form': form,
        'next': next_url,
    }
    return render(request, 'simulator/login.html', context)


def logout_view(request):
    """Завершение смены и выход из учетной записи"""
    logout(request)
    messages.info(request, "Смена завершена. Вы успешно вышли из системы ВСМ.")
    return redirect('simulator:login')


# =========================================================================
# ЦЕНТР УВЕДОМЛЕНИЙ ПРОВОДНИКА
# =========================================================================

def api_notifications_list(request):
    """Список уведомлений проводника и счетчик непрочитанных"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)

    notifications = conductor.notifications.all()[:20]
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'type_display': n.get_notification_type_display(),
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m %H:%M'),
        })
    return JsonResponse({
        'success': True,
        'unread_count': conductor.unread_notifications_count(),
        'notifications': data,
    })


@require_POST
def api_notification_mark_read(request, notification_id):
    """Отметка уведомления как прочитанного"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)

    notif = get_object_or_404(Notification, id=notification_id, conductor=conductor)
    notif.is_read = True
    notif.save(update_fields=['is_read'])

    return JsonResponse({
        'success': True,
        'unread_count': conductor.unread_notifications_count(),
    })


@require_POST
def api_notifications_read_all(request):
    """Отметка всех уведомлений как прочитанных"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)

    conductor.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({
        'success': True,
        'unread_count': 0,
    })


# =========================================================================
# АНАЛИТИКА КОМПЕТЕНЦИЙ И РЕКОМЕНДАЦИИ
# =========================================================================

def get_conductor_analytics(conductor):
    """Расчет аналитических показателей матрицы компетенций проводника"""
    all_competencies = list(Competency.objects.all().order_by('id'))
    if conductor:
        for comp in all_competencies:
            ConductorCompetencyScore.objects.get_or_create(
                profile=conductor,
                competency=comp,
                defaults={'score': 65}
            )

    competency_scores = ConductorCompetencyScore.objects.filter(
        profile=conductor
    ).select_related('competency').order_by('competency__id')

    comp_list = []
    radar_labels = []
    radar_short_labels = []
    radar_values = []
    radar_benchmarks = []
    BENCHMARK_SCORE = 85

    short_titles = {
        'service_etiquette': 'Сервисный этикет',
        'safety_regulations': 'Безопасность/ПТЭ',
        'conflict_resolution': 'Конфликтология',
        'emergency_medical': 'Первая помощь',
        'vsm_tech_protocols': 'Системы поезда',
        'mobility_assistance': 'Пассажиры МГН',
    }

    for cs in competency_scores:
        comp = cs.competency
        score = cs.score
        s_title = short_titles.get(comp.code, comp.title[:16])
        radar_labels.append(comp.title)
        radar_short_labels.append(s_title)
        radar_values.append(score)
        radar_benchmarks.append(BENCHMARK_SCORE)

        if score >= 80:
            status = 'mastered'
            status_label = 'Освоено'
            status_color = '#10b981'
        elif score >= 65:
            status = 'developing'
            status_label = 'В развитии'
            status_color = '#00d2ff'
        else:
            status = 'attention'
            status_label = 'Зона роста'
            status_color = '#fd033a'

        comp_list.append({
            'code': comp.code,
            'title': comp.title,
            'short_title': s_title,
            'description': comp.description,
            'score': score,
            'benchmark': BENCHMARK_SCORE,
            'delta': score - BENCHMARK_SCORE,
            'abs_delta': abs(score - BENCHMARK_SCORE),
            'status': status,
            'status_label': status_label,
            'status_color': status_color,
            'icon': comp.icon,
        })

    sorted_comps = sorted(comp_list, key=lambda x: x['score'], reverse=True)
    strengths = [c for c in sorted_comps if c['score'] >= 75][:3]
    weaknesses = [c for c in sorted_comps if c['score'] < 75]
    if not weaknesses and sorted_comps:
        weaknesses = sorted_comps[-2:]

    weak_codes = [w['code'] for w in weaknesses]
    recommended_scenarios = Scenario.objects.filter(
        is_active=True,
        nodes__choices__competency__code__in=weak_codes
    ).distinct()[:4]

    if not recommended_scenarios.exists():
        recommended_scenarios = Scenario.objects.filter(is_active=True)[:4]

    avg_score = round(sum(radar_values) / len(radar_values), 1) if radar_values else 0

    return {
        'conductor': conductor,
        'competencies': comp_list,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'recommended_scenarios': recommended_scenarios,
        'overall_index': avg_score,
        'radar_labels': radar_labels,
        'radar_short_labels': radar_short_labels,
        'radar_values': radar_values,
        'radar_benchmarks': radar_benchmarks,
    }


def analytics_view(request):
    """Экран матрицы компетенций, зон роста и персональных рекомендаций обучения"""
    conductor = get_current_conductor(request)
    if not conductor:
        return redirect('simulator:login')

    analytics_data = get_conductor_analytics(conductor)
    context = {
        'conductor': conductor,
        'analytics': analytics_data,
        'radar_json': json.dumps({
            'labels': analytics_data['radar_labels'],
            'short_labels': analytics_data.get('radar_short_labels', []),
            'values': analytics_data['radar_values'],
            'benchmarks': analytics_data['radar_benchmarks'],
        }, ensure_ascii=False),
    }
    return render(request, 'simulator/analytics.html', context)


def api_analytics_data(request):
    """JSON API матрицы компетенций проводника для интеграций и построения графиков"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Не авторизован'}, status=401)

    analytics_data = get_conductor_analytics(conductor)
    recommended = []
    for sc in analytics_data['recommended_scenarios']:
        recommended.append({
            'slug': sc.slug,
            'title': sc.title,
            'difficulty': sc.get_difficulty_display(),
            'speed': sc.train_speed,
            'url': reverse('simulator:scenario_detail', kwargs={'slug': sc.slug}),
        })

    return JsonResponse({
        'success': True,
        'conductor': {
            'full_name': conductor.full_name,
            'badge_number': conductor.badge_number,
            'rank': conductor.get_rank_display(),
            'level': conductor.level,
        },
        'overall_index': analytics_data['overall_index'],
        'competencies': analytics_data['competencies'],
        'strengths': analytics_data['strengths'],
        'weaknesses': analytics_data['weaknesses'],
        'recommended_scenarios': recommended,
        'radar': {
            'labels': analytics_data['radar_labels'],
            'values': analytics_data['radar_values'],
            'benchmarks': analytics_data['radar_benchmarks'],
        }
    })


# =========================================================================
# REST API V1: ПОЛНОЦЕННЫЙ ПРОГРАММНЫЙ ИНТЕРФЕЙС ПЛАТФОРМЫ
# =========================================================================

@csrf_exempt
def api_v1_profile(request):
    """
    REST API: Профиль проводника, табельный номер, депо, бригада и метрики.
    GET: Получение полной сводки профиля.
    POST / PATCH: Обновление редактируемых полей (депо, бригада, специализация обучения).
    """
    conductor = get_current_conductor(request) or ConductorProfile.objects.filter(is_example=False).first() or ConductorProfile.objects.first()
    if not conductor:
        return JsonResponse({'error': 'Профиль проводника не найден', 'code': 'NOT_FOUND'}, status=404)

    if request.method in ['POST', 'PATCH']:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        updated_fields = []
        if 'training_track' in data and data['training_track'] in dict(ConductorProfile.TRAINING_TRACKS):
            conductor.training_track = data['training_track']
            updated_fields.append('training_track')
        if 'depot' in data and isinstance(data['depot'], str) and data['depot'].strip():
            conductor.depot = data['depot'].strip()
            updated_fields.append('depot')
        if 'brigade' in data and isinstance(data['brigade'], str) and data['brigade'].strip():
            conductor.brigade = data['brigade'].strip()
            updated_fields.append('brigade')

        if updated_fields:
            conductor.save(update_fields=updated_fields)

    progress = conductor.get_progress_to_next_level()
    return JsonResponse({
        'success': True,
        'profile': {
            'full_name': conductor.full_name,
            'badge_number': conductor.badge_number,
            'depot': conductor.depot,
            'brigade': conductor.brigade,
            'rank': conductor.rank,
            'rank_display': conductor.get_rank_display(),
            'training_track': conductor.training_track,
            'training_track_display': conductor.get_training_track_display(),
            'track_progress': conductor.get_track_progress(),
            'level': conductor.level,
            'experience_points': conductor.experience_points,
            'loyalty_rating': conductor.loyalty_rating,
            'safety_rating': conductor.safety_rating,
            'service_rating': conductor.service_rating,
            'shifts_completed': conductor.shifts_completed,
            'perfect_shifts': conductor.perfect_shifts,
            'crew_count': conductor.crew_members.count(),
            'crew_synergy': conductor.get_crew_synergy(),
            'unread_notifications': conductor.unread_notifications_count(),
            'level_progress': progress,
        }
    })


def api_v1_scenarios(request):
    """REST API: Каталог обучающих кейс-сценариев с фильтрацией по категории, сложности и классу обслуживания"""
    category = request.GET.get('category')
    difficulty = request.GET.get('difficulty')
    service_class = request.GET.get('service_class') or request.GET.get('track')

    qs = Scenario.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if service_class and service_class != 'all':
        qs = qs.filter(service_class__in=[service_class, 'all'])

    items = []
    for sc in qs.order_by('order'):
        items.append({
            'slug': sc.slug,
            'title': sc.title,
            'category': sc.category,
            'category_display': sc.get_category_display(),
            'difficulty': sc.difficulty,
            'difficulty_display': sc.get_difficulty_display(),
            'service_class': sc.service_class,
            'service_class_display': sc.get_service_class_display(),
            'service_class_badge': sc.get_service_class_badge(),
            'train_speed': sc.train_speed,
            'base_xp': sc.base_xp,
            'description': sc.description,
            'car_info': sc.car_info,
            'location_name': sc.location_name,
            'regulation_reference': sc.regulation_reference,
            'nodes_count': sc.nodes.count(),
        })
    return JsonResponse({'success': True, 'count': len(items), 'scenarios': items})


def api_v1_scenario_detail(request, slug):
    """REST API: Детальная информация о сценарии и первый диалоговый узел"""
    sc = get_object_or_404(Scenario, slug=slug, is_active=True)
    start_node = sc.nodes.filter(node_key='start').first() or sc.nodes.first()

    start_choices = []
    if start_node:
        for c in start_node.choices.all().order_by('order'):
            start_choices.append({
                'id': c.id,
                'text': c.choice_text,
                'tactical_hint': c.tactical_hint,
            })

    return JsonResponse({
        'success': True,
        'scenario': {
            'slug': sc.slug,
            'title': sc.title,
            'category': sc.category,
            'category_display': sc.get_category_display(),
            'difficulty': sc.difficulty,
            'difficulty_display': sc.get_difficulty_display(),
            'train_speed': sc.train_speed,
            'base_xp': sc.base_xp,
            'description': sc.description,
            'car_info': sc.car_info,
            'location_name': sc.location_name,
            'regulation_reference': sc.regulation_reference,
            'initial_node': {
                'title': start_node.title,
                'character_name': start_node.character_name,
                'character_role': start_node.character_role,
                'character_mood': start_node.character_mood,
                'dialogue_text': start_node.dialogue_text,
                'narrative_context': start_node.narrative_context,
                'time_limit_seconds': start_node.time_limit_seconds,
                'choices': start_choices,
            } if start_node else None,
        }
    })


@csrf_exempt
@require_POST
def api_v1_simulation_start(request, slug):
    """REST API: Старт сессии симулятора по слагу сценария"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    scenario = get_object_or_404(Scenario, slug=slug, is_active=True)
    start_node = scenario.nodes.filter(node_key='start').first() or scenario.nodes.first()
    if not start_node:
        return JsonResponse({'error': 'Стартовый узел сценария не найден'}, status=400)

    session = TrainingSession.objects.create(
        conductor=conductor,
        scenario=scenario,
        current_node=start_node,
        current_loyalty=75,
        current_safety=95,
        current_service=80,
        current_stress=20,
        status='in_progress',
        session_log=[
            {
                'timestamp': timezone.now().strftime('%H:%M:%S'),
                'type': 'start',
                'action': f'Начало отработки сценария: {scenario.title}',
                'node_title': start_node.title,
            }
        ]
    )

    choices_data = []
    for c in start_node.choices.all().order_by('order'):
        choices_data.append({
            'id': c.id,
            'text': c.choice_text,
            'tactical_hint': c.tactical_hint,
        })

    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'scenario': {
            'slug': scenario.slug,
            'title': scenario.title,
            'train_speed': scenario.train_speed,
        },
        'current_node': {
            'title': start_node.title,
            'character_name': start_node.character_name,
            'character_role': start_node.character_role,
            'character_mood': start_node.character_mood,
            'dialogue_text': start_node.dialogue_text,
            'narrative_context': start_node.narrative_context,
            'time_limit_seconds': start_node.time_limit_seconds,
            'choices': choices_data,
        },
        'metrics': {
            'loyalty': session.current_loyalty,
            'safety': session.current_safety,
            'service': session.current_service,
            'stress': session.current_stress,
        }
    })


@csrf_exempt
@require_POST
def api_v1_simulation_choose(request, session_id):
    """REST API: Принятие решения в сессии с продвижением по дереву узлов"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)
    if session.status != 'in_progress':
        return JsonResponse({'error': 'Сессия уже завершена', 'code': 'SESSION_CLOSED'}, status=400)

    try:
        data = json.loads(request.body)
        choice_id = data.get('choice_id')
        is_timeout = data.get('is_timeout', False)
    except Exception:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    choice = None
    if choice_id and not is_timeout:
        choice = get_object_or_404(ScenarioChoice, id=choice_id, node=session.current_node)

    return process_simulation_decision(session, choice=choice, is_timeout=is_timeout)


@csrf_exempt
@require_POST
def api_v1_simulation_timeout(request, session_id):
    """REST API: Штраф по таймеру и переход при истечении лимита времени"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)
    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)
    return process_simulation_decision(session, choice=None, is_timeout=True)


def api_v1_simulation_debrief(request, session_id):
    """REST API: Обучающий разбор (дебрифинг) по 4-шаговой ролевой модели ВСМ"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    session = get_object_or_404(TrainingSession, id=session_id, conductor=conductor)
    if not session.debrief_feedback or 'remarks' not in session.debrief_feedback:
        session.debrief_feedback = generate_scenario_debrief(
            session, session.scenario, session.current_node, session.is_success
        )
        session.save(update_fields=['debrief_feedback'])

    return JsonResponse({
        'success': True,
        'session_id': session.id,
        'scenario': session.scenario.title,
        'is_success': session.is_success,
        'final_score': session.final_score,
        'earned_xp': session.earned_xp,
        'debrief': session.debrief_feedback,
    })


@csrf_exempt
def api_v1_notifications(request):
    """REST API: Получение списка и отметка прочитанности уведомлений проводника"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            notif_id = data.get('id')
            mark_all = data.get('all', False)
        except Exception:
            return JsonResponse({'error': 'Некорректный запрос'}, status=400)

        if mark_all:
            conductor.notifications.filter(is_read=False).update(is_read=True)
        elif notif_id:
            conductor.notifications.filter(id=notif_id).update(is_read=True)

        return JsonResponse({'success': True, 'unread_count': conductor.unread_notifications_count()})

    notifications = conductor.notifications.all()[:20]
    items = []
    for n in notifications:
        items.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'type_display': n.get_notification_type_display(),
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m %H:%M'),
        })

    return JsonResponse({
        'success': True,
        'unread_count': conductor.unread_notifications_count(),
        'notifications': items,
    })


def api_v1_analytics(request):
    """REST API: Аналитика матрицы компетенций, сильных/слабых зон и рекомендаций"""
    return api_analytics_data(request)


def api_v1_leaderboard(request):
    """REST API: Таблица лидеров проводников с фильтрацией"""
    depot_filter = request.GET.get('depot')
    account_type = request.GET.get('type', 'all')

    qs = ConductorProfile.objects.all()
    if depot_filter and depot_filter != 'all':
        qs = qs.filter(depot__icontains=depot_filter)
    if account_type == 'registered':
        qs = qs.filter(is_example=False)
    elif account_type == 'example':
        qs = qs.filter(is_example=True)

    conductors = qs.order_by('-experience_points')[:50]
    items = []
    for idx, c in enumerate(conductors, 1):
        items.append({
            'rank_position': idx,
            'full_name': c.full_name,
            'badge_number': c.badge_number,
            'depot': c.depot,
            'brigade': c.brigade,
            'rank': c.get_rank_display(),
            'level': c.level,
            'xp': c.experience_points,
            'loyalty': c.loyalty_rating,
            'safety': c.safety_rating,
            'is_example': c.is_example,
        })
    return JsonResponse({'success': True, 'total': len(items), 'leaderboard': items})


def api_v1_regulations(request):
    """
    REST API: Каталог нормативных документов, регламентов и стандартов ВСМ.
    Поддерживает фильтрацию по категории и текстовый поиск по названию/описанию.
    """
    category = request.GET.get('category')
    search = request.GET.get('q', '').strip().lower()

    db_docs = RegulationDocument.objects.filter(is_active=True).order_by('order_number')
    items = []

    if db_docs.exists():
        for d in db_docs:
            if category and d.category != category:
                continue
            if search and (search not in d.title.lower() and search not in d.subtitle.lower() and search not in d.description.lower()):
                continue
            items.append({
                'key': d.key,
                'title': d.title,
                'subtitle': d.subtitle,
                'order_number': d.order_number,
                'category': d.category,
                'badge': d.badge,
                'badge_color': d.badge_color,
                'description': d.description,
                'file_name': d.file_name,
                'file_size': d.file_size_display,
                'has_pdf': bool(d.file_base64),
                'chapters_count': len(d.chapters_data or []),
                'url': reverse('simulator:api_v1_regulation_detail', kwargs={'doc_key': d.key}),
            })
    else:
        for key, doc in REGULATION_DOCUMENTS.items():
            if search and (search not in doc.get('title', '').lower() and search not in doc.get('subtitle', '').lower() and search not in doc.get('description', '').lower()):
                continue
            items.append({
                'key': doc.get('key', key),
                'title': doc.get('title', ''),
                'subtitle': doc.get('subtitle', ''),
                'order_number': 0,
                'category': 'standard',
                'badge': doc.get('badge', ''),
                'badge_color': doc.get('badge_color', '#082a99'),
                'description': doc.get('description', ''),
                'file_name': doc.get('filename', ''),
                'file_size': doc.get('size', ''),
                'has_pdf': doc.get('format') == 'PDF',
                'chapters_count': len(doc.get('chapters', [])),
                'url': reverse('simulator:api_v1_regulation_detail', kwargs={'doc_key': key}),
            })

    return JsonResponse({
        'success': True,
        'count': len(items),
        'regulations': items
    })


def api_v1_regulation_detail(request, doc_key):
    """REST API: Получение текста и глав нормативного документа из базы данных или библиотеки первоисточников"""
    db_doc = RegulationDocument.objects.filter(key=doc_key, is_active=True).first()
    if db_doc:
        return JsonResponse({
            'success': True,
            'key': db_doc.key,
            'title': db_doc.title,
            'subtitle': db_doc.subtitle,
            'order_number': db_doc.order_number,
            'category': db_doc.category,
            'badge': db_doc.badge,
            'badge_color': db_doc.badge_color,
            'description': db_doc.description,
            'file_name': db_doc.file_name,
            'file_size': db_doc.file_size_display,
            'has_pdf': bool(db_doc.file_base64),
            'chapters': db_doc.chapters_data or [],
            'content': db_doc.content_markdown,
        })

    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return JsonResponse({'error': 'Документ не найден', 'code': 'NOT_FOUND'}, status=404)

    content = get_document_raw_content(doc_key)
    return JsonResponse({
        'success': True,
        'key': doc_info.get('key', doc_key),
        'title': doc_info.get('title', ''),
        'subtitle': doc_info.get('subtitle', ''),
        'order_number': 0,
        'category': 'standard',
        'badge': doc_info.get('badge', ''),
        'badge_color': doc_info.get('badge_color', '#082a99'),
        'description': doc_info.get('description', ''),
        'file_name': doc_info.get('filename', ''),
        'file_size': doc_info.get('size', ''),
        'has_pdf': doc_info.get('format') == 'PDF',
        'chapters': doc_info.get('chapters', []),
        'content': content,
    })


def api_v1_crew(request):
    """REST API: Состав поездного экипажа проводника и расчет синергии"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    members = []
    for m in conductor.crew_members.all().order_by('-experience_points'):
        members.append({
            'id': m.id,
            'full_name': m.full_name,
            'badge_number': m.badge_number,
            'rank': m.rank,
            'rank_display': m.get_rank_display(),
            'depot': m.depot,
            'brigade': m.brigade,
            'level': m.level,
            'experience_points': m.experience_points,
            'loyalty_rating': m.loyalty_rating,
            'safety_rating': m.safety_rating,
            'service_rating': m.service_rating,
        })

    return JsonResponse({
        'success': True,
        'crew_count': len(members),
        'crew_synergy': conductor.get_crew_synergy(),
        'crew_members': members,
    })


@csrf_exempt
@require_POST
def api_v1_crew_add(request, profile_id):
    """REST API: Включение коллеги в состав поездного экипажа"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    other = get_object_or_404(ConductorProfile, id=profile_id)
    if other.id == conductor.id:
        return JsonResponse({'error': 'Нельзя добавить себя в экипаж', 'code': 'SELF_ADD'}, status=400)

    conductor.add_to_crew(other)
    return JsonResponse({
        'success': True,
        'message': f'{other.full_name} успешно включен в ваш поездной экипаж.',
        'crew_count': conductor.crew_members.count(),
        'crew_synergy': conductor.get_crew_synergy(),
    })


@csrf_exempt
@require_POST
def api_v1_crew_remove(request, profile_id):
    """REST API: Исключение сотрудника из состава экипажа"""
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({'error': 'Требуется авторизация', 'code': 'UNAUTHORIZED'}, status=401)

    other = get_object_or_404(ConductorProfile, id=profile_id)
    conductor.remove_from_crew(other)
    return JsonResponse({
        'success': True,
        'message': f'{other.full_name} исключен из состава экипажа.',
        'crew_count': conductor.crew_members.count(),
        'crew_synergy': conductor.get_crew_synergy(),
    })


@csrf_exempt
@require_POST
def api_v1_profile_reset(request):
    """REST API: Сброс игрового прогресса проводника до 1 уровня"""
    conductor = get_current_conductor(request) or ConductorProfile.objects.filter(is_example=False).first() or ConductorProfile.objects.first()
    if not conductor:
        return JsonResponse({'error': 'Профиль проводника не найден', 'code': 'NOT_FOUND'}, status=404)

    conductor.reset_progress()
    return JsonResponse({
        'success': True,
        'message': f'Квалификационный прогресс проводника {conductor.full_name} сброшен.',
        'conductor': conductor.full_name,
        'level': conductor.level,
        'experience_points': conductor.experience_points,
        'rank': conductor.rank,
    })


@csrf_exempt
@require_POST
def api_v1_set_training_track(request):
    """REST API: Установка специализации обучения проводника (эконом, комфорт, бизнес, все)"""
    conductor = get_current_conductor(request) or ConductorProfile.objects.filter(is_example=False).first() or ConductorProfile.objects.first()
    if not conductor:
        return JsonResponse({'error': 'Профиль проводника не найден', 'code': 'NOT_FOUND'}, status=404)

    track = None
    try:
        if request.body:
            data = json.loads(request.body)
            track = data.get('training_track') or data.get('track')
    except Exception:
        pass

    if not track:
        track = request.POST.get('training_track') or request.POST.get('track')

    valid_tracks = dict(ConductorProfile.TRAINING_TRACKS)
    if not track or track not in valid_tracks:
        return JsonResponse({
            'error': f'Недопустимый класс обучения. Выберите один из: {", ".join(valid_tracks.keys())}',
            'code': 'INVALID_TRACK'
        }, status=400)

    conductor.training_track = track
    conductor.save(update_fields=['training_track'])

    return JsonResponse({
        'success': True,
        'message': f'Специализация обучения изменена: {valid_tracks[track]}',
        'training_track': track,
        'training_track_display': valid_tracks[track],
        'track_progress': conductor.get_track_progress(),
    })


def set_training_track_web(request, track):
    """Веб-действие: переключение специализации обучения с редиректом"""
    conductor = get_current_conductor(request)
    if conductor:
        valid_tracks = dict(ConductorProfile.TRAINING_TRACKS)
        if track in valid_tracks:
            conductor.training_track = track
            conductor.save(update_fields=['training_track'])
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or reverse('simulator:dashboard')
    return redirect(next_url)


ALLOWED_NEURAL_VOICES = {
    'ru-RU-DmitryNeural': 'Дмитрий (Нейросеть ВСМ, Мужской)',
    'ru-RU-SvetlanaNeural': 'Светлана (Нейросеть ВСМ, Женский)',
    'robot-telemetry': 'Бортовой компьютер ВСМ (Роботизированный женский)',
    'machinist-radio': 'Кабина машиниста (Рация интеркома)',
    'en-US-JennyNeural': 'Jenny (Нейросеть EN, Женский)',
    'en-US-GuyNeural': 'Guy (Нейросеть EN, Мужской)',
}


def sanitize_tts_text(text: str) -> str:
    """Очистка текста от спецсимволов для стабильной работы синтеза речи (только прямая речь, без ремарок в скобках)"""
    if not text:
        return ''
    
    # 1. Удаление сценических ремарок и звукоподражаний в скобках: (плачет), [кашляет], (кричит), (разбивает бокал) и т.д.
    text = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', text)
    
    # 2. Извлечение прямой речи персонажа, если передан текст с контекстом или кавычками
    quote_matches = re.findall(r'«([^»]+)»', text) or re.findall(r'"([^"]+)"', text)
    if quote_matches:
        text = ' '.join(quote_matches)
    else:
        colon_idx = text.find(':')
        if 0 < colon_idx < 45:
            text = text[colon_idx + 1:].strip()

    # 3. Повторная зачистка скобок на случай скобок внутри цитат или ремарок
    text = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', ' ', text)

    replacements = {
        '«': '', '»': '', '“': '', '”': '', '„': '', '"': '',
        '—': ' - ', '–': ' - ', '…': '...',
        '\r': ' ', '\n': ' ', '\t': ' ',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def classify_speaker_persona(name: str, role: str, title: str, text: str):
    """
    Интеллектуальное распределение голосов (делегирует в resolve_challenge_persona_and_avatar):
    Возвращает: (sp_type, voice, actual_voice, rate, pitch)
    """
    p = resolve_challenge_persona_and_avatar(name, role, title, text)
    return p['speaker_type'], p['voice_code'], p['actual_voice'], p['rate'], p['pitch']


def api_v1_tts_preload_list(request):
    """
    REST API: Возвращает список всех реплик диалогов (сценарии + бесконечная карусель)
    для фонового воркера предзагрузки в IndexedDB / localStorage браузера.
    """
    items = []
    seen_texts = set()
    cache_dir = settings.BASE_DIR / 'simulator' / 'static' / 'simulator' / 'audio' / 'tts_cache'

    # 1. Диалоги из сценариев
    for node in ScenarioNode.objects.filter(scenario__is_active=True).exclude(dialogue_text=''):
        raw = node.dialogue_text
        clean = sanitize_tts_text(raw)
        if not clean or clean in seen_texts:
            continue
        seen_texts.add(clean)

        sp_type, voice, actual_voice, rate, pitch = classify_speaker_persona(
            node.character_name, node.character_role, node.title, clean
        )

        sig = f"{actual_voice}_{rate}_{pitch}_{clean}".encode('utf-8')
        md5_hash = hashlib.md5(sig).hexdigest()
        file_path = cache_dir / f"{md5_hash}.mp3"
        cached = file_path.exists() and file_path.stat().st_size > 0

        items.append({
            'id': f"node_{node.id}",
            'text': clean,
            'speaker_type': sp_type,
            'voice': voice,
            'actual_voice': actual_voice,
            'rate': rate,
            'pitch': pitch,
            'hash': md5_hash,
            'audio_url': f"/static/simulator/audio/tts_cache/{md5_hash}.mp3",
            'cached': cached
        })

    # 2. Диалоги из бесконечной смены
    for ch in EndlessChallenge.objects.exclude(dialogue_text=''):
        raw = ch.dialogue_text
        clean = sanitize_tts_text(raw)
        if not clean or clean in seen_texts:
            continue
        seen_texts.add(clean)

        sp_type, voice, actual_voice, rate, pitch = classify_speaker_persona(
            ch.character_name, ch.character_role, ch.title, clean
        )

        sig = f"{actual_voice}_{rate}_{pitch}_{clean}".encode('utf-8')
        md5_hash = hashlib.md5(sig).hexdigest()
        file_path = cache_dir / f"{md5_hash}.mp3"
        cached = file_path.exists() and file_path.stat().st_size > 0

        items.append({
            'id': f"ech_{ch.id}",
            'text': clean,
            'speaker_type': sp_type,
            'voice': voice,
            'actual_voice': actual_voice,
            'rate': rate,
            'pitch': pitch,
            'hash': md5_hash,
            'audio_url': f"/static/simulator/audio/tts_cache/{md5_hash}.mp3",
            'cached': cached
        })

    return JsonResponse({
        'success': True,
        'total': len(items),
        'items': items
    })


@csrf_exempt
def api_v1_tts(request):
    """
    REST API: Нейросетевой синтез речи (Microsoft Neural AI) для реплик пассажиров и объявлений ВСМ.
    Поддерживает естественные интонации, выбор диктора и дисковое кэширование mp3.
    """
    raw_text = (request.GET.get('text') or request.POST.get('text') or '').strip()
    if not raw_text:
        return JsonResponse({'error': 'Текст для озвучки не передан', 'code': 'EMPTY_TEXT'}, status=400)

    clean_text = sanitize_tts_text(raw_text)
    if not clean_text:
        return JsonResponse({'error': 'Текст не содержит произносимых символов', 'code': 'INVALID_TEXT'}, status=400)

    if len(clean_text) > 1500:
        clean_text = clean_text[:1500]

    voice_input = (request.GET.get('voice') or request.POST.get('voice') or 'ru-RU-DmitryNeural').strip()
    is_robot = (voice_input == 'robot-telemetry')
    is_machinist = (voice_input == 'machinist-radio')

    if is_robot:
        voice = 'ru-RU-SvetlanaNeural'
        default_rate = '+12%'
        default_pitch = '+10Hz'
    elif is_machinist:
        voice = 'ru-RU-DmitryNeural'
        default_rate = '+10%'
        default_pitch = '-20Hz'
    elif voice_input in ALLOWED_NEURAL_VOICES:
        voice = voice_input
        default_rate = '+0%'
        default_pitch = '+0Hz'
    else:
        voice = 'ru-RU-DmitryNeural'
        default_rate = '+0%'
        default_pitch = '+0Hz'

    rate_param = (request.GET.get('rate') or request.POST.get('rate') or default_rate).strip()
    pitch_param = (request.GET.get('pitch') or request.POST.get('pitch') or default_pitch).strip()

    # Нормализация скорости речи
    try:
        if rate_param.replace('.', '', 1).isdigit() or (rate_param.startswith('-') and rate_param[1:].replace('.', '', 1).isdigit()):
            rate_float = float(rate_param)
            rate_pct = int(round((rate_float - 1.0) * 100))
            rate_str = f"{rate_pct:+d}%"
        else:
            rate_str = rate_param if ('%' in rate_param) else '+0%'
    except Exception:
        rate_str = '+0%'

    # Нормализация высоты тона
    try:
        if pitch_param.replace('.', '', 1).isdigit() or (pitch_param.startswith('-') and pitch_param[1:].replace('.', '', 1).isdigit()):
            pitch_float = float(pitch_param)
            pitch_hz = int(round((pitch_float - 1.0) * 20))
            pitch_str = f"{pitch_hz:+d}Hz"
        else:
            pitch_str = pitch_param if ('Hz' in pitch_param) else '+0Hz'
    except Exception:
        pitch_str = '+0Hz'

    # Потоковый синтез в оперативной памяти БЕЗ дискового кэширования (живой чат)
    try:
        from asgiref.sync import async_to_sync
        import edge_tts

        audio_chunks = []
        async def _synthesize():
            try:
                comm = edge_tts.Communicate(clean_text, voice=voice, rate=rate_str, pitch=pitch_str)
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
            except Exception:
                pass

            if not audio_chunks:
                try:
                    comm = edge_tts.Communicate(clean_text, voice=voice)
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            audio_chunks.append(chunk["data"])
                except Exception:
                    pass

        async_to_sync(_synthesize)()

        if audio_chunks:
            audio_bytes = b"".join(audio_chunks)
            b64_audio = base64.b64encode(audio_bytes).decode('ascii')
            audio_data_url = f"data:audio/mpeg;base64,{b64_audio}"
            return JsonResponse({
                'success': True,
                'audio_url': audio_data_url,
                'cached': False,
                'voice': voice,
                'voice_name': ALLOWED_NEURAL_VOICES.get(voice, voice),
            })
        else:
            return JsonResponse({
                'success': False,
                'fallback_to_browser': True,
                'error': 'Служба нейросинтеза не сформировала аудиофайл, переключение на локальный диктор устройства',
                'code': 'EMPTY_AUDIO',
            }, status=200)
    except Exception as exc:
        return JsonResponse({
            'success': False,
            'fallback_to_browser': True,
            'error': f'Служба синтеза речи временно недоступна: {str(exc)}',
            'code': 'SYNTHESIS_FALLBACK',
        }, status=200)


def get_openapi_spec(request):
    """Спецификация OpenAPI 3.0.3 для REST API платформы ВСМ-1"""
    base_url = request.build_absolute_uri('/')
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "ВСМ-1 «Белый кречет» | API Обучающего комплекса проводников",
            "version": "1.0.0",
            "description": "Официальный программный интерфейс (REST API) обучающего комплекса экипажей ВСМ-1 Москва — Санкт-Петербург (до 400 км/ч). Разработан по стандартам ВСМ и нормативным актам СТО ВСМ 03.011-2026, 03.013-2026, 03.014-2026."
        },
        "servers": [
            {"url": base_url, "description": "Текущий сервер ВСМ"}
        ],
        "tags": [
            {"name": "Profile", "description": "Управление профилем проводника и статистика"},
            {"name": "Crew", "description": "Поездной экипаж (социальная сеть поездных бригад и синергия)"},
            {"name": "Scenarios", "description": "Сценарные кейсы и дерево решений"},
            {"name": "Simulation", "description": "Управление сессией прохождения и разбор полетов"},
            {"name": "Carousel", "description": "Режим скоростной карусели решений (250-400 км/ч)"},
            {"name": "Regulations", "description": "Нормативная документация и стандарты ВСМ из БД"},
            {"name": "Analytics", "description": "Матрица компетенций и рекомендации"},
            {"name": "Leaderboard", "description": "Рейтинг экипажа и статистика депо"},
            {"name": "Notifications", "description": "Центр уведомлений и сгорающих баллов"},
            {"name": "Audio", "description": "Синтез речи (TTS) и аудиосистема ВСМ"},
            {"name": "AI Live", "description": "Интерактивный диалоговый ИИ, речевой комплекс и ключи доступа"}
        ],
        "paths": {
            "/api/v1/profile/": {
                "get": {
                    "tags": ["Profile"],
                    "summary": "Получить профиль проводника",
                    "description": "Возвращает квалификацию, ранг, депо, бригаду, состав экипажа, очки опыта и шкалы лояльности/безопасности.",
                    "responses": {
                        "200": {"description": "Успешный ответ"},
                        "401": {"description": "Не авторизован"}
                    }
                },
                "patch": {
                    "tags": ["Profile"],
                    "summary": "Обновить данные профиля проводника",
                    "description": "Обновление редактируемых полей: специализация (training_track), депо (depot), бригада (brigade).",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "training_track": {"type": "string", "enum": ["economy", "comfort", "business", "all"]},
                                        "depot": {"type": "string", "description": "Наименование депо приписки"},
                                        "brigade": {"type": "string", "description": "Номер или название поездной бригады"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Профиль успешно обновлен"},
                        "401": {"description": "Не авторизован"}
                    }
                }
            },
            "/api/v1/profile/reset/": {
                "post": {
                    "tags": ["Profile"],
                    "summary": "Сброс прогресса аккаунта проводника до 1 уровня",
                    "responses": {"200": {"description": "Статус сброса"}}
                }
            },
            "/api/v1/profile/training-track/": {
                "post": {
                    "tags": ["Profile"],
                    "summary": "Установить или переключить специализацию обучения проводника",
                    "description": "Позволяет выбрать класс обслуживания: economy (эконом), comfort (комфорт), business (бизнес) или all (все классы). Возвращает обновленный профиль и прогресс аттестации.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "training_track": {
                                            "type": "string",
                                            "enum": ["economy", "comfort", "business", "all"],
                                            "description": "Код специализации"
                                        }
                                    },
                                    "required": ["training_track"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Специализация успешно обновлена"},
                        "400": {"description": "Недопустимый код специализации"}
                    }
                }
            },
            "/api/v1/crew/": {
                "get": {
                    "tags": ["Crew"],
                    "summary": "Состав поездного экипажа проводника и показатель синергии",
                    "responses": {"200": {"description": "Список членов экипажа и синергия"}}
                }
            },
            "/api/v1/crew/add/{profile_id}/": {
                "post": {
                    "tags": ["Crew"],
                    "summary": "Включение сотрудника в поездной экипаж",
                    "parameters": [{"name": "profile_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Успешное добавление"}}
                }
            },
            "/api/v1/crew/remove/{profile_id}/": {
                "post": {
                    "tags": ["Crew"],
                    "summary": "Исключение сотрудника из поездного экипажа",
                    "parameters": [{"name": "profile_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Успешное исключение"}}
                }
            },
            "/api/v1/scenarios/": {
                "get": {
                    "tags": ["Scenarios"],
                    "summary": "Каталог сценариев рейса",
                    "parameters": [
                        {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Категория (conflict, medical, safety, tech_failure, etc.)"},
                        {"name": "difficulty", "in": "query", "schema": {"type": "string"}, "description": "Сложность (easy, medium, hard, expert)"},
                        {"name": "service_class", "in": "query", "schema": {"type": "string", "enum": ["economy", "comfort", "business", "all"]}, "description": "Класс обслуживания вагона (economy, comfort, business, all)"}
                    ],
                    "responses": {"200": {"description": "Список сценариев с метаданными"}}
                }
            },
            "/api/v1/scenario/{slug}/": {
                "get": {
                    "tags": ["Scenarios"],
                    "summary": "Детальная информация о сценарии и стартовый шаг",
                    "parameters": [{"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Данные сценария"}, "404": {"description": "Сценарий не найден"}}
                }
            },
            "/api/v1/simulation/start/{slug}/": {
                "post": {
                    "tags": ["Simulation"],
                    "summary": "Начать сессию прохождения сценария",
                    "parameters": [{"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Сессия создана, возвращен ID и стартовый диалог"}}
                }
            },
            "/api/v1/simulation/{session_id}/choose/": {
                "post": {
                    "tags": ["Simulation"],
                    "summary": "Принять решение на текущем этапе",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"choice_id": {"type": "integer"}}}}}
                    },
                    "responses": {"200": {"description": "Результат решения, изменение шкал, переход к следующему узлу или финал"}}
                }
            },
            "/api/v1/simulation/{session_id}/timeout/": {
                "post": {
                    "tags": ["Simulation"],
                    "summary": "Обработка истечения таймера на этапе сценария",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Применен штраф по тайм-ауту и совершен переход"}}
                }
            },
            "/api/v1/simulation/{session_id}/debrief/": {
                "get": {
                    "tags": ["Simulation"],
                    "summary": "Обучающий разбор (дебрифинг) по 4-шаговой ролевой модели ВСМ",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Детализированный разбор ошибок и успехов"}}
                }
            },
            "/api/v1/carousel/start/": {
                "post": {
                    "tags": ["Carousel"],
                    "summary": "Старт смены в режиме «Карусель решений»",
                    "description": "Инициализирует скоростную смену поездной бригады, генерирует дорожные дилеммы по классу обслуживания вагона и возвращает первую задачу.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "service_class": {
                                            "type": "string",
                                            "enum": ["economy", "comfort", "business", "all"],
                                            "default": "all",
                                            "description": "Класс обслуживания вагона для отработки ситуаций"
                                        },
                                        "challenge_id": {
                                            "type": "integer",
                                            "description": "Необязательный ID конкретной задачи для принудительного старта"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Смена открыта, возвращена первая дилемма и параметры поезда"},
                        "401": {"description": "Требуется авторизация"}
                    }
                }
            },
            "/api/v1/carousel/{session_id}/choose/": {
                "post": {
                    "tags": ["Carousel"],
                    "summary": "Принятие решения проводника в карусели",
                    "description": "Проверяет регламентное действие, рассчитывает стрик и множитель очков, ускоряет поезд (250-400 км/ч), начисляет опыт и возвращает следующую задачу либо итоги рейса.",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "challenge_id": {"type": "integer", "description": "ID решаемой задачи"},
                                        "choice_index": {"type": "integer", "description": "Индекс выбранного ответа"},
                                        "time_spent": {"type": "number", "description": "Затраченное время на ответ в секундах"}
                                    },
                                    "required": ["challenge_id"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Результат решения, дельты шкал, стрик, скорость и следующая задача"},
                        "400": {"description": "Некорректный запрос или смена уже закрыта"}
                    }
                }
            },
            "/api/v1/carousel/{session_id}/finish/": {
                "post": {
                    "tags": ["Carousel"],
                    "summary": "Штатная сдача вагона и завершение смены в карусели",
                    "description": "Фиксирует набранные баллы, проверяет безупречность смены, начисляет квалификационный опыт и формирует замечания в бортовой журнал.",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Итоговая ведомость смены и расчет опыта"},
                        "400": {"description": "Смена уже была закрыта"}
                    }
                }
            },
            "/api/v1/carousel/{session_id}/state/": {
                "get": {
                    "tags": ["Carousel"],
                    "summary": "Текущее состояние активной смены в карусели",
                    "description": "Возвращает скорость состава, уровень стресса/лояльности, решенные задачи и текущую дилемму.",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Текущий HUD статус сессии"},
                        "404": {"description": "Сессия не найдена"}
                    }
                }
            },
            "/api/v1/regulations/": {
                "get": {
                    "tags": ["Regulations"],
                    "summary": "Каталог нормативных документов, регламентов и стандартов ВСМ",
                    "description": "Возвращает список официальных стандартов СТО ВСМ, учебников, ПТЭ и инструкций с поддержкой фильтрации по категории и текстового поиска.",
                    "parameters": [
                        {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Категория (standard, textbook, pte, rules)"},
                        {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Поисковый запрос по названию или описанию"}
                    ],
                    "responses": {
                        "200": {"description": "Каталог нормативных документов с метаданными и количеством глав"}
                    }
                }
            },
            "/api/v1/regulations/{doc_key}/": {
                "get": {
                    "tags": ["Regulations"],
                    "summary": "Получить нормативный документ из БД",
                    "parameters": [{"name": "doc_key", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Метаданные, главы и markdown-текст регламента"}}
                }
            },
            "/api/v1/notifications/": {
                "get": {
                    "tags": ["Notifications"],
                    "summary": "Список уведомлений проводника",
                    "responses": {"200": {"description": "Список уведомлений и счетчик непрочитанных"}}
                },
                "post": {
                    "tags": ["Notifications"],
                    "summary": "Отметить уведомление как прочитанное",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"id": {"type": "integer"}, "all": {"type": "boolean"}}}}}
                    },
                    "responses": {"200": {"description": "Статус обновления"}}
                }
            },
            "/api/v1/analytics/": {
                "get": {
                    "tags": ["Analytics"],
                    "summary": "Аналитика матрицы компетенций проводника",
                    "responses": {"200": {"description": "Радар компетенций, зоны роста, персональные рекомендации"}}
                }
            },
            "/api/v1/leaderboard/": {
                "get": {
                    "tags": ["Leaderboard"],
                    "summary": "Таблица лидеров и рейтинг депо",
                    "parameters": [
                        {"name": "depot", "in": "query", "schema": {"type": "string"}, "description": "Фильтр по названию депо"},
                        {"name": "type", "in": "query", "schema": {"type": "string"}, "description": "all | registered | example"}
                    ],
                    "responses": {"200": {"description": "Рейтинговый список"}}
                }
            },
            "/api/v1/tts/": {
                "get": {
                    "tags": ["Audio"],
                    "summary": "Нейросетевой синтез речи реплик и объявлений (Microsoft Neural AI)",
                    "description": "Синтезирует речь реплик пассажиров и объявлений ВСМ с естественными интонациями и дисковым кэшированием.",
                    "parameters": [
                        {"name": "text", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Текст для озвучки"},
                        {"name": "voice", "in": "query", "schema": {"type": "string", "default": "ru-RU-DmitryNeural"}, "description": "Голос диктора (ru-RU-DmitryNeural, ru-RU-SvetlanaNeural, en-US-JennyNeural, en-US-GuyNeural, robot-telemetry, machinist-radio)"},
                        {"name": "rate", "in": "query", "schema": {"type": "string", "default": "+0%"}, "description": "Скорость речи (+0%, 1.0, +10%, etc.)"},
                        {"name": "pitch", "in": "query", "schema": {"type": "string", "default": "+0Hz"}, "description": "Высота тона (+0Hz, 1.0, +5Hz, etc.)"}
                    ],
                    "responses": {
                        "200": {"description": "Успешный синтез с прямой ссылкой на аудиофайл MP3 или Base64 Data URL"},
                        "400": {"description": "Пустой или невалидный текст"},
                        "500": {"description": "Ошибка генерации аудио"}
                    }
                }
            },
            "/api/v1/tts/preload-list/": {
                "get": {
                    "tags": ["Audio"],
                    "summary": "Список всех реплик диалогов для фоновой предзагрузки аудио",
                    "description": "Возвращает полные метаданные реплик сценариев и карусели с MD5-хэшами и статусом дискового кэширования для воркера офлайн-синтеза.",
                    "responses": {
                        "200": {"description": "Список реплик и аудио-ссылок"}
                    }
                }
            },
            "/api/v1/live/turn/": {
                "post": {
                    "tags": ["AI Live"],
                    "summary": "Генеративный ход ИИ-диалога (Диалоговый ИИ + судейство регламентов ВСМ)",
                    "description": "Принимает свободную речь проводника (текст/ASR), физические действия с оборудованием состава и историю. Возвращает ответ персонажа, динамику поезда, обновление шкал и статус сценария.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_id": {"type": "integer"},
                                        "message": {"type": "string", "description": "Речь проводника"},
                                        "action": {"type": "string", "description": "Код физического действия с оборудованием (emergency_brake, glass_hammer, fire_extinguisher, electric_panel, aed_medkit, ukeb_scan, tea_service, driver_intercom)"},
                                        "history": {"type": "array", "items": {"type": "object"}}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Успешный ход с репликой персонажа, дельтами шкал и обратной связью"},
                        "400": {"description": "Некорректный запрос"},
                        "404": {"description": "Сессия не найдена"}
                    }
                }
            },
            "/api/v1/live/asr/": {
                "post": {
                    "tags": ["AI Live"],
                    "summary": "Распознавание речи проводника (Бортовой речевой комплекс ВСМ)",
                    "description": "Принимает бинарный аудиопоток (WebM/Opus, OGG, WAV) с микрофона проводника и возвращает распознанный текст (через Vulkan GPU Whisper).",
                    "responses": {
                        "200": {"description": "Результат распознавания текста речи"},
                        "400": {"description": "Аудиоданные не получены"}
                    }
                }
            },
            "/api/v1/live/tts/": {
                "get": {
                    "tags": ["AI Live"],
                    "summary": "Синтез речи персонажей ВСМ (Бортовой комплекс TTS)",
                    "description": "Синтезирует аудиопоток реплик пассажиров и объявлений через бортовой речевой комплекс ВСМ.",
                    "parameters": [
                        {"name": "text", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Текст реплики"},
                        {"name": "voice", "in": "query", "schema": {"type": "string", "default": "Ost_24000"}, "description": "Голос синтеза ВСМ"},
                        {"name": "format", "in": "query", "schema": {"type": "string", "default": "opus"}, "description": "Формат аудиопотока (opus, wav16)"}
                    ],
                    "responses": {
                        "200": {"description": "Бинарный аудиопоток речи"},
                        "400": {"description": "Текст обязателен"}
                    }
                }
            },
            "/api/v1/conductor/sber-credentials/": {
                "get": {
                    "tags": ["AI Live"],
                    "summary": "Статус подключения Корпоративный ID и маскированные ключи профиля",
                    "description": "Проверяет наличие персональных токенов ИИ в профиле авторизованного проводника.",
                    "responses": {
                        "200": {"description": "Статус наличия ключей и маскированные значения"},
                        "401": {"description": "Требуется авторизация"}
                    }
                },
                "post": {
                    "tags": ["AI Live"],
                    "summary": "Привязка и верификация персонального ключа диалогового ИИ",
                    "description": "Сохраняет персональный ключ доступа, выполняет онлайн-проверку через шлюз API и выдает срок действия токена.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "auth_key": {"type": "string", "description": "Base64 Authorization Key"},
                                        "client_id": {"type": "string", "description": "Client ID платформы ИИ"},
                                        "client_secret": {"type": "string", "description": "Client Secret платформы ИИ"},
                                        "salutespeech_auth_key": {"type": "string", "description": "Ключ речевого комплекса"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Ключ успешно верифицирован и сохранен"},
                        "400": {"description": "Ошибка верификации ключа"}
                    }
                }
            },
            "/api/v1/sber/verify-key/": {
                "post": {
                    "tags": ["AI Live"],
                    "summary": "Мгновенная проверка ключа платформы ИИ при регистрации",
                    "description": "Публичный эндпоинт валидации учетных данных без сохранения в БД.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "client_id": {"type": "string"},
                                        "client_secret": {"type": "string"},
                                        "key": {"type": "string", "description": "Base64 auth key"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Результат верификации (успешно / ошибка авторизации)"}
                    }
                }
            }
        }
    }


def api_v1_openapi(request):
    """REST API: Выдача спецификации OpenAPI 3.0.3 в формате JSON"""
    spec = get_openapi_spec(request)
    return JsonResponse(spec, json_dumps_params={'ensure_ascii': False, 'indent': 2})


def swagger_ui(request):
    """Интерактивная страница Swagger UI документации REST API ВСМ-1"""
    conductor = get_current_conductor(request)
    context = {
        'conductor': conductor,
        'openapi_url': reverse('simulator:api_v1_openapi'),
    }
    return render(request, 'simulator/swagger_ui.html', context)


# =========================================================================
# ГЕНЕРАТИВНЫЙ ИИ-ДИАЛОГ И ГОЛОСОВОЙ LIVE ЭФИР ВСМ
# =========================================================================

@csrf_exempt
def api_live_turn(request):
    """
    Эндпоинт генеративного диалога с интеллектуальным ассистентом.
    Принимает речь проводника (текст/ASR), физические действия с оборудованием и историю.
    Возвращает реплику персонажа, динамику поезда, обновление шкал и статус сценария.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Метод должен быть POST")

    conductor = get_current_conductor(request)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Некорректный формат JSON'}, status=400)

    session_id = data.get('session_id')
    if not session_id:
        return JsonResponse({'error': 'Параметр session_id обязателен'}, status=400)

    if conductor:
        session = TrainingSession.objects.filter(id=session_id, conductor=conductor).first()
    else:
        session = TrainingSession.objects.filter(id=session_id).first()

    if not session:
        return JsonResponse({'error': 'Игровая сессия не найдена'}, status=404)

    message = data.get('message', '').strip()
    action = data.get('action', '').strip()
    history = data.get('history', [])

    turn_data = SberAIService.generate_live_turn(
        scenario=session.scenario,
        session=session,
        conductor_message=message,
        conductor_action=action,
        dialogue_history=history
    )

    if session.status in ['completed', 'failed']:
        check_and_unlock_achievements(session.conductor, session, session.scenario)

    return JsonResponse({'ok': True, 'data': turn_data})


@csrf_exempt
def api_live_asr(request):
    """
    Распознавание речи проводника через бортовой аппаратно-ускоренный модуль (Vulkan GPU).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Метод должен быть POST")

    audio_bytes = None
    content_type = "audio/ogg;codecs=opus"

    if request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        audio_bytes = audio_file.read()
        content_type = audio_file.content_type or content_type
    else:
        try:
            if request.body:
                audio_bytes = request.body
                content_type = request.content_type or content_type
        except Exception:
            audio_bytes = None

    if not audio_bytes:
        return JsonResponse({'ok': False, 'error': 'Аудиоданные не переданы', 'fallback_to_browser': True}, status=400)

    # 1. Приоритет: бортовой аппаратно-ускоренный модуль Vulkan ASR
    from .services.whisper_service import WhisperVulkanService
    if WhisperVulkanService.is_available():
        res = WhisperVulkanService.transcribe(audio_bytes, language="ru")
        if res.get("ok"):
            return JsonResponse(res)

    conductor = get_current_conductor(request)
    res = SberAIService.recognize_speech(audio_bytes, content_type=content_type, conductor=conductor)
    return JsonResponse(res)


def api_live_tts(request):
    """
    Потоковый многоголосый синтез речи персонажей ВСМ (Microsoft Edge Neural TTS) без дискового кэширования.
    """
    text = request.GET.get('text', '').strip()
    voice = request.GET.get('voice', 'Ost_24000').strip()
    fmt = request.GET.get('format', 'mp3').strip()

    if not text:
        return HttpResponseBadRequest("Параметр text обязателен")

    conductor = get_current_conductor(request)
    audio_bytes, mime = SberAIService.synthesize_speech(text, voice=voice, format_type=fmt, conductor=conductor)
    if not audio_bytes:
        return HttpResponse("Не удалось синтезировать речь", status=500)

    response = HttpResponse(audio_bytes, content_type=mime)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


# =========================================================================
# КОРПОРАТИВНЫЙ ID OAUTH 2.0 АВТОРИЗАЦИЯ ПРОВОДНИКОВ
# =========================================================================

def auth_sber_login(request):
    """
    Авторизация через Корпоративный ID OAuth 2.0:
    - Проверяет авторизационный ключ через шлюз API
    - Получает рабочий токен диалогового ИИ
    - Привязывает персональный ключ к ConductorProfile проводника
    """
    custom_key = (request.POST.get('sber_auth_key') or request.GET.get('sber_auth_key') or '').strip()
    client_id = (request.POST.get('client_id') or '').strip()
    client_secret = (request.POST.get('client_secret') or '').strip()

    if client_id and client_secret:
        import base64
        custom_key = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    auth_key = custom_key or getattr(settings, 'GIGACHAT_AUTH_KEY', '').strip()
    scope = getattr(settings, 'GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')

    if not auth_key:
        messages.info(request, "Для подключения ИИ-ассистента укажите персональный ключ в профиле или войдите по логину.")
        return redirect('simulator:login')

    test_res = SberAIService.test_conductor_auth_key(auth_key, scope=scope)
    if not test_res.get("ok"):
        err = test_res.get("error", "Неизвестная ошибка шлюза")
        messages.error(request, f"Ошибка шлюза авторизации OAuth: {err}")
        return redirect('simulator:login')

    access_token = test_res.get("access_token", "")

    # 1. Если проводник уже авторизован на сайте под своей учетной записью
    if request.user.is_authenticated and hasattr(request.user, 'conductor_profile'):
        profile = request.user.conductor_profile
        profile.sber_auth_key = auth_key
        profile.sber_access_token = access_token
        profile.save(update_fields=['sber_auth_key', 'sber_access_token'])
        messages.success(request, f"Ключ успешно привязан к вашему профилю проводника ({profile.full_name})! Интеллектуальный ассистент активирован.")
        return redirect('simulator:dashboard')

    # 2. Ищем существующего проводника с этим ключом
    existing_profile = ConductorProfile.objects.filter(sber_auth_key=auth_key).select_related('user').first()
    if existing_profile and existing_profile.user:
        user = existing_profile.user
        existing_profile.sber_access_token = access_token
        existing_profile.save(update_fields=['sber_access_token'])
        login(request, user)
        messages.success(request, f"С возвращением, {existing_profile.full_name}! Интеллектуальный ассистент активирован.")
        return redirect('simulator:dashboard')

    # 3. Ищем основной профиль проводника 'maxim'
    user = User.objects.filter(username='maxim').first()
    if user and hasattr(user, 'conductor_profile'):
        profile = user.conductor_profile
        profile.sber_auth_key = auth_key
        profile.sber_access_token = access_token
        profile.save(update_fields=['sber_auth_key', 'sber_access_token'])
        login(request, user)
        messages.success(request, f"Добро пожаловать в тренажер, {profile.full_name}! Интеллектуальный ассистент активирован.")
        return redirect('simulator:dashboard')

    # 4. Если профиль еще не создан — перенаправляем на регистрацию с предзаполненным ключом
    request.session['pending_sber_auth_key'] = auth_key
    messages.info(request, "Ключ успешно подтвержден! Заполните анкету для создания служебного профиля проводника.")
    return redirect('simulator:register')


def auth_sber_callback(request):
    """Callback-обработчик перенаправляет на единый вход auth_sber_login"""
    return auth_sber_login(request)


@csrf_exempt
def api_conductor_sber_credentials(request):
    """
    API управления личными токенами и ключами ИИ-ассистент в профиле проводника:
    GET: статус подключения Единый ID и наличие персонального токена
    POST: сохранение и верификация персонального ключа sber_auth_key
    """
    conductor = get_current_conductor(request)
    if not conductor:
        return JsonResponse({"error": "Требуется авторизация проводника"}, status=401)

    if request.method == 'GET':
        return JsonResponse({
            "ok": True,
            "has_sber_id": bool(conductor.sber_id),
            "sber_id": conductor.sber_id or "",
            "has_auth_key": bool(conductor.sber_auth_key),
            "auth_key_masked": (conductor.sber_auth_key[:6] + "..." + conductor.sber_auth_key[-4:]) if conductor.sber_auth_key and len(conductor.sber_auth_key) > 10 else "",
            "has_salutespeech_auth_key": bool(conductor.salutespeech_auth_key),
            "salutespeech_auth_key_masked": (conductor.salutespeech_auth_key[:6] + "..." + conductor.salutespeech_auth_key[-4:]) if conductor.salutespeech_auth_key and len(conductor.salutespeech_auth_key) > 10 else "",
            "has_access_token": bool(conductor.sber_access_token),
            "scope": conductor.sber_scope or "GIGACHAT_API_PERS",
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.POST

        # Проверяем отдельный ключ для речевого комплекса
        if 'salutespeech_auth_key' in data:
            salutespeech_key = (data.get('salutespeech_auth_key') or '').strip()
            if salutespeech_key:
                check = SberAIService.test_conductor_auth_key(salutespeech_key, scope='SALUTE_SPEECH_PERS')
                if not check.get('ok'):
                    return JsonResponse({
                        "ok": False,
                        "error": f"Ошибка верификации ключа речевого комплекса: {check.get('error')}"
                    }, status=400)

                conductor.salutespeech_auth_key = salutespeech_key
                conductor.save(update_fields=['salutespeech_auth_key'])
                return JsonResponse({
                    "ok": True,
                    "message": "Персональный ключ речевого комплекса успешно привязан и проверен!",
                    "expires_at": check.get('expires_at')
                })
            else:
                conductor.salutespeech_auth_key = None
                conductor.save(update_fields=['salutespeech_auth_key'])
                return JsonResponse({
                    "ok": True,
                    "message": "Личный ключ речевого комплекса удален из профиля."
                })

        # Обработка ключа диалогового ИИ
        client_id = (data.get('client_id') or data.get('sber_client_id') or '').strip()
        client_secret = (data.get('client_secret') or data.get('sber_client_secret') or '').strip()
        auth_key = (data.get('auth_key') or data.get('sber_auth_key') or '').strip()
        scope = (data.get('scope') or 'GIGACHAT_API_PERS').strip()

        if client_id and client_secret:
            auth_key = base64.b64encode(f"{client_id}:{client_secret}".encode('utf-8')).decode('utf-8')
        elif auth_key:
            try:
                dec = base64.b64decode(auth_key).decode('utf-8', errors='ignore')
                if ':' in dec:
                    parts = dec.split(':', 1)
                    if not client_id:
                        client_id = parts[0]
                    if not client_secret:
                        client_secret = parts[1]
            except Exception:
                pass

        if auth_key:
            check = SberAIService.test_conductor_auth_key(auth_key, scope=scope)
            if not check.get('ok'):
                return JsonResponse({
                    "ok": False,
                    "error": f"Ошибка верификации ключа: {check.get('error')}"
                }, status=400)

            conductor.sber_client_id = client_id
            conductor.sber_client_secret = client_secret
            conductor.sber_auth_key = auth_key
            conductor.sber_scope = scope
            if check.get('access_token'):
                conductor.sber_access_token = check.get('access_token')
            conductor.save(update_fields=['sber_client_id', 'sber_client_secret', 'sber_auth_key', 'sber_scope', 'sber_access_token'])

            return JsonResponse({
                "ok": True,
                "message": "Персональный ключ ИИ успешно привязан и проверен!",
                "expires_at": check.get('expires_at')
            })
        else:
            conductor.sber_client_id = ""
            conductor.sber_client_secret = ""
            conductor.sber_auth_key = None
            conductor.sber_access_token = None
            conductor.save(update_fields=['sber_client_id', 'sber_client_secret', 'sber_auth_key', 'sber_access_token'])
            return JsonResponse({
                "ok": True,
                "message": "Личный ключ диалогового ИИ удален из профиля."
            })


@csrf_exempt
@require_POST
def api_verify_sber_key(request):
    """
    Публичный API-эндпоинт для мгновенной верификации учетных данных платформы ИИ
    (раздельные Client ID и Client Secret, либо готовый Base64) на месте при вводе в форме регистрации проводника.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    client_id = (data.get('client_id') or data.get('sber_client_id') or '').strip()
    client_secret = (data.get('client_secret') or data.get('sber_client_secret') or '').strip()
    auth_key = (data.get('key') or data.get('sber_auth_key') or '').strip()
    scope = (data.get('scope') or 'GIGACHAT_API_PERS').strip()

    # Если переданы раздельные Client ID и Client Secret
    if client_id and client_secret:
        auth_key = base64.b64encode(f"{client_id}:{client_secret}".encode('utf-8')).decode('utf-8')
    elif not auth_key:
        if client_id and not client_secret:
            return JsonResponse({
                "ok": False,
                "error": "Указан Client ID, но не указан Client Secret. Пожалуйста, заполните оба поля."
            }, status=400)
        elif client_secret and not client_id:
            # Проверяем: вдруг пользователь вставил полный Base64 в поле Client Secret
            try:
                dec = base64.b64decode(client_secret).decode('utf-8', errors='ignore')
                if ':' in dec:
                    auth_key = client_secret
                    parts = dec.split(':', 1)
                    client_id = parts[0]
                    client_secret = parts[1]
                else:
                    return JsonResponse({
                        "ok": False,
                        "error": "Указан Client Secret, но не указан Client ID. Пожалуйста, введите оба значения."
                    }, status=400)
            except Exception:
                return JsonResponse({
                    "ok": False,
                    "error": "Указан Client Secret, но не указан Client ID. Пожалуйста, введите оба значения."
                }, status=400)
        else:
            return JsonResponse({
                "ok": False,
                "error": "Укажите Client ID и Client Secret из кабинета платформы ИИ."
            }, status=400)

    # Проверка формата Base64 перед отправкой в шлюз
    try:
        decoded = base64.b64decode(auth_key).decode('utf-8', errors='ignore')
        if ':' not in decoded:
            return JsonResponse({
                "ok": False,
                "error": "Неверный формат учетных данных. Убедитесь, что указаны корректные Client ID и Client Secret."
            }, status=400)
    except Exception:
        return JsonResponse({
            "ok": False,
            "error": "Ключ не является корректной строкой Base64."
        }, status=400)

    # Проверка через шлюз авторизации
    test_res = SberAIService.test_conductor_auth_key(auth_key, scope=scope)
    if test_res.get('ok'):
        expires_at = test_res.get('expires_at')
        expires_text = ""
        if expires_at:
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(expires_at / 1000.0, tz=datetime.timezone.utc)
                expires_text = dt.strftime('%H:%M:%S UTC')
            except Exception:
                pass
        return JsonResponse({
            "ok": True,
            "message": "Ключ успешно подтвержден шлюзом ИИ! Доступ к диалоговой модели активен.",
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_key": auth_key,
            "expires_at": expires_at,
            "expires_text": expires_text,
            "scope": test_res.get('scope')
        })
    else:
        return JsonResponse({
            "ok": False,
            "error": test_res.get('error', 'Ошибка верификации ключа шлюзом авторизации.')
        }, status=400)



