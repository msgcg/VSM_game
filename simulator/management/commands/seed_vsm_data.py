import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from simulator.models import (
    Competency,
    ConductorProfile,
    ConductorCompetencyScore,
    Achievement,
    ConductorAchievement,
    Scenario,
    ScenarioNode,
    ScenarioChoice,
    TrainingSession,
    EndlessChallenge,
    EndlessShiftSession,
)


class Command(BaseCommand):
    help = "Инициализация расширенной базы данных ВСМ: 12 сценариев, 20 задач бесконечной карусели, достижения"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Начало наполнения расширенной базы данных ВСМ..."))

        # 1. Компетенции
        competencies_data = [
            {
                "code": "service_etiquette",
                "title": "Сервисный этикет и клиентоориентированность ВСМ",
                "description": "Премиальные стандарты обслуживания 'Белый кречет': вежливость, эмпатия, упреждающий сервис, работа с VIP-пассажирами первого и бизнес-классов.",
                "icon": "sparkles",
                "color": "#1c6389",
            },
            {
                "code": "safety_regulations",
                "title": "Безопасность и нормативные регламенты ВСМ (400 км/ч)",
                "description": "Правила технической эксплуатации (ПТЭ), пожарная безопасность (СПАС-ВО), запреты срыва стоп-кранов на мостах и тоннелях ВСМ.",
                "icon": "shield-check",
                "color": "#082a99",
            },
            {
                "code": "conflict_resolution",
                "title": "Стрессоустойчивость и конфликтология",
                "description": "Навыки мгновенной деэскалации споров между пассажирами, управление стрессом в замкнутом пространстве на высокой скорости.",
                "icon": "message-circle-heart",
                "color": "#eab308",
            },
            {
                "code": "emergency_medical",
                "title": "Первая доврачебная помощь и экстренный протокол",
                "description": "Алгоритмы сердечно-легочной реанимации, применение АНД, купирование приступов, взаимодействие с ЛНП и вызов скорой помощи к перрону.",
                "icon": "heart-pulse",
                "color": "#ef4444",
            },
            {
                "code": "vsm_tech_protocols",
                "title": "Эксплуатация систем поезда «Белый кречет»",
                "description": "Управление климатическими установками, электрооборудованием, радиосвязью, СКНБ, терминалами мобильного контроля и сервисными зонами.",
                "icon": "cpu",
                "color": "#06b6d4",
            },
        ]

        comp_objects = {}
        for c in competencies_data:
            obj, _ = Competency.objects.update_or_create(
                code=c["code"],
                defaults={
                    "title": c["title"],
                    "description": c["description"],
                    "icon": c["icon"],
                    "color": c["color"],
                }
            )
            comp_objects[c["code"]] = obj

        # 2. Достижения (Ачивки)
        achievements_data = [
            {
                "code": "first_shift",
                "title": "Первый высокоскоростной рейс",
                "description": "Успешно пройдите свой первый обучающий сценарий на магистрали ВСМ-1.",
                "icon_name": "train-front",
                "badge_color": "#1c6389",
                "xp_reward": 150,
                "rarity": "common",
            },
            {
                "code": "diplomat_master",
                "title": "Мастер дипломатии 400 км/ч",
                "description": "Урегулируйте острый конфликт в Бизнес-классе с сохранением лояльности пассажира выше 90%.",
                "icon_name": "award",
                "badge_color": "#082a99",
                "xp_reward": 300,
                "rarity": "rare",
            },
            {
                "code": "golden_hour_saver",
                "title": "Специалист неотложной помощи",
                "description": "Безупречно окажите неотложную доврачебную помощь до прибытия скорой помощи на станцию.",
                "icon_name": "heart-handshake",
                "badge_color": "#ef4444",
                "xp_reward": 450,
                "rarity": "epic",
            },
            {
                "code": "spas_sentinel",
                "title": "Страж СПАС-ВО",
                "description": "Ликвидируйте угрозу задымления по нормативу за 30 секунд без паники и ложной остановки поезда.",
                "icon_name": "flame-kindling",
                "badge_color": "#f97316",
                "xp_reward": 350,
                "rarity": "rare",
            },
            {
                "code": "anti_terror_shield",
                "title": "Антитеррористический щит",
                "description": "Проявите идеальную бдительность при обнаружении бесхозного предмета в вагоне-бистро.",
                "icon_name": "shield-alert",
                "badge_color": "#8b5cf6",
                "xp_reward": 400,
                "rarity": "epic",
            },
            {
                "code": "perfect_service",
                "title": "Безупречный сервис «Белый кречет»",
                "description": "Завершите смену со 100% показателем безопасности и 95%+ лояльности пассажиров.",
                "icon_name": "crown",
                "badge_color": "#eab308",
                "xp_reward": 500,
                "rarity": "legendary",
            },
            {
                "code": "carousel_streak_10",
                "title": "Марафонец бесконечной смены",
                "description": "Наберите серию из 10 правильных решений подряд в режиме «Бесконечная карусель решений».",
                "icon_name": "flame",
                "badge_color": "#ec4899",
                "xp_reward": 600,
                "rarity": "legendary",
            },
        ]

        achieve_objects = {}
        for a in achievements_data:
            obj, _ = Achievement.objects.update_or_create(
                code=a["code"],
                defaults=a
            )
            achieve_objects[a["code"]] = obj

        # 3. Пользователи и Профили проводников
        # Проводники регистрируются индивидуально со своими ключами доступа к сервисам ИИ
        conductors_data = []

        for cd in conductors_data:
            user, created = User.objects.get_or_create(
                username=cd["username"],
                defaults={
                    "first_name": cd["full_name"].split()[0],
                    "last_name": cd["full_name"].split()[1],
                    "email": f"{cd['username']}@vsm.trans.ru",
                }
            )
            if created or not user.has_usable_password():
                user.set_password("vsm2026pass")
                user.save()

            profile, _ = ConductorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "full_name": cd["full_name"],
                    "badge_number": cd["badge"],
                    "depot": cd["depot"],
                    "rank": cd["rank"],
                    "level": cd["level"],
                    "experience_points": cd["xp"],
                    "loyalty_rating": cd["loyalty"],
                    "safety_rating": cd["safety"],
                    "service_rating": cd["service"],
                    "shifts_completed": cd["shifts"],
                    "perfect_shifts": cd["perfect"],
                    "avatar": cd["avatar"],
                    "is_example": True,
                }
            )

            for ach_code in cd["achievements"]:
                if ach_code in achieve_objects:
                    ConductorAchievement.objects.get_or_create(
                        profile=profile,
                        achievement=achieve_objects[ach_code]
                    )

            for c_code, score in cd["comp_scores"].items():
                if c_code in comp_objects:
                    ConductorCompetencyScore.objects.update_or_create(
                        profile=profile,
                        competency=comp_objects[c_code],
                        defaults={"score": score}
                    )

        # 4. Создаем 20 полных нелинейных сценариев
        self.create_all_20_scenarios(comp_objects)

        # 5. Создаем 20 задач для карусели бесконечных решений
        self.create_endless_challenges()

        self.stdout.write(self.style.SUCCESS("Расширенная база ВСМ (20 сценариев + 20 задач карусели) успешно загружена!"))

    def create_all_20_scenarios(self, comp):
        """Создание 20 разветвленных сценариев на основе официальных отраслевых регламентов ВСМ и учебных пособий"""
        scenarios_catalog = [
            # 1
            ("business-class-conflict", "Инцидент в Бизнес-классе на 380 км/ч: Самовольная пересадка", "conflict", "medium", 380, "Вагон № 2 (Бизнес-класс)", "Пассажир с билетом комфорт-класса самовольно занял кресло в бизнес-классе и шумит.", "sc_business_conflict.jpg", 300, 25, 1),
            # 2
            ("cardiac-emergency", "Медицинская тревога: Сердечный приступ на 360 км/ч", "medical", "extreme", 360, "Вагон № 6 (Комфорт-класс)", "Пассажир без сознания на перегоне Валдай — Выползово. Протокол АНД.", "sc_cardiac_emergency.jpg", 450, 18, 2),
            # 3
            ("toilet-smoke-alarm", "Тревога СПАС-ВО: Дым в туалетном модуле на 400 км/ч", "safety", "hard", 400, "Вагон № 4 (Стандарт-класс)", "Сработал оптический датчик дыма на мосту через Тверцу. Запрет срыва стоп-крана.", "sc_smoke_alarm.jpg", 350, 20, 3),
            # 4
            ("unattended-briefcase", "Антитеррористический регламент: Подозрительный кейс в Бистро", "anti_terror", "hard", 370, "Вагон № 5 (Вагон-бистро)", "Под столиком оставлен темный кейс с проводом и светодиодом. Правило: не трогать!", "sc_unattended_bag.jpg", 350, 25, 4),
            # 5
            ("pet-allergy-crisis", "Конфликт пассажиров: Экзотический питомец и острая аллергия", "conflict", "medium", 350, "Вагон № 3 (Комфорт-класс)", "Хорёк без переноски и развивающийся отек Квинке у соседа. Медиация и правила.", "sc_pet_carrier.jpg", 280, 25, 5),
            # 6
            ("ac-failure-heatwave", "Технический сбой: Отказ климат-контроля при +33°C за бортом", "tech_failure", "medium", 390, "Вагон № 7 (Стандарт-класс)", "Отказ кондиционера в жару. Запрет выбивания герметичных окон ВСМ, резервный обдув.", "vsm_train_equipment.jpg", 300, 25, 6),
            # 7
            ("overbooking-seat-conflict", "Двойная продажа (Овербукинг) места на скорости 390 км/ч", "conflict", "medium", 390, "Вагон № 3 (Комфорт-класс)", "На кресло 14Б претендуют двое пассажиров с подлинными электронными билетами. Регламент: апгрейд без доплаты!", "vsm_classes_schemes.jpg", 320, 22, 7),
            # 8
            ("passenger-missed-train", "Пассажир отстал от поезда на 1-минутной стоянке", "conflict", "hard", 380, "Вагон № 4 (Стандарт-класс)", "Пассажир вышел за кофе на станции Тверь, двери заперты. В купе остался плачущий ребенок и багаж.", "sc_platform_boarding.jpg", 360, 20, 8),
            # 9
            ("sknb-overheating-alarm", "Срабатывание СКНБ: Аварийный перегрев букс на 400 км/ч", "safety", "extreme", 400, "Вагон № 5 (Бистро / Тележка)", "Зуммер СКНБ сигнализирует перегрев буксового узла. Угроза излома оси на 400 км/ч.", "sc_sknb_sensor.jpg", 460, 15, 9),
            # 10
            ("chassis-ground-fault", "Замыкание электрооборудования на корпус вагона", "tech_failure", "hard", 370, "Вагон № 1 (Первый класс)", "Лампа 'минус на корпус' в цепи 110/3000 В. Опасность шагового напряжения и пожара щита.", "sc_ground_fault.jpg", 340, 20, 10),
            # 11
            ("ticket-typo-conflict", "Опечатка в билете: Разногласие в паспорте VIP-пассажира", "vip_service", "easy", 320, "Вагон № 2 (Бизнес-класс)", "Несовпадение 1 буквы в фамилии и 1 цифры паспорта. Пассажир спешит на правительственный саммит.", "sc_platform_boarding.jpg", 250, 25, 11),
            # 12
            ("drunken-brawler-bistro", "Нетрезвый дебошир и нарушение порядка в вагоне-бистро", "conflict", "hard", 360, "Вагон № 5 (Вагон-бистро)", "Пассажир распивает алкоголь, хамит гостям и бьет посуду на скорости 360 км/ч.", "sc_bistro_bar.jpg", 340, 20, 12),
            # 13
            ("vacuum-toilet-system-failure", "Отказ вакуумной системы туалетных модулей на 400 км/ч", "tech_failure", "hard", 400, "Вагон № 4 (Стандарт-класс)", "Блокировка вакуумного компрессора санузлов вагонов 3-4 из-за постороннего предмета. Очередь пассажиров.", "sc_vacuum_toilet.jpg", 350, 20, 13),
            # 14
            ("unaccompanied-child-passenger", "Несовершеннолетний пассажир без сопровождения на 350 км/ч", "vip_service", "medium", 350, "Вагон № 3 (Комфорт-класс)", "10-летний ребенок остался один в поезде: мать отстала при посадке в Зеленограде. Протокол ФЗ-259.", "sc_child_care.jpg", 320, 22, 14),
            # 15
            ("pantograph-icing-voltage-drop", "Обледенение токоприемника и бросок напряжения 27.5 кВ", "tech_failure", "extreme", 380, "Вагон № 8 (Хвостовой вагон)", "Искрение токоприемника в ледяной дождь, переход состава на аварийное аккумуляторное питание 110 В.", "sc_pantograph.jpg", 420, 18, 15),
            # 16
            ("lost-passport-migration-card", "Утеря документов иностранным делегатом перед Санкт-Петербургом", "conflict", "easy", 320, "Вагон № 2 (Бизнес-класс)", "Иностранный гость потерял паспорт и миграционную карту за 20 минут до вокзала. Паника и протокол ЛУ.", "vsm_interior_couple.jpg", 260, 25, 16),
            # 17
            ("child-anaphylaxis-bistro", "Острый анафилактический шок у ребенка в вагоне-бистро", "medical", "extreme", 390, "Вагон № 5 (Вагон-бистро)", "Отек Квинке и удушье после десерта с арахисом. Экстренное введение эпинефрина и встреча реанимобиля.", "sc_child_care.jpg", 470, 15, 17),
            # 18
            ("oversized-bicycle-conflict", "Негабаритный электровелосипед заблокировал эвакуационный проход", "conflict", "medium", 300, "Вагон № 7 (Стандарт-класс)", "Пассажир перегородил проход тяжелым электробайком. Нарушение правил пожарной безопасности и ПТЭ.", "sc_oversized_luggage.jpg", 290, 22, 18),
            # 19
            ("drone-hazard-viaduct", "Обнаружение неопознанного БПЛА над скоростным виадуком", "anti_terror", "extreme", 400, "Вагон № 3 (Комфорт-класс)", "Крупный дрон замечен вблизи контактной сети на мосту через Логовежь на 400 км/ч. Скрытый протокол.", "sc_drone_viaduct.jpg", 450, 16, 19),
            # 20
            ("security-cab-door-intrusion", "Попытка проникновения в кабину управления на 400 км/ч", "anti_terror", "hard", 400, "Вагон № 1 (Первый класс)", "Агрессивный пассажир пытается взломать бронированную дверь машиниста, требуя снизить скорость.", "sc_cab_door.jpg", 400, 18, 20),
        ]

        for slug, title, cat, diff, spd, car, desc, bg, xp, tm, order in scenarios_catalog:
            sc, _ = Scenario.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": cat,
                    "difficulty": diff,
                    "train_speed": spd,
                    "train_number": "№ 702 «Белый кречет» Москва — Санкт-Петербург",
                    "location_name": "Магистраль ВСМ-1 (Москва — Санкт-Петербург)",
                    "car_info": car,
                    "description": desc,
                    "briefing": f"Ситуационная задача по регламенту высокоскоростного движения на магистрали ВСМ-1. Поезд «Белый кречет» следует со скоростью {spd} км/ч. {desc}",
                    "regulation_reference": "Правила оказания услуг ВСМ, Инструкция проводника пассажирского вагона, Учебник 'Проводник пассажирских вагонов' (Отраслевое пособие), билеты 4-го разряда.",
                    "background_image": bg,
                    "base_xp": xp,
                    "time_limit_default": tm,
                    "order": order,
                    "is_active": True,
                }
            )
            self.create_nodes_for_scenario(sc, comp)

    def create_nodes_for_scenario(self, sc, comp):
        """Генерация нелинейных узлов решений для каждого сценария (всегда минимум 2 выбора на узел)"""
        ScenarioNode.objects.filter(scenario=sc).delete()

        if sc.slug == "business-class-conflict":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Самовольная пересадка в Бизнес-класс",
                character_name="Пассажир Сидоров", character_role="Пассажир комфорт-класса",
                character_mood="irritated",
                dialogue_text="«Я заплатил за билет, а в вашем комфорте шумно! Здесь полно пустых мест, я буду сидеть тут, и никто меня не сдвинет!»",
                narrative_context="Скорость 380 км/ч. Пассажир шумит по громкой связи и мешает попутчикам в вагоне № 2.",
                time_limit_seconds=25, is_terminal=False
            )
            n_upgrade = ScenarioNode.objects.create(
                scenario=sc, node_key="upgrade", title="Оформление апгрейда по п. 22",
                character_name="Пассажир Сидоров", character_role="Пассажир Бизнес-класса",
                character_mood="formal",
                dialogue_text="«Хорошо, если по правилам можно доплатить разницу тарифа прямо на борту через терминал — давайте оформим. Признаю, погорячился».",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Конфликт деэскалирован",
                character_name="ЛНП рейса", character_role="Начальник поезда",
                character_mood="calm", dialogue_text="«Апгрейд оформлен по мобильному терминалу, чек выдан. Вы блестяще сохранили достоинство сервиса ВСМ!»",
                is_terminal=True, is_success=True,
                resolution_report="ОТЛИЧНО: Проводник применил п. 22 Правил оказания услуг (доплата разницы тарифа на борту) и стандарты премиального гостеприимства «Белый кречет»."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Скандал на весь вагон",
                character_name="Пассажир", character_role="Возмущенный гость",
                character_mood="panicked", dialogue_text="«Вы смеете мне хамить и угрожать полицией при всех?! Я напишу жалобу руководству магистрали!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Грубость или финансовые махинации проводника спровоцировали скандал и грубое нарушение регламента обслуживания пассажиров."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Вежливо подойти, обратиться по имени, понизить тон и предложить 2 законных варианта: вернуться на свое место или доплатить разницу тарифа по п. 22.",
                tactical_hint="Правила перевозок п. 22: возможность доплаты до высшего класса на борту.",
                next_node_key="upgrade", loyalty_impact=20, safety_impact=10, service_impact=30, stress_impact=-10,
                competency=comp.get("service_etiquette"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Громко заявить: «Мужчина, вы не из этого класса, немедленно пошли вон в свой эконом, иначе сниму с поезда!»",
                tactical_hint="Грубейшее нарушение этикета стюарда ВСМ.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-15, service_impact=-50, stress_impact=40,
                competency=comp.get("conflict_resolution"), competency_points=-35, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_upgrade, choice_text="Оформить доплату через мобильный терминал ЛНП, выдать чек и предложить пассажиру приветственный набор бизнес-класса.",
                tactical_hint="Стандарты обслуживания «Белый кречет».",
                next_node_key="success", loyalty_impact=25, safety_impact=10, service_impact=25, stress_impact=-5,
                competency=comp.get("service_etiquette"), competency_points=30, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_upgrade, choice_text="Предложить рассчитаться наличными лично в карман проводнику со скидкой 50% («переведите мне на карту, так проще»).",
                tactical_hint="Грубейшее коррупционное и финансовое нарушение.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-20, service_impact=-50, stress_impact=45,
                competency=comp.get("service_etiquette"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "cardiac-emergency":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Сердечный приступ на 360 км/ч",
                character_name="Попутчик", character_role="Сосед по ряду",
                character_mood="panicked",
                dialogue_text="«Помогите! Мужчина схватился за сердце и упал в проход, он не дышит и синеет!»",
                narrative_context="Скорость 360 км/ч, перегон Валдай — Выползово. Пассажир без сознания, пульс на сонной артерии отсутствует.",
                time_limit_seconds=18, is_terminal=False
            )
            n_aed = ScenarioNode.objects.create(
                scenario=sc, node_key="aed", title="Применение АНД и СЛР",
                character_name="Дефибриллятор АНД", character_role="Голосовой помощник",
                character_mood="critical",
                dialogue_text="«Электроды наложены. Проводится анализ сердечного ритма. Не прикасайтесь к пациенту! Нажмите мигающую кнопку РАЗРЯД!»",
                time_limit_seconds=12, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Жизнь спасена: Золотой час",
                character_name="Врач бригады СМП", character_role="Реаниматолог",
                character_mood="calm", dialogue_text="«Сердечный ритм восстановлен благодаря мгновенному разряду дефибриллятора и правильному массажу. Вы спасли человеку жизнь!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЫСШАЯ НАГРАДА: Проводник безукоризненно выполнил протокол доврачебной реанимации с АНД. Скорая встретила поезд на станции."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Фатальная задержка помощи",
                character_name="Врач", character_role="Медик",
                character_mood="panicked", dialogue_text="«Время золотого часа упущено, почему не был использован штатный АНД?!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Неприменение автоматического наружного дефибриллятора при остановке сердца привело к клинической смерти. Каждая минута промедления снижает выживаемость на 10%."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Немедленно передать по рации: «Медицинская тревога вагон 6!», затребовать АНД из служебного купе и объявить поиск врача по поезду.",
                tactical_hint="Протокол экстренной доврачебной помощи ВСМ.",
                next_node_key="aed", loyalty_impact=20, safety_impact=45, service_impact=20, stress_impact=10,
                competency=comp.get("emergency_medical"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Попытаться напоить человека горячим сладким чаем и ждать прибытия на конечную станцию через час.",
                tactical_hint="Смертельно опасное действие при потере сознания и остановке сердца.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-80, service_impact=-50, stress_impact=50,
                competency=comp.get("emergency_medical"), competency_points=-40, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_aed, choice_text="Убедиться в безопасности окружающих, нажать кнопку разряда АНД и начать непрямой массаж сердца 30:2 с глубиной 5-6 см до приезда медиков.",
                tactical_hint="Алгоритм сердечно-легочной реанимации Минздрава РФ.",
                next_node_key="success", loyalty_impact=25, safety_impact=40, service_impact=25, stress_impact=-10,
                competency=comp.get("emergency_medical"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_aed, choice_text="Испугаться применять дефибриллятор («вдруг меня обвинят в ударе током?») и просто побрызгать лицо пассажира водой.",
                tactical_hint="Отказ от сертифицированного АНД при явных показаниях аппарата.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-70, service_impact=-45, stress_impact=45,
                competency=comp.get("emergency_medical"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "toilet-smoke-alarm":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Дым в туалете на мостовом переходе",
                character_name="Пассажир у стоп-крана", character_role="Испуганный пассажир",
                character_mood="panicked",
                dialogue_text="«Пожар! Дым валит из туалета! Я сейчас сорву стоп-кран, мы сгорим заживо!»",
                narrative_context="Скорость 400 км/ч. Состав идет по высокому мосту через реку Тверца. Сработал датчик СПАС-ВО.",
                time_limit_seconds=20, is_terminal=False
            )
            n_fire_attack = ScenarioNode.objects.create(
                scenario=sc, node_key="fire_attack", title="Локализация очага задымления",
                character_name="Проводник", character_role="Действия по регламенту СПАС-ВО",
                character_mood="formal",
                dialogue_text="«Тлеет урна для салфеток от брошенной электронной сигареты. Открытого пламени нет, сильное задымление!»",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Пожар ликвидирован по регламенту",
                character_name="ЛНП рейса", character_role="Начальник поезда",
                character_mood="calm", dialogue_text="«Очаг ликвидирован за 20 секунд. Главное — вы не допустили срыва стоп-крана на мосту. Браво!»",
                is_terminal=True, is_success=True,
                resolution_report="ИДЕАЛЬНО: Согласно Инструкции ЦЛ-114 и ПТЭ, категорически запрещается остановка поезда на мостах и в тоннелях при пожаре. Очаг потушен первичными средствами."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Катастрофическая остановка на мосту",
                character_name="Пожарный инспектор", character_role="МЧС России",
                character_mood="critical", dialogue_text="«Остановка на мосту отрезала пути эвакуации, а приток воздуха на 400 км/ч превратил тление в верховой пожар!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФА: Срыв стоп-крана на мостовом переходе запрещен ПТЭ! Поезд заблокирован на высоте без подъезда пожарных машин, возникла давка."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Физически отвести руку от стоп-крана со словами: «Мы на мосту, тормозить смертельно опасно!», взять огнетушитель ОУ-2 и вскрыть кабину туалета.",
                tactical_hint="Инструкция СПАС-ВО и ЦЛ-114: категорический запрет остановки на мостах.",
                next_node_key="fire_attack", loyalty_impact=15, safety_impact=45, service_impact=20, stress_impact=5,
                competency=comp.get("safety_regulations"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Поддаться панике пассажира и помочь сорвать стоп-кран прямо на середине высокого железнодорожного моста.",
                tactical_hint="Грубейшее нарушение ПТЭ железных дорог РФ.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-90, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_fire_attack, choice_text="Подать струю огнетушителя в урну, перекрыть приток воздуха, залить водой из гигиенического шланга и доложить машинисту о ликвидации.",
                tactical_hint="Правила применения первичных средств пожаротушения.",
                next_node_key="success", loyalty_impact=20, safety_impact=35, service_impact=20, stress_impact=-10,
                competency=comp.get("safety_regulations"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_fire_attack, choice_text="Распахнуть настежь окна и дверь туалета в салон для проветривания, не применяя огнетушитель.",
                tactical_hint="Приток кислорода на скорости вызовет взрывное горение.",
                next_node_key="fail", loyalty_impact=-35, safety_impact=-60, service_impact=-40, stress_impact=40,
                competency=comp.get("safety_regulations"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "unattended-briefcase":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Подозрительный кейс в вагоне-бистро",
                character_name="Бармен бистро", character_role="Сотрудник вагона-бистро",
                character_mood="panicked",
                dialogue_text="«Смотри, под угловым столиком кейс оставили! Из замка торчит проводок и светодиод моргает. Давай выкинем его в окно на ходу?!»",
                narrative_context="Скорость 370 км/ч. В бистро 12 пассажиров. Подозрение на самодельное взрывное устройство.",
                time_limit_seconds=25, is_terminal=False
            )
            n_cordon = ScenarioNode.objects.create(
                scenario=sc, node_key="cordon", title="Оцепление и эвакуация гостей",
                character_name="Пассажиры", character_role="Гости бистро",
                character_mood="calm",
                dialogue_text="«Проводник спокойно попросил нас пройти в вагон 6 на дегустацию чая из-за технической уборки. Никакой паники нет».",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Антитеррористический норматив выполнен",
                character_name="Сотрудник транспортной безопасности", character_role="СБ ВСМ",
                character_mood="calm", dialogue_text="«Зона оцеплена без радиоизлучений, предмет не тронут. На станции Новгород кейс проверен взрывотехниками. Образцовые действия!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЫСШИЙ БАЛЛ: Проводник строго соблюдал памятку антитеррора: не прикасаться, не перемещать, исключить мобильную связь вблизи предмета, эвакуировать людей."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Детонация опасного предмета",
                character_name="Служба безопасности", character_role="СБ ВСМ",
                character_mood="critical", dialogue_text="«Грубое нарушение антитеррористической инструкции! Попытка переместить кейс или звонок мобильного спровоцировали детонацию!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФА: Нарушен антитеррористический протокол безопасности ВСМ. Категорически запрещено перемещать подозрительные предметы и пользоваться сотовой связью вблизи них."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Жестко пресечь перемещение: «Руки прочь! Не трогать!», тихо объявить гостям переход в соседний вагон под предлогом техобслуживания и вызвать ЛНП по служебной проводной связи.",
                tactical_hint="Регламент безопасности ВСМ при обнаружении бесхозных предметов.",
                next_node_key="cordon", loyalty_impact=15, safety_impact=45, service_impact=20, stress_impact=5,
                competency=comp.get("safety_regulations"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Поддаться панике бармена, поднять кейс за ручку и попытаться на бегу выбросить его через торцевую дверь на скорости 370 км/ч.",
                tactical_hint="Смертельно опасное действие: срабатывание датчика наклона/вибрации СВУ.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-95, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_cordon, choice_text="Перекрыть торцевые двери бистро, выставить визуальный пост наблюдения на безопасном расстоянии и доложить дежурному по вокзалу прибытия.",
                tactical_hint="Оцепление опасной зоны до прибытия взрывотехнической группы.",
                next_node_key="success", loyalty_impact=20, safety_impact=30, service_impact=20, stress_impact=-5,
                competency=comp.get("safety_regulations"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_cordon, choice_text="Подойти вплотную к кейсу, включить сотовый телефон и начать вести прямую трансляцию в соцсети со вспышкой.",
                tactical_hint="Радиоизлучение мобильного телефона провоцирует радиовзрыватель.",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-80, service_impact=-40, stress_impact=45,
                competency=comp.get("safety_regulations"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "pet-allergy-crisis":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Экзотический питомец и отек Квинке",
                character_name="Пассажир Анохин", character_role="Пассажир с аллергией",
                character_mood="panicked",
                dialogue_text="«(задыхается) Уберите хорька! У меня острая аллергия на шерсть, горло сдавливает, я задыхаюсь!»",
                narrative_context="Скорость 350 км/ч. Пассажирка держит хорька на коленях без контейнера. Сосед бледнеет от развивающегося отека.",
                time_limit_seconds=25, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Конфликт исчерпан, здоровье спасено",
                character_name="Пассажир Анохин", character_role="Пострадавший",
                character_mood="calm", dialogue_text="«Спасибо! На новом месте с чистым обдувом и после антигистаминного препарата дыхание нормализовалось. Отличный сервис!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЕРНО: По правилам перевозок мелкие домашние животные провозятся только в жестких переносках с глухим дном. Проводник оперативно изолировал аллерген и оказал первую помощь."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Тяжелый приступ удушья",
                character_name="Врач скорой помощи", character_role="Медик",
                character_mood="critical", dialogue_text="«Пассажир доставлен в реанимацию с отеком гортани! Почему проводник не изолировал животное по п. 34 Правил?!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Непринятие мер по изоляции аллергена и неоказание доврачебной помощи. Нарушен п. 34 Правил перевозок (провоз животных строго в контейнерах)."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Потребовать немедленно поместить хорька в переноску по п. 34 Правил, пересадить задыхающегося пассажира на свободное кресло с мощным обдувом кондиционера и предложить антигистаминное средство.",
                tactical_hint="Правила провоза животных + купирование аллергического приступа.",
                next_node_key="success", loyalty_impact=25, safety_impact=25, service_impact=30, stress_impact=-10,
                competency=comp.get("conflict_resolution"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сказать задыхающемуся пассажиру: «Потерпите до Санкт-Петербурга, пассажирка имеет право везти питомца, а вам нужно было пить таблетки заранее дома».",
                tactical_hint="Преступное бездействие и нарушение правил перевозки животных.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-60, service_impact=-50, stress_impact=40,
                competency=comp.get("conflict_resolution"), competency_points=-35, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сорвать стоп-кран на скорости 350 км/ч, чтобы «немедленно высадить девушку с хорьком прямо на перегоне в лесу».",
                tactical_hint="Необоснованное экстренное торможение скоростного поезда.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-80, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-45, audio_cue="emergency"
            )

        elif sc.slug == "ac-failure-heatwave":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Отказ кондиционера при +33°C",
                character_name="Пассажир с молотком", character_role="Возмущенный пассажир",
                character_mood="panicked",
                dialogue_text="«Здесь дышать нечем, +30 градусов! Я сейчас выбью аварийное окно аварийным молотком, чтобы воздух пошел!»",
                narrative_context="Скорость 390 км/ч. Отказал компрессор кондиционера в вагоне № 7. Пассажир замахнулся красным молотком на окно.",
                time_limit_seconds=25, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Декомпрессия предотвращена",
                character_name="Поездной электромеханик", character_role="ПЭМ ВСМ",
                character_mood="calm", dialogue_text="«Перезапустил климатическую установку по резервному контуру. Если бы он выбил гермоокно на 390 км/ч — вагон бы разнесло напором воздуха!»",
                is_terminal=True, is_success=True,
                resolution_report="БЛЕСТЯЩЕ: Выбивание окон на скоростях свыше 200 км/ч смертельно опасно из-за аэродинамического удара. Проводник включил аварийную вентиляцию и успокоил людей."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Разгерметизация на 390 км/ч",
                character_name="Пассажиры", character_role="Пострадавшие",
                character_mood="critical", dialogue_text="«Окно выбито! Грохот, ветер срывает вещи, осколки стекла ранили пассажиров, сработали аварийные тормоза!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФА: На скорости 390 км/ч разбитие стеклопакета привело к баротравмам, срыву обшивки салона и экстренной остановке экспресса. Выбивание окон на ходу категорически запрещено!"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Остановить замах: «Окно бить нельзя! На 390 км/ч давление сорвет обшивку!», включить аварийную приточную вентиляцию на щите и раздать пассажирам бутилированную воду.",
                tactical_hint="Техника безопасности высокоскоростного подвижного состава + сервис.",
                next_node_key="success", loyalty_impact=20, safety_impact=45, service_impact=25, stress_impact=-5,
                competency=comp.get("vsm_tech_protocols"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Разрешить пассажиру: «Хорошо, разбивайте только аккуратно, духота невыносимая, пусть хоть чуть-чуть задует!»",
                tactical_hint="Смертельно опасное нарушение правил высокоскоростного движения.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-90, service_impact=-50, stress_impact=50,
                competency=comp.get("vsm_tech_protocols"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Испугаться криков, закрыться в служебном купе на ключ и ждать прибытия в Санкт-Петербург через 2 часа.",
                tactical_hint="Оставление пассажиров в аварийной ситуации.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-60, service_impact=-45, stress_impact=35,
                competency=comp.get("conflict_resolution"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "overbooking-seat-conflict":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Спор за кресло 14Б",
                character_name="Пассажир Власов", character_role="Пассажир с билетом 14Б",
                character_mood="irritated",
                dialogue_text="«Проводник! У меня посадочный в мобильном приложении на 14Б, а здесь уже сидит женщина и отказывается вставать! Разберитесь немедленно!»",
                narrative_context="Оба пассажира показывают подлинные билеты на место 14Б (сбой синхронизации билетного сервера). Скорость 390 км/ч.",
                time_limit_seconds=22, is_terminal=False
            )
            n_upgrade = ScenarioNode.objects.create(
                scenario=sc, node_key="upgrade", title="Предложение пересадки в Бизнес-класс",
                character_name="Пассажирка Крылова", character_role="Второй пассажир",
                character_mood="formal",
                dialogue_text="«Вы предлагаете мне пересесть в Бизнес-класс в вагон № 2 без какой-либо доплаты? Это очень любезно с вашей стороны, я согласна!»",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Идеальное разрешение по п. 23 Правил",
                character_name="ЛНП рейса", character_role="Начальник поезда",
                character_mood="calm", dialogue_text="«Акт формы ЛУ составлен, оба гостя довольны. Вы блестяще применили пункт 23 Правил перевозок!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЫСШИЙ БАЛЛ: Согласно п. 23 Правил оказания услуг перевозки, при невозможности предоставить место железная дорога обязана предоставить место в вагоне БОЛЕЕ ВЫСОКОЙ категории БЕЗ ДОПЛАТЫ. Лояльность сохранена на 100%."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Грубый выгон пассажира: Провал",
                character_name="Пассажир", character_role="Пострадавший",
                character_mood="panicked", dialogue_text="«Вы заставили меня стоять в тамбуре на скорости 390 км/ч или требовали взятку за место?! Я подаю в суд на ВСМ!»",
                is_terminal=True, is_success=False,
                resolution_report="КРИТИЧЕСКИЙ ПРОВАЛ: Проводник нарушил п. 23 Правил перевозок: пассажир был выдворен в тамбур либо с него незаконно требовали деньги за положенный бесплатный апгрейд."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Проверить QR-коды в терминале, извиниться за сбой системы и предложить одному из пассажиров бесплатный апгрейд в Бизнес-класс по п. 23.",
                tactical_hint="Пункт 23 Правил: повышение класса обслуживания без взимания доплаты при овербукинге.",
                next_node_key="upgrade", loyalty_impact=20, safety_impact=10, service_impact=30, stress_impact=-5,
                competency=comp.get("service_etiquette"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Потребовать от одного из пассажиров покинуть вагон и ожидать в тамбуре решения начальника поезда.",
                tactical_hint="Выдворение пассажира с билетом в тамбур на 390 км/ч.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-25, service_impact=-45, stress_impact=35,
                competency=comp.get("conflict_resolution"), competency_points=-30, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_upgrade, choice_text="Сопроводить пассажирку в вагон № 2, помочь перенести багаж, предложить приветственный напиток и составить служебный акт с ЛНП.",
                tactical_hint="Закрепление высокого стандарта гостеприимства «Белый кречет».",
                next_node_key="success", loyalty_impact=25, safety_impact=10, service_impact=25, stress_impact=-5,
                competency=comp.get("service_etiquette"), competency_points=30, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_upgrade, choice_text="Потребовать у пассажирки доплату наличными: «За переход в Бизнес-класс придется доплатить мне лично 3000 рублей прямо сейчас».",
                tactical_hint="Грубое вымогательство и прямое нарушение п. 23 Правил перевозок.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-15, service_impact=-50, stress_impact=45,
                competency=comp.get("service_etiquette"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "passenger-missed-train":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Отставший пассажир на платформе",
                character_name="Ребенок (9 лет)", character_role="Сын отставшего пассажира",
                character_mood="panicked",
                dialogue_text="«(плачет) Где папа?! Папа пошел за кофе на станцию, двери закрылись и мы уехали! Что теперь будет?!»",
                narrative_context="Поезд набрал 380 км/ч после 1-минутной остановки в Твери. В вагоне остались вещи пассажира и испуганный ребенок.",
                time_limit_seconds=20, is_terminal=False
            )
            n_report = ScenarioNode.objects.create(
                scenario=sc, node_key="report", title="Запуск протокола отставания",
                character_name="Проводник", character_role="Действия по регламенту",
                character_mood="formal",
                dialogue_text="«Присаживайся со мной, не бойся, папа свяжется с нами. Я вызываю начальника поезда для отправки служебной телеграммы в Тверь и описи багажа.»",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Протокол выполнен идеально",
                character_name="Дежурный по вокзалу Тверь", character_role="Связь через ЛНП",
                character_mood="calm", dialogue_text="«Отец найден на станции Тверь, посажен на следующий поезд № 704. Багаж описан комиссией. Ребенок под вашей опекой до Бологого.»",
                is_terminal=True, is_success=True,
                resolution_report="ОТЛИЧНАЯ РАБОТА: Проводник успокоил несовершеннолетнего, не допустил паники, выполнил требование билета 20: составление описи вещей комиссией из 3 человек и подача служебной телеграммы."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Срыв протокола и оставление ребенка",
                character_name="Транспортная прокуратура", character_role="Инспекция",
                character_mood="critical", dialogue_text="«Ребенок высажен один на станции или багаж брошен без описи. Возбуждено административное расследование!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Нарушен билет 20 экзамена проводника и ФЗ № 259. Категорически запрещено оставлять детей без присмотра, высаживать их одних или срывать стоп-краны ради опоздавших."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Присесть на уровень глаз ребенка, успокоить, напоить чаем и по рации немедленно доложить ЛНП для подачи телеграммы на станцию Тверь.",
                tactical_hint="Экзаменационный билет 6/20: психологическая помощь + протокол описи вещей и телеграммы.",
                next_node_key="report", loyalty_impact=20, safety_impact=25, service_impact=25, stress_impact=-10,
                competency=comp.get("conflict_resolution"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сказать 9-летнему ребенку: «Не реви, папа сам виноват, на следующей станции Тверь сойдешь и будешь ждать его на вокзале один».",
                tactical_hint="Уголовная ответственность по ст. 125 УК РФ и нарушение ФЗ № 259.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-60, service_impact=-50, stress_impact=45,
                competency=comp.get("conflict_resolution"), competency_points=-45, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сорвать стоп-кран посреди перегона через 10 минут после отправления, требуя машиниста сдать поезд назад на станцию Тверь.",
                tactical_hint="Категорически запрещенное экстренное торможение скоростного состава.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-85, service_impact=-45, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-45, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_report, choice_text="Составить акт описи вещей в трех экземплярах (ЛНП, проводник, пассажир-свидетель) и организовать встречу ребенка родственниками.",
                tactical_hint="Строгое соблюдение регламента оформления забытых/оставленных вещей.",
                next_node_key="success", loyalty_impact=20, safety_impact=20, service_impact=20, stress_impact=-5,
                competency=comp.get("safety_regulations"), competency_points=30, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_report, choice_text="Сгрузить все чемоданы отца в неохраняемый тамбур без описи: «Мне некогда бумажки писать, пусть так полежат».",
                tactical_hint="Халатность и утрата багажа пассажира.",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-30, service_impact=-35, stress_impact=25,
                competency=comp.get("safety_regulations"), competency_points=-30, audio_cue="emergency"
            )

        elif sc.slug == "sknb-overheating-alarm":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Зуммер СКНБ на 400 км/ч",
                character_name="Пульт контроля вагона", character_role="Сигнализация СКНБ",
                character_mood="critical",
                dialogue_text="«ТРЕВОГА! ПЕРЕГРЕВ БУКСОВОГО УЗЛА: ВАГОН 5, ТЕЛЕЖКА 2, КОЛЕСНАЯ ПАРА 3. ТЕМПЕРАТУРА ВЫШЕ НОРМЫ НА 35°C!»",
                narrative_context="Скорость 400 км/ч. При разрушении подшипника буксы возможен сход с рельсов за считанные секунды!",
                time_limit_seconds=15, is_terminal=False
            )
            n_call_driver = ScenarioNode.objects.create(
                scenario=sc, node_key="call_driver", title="Доклад машинисту и снижение скорости",
                character_name="Машинист электропоезда", character_role="Кабина поезда",
                character_mood="formal",
                dialogue_text="«Вагон 5, тревогу принял! Начинаю служебное плавное торможение до 140 км/ч. Контролируйте запах и звук в районе 2-й тележки!»",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Опасность ликвидирована",
                character_name="Поездной электромеханик", character_role="ПЭМ поезда",
                character_mood="calm", dialogue_text="«Осмотр завершен: датчик СКНБ сработал штатно на локальный перегрев уплотнения. Состав допущен до станции Бологое с ограничением скорости.»",
                is_terminal=True, is_success=True,
                resolution_report="БЕЗУПРЕЧНО: Проводник мгновенно доложил в кабину машиниста (билет 2, 14), не допустил экстренного стоп-крана на 400 км/ч и организовал совместный осмотр буксового узла."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Крушение буксового узла",
                character_name="Ревизор по безопасности", character_role="Служба безопасности движения",
                character_mood="critical", dialogue_text="«Срыв стоп-крана заклинил колесную пару либо игнорирование тревоги привело к излому шейки оси!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФА: Игнорирование сигнала СКНБ или резкий срыв стоп-крана на 400 км/ч повлек срез буксы и сход колесной пары. Билеты 8 и 14 строго требуют служебной связи с машинистом."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Немедленно вызвать машиниста по переговорной связи: «Машинист, СКНБ вагон 5, вторая тележка, требую снижения скорости!»",
                tactical_hint="Билеты 8, 14: Первое действие проводника при СКНБ — немедленный доклад машинисту.",
                next_node_key="call_driver", loyalty_impact=10, safety_impact=40, service_impact=15, stress_impact=15,
                competency=comp.get("safety_regulations"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Резко сорвать стоп-кран в вагоне на скорости 400 км/ч без предупреждения локомотивной бригады.",
                tactical_hint="Резкий стоп-кран при нагретой буксе срезает шейку оси и опрокидывает вагон.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-95, service_impact=-45, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Заглушить зуммер кнопкой «Сброс» на электрощите и продолжать путь, решив, что это ложный глюк электроники.",
                tactical_hint="Преступная халатность при срабатывании СКНБ.",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-90, service_impact=-40, stress_impact=40,
                competency=comp.get("vsm_tech_protocols"), competency_points=-45, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_call_driver, choice_text="Вместе с поездным электромехаником (ПЭМ) провести осмотр тележки через технологический люк и прибором тактильного замера.",
                tactical_hint="Регламент инструментального контроля узлов ходовой части.",
                next_node_key="success", loyalty_impact=15, safety_impact=30, service_impact=20, stress_impact=-10,
                competency=comp.get("vsm_tech_protocols"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_call_driver, choice_text="Сказать машинисту: «Все в порядке, гарью вроде не пахнет, можете разгоняться дальше до 400 км/ч без осмотра механиком».",
                tactical_hint="Недопустимый отказ от регламентного осмотра тележки.",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-80, service_impact=-35, stress_impact=35,
                competency=comp.get("safety_regulations"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "chassis-ground-fault":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Лампа замыкания на корпус",
                character_name="Электрощит вагона", character_role="Система питания",
                character_mood="critical",
                dialogue_text="«Светится красная сигнальная лампа: «Замыкание минуса на корпус». Напряжение сети вагона нестабильно.»",
                narrative_context="Скорость 370 км/ч. Опасность пробоя изоляции на металлические поручни и пожара электрощита.",
                time_limit_seconds=20, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Безопасность электросистемы восстановлена",
                character_name="Поездной электромеханик (ПЭМ)", character_role="ПЭМ",
                character_mood="calm", dialogue_text="«Вы своевременно обесточили электрокипятильник и климатический компрессор вагона. Утечка локализована, угрозы поражения током нет!»",
                is_terminal=True, is_success=True,
                resolution_report="ОТЛИЧНО: Проводник строго соблюдал правила техники безопасности на электрофицированных участках (билеты 7, 10, 19)."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Пожар электрощита и поражение током",
                character_name="Инспектор Ространснадзора", character_role="Инспекция",
                character_mood="critical", dialogue_text="«Поражение пассажира током через металлический поручень и возгорание изоляции электрощита!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Нарушена инструкция по электробезопасности ЦЛ-114 и билеты 7, 10. При замыкании на корпус проводник обязан обесточить потребители, вызвать механика и не прикасаться к металлическим элементам."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Отключить энергоемкие потребители на щите (кипятильник, охладитель воды), не касаться металлических частей и вызвать ПЭМ.",
                tactical_hint="Билеты 7, 10: Порядок действий проводника при появлении замыкания на корпус вагона.",
                next_node_key="success", loyalty_impact=10, safety_impact=35, service_impact=15, stress_impact=5,
                competency=comp.get("vsm_tech_protocols"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Открыть дверцу открытого электрощита и голыми руками проверять надежность силовых соединений под напряжением 110 В.",
                tactical_hint="Грубейшее нарушение правил электробезопасности (риск удара током).",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-75, service_impact=-30, stress_impact=45,
                competency=comp.get("vsm_tech_protocols"), competency_points=-40, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Проигнорировать красную лампу «Земля на корпусе» и включить электроотопление и титан на максимальную мощность.",
                tactical_hint="Риск мгновенного дугового короткого замыкания и возгорания кабельной трассы.",
                next_node_key="fail", loyalty_impact=-25, safety_impact=-80, service_impact=-35, stress_impact=40,
                competency=comp.get("safety_regulations"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "ticket-typo-conflict":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Ошибка в электронном билете",
                character_name="Пассажир Савельев", character_role="VIP-пассажир",
                character_mood="irritated",
                dialogue_text="«Какая еще ошибка в фамилии?! В билете 'Савелев' вместо 'Савельев'? И из-за этого вы задерживаете меня при посадке?! Я опаздываю на совещание!»",
                narrative_context="Посадка в бизнес-класс поезда «Белый кречет». До отправления поезда 4 минуты.",
                time_limit_seconds=25, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Проход по правилу одной буквы (Тел. 852)",
                character_name="Пассажир Савельев", character_role="Гость Бизнес-класса",
                character_mood="calm", dialogue_text="«Спасибо за профессионализм! Составили акт прямо на месте за 1 минуту и помогли занести портфель. Отличный сервис!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЕРНО: По телеграмме № 852 и п. 14 Правил перевозок, при расхождении не более 1 буквы в фамилии и 1 цифры в номере паспорта пассажир ДОПУСКАЕТСЯ в поезд с составлением акта."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Незаконный отказ в посадке",
                character_name="Юридический департамент ВСМ", character_role="Претензионный отдел",
                character_mood="critical", dialogue_text="«Пассажир отстранен от рейса вопреки Телеграмме № 852. Компания понесла репутационный ущерб и выплачивает штраф!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Грубейшее нарушение Отраслевого распоряжения № 852 и п. 14 Правил перевозок. Пассажир с одной опечаткой в фамилии или одной цифре паспорта ДОПУСКАЕТСЯ к поездке с составлением акта формы ЛУ."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Вежливо улыбнуться: «Не волнуйтесь! По правилам допускается до одной опечатки в фамилии. Проходите на ваше место 3А, я оформлю акт прямо в пути».",
                tactical_hint="Правила перевозок: допуск пассажира при наличии незначительной опечатки без создания стресса.",
                next_node_key="success", loyalty_impact=25, safety_impact=15, service_impact=30, stress_impact=-10,
                competency=comp.get("service_etiquette"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Категорически заблокировать вход: «С ошибками вход запрещен! Ваш билет недействителен, покупайте новый за 15 000 рублей или оставайтесь на перроне!»",
                tactical_hint="Грубое нарушение Телеграммы № 852 и п. 14 Правил перевозок.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-15, service_impact=-50, stress_impact=40,
                competency=comp.get("conflict_resolution"), competency_points=-35, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Потребовать у пассажира 5 000 рублей «штрафа на месте за исправление буквы» в карман проводника.",
                tactical_hint="Коррупция и прямое нарушение финансовой дисциплины.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-20, service_impact=-50, stress_impact=50,
                competency=comp.get("service_etiquette"), competency_points=-45, audio_cue="emergency"
            )

        elif sc.slug == "drunken-brawler-bistro":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Дебош в вагоне-бистро",
                character_name="Нетрезвый пассажир", character_role="Нарушитель порядка",
                character_mood="irritated",
                dialogue_text="«Эй, стюард! Налей мне коньяку еще! Чего смотришь?! Я за все плачу, а вы тут со своими правилами лезете!» (разбивает бокал об пол).",
                narrative_context="Поезд идет на 360 км/ч. В бистро 15 гостей, нарушитель угрожает персоналу.",
                time_limit_seconds=20, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Изоляция дебошира по п. 27",
                character_name="Сотрудник транспортной безопасности", character_role="Охрана поезда",
                character_mood="calm", dialogue_text="«Нарушитель блокирован в служебном отсеке. На станции Новая Тверь оформлена сдача наряду полиции по п. 27 Правил оказания услуг.»",
                is_terminal=True, is_success=True,
                resolution_report="ГРАМОТНО: Согласно п. 27а Правил, нарушитель общественного порядка изолируется поездной бригадой и удаляется из поезда сотрудниками полиции."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Драка и травмы в вагоне-бистро",
                character_name="Пассажиры", character_role="Пострадавшие",
                character_mood="critical", dialogue_text="«В бистро побоище, разбитая посуда и паника! Проводник сам полез в драку или подливал алкоголь дебоширу!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Нарушен регламент п. 27 Правил перевозок. Дебоширы изолируются силами охраны и сдаются полиции. Персонал обязан ограждать пассажиров, а не устраивать кулачные бои."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Не вступать в рукопашный спор, занять позицию безопасности, вызвать тревожной кнопкой охрану поезда и ЛНП, оградив гостей от дебошира.",
                tactical_hint="Пункт 27 Правил: удаление пьяного пассажира силами полиции с оформлением акта.",
                next_node_key="success", loyalty_impact=15, safety_impact=30, service_impact=20, stress_impact=10,
                competency=comp.get("conflict_resolution"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Схватить металлический поднос и наброситься на пьяного с кулаками прямо посреди столиков с гостями.",
                tactical_hint="Недопустимое участие персонала в потасовке, создающее угрозу гостям.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-60, service_impact=-50, stress_impact=45,
                competency=comp.get("conflict_resolution"), competency_points=-40, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Налить нарушителю еще двойную порцию коньяка за счет заведения, чтобы он «выпил и уснул».",
                tactical_hint="Категорически запрещено поить дебоширов спиртным.",
                next_node_key="fail", loyalty_impact=-35, safety_impact=-50, service_impact=-40, stress_impact=35,
                competency=comp.get("service_etiquette"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "vacuum-toilet-system-failure":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Сбой вакуумной системы санузлов",
                character_name="Очередь пассажиров", character_role="Пассажир вагона № 4",
                character_mood="irritated",
                dialogue_text="«Проводник! Почему обе туалетные кабины закрыты и горят красным?! Нам до Питера терпеть?! Разберитесь немедленно!»",
                narrative_context="Скорость 400 км/ч, перегон Валдай — Новгород. Засор вакуумного компрессора из-за постороннего предмета.",
                time_limit_seconds=20, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Маршрутизация потока и заявка ПЭМ",
                character_name="Поездной электромеханик", character_role="ПЭМ ВСМ",
                character_mood="calm", dialogue_text="«Засор клапана устранен на технической стоянке без залива тамбура. Вы отлично перенаправили пассажиров в вагоны 3 и 5!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЕРНО: Проводник заблокировал неисправный санузел трехгранником, включил информационные указатели и перенаправил поток пассажиров в смежные вагоны."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Затопление ковролина нечистотами",
                character_name="Пассажиры вагона", character_role="Возмущенные гости",
                character_mood="critical", dialogue_text="«Ковролин вагона залит грязной водой! Запах невыносимый, люди требуют компенсации за испорченную обувь!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Нарушен регламент технической эксплуатации вакуумных систем ЭЧТК. Попытки кустарного пробивания клапана под давлением привели к гидроудару и заливу салона."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Запереть аварийные санузлы трехгранным ключом, выставить статус на табло, вежливо перенаправить гостей в свободные санузлы вагонов 3 и 5 и передать заявку ПЭМ.",
                tactical_hint="Регламент технической эксплуатации ЭЧТК скоростных поездов.",
                next_node_key="success", loyalty_impact=15, safety_impact=25, service_impact=20, stress_impact=-5,
                competency=comp.get("vsm_tech_protocols"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Оставить санузлы открытыми и сказать пассажирам: «Продолжайте нажимать смыв сильнее, может само проскочит».",
                tactical_hint="Приводит к переполнению фановой трубы и заливу пола нечистотами.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-40, service_impact=-50, stress_impact=40,
                competency=comp.get("vsm_tech_protocols"), competency_points=-35, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Взять металлическую швабру и с силой попытаться пробить вакуумный клапан унитаза под давлением.",
                tactical_hint="Смертельно опасный срыв вакуумного фланца под рабочим давлением системы.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-60, service_impact=-45, stress_impact=45,
                competency=comp.get("vsm_tech_protocols"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "unaccompanied-child-passenger":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Ребенок без сопровождения",
                character_name="Миша (10 лет)", character_role="Несовершеннолетний пассажир",
                character_mood="panicked",
                dialogue_text="«(плачет) Мама осталась на платформе в Зеленограде, не успела в двери! Я один еду, у меня даже телефона нет!»",
                narrative_context="Скорость 350 км/ч. Поезд следует без остановок до Твери. Мальчик едет один без документов и связи.",
                time_limit_seconds=22, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Протокол ФЗ-259 выполнен безупречно",
                character_name="Мама Миши (по телефону)", character_role="Родитель",
                character_mood="calm", dialogue_text="«Спасибо огромное проводнику! Ребенка успокоили, накормили и передали бабушке на вокзале под роспись полиции!»",
                is_terminal=True, is_success=True,
                resolution_report="ОТЛИЧНО: В соответствии с ФЗ № 259 категорически запрещена высадка несовершеннолетних пассажиров. Проводник обеспечил опеку и информировал ЛНП."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Незаконная высадка несовершеннолетнего",
                character_name="Следственный комитет РФ", character_role="Инспекция",
                character_mood="critical", dialogue_text="«Возбуждено уголовное дело по ст. 125 УК РФ (оставление в опасности) за попытку высадки ребенка одного на станции!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФИЧЕСКИЙ ПРОВАЛ: Федеральный закон № 259 категорически запрещает высаживать детей без сопровождения! Проводник обязан окружить ребенка опекой и передать в руки полиции/родителей."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Присесть рядом с ребенком, успокоить, угостить чаем, связаться с матерью по контактным данным билета и передать данные ЛНП для встречи инспектором ПДН.",
                tactical_hint="ФЗ № 259 и регламент безопасной перевозки несовершеннолетних.",
                next_node_key="success", loyalty_impact=25, safety_impact=30, service_impact=30, stress_impact=-10,
                competency=comp.get("service_etiquette"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сказать ребенку: «Выходи на первой же станции Тверь на платформу и езжай обратно на электричке, мы не детский сад».",
                tactical_hint="Прямое нарушение Федерального закона № 259 и ст. 125 УК РФ.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-70, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сделать вид, что не заметили плачущего ребенка, и уйти разносить чай в хвост состава.",
                tactical_hint="Преступное оставление несовершеннолетнего в опасной обстановке.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-50, service_impact=-45, stress_impact=35,
                competency=comp.get("service_etiquette"), competency_points=-35, audio_cue="emergency"
            )

        elif sc.slug == "pantograph-icing-voltage-drop":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Бросок напряжения в контактной сети",
                character_name="Пассажиры вагона", character_role="Испуганные пассажиры",
                character_mood="panicked",
                dialogue_text="«Свет погас! За окном сноп искр от крыши поезда! Мы сейчас сойдем с рельсов на 380 км/ч?!»",
                narrative_context="Скорость 380 км/ч, ледяной дождь. Обледенение контактного провода 27.5 кВ вызвало переключение на аварийные аккумуляторы 110 В.",
                time_limit_seconds=18, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Штатный переход на резервное питание",
                character_name="Машинист электропоезда", character_role="Кабина управления",
                character_mood="calm", dialogue_text="«Пневмоочистка токоприемника сработала, напряжение в норме. Благодарю экипаж за хладнокровие и спокойствие в салоне!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЕРНО: Проводник оперативно проинформировал пассажиров о штатном переключении на аккумуляторы и предотвратил панику в темном вагоне."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Паника и срыв стоп-крана на 380 км/ч",
                character_name="Начальник поезда", character_role="ЛНП рейса",
                character_mood="critical", dialogue_text="«Необоснованная паника проводника спровоцировала срыв стоп-крана на огромной скорости и повреждение колесных пар!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Искрение токоприемника в гололед — нормальное физическое явление. Ложная паника и срыв тормозов на 380 км/ч привели к юзу колес и травмам пассажиров."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Включить служебную громкую связь: «Уважаемые гости! Включено штатное резервное освещение. Поезд следует на безопасных аккумуляторах по графику». Проверить щит питания.",
                tactical_hint="Инструкция по действиям бригады при падении напряжения в контактной сети.",
                next_node_key="success", loyalty_impact=20, safety_impact=35, service_impact=25, stress_impact=-10,
                competency=comp.get("vsm_tech_protocols"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="В панике выбежать в салон с криками: «Мы горим на крыше! Все ложитесь на пол, падаем!»",
                tactical_hint="Провоцирование паники и давки среди пассажиров.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-60, service_impact=-50, stress_impact=45,
                competency=comp.get("conflict_resolution"), competency_points=-40, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Сорвать стоп-кран посреди скоростного перегона 380 км/ч при штатном мигании ламп.",
                tactical_hint="Категорически необоснованное экстренное торможение.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-85, service_impact=-45, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-45, audio_cue="emergency"
            )

        elif sc.slug == "lost-passport-migration-card":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Утеря документов иностранным делегатом",
                character_name="Мистер Чжан", character_role="Делегат форума (VIP)",
                character_mood="panicked",
                dialogue_text="«Help! I lost my passport and migration card! Где мой паспорт?! Через 20 минут вокзал, меня арестует полиция?!»",
                narrative_context="Скорость 320 км/ч, подъезд к Санкт-Петербургу. Пассажир бизнес-класса в панике обыскивает кресло.",
                time_limit_seconds=25, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Паспорт найден, гость спасен",
                character_name="Мистер Чжан", character_role="VIP-гость",
                character_mood="calm", dialogue_text="«Вы нашли его за подушкой сиденья! Thank you so much! Ваш сервис на ВСМ просто невероятный!»",
                is_terminal=True, is_success=True,
                resolution_report="ОТЛИЧНО: Проводник проявил выдержку, успокоил иностранного гостя, методично осмотрел технологические зазоры кресла и нашел документ."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Международный дипломатический скандал",
                character_name="МИД РФ", character_role="Протокол",
                character_mood="critical", dialogue_text="«Хамство и равнодушие проводника к иностранному делегату нанесли ущерб международному статусу ВСМ «Белый кречет»!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Нарушены стандарты сервиса ВСМ. Проводник обязан оказывать максимальную помощь гостям при потере документов и привлекать начальника поезда."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Вежливо на английском и русском успокоить гостя: «Don't worry, we will help you!», методично проверить зазор между спинкой и сиденьем и подготовить бланк формы ЛУ на случай утери.",
                tactical_hint="Стандарты международного гостеприимства ВСМ и розыска находок.",
                next_node_key="success", loyalty_impact=30, safety_impact=15, service_impact=35, stress_impact=-15,
                competency=comp.get("service_etiquette"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Равнодушно заявить: «Следить надо за вещами! Я вам не сыщик, на вокзале вас задержит миграционная полиция».",
                tactical_hint="Грубейшее хамство и разрушение репутации сервиса ВСМ.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-20, service_impact=-50, stress_impact=40,
                competency=comp.get("service_etiquette"), competency_points=-40, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Объявить по громкой связи на весь скоростной экспресс, что в кресле 3А потеряли паспорт, спровоцировав насмешки в салоне.",
                tactical_hint="Грубое разглашение персональных данных VIP-гостя.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-15, service_impact=-40, stress_impact=35,
                competency=comp.get("service_etiquette"), competency_points=-30, audio_cue="emergency"
            )

        elif sc.slug == "child-anaphylaxis-bistro":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Анафилаксия у ребенка в бистро",
                character_name="Мать ребенка", character_role="Родитель в панике",
                character_mood="panicked",
                dialogue_text="«Помогите! Ребенок съел десерт с орехом! Он синеет, губы раздуло, он не может дышать! Сделайте что-нибудь!»",
                narrative_context="Скорость 390 км/ч. Молниеносный анафилактический шок, отек Квинке. Счет идет на секунды.",
                time_limit_seconds=15, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Мгновенный ввод адреналина и спасение",
                character_name="Врач реанимобиля", character_role="Скорая помощь",
                character_mood="calm", dialogue_text="«Введение эпинефрина в бедро за 30 секунд спасло ребенку жизнь от удушья. Дополнительно подан кислород. Вы настоящий герой!»",
                is_terminal=True, is_success=True,
                resolution_report="ВЫСШАЯ НАГРАДА: Мгновенное купирование анафилактического шока препаратом первой помощи и вызов реанимации к ближайшей станции."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Асфиксия и летальный исход",
                character_name="Следственный комитет", character_role="Юрист",
                character_mood="critical", dialogue_text="«Время на введение адреналина упущено. Ребенок задохнулся от спазма дыхательных путей!»",
                is_terminal=True, is_success=False,
                resolution_report="ФАТАЛЬНЫЙ ПРОВАЛ: При анафилаксии промедление в 2-3 минуты приводит к асфиксии. Неоказание неотложной помощи автоинъектором эпинефрина привело к гибели."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Уложить ребенка, освободить шею, извлечь из сумки матери автоинъектор с эпинефрином, ввести дозу в наружную поверхность бедра и передать машинисту запрос на реанимобиль в Новгород.",
                tactical_hint="Протокол оказания первой помощи при анафилактическом шоке Минздрава РФ.",
                next_node_key="success", loyalty_impact=30, safety_impact=50, service_impact=30, stress_impact=-10,
                competency=comp.get("emergency_medical"), competency_points=50, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Дать ребенку выпить стакан сладкой газировки и ждать 45 минут до прибытия поезда в Санкт-Петербург.",
                tactical_hint="Фатальное бездействие: жидкость при спазме трахеи вызовет мгновенное удушье.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-95, service_impact=-50, stress_impact=50,
                competency=comp.get("emergency_medical"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Насильно залить в горло горячий чай из служебного купе, пытаясь «промыть горло».",
                tactical_hint="Тяжелейший ожог гортани и спазм дыхательных путей.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-90, service_impact=-50, stress_impact=50,
                competency=comp.get("emergency_medical"), competency_points=-50, audio_cue="emergency"
            )

        elif sc.slug == "oversized-bicycle-conflict":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Электровелосипед блокирует проход",
                character_name="Велосипедист Котов", character_role="Пассажир с велосипедом",
                character_mood="irritated",
                dialogue_text="«Куда я его дену?! Он дорогой, я его из рук не выпущу! Постоите в проходе, никто не умрет!»",
                narrative_context="Скорость 300 км/ч. Тяжелый электробайк перегородил центральный эвакуационный проход стандарт-класса.",
                time_limit_seconds=22, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Размещение в багажном модуле",
                character_name="Велосипедист Котов", character_role="Пассажир",
                character_mood="calm", dialogue_text="«Спасибо, что помогли закрепить его в багажном отсеке вагона № 1 ремнями. Признаю, проход перекрывать было нельзя».",
                is_terminal=True, is_success=True,
                resolution_report="ВЕРНО: По правилам перевозок на ВСМ негабаритный багаж и велотранспорт размещаются исключительно в выделенных багажных зонах с фиксацией."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Травмирование пассажиров незакрепленным байком",
                character_name="Инспектор ПТЭ", character_role="Ревизор",
                character_mood="critical", dialogue_text="«При служебном торможении 35-килограммовый электробайк сорвался и нанес травмы троим пассажирам в проходе!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Категорически запрещено оставлять громоздкие предметы в проходах. Нарушены правила пожарной безопасности и ПТЭ путей эвакуации."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Спокойно и твердо сослаться на правила пожарной безопасности ПТЭ, предложить помощь в бесплатной транспортировке и фиксации электробайка в багажном купе вагона № 1.",
                tactical_hint="Правила провоза багажа и пожарная безопасность путей эвакуации.",
                next_node_key="success", loyalty_impact=20, safety_impact=35, service_impact=25, stress_impact=-10,
                competency=comp.get("conflict_resolution"), competency_points=35, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Разрешить оставить тяжелый электробайк поперек прохода: «Ладно, только прислоните к креслам соседей».",
                tactical_hint="Грубейшее нарушение пожарной безопасности и ПТЭ.",
                next_node_key="fail", loyalty_impact=-30, safety_impact=-65, service_impact=-40, stress_impact=35,
                competency=comp.get("safety_regulations"), competency_points=-35, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Начать силой вырывать руль у пассажира и угрожать сбросить велосипед с поезда на ходу.",
                tactical_hint="Хулиганские действия со стороны проводника.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-50, service_impact=-50, stress_impact=45,
                competency=comp.get("conflict_resolution"), competency_points=-40, audio_cue="emergency"
            )

        elif sc.slug == "drone-hazard-viaduct":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="БПЛА над скоростным виадуком",
                character_name="Пассажир у окна", character_role="Очевидец",
                character_mood="panicked",
                dialogue_text="«Смотрите в окно! Над мостом прямо над нашими проводами висит огромный дрон с камерой и грузом! Нас сейчас подорвут!»",
                narrative_context="Скорость 400 км/ч, высокий мост через реку Логовежь. Пассажиры бросаются к окнам, возникает давка.",
                time_limit_seconds=16, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Антитеррористический протокол ВСМ",
                character_name="Дежурный диспетчер ВСМ", character_role="ЦУП ВСМ",
                character_mood="calm", dialogue_text="«Сообщение проводника принято, координаты переданы в силовые структуры. Поезд прошел виадук на максимальной скорости без повреждений!»",
                is_terminal=True, is_success=True,
                resolution_report="БЕЗУПРЕЧНО: Опускание защитных шторок защитило пассажиров от осколочного риска, а закрытый доклад машинисту передал координаты без паники."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Срыв стоп-крана на открытом мосту",
                character_name="Служба безопасности", character_role="Антитеррор",
                character_mood="critical", dialogue_text="«Срыв стоп-крана остановил поезд неподвижной мишенью посреди открытого виадука! Возникла давка у окон!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФА: Нарушен антитеррористический протокол ВСМ и строжайший запрет применения стоп-крана на мостах. Поезд обязан на максимальной скорости покинуть опасную зону."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Опустить солнцезащитные шторки на окнах («В целях безопасности оставайтесь на местах»), по служебному телефону передать машинисту время и пикет наблюдения БПЛА.",
                tactical_hint="Антитеррористический регламент ВСМ при воздушной угрозе.",
                next_node_key="success", loyalty_impact=15, safety_impact=45, service_impact=20, stress_impact=5,
                competency=comp.get("safety_regulations"), competency_points=40, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Закричать в вагон: «Дрон над нами! Все к окнам, фотографируйте!» и сорвать стоп-кран прямо на середине моста.",
                tactical_hint="Остановка на мосту под угрозой удара дрона категорически запрещена.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-90, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Открыть аварийную форточку и попытаться на ходу 400 км/ч сбить дрон огнетушителем ОУ-2.",
                tactical_hint="Смертельно опасный выброс предметов из скоростного поезда.",
                next_node_key="fail", loyalty_impact=-40, safety_impact=-85, service_impact=-45, stress_impact=45,
                competency=comp.get("safety_regulations"), competency_points=-45, audio_cue="emergency"
            )

        elif sc.slug == "security-cab-door-intrusion":
            n_start = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Попытка проникновения в кабину",
                character_name="Нарушитель", character_role="Агрессивный пассажир",
                character_mood="critical",
                dialogue_text="«Откройте дверь машиниста! Он несется 400 км/ч, мы разобьемся! Я сам встану за управление поездом!» (ломает ручку кодового замка).",
                narrative_context="Скорость 400 км/ч, вагон № 1. Попытка несанкционированного доступа в кабину управления скоростным электропоездом.",
                time_limit_seconds=18, is_terminal=False
            )
            n_success = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Захват управления предотвращен",
                character_name="Сотрудник транспортной безопасности", character_role="СБ ВСМ",
                character_mood="calm", dialogue_text="«Нарушитель блокирован и обездвижен. Кабина управления защищена. На станции Санкт-Петербург нарушитель сдан сотрудникам ФСБ.»",
                is_terminal=True, is_success=True,
                resolution_report="ВЫСШИЙ БАЛЛ: Проводник применил скрытую тревожную кнопку, защитил вход в кабину машиниста и содействовал охране в задержании злоумышленника."
            )
            n_fail = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Захват кабины управления поездом",
                character_name="ФСБ России", character_role="Антитеррористический центр",
                character_mood="critical", dialogue_text="«Посторонний проник в кабину управления на 400 км/ч из-за слабости или паники проводника!»",
                is_terminal=True, is_success=False,
                resolution_report="КАТАСТРОФИЧЕСКИЙ ПРОВАЛ: Нарушен регламент охраны режимных зон ВСМ. Проникновение посторонних лиц в кабину управления на 400 км/ч создало угрозу крушения поезда."
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Активировать скрытую тревожную сигнализацию, занять оборонительную позицию перед дверью, подать громкую команду: «Отойдите от служебной зоны!» и зафиксировать нарушителя с охраной.",
                tactical_hint="Защита режимных зон высокоскоростного подвижного состава.",
                next_node_key="success", loyalty_impact=15, safety_impact=50, service_impact=20, stress_impact=15,
                competency=comp.get("safety_regulations"), competency_points=45, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Поверить нарушителю, испугаться и открыть ему кодовый замок служебной кабины машиниста на скорости 400 км/ч.",
                tactical_hint="Тягчайшее должностное преступление против безопасности движения.",
                next_node_key="fail", loyalty_impact=-50, safety_impact=-100, service_impact=-50, stress_impact=50,
                competency=comp.get("safety_regulations"), competency_points=-50, audio_cue="emergency"
            )
            ScenarioChoice.objects.create(
                node=n_start, choice_text="Убежать в хвостовой вагон № 10, бросив служебную зону без охраны и никому не сообщив по рации.",
                tactical_hint="Оставление поста безопасности и сокрытие угрозы захвата поезда.",
                next_node_key="fail", loyalty_impact=-45, safety_impact=-90, service_impact=-45, stress_impact=40,
                competency=comp.get("safety_regulations"), competency_points=-45, audio_cue="emergency"
            )

        else:
            n1 = ScenarioNode.objects.create(
                scenario=sc, node_key="start", title="Начало ситуации",
                character_name="Пассажир", character_role="Пассажир ВСМ", character_mood="irritated",
                dialogue_text="«Проводник, обратите внимание на ситуацию!»",
                time_limit_seconds=20, is_terminal=False
            )
            n2 = ScenarioNode.objects.create(
                scenario=sc, node_key="success", title="Успешное завершение",
                character_name="ЛНП", character_role="Начальник поезда", character_mood="calm",
                dialogue_text="«Регламент выполнен в полном объеме!»",
                is_terminal=True, is_success=True,
                resolution_report="Стандарты сервиса и безопасности соблюдены."
            )
            n3 = ScenarioNode.objects.create(
                scenario=sc, node_key="fail", title="Нарушение регламента",
                character_name="Инспектор", character_role="Контролер ВСМ", character_mood="critical",
                dialogue_text="«Допущены нарушения правил безопасности высокоскоростного движения!»",
                is_terminal=True, is_success=False,
                resolution_report="ПРОВАЛ: Действия не соответствовали инструкциям высокоскоростной магистрали."
            )
            ScenarioChoice.objects.create(
                node=n1, choice_text="Действовать строго по инструкции начальника поезда и ПТЭ.",
                tactical_hint="Соблюдение регламента ВСМ.",
                next_node_key="success", loyalty_impact=10, safety_impact=15, service_impact=15, stress_impact=-5,
                competency=comp.get("safety_regulations"), competency_points=25, audio_cue="success"
            )
            ScenarioChoice.objects.create(
                node=n1, choice_text="Проигнорировать регламент и действовать наугад.",
                tactical_hint="Нарушение регламента ВСМ.",
                next_node_key="fail", loyalty_impact=-20, safety_impact=-25, service_impact=-20, stress_impact=20,
                competency=comp.get("safety_regulations"), competency_points=-20, audio_cue="emergency"
            )

    def create_endless_challenges(self):
        """Создание 20 разноуровневых ситуационных карточек для режима бесконечной карусели"""
        EndlessChallenge.objects.all().delete()

        challenges_data = [
            # TIER 1: Базовый уровень (Легкий, 250-280 км/ч, 25 сек)
            {
                "code": "ech_child_ticket",
                "title": "Проезд ребенка до 5 лет без места",
                "category": "tickets",
                "difficulty_level": 1,
                "train_speed": 260,
                "car_info": "Вагон № 7 (Стандарт)",
                "character_name": "Пассажирка с ребенком",
                "character_role": "Мать 3-летнего ребенка",
                "character_mood": "neutral",
                "situation_text": "Пассажирка садится в поезд с 3-летним сыном на руках. У матери есть билет, но отдельный билет на ребенка она не оформляла, утверждая, что 'до 5 лет бесплатно'.",
                "dialogue_text": "«Мне в кассе сказали, что до 5 лет дети едут бесплатно без отдельного места. Зачем мне еще бумажки оформлять?»",
                "timer_seconds": 25,
                "regulation_reference": "Правила оказания услуг по перевозке пассажиров: Проезд ребенка до 5 лет без занятия отдельного места оформляется ОБЯЗАТЕЛЬНЫМ безденежным проездным документом.",
                "competency_code": "service_etiquette",
                "choices_data": [
                    {
                        "id": 1, "text": "Вежливо объяснить: «Да, проезд бесплатный, но закон требует оформления безденежного билета для страховки. Начальник поезда выпишет его прямо сейчас».",
                        "hint": "Оформление безденежного билета на борту без штрафа.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 10, "service_delta": 20, "stress_delta": -5,
                        "feedback": "Верно! Безденежный билет обязателен для страхового покрытия ребенка."
                    },
                    {
                        "id": 2, "text": "Не пускать мать в вагон и отправить обратно в вокзальную кассу за билетом.",
                        "hint": "Высадка мамы с ребенком при мелкой формальности.", "is_correct": False,
                        "loyalty_delta": -35, "safety_delta": -10, "service_delta": -40, "stress_delta": 25,
                        "feedback": "Ошибка! Проводник оформляет ребенка на борту через ЛНП."
                    }
                ]
            },
            {
                "code": "ech_luggage_aisle",
                "title": "Багаж перегородил центральный проход",
                "category": "luggage",
                "difficulty_level": 1,
                "train_speed": 270,
                "car_info": "Вагон № 6 (Комфорт)",
                "character_name": "Пассажир с чемоданом",
                "character_role": "Пассажир места 22",
                "character_mood": "calm",
                "situation_text": "Огромный чемодан на колесиках стоит прямо в проходе вагона, затрудняя движение сервисной тележки и блокируя эвакуационный путь.",
                "dialogue_text": "«Он на полку не помещается, а в ногах мне неудобно. Пусть тут постоит, никому же не мешает!»",
                "timer_seconds": 22,
                "regulation_reference": "ПТЭ и ТБ: Загромождение проходов и путей эвакуации ручной кладью категорически запрещается.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Помочь пассажиру бережно переместить чемодан в специальный багажный накопитель в торце вагона.",
                        "hint": "Освобождение эвакуационного прохода с проявлением заботы.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 25, "service_delta": 20, "stress_delta": -5,
                        "feedback": "Отлично! Проход свободен, пассажир благодарен за помощь."
                    },
                    {
                        "id": 2, "text": "Оставить чемодан в проходе, чтобы не портить настроение пассажиру.",
                        "hint": "Игнорирование требований пожарной безопасности.", "is_correct": False,
                        "loyalty_delta": 0, "safety_delta": -35, "service_delta": -25, "stress_delta": 15,
                        "feedback": "Грубое нарушение! При резком торможении чемодан травмирует людей."
                    }
                ]
            },
            {
                "code": "ech_phone_shield",
                "title": "Просьба зарядки от служебного электрощита",
                "category": "tech",
                "difficulty_level": 1,
                "train_speed": 280,
                "car_info": "Служебное купе проводника",
                "character_name": "Пассажир",
                "character_role": "Гость вагона Стандарт",
                "character_mood": "neutral",
                "situation_text": "Пассажир просит проводника включить его мощное зарядное устройство в розетку на служебном пульте вагона.",
                "dialogue_text": "«У меня телефон сел, а у меня важный звонок! Воткните провод в ваш пульт, у вас же там розетка есть!»",
                "timer_seconds": 20,
                "regulation_reference": "Инструкция по технике электробезопасности: Запрещается подключение бытовых приборов пассажиров к технологическим розеткам щита (110 В постоянного тока).",
                "competency_code": "vsm_tech_protocols",
                "choices_data": [
                    {
                        "id": 1, "text": "Вежливо отказать: «В щите технологическое напряжение, ваш телефон сгорит. Пройдемте к розеткам 220 В у вашего кресла».",
                        "hint": "Предотвращение пожара и решение проблемы гостя штатной розеткой.", "is_correct": True,
                        "loyalty_delta": 10, "safety_delta": 20, "service_delta": 15, "stress_delta": -5,
                        "feedback": "Правильно! Служебный щит защищен от короткого замыкания."
                    },
                    {
                        "id": 2, "text": "Согласиться и воткнуть зарядку в розетку электрощита.",
                        "hint": "Грубейшее нарушение ПТЭ.", "is_correct": False,
                        "loyalty_delta": 5, "safety_delta": -40, "service_delta": -20, "stress_delta": 25,
                        "feedback": "Опасно! Риск выгорания преобразователя и возгорания проводки."
                    }
                ]
            },

            # TIER 2: Повышенный уровень (Средний, 300-330 км/ч, 20 сек)
            {
                "code": "ech_typo_passport",
                "title": "Опечатка в 1 букве фамилии при посадке",
                "category": "tickets",
                "difficulty_level": 2,
                "train_speed": 310,
                "car_info": "Вагон № 2 (Бизнес)",
                "character_name": "Пассажир Ковалев",
                "character_role": "Пассажир бизнес-класса",
                "character_mood": "irritated",
                "situation_text": "В паспорте фамилия 'Ковалев', а в электронном билете кассир вбил 'Коволев' (опечатка в 1 букве). Пассажир волнуется.",
                "dialogue_text": "«Мне в командировку надо! Вы меня пустите в поезд или мне бежать билет менять?!»",
                "timer_seconds": 18,
                "regulation_reference": "Отраслевое распоряжение № 852: При расхождении не более 1 буквы в фамилии и 1 цифры в номере паспорта пассажир ДОПУСКАЕТСЯ к поездке с составлением акта.",
                "competency_code": "service_etiquette",
                "choices_data": [
                    {
                        "id": 1, "text": "«Не переживайте, по правилам 1 буква допускается. Проходите на посадку, в пути начальник поезда составит стандартный акт».",
                        "hint": "Применение телеграммы № 852 без задержки посадки.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 10, "service_delta": 25, "stress_delta": -10,
                        "feedback": "Идеально! Правило одной буквы соблюдено, пассажир спокоен."
                    },
                    {
                        "id": 2, "text": "Отказать в посадке и потребовать сдать билет в кассу вокзала.",
                        "hint": "Нарушение регламента телеграммы 852.", "is_correct": False,
                        "loyalty_delta": -40, "safety_delta": 0, "service_delta": -45, "stress_delta": 30,
                        "feedback": "Грубая ошибка! Пассажир с одной опечаткой допускается к рейсу."
                    }
                ]
            },
            {
                "code": "ech_forgotten_laptop",
                "title": "Забытый ноутбук на сиденье при высадке",
                "category": "service",
                "difficulty_level": 2,
                "train_speed": 320,
                "car_info": "Вагон № 1 (Первый класс)",
                "character_name": "Бортовой журнал",
                "character_role": "Осмотр вагона",
                "character_mood": "formal",
                "situation_text": "После отправления со станции Новая Тверь на кресле 4А обнаружен оставленный дорогой ультрабук в кожаном чехле.",
                "dialogue_text": "«Пассажир сошел на станции Тверь 3 минуты назад. Ноутбук включен.»",
                "timer_seconds": 18,
                "regulation_reference": "Инструкция проводника: Забытые вещи немедленно передаются начальнику поезда с составлением описи по бланку ЛУ-72 и телеграммой на станцию высадки.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Не открывая личные файлы, вызвать ЛНП, составить акт формы ЛУ-72 в 2 экземплярах и направить телеграмму дежурному по вокзалу Тверь.",
                        "hint": "Регламент работы с забытыми вещами пассажиров.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 15, "service_delta": 25, "stress_delta": -5,
                        "feedback": "Образцово! Вещь задокументирована и вернется владельцу."
                    },
                    {
                        "id": 2, "text": "Убрать ноутбук в личный шкаф проводника и подождать, пока владелец сам не позвонит.",
                        "hint": "Утаивание забытых вещей.", "is_correct": False,
                        "loyalty_delta": -25, "safety_delta": -30, "service_delta": -30, "stress_delta": 20,
                        "feedback": "Нарушение! Все находки сдаются только через ЛНП по описи."
                    }
                ]
            },
            {
                "code": "ech_vape_vestibule",
                "title": "Курение вейпа в межвагонном переходе",
                "category": "safety",
                "difficulty_level": 2,
                "train_speed": 330,
                "car_info": "Переход вагон 4-5",
                "character_name": "Молодой пассажир",
                "character_role": "Пассажир с вейпом",
                "character_mood": "calm",
                "situation_text": "Пассажир пускает густой пар от мощного вейпа прямо перед датчиком пожарной сигнализации СПАС-ВО.",
                "dialogue_text": "«Да это же просто пар, не табак! Чего вы придираетесь, пожара не будет!»",
                "timer_seconds": 16,
                "regulation_reference": "Федеральный закон № 15-ФЗ; Регламент пожарной безопасности ВСМ: Курение любых электронных испарителей запрещено, так как аэрозоль вызывает срабатывание СПАС-ВО.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Потребовать немедленно убрать устройство: «Оптические датчики поезда реагируют на аэрозоль как на дым! Это вызовет ложную тревогу состава на 330 км/ч».",
                        "hint": "Четкое техническое объяснение запрета + соблюдение закона.", "is_correct": True,
                        "loyalty_delta": 10, "safety_delta": 25, "service_delta": 15, "stress_delta": -5,
                        "feedback": "Правильно! Оптический датчик СПАС-ВО слеп к составу пара и дает тревогу."
                    },
                    {
                        "id": 2, "text": "Разрешить попарить еще пару минут, если он машет рукой на датчик.",
                        "hint": "Халатность проводника.", "is_correct": False,
                        "loyalty_delta": 5, "safety_delta": -40, "service_delta": -25, "stress_delta": 20,
                        "feedback": "Ошибка! Зуммер СПАС-ВО включит тревогу по всему составу."
                    }
                ]
            },

            # TIER 3: Высокий стресс (Сложный, 350-370 км/ч, 16 сек)
            {
                "code": "ech_overbooking_fast",
                "title": "Овербукинг кресла на скорости 350 км/ч",
                "category": "conflict",
                "difficulty_level": 3,
                "train_speed": 350,
                "car_info": "Вагон № 3 (Комфорт)",
                "character_name": "Пассажир Басов",
                "character_role": "Пассажир",
                "character_mood": "irritated",
                "situation_text": "Два пассажира претендуют на одно кресло 10А. Скандал назревает на глазах всего вагона.",
                "dialogue_text": "«Я сижу здесь! Мой билет куплен неделю назад! Пусть он идет в другой вагон!»",
                "timer_seconds": 15,
                "regulation_reference": "Правила перевозок п. 23: При непредоставлении места пассажиру предоставляется место в вагоне более высокого класса БЕЗ ДОПЛАТЫ.",
                "competency_code": "conflict_resolution",
                "choices_data": [
                    {
                        "id": 1, "text": "«Уважаемые гости! Произошла техническая накладка. Я с удовольствием приглашаю одного из вас занять свободное VIP-кресло в Бизнес-классе без всяких доплат».",
                        "hint": "Апгрейд по п. 23 мгновенно гасит спор.", "is_correct": True,
                        "loyalty_delta": 25, "safety_delta": 15, "service_delta": 30, "stress_delta": -10,
                        "feedback": "Блестяще! Конфликт мгновенно превратился в радость пассажиров."
                    },
                    {
                        "id": 2, "text": "Предложить пассажирам самим бросить жребий на монетке.",
                        "hint": "Непрофессиональное поведение стюарда.", "is_correct": False,
                        "loyalty_delta": -35, "safety_delta": -15, "service_delta": -40, "stress_delta": 30,
                        "feedback": "Провал! Проводник обязан применять регламент перевозок, а не жребий."
                    }
                ]
            },
            {
                "code": "ech_epilepsy_fit",
                "title": "Приступ эпилепсии у пассажира",
                "category": "medical",
                "difficulty_level": 3,
                "train_speed": 360,
                "car_info": "Вагон № 4 (Стандарт)",
                "character_name": "Очевидец",
                "character_role": "Сосед по ряду",
                "character_mood": "panicked",
                "situation_text": "У пассажира судорожный припадок с пеной у рта, соседи пытаются силой разжать ему зубы металлической ложкой!",
                "dialogue_text": "«Держите его! Дайте ложку, надо язык вытащить, он задохнется!»",
                "timer_seconds": 14,
                "regulation_reference": "Протокол первой помощи Минздрава: КАТЕГОРИЧЕСКИ запрещено вставлять твердые предметы в рот. Повернуть на бок, придержать голову.",
                "competency_code": "emergency_medical",
                "choices_data": [
                    {
                        "id": 1, "text": "Отогнать людей с ложкой! Повернуть человека на бок, подложить мягкий валик под голову и вызвать ЛНП по рации.",
                        "hint": "Защита дыхательных путей и профилактика перелома челюсти.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 35, "service_delta": 25, "stress_delta": -5,
                        "feedback": "Спас жизнь! Разжимание зубов ложкой ломает зубы и блокирует трахею."
                    },
                    {
                        "id": 2, "text": "Помочь силой разжать челюсть металлической ложкой.",
                        "hint": "Фатальная доврачебная ошибка.", "is_correct": False,
                        "loyalty_delta": -25, "safety_delta": -50, "service_delta": -30, "stress_delta": 40,
                        "feedback": "Опаснейшее действие! Осколки зубов попадут в дыхательные пути."
                    }
                ]
            },
            {
                "code": "ech_sknb_warning_car",
                "title": "Предупредительный сигнал СКНБ вагона",
                "category": "safety",
                "difficulty_level": 3,
                "train_speed": 365,
                "car_info": "Вагон № 6 (Комфорт)",
                "character_name": "Электрощит вагона",
                "character_role": "Сигнал СКНБ",
                "character_mood": "critical",
                "situation_text": "На панели вагона замигал индикатор СКНБ. Поезд идет на скорости 365 км/ч.",
                "dialogue_text": "«СКНБ: прерывистый сигнал зуммера. Температура буксового узла нарастает.»",
                "timer_seconds": 15,
                "regulation_reference": "Билеты 8, 14: Немедленный вызов машиниста по переговорному устройству для плавного снижения скорости.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Связаться с кабиной управления: «Машинист, СКНБ вагон 6! Требуется плавное служебное снижение хода».",
                        "hint": "Плавное служебное торможение предотвращает сход с рельсов.", "is_correct": True,
                        "loyalty_delta": 10, "safety_delta": 35, "service_delta": 15, "stress_delta": 5,
                        "feedback": "Верно! Экстренный срыв стоп-крана на 365 км/ч запрещен, доклад машинисту обязателен."
                    },
                    {
                        "id": 2, "text": "Сорвать стоп-кран посреди скоростного виража.",
                        "hint": "Резкое торможение на вираже.", "is_correct": False,
                        "loyalty_delta": -30, "safety_delta": -50, "service_delta": -40, "stress_delta": 45,
                        "feedback": "Катастрофическая ошибка! Резкий тормоз на вираже может сбросить состав."
                    }
                ]
            },

            # TIER 4: Высокий риск (Стресс 380 км/ч, 12 сек)
            {
                "code": "ech_fire_bridge_quick",
                "title": "Задымление в туалете на мостовом переходе",
                "category": "safety",
                "difficulty_level": 4,
                "train_speed": 380,
                "car_info": "Вагон № 4 (Стандарт)",
                "character_name": "Испуганный пассажир",
                "character_role": "Пассажир у стоп-крана",
                "character_mood": "panicked",
                "situation_text": "Из туалета валит дым. Поезд несется по мосту через реку Тверца со скоростью 380 км/ч. Пассажир ухватился за рукоятку аварийного тормоза.",
                "dialogue_text": "«Пожар! Мы горим! Я дергаю стоп-кран!»",
                "timer_seconds": 12,
                "regulation_reference": "Инструкция ЦЛ-114: Категорически запрещается остановка поезда на мостах и в тоннелях при возгорании!",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Громко крикнуть: «Стоп! Мы на мосту, тормозить нельзя!», отвести руку от рукоятки и применить огнетушитель ОУ-2.",
                        "hint": "Защита от фатальной остановки на узкой ферме моста.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 40, "service_delta": 20, "stress_delta": 10,
                        "feedback": "Идеально! На мосту останавливаться смертельно опасно."
                    },
                    {
                        "id": 2, "text": "Позволить сорвать стоп-кран, чтобы быстрее выскочить на рельсы.",
                        "hint": "Остановка над обрывом/рекой.", "is_correct": False,
                        "loyalty_delta": -40, "safety_delta": -60, "service_delta": -50, "stress_delta": 50,
                        "feedback": "Крушение! Остановка на ферме заблокировала все двери состава."
                    }
                ]
            },
            {
                "code": "ech_antiterror_box",
                "title": "Бесхозная коробка с проводами в Бистро",
                "category": "anti_terror",
                "difficulty_level": 4,
                "train_speed": 380,
                "car_info": "Вагон № 5 (Бистро)",
                "character_name": "Бармен",
                "character_role": "Сотрудник бистро",
                "character_mood": "panicked",
                "situation_text": "Под барной стойкой обнаружена коробка, обмотанная скотчем, с индикатором питания.",
                "dialogue_text": "«Давай я ее в мусорный бак выброшу за окно на ходу!»",
                "timer_seconds": 12,
                "regulation_reference": "Регламент антитеррора: Запрещено прикасаться, перемещать или выбрасывать подозрительный предмет. Оцепление и доклад по проводной связи.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "«Не трогать! Руки прочь! Спокойно просим гостей перейти в вагон 6 на техобслуживание, оцепляем зону и звоним ЛНП по служебному телефону».",
                        "hint": "Никакого физического воздействия + исключение радиопомех.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 40, "service_delta": 20, "stress_delta": 5,
                        "feedback": "Образцово! Взрывотехники запрещают любые перемещения."
                    },
                    {
                        "id": 2, "text": "Схватить коробку и выбросить в окно на скорости 380 км/ч.",
                        "hint": "Детонация от инерционного датчика.", "is_correct": False,
                        "loyalty_delta": -50, "safety_delta": -70, "service_delta": -60, "stress_delta": 60,
                        "feedback": "Смертельно опасно! При встряске сработает датчик разгрузки."
                    }
                ]
            },
            {
                "code": "ech_drunken_threat",
                "title": "Угроза разбития герметичного стеклопакета",
                "category": "conflict",
                "difficulty_level": 4,
                "train_speed": 385,
                "car_info": "Вагон № 7 (Стандарт)",
                "character_name": "Пьяный пассажир",
                "character_role": "Нарушитель с молотком",
                "character_mood": "irritated",
                "situation_text": "Нетрезвый мужчина сорвал аварийный молоток со стены и замахнулся на окно вагона на скорости 385 км/ч!",
                "dialogue_text": "«Мне душно! Я окно разобью, пусть свежий воздух пойдет!»",
                "timer_seconds": 10,
                "regulation_reference": "ПТЭ ВСМ: Разгерметизация салона на скорости 385 км/ч вызовет баротравмы у всех пассажиров и срыв обшивки потоком воздуха.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Мгновенно перехватить руку с молотком, нажать кнопку вызова охраны поезда и жестко скомандовать нарушителю лечь на пол.",
                        "hint": "Защита целостности гермокабины высокоскоростного поезда.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 40, "service_delta": 20, "stress_delta": 15,
                        "feedback": "Превосходно! Разгерметизация на 385 км/ч привела бы к катастрофе."
                    },
                    {
                        "id": 2, "text": "Уговаривать пассажира стихами и предложить ему чаю.",
                        "hint": "Упущенное время перед ударом.", "is_correct": False,
                        "loyalty_delta": -30, "safety_delta": -60, "service_delta": -40, "stress_delta": 40,
                        "feedback": "Провал! Молоток разбил внешнее стекло, сработал аварийный сброс давления."
                    }
                ]
            },

            # TIER 5: Экстремальный уровень (Кризис на 400 км/ч, 8-10 сек)
            {
                "code": "ech_cpr_cardiac_max",
                "title": "Остановка сердца на скорости 400 км/ч",
                "category": "medical",
                "difficulty_level": 5,
                "train_speed": 400,
                "car_info": "Вагон № 2 (Бизнес)",
                "character_name": "Второй проводник",
                "character_role": "Напарник с АНД",
                "character_mood": "critical",
                "situation_text": "Пассажир без дыхания и пульса на полу. Дефибриллятор АНД подключен, звучит команда: 'Рекомендован разряд!'.",
                "dialogue_text": "«АНД: Идет накопление заряда. Не прикасайтесь к пациенту!»",
                "timer_seconds": 9,
                "regulation_reference": "Протокол сердечно-легочной реанимации: Перед подачей разряда проводник обязан громко скомандовать 'Всем отойти!' и убедиться в отсутствии контакта.",
                "competency_code": "emergency_medical",
                "choices_data": [
                    {
                        "id": 1, "text": "Развести руки, громко скомандовать: «Всем отойти от пациента!», убедиться в изоляции и нажать мигающую кнопку разряда.",
                        "hint": "Защита окружающих от поражения током разряда АНД.", "is_correct": True,
                        "loyalty_delta": 25, "safety_delta": 45, "service_delta": 30, "stress_delta": -10,
                        "feedback": "Жизнь спасена! Ритм сердца успешно восстановлен."
                    },
                    {
                        "id": 2, "text": "Держать пациента за руку, чтобы успокоить во время разряда.",
                        "hint": "Поражение током самого проводника.", "is_correct": False,
                        "loyalty_delta": -40, "safety_delta": -60, "service_delta": -50, "stress_delta": 50,
                        "feedback": "Катастрофа! Проводник сам получил электрический удар от дефибриллятора."
                    }
                ]
            },
            {
                "code": "ech_tunnel_panic_stop",
                "title": "Попытка остановки поезда внутри тоннеля ВСМ",
                "category": "safety",
                "difficulty_level": 5,
                "train_speed": 400,
                "car_info": "Вагон № 3 (Комфорт / Тоннель)",
                "character_name": "Пассажир в панике",
                "character_role": "Пассажир с клаустрофобией",
                "character_mood": "panicked",
                "situation_text": "Поезд летит в 7-километровом тоннеле со скоростью 400 км/ч. Пассажир в приступе клаустрофобии виснет на рукоятке аварийного тормоза.",
                "dialogue_text": "«Мы замурованы под землей! Выпустите меня отсюда немедленно!»",
                "timer_seconds": 8,
                "regulation_reference": "ПТЭ ВСМ: Остановка в скоростном тоннеле категорически запрещена нормами эвакуации.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Телом блокировать рукоятку стоп-крана: «В тоннеле останавливаться нельзя! Через 60 секунд поезд выйдет на открытую трассу!»",
                        "hint": "Предотвращение катастрофы в узком тоннельном створе.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 50, "service_delta": 25, "stress_delta": 10,
                        "feedback": "Подвиг! Остановка в тоннеле на 400 км/ч привела бы к колоссальным перегрузкам."
                    },
                    {
                        "id": 2, "text": "Отпустить стоп-кран и посмотреть, остановится ли поезд в темноте.",
                        "hint": "Аварийное торможение в тоннеле.", "is_correct": False,
                        "loyalty_delta": -50, "safety_delta": -80, "service_delta": -60, "stress_delta": 60,
                        "feedback": "Тяжелейшее ЧП! Состав встал в тоннеле без вентиляции."
                    }
                ]
            },
            {
                "code": "ech_door_seal_breach",
                "title": "Нарушение герметичности наружной двери на 400 км/ч",
                "category": "tech",
                "difficulty_level": 5,
                "train_speed": 400,
                "car_info": "Тамбур вагона № 1",
                "character_name": "Бортовой компьютер",
                "character_role": "СКУД поезда",
                "character_mood": "critical",
                "situation_text": "Свист воздуха в тамбуре. Датчик давления сигнализирует отжим прислонно-сдвижной двери набегающим потоком ветра 400 км/ч.",
                "dialogue_text": "«КРИТИЧЕСКОЕ ПАДЕНИЕ ПРИЖИМА СТВОРКИ ДВЕРИ № 2. ВАКУУМНЫЙ СРЫВ.»",
                "timer_seconds": 8,
                "regulation_reference": "Руководство по эксплуатации ЭВС2: Запрещено приближаться к створке. Немедленная блокировка тамбурной перегородки и сигнал в кабину.",
                "competency_code": "vsm_tech_protocols",
                "choices_data": [
                    {
                        "id": 1, "text": "Закрыть и запереть межтамбурную гермодверь в салон, удалить людей от опасной зоны и по прямой связи передать машинисту код аварии двери.",
                        "hint": "Изоляция салона от взрывной декомпрессии.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 50, "service_delta": 25, "stress_delta": 15,
                        "feedback": "Спасение пассажиров! Гермоперегородка защитила салон от перепада давления."
                    },
                    {
                        "id": 2, "text": "Подойти вплотную к створке и попробовать подтолкнуть ее плечом.",
                        "hint": "Риск выпадения наружу воздушным потоком.", "is_correct": False,
                        "loyalty_delta": -40, "safety_delta": -70, "service_delta": -50, "stress_delta": 60,
                        "feedback": "Фатальная ошибка! Давление воздуха вырвало бы проводника наружу."
                    }
                ]
            },
            {
                "code": "ech_ticket_left_behind",
                "title": "Билет остался у провожающего на перроне вокзала",
                "category": "service",
                "difficulty_level": 1,
                "train_speed": 260,
                "car_info": "Вагон № 4 (Стандарт)",
                "character_name": "Пассажирка в слезах",
                "character_role": "Пассажир без билета на руках",
                "character_mood": "panicked",
                "situation_text": "После отправления поезда из Москвы пассажирка обнаружила, что бумажный билет и посадочный талон остались в сумке провожающего мужа на платформе.",
                "dialogue_text": "«Мой муж унес билет! Вы меня сейчас высадите в лесу на скорости?! У меня только паспорт!»",
                "timer_seconds": 22,
                "regulation_reference": "Билет проводника № 16, вопр. 5; Правила перевозок: При наличии документа, удостоверяющего личность, проводник проверяет электронную базу АСУ 'Экспресс' через терминал УКЭБ или вызывает ЛНП для подтверждения реквизитов.",
                "competency_code": "service_etiquette",
                "choices_data": [
                    {
                        "id": 1, "text": "Успокоить пассажирку: «Не волнуйтесь, все билеты на 'Белый кречет' именные. Я сверю ваш паспорт с ведомостью УКЭБ через терминал, и вы продолжите поездку без штрафов».",
                        "hint": "Проверка электронной базы УКЭБ без паники.", "is_correct": True,
                        "loyalty_delta": 25, "safety_delta": 10, "service_delta": 25, "stress_delta": -15,
                        "feedback": "Идеально! Паспорт проверен по базе УКЭБ, статус посадки подтвержден."
                    },
                    {
                        "id": 2, "text": "Заявить: «Без билета проезд запрещен! На ближайшей станции Зеленоград сдаю вас полиции!».",
                        "hint": "Грубейшее нарушение клиентоориентированности и правил.", "is_correct": False,
                        "loyalty_delta": -45, "safety_delta": -15, "service_delta": -40, "stress_delta": 35,
                        "feedback": "Грубая ошибка! Все билеты ВСМ оформляются по паспорту и дублируются в системе."
                    }
                ]
            },
            {
                "code": "ech_pet_carrier_rules",
                "title": "Провоз собаки крупной породы без намордника",
                "category": "service",
                "difficulty_level": 2,
                "train_speed": 310,
                "car_info": "Вагон № 6 (Комфорт с животными)",
                "character_name": "Владелец овчарки",
                "character_role": "Пассажир с собакой",
                "character_mood": "irritated",
                "situation_text": "В специализированной зоне для перевозки животных пассажир снял намордник с крупной немецкой овчарки. Собака рычит на проходящих людей.",
                "dialogue_text": "«Ей жарко и душно в наморднике! Она у меня дрессированная, никого не тронет!»",
                "timer_seconds": 18,
                "regulation_reference": "Билет проводника № 13, вопр. 4; Правила перевозки домашних животных: Крупные собаки перевозятся исключительно в наморднике и на поводке под постоянным контролем владельца.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "Твердо и вежливо потребовать надеть намордник: «По правилам ВСМ безопасность всех пассажиров приоритетна. При отказе мы будем вынуждены изолировать животное или передать информацию ЛНП».",
                        "hint": "Соблюдение правил перевозки животных и защита пассажиров.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 25, "service_delta": 20, "stress_delta": -5,
                        "feedback": "Верно! Намордник надет, риск укуса в узком проходе предотвращен."
                    },
                    {
                        "id": 2, "text": "Разрешить оставить собаку без намордника, если хозяин держит ее за ошейник.",
                        "hint": "Нарушение техники безопасности перевозки животных.", "is_correct": False,
                        "loyalty_delta": -20, "safety_delta": -40, "service_delta": -25, "stress_delta": 30,
                        "feedback": "Опасно! При толчке или резком звуке на 300 км/ч собака может напасть на соседа."
                    }
                ]
            },
            {
                "code": "ech_passenger_trauma",
                "title": "Падение и ушиб пассажира при маневре поезда",
                "category": "safety",
                "difficulty_level": 3,
                "train_speed": 350,
                "car_info": "Вагон № 5 (Бистро)",
                "character_name": "Пожилой пассажир",
                "character_role": "Пострадавший пассажир",
                "character_mood": "panicked",
                "situation_text": "При прохождении стрелочного перегона пассажир не удержался за поручень, упал и сильно рассек бровь о край столика бистро.",
                "dialogue_text": "«Ой, голова кружится, кровь течет! Что у вас за поезд такой резкий?!»",
                "timer_seconds": 15,
                "regulation_reference": "Билет проводника № 19, вопр. 4; Инструкция по оказанию доврачебной помощи: Проводник обязан обработать рану асептической повязкой, усадить пострадавшего, вызвать ЛНП и составить Акт о несчастном случае на бланке формы НУ-1.",
                "competency_code": "emergency_medical",
                "choices_data": [
                    {
                        "id": 1, "text": "Усадить пассажира, вскрыть вагонную аптечку, наложить стерильную давящую повязку, приложить гипотермический пакет со льдом и вызвать ЛНП для оформления акта формы НУ-1.",
                        "hint": "Полный регламент первой помощи и документального оформления производственной травмы.", "is_correct": True,
                        "loyalty_delta": 25, "safety_delta": 30, "service_delta": 25, "stress_delta": -5,
                        "feedback": "Образцово! Кровотечение остановлено, акт оформлен, вызвана медслужба."
                    },
                    {
                        "id": 2, "text": "Дать пассажиру бумажную салфетку и сказать, чтобы сам зажал рану до Санкт-Петербурга.",
                        "hint": "Отказ в квалифицированной помощи.", "is_correct": False,
                        "loyalty_delta": -45, "safety_delta": -50, "service_delta": -45, "stress_delta": 40,
                        "feedback": "Грубейшее неоказание помощи! Рана инфицирована, риск сотрясения мозга."
                    }
                ]
            },
            {
                "code": "ech_body_ground_fault",
                "title": "Срабатывание контроля изоляции: замыкание на корпус вагона",
                "category": "tech",
                "difficulty_level": 4,
                "train_speed": 380,
                "car_info": "Служебное купе вагона № 2",
                "character_name": "Пульт электрооборудования",
                "character_role": "Светодиод 'ЗЕМЛЯ (+)'",
                "character_mood": "critical",
                "situation_text": "На распределительном щите вагона загорелся красный индикатор системы контроля утечки тока на кузов вагона ('Земля в цепи').",
                "dialogue_text": "«ЗВУКОВОЙ ЗУММЕР ЩИТА: УТЕЧКА ТОКА В ЦЕПИ ПОСТОЯННОГО НАПРЯЖЕНИЯ 110В.»",
                "timer_seconds": 12,
                "regulation_reference": "Билет проводника № 12, вопр. 3; Инструкция по обслуживанию электрооборудования: Запрещено включение мощных потребителей. Проводник обязан поочередным отключением групп потребителей определить аварийную цепь и доложить поездному электромеханику.",
                "competency_code": "vsm_tech_protocols",
                "choices_data": [
                    {
                        "id": 1, "text": "Обесточить второстепенные потребители (климатический догреватель, розетки), методом поочередного тумблерного опроса выявить поврежденную группу и немедленно вызвать поездного электромеханика (ПЭМ).",
                        "hint": "Локализация замыкания на корпус по инструкции ПЭУ.", "is_correct": True,
                        "loyalty_delta": 15, "safety_delta": 40, "service_delta": 20, "stress_delta": -5,
                        "feedback": "Профессионально! Предотвращено короткое замыкание и возгорание изоляции."
                    },
                    {
                        "id": 2, "text": "Наклеить скотч на зуммер, чтобы он не пищал, и продолжить раздачу чая.",
                        "hint": "Преступная халатность при утечке тока на корпус.", "is_correct": False,
                        "loyalty_delta": -30, "safety_delta": -70, "service_delta": -40, "stress_delta": 50,
                        "feedback": "Угроза пожара! Утечка на корпус привела к пробою изоляции на высокой скорости."
                    }
                ]
            },
            {
                "code": "ech_tail_signal_failure",
                "title": "Отказ красных хвостовых огней экспресса в ночи на 400 км/ч",
                "category": "safety",
                "difficulty_level": 5,
                "train_speed": 400,
                "car_info": "Хвостовой вагон № 8",
                "character_name": "Система локомотивной сигнализации",
                "character_role": "Бортовой мониторинг",
                "character_mood": "critical",
                "situation_text": "Ночной рейс на скорости 400 км/ч. Датчик сообщает о погасании всех трех красных габаритных хвостовых огней вагона № 8.",
                "dialogue_text": "«ТРЕВОГА: ПОЕЗД НЕ ОСВЕЩАЕТ ХВОСТ С СООТВЕТСТВИИ С ПТЭ. УГРОЗА ПОПУТНОГО СТОЛКНОВЕНИЯ.»",
                "timer_seconds": 8,
                "regulation_reference": "Билет проводника № 18, вопр. 3; ПТЭ: Хвост пассажирского поезда обозначается 3 красными огнями. При их неисправности проводник хвостового вагона обязан немедленно уведомить машиниста и задействовать резервные аккумуляторные фонари.",
                "competency_code": "safety_regulations",
                "choices_data": [
                    {
                        "id": 1, "text": "По переговорному устройству доложить машинисту, включить аварийные автономные красные светодиодные буферные фонари и лично визуально проконтролировать их свечение.",
                        "hint": "Обеспечение видимости хвоста состава согласно ПТЭ.", "is_correct": True,
                        "loyalty_delta": 20, "safety_delta": 50, "service_delta": 25, "stress_delta": 10,
                        "feedback": "Идеально! Хвост поезда снова обозначен, безопасность магистрали соблюдена."
                    },
                    {
                        "id": 2, "text": "Решить, что на 400 км/ч нас никто сзади не догонит, и подождать прибытия в Санкт-Петербург.",
                        "hint": "Нарушение ПТЭ по обозначению подвижного состава.", "is_correct": False,
                        "loyalty_delta": -35, "safety_delta": -80, "service_delta": -50, "stress_delta": 60,
                        "feedback": "Катастрофическое нарушение ПТЭ! Поезд невидим для попутных диагностических комплексов."
                    }
                ]
            }
        ]

        for cd in challenges_data:
            EndlessChallenge.objects.update_or_create(
                code=cd["code"],
                defaults=cd
            )

        print(f"Успешно создано {len(challenges_data)} задач для режима бесконечной карусели.")

        from django.core.management import call_command
        try:
            call_command('seed_regulations')
            call_command('seed_official_scenarios')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Внимание при сидировании официальных регламентов: {e}"))

        from simulator.views import sync_scenarios_and_challenges
        synced_count = sync_scenarios_and_challenges()
        self.stdout.write(self.style.SUCCESS(f"Двусторонняя синхронизация завершена: {synced_count} задач из сценариев перенесены в карусель!"))
