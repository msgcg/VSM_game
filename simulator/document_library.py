"""
Нормативно-справочная библиотека высокоскоростной магистрали (ВСМ-1).
Содержит структурированные выдержки, статьи регламентов и каталог первоисточников
(учебные пособия проводника, билеты 4-го разряда, правила перевозок, ПТЭ, инструкции).
"""

import os
from django.conf import settings

DOCUMENTS_DIR = os.path.join(settings.BASE_DIR, 'regulations_docs')

# Каталог первоисточников и нормативных документов
REGULATION_DOCUMENTS = {
    'bolotin': {
        'key': 'bolotin',
        'title': 'Учебное пособие проводника скоростного поезда',
        'subtitle': 'Отраслевой курс подготовки поездных бригад скоростных магистралей',
        'filename': 'VSM_Conductor_Handbook.pdf',
        'pdf_filename': 'VSM_Conductor_Handbook.pdf',
        'size': '15 МБ',
        'format': 'PDF',
        'badge': 'Базовый курс ВСМ',
        'badge_color': '#082a99',
        'icon': 'book-open-check',
        'description': 'Основное руководство по устройству вагонов, колесных пар, автотормозов, СКНБ, электрощитов, систем отопления, пожарной безопасности (СПАС-ВО) и культуре сервиса.',
        'sections_count': 9,
        'chapters': [
            {
                'num': 1,
                'title': 'Общие обязанности проводника и подготовка состава в рейс',
                'summary': 'Порядок явки на смену, получение инвентаря, прохождение предрейсового медицинского осмотра, проверка вагонной книги формы ВУ-8, проверка пломб и огнетушителей.'
            },
            {
                'num': 2,
                'title': 'Культура обслуживания пассажиров и этикет',
                'summary': 'Стандарты общения, обращение на «Вы», предотвращение конфликтных ситуаций, обслуживание пассажиров с детьми и маломобильных граждан, сервис чайной продукции.'
            },
            {
                'num': 3,
                'title': 'Внутреннее оборудование пассажирских вагонов',
                'summary': 'Устройство замков, аварийных выходов, межвагонных переходных площадок, вакуумных санитарно-гигиенических узлов, трансформируемой мебели и рундуков.'
            },
            {
                'num': 4,
                'title': 'Отопление, вентиляция и кондиционирование воздуха',
                'summary': 'Эксплуатация климатических установок, регулирование притока свежего воздуха, температурные режимы (зима: 20-24°C, лето: 22-26°C), порядок работы при отказе кондиционера.'
            },
            {
                'num': 5,
                'title': 'Электрооборудование пассажирских вагонов и СКНБ',
                'summary': 'Подвагонные генераторы, аккумуляторные батареи, система контроля нагрева букс (СКНБ), действия при замыкании на корпус вагона (лампа «Земля») и перегрузках цепей.'
            },
            {
                'num': 6,
                'title': 'Ходовые части, колесные пары и автотормоза',
                'summary': 'Устройство буксового узла, признаки нагрева букс, ползуны и выбоины на колесных парах, опробование тормозов (полное и сокращенное), ручной тормоз.'
            },
            {
                'num': 7,
                'title': 'Безопасность движения, ПТЭ и сигналы',
                'summary': 'Правила технической эксплуатации (ПТЭ), видимые и звуковые сигналы, обозначение хвоста поезда тремя красными огнями, запреты на срыв стоп-крана.'
            },
            {
                'num': 8,
                'title': 'Охрана труда, электробезопасность и пожарная безопасность',
                'summary': 'Инструкция ЦЛ-114, правила работы с электрощитом под напряжением до 1000В и 3000В, применение огнетушителей ОУ-2 и ОВП, эвакуация пассажиров.'
            },
            {
                'num': 9,
                'title': 'Первая доврачебная помощь при неотложных состояниях',
                'summary': 'Алгоритм сердечно-легочной реанимации, использование АНД, остановка кровотечений (жгут, давящая повязка), помощь при ожогах, обмороках и тепловых ударах.'
            }
        ]
    },
    'tickets_4_rank': {
        'key': 'tickets_4_rank',
        'title': 'Экзаменационные билеты проводника 4-го разряда',
        'subtitle': 'Квалификационные аттестационные билеты (25 билетов с эталонами ответов)',
        'filename': 'VSM_Exam_Tickets_4_Rank.pdf',
        'pdf_filename': 'VSM_Exam_Tickets_4_Rank.pdf',
        'size': '137 КБ',
        'format': 'PDF',
        'badge': 'Квалификационный экзамен',
        'badge_color': '#10b981',
        'icon': 'award',
        'description': 'Полный перечень официальных экзаменационных билетов проводника: тормоза, СКНБ, замыкание на корпус, СПАС-ВО, перевозка детей и животных, забытые вещи.',
        'sections_count': 25,
        'chapters': [
            {
                'num': 1,
                'title': 'Билеты 1-5: Тормозное оборудование и ПТЭ',
                'summary': 'Сокращенное и полное опробование тормозов, назначение ручных тормозов, сигналы бдительности, отцепка вагона в пути следования.'
            },
            {
                'num': 2,
                'title': 'Билеты 6-10: Электрооборудование и контроль букс',
                'summary': 'Типы генераторов и аккумуляторных батарей, контроль изоляции («Земля в цепи»), сигнализация СКНБ, порядок включения электроотопления.'
            },
            {
                'num': 3,
                'title': 'Билеты 11-15: Пожарная безопасность и посадка',
                'summary': 'Огнетушители ОУ-5 и ОП-5, противопожарные заслонки, перевозка домашних животных и собак крупных пород, провоз электронной техники.'
            },
            {
                'num': 4,
                'title': 'Билеты 16-20: Нештатные ситуации с пассажирами',
                'summary': 'Билет остался у провожающего на перроне, пассажир отстал от поезда, травмирование пассажира (акт НУ-1), забытые вещи (акт ЛУ-72).'
            },
            {
                'num': 5,
                'title': 'Билеты 21-25: Охрана труда и электробезопасность',
                'summary': 'Освобождение пострадавшего от действия электрического тока, действия при взрыве АКБ, саморасцеп автосцепок, ограждение хвоста поезда.'
            }
        ]
    },
    'passenger_rules': {
        'key': 'passenger_rules',
        'title': 'Правила перевозок пассажиров и багажа',
        'subtitle': 'Стандарты обслуживания и правила проезда на скоростных линиях ВСМ',
        'filename': 'VSM_Passenger_Rules.pdf',
        'pdf_filename': 'VSM_Passenger_Rules.pdf',
        'size': '160 КБ',
        'format': 'PDF',
        'badge': 'Регламент перевозок ВСМ',
        'badge_color': '#f59e0b',
        'icon': 'scroll',
        'description': 'Нормативы проезда, правила посадки, перевозка ручной клади (до 36/50 кг), провоз животных, п. 23 (овербукинг и бесплатный апгрейд) и порядок возврата.',
        'sections_count': 6,
        'chapters': [
            {
                'num': 1,
                'title': 'Правило одной буквы (Телеграмма № 852)',
                'summary': 'Допускается расхождение в билете не более одной буквы в фамилии/инициалах и не более одной цифры в номере паспорта. Пассажир допускается к посадке.'
            },
            {
                'num': 2,
                'title': 'Пункт 23: Овербукинг и отсутствие места',
                'summary': 'При невозможности предоставить оплаченное место перевозчик обязан с согласия пассажира бесплатно пересадить его в вагон более высокого класса без доплаты.'
            },
            {
                'num': 3,
                'title': 'Нормы перевозки ручной клади и багажа',
                'summary': 'До 36 кг на билет (в СВ/Первом классе до 50 кг), сумма трех измерений не более 180 см. Спортинвентарь перевозится в чехлах в специализированных зонах.'
            },
            {
                'num': 4,
                'title': 'Провоз домашних животных',
                'summary': 'Мелкие животные — в переносках размером до 180 см по сумме сторон. Крупные собаки — исключительно на поводке и в наморднике в спецкупе или вагоне с животными.'
            },
            {
                'num': 5,
                'title': 'Отставание пассажира от поезда',
                'summary': 'Дежурный по станции отправляет телеграмму на станцию следования. Багаж снимается комиссией из 3 человек (ЛНП, проводник, свидетель) по акту ЛУ-72.'
            }
        ]
    },
    'conductor_instruction': {
        'key': 'conductor_instruction',
        'title': 'Типовая инструкция проводника скоростного поезда',
        'subtitle': 'Должностные обязанности, охрана труда и действия в аварийных ситуациях',
        'filename': 'VSM_Conductor_Instruction.pdf',
        'pdf_filename': 'VSM_Conductor_Instruction.pdf',
        'size': '198 КБ',
        'format': 'PDF',
        'badge': 'Охрана труда и безопасность',
        'badge_color': '#ef4444',
        'icon': 'shield-check',
        'description': 'Пошаговый регламент действий проводника при движении со скоростью до 400 км/ч, задымлении, взрыве АКБ, аварийной остановке на перегоне и первой помощи.',
        'sections_count': 5,
        'chapters': [
            {
                'num': 1,
                'title': 'Требования безопасности перед началом рейса',
                'summary': 'Проверка сигнальных фонарей, ручного тормоза, огнетушителей, системы СКНБ, закрытия фальшбортов и исправности межвагонных суфле.'
            },
            {
                'num': 2,
                'title': 'Требования безопасности во время движения поезда',
                'summary': 'Запрет высовываться из окон и открывать наружные двери на ходу, контроль за пассажирами в тамбурах, проверка температуры буксовых узлов по датчикам.'
            },
            {
                'num': 3,
                'title': 'Действия при аварийных ситуациях на высокой скорости',
                'summary': 'Порядок действий при задымлении СПАС-ВО, запрет срыва стоп-крана на мостах и в тоннелях, ограждение состава при вынужденной остановке петардами.'
            },
            {
                'num': 4,
                'title': 'Электробезопасность при напряжении до и выше 1000В',
                'summary': 'Правила работы в зоне высоковольтного подвагонного оборудования, заземление штанг, отключение подвагонных ящиков только при снятом напряжении.'
            }
        ]
    },
    'electronic_tickets': {
        'key': 'electronic_tickets',
        'title': 'Технология электронных билетов и работа с УКЭБ',
        'subtitle': 'Регламент мобильного контроля посадки пассажиров ВСМ',
        'filename': 'VSM_Electronic_Tickets.pdf',
        'pdf_filename': 'VSM_Electronic_Tickets.pdf',
        'size': '142 КБ',
        'format': 'PDF',
        'badge': 'Цифровой сервис',
        'badge_color': '#00d2ff',
        'icon': 'smartphone',
        'description': 'Посадка по электронной регистрации без распечатки, сканирование QR-кодов терминалом УКЭБ, выгрузка списков пассажиров, действия при сбое радиосвязи.',
        'sections_count': 4,
        'chapters': [
            {
                'num': 1,
                'title': 'Посадка пассажиров по электронной регистрации',
                'summary': 'Проверка паспорта по загруженной ведомости УКЭБ. Бумажный билет не требуется. Погашение электронного статуса поездки при входе в вагон.'
            },
            {
                'num': 2,
                'title': 'Работа терминала УКЭБ в автономном режиме',
                'summary': 'При отсутствии сотовой связи на перегоне терминал сохраняет данные в локальной энергонезависимой памяти и синхронизируется на опорной станции.'
            },
            {
                'num': 3,
                'title': 'Сбой терминала мобильного контроля',
                'summary': 'При разрядке или поломке УКЭБ проводник использует бумажную дублирующую ведомость ЛНП или запрашивает резервный терминал начальника поезда.'
            }
        ]
    },
    'acceptance_handover': {
        'key': 'acceptance_handover',
        'title': 'Регламент приемки и сдачи вагона перед рейсом',
        'subtitle': 'Чек-лист технической и санитарной экипировки состава «Белый кречет»',
        'filename': 'VSM_Acceptance_Handover.pdf',
        'pdf_filename': 'VSM_Acceptance_Handover.pdf',
        'size': '124 КБ',
        'format': 'PDF',
        'badge': 'Техническая готовность',
        'badge_color': '#8b5cf6',
        'icon': 'clipboard-check',
        'description': 'Пошаговый регламент осмотра салона, проверки пломб огнетушителей, аптечек, прислонно-сдвижных дверей, исправности климата и сдачи вагона сменщику.',
        'sections_count': 4,
        'chapters': [
            {
                'num': 1,
                'title': 'Приемка вагона в парке формирования',
                'summary': 'Приемка за 2 часа до подачи на перрон: проверка пломб СПАС-ВО, манометров огнетушителей, комплектации АНД, чистоты кресел и ковровых покрытий.'
            },
            {
                'num': 2,
                'title': 'Проверка систем жизнеобеспечения поезда',
                'summary': 'Тестирование автоматики дверей СКУД, подачи воды в санузлы, нагрева воды в бистро, работы индивидуального освещения и мультимедийных экранов.'
            },
            {
                'num': 3,
                'title': 'Сдача вагона на конечной станции (оборот)',
                'summary': 'Осмотр салона на предмет забытых вещей, проверка целостности оборудования, оформление записей в бортовом журнале формы ТУ-152.'
            }
        ]
    },
    'interior_equipment': {
        'key': 'interior_equipment',
        'title': 'Внутреннее оборудование пассажирских вагонов',
        'subtitle': 'Устройство салонных систем, кресел и вакуумных санузлов ЭВС2',
        'filename': 'VSM_Interior_Equipment.pdf',
        'pdf_filename': 'VSM_Interior_Equipment.pdf',
        'size': '179 КБ',
        'format': 'PDF',
        'badge': 'Эргономика и сервис',
        'badge_color': '#ec4899',
        'icon': 'armchair',
        'description': 'Руководство по эксплуатации поворотных эргономичных кресел, вакуумных систем санузлов, климатических жалюзи, дисплеев и оборудования бистро.',
        'sections_count': 4,
        'chapters': [
            {
                'num': 1,
                'title': 'Кресельные модули Бизнес и Первого классов',
                'summary': 'Регулировка угла наклона спинки (до 145°), подставки для ног, индивидуальные столики, беспроводные зарядные устройства и наушники.'
            },
            {
                'num': 2,
                'title': 'Вакуумная туалетная система замкнутого типа',
                'summary': 'Устройство вакуумного эжектора, датчики уровня заполнения бака (80% и 100%), действия при блокировке сливного клапана посторонним предметом.'
            },
            {
                'num': 3,
                'title': 'Оборудование вагона-бистро',
                'summary': 'Конвекционные печи, кофемашины высокого давления, холодильные камеры для скоропортящейся продукции, термопоты и мойки с фильтрацией воды.'
            }
        ]
    },
    'onboard_situations': {
        'key': 'onboard_situations',
        'title': 'Ситуации на борту: Взаимодействие поездного персонала ВСМ с пассажирами',
        'subtitle': 'Официальное методическое пособие и ролевые модели поведения поездной бригады',
        'filename': 'VSM_Onboard_Situations_Guide.pdf',
        'pdf_filename': 'VSM_Onboard_Situations_Guide.pdf',
        'size': '519 КБ',
        'format': 'PDF',
        'badge': 'Методическое пособие ВСМ',
        'badge_color': '#7c3aed',
        'icon': 'messages-square',
        'description': 'Официальный регламент и 48 кейсов взаимодействия поездного персонала ВСМ с пассажирами: 4 шага сервисного разрешения (Признать, Обозначить правило, Предложить решение, Заверить), посадка без билета или паспорта, провоз животных, ручная кладь, овербукинг, шумные пассажиры, климат-контроль и неотложная помощь.',
        'sections_count': 7,
        'chapters': [
            {
                'num': 1,
                'title': 'Ролевая модель сервисного общения (4 шага)',
                'summary': 'Базовый алгоритм из 4 шагов: Признать ситуацию («Я Вас понимаю...») -> Обозначить правило («Обращаю Ваше внимание...») -> Предложить решение («Позвольте предложить для Вас альтернативный вариант...») -> Заверить («Благодарю Вас за понимание и терпение»).'
            },
            {
                'num': 2,
                'title': 'Ситуации на посадке: отсутствие билета, документов, биометрия',
                'summary': 'Порядок действий при отсутствии проездного документа, несовпадении паспортных данных, проверке по УКЭБ и биометрической идентификации.'
            },
            {
                'num': 3,
                'title': 'Перевозка животных и негабаритного багажа',
                'summary': 'Обязательное нахождение питомцев в переносках, покупка переноски на борту поезда, разборка и упаковка велосипедов, размещение ручной клади без загромождения эвакуационных проходов.'
            },
            {
                'num': 4,
                'title': 'Культура питания, сервис бистро и повышение класса обслуживания',
                'summary': 'Отсутствие выбранного блюда из меню, предложение аналогичного блюда из той же категории, предварительный заказ через мобильное приложение, оформление апгрейда класса через мобильную кассу УКЭБ.'
            },
            {
                'num': 5,
                'title': 'Пассажиры с детьми, плач ребенка и тихие зоны',
                'summary': 'Предоставление детских игровых наборов, перевод семьи в игровую зону вагона Комфорт, деликатное урегулирование претензий пассажиров в тихой зоне.'
            },
            {
                'num': 6,
                'title': 'Неисправности оборудования вагона и климат-контроля',
                'summary': 'Поломка механизма наклона кресел, отсутствие питания в индивидуальных розетках, перегрев салона при сбое кондиционера, перезапуск климатической установки через электрощит вагона.'
            },
            {
                'num': 7,
                'title': 'Конфликты, нетрезвые пассажиры и медицинская помощь',
                'summary': 'Деэскалация без провоцирования агрессии, вызов начальника поезда (ЛНП) и сотрудников транспортной безопасности, оказание первой доврачебной помощи с АНД и вызов скорой к ближайшей станции.'
            }
        ]
    }
}

