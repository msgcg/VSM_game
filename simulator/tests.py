import base64
import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import (
    Scenario,
    ScenarioNode,
    ScenarioChoice,
    TrainingSession,
    ConductorProfile,
    Competency,
    ConductorCompetencyScore,
    Achievement,
    ConductorAchievement,
    EndlessChallenge,
    EndlessShiftSession,
    RegulationDocument,
    Notification,
)


class VSMSimulatorTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Создаем компетенцию
        self.comp = Competency.objects.create(
            code="service_etiquette",
            title="Сервисный этикет ВСМ",
            description="Стандарты сервиса",
            color="#082a99"
        )

        # Создаем пользователя и профиль проводника
        self.user = User.objects.create_user(
            username="conductor_max",
            password="testpassword"
        )
        self.profile = ConductorProfile.objects.create(
            user=self.user,
            full_name="Максим Петров",
            badge_number="VSM-0101",
            rank="conductor",
            level=2,
            experience_points=600
        )
        ConductorCompetencyScore.objects.create(
            profile=self.profile,
            competency=self.comp,
            score=70
        )
        self.client.force_login(self.user)

        # Создаем сценарий и узлы
        self.scenario = Scenario.objects.create(
            slug="test-scenario",
            title="Тестовый сценарий ВСМ",
            category="conflict",
            difficulty="medium",
            train_speed=380,
            train_number="ЭВС2-01",
            location_name="Перегон Тверь — Валдай",
            car_info="Вагон № 2",
            description="Описание тестовой ситуации",
            briefing="Подробный брифинг",
            regulation_reference="Регламент ВСМ № 1"
        )

        self.node_start = ScenarioNode.objects.create(
            scenario=self.scenario,
            node_key="start",
            title="Начало ситуации",
            character_name="Пассажир 12А",
            character_role="Пассажир",
            dialogue_text="Я требую внимания!",
            time_limit_seconds=25,
            is_terminal=False
        )

        self.node_success = ScenarioNode.objects.create(
            scenario=self.scenario,
            node_key="success",
            title="Успешное разрешение",
            character_name="Пассажир 12А",
            character_role="Пассажир",
            dialogue_text="Спасибо за понимание.",
            time_limit_seconds=0,
            is_terminal=True,
            is_success=True,
            resolution_report="Отличная работа по регламенту."
        )

        self.node_fail = ScenarioNode.objects.create(
            scenario=self.scenario,
            node_key="fail",
            title="Провал ситуации",
            character_name="Пассажир 12А",
            character_role="Пассажир",
            dialogue_text="Я требую начальника поезда!",
            time_limit_seconds=0,
            is_terminal=True,
            is_success=False,
            resolution_report="Грубый отказ нарушил правила обслуживания пассажиров."
        )

        self.choice = ScenarioChoice.objects.create(
            node=self.node_start,
            choice_text="Вежливо предложить чай и объяснить правила",
            tactical_hint="Снижение напряжения",
            next_node_key="success",
            loyalty_impact=15,
            safety_impact=10,
            service_impact=20,
            stress_impact=-5,
            competency=self.comp,
            competency_points=25,
            feedback_toast="Пассажир успокоился!",
            audio_cue="success"
        )

        self.choice_fail = ScenarioChoice.objects.create(
            node=self.node_start,
            choice_text="Грубо указать на правила и пригрозить высадкой",
            tactical_hint="Эскалация конфликта",
            next_node_key="fail",
            loyalty_impact=-30,
            safety_impact=-20,
            service_impact=-30,
            stress_impact=30,
            competency=self.comp,
            competency_points=0,
            feedback_toast="Конфликт обострился!",
            audio_cue="warning"
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse('simulator:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Максим Петров")
        self.assertContains(response, "ВСМ-1")

    def test_scenario_list_view(self):
        response = self.client.get(reverse('simulator:scenario_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовый сценарий ВСМ")

    def test_scenario_detail_view(self):
        response = self.client.get(reverse('simulator:scenario_detail', kwargs={'slug': self.scenario.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Подробный брифинг")

    def test_simulation_workflow(self):
        # 1. Запуск сценария
        response = self.client.get(reverse('simulator:start_simulation', kwargs={'slug': self.scenario.slug}))
        self.assertEqual(response.status_code, 302)
        
        session = TrainingSession.objects.filter(conductor=self.profile, scenario=self.scenario).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'in_progress')

        # 2. Экран игры
        play_url = reverse('simulator:simulation_play', kwargs={'session_id': session.id})
        response = self.client.get(play_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Я требую внимания!")

        # 3. Выбор варианта решения через API
        api_url = reverse('simulator:api_choose_action', kwargs={'session_id': session.id})
        payload = json.dumps({'choice_id': self.choice.id})
        response = self.client.post(api_url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['is_terminal'])
        self.assertIn('/result/', data['redirect_url'])

        # 4. Проверка обновления состояния сессии
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertTrue(session.is_success)
        self.assertGreater(session.final_score, 0)
        self.assertGreater(session.earned_xp, 0)

        # 5. Экран результатов
        result_url = reverse('simulator:simulation_result', kwargs={'session_id': session.id})
        response = self.client.get(result_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "РЕЙС УСПЕШЕН")

    def test_leaderboard_view(self):
        response = self.client.get(reverse('simulator:leaderboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Рейтинг поездных бригад")

    def test_conductor_profile_view(self):
        response = self.client.get(reverse('simulator:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Квалификационный паспорт")
        self.assertContains(response, "VSM-0101")

    def test_regulations_view(self):
        response = self.client.get(reverse('simulator:regulations'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Справочник проводника")

    def test_endless_carousel_view(self):
        response = self.client.get(reverse('simulator:endless_carousel'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Карусель скоростных решений")
        self.assertContains(response, "Белый кречет")

    def test_endless_carousel_full_workflow(self):
        # Создаем тестовую задачу карусели
        challenge = EndlessChallenge.objects.create(
            code="test_endless_1",
            title="Тестовая задача карусели",
            difficulty_level=1,
            train_speed=250,
            situation_text="Пассажир предъявил билет с опечаткой",
            timer_seconds=20,
            regulation_reference="Правила перевозок п. 14",
            competency_code="service_etiquette",
            choices_data=[
                {
                    "text": "Допустить пассажира по регламенту (верно)",
                    "hint": "Телеграмма № 852",
                    "is_correct": True,
                    "loyalty_delta": 15,
                    "safety_delta": 10,
                    "service_delta": 15,
                    "stress_delta": -5,
                    "feedback": "Идеально по регламенту!"
                },
                {
                    "text": "Отказать в посадке (ошибка)",
                    "hint": "Грубое нарушение",
                    "is_correct": False,
                    "loyalty_delta": -25,
                    "safety_delta": -10,
                    "service_delta": -20,
                    "stress_delta": 25,
                    "feedback": "Грубая ошибка!"
                }
            ]
        )

        # 1. Запуск смены через API
        start_url = reverse('simulator:api_endless_start')
        resp = self.client.post(start_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        session_id = data['session_id']
        self.assertEqual(data['current_streak'], 0)
        self.assertEqual(data['multiplier'], 1.0)

        session = EndlessShiftSession.objects.get(id=session_id)
        self.assertEqual(session.status, 'active')

        # 2. Правильный выбор (индекс 0)
        choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': session_id})
        payload = json.dumps({
            'challenge_id': challenge.id,
            'choice_index': 0,
            'is_timeout': False
        })
        resp = self.client.post(choose_url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        choose_data = resp.json()
        self.assertTrue(choose_data['is_correct'])
        self.assertEqual(choose_data['stats']['current_streak'], 1)
        self.assertGreater(choose_data['stats']['total_score'], 0)
        self.assertGreaterEqual(choose_data['stats']['current_speed'], 250)

        # 3. Штатное завершение смены
        finish_url = reverse('simulator:api_endless_finish', kwargs={'session_id': session_id})
        resp = self.client.post(finish_url)
        self.assertEqual(resp.status_code, 200)
        finish_data = resp.json()
        self.assertTrue(finish_data['success'])
        self.assertEqual(finish_data['summary']['challenges_solved'], 1)

        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')

    def test_gamified_route_stations(self):
        """Проверка интерактивно-игрового маршрута ВСМ на дашборде"""
        response = self.client.get(reverse('simulator:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('route_progress', response.context)
        self.assertIn('stations_json', response.context)
        route_progress = response.context['route_progress']
        self.assertEqual(len(route_progress['stations']), 8)
        # Уровень профиля в setUp равен 2 -> Москва и Зеленоград открыты, остальные закрыты
        self.assertTrue(route_progress['stations'][0]['is_unlocked'])
        self.assertTrue(route_progress['stations'][1]['is_unlocked'])
        self.assertFalse(route_progress['stations'][2]['is_unlocked'])
        self.assertEqual(route_progress['current_station']['name'], 'Зеленоград')
        self.assertContains(response, 'vsm-station-modal')
        self.assertContains(response, 'vsm-stations-data')

    def test_document_library_and_reader(self):
        """Проверка скачивания первоисточников и API читалки регламентов"""
        # 1. API читалки для экзаменационных билетов
        reader_url = reverse('simulator:api_document_reader', kwargs={'doc_key': 'tickets_4_rank'})
        resp = self.client.get(reader_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('билеты', data['title'].lower())
        self.assertTrue(len(data['chapters']) > 0)

        # 2. Несуществующий документ
        bad_reader_url = reverse('simulator:api_document_reader', kwargs={'doc_key': 'non_existent_doc'})
        resp = self.client.get(bad_reader_url)
        self.assertEqual(resp.status_code, 404)

        # 3. Скачивание документа
        dl_url = reverse('simulator:download_document', kwargs={'doc_key': 'tickets_4_rank'})
        resp = self.client.get(dl_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_all_20_scenarios_seeded_and_functional(self):
        """Проверка создания и работоспособности 20 сценариев через management command"""
        from django.core.management import call_command
        call_command('seed_vsm_data')
        # 20 официальных сценариев ВСМ + 1 тестовый сценарий из setUp
        self.assertGreaterEqual(Scenario.objects.filter(is_active=True).exclude(slug="test-scenario").count(), 20)
        
        # Проверяем, что у каждого сценария есть стартовый узел и успешный терминальный узел
        for sc in Scenario.objects.all():
            start_node = ScenarioNode.objects.filter(scenario=sc, node_key='start').first()
            self.assertIsNotNone(start_node, f"Сценарий {sc.slug} не имеет start узла")
            self.assertGreater(start_node.choices.count(), 0, f"Узел start сценария {sc.slug} не имеет вариантов решений")
            success_node = ScenarioNode.objects.filter(scenario=sc, is_terminal=True, is_success=True).first()
            self.assertIsNotNone(success_node, f"Сценарий {sc.slug} не имеет success узла")

    def test_robots_txt(self):
        """Проверка поискового файла robots.txt"""
        response = self.client.get(reverse('simulator:robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('User-agent: *', content)
        self.assertIn('Allow: /', content)
        self.assertIn('Allow: /scenarios/', content)
        self.assertIn('Disallow: /admin/', content)
        self.assertIn('Disallow: /api/', content)
        self.assertIn('Disallow: /simulation/', content)
        self.assertIn('Sitemap:', content)
        self.assertIn('/sitemap.xml', content)

    def test_sitemap_xml(self):
        """Проверка генерации карты сайта sitemap.xml"""
        response = self.client.get(reverse('simulator:sitemap_xml'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/xml', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', content)
        self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', content)
        self.assertIn('/scenarios/', content)
        self.assertIn('/endless/', content)
        self.assertIn('/regulations/', content)
        self.assertIn('/leaderboard/', content)
        self.assertIn('/profile/', content)
        self.assertIn('/scenario/test-scenario/', content)

    def test_manifest_json(self):
        """Проверка PWA веб-манифеста manifest.json"""
        response = self.client.get(reverse('simulator:manifest_json'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/manifest+json', response['Content-Type'])
        data = response.json()
        self.assertEqual(data['name'], 'ВСМ-1 «Белый кречет» | Тренажер проводника')
        self.assertEqual(data['short_name'], 'ВСМ Тренажер')
        self.assertEqual(data['display'], 'standalone')
        self.assertEqual(data['theme_color'], '#082a99')
        self.assertEqual(data['background_color'], '#070c18')
        self.assertTrue(len(data['icons']) >= 2)
        self.assertTrue(len(data['shortcuts']) >= 3)

    def test_humans_txt(self):
        """Проверка файла humans.txt"""
        response = self.client.get(reverse('simulator:humans_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('/* TEAM */', content)
        self.assertIn('Maxim', content)
        self.assertIn('Белый кречет', content)
        self.assertIn('/* SPECIFICATION & STANDARDS */', content)

    def test_responsive_and_technical_metadata_in_templates(self):
        """Проверка наличия Open Graph, Twitter cards, PWA manifest и адаптивных классов"""
        response = self.client.get(reverse('simulator:dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Метатеги и PWA
        self.assertIn('rel="manifest"', content)
        self.assertIn('/manifest.json', content)
        self.assertIn('rel="canonical"', content)
        self.assertIn('property="og:title"', content)
        self.assertIn('property="og:image"', content)
        self.assertIn('name="twitter:card"', content)
        self.assertIn('viewport-fit=cover', content)

        # Адаптивные классы
        self.assertIn('vsm-dashboard-grid', content)
        self.assertIn('vsm-endless-cta', content)
        self.assertIn('vsm-station-params-grid', content)

    def test_registration_get(self):
        """Проверка отображения страницы регистрации проводника"""
        self.client.logout()
        response = self.client.get(reverse('simulator:register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertContains(response, "Регистрация проводника ВСМ")
        self.assertContains(response, "Кадровый реестр экипажей")

    def test_registration_post_success(self):
        """Проверка успешной регистрации проводника с созданием профиля в БД"""
        self.client.logout()
        payload = {
            'username': 'ivan_smirnov',
            'full_name': 'Смирнов Иван Алексеевич',
            'email': 'ivan@vsm.trans.ru',
            'depot': 'Санкт-Петербург Главный ВСМ',
            'avatar': 'avatar_2.svg',
            'password': 'superpassword123',
            'password_confirm': 'superpassword123',
        }
        response = self.client.post(reverse('simulator:register'), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('simulator:dashboard'))

        # Проверка создания в БД
        user = User.objects.filter(username='ivan_smirnov').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'ivan@vsm.trans.ru')

        profile = ConductorProfile.objects.filter(user=user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.full_name, 'Смирнов Иван Алексеевич')
        self.assertEqual(profile.depot, 'Санкт-Петербург Главный ВСМ')
        self.assertEqual(profile.avatar, 'avatar_2.svg')
        self.assertFalse(profile.is_example)
        self.assertTrue(profile.badge_number.startswith('VSM-'))

    def test_registration_validation_errors(self):
        """Проверка валидации формы регистрации: несовпадение паролей и дублирование логина"""
        self.client.logout()

        # 1. Несовпадение паролей
        mismatch_payload = {
            'username': 'mismatch_user',
            'full_name': 'Петров Петр Петрович',
            'depot': 'Москва-Октябрьская ВСМ',
            'avatar': 'avatar_1.svg',
            'password': 'password123',
            'password_confirm': 'different456',
        }
        response = self.client.post(reverse('simulator:register'), data=mismatch_payload)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('password_confirm', form.errors)
        self.assertIn("Пароли не совпадают", form.errors['password_confirm'][0])

        # 2. Дублирование логина
        duplicate_payload = {
            'username': 'conductor_max',  # Уже существует из setUp
            'full_name': 'Дубликат Пользователя',
            'depot': 'Москва-Октябрьская ВСМ',
            'avatar': 'avatar_1.svg',
            'password': 'password123',
            'password_confirm': 'password123',
        }
        response = self.client.post(reverse('simulator:register'), data=duplicate_payload)
        self.assertEqual(response.status_code, 200)
        dup_form = response.context['form']
        self.assertTrue(dup_form.errors)
        self.assertIn('username', dup_form.errors)
        self.assertIn("уже зарегистрирован", dup_form.errors['username'][0])

    def test_login_and_logout(self):
        """Проверка входа по логину/паролю и выхода из системы"""
        self.client.logout()

        # 1. Экран логина
        login_url = reverse('simulator:login')
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Авторизация проводника")

        # 2. Неверный пароль
        response = self.client.post(login_url, data={'username': 'conductor_max', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль проводника")

        # 3. Успешный вход
        response = self.client.post(login_url, data={'username': 'conductor_max', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('simulator:dashboard'))

        # 4. Выход из системы
        logout_url = reverse('simulator:logout')
        response = self.client.get(logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('simulator:login'))

    def test_register_with_sber_key(self):
        """Проверка регистрации проводника с личным ключом платформы ИИ"""
        self.client.logout()

        with patch('simulator.services.sber_service.SberAIService.test_conductor_auth_key') as mock_test:
            mock_test.return_value = {
                'ok': True,
                'access_token': 'mock_sber_access_token_reg',
                'expires_at': 1799999999
            }
            resp = self.client.post(reverse('simulator:register'), {
                'username': 'ivan_novikov',
                'full_name': 'Иван Новиков',
                'email': 'ivan.novikov@vsm.trans.ru',
                'depot': 'Москва-Октябрьская ВСМ',
                'avatar': 'avatar_1.svg',
                'password': 'strongpassword123',
                'password_confirm': 'strongpassword123',
                'sber_auth_key': 'MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY='
            })

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.url, reverse('simulator:dashboard'))

            new_user = User.objects.filter(username='ivan_novikov').first()
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.conductor_profile.sber_auth_key, 'MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=')
            self.assertEqual(new_user.conductor_profile.sber_access_token, 'mock_sber_access_token_reg')

    def test_register_with_sber_client_id_and_secret(self):
        """Проверка регистрации проводника с раздельными Client ID и Client Secret"""
        self.client.logout()
        with patch('simulator.services.sber_service.SberAIService.test_conductor_auth_key') as mock_test:
            mock_test.return_value = {
                'ok': True,
                'access_token': 'mock_sber_access_token_dual',
                'expires_at': 1799999999
            }
            client_id = "01a07215-cf66-7ec2-bf49-e602f1f833a6"
            client_secret = "fce0a0b0-a1d1-4c0b-9bf2-663a40a30efc"
            resp = self.client.post(reverse('simulator:register'), {
                'username': 'elena_morozova',
                'full_name': 'Елена Морозова',
                'email': 'elena.morozova@vsm.trans.ru',
                'depot': 'Москва-Октябрьская ВСМ',
                'avatar': 'avatar_2.svg',
                'password': 'strongpassword123',
                'password_confirm': 'strongpassword123',
                'sber_client_id': client_id,
                'sber_client_secret': client_secret
            })

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.url, reverse('simulator:dashboard'))

            user = User.objects.filter(username='elena_morozova').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.conductor_profile.sber_client_id, client_id)
            self.assertEqual(user.conductor_profile.sber_client_secret, client_secret)
            expected_auth_key = base64.b64encode(f"{client_id}:{client_secret}".encode('utf-8')).decode('utf-8')
            self.assertEqual(user.conductor_profile.sber_auth_key, expected_auth_key)
            self.assertEqual(user.conductor_profile.sber_access_token, 'mock_sber_access_token_dual')

    def test_leaderboard_db_accounts_and_filters(self):
        """Проверка выгрузки живых аккаунтов из базы данных в рейтинг и работы фильтров"""
        # Создаем зарегистрированного проводника
        reg_user = User.objects.create_user(username='reg_ann', password='pwd')
        reg_profile = ConductorProfile.objects.create(
            user=reg_user,
            full_name='Анна Чернова',
            badge_number='VSM-0044',
            depot='Санкт-Петербург Главный ВСМ',
            experience_points=1500,
            is_example=False
        )

        # Создаем тестового эталонного проводника
        ex_user = User.objects.create_user(username='ex_dmitry', password='pwd')
        ex_profile = ConductorProfile.objects.create(
            user=ex_user,
            full_name='Дмитрий Воронов',
            badge_number='VSM-0033',
            depot='Москва-Октябрьская ВСМ',
            experience_points=2500,
            is_example=True
        )

        # 1. Рейтинг по умолчанию (все)
        url = reverse('simulator:leaderboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        conductors = list(response.context['conductors'])
        conductor_names = [c.full_name for c in conductors]
        self.assertIn('Анна Чернова', conductor_names)
        self.assertIn('Дмитрий Воронов', conductor_names)
        self.assertContains(response, 'Тестовый эталон')
        self.assertContains(response, 'Аттестован')

        # 2. Фильтр только зарегистрированные
        resp_reg = self.client.get(url + '?type=registered')
        self.assertEqual(resp_reg.status_code, 200)
        reg_names = [c.full_name for c in resp_reg.context['conductors']]
        self.assertIn('Анна Чернова', reg_names)
        self.assertNotIn('Дмитрий Воронов', reg_names)

        # 3. Фильтр только тестовые эталоны
        resp_ex = self.client.get(url + '?type=example')
        self.assertEqual(resp_ex.status_code, 200)
        ex_names = [c.full_name for c in resp_ex.context['conductors']]
        self.assertIn('Дмитрий Воронов', ex_names)
        self.assertNotIn('Анна Чернова', ex_names)

        # 4. Фильтр по депо
        resp_spb = self.client.get(url + '?depot=Санкт-Петербург')
        self.assertEqual(resp_spb.status_code, 200)
        spb_names = [c.full_name for c in resp_spb.context['conductors']]
        self.assertIn('Анна Чернова', spb_names)
        self.assertNotIn('Дмитрий Воронов', spb_names)

    def test_all_scenarios_have_multiple_choices_and_fail_nodes(self):
        """Проверка: в каждом сценарии каждый нетерминальный узел имеет >= 2 выборов, и есть узел fail"""
        from django.core.management import call_command
        call_command('seed_vsm_data')

        for sc in Scenario.objects.all():
            non_terminal = sc.nodes.filter(is_terminal=False)
            self.assertGreater(non_terminal.count(), 0, f"Сценарий {sc.slug} не имеет нетерминальных узлов")
            for node in non_terminal:
                choices_count = node.choices.count()
                self.assertGreaterEqual(
                    choices_count, 2,
                    f"Узел '{node.node_key}' в сценарии '{sc.slug}' имеет только {choices_count} выбор(а)! Должно быть >= 2."
                )

            # Проверка наличия узла fail с разбором ошибок
            fail_node = sc.nodes.filter(is_terminal=True, is_success=False).first()
            self.assertIsNotNone(fail_node, f"В сценарии '{sc.slug}' отсутствует узел провала (fail)")
            self.assertTrue(bool(fail_node.resolution_report), f"В узле fail сценария '{sc.slug}' нет отчета resolution_report")

    def test_simulation_failure_modal_data(self):
        """Проверка: при ошибке/провале API возвращает is_fail=True и структурированные данные fail_info"""
        from django.core.management import call_command
        call_command('seed_vsm_data')

        sc = Scenario.objects.get(slug='business-class-conflict')
        session = TrainingSession.objects.create(
            conductor=self.profile,
            scenario=sc,
            current_node=sc.nodes.get(node_key='start')
        )

        # Выбираем заведомо провальный/грубый вариант
        bad_choice = session.current_node.choices.filter(next_node_key='fail').first()
        self.assertIsNotNone(bad_choice)

        api_url = reverse('simulator:api_choose_action', kwargs={'session_id': session.id})
        response = self.client.post(
            api_url,
            data=json.dumps({'choice_id': bad_choice.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['is_terminal'])
        self.assertFalse(data['is_success'])
        self.assertTrue(data['is_fail'])
        self.assertIn('fail_info', data)

        fail_info = data['fail_info']
        self.assertIn('title', fail_info)
        self.assertIn('action_taken', fail_info)
        self.assertIn('resolution_report', fail_info)
        self.assertIn('regulation_reference', fail_info)
        self.assertIn('recommended_approach', fail_info)
        self.assertIn('restart_url', fail_info)

    def test_endless_carousel_mistake_and_failure_feedback(self):
        """Проверка: при ошибке или таймауте в карусели API возвращает данные для окна разбора ошибки"""
        from django.core.management import call_command
        call_command('seed_vsm_data')

        # Запускаем бесконечную смену
        start_resp = self.client.post(reverse('simulator:api_endless_start'))
        self.assertEqual(start_resp.status_code, 200)
        session_id = start_resp.json()['session_id']

        challenge = EndlessChallenge.objects.first()
        self.assertIsNotNone(challenge)

        # Находим неверный ответ
        wrong_idx = next(i for i, c in enumerate(challenge.choices_data) if not c.get('is_correct'))

        choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': session_id})
        response = self.client.post(
            choose_url,
            data=json.dumps({'challenge_id': challenge.id, 'choice_index': wrong_idx, 'is_timeout': False}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data['is_correct'])
        self.assertIn('why_wrong', data)
        self.assertIn('correct_choice_text', data)
        self.assertIn('regulation', data)
        self.assertIn('challenge_title', data)

    def test_regulations_guide_button_and_reader_content(self):
        """Проверка: в базе регламентов кнопка читалки подписана 'Подробнее' и контент содержит форматирование"""
        url = reverse('simulator:regulations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Подробнее")
        self.assertNotContains(response, "Интерактивная читалка")

        # Проверка API читалки документов
        reader_url = reverse('simulator:api_document_reader', kwargs={'doc_key': 'tickets_4_rank'})
        resp_reader = self.client.get(reader_url)
        self.assertEqual(resp_reader.status_code, 200)
        data = resp_reader.json()
        self.assertTrue(data['success'])
        self.assertIn('#', data['content'])  # Markdown заголовки
        self.assertIn('Билет', data['content'])
        self.assertIn('pdf_url', data)

    def test_route_progress_alignment_and_track_fraction(self):
        """Проверка: полоса прогресса и рельсовая нить точно рассчитывают доли для соединения станций"""
        from simulator.views import get_gamified_stations

        # Уровень 1: открыта только Москва
        p1 = get_gamified_stations(1)
        self.assertEqual(p1['unlocked_count'], 1)
        self.assertEqual(p1['track_fraction'], 0.0)
        self.assertEqual(p1['station_percentage'], 12)

        # Уровень 4: открыто 4 станции (Москва, Зеленоград, Высоковск, Новая Тверь)
        p4 = get_gamified_stations(4)
        self.assertEqual(p4['unlocked_count'], 4)
        self.assertEqual(p4['total_count'], 8)
        self.assertEqual(p4['station_percentage'], 50)
        # Доля между станциями: (4 - 1) / (8 - 1) = 3/7 = 0.4286
        self.assertAlmostEqual(p4['track_fraction'], 3 / 7, places=3)
        self.assertEqual(p4['current_station']['name'], 'Новая Тверь')

        # Проверка рендера дашборда с новым расчетом
        self.profile.level = 4
        self.profile.save()
        resp = self.client.get(reverse('simulator:dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Открыто станций: <strong style=\"color: var(--vsm-cyan);\">4 из 8 (50%)</strong>")

    def test_station_scenarios_have_russian_titles(self):
        """Проверка: в сценариях станций выводятся русские названия, а не технические slug"""
        from simulator.views import get_gamified_stations
        progress = get_gamified_stations(5)
        st5 = next(s for s in progress['stations'] if s['id'] == 5)
        self.assertEqual(st5['name'], 'Логовежь')
        self.assertIn('scenarios_detail', st5)
        sc_details = st5['scenarios_detail']
        self.assertEqual(len(sc_details), 2)
        
        # Проверяем, что заголовки на русском языке
        titles = [sc['title'] for sc in sc_details]
        self.assertTrue(any('СКНБ' in t for t in titles))
        self.assertTrue(any('Земля' in t or 'Замыкание' in t for t in titles))
        # Проверяем, что нет сырых slug в заголовках
        self.assertNotIn('sknb-overheating-alarm', titles)
        self.assertNotIn('chassis-ground-fault', titles)

    def test_view_pdf_document_inline(self):
        """Проверка: внутрибраузерный просмотр PDF отдает корректный application/pdf с inline disposition"""
        pdf_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': 'tickets_4_rank'})
        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline', response['Content-Disposition'])

        # Проверка PDF руководства проводника (даже если файл не на диске, fallback гарантирует 200 OK)
        bolotin_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': 'bolotin'})
        response_b = self.client.get(bolotin_url)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b['Content-Type'], 'application/pdf')

    def test_document_views_graceful_when_file_missing(self):
        """Проверка: код не ломается и не выбрасывает 500, если файл отсутствует на диске"""
        from simulator.document_library import REGULATION_DOCUMENTS
        for doc_key in REGULATION_DOCUMENTS.keys():
            # API читалки всегда отдает 200 OK со структурированными главами
            api_url = reverse('simulator:api_document_reader', kwargs={'doc_key': doc_key})
            api_resp = self.client.get(api_url)
            self.assertEqual(api_resp.status_code, 200)
            data = api_resp.json()
            self.assertTrue(data['success'])
            self.assertIn('chapters', data)

            # Просмотр PDF отдает 200 OK
            pdf_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': doc_key})
            pdf_resp = self.client.get(pdf_url)
            self.assertEqual(pdf_resp.status_code, 200)
            self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')

            # Скачивание документа отдает 200 OK
            dl_url = reverse('simulator:download_document', kwargs={'doc_key': doc_key})
            dl_resp = self.client.get(dl_url)
            self.assertEqual(dl_resp.status_code, 200)

    def test_endless_session_sync_conductor_level_and_speed(self):
        """Проверка: уровень проводника и счетчик смен синхронизируются, скорость зависит от уровня"""
        self.profile.level = 4
        self.profile.shifts_completed = 3
        self.profile.perfect_shifts = 2
        self.profile.save()

        resp = self.client.post(reverse('simulator:api_endless_start'), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['shift_number'], 4)
        self.assertEqual(data['conductor_level'], 4)
        self.assertEqual(data['shifts_completed'], 3)
        self.assertEqual(data['perfect_shifts'], 2)
        # initial_speed = min(340, 240 + 4 * 15) = 300
        self.assertEqual(data['current_speed'], 300)

        # Убеждаемся, что уровень проводника в базе не сбросился
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.level, 4)

    def test_endless_sync_scenarios_and_challenges_bidirectional(self):
        """Проверка: задачи из сценариев появляются в карусели с флагом source_type='scenario'"""
        from simulator.views import sync_scenarios_and_challenges
        synced = sync_scenarios_and_challenges()
        self.assertGreater(synced, 0)

        scenario_challenges = EndlessChallenge.objects.filter(source_type='scenario')
        self.assertTrue(scenario_challenges.exists())
        sc_ch = scenario_challenges.first()
        self.assertIsNotNone(sc_ch.source_scenario)
        self.assertIn(sc_ch.source_scenario.title, sc_ch.title)

    def test_endless_shift_completion_flawless_increments_perfect_counter(self):
        """Проверка: безошибочное прохождение 8 станций сдает безупречную смену и увеличивает счетчик"""
        from simulator.views import sync_scenarios_and_challenges
        sync_scenarios_and_challenges()

        self.profile.shifts_completed = 1
        self.profile.perfect_shifts = 1
        self.profile.experience_points = 500
        self.profile.save()

        # Создаем тестовую задачу карусели с гарантированным правильным ответом
        ch = EndlessChallenge.objects.create(
            code="test_ch_flawless",
            title="Тестовая задача карусели",
            category="conflict",
            difficulty_level=2,
            train_speed=300,
            situation_text="Тест ситуация",
            choices_data=[
                {'index': 0, 'text': 'Правильный ответ', 'is_correct': True, 'loyalty_delta': 5, 'safety_delta': 5, 'feedback': 'Ок'},
                {'index': 1, 'text': 'Неверный ответ', 'is_correct': False, 'loyalty_delta': -10, 'safety_delta': -10, 'feedback': 'Ошибка'}
            ]
        )

        session = EndlessShiftSession.objects.create(
            conductor=self.profile,
            shift_number=2,
            target_challenges_count=8,
            challenges_solved=7,  # Предпоследний кейс
            mistakes_count=0,
            is_perfect=True,
            current_speed=300,
            current_loyalty=90,
            current_safety=90,
            current_service=90,
            current_stress=10,
            status='active'
        )

        choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': session.id})
        resp = self.client.post(
            choose_url,
            data=json.dumps({'challenge_id': ch.id, 'choice_index': 0, 'is_timeout': False}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['is_terminal'])
        self.assertTrue(data['is_shift_completed'])
        self.assertTrue(data['is_perfect'])
        self.assertEqual(data['mistakes_count'], 0)

        # Проверяем обновление проводника в базе:
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.shifts_completed, 2)
        self.assertEqual(self.profile.perfect_shifts, 2)  # Увеличился на 1!

    def test_endless_shift_completion_with_mistakes_does_not_increment_perfect(self):
        """Проверка: если была хотя бы 1 ошибка, смена засчитывается, но perfect_shifts не увеличивается"""
        self.profile.shifts_completed = 2
        self.profile.perfect_shifts = 1
        self.profile.save()

        ch = EndlessChallenge.objects.create(
            code="test_ch_mistake",
            title="Тестовая задача с ошибкой",
            category="conflict",
            difficulty_level=2,
            train_speed=300,
            situation_text="Тест ситуация",
            choices_data=[
                {'index': 0, 'text': 'Правильный ответ', 'is_correct': True, 'loyalty_delta': 5, 'safety_delta': 5, 'feedback': 'Ок'},
                {'index': 1, 'text': 'Неверный ответ', 'is_correct': False, 'loyalty_delta': -10, 'safety_delta': -10, 'feedback': 'Ошибка'}
            ]
        )

        session = EndlessShiftSession.objects.create(
            conductor=self.profile,
            shift_number=3,
            target_challenges_count=8,
            challenges_solved=7,
            mistakes_count=1,  # Была допущена ошибка ранее
            is_perfect=False,
            current_speed=280,
            current_loyalty=70,
            current_safety=85,
            current_service=75,
            current_stress=25,
            status='active'
        )

        choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': session.id})
        resp = self.client.post(
            choose_url,
            data=json.dumps({'challenge_id': ch.id, 'choice_index': 0, 'is_timeout': False}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['is_terminal'])
        self.assertTrue(data['is_shift_completed'])
        self.assertFalse(data['is_perfect'])
        self.assertEqual(data['mistakes_count'], 1)

        # Проверяем проводника в БД:
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.shifts_completed, 3)  # Смена завершена
        self.assertEqual(self.profile.perfect_shifts, 1)    # Безупречные смены не увеличились!

    def test_regulation_document_database_serving(self):
        """Проверка: документы отдаются напрямую из базы данных (SQLite) без чтения диска"""
        sample_pdf_base64 = (
            "JVBERi0xLjQKJcOkw7zDtsOfCjEgMCBvYmoKPDwvVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFI+Pgpl"
            "bmRvYmoKMiAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxPj4KZW5kb2Jq"
            "CjMgMCBvYmoKPDwvVHlwZSAvUGFnZQovUGFyZW50IDIgMCBSCi9NZWRpYUJveCBbMCAwIDMwMCAxNDRd"
            "Ci9Db250ZW50cyA0IDAgUj4+CmVuZG9iago0IDAgb2JqCjw8L0xlbmd0aCA0ND4+CnN0cmVhbQpCVAov"
            "RiAxMiBUZgoxMDAgMTAwIFRECltUZXN0XSBUSgpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA1CjAw"
            "MDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDYwIDAwMDAwIG4gCjAw"
            "MDAwMDAxMTEgMDAwMDAgbiAKMDAwMDAwMDIxMiAwMDAwMCBuIAp0cmFpbGVyCjw8L1NpemUgNQovUm9v"
            "dCAxIDAgUj4+CnN0YXJ0eHJlZgoyMDMKJSVFT0YK"
        )
        doc = RegulationDocument.objects.create(
            key="sto_test_doc",
            title="Тестовый регламент СТО ВСМ",
            subtitle="Распоряжение № 999-р",
            order_number="999-р",
            category="standard",
            description="Описание регламента для тестов",
            content_markdown="## Раздел 1. Введение",
            chapters_data=[{"title": "Раздел 1", "content": "Введение в норматив"}],
            file_base64=sample_pdf_base64,
            file_name="sto_test.pdf",
            file_size_display="120 КБ"
        )

        # 1. Просмотр PDF через iframe/вкладку
        pdf_url = reverse('simulator:view_pdf_document', kwargs={'doc_key': doc.key})
        resp = self.client.get(pdf_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        pdf_bytes = b"".join(resp.streaming_content)
        self.assertIn(b'%PDF', pdf_bytes)

        # 2. Скачивание PDF файла
        dl_url = reverse('simulator:download_document', kwargs={'doc_key': doc.key})
        resp_dl = self.client.get(dl_url)
        self.assertEqual(resp_dl.status_code, 200)
        self.assertEqual(resp_dl['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resp_dl['Content-Disposition'])
        dl_bytes = b"".join(resp_dl.streaming_content)
        self.assertIn(b'%PDF', dl_bytes)

        # 3. Интерактивная читалка
        reader_url = reverse('simulator:api_document_reader', kwargs={'doc_key': doc.key})
        resp_reader = self.client.get(reader_url)
        self.assertEqual(resp_reader.status_code, 200)
        data = resp_reader.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], doc.title)

    def test_api_v1_profile(self):
        """Проверка REST API v1: Профиль проводника"""
        url = reverse('simulator:api_v1_profile')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['profile']['badge_number'], "VSM-0101")
        self.assertEqual(data['profile']['full_name'], "Максим Петров")

    def test_api_v1_scenarios_and_detail(self):
        """Проверка REST API v1: Список сценариев и детальная информация"""
        # Каталог
        list_url = reverse('simulator:api_v1_scenarios')
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)

        # Детализация
        detail_url = reverse('simulator:api_v1_scenario_detail', kwargs={'slug': self.scenario.slug})
        resp_detail = self.client.get(detail_url)
        self.assertEqual(resp_detail.status_code, 200)
        det_data = resp_detail.json()
        self.assertTrue(det_data['success'])
        self.assertEqual(det_data['scenario']['slug'], self.scenario.slug)
        self.assertIsNotNone(det_data['scenario']['initial_node'])

    def test_api_v1_simulation_workflow_and_debrief(self):
        """Проверка REST API v1: Полный цикл симуляции, выбор решения и обучающий дебрифинг"""
        # Старт симуляции
        start_url = reverse('simulator:api_v1_simulation_start', kwargs={'slug': self.scenario.slug})
        resp = self.client.post(start_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        session_id = data['session_id']

        # Выбор ответа
        choose_url = reverse('simulator:api_v1_simulation_choose', kwargs={'session_id': session_id})
        resp_choose = self.client.post(
            choose_url,
            data=json.dumps({'choice_id': self.choice.id}),
            content_type='application/json'
        )
        self.assertEqual(resp_choose.status_code, 200)
        ch_data = resp_choose.json()
        self.assertTrue(ch_data['is_terminal'])
        self.assertTrue(ch_data['is_success'])

        # Получение обучающего дебрифинга по 4 шагам сервиса ВСМ
        debrief_url = reverse('simulator:api_v1_simulation_debrief', kwargs={'session_id': session_id})
        resp_debrief = self.client.get(debrief_url)
        self.assertEqual(resp_debrief.status_code, 200)
        deb_data = resp_debrief.json()
        self.assertTrue(deb_data['success'])
        self.assertIn('debrief', deb_data)
        self.assertIn('steps', deb_data['debrief'])
        self.assertEqual(len(deb_data['debrief']['steps']), 4)

    def test_api_v1_simulation_timeout(self):
        """Проверка REST API v1: Обработка истечения лимита времени (таймаута)"""
        start_url = reverse('simulator:api_v1_simulation_start', kwargs={'slug': self.scenario.slug})
        resp = self.client.post(start_url)
        session_id = resp.json()['session_id']

        timeout_url = reverse('simulator:api_v1_simulation_timeout', kwargs={'session_id': session_id})
        resp_to = self.client.post(timeout_url)
        self.assertEqual(resp_to.status_code, 200)
        to_data = resp_to.json()
        self.assertTrue(to_data['is_timeout'])

    def test_api_v1_notifications_and_read(self):
        """Проверка REST API v1: Получение уведомлений и отметка о прочтении"""
        notif = Notification.objects.create(
            conductor=self.profile,
            title="Сгорание баллов",
            message="Через 48 часов сгорят баллы лояльности!",
            notification_type="points_expiring"
        )

        notif_url = reverse('simulator:api_v1_notifications')
        resp = self.client.get(notif_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['unread_count'], 1)

        # Отметка отдельного уведомления как прочитанного
        resp_mark = self.client.post(
            notif_url,
            data=json.dumps({'id': notif.id}),
            content_type='application/json'
        )
        self.assertEqual(resp_mark.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # Отметка всех как прочитанных
        resp_all = self.client.post(
            notif_url,
            data=json.dumps({'all': True}),
            content_type='application/json'
        )
        self.assertEqual(resp_all.status_code, 200)

    def test_api_v1_analytics_and_matrix_view(self):
        """Проверка REST API v1 Аналитики и HTML-страницы матрицы компетенций"""
        # API
        api_url = reverse('simulator:api_v1_analytics')
        resp = self.client.get(api_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('radar', data)
        self.assertIn('strengths', data)

        # HTML View
        view_url = reverse('simulator:analytics')
        resp_view = self.client.get(view_url)
        self.assertEqual(resp_view.status_code, 200)
        self.assertContains(resp_view, "Матрица компетенций")
        self.assertContains(resp_view, "Радар готовности")

    def test_api_v1_leaderboard(self):
        """Проверка REST API v1: Лидерборд с фильтрацией"""
        url = reverse('simulator:api_v1_leaderboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['total'], 1)

    def test_api_v1_openapi_and_swagger_ui(self):
        """Проверка REST API v1: Спецификация OpenAPI 3.0.3 и интерфейс Swagger UI"""
        # OpenAPI JSON
        schema_url = reverse('simulator:api_v1_openapi')
        resp_schema = self.client.get(schema_url)
        self.assertEqual(resp_schema.status_code, 200)
        spec = resp_schema.json()
        self.assertEqual(spec['openapi'], '3.0.3')
        self.assertIn('/api/v1/profile/', spec['paths'])
        self.assertIn('/api/v1/scenarios/', spec['paths'])
        self.assertIn('/api/v1/simulation/start/{slug}/', spec['paths'])

        # Swagger UI HTML
        docs_url = reverse('simulator:swagger_ui')
        resp_docs = self.client.get(docs_url)
        self.assertEqual(resp_docs.status_code, 200)
        self.assertContains(resp_docs, "swagger-ui")

    def test_api_v1_openapi_full_coverage(self):
        """Проверка полноты спецификации OpenAPI: все 24 эндпоинта и 11 модулей платформы"""
        resp = self.client.get(reverse('simulator:api_v1_openapi'))
        self.assertEqual(resp.status_code, 200)
        spec = resp.json()
        expected_paths = [
            '/api/v1/profile/',
            '/api/v1/profile/reset/',
            '/api/v1/profile/training-track/',
            '/api/v1/crew/',
            '/api/v1/crew/add/{profile_id}/',
            '/api/v1/crew/remove/{profile_id}/',
            '/api/v1/scenarios/',
            '/api/v1/scenario/{slug}/',
            '/api/v1/simulation/start/{slug}/',
            '/api/v1/simulation/{session_id}/choose/',
            '/api/v1/simulation/{session_id}/timeout/',
            '/api/v1/simulation/{session_id}/debrief/',
            '/api/v1/carousel/start/',
            '/api/v1/carousel/{session_id}/choose/',
            '/api/v1/carousel/{session_id}/finish/',
            '/api/v1/carousel/{session_id}/state/',
            '/api/v1/regulations/',
            '/api/v1/regulations/{doc_key}/',
            '/api/v1/notifications/',
            '/api/v1/analytics/',
            '/api/v1/leaderboard/',
            '/api/v1/tts/',
            '/api/v1/tts/preload-list/',
            '/api/v1/live/turn/',
            '/api/v1/live/asr/',
            '/api/v1/live/tts/',
            '/api/v1/conductor/sber-credentials/',
            '/api/v1/sber/verify-key/',
        ]
        for p in expected_paths:
            self.assertIn(p, spec['paths'], f"Эндпоинт {p} отсутствует в OpenAPI спецификации")

    def test_api_v1_regulations_catalog_and_detail(self):
        """Проверка REST API v1: Каталог нормативной документации и детальная карточка регламента"""
        # 1. Каталог всех документов
        cat_url = reverse('simulator:api_v1_regulations')
        resp = self.client.get(cat_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)

        # 2. Поиск по названию
        resp_search = self.client.get(cat_url, {'q': 'учебник'})
        self.assertEqual(resp_search.status_code, 200)
        data_search = resp_search.json()
        self.assertTrue(data_search['success'])

        # 3. Детальная карточка документа (например, bolotin)
        detail_url = reverse('simulator:api_v1_regulation_detail', kwargs={'doc_key': 'bolotin'})
        resp_detail = self.client.get(detail_url)
        self.assertEqual(resp_detail.status_code, 200)
        detail_data = resp_detail.json()
        self.assertTrue(detail_data['success'])
        self.assertEqual(detail_data['key'], 'bolotin')
        self.assertIn('chapters', detail_data)

    def test_api_v1_carousel_rest_flow(self):
        """Проверка REST API v1: Полный цикл работы карусели через эндпоинты /api/v1/carousel/..."""
        # Создаем задачу для карусели
        challenge = EndlessChallenge.objects.create(
            code="test_carousel_ch_1",
            title="Тестовая ситуация карусели",
            character_name="Пассажир Сидоров",
            character_role="Пассажир эконома",
            dialogue_text="Подскажите, где кипяток?",
            situation_text="Пассажир обратился с вопросом о кипятке",
            choices_data=[
                {"text": "Показать кулер в начале вагона", "is_correct": True, "feedback": "Верно"},
                {"text": "Отказать", "is_correct": False, "feedback": "Нарушение стандарта"}
            ],
            difficulty_level=1,
            service_class="all"
        )

        # 1. Старт смены через /api/v1/carousel/start/
        start_url = reverse('simulator:api_v1_carousel_start')
        resp_start = self.client.post(start_url, json.dumps({'service_class': 'all', 'challenge_id': challenge.id}), content_type='application/json')
        self.assertEqual(resp_start.status_code, 200)
        data_start = resp_start.json()
        self.assertTrue(data_start['success'])
        session_id = data_start['session_id']

        # 2. Получение состояния через /api/v1/carousel/<session_id>/state/
        state_url = reverse('simulator:api_v1_carousel_state', kwargs={'session_id': session_id})
        resp_state = self.client.get(state_url)
        self.assertEqual(resp_state.status_code, 200)
        data_state = resp_state.json()
        self.assertTrue(data_state['success'])
        self.assertEqual(data_state['session_id'], session_id)

        # 3. Принятие решения через /api/v1/carousel/<session_id>/choose/
        choose_url = reverse('simulator:api_v1_carousel_choose', kwargs={'session_id': session_id})
        resp_choose = self.client.post(choose_url, json.dumps({'challenge_id': challenge.id, 'choice_index': 0}), content_type='application/json')
        self.assertEqual(resp_choose.status_code, 200)
        data_choose = resp_choose.json()
        self.assertTrue(data_choose['success'])

        # 4. Завершение смены через /api/v1/carousel/<session_id>/finish/
        finish_url = reverse('simulator:api_v1_carousel_finish', kwargs={'session_id': session_id})
        resp_finish = self.client.post(finish_url)
        self.assertEqual(resp_finish.status_code, 200)
        data_finish = resp_finish.json()
        self.assertTrue(data_finish['success'])
        self.assertTrue(data_finish['is_shift_completed'])

    def test_api_v1_profile_patch_update(self):
        """Проверка REST API v1: Обновление профиля проводника через PATCH /api/v1/profile/"""
        profile_url = reverse('simulator:api_v1_profile')
        patch_data = {
            'depot': 'Депо Москва-Октябрьская ВСМ',
            'brigade': 'Бригада №10',
            'training_track': 'business'
        }
        resp = self.client.patch(profile_url, json.dumps(patch_data), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['profile']['depot'], 'Депо Москва-Октябрьская ВСМ')
        self.assertEqual(data['profile']['brigade'], 'Бригада №10')
        self.assertEqual(data['profile']['training_track'], 'business')

    def test_api_v1_tts_preload_list(self):
        """Проверка REST API v1: Получение списка реплик для предзагрузки TTS"""
        url = reverse('simulator:api_v1_tts_preload_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('items', data)
        self.assertIn('total', data)

    def test_api_conductor_sber_credentials(self):
        """Проверка REST API v1: Управление ключами диалогового ИИ в профиле проводника"""
        url = reverse('simulator:api_conductor_sber_credentials')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('has_sber_id', data)
        self.assertIn('has_auth_key', data)

    def test_crew_management_and_synergy(self):
        """Проверка функционала поездного экипажа (добавление, удаление, синергия, взаимность)"""
        # Создаем второго проводника
        user2 = User.objects.create_user(username="crew_mate", password="password")
        profile2 = ConductorProfile.objects.create(
            user=user2,
            full_name="Елена Соколова",
            badge_number="VSM-0202",
            rank="senior_conductor",
            level=3,
            experience_points=1200,
            loyalty_rating=90.0,
            safety_rating=95.0,
            service_rating=92.0
        )

        # 1. Добавление в экипаж через web API
        add_url = reverse('simulator:api_crew_add', kwargs={'profile_id': profile2.id})
        resp = self.client.post(add_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['crew_count'], 1)

        # Взаимность (symmetrical)
        self.assertTrue(self.profile.is_in_crew(profile2))
        self.assertTrue(profile2.is_in_crew(self.profile))

        # Синергия экипажа
        synergy = self.profile.get_crew_synergy()
        self.assertGreater(synergy, 0)

        # Попытка добавить самого себя
        self_add_url = reverse('simulator:api_crew_add', kwargs={'profile_id': self.profile.id})
        resp_self = self.client.post(self_add_url)
        self.assertEqual(resp_self.status_code, 400)

        # 2. REST API v1 Экипажа
        api_crew_url = reverse('simulator:api_v1_crew')
        resp_v1 = self.client.get(api_crew_url)
        self.assertEqual(resp_v1.status_code, 200)
        v1_data = resp_v1.json()
        self.assertTrue(v1_data['success'])
        self.assertEqual(v1_data['crew_count'], 1)
        self.assertEqual(v1_data['crew_members'][0]['id'], profile2.id)

        # 3. Исключение из экипажа через web API
        remove_url = reverse('simulator:api_crew_remove', kwargs={'profile_id': profile2.id})
        resp_rem = self.client.post(remove_url)
        self.assertEqual(resp_rem.status_code, 200)
        rem_data = resp_rem.json()
        self.assertTrue(rem_data['success'])
        self.assertEqual(rem_data['crew_count'], 0)
        self.assertFalse(self.profile.is_in_crew(profile2))

        # 4. REST API v1 Добавление и удаление
        v1_add_url = reverse('simulator:api_v1_crew_add', kwargs={'profile_id': profile2.id})
        resp_v1_add = self.client.post(v1_add_url)
        self.assertEqual(resp_v1_add.status_code, 200)
        self.assertTrue(resp_v1_add.json()['success'])

        v1_rem_url = reverse('simulator:api_v1_crew_remove', kwargs={'profile_id': profile2.id})
        resp_v1_rem = self.client.post(v1_rem_url)
        self.assertEqual(resp_v1_rem.status_code, 200)
        self.assertTrue(resp_v1_rem.json()['success'])

    def test_account_data_reset(self):
        """Проверка сброса данных аккаунта и прогресса проводника"""
        # Начислим опыт, завершим сессию, добавим ачивку
        self.profile.add_xp(1500)
        self.assertGreater(self.profile.level, 2)

        ach = Achievement.objects.create(
            code="test_ach",
            title="Тестовая награда",
            description="Описание",
            badge_color="#10b981",
            xp_reward=100
        )
        ConductorAchievement.objects.create(profile=self.profile, achievement=ach)

        TrainingSession.objects.create(
            conductor=self.profile,
            scenario=self.scenario,
            current_node=self.node_start,
            status="finished",
            is_success=True
        )

        self.assertEqual(self.profile.sessions.count(), 1)
        self.assertEqual(self.profile.achievements.count(), 1)

        # Сброс через POST запрос
        reset_url = reverse('simulator:reset_account_data')
        resp = self.client.post(reset_url, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Проверяем, что прогресс обнулился
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.level, 1)
        self.assertEqual(self.profile.rank, 'trainee')
        self.assertEqual(self.profile.experience_points, 100)
        self.assertEqual(self.profile.sessions.count(), 0)
        self.assertEqual(self.profile.achievements.count(), 0)
        self.assertEqual(self.profile.competencies.first().score, 50)

        # Проверка REST API v1 сброса
        v1_reset_url = reverse('simulator:api_v1_profile_reset')
        resp_v1 = self.client.post(v1_reset_url)
        self.assertEqual(resp_v1.status_code, 200)
        self.assertTrue(resp_v1.json()['success'])

    def test_api_v1_tts_and_openapi(self):
        """Проверка REST API v1: Нейросетевой синтез речи (TTS) и наличие в OpenAPI спецификации"""
        tts_url = reverse('simulator:api_v1_tts')

        # 1. Пустой запрос должен возвращать 400
        resp_empty = self.client.get(tts_url, {'text': ''})
        self.assertEqual(resp_empty.status_code, 400)
        self.assertEqual(resp_empty.json()['code'], 'EMPTY_TEXT')

        # 2. Корректный запрос синтеза (потоковый in-memory синтез для живого чата)
        resp = self.client.get(tts_url, {
            'text': 'Поезд «Белый кречет» прибывает на станцию Тверь!',
            'voice': 'ru-RU-DmitryNeural',
            'rate': '+0%',
            'pitch': '+0Hz',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('audio_url', data)
        self.assertTrue(data['audio_url'].startswith('data:audio/mpeg;base64,') or data['audio_url'].endswith('.mp3'))
        self.assertEqual(data['voice'], 'ru-RU-DmitryNeural')
        self.assertFalse(data['cached'])

        # 3. Проверка присутствия /api/v1/tts/ в OpenAPI спецификации
        spec_url = reverse('simulator:api_v1_openapi')
        resp_spec = self.client.get(spec_url)
        self.assertEqual(resp_spec.status_code, 200)
        spec_json = resp_spec.json()
        self.assertIn('/api/v1/tts/', spec_json['paths'])

    def test_training_tracks_and_service_class_specialization(self):
        """Тестирование раздельных групп задач для обучения проводников эконом, комфорт и бизнес классов"""
        # 1. Проверяем бейджи классов у сценария и задачи карусели
        sc_badge = self.scenario.get_service_class_badge()
        self.assertIn('label', sc_badge)
        self.assertIn('code', sc_badge)
        self.assertIn('css_class', sc_badge)
        self.assertIn('icon', sc_badge)

        self.scenario.service_class = 'business'
        self.scenario.save()
        biz_badge = self.scenario.get_service_class_badge()
        self.assertEqual(biz_badge['code'], 'business')
        self.assertEqual(biz_badge['label'], 'Бизнес-класс')
        self.assertEqual(biz_badge['css_class'], 'vsm-badge-track-business')

        # 2. Проверяем get_track_progress в профиле проводника
        track_prog = self.profile.get_track_progress()
        self.assertIn('economy', track_prog)
        self.assertIn('comfort', track_prog)
        self.assertIn('business', track_prog)
        self.assertEqual(track_prog['business']['code'], 'business')
        self.assertIn('total', track_prog['business'])
        self.assertIn('passed', track_prog['business'])
        self.assertIn('percentage', track_prog['business'])
        self.assertIn('is_certified', track_prog['business'])

        # 3. API переключения специализации проводника
        track_api_url = reverse('simulator:api_v1_set_training_track')
        
        # 3a. Установка трека через JSON
        resp_set = self.client.post(
            track_api_url,
            data=json.dumps({'training_track': 'comfort'}),
            content_type='application/json'
        )
        self.assertEqual(resp_set.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.training_track, 'comfort')

        # 3b. Недопустимый трек возвращает 400
        resp_invalid = self.client.post(
            track_api_url,
            data=json.dumps({'training_track': 'super_vip'}),
            content_type='application/json'
        )
        self.assertEqual(resp_invalid.status_code, 400)

        # 4. Web-редирект смены специализации
        web_track_url = reverse('simulator:set_training_track_web', kwargs={'track': 'business'})
        resp_web = self.client.get(web_track_url)
        self.assertEqual(resp_web.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.training_track, 'business')

        # 5. Проверка фильтрации на пульте управления (Dashboard)
        dash_resp = self.client.get(reverse('simulator:dashboard') + '?track=business')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn('track_progress', dash_resp.context)
        self.assertIn('selected_track', dash_resp.context)
        self.assertEqual(dash_resp.context['selected_track'], 'business')

        # 6. Проверка фильтрации в каталоге сценариев (scenario_list)
        list_resp = self.client.get(reverse('simulator:scenario_list') + '?service_class=business')
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.context['service_class'], 'business')

        # 7. Запуск сессии карусели с указанием класса
        start_carousel_url = reverse('simulator:api_endless_start')
        resp_car = self.client.post(
            start_carousel_url,
            data=json.dumps({'service_class': 'comfort'}),
            content_type='application/json'
        )
        self.assertEqual(resp_car.status_code, 200)
        car_data = resp_car.json()
        self.assertTrue(car_data['success'])
        session_obj = EndlessShiftSession.objects.get(id=car_data['session_id'])
        self.assertEqual(session_obj.service_class, 'comfort')

        # 8. Проверка OpenAPI спецификации на наличие endpoints и параметров
        spec_url = reverse('simulator:api_v1_openapi')
        resp_spec = self.client.get(spec_url)
        spec_json = resp_spec.json()
        self.assertIn('/api/v1/profile/training-track/', spec_json['paths'])
        scenarios_get_params = spec_json['paths']['/api/v1/scenarios/']['get']['parameters']
        param_names = [p['name'] for p in scenarios_get_params]
        self.assertIn('service_class', param_names)


class SberAITests(TestCase):
    """Тестирование интеграции с сервисами AI: диалог, распознавание речи, озвучка и OAuth"""

    def setUp(self):
        from .services.sber_service import SberAIService
        self.sber_service = SberAIService
        self.user = User.objects.create_user(username='test_conductor_ai', password='password123')
        self.profile = ConductorProfile.objects.create(
            user=self.user,
            full_name='Тестовый Стюард ВСМ',
            rank='conductor',
            training_track='business'
        )
        self.scenario = Scenario.objects.create(
            title='Тестовый сценарий ВСМ',
            slug='test-vsm-scenario',
            description='Проверка генеративного диалога',
            regulation_reference='СТО ВСМ 03.011-2026',
            train_speed=360
        )
        self.session = TrainingSession.objects.create(
            conductor=self.profile,
            scenario=self.scenario,
            current_loyalty=80,
            current_safety=90,
            current_service=85,
            current_stress=25
        )

    def test_clean_text_for_tts(self):
        """Проверка очистки текста для озвучки (удаление ремарок в скобках и кавычек)"""
        raw_text = '«(громко плачет) Гражданин проводник! [кричит] Где мой багаж?»'
        cleaned = self.sber_service.clean_text_for_tts(raw_text)
        self.assertNotIn('(громко плачет)', cleaned)
        self.assertNotIn('[кричит]', cleaned)
        self.assertNotIn('«', cleaned)
        self.assertNotIn('»', cleaned)
        self.assertIn('Гражданин проводник!', cleaned)

    def test_sber_id_auth_url(self):
        """Проверка генерации URL авторизации OAuth 2.0"""
        with self.settings(SBER_ID_CLIENT_ID='test_client_id_vsm'):
            url = self.sber_service.get_sber_id_auth_url(state="vsm_test")
            self.assertIn("https://id.sber.ru/CSAFront/oidc/sberbank_id/authorize.do", url)
            self.assertIn("client_id=test_client_id_vsm", url)
            self.assertIn("state=vsm_test", url)

        with self.settings(SBER_ID_CLIENT_ID=''):
            url_fallback = self.sber_service.get_sber_id_auth_url()
            self.assertEqual(url_fallback, "https://developers.sber.ru/studio/")

    def test_api_live_turn_endpoint(self):
        """Проверка эндпоинта генеративного диалога /api/v1/live/turn/"""
        self.client.login(username='test_conductor_ai', password='password123')
        payload = {
            'session_id': self.session.id,
            'message': 'Добрый день! Позвольте проверить ваш билет по терминалу УКЭБ.',
            'action': 'ukeb_scan',
            'history': []
        }
        resp = self.client.post(
            reverse('simulator:api_live_turn'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('character_reply', data['data'])
        self.assertIn('current_loyalty', data['data'])
        self.assertIn('current_safety', data['data'])

        # Проверяем запись в лог сессии
        self.session.refresh_from_db()
        self.assertGreaterEqual(len(self.session.session_log), 1)

    def test_api_live_asr_endpoint(self):
        """Проверка эндпоинта голосового распознавания ASR /api/v1/live/asr/"""
        # Пустой запрос
        resp_empty = self.client.post(reverse('simulator:api_live_asr'))
        self.assertEqual(resp_empty.status_code, 400)

        # С фиктивным бинарным аудио
        dummy_audio = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00dummy_audio_stream"
        resp = self.client.post(
            reverse('simulator:api_live_asr'),
            data=dummy_audio,
            content_type='audio/ogg;codecs=opus'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('ok', data)

    def test_api_live_tts_endpoint(self):
        """Проверка эндпоинта речевого синтеза TTS /api/v1/live/tts/"""
        # Без текста
        resp_bad = self.client.get(reverse('simulator:api_live_tts'))
        self.assertEqual(resp_bad.status_code, 400)

        # С текстом
        resp = self.client.get(reverse('simulator:api_live_tts'), {'text': 'Внимание, скорый поезд прибывает на станцию Новая Тверь.'})
        # Возвращает либо сгенерированный аудиопоток (200), либо кэш
        self.assertIn(resp.status_code, [200, 500])

    @patch('simulator.services.sber_service.SberAIService.test_conductor_auth_key')
    def test_sber_id_login_flow(self, mock_test_key):
        """Проверка старта авторизации и привязки личного ключа AI"""
        mock_test_key.return_value = {
            'ok': True,
            'access_token': 'test_sber_access_token_login',
            'expires_at': 1799999999
        }
        self.client.login(username='test_conductor_ai', password='password123')
        resp = self.client.post(reverse('simulator:auth_sber_login'), {
            'sber_auth_key': 'mock_auth_key_123'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('simulator:dashboard'))

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sber_auth_key, 'mock_auth_key_123')
        self.assertEqual(self.profile.sber_access_token, 'test_sber_access_token_login')

    @patch('simulator.services.sber_service.SberAIService.test_conductor_auth_key')
    def test_sber_id_callback_flow(self, mock_test_key):
        """Проверка обмена кода авторизации OAuth на профиль проводника"""
        mock_test_key.return_value = {
            'ok': True,
            'access_token': 'test_sber_access_token_123',
            'expires_at': 1799999999
        }
        self.client.login(username='test_conductor_ai', password='password123')
        resp = self.client.get(reverse('simulator:auth_sber_callback'), {
            'sber_auth_key': 'test_auth_key_callback'
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('simulator:dashboard'))

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sber_auth_key, 'test_auth_key_callback')
        self.assertEqual(self.profile.sber_access_token, 'test_sber_access_token_123')

    def test_openapi_has_sber_endpoints(self):
        """Проверка отражения Live эндпоинтов AI в документации OpenAPI"""
        resp = self.client.get(reverse('simulator:api_v1_openapi'))
        self.assertEqual(resp.status_code, 200)
        spec = resp.json()
        self.assertIn('/api/v1/live/turn/', spec['paths'])
        self.assertIn('/api/v1/live/asr/', spec['paths'])
        self.assertIn('/api/v1/live/tts/', spec['paths'])

    def test_simulation_timeout_immediate_fail(self):
        """Проверка немедленного завершения сценария при первом же таймауте (без 5 штрафов)"""
        node_start = ScenarioNode.objects.create(
            scenario=self.scenario,
            node_key='start',
            title='Начало',
            character_name='Пассажир',
            character_role='Пассажир',
            dialogue_text='Внимание!',
            time_limit_seconds=20
        )
        self.session.current_node = node_start
        self.session.save()
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse('simulator:api_choose_action', args=[self.session.id]),
            data=json.dumps({'is_timeout': True}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('is_terminal'))
        self.assertTrue(data.get('is_fail'))
        self.assertTrue(data.get('is_timeout'))
        self.assertIn('fail_info', data)
        self.assertEqual(data['fail_info']['mistake_title'], 'Критическое промедление')
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'failed')
        self.assertFalse(self.session.is_success)

    @patch('simulator.services.sber_service.SberAIService.test_conductor_auth_key')
    def test_conductor_salutespeech_credentials_api(self, mock_test_key):
        """Проверка API управления персональным ключом речевого сервиса"""
        mock_test_key.return_value = {
            'ok': True,
            'access_token': 'test_salute_token_xyz',
            'expires_at': 1799999999,
            'scope': 'SALUTE_SPEECH_PERS'
        }
        self.client.force_login(self.user)

        # GET: проверяем наличие полей
        resp = self.client.get(reverse('simulator:api_conductor_sber_credentials'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('has_salutespeech_auth_key', data)
        self.assertFalse(data['has_salutespeech_auth_key'])

        # POST: привязка ключа речевого комплекса
        resp_post = self.client.post(
            reverse('simulator:api_conductor_sber_credentials'),
            data=json.dumps({'salutespeech_auth_key': 'salute_secret_key_base64'}),
            content_type='application/json'
        )
        self.assertEqual(resp_post.status_code, 200)
        post_data = resp_post.json()
        self.assertTrue(post_data.get('ok'))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.salutespeech_auth_key, 'salute_secret_key_base64')

    def test_endless_timeout_status(self):
        """Проверка возврата is_resolved: True и status: failed при таймауте в карусели решений"""
        self.client.force_login(self.user)
        challenge = EndlessChallenge.objects.create(
            title="Тестовый вызов",
            category="conflict",
            difficulty_level=2,
            character_role="Пассажир",
            character_name="Пассажир",
            situation_text="Тестовая ситуация",
            choices_data=[
                {'text': 'Правильный выбор', 'is_correct': True, 'hint': 'Верно'}
            ]
        )
        endless_session = EndlessShiftSession.objects.create(
            conductor=self.profile,
            status='active'
        )
        resp = self.client.post(
            reverse('simulator:api_endless_choose', args=[endless_session.id]),
            data=json.dumps({'challenge_id': challenge.id, 'is_timeout': True}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('is_timeout'))
        self.assertTrue(data.get('is_resolved'))
        self.assertEqual(data.get('status'), 'failed')
        self.assertFalse(data.get('is_correct'))

    def test_service_worker_endpoint(self):
        """Проверка: PWA Service Worker доступен по корневому адресу /sw.js"""
        resp = self.client.get('/sw.js')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/javascript', resp['Content-Type'])
        self.assertEqual(resp.get('Service-Worker-Allowed'), '/')
        self.assertIn('vsm-krechet', resp.content.decode('utf-8'))

    def test_whisper_service_cross_platform(self):
        """Проверка универсального сервиса Whisper (бинарник, модель, безопасная деградация)"""
        from simulator.services.whisper_service import WhisperVulkanService

        # Проверка безопасного вызова методов обнаружения
        bin_path = WhisperVulkanService.get_bin_path()
        model_path = WhisperVulkanService.get_model_path()
        is_avail = WhisperVulkanService.is_available()

        self.assertIsInstance(is_avail, bool)

        # Проверка обработки пустого аудио
        empty_res = WhisperVulkanService.transcribe(b"")
        self.assertFalse(empty_res["ok"])
        self.assertIn("error", empty_res)

    def test_equipment_actions_without_conductor_comment(self):
        """Проверка: применение оборудования вагона без словесного комментария проводника вызывает реакцию системы и персонажа"""
        # 1. Проверка live_turn с пустым сообщением и действием
        session = self.session

        actions = [
            'tea_service',
            'electric_panel',
            'driver_intercom',
            'fire_extinguisher',
            'aed_medkit',
            'ukeb_scan',
            'emergency_brake',
            'glass_hammer'
        ]

        for act in actions:
            res = self.sber_service.generate_live_turn(
                scenario=self.scenario,
                session=session,
                conductor_message="",
                conductor_action=act
            )
            self.assertIn('character_reply', res)
            self.assertTrue(len(res['character_reply']) > 0, f"Empty reply for action {act}")
            self.assertIn('system_event', res)
            self.assertTrue(len(res['system_event']) > 0, f"Empty system_event for action {act}")

        # 2. Проверка endless fallback для всех 8 типов оборудования
        challenge = EndlessChallenge.objects.create(
            title="Тестовая неисправность климата",
            situation_text="В вагоне сработала сигнализация СКНБ и отключился климат",
            service_class="all",
            character_name="Пассажир",
            character_role="Пассажир",
            difficulty_level=1,
            choices_data=[
                {"text": "Проверить электрощит", "hint": "СТО ВСМ", "is_correct": True}
            ]
        )

        for act in actions:
            fallback_res = self.sber_service._fallback_endless_eval(challenge, message="", action=act)
            self.assertIn('character_reply', fallback_res)
            self.assertTrue(len(fallback_res['character_reply']) > 0, f"Empty fallback reply for {act}")
            self.assertIn('system_notice', fallback_res)
            self.assertTrue(len(fallback_res['system_notice']) > 0, f"Empty system_notice for {act}")
            self.assertIn(fallback_res.get('status'), ['resolved', 'in_progress', 'failed'])

        # 3. Проверка эндпоинта api_live_turn с оборудованием без слов проводника
        live_turn_url = reverse('simulator:api_live_turn')
        resp_live = self.client.post(
            live_turn_url,
            data=json.dumps({
                'session_id': self.session.id,
                'message': '',
                'action': 'electric_panel'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp_live.status_code, 200)
        live_json = resp_live.json()
        self.assertTrue(live_json.get('ok'))
        self.assertIn('data', live_json)
        self.assertTrue(len(live_json['data'].get('character_reply', '')) > 0)

        # 4. Проверка эндпоинта api_endless_choose с оборудованием без слов проводника
        car_session = EndlessShiftSession.objects.create(
            conductor=self.profile,
            service_class="all",
            current_speed=360,
            status="active"
        )
        endless_choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': car_session.id})
        self.client.login(username='test_conductor_ai', password='password123')
        resp_endless = self.client.post(
            endless_choose_url,
            data=json.dumps({
                'challenge_id': challenge.id,
                'message': '',
                'action': 'electric_panel',
                'action_title': 'Осмотр электрощита и СКНБ'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp_endless.status_code, 200)
        endless_json = resp_endless.json()
        self.assertIn('character_reply', endless_json)
        self.assertTrue(len(endless_json['character_reply']) > 0)
        self.assertIn('Осмотр электрощита', endless_json.get('selected_choice_text', ''))

    def test_touch_dnd_clean_db_and_situations_document(self):
        """Проверка: документ Ситуации на борту, отсутствие слова 'справа' и чистота БД"""
        from simulator.document_library import REGULATION_DOCUMENTS
        from django.core.management import call_command

        # 1. Проверка наличия 'onboard_situations' в словаре регламентов
        self.assertIn('onboard_situations', REGULATION_DOCUMENTS)
        self.assertIn('onboard_situations_guide', REGULATION_DOCUMENTS)
        doc_info = REGULATION_DOCUMENTS['onboard_situations']
        self.assertEqual(doc_info['filename'], 'VSM_Onboard_Situations_Guide.pdf')
        self.assertTrue(len(doc_info['chapters']) >= 5)

        # 2. Проверка отображения в представлении simulation_play: нет слова 'справа' в drop target
        node = ScenarioNode.objects.create(
            scenario=self.scenario,
            node_key='test_node_touch',
            title='Тестовый узел',
            dialogue_text='Здравствуйте, проводник!'
        )
        self.session.current_node = node
        self.session.save()
        self.client.login(username='test_conductor_ai', password='password123')
        play_url = reverse('simulator:simulation_play', kwargs={'session_id': self.session.id})
        resp_play = self.client.get(play_url)
        self.assertEqual(resp_play.status_code, 200)
        content_html = resp_play.content.decode('utf-8')
        self.assertIn('id="vsm-drop-target-text"', content_html)
        self.assertNotIn('кликните по оборудованию справа', content_html)
        self.assertIn('кликните по оборудованию', content_html)
        self.assertIn('id="vsm-car-temp"', content_html)
        self.assertIn('id="vsm-car-clock"', content_html)

        # 3. Проверка команды purge_personal_data
        call_command('purge_personal_data')
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(ConductorProfile.objects.count(), 0)

    def test_endless_streak_multiplier_and_score_progression(self):
        """Проверка: серия решений растет, множитель увеличивается, счет и опыт накапливаются без преждевременного сброса смены"""
        self.client.login(username='test_conductor_ai', password='password123')

        ch1 = EndlessChallenge.objects.create(
            code="test_streak_1",
            title="Тестовая задача 1",
            category="service",
            difficulty_level=1,
            choices_data=[
                {'text': 'Верное действие 1', 'is_correct': True, 'hint': 'Регламент'},
                {'text': 'Неверное действие 1', 'is_correct': False, 'hint': 'Ошибка'}
            ]
        )
        ch2 = EndlessChallenge.objects.create(
            code="test_streak_2",
            title="Тестовая задача 2",
            category="service",
            difficulty_level=2,
            choices_data=[
                {'text': 'Верное действие 2', 'is_correct': True, 'hint': 'Регламент'},
                {'text': 'Неверное действие 2', 'is_correct': False, 'hint': 'Ошибка'}
            ]
        )

        session = EndlessShiftSession.objects.create(
            conductor=self.profile,
            shift_number=5,
            target_challenges_count=8,
            current_speed=260,
            current_streak=0,
            total_score=0,
            earned_xp=0,
            status='active'
        )

        choose_url = reverse('simulator:api_endless_choose', kwargs={'session_id': session.id})

        # 1. Первый верный ответ: стрик становится 1, множитель x1.2, счет и опыт начисляются, смена продолжается
        resp1 = self.client.post(
            choose_url,
            data=json.dumps({'challenge_id': ch1.id, 'choice_index': 0}),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 200)
        d1 = resp1.json()
        self.assertFalse(d1.get('is_terminal'))
        self.assertTrue(d1.get('is_resolved'))
        self.assertEqual(d1['stats']['current_streak'], 1)
        self.assertEqual(d1['stats']['multiplier'], 1.2)
        self.assertEqual(d1['stats']['total_score'], 120)
        self.assertEqual(d1['stats']['earned_xp'], 48)

        # 2. Второй верный ответ: стрик становится 2, счет увеличивается
        resp2 = self.client.post(
            choose_url,
            data=json.dumps({'challenge_id': ch2.id, 'choice_index': 0}),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.json()
        self.assertFalse(d2.get('is_terminal'))
        self.assertEqual(d2['stats']['current_streak'], 2)
        self.assertEqual(d2['stats']['multiplier'], 1.2)
        self.assertEqual(d2['stats']['earned_xp'], 48 + int(int(200 * 1.2) * 0.4))


class LoginAuthenticationSecurityTests(TestCase):
    """
    Тестирование безопасности авторизации:
    Ввод логина проверяет исключительно наличие проводника в БД и никогда не регистрирует его автоматически.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='registered_conductor',
            password='SecretPassword123!',
            first_name='Алексей',
            last_name='Иванов'
        )
        self.profile = ConductorProfile.objects.create(
            user=self.user,
            full_name='Иванов Алексей Сергеевич',
            badge_number='ВСМ-77701',
            rank='conductor_1',
            level=2
        )

    def test_login_unregistered_username_does_not_create_user_or_profile(self):
        """Попытка входа с несуществующим логином не должна создавать пользователя в БД"""
        initial_user_count = User.objects.count()
        initial_profile_count = ConductorProfile.objects.count()
        unregistered_login = "unknown_stranger_user"

        response = self.client.post(reverse('simulator:login'), {
            'username': unregistered_login,
            'password': 'AnyRandomPassword999!',
        })

        # Пользователь не создается
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(ConductorProfile.objects.count(), initial_profile_count)
        self.assertFalse(User.objects.filter(username=unregistered_login).exists())
        self.assertFalse(ConductorProfile.objects.filter(badge_number=unregistered_login).exists())

        # Возвращается страница входа с сообщением об ошибке
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "не найден в реестре экипажей ВСМ")

    def test_login_existing_conductor_by_username_succeeds(self):
        """Зарегистрированный проводник успешно входит по своему username"""
        response = self.client.post(reverse('simulator:login'), {
            'username': 'registered_conductor',
            'password': 'SecretPassword123!',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'registered_conductor')

    def test_login_existing_conductor_by_badge_number_succeeds(self):
        """Зарегистрированный проводник успешно входит по табельному номеру"""
        response = self.client.post(reverse('simulator:login'), {
            'username': 'ВСМ-77701',
            'password': 'SecretPassword123!',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'registered_conductor')

    def test_login_wrong_password_does_not_authenticate(self):
        """Неверный пароль не позволяет войти и возвращает соответствующую ошибку"""
        response = self.client.post(reverse('simulator:login'), {
            'username': 'registered_conductor',
            'password': 'WrongPassword!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный пароль")

