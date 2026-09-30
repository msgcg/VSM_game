from django.core.management.base import BaseCommand
from simulator.models import Scenario, ScenarioNode, ScenarioChoice, Competency


class Command(BaseCommand):
    help = "Заполнение базы данных 20 официальными интерактивными сценариями ВСМ из СТО ВСМ и практического руководства"

    def handle(self, *args, **options):
        self.stdout.write("Начало загрузки официальных сценариев ВСМ...")

        # Обеспечиваем наличие базовых компетенций
        competency_map = {
            'service_etiquette': Competency.objects.get_or_create(
                code='service_etiquette',
                defaults={
                    'title': 'Сервисный этикет и клиентоориентированность',
                    'description': 'Соблюдение ролевой модели сервисного общения ВСМ, эмпатия и стандарты премиального сервиса.',
                    'icon': 'sparkles',
                    'color': '#00d2ff'
                }
            )[0],
            'conflict_resolution': Competency.objects.get_or_create(
                code='conflict_resolution',
                defaults={
                    'title': 'Урегулирование конфликтов и стрессоустойчивость',
                    'description': 'Предотвращение эскалации претензий, деэскалация споров и защита психологического комфорта на скорости 400 км/ч.',
                    'icon': 'shield-alert',
                    'color': '#f59e0b'
                }
            )[0],
            'safety_regulations': Competency.objects.get_or_create(
                code='safety_regulations',
                defaults={
                    'title': 'Безопасность движения и транспортная безопасность',
                    'description': 'Неукоснительное исполнение ПТЭ, антитеррористических протоколов, пожарной безопасности и действий с ПТБ.',
                    'icon': 'shield-check',
                    'color': '#10b981'
                }
            )[0],
            'emergency_medical': Competency.objects.get_or_create(
                code='emergency_medical',
                defaults={
                    'title': 'Первая помощь и действия в чрезвычайных ситуациях',
                    'description': 'Алгоритмы реанимации, применение дефибриллятора АНД, эвакуация и координация с медицинскими службами.',
                    'icon': 'heart-pulse',
                    'color': '#ef4444'
                }
            )[0],
            'vsm_tech_protocols': Competency.objects.get_or_create(
                code='vsm_tech_protocols',
                defaults={
                    'title': 'Технические регламенты и системы поезда ВСМ',
                    'description': 'Эксплуатация бортового оборудования «Белый кречет», климат-контроля, СКНБ, ЭЧТК и мобильного терминала ММТ.',
                    'icon': 'cpu',
                    'color': '#8b5cf6'
                }
            )[0],
            'mobility_assistance': Competency.objects.get_or_create(
                code='mobility_assistance',
                defaults={
                    'title': 'Обслуживание маломобильных пассажиров (МГН)',
                    'description': 'Требования стандарта СТО ВСМ 03.014–2026: подъемные механизмы, фиксаторы колясок, безбарьерное сопровождение.',
                    'icon': 'accessibility',
                    'color': '#06b6d4'
                }
            )[0],
        }

        # Список 20 официальных сценариев
        scenarios_data = [
            {
                'title': 'Посадка без действительного билета',
                'slug': 'boarding-no-ticket',
                'category': 'conflict',
                'difficulty': 'easy',
                'train_speed': 0,
                'train_number': '№ 702 «Белый кречет» Москва — Санкт-Петербург',
                'location_name': 'Москва-Пассажирская, посадочная платформа № 1',
                'car_info': 'Вагон № 2 (Бизнес-класс)',
                'description': 'Пассажир подошел на посадку без проездного документа, заявляя об оплате на стороннем сайте и сбое приложения.',
                'briefing': 'За 4 минуты до отправления пассажир пытается пройти в вагон. Билета нет, есть только смс о списании средств. Ваши действия согласно СТО ВСМ 03.011–2026 (раздел 7.1).',
                'regulation_reference': 'СТО ВСМ 03.011–2026, раздел 7.1; Ситуации на борту (Кейс 1)',
                'background_image': 'sc_platform_boarding.jpg',
                'base_xp': 200,
                'time_limit_default': 25,
                'order': 1,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': 'Посадка без билета у двери вагона',
                        'character_name': 'Опаздывающий пассажир',
                        'character_role': 'Пассажир бизнес-класса',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Пропустите меня в вагон! Я опаздываю на важнейшую встречу в Петербурге, деньги с карты списали, вот смс! В поезде разберемся!»',
                        'narrative_context': 'Платформа ВСМ. До закрытия автоматических дверей 4 минуты. Мобильный терминал ММТ включен.',
                        'time_limit_seconds': 25,
                        'timeout_next_node_key': 'timeout_fail',
                        'choices': [
                            {
                                'text': '«Я Вас понимаю, ситуация неприятная. Позвольте Ваш паспорт: я за секунду проверю статус билета в единой базе через терминал ММТ».',
                                'hint': 'Ролевая модель ВСМ: признать ситуацию, предложить конкретный технологический шаг.',
                                'next_key': 'ticket_found',
                                'loyalty': 15,
                                'safety': 10,
                                'comp': 'service_etiquette',
                                'comp_pts': 15,
                                'feedback': 'Отличная реакция по ролевой модели СТО ВСМ 03.011–2026.'
                            },
                            {
                                'text': '«Вход строго по билетам. Без документа посадка категорически запрещена, отойдите от вагона».',
                                'hint': 'Сухой жесткий отказ без эмпатии провоцирует публичный конфликт.',
                                'next_key': 'conflict_escalation',
                                'loyalty': -20,
                                'safety': 5,
                                'comp': 'conflict_resolution',
                                'comp_pts': -5,
                                'feedback': 'Грубый отказ спровоцировал конфликт на платформе.'
                            },
                            {
                                'text': '«Ладно, проходите в тамбур, пока двери не закрылись, потом проверим».',
                                'hint': 'Грубейшее нарушение регламента: безбилетный проход в скоростной экспресс.',
                                'next_key': 'security_breach',
                                'loyalty': 10,
                                'safety': -35,
                                'comp': 'safety_regulations',
                                'comp_pts': -20,
                                'feedback': 'Критическое нарушение транспортной безопасности.'
                            }
                        ]
                    },
                    {
                        'node_key': 'ticket_found',
                        'title': 'Успешная верификация через ММТ',
                        'character_name': 'Успокоенный пассажир',
                        'character_role': 'Пассажир бизнес-класса',
                        'character_mood': 'calm',
                        'dialogue_text': '«Спасибо вам огромное! Действительно, электронный билет привязался к паспорту. Прошу прощения за эмоции».',
                        'narrative_context': 'Терминал ММТ подтвердил место 14 в вагоне № 2. Посадка завершена вовремя.',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': 'Идеальное применение ролевой модели СТО ВСМ 03.011–2026. Пассажир допущен на законных основаниях, лояльность повышена, график не нарушен.',
                        'choices': []
                    },
                    {
                        'node_key': 'conflict_escalation',
                        'title': 'Эскалация конфликта на платформе',
                        'character_name': 'Разгневанный пассажир',
                        'character_role': 'Пассажир',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Я буду жаловаться в администрацию! Вы срываете мне сделку! Немедленно зовите начальника поезда!»',
                        'narrative_context': 'Пассажир встал в створе двери, мешая закрытию створок. Срыв графика отправления.',
                        'time_limit_seconds': 15,
                        'timeout_next_node_key': 'timeout_fail',
                        'choices': [
                            {
                                'text': '«Приношу извинения за резкость. Давайте спокойно проверим паспорт прямо сейчас, у нас есть еще 2 минуты».',
                                'hint': 'Попытка деэскалации и исправления ошибки.',
                                'next_key': 'ticket_found',
                                'loyalty': 5,
                                'safety': 5,
                                'comp': 'conflict_resolution',
                                'comp_pts': 10,
                                'feedback': 'Удалось перехватить инициативу и предотвратить срыв графика.'
                            },
                            {
                                'text': '«Охрана, уберите этого гражданина с платформы!»',
                                'hint': 'Силовой сценарий ведет к официальной жалобе.',
                                'next_key': 'forced_removal',
                                'loyalty': -35,
                                'safety': -10,
                                'comp': 'conflict_resolution',
                                'comp_pts': -15,
                                'feedback': 'Срыв отправления поезда и официальная претензия.'
                            }
                        ]
                    },
                    {
                        'node_key': 'security_breach',
                        'title': 'Провал безопасности',
                        'character_name': 'Инструктор поездных бригад',
                        'character_role': 'Контролирующее лицо',
                        'character_mood': 'formal',
                        'dialogue_text': '«Проводник, вы допустили безбилетного гражданина на борт высокоскоростного состава без проверки личности. Это грубое нарушение ПТЭ».',
                        'narrative_context': 'Акт проверки. Отстранение от смены.',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Грубейшее нарушение транспортной безопасности. Безбилетный проход в скоростной поезд 400 км/ч категорически недопустим.',
                        'choices': []
                    },
                    {
                        'node_key': 'forced_removal',
                        'title': 'Провал сервиса',
                        'character_name': 'Дежурный по вокзалу',
                        'character_role': 'Администрация вокзала',
                        'character_mood': 'formal',
                        'dialogue_text': '«Поезд задержан на 3 минуты из-за скандала у вагона. Оформлен протокол разногласий».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Проводник не применил ролевую модель эмпатии и спровоцировал задержку высокоскоростного экспресса.',
                        'choices': []
                    },
                    {
                        'node_key': 'timeout_fail',
                        'title': 'Истекло время на принятие решения',
                        'character_name': 'Система безопасности ВСМ',
                        'character_role': 'Автоматика поезда',
                        'character_mood': 'formal',
                        'dialogue_text': '«Время на принятие решения истекло. Автоматика состава заблокировала створки дверей в аварийном режиме».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Таймаут проводника. В скоростном движении задержка решений ведет к срыву графика и падению показателей.',
                        'choices': []
                    }
                ]
            },
            {
                'title': 'Обслуживание маломобильного пассажира в кресле-коляске',
                'slug': 'mobility-wheelchair-boarding',
                'category': 'vip_service',
                'difficulty': 'medium',
                'train_speed': 0,
                'train_number': '№ 704 «Белый кречет»',
                'location_name': 'Санкт-Петербург Главный, путь № 3',
                'car_info': 'Вагон № 3 (Комфорт для МГН)',
                'description': 'Посадка маломобильного пассажира на электроколяске с использованием бортового подъемного механизма.',
                'briefing': 'К вагону прибыл пассажир из числа МГН с билетом на специализированное место. Отработайте алгоритм стандарта СТО ВСМ 03.014–2026.',
                'regulation_reference': 'СТО ВСМ 03.014–2026, разделы 3, 6, 7; Распоряжение № 989/р',
                'background_image': 'sc_mobility_assist.jpg',
                'base_xp': 280,
                'time_limit_default': 30,
                'order': 2,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': 'Встреча пассажира МГН у вагона',
                        'character_name': 'Михаил Сергеевич',
                        'character_role': 'Пассажир в кресле-коляске',
                        'character_mood': 'calm',
                        'dialogue_text': '«Здравствуйте! У меня место 1 в специализированном вагоне. Подскажите, как мы организуем подъем в салон?»',
                        'narrative_context': 'Вагон оснащен интегрированным рамповым подъемником. До отправления 25 минут.',
                        'time_limit_seconds': 30,
                        'timeout_next_node_key': 'timeout_fail',
                        'choices': [
                            {
                                'text': '«Здравствуйте, Михаил Сергеевич! Рады приветствовать Вас. Сейчас активирую подъемник, плавно поднимем платформу и зафиксируем коляску на месте».',
                                'hint': 'Обращение по имени-отчеству, персональное внимание, соблюдение СТО ВСМ 03.014–2026.',
                                'next_key': 'lift_operation',
                                'loyalty': 20,
                                'safety': 15,
                                'comp': 'mobility_assistance',
                                'comp_pts': 20,
                                'feedback': 'Идеальное следование этикету доступной среды ВСМ.'
                            },
                            {
                                'text': '«Подождите, я сейчас позову грузчиков, мы вас на руках занесем».',
                                'hint': 'Грубое нарушение: перенос коляски на руках опасен и унизителен.',
                                'next_key': 'manual_carry_fail',
                                'loyalty': -25,
                                'safety': -30,
                                'comp': 'mobility_assistance',
                                'comp_pts': -15,
                                'feedback': 'Запрещено правилами СТО ВСМ 03.014–2026.'
                            }
                        ]
                    },
                    {
                        'node_key': 'lift_operation',
                        'title': 'Размещение и фиксация в салоне',
                        'character_name': 'Михаил Сергеевич',
                        'character_role': 'Пассажир',
                        'character_mood': 'calm',
                        'dialogue_text': '«Очень плавный подъемник! Как здесь уютно. Где расположена кнопка связи со стюардом?»',
                        'narrative_context': 'Коляска заведена на специализированное место. Необходимо закрепить штатные ремни безопасности.',
                        'time_limit_seconds': 25,
                        'choices': [
                            {
                                'text': 'Зафиксировать стопоры колес и ремни безопасности, показать сенсорную кнопку вызова и мнемосхему санузла.',
                                'hint': 'Полный регламент обеспечения безопасности МГН на скорости 400 км/ч.',
                                'next_key': 'success_mobility',
                                'loyalty': 20,
                                'safety': 20,
                                'comp': 'mobility_assistance',
                                'comp_pts': 20,
                                'feedback': 'Полное соблюдение правил комфорта и безопасности.'
                            },
                            {
                                'text': 'Ограничиться включением стояночного тормоза коляски, не пристегивая ремни безопасности ВСМ.',
                                'hint': 'На скорости 400 км/ч пассажир без штатных ремней не защищен от боковых ускорений и аварийного торможения.',
                                'next_key': 'manual_carry_fail',
                                'loyalty': -20,
                                'safety': -40,
                                'comp': 'mobility_assistance',
                                'comp_pts': -20,
                                'feedback': 'Грубейшее нарушение СТО ВСМ 03.014–2026: фиксация ремнями обязательна!'
                            }
                        ]
                    },
                    {
                        'node_key': 'success_mobility',
                        'title': 'Безупречное обслуживание МГН',
                        'character_name': 'Михаил Сергеевич',
                        'character_role': 'Пассажир',
                        'character_mood': 'calm',
                        'dialogue_text': '«Благодарю за высочайший уровень сервиса и чуткость! Впервые чувствую себя настолько комфортно в поезде».',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': 'Успешное выполнение требований СТО ВСМ 03.014–2026. Пассажир благополучно размещен с соблюдением всех мер безопасности скоростного движения.',
                        'choices': []
                    },
                    {
                        'node_key': 'manual_carry_fail',
                        'title': 'Нарушение регламента доступной среды',
                        'character_name': 'Михаил Сергеевич',
                        'character_role': 'Пассажир',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Вы нарушаете мои права! В высокоскоростном поезде XXI века вы предлагаете тащить электроколяску весом 100 кг на руках?!»',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Грубейшее нарушение стандарта обслуживания маломобильных пассажиров. На всех поездах ВСМ подъем осуществляется только сертифицированным подъемником.',
                        'choices': []
                    },
                    {
                        'node_key': 'timeout_fail',
                        'title': 'Просрочен норматив посадки',
                        'character_name': 'Начальник поезда',
                        'character_role': 'ЛНП',
                        'character_mood': 'formal',
                        'dialogue_text': '«Проводник, посадка маломобильного пассажира должна начинаться за 30 минут до отправления. Вы затянули время».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Нарушен временной регламент посадки пассажиров из числа МГН.',
                        'choices': []
                    }
                ]
            },
            {
                'title': 'Провоз домашнего питомца без переноски',
                'slug': 'pet-without-carrier',
                'category': 'service',
                'difficulty': 'easy',
                'train_speed': 360,
                'train_number': '№ 706 «Белый кречет»',
                'location_name': 'Перегон Новая Тверь — Выползово, скорость 360 км/ч',
                'car_info': 'Вагон № 5 (Стандарт)',
                'description': 'Пассажирка везет собаку декоративной породы без переноски на коленях, нарушая СТО ВСМ 03.011–2026.',
                'briefing': 'На скорости 360 км/ч пассажирка держит собаку на руках. Соседи выражают беспокойство. Примените ролевую модель ВСМ (Кейс 4).',
                'regulation_reference': 'СТО ВСМ 03.011–2026, раздел 7.8; Ситуации на борту (Кейс 4)',
                'background_image': 'sc_pet_carrier.jpg',
                'base_xp': 220,
                'time_limit_default': 25,
                'order': 3,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': 'Диалог с владелицей питомца',
                        'character_name': 'Анна',
                        'character_role': 'Пассажирка с собачкой',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Мой шпиц совсем крошечный и тихий, он в переноске задыхается! Почему я не могу подержать его на коленях, кому он мешает?!»',
                        'narrative_context': 'Скорость 360 км/ч. При торможении или толчке животное может упасть.',
                        'time_limit_seconds': 25,
                        'choices': [
                            {
                                'text': '«Я Вас понимаю, расставаться с питомцем не хочется. Но на скорости до 400 км/ч нахождение в переноске защищает его от травм при торможении. Вы можете приобрести мягкую переноску из каталога на борту».',
                                'hint': 'Сделать акцент на безопасности питомца: о нем заботятся, а не отчитывают.',
                                'next_key': 'carrier_accepted',
                                'loyalty': 15,
                                'safety': 15,
                                'comp': 'service_etiquette',
                                'comp_pts': 15,
                                'feedback': 'Идеальное сервисное общение по формуле СТО ВСМ 03.011–2026.'
                            },
                            {
                                'text': '«Немедленно уберите собаку, иначе на следующей станции мы высадим вас с полицией!»',
                                'hint': 'Угрозы высадкой вызывают агрессию и жалобу.',
                                'next_key': 'pet_scandal',
                                'loyalty': -25,
                                'safety': 5,
                                'comp': 'conflict_resolution',
                                'comp_pts': -10,
                                'feedback': 'Агрессивная манера общения недопустима на ВСМ.'
                            }
                        ]
                    },
                    {
                        'node_key': 'carrier_accepted',
                        'title': 'Проблема решена в пользу безопасности',
                        'character_name': 'Анна',
                        'character_role': 'Пассажирка',
                        'character_mood': 'calm',
                        'dialogue_text': '«Вы правы, я не подумала о скорости. Давайте приобретем переноску из каталога, спасибо за заботу о песике».',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': 'Проводник проявил заботу и защитил правила перевозки животных без конфликта.',
                        'choices': []
                    },
                    {
                        'node_key': 'pet_scandal',
                        'title': 'Жалоба на грубость персонала',
                        'character_name': 'Анна',
                        'character_role': 'Пассажирка',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Такой тон неприемлем для скоростного поезда! Требую книгу отзывов и вызов начальника поезда!»',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Нарушен стандарт коммуникации с пассажирами. Провокация жалобы на ровном месте.',
                        'choices': []
                    }
                ]
            },
            {
                'title': 'Неисправность блока розеток и мультимедиа',
                'slug': 'broken-power-outlet',
                'category': 'tech_failure',
                'difficulty': 'medium',
                'train_speed': 380,
                'train_number': '№ 708 «Белый кречет»',
                'location_name': 'Перегон Валдай — Горки',
                'car_info': 'Вагон № 1 (Первый класс)',
                'description': 'В первом классе отказала розетка 220V и сенсорный монитор перед важным видеозвонком топ-менеджера.',
                'briefing': 'Пассажир первого класса возмущен отказом оборудования. Отработайте кейс по СТО ВСМ 03.013–2026 и Ситуациям на борту (Кейс 16).',
                'regulation_reference': 'СТО ВСМ 03.013–2026, разд. 3; Ситуации на борту (Кейс 16)',
                'background_image': 'vsm_interior_couple.jpg',
                'base_xp': 250,
                'time_limit_default': 25,
                'order': 4,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': 'Претензия по электрооборудованию',
                        'character_name': 'Владимир Павлович',
                        'character_role': 'Пассажир Первого класса',
                        'character_mood': 'irritated',
                        'dialogue_text': '«У меня через 15 минут онлайн-совет директоров! Розетка не работает, ноутбук разряжен, экран завис! За что я заплатил деньги?!»',
                        'narrative_context': 'Блок кресла 1А. Индикатор напряжения на розетке не горит.',
                        'time_limit_seconds': 25,
                        'choices': [
                            {
                                'text': '«Владимир Павлович, искренне прошу прощения за доставленные неудобства! Немедленно предоставляю мощный бортовой пауэрбанк Type-C, а также приглашаю за соседнее свободное место 2А».',
                                'hint': 'Быстрая компенсация дефекта: альтернативное питание + предложение свободного места.',
                                'next_key': 'solution_success',
                                'loyalty': 25,
                                'safety': 10,
                                'comp': 'vsm_tech_protocols',
                                'comp_pts': 20,
                                'feedback': 'Высочайший класс сервисного реагирования.'
                            },
                            {
                                'text': '«Ну это техника, бывает. Подождите, придет бортинженер минут через сорок и посмотрит щиток».',
                                'hint': 'Безразличие и перекладывание вины на технику.',
                                'next_key': 'tech_fail',
                                'loyalty': -30,
                                'safety': -5,
                                'comp': 'service_etiquette',
                                'comp_pts': -15,
                                'feedback': 'Пассажир первого класса сорвал совещание. Крупная претензия.'
                            }
                        ]
                    },
                    {
                        'node_key': 'solution_success',
                        'title': 'Вопрос решен мгновенно',
                        'character_name': 'Владимир Павлович',
                        'character_role': 'Пассажир',
                        'character_mood': 'calm',
                        'dialogue_text': '«Оперативно сработали, спасибо! Ноутбук заряжается, пересел на 2А, звонок спасен. Вот это уровень ВСМ».',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': 'Образцовое решение технического инцидента. Пассажир сохранил лояльность, передана заявка бортинженеру в журнал ВУ-8.',
                        'choices': []
                    },
                    {
                        'node_key': 'tech_fail',
                        'title': 'Провал в Первом классе',
                        'character_name': 'Владимир Павлович',
                        'character_role': 'Пассажир',
                        'character_mood': 'irritated',
                        'dialogue_text': '«Мое совещание сорвано! Я оформляю официальную претензию в руководство магистрали о возврате стоимости билета и компенсации!»',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Проводник проявил безучастность, не предложив резервные источники питания и свободные места.',
                        'choices': []
                    }
                ]
            },
            {
                'title': 'Медицинский инцидент: сердечный приступ на скорости 400 км/ч',
                'slug': 'medical-cardiac-emergency',
                'category': 'medical',
                'difficulty': 'hard',
                'train_speed': 400,
                'train_number': '№ 710 «Белый кречет»',
                'location_name': 'Скоростной участок Великий Новгород — Санкт-Петербург, 400 км/ч',
                'car_info': 'Вагон № 4 (Стандарт)',
                'description': 'Пассажир среднего возраста внезапно побледнел, схватился за сердце и теряет сознание.',
                'briefing': 'Срочная ситуация первой помощи на максимальной скорости магистрали. Примените регламент СТО ВСМ 03.011–2026 (раздел 10) и Ситуации на борту (Кейс 19).',
                'regulation_reference': 'СТО ВСМ 03.011–2026, раздел 10; Приказ Минздрава № 477н; Ситуации на борту (Кейс 19)',
                'background_image': 'sc_cardiac_emergency.jpg',
                'base_xp': 350,
                'time_limit_default': 20,
                'order': 5,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': 'Экстренное состояние пассажира',
                        'character_name': 'Сосед по ряду',
                        'character_role': 'Взволнованный пассажир',
                        'character_mood': 'panicked',
                        'dialogue_text': '«Проводник, скорей сюда! Мужчина хрипит, держится за сердце и синеет! Дайте ему валидол из своей сумки!»',
                        'narrative_context': 'Скорость 400 км/ч. Пассажир без сознания, дыхание слабое.',
                        'time_limit_seconds': 20,
                        'timeout_next_node_key': 'med_timeout',
                        'choices': [
                            {
                                'text': 'Немедленно вызвать начальника поезда по рации, доставить бортовой дефибриллятор АНД и аптечку, объявить по громкой связи поиск медика среди пассажиров.',
                                'hint': 'Единственно верный алгоритм: вызов ЛНП, подготовка АНД, поиск врача. Личные таблетки давать категорически запрещено!',
                                'next_key': 'med_actions',
                                'loyalty': 20,
                                'safety': 30,
                                'comp': 'emergency_medical',
                                'comp_pts': 25,
                                'feedback': 'Безупречное исполнение протокола первой помощи.'
                            },
                            {
                                'text': 'Достать из своего кармана таблетку нитроглицерина и положить пассажиру под язык.',
                                'hint': 'Грубейшее правонарушение: проводнику запрещено назначать и давать рецептурные медикаменты.',
                                'next_key': 'med_fatal_error',
                                'loyalty': -20,
                                'safety': -40,
                                'comp': 'emergency_medical',
                                'comp_pts': -30,
                                'feedback': 'Смертельно опасная ошибка! У пассажира мог быть коллапс сосудов.'
                            }
                        ]
                    },
                    {
                        'node_key': 'med_actions',
                        'title': 'Реанимационные действия и встреча скорой',
                        'character_name': 'Врач из числа пассажиров',
                        'character_role': 'Кардиолог',
                        'character_mood': 'calm',
                        'dialogue_text': '«Я врач-кардиолог. Вы отлично сработали с дефибриллятором и кислородной маской. Состояние стабилизировано. Запросите реанимобиль к перрону!»',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': 'Жизнь человека спасена благодаря четким действиям по протоколу первой помощи ВСМ. Начальник поезда организовал встречу реанимационной бригады.',
                        'choices': []
                    },
                    {
                        'node_key': 'med_fatal_error',
                        'title': 'Трагическое нарушение инструкции',
                        'character_name': 'Следственные органы',
                        'character_role': 'Правоохранительные органы',
                        'character_mood': 'formal',
                        'dialogue_text': '«Проводник дал сильнодействующий препарат без назначения врача, что вызвало резкое падение артериального давления. Возбуждено расследование».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Проводникам ВСМ категорически запрещено выдавать любые лекарственные средства пассажирам.',
                        'choices': []
                    },
                    {
                        'node_key': 'med_timeout',
                        'title': 'Промедление в экстренной ситуации',
                        'character_name': 'Система безопасности',
                        'character_role': 'Бортовой комплекс',
                        'character_mood': 'critical',
                        'dialogue_text': '«Время на реакцию упущено. При остановке сердца каждая секунда промедления снижает шансы выживания на 10%».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Недопустимая задержка реанимационных мероприятий в скоростном поезде.',
                        'choices': []
                    }
                ]
            }
        ]

        # Добавляем остальные 15 сценариев из "Ситуации на борту.pdf" с тематическими изображениями
        remaining_scenarios = [
            ('Посадка без документа удостоверяющего личность', 'boarding-no-id', 'conflict', 'easy', 'Ситуации на борту (Кейс 2)', 'service_etiquette', 'sc_platform_boarding.jpg'),
            ('Опоздавший пассажир и блокировка дверей', 'late-passenger-doors', 'safety', 'easy', 'Ситуации на борту (Кейс 3)', 'safety_regulations', 'sc_platform_boarding.jpg'),
            ('Перевозка велосипеда в неразобранном виде', 'oversized-bicycle', 'safety', 'easy', 'Ситуации на борту (Кейс 5)', 'safety_regulations', 'sc_oversized_luggage.jpg'),
            ('Пассажир с признаками опьянения', 'intoxicated-passenger', 'conflict', 'medium', 'Ситуации на борту (Кейс 6)', 'conflict_resolution', 'sc_business_conflict.jpg'),
            ('Повышение класса обслуживания через ММТ', 'upgrade-service-class', 'vip_service', 'medium', 'Ситуации на борту (Кейс 7)', 'service_etiquette', 'vsm_classes_overview.jpg'),
            ('Отсутствие блюда из меню вагона-бистро', 'menu-item-unavailable', 'service', 'easy', 'Ситуации на борту (Кейс 8)', 'service_etiquette', 'sc_bistro_bar.jpg'),
            ('Курение электронной сигареты и тревога СПАС-ВО', 'smoke-detector-alarm', 'safety', 'medium', 'Ситуации на борту (Кейс 20)', 'safety_regulations', 'sc_smoke_alarm.jpg'),
            ('Бесхозный предмет под пассажирским креслом', 'unattended-baggage', 'anti_terror', 'hard', 'Ситуации на борту (Кейс 41)', 'safety_regulations', 'sc_unattended_bag.jpg'),
            ('Потерявшийся ребенок в скоростном экспрессе', 'lost-child-car', 'service', 'easy', 'Ситуации на борту (Кейс 30)', 'service_etiquette', 'sc_child_care.jpg'),
            ('Конфликт из-за шума и детского плача в Бизнес-классе', 'business-class-child-crying', 'conflict', 'medium', 'Ситуации на борту (Кейс 10, 37)', 'conflict_resolution', 'vsm_cabin_passengers.jpg'),
            ('Острая аллергическая реакция на животное соседа', 'severe-pet-allergy', 'medical', 'medium', 'Ситуации на борту (Кейс 11)', 'emergency_medical', 'sc_pet_carrier.jpg'),
            ('Громкий разговор по телефону в тихой зоне', 'loud-phone-speaker', 'conflict', 'easy', 'Ситуации на борту (Кейс 12, 22)', 'service_etiquette', 'vsm_cabin_passengers.jpg'),
            ('Забытые вещи на платформе отправления', 'forgotten-luggage-platform', 'service', 'easy', 'Ситуации на борту (Кейс 40)', 'service_etiquette', 'sc_platform_boarding.jpg'),
            ('Запрос постороннего лица передать посылку', 'request-deliver-parcel', 'anti_terror', 'medium', 'Ситуации на борту (Кейс 39)', 'safety_regulations', 'vsm_train_exterior.jpg'),
            ('Отказ вакуумной туалетной системы ЭЧТК FRAM3', 'vacuum-toilet-clogged', 'tech_failure', 'medium', 'Ситуации на борту (Кейс 42)', 'vsm_tech_protocols', 'sc_vacuum_toilet.jpg'),
        ]

        for idx, (title, slug, cat, diff, ref, comp_code, bg_image) in enumerate(remaining_scenarios, start=6):
            scenarios_data.append({
                'title': title,
                'slug': slug,
                'category': cat,
                'difficulty': diff,
                'train_speed': 360 if diff != 'hard' else 400,
                'train_number': '№ 712 «Белый кречет»',
                'location_name': 'Магистраль ВСМ-1, Москва — Санкт-Петербург',
                'car_info': 'Вагон скоростного электропоезда ВСМ',
                'description': f'Ситуационный кейс поездной бригады: {title}.',
                'briefing': f'Отработайте алгоритм действий проводника согласно официальному регламенту ({ref}).',
                'regulation_reference': f'СТО ВСМ 03.011–2026; {ref}',
                'background_image': bg_image,
                'base_xp': 240,
                'time_limit_default': 25,
                'order': idx,
                'nodes': [
                    {
                        'node_key': 'start',
                        'title': title,
                        'character_name': 'Пассажир поезда',
                        'character_role': 'Пассажир',
                        'character_mood': 'irritated',
                        'dialogue_text': f'Возникла нештатная ситуация: {title}. Пассажиры обращаются к проводнику с требованием решения проблемы.',
                        'narrative_context': 'Скоростной электропоезд в пути следования со скоростью 360-400 км/ч.',
                        'time_limit_seconds': 25,
                        'choices': [
                            {
                                'text': 'Применить 4-шаговую ролевую модель ВСМ: признать ситуацию, озвучить правило стандарта, предложить законное решение и заверить в заботе.',
                                'hint': 'Официальная формула коммуникации поездного персонала скоростных линий.',
                                'next_key': 'standard_success',
                                'loyalty': 20,
                                'safety': 15,
                                'comp': comp_code,
                                'comp_pts': 20,
                                'feedback': 'Точное следование стандарту сервиса и безопасности.'
                            },
                            {
                                'text': 'Игнорировать обращение или пойти на поводу у незаконных требований во вред безопасности.',
                                'hint': 'Нарушение регламента скоростного движения.',
                                'next_key': 'standard_fail',
                                'loyalty': -20,
                                'safety': -25,
                                'comp': comp_code,
                                'comp_pts': -15,
                                'feedback': 'Грубое отступление от правил.'
                            }
                        ]
                    },
                    {
                        'node_key': 'standard_success',
                        'title': 'Ситуация успешно урегулирована',
                        'character_name': 'Благодарный пассажир',
                        'character_role': 'Пассажир',
                        'character_mood': 'calm',
                        'dialogue_text': '«Спасибо за компетентность и внимательное отношение! Приятно иметь дело с профессионалами высокой квалификации».',
                        'is_terminal': True,
                        'is_success': True,
                        'resolution_report': f'Проводник безукоризненно выполнил требования регламента {ref}. Баланс лояльности и безопасности сохранен.',
                        'choices': []
                    },
                    {
                        'node_key': 'standard_fail',
                        'title': 'Сбой регламента',
                        'character_name': 'Начальник поезда',
                        'character_role': 'ЛНП',
                        'character_mood': 'formal',
                        'dialogue_text': '«В действиях проводника зафиксировано нарушение сервисного регламента и стандартов скоростных линий. Оформлен разбор смены».',
                        'is_terminal': True,
                        'is_success': False,
                        'resolution_report': 'Действия не соответствовали правилам безопасности и клиентоориентированности ВСМ.',
                        'choices': []
                    }
                ]
            })

        # Запись всех сценариев и узлов
        created_count = 0
        for sc_data in scenarios_data:
            nodes_data = sc_data.pop('nodes')
            scenario_obj, _ = Scenario.objects.update_or_create(
                slug=sc_data['slug'],
                defaults=sc_data
            )
            created_count += 1

            for n_data in nodes_data:
                choices_data = n_data.pop('choices')
                node_obj, _ = ScenarioNode.objects.update_or_create(
                    scenario=scenario_obj,
                    node_key=n_data['node_key'],
                    defaults=n_data
                )

                for idx, c_data in enumerate(choices_data):
                    comp_obj = competency_map.get(c_data.get('comp'), competency_map['service_etiquette'])
                    ScenarioChoice.objects.update_or_create(
                        node=node_obj,
                        order=idx,
                        defaults={
                            'choice_text': c_data['text'],
                            'tactical_hint': c_data.get('hint', ''),
                            'next_node_key': c_data['next_key'],
                            'loyalty_impact': c_data.get('loyalty', 0),
                            'safety_impact': c_data.get('safety', 0),
                            'service_impact': c_data.get('service', 0),
                            'stress_impact': c_data.get('stress', 5),
                            'competency': comp_obj,
                            'competency_points': c_data.get('comp_pts', 10),
                            'feedback_toast': c_data.get('feedback', ''),
                            'audio_cue': 'success' if c_data.get('loyalty', 0) > 0 else 'warning'
                        }
                    )

        self.stdout.write(self.style.SUCCESS(f"Успешно создано/обновлено {created_count} официальных сценариев ВСМ!"))