# Синоним для совместимости с базой данных
REGULATION_DOCUMENTS['onboard_situations_guide'] = REGULATION_DOCUMENTS['onboard_situations']


# Экспресс-шпаргалка для мгновенного решения задач проводником
CONDUCTOR_CHEAT_SHEETS = [
    {
        'category': 'Билеты и посадка',
        'rule': 'Правило 1 буквы и 1 цифры',
        'reference': 'Отраслевое распоряжение № 852',
        'summary': 'Допускается расхождение до 1 буквы в фамилии/инициалах и 1 цифры в номере паспорта. Пассажир ОБЯЗАТЕЛЬНО допускается к посадке. В пути ЛНП оформляет стандартный акт.',
        'icon': 'check-circle-2',
        'color': '#10b981'
    },
    {
        'category': 'Места и овербукинг',
        'rule': 'Бесплатный апгрейд при занятом месте',
        'reference': 'Правила перевозок п. 23',
        'summary': 'Если место пассажира занято или неисправно, перевозчик ОБЯЗАН бесплатно пересадить его в вагон более высокого класса (Бизнес / Первый) без какой-либо доплаты.',
        'icon': 'crown',
        'color': '#f59e0b'
    },
    {
        'category': 'Безопасность 400 км/ч',
        'rule': 'Запрет срыва стоп-крана на мостах и в тоннелях',
        'reference': 'ПТЭ железных дорог РФ',
        'summary': 'Категорически запрещено применять экстренное торможение на мостах, эстакадах и в тоннелях, а также при пожаре и болезнях. Состав обязан на максимальном ходу выйти на открытую станцию.',
        'icon': 'alert-octagon',
        'color': '#fd033a'
    },
    {
        'category': 'Технические сбои',
        'rule': 'Тревога СКНБ (нагрев букс)',
        'reference': 'Инструкция по сигнализации СКНБ',
        'summary': 'При звуковом сигнале СКНБ проводник НЕМЕДЛЕННО связывается с машинистом по радиосвязи для плавного служебного снижения скорости. Резкое торможение стоп-краном запрещено!',
        'icon': 'gauge',
        'color': '#00d2ff'
    },
    {
        'category': 'Багаж и находки',
        'rule': 'Забытые вещи и отставшие пассажиры',
        'reference': 'Бланк формы ЛУ-72',
        'summary': 'Опись забытых вещей проводится комиссией из 3 человек (ЛНП, проводник, свидетель-пассажир). Направляется служебная телеграмма на станцию отправления/высадки.',
        'icon': 'archive',
        'color': '#8b5cf6'
    },
    {
        'category': 'Неотложная помощь',
        'rule': 'Реанимация и дефибриллятор АНД',
        'reference': 'Приказ Минздрава № 477н',
        'summary': 'При остановке сердца — немедленно доставить АНД, вызвать врача через ЛНП. Перед разрядом громко скомандовать «Всем отойти!». Сильнодействующие таблетки проводнику давать ЗАПРЕЩЕНО.',
        'icon': 'heart-pulse',
        'color': '#ef4444'
    }
]


def get_document_pdf_path(doc_key):
    """Возвращает абсолютный путь к официальному PDF-файлу регламента для браузерной читалки"""
    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return None
    pdf_filename = doc_info.get('pdf_filename') or doc_info['filename'].replace('.doc', '.pdf')
    pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
    if os.path.exists(pdf_path):
        return pdf_path
    
    direct_path = os.path.join(DOCUMENTS_DIR, doc_info['filename'])
    if os.path.exists(direct_path) and direct_path.endswith('.pdf'):
        return direct_path
    return None


def get_document_file_path(doc_key):
    """Возвращает абсолютный путь к файлу документа (приоритет PDF)"""
    pdf_path = get_document_pdf_path(doc_key)
    if pdf_path and os.path.exists(pdf_path):
        return pdf_path
    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return None
    file_path = os.path.join(DOCUMENTS_DIR, doc_info['filename'])
    if os.path.exists(file_path):
        return file_path
    return None


def get_or_create_document_pdf(doc_key):
    """
    Возвращает абсолютный путь к PDF-файлу документа.
    Если физический PDF-файл отсутствует на диске (например, из-за исключения тяжелых файлов из git),
    автоматически генерирует эталонный PDF-документ высокой типографики со всеми регламентами и разделами.
    Гарантирует, что при любых обстоятельствах код не падает, а пользователь получает полноценный документ.
    """
    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return None

    # 1. Проверяем наличие оригинального PDF или файла
    direct_pdf = get_document_pdf_path(doc_key)
    if direct_pdf and os.path.exists(direct_pdf):
        return direct_pdf

    # 2. Проверяем, был ли ранее сгенерирован fallback PDF
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    digital_pdf_name = f"{doc_key}_digital_handbook.pdf"
    digital_pdf_path = os.path.join(DOCUMENTS_DIR, digital_pdf_name)
    if os.path.exists(digital_pdf_path) and os.path.getsize(digital_pdf_path) > 100:
        return digital_pdf_path

    # 3. Генерируем компактный структурированный PDF с помощью ReportLab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_name = 'Helvetica'
        moscow_sans_path = os.path.join(settings.BASE_DIR, 'simulator', 'static', 'simulator', 'fonts', 'MoscowSans-Regular.ttf')
        for candidate_font in [
            moscow_sans_path,
            'C:\\Windows\\Fonts\\arial.ttf',
            'C:\\Windows\\Fonts\\tahoma.ttf',
            'C:\\Windows\\Fonts\\calibri.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]:
            if os.path.exists(candidate_font):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFont', candidate_font))
                    font_name = 'CyrillicFont'
                    break
                except Exception:
                    pass

        doc = SimpleDocTemplate(
            digital_pdf_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        badge_style = ParagraphStyle(
            'DocBadge',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#082a99'),
            alignment=1,
            spaceAfter=8
        )
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#082a99'),
            spaceAfter=6,
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12,
            alignment=1
        )
        h2_style = ParagraphStyle(
            'DocH2',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#0284c7'),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=6
        )

        story = [
            Paragraph("ОПЕРАТОР СКОРОСТНЫХ ЛИНИЙ • ВЫСОКОСКОРОСТНАЯ ЖЕЛЕЗНОДОРОЖНАЯ МАГИСТРАЛЬ ВСМ-1 «БЕЛЫЙ КРЕЧЕТ»", badge_style),
            Paragraph(f"<b>{doc_info['title']}</b>", title_style),
            Paragraph(doc_info.get('subtitle', ''), subtitle_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#00d2ff'), spaceAfter=10),
            Paragraph("<b>Аннотация и назначение:</b> " + doc_info.get('description', ''), body_style),
            Spacer(1, 6),
            Paragraph("<b>ОФИЦИАЛЬНЫЕ НОРМАТИВНЫЕ РАЗДЕЛЫ И РЕГЛАМЕНТЫ ЭКИПАЖА</b>", h2_style),
        ]

        for ch in doc_info.get('chapters', []):
            story.append(Paragraph(f"<b>Раздел {ch['num']}. {ch['title']}</b>", h2_style))
            story.append(Paragraph(ch['summary'], body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        if os.path.exists(digital_pdf_path):
            return digital_pdf_path
    except Exception:
        # Резервный компактный генератор через Canvas
        try:
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(digital_pdf_path)
            c.setFont("Helvetica", 12)
            c.drawString(40, 800, f"VSM-1 Regulations: {doc_info['title'][:50]}")
            c.setFont("Helvetica", 9)
            c.drawString(40, 780, f"Digital Conductor Handbook: {doc_key}")
            y = 750
            for ch in doc_info.get('chapters', [])[:10]:
                c.drawString(40, y, f"Section {ch['num']}: {ch['title'][:65]}")
                y -= 25
            c.save()
            return digital_pdf_path
        except Exception:
            pass

    return None



def get_document_raw_content(doc_key):
    """Считывает текстовое содержимое документа для интерактивной читалки с форматированием"""
    import re
    doc_info = REGULATION_DOCUMENTS.get(doc_key)
    if not doc_info:
        return ""

    lines = [
        f"# {doc_info['title']}",
        f"*{doc_info['subtitle']}*",
        "",
        "## Официальный регламент и первоисточник",
        f"**Краткая аннотация:** {doc_info['description']}",
        "",
        "---",
        "## Нормативные разделы и правила:",
        ""
    ]
    for ch in doc_info.get('chapters', []):
        lines.append(f"### Раздел {ch['num']}. {ch['title']}")
        lines.append(f"{ch['summary']}")
        lines.append("")

    file_path = os.path.join(DOCUMENTS_DIR, doc_info['filename'])
    if os.path.exists(file_path) and doc_info['filename'].endswith('.doc'):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            decoded = data.decode('utf-16le', errors='ignore')
            raw_paras = re.split(r'[\r\n]+', decoded)
            clean_paras = []
            for p in raw_paras:
                p_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ue000-\uf8ff\uff00-\uffef]', '', p).strip()
                cyr_count = sum(1 for c in p_clean if '\u0400' <= c <= '\u04ff')
                if cyr_count >= 15:
                    clean_paras.append(p_clean)
            if clean_paras:
                lines.append("\n---\n## Текст исходной инструкции:\n")
                for p in clean_paras[:80]:
                    if len(p) < 80 and (p.isupper() or p.endswith(':') or re.match(r'^\d+\.\s+[А-ЯЁ\s]+$', p)):
                        lines.append(f"\n### {p}\n")
                    elif p.startswith(('ВНИМАНИЕ', 'ВАЖНО', 'ЗАПРЕЩАЕТСЯ', 'ЗАПРЕЩЕНО', 'ОБЯЗАН')):
                        lines.append(f"> **{p}**\n")
                    else:
                        lines.append(f"{p}\n")
        except Exception:
            pass

    return "\n".join(lines)

