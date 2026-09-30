import os
import re
import json
import time
import uuid
import hashlib
import asyncio
import urllib3
import requests
import edge_tts
from pathlib import Path
from django.conf import settings
from django.utils import timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SberAIService:
    """
    Единый сервис интеграции с искусственным интеллектом:
    1. Диалоговая языковая модель — генеративный интерактивный ИИ-диалог, физика поезда и судейство регламентов ВСМ
    2. Бортовой STT Vulkan — аппаратное распознавание речи проводника с GPU-ускорением
    3. Multi-voice Neural TTS — потоковый синтез голосов пассажиров и поездной бригады без кэширования на диск
    4. Корпоративный ID OAuth 2.0 — единый вход сотрудников и проводников
    """

    _gigachat_token = None
    _gigachat_expires_at = 0

    _salutespeech_token = None
    _salutespeech_expires_at = 0

    @classmethod
    def get_gigachat_token(cls, conductor=None) -> str:
        """
        Получает токен доступа к API диалоговой модели.
        ПРАВИЛО БЕЗОПАСНОСТИ И АВТОНОМИИ:
        Каждый проводник обязан иметь свой собственный авторизационный ключ.
        Глобальный системный ключ НЕ используется для игровых сессий проводников.
        """
        current_time = int(time.time() * 1000)

        # 1. Если передан проводник — строго требуем и используем его личный ключ
        if conductor:
            # Если уже сохранен рабочий access token и он не истек
            if getattr(conductor, 'sber_access_token', None) and len(conductor.sber_access_token) > 20:
                return conductor.sber_access_token

            # Личный авторизационный ключ проводника
            auth_key = getattr(conductor, 'sber_auth_key', '').strip()
            if not auth_key:
                raise ValueError(
                    "У проводника не настроен личный авторизационный ключ платформы ИИ. "
                    "Перейдите в профиль проводника (или раздел настроек) и сохраните ваш личный ключ (Base64), "
                    "полученный в личном кабинете разработчика."
                )

            scope = getattr(conductor, 'sber_scope', 'GIGACHAT_API_PERS') or 'GIGACHAT_API_PERS'
            oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            headers = {
                "Authorization": f"Basic {auth_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"scope": scope}
            try:
                resp = requests.post(oauth_url, headers=headers, data=data, verify=False, timeout=12)
                if resp.status_code == 200:
                    res_data = resp.json()
                    token = res_data.get("access_token")
                    if token:
                        conductor.sber_access_token = token
                        try:
                            conductor.save(update_fields=['sber_access_token'])
                        except Exception:
                            pass
                        return token
                err_body = resp.text[:200]
                raise ValueError(f"Шлюз OAuth отклонил авторизацию проводника (код {resp.status_code}): {err_body}")
            except requests.RequestException as exc:
                raise RuntimeError(f"Ошибка соединения со шлюзом OAuth при авторизации проводника: {exc}")

        # 2. Системный токен (только для фоновых CLI-скриптов и тестов без профиля проводника)
        if cls._gigachat_token and (cls._gigachat_expires_at - current_time > 60000):
            return cls._gigachat_token

        auth_key = getattr(settings, 'GIGACHAT_AUTH_KEY', '')
        scope = getattr(settings, 'GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')

        if not auth_key:
            raise ValueError(
                "Личный авторизационный ключ платформы ИИ не указан в профиле проводника. "
                "Укажите ваш ключ в настройках профиля проводника."
            )

        oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"scope": scope}

        try:
            resp = requests.post(oauth_url, headers=headers, data=data, verify=False, timeout=12)
            resp.raise_for_status()
            res_data = resp.json()
            cls._gigachat_token = res_data.get("access_token")
            cls._gigachat_expires_at = res_data.get("expires_at", current_time + 1800000)
            return cls._gigachat_token
        except Exception as exc:
            raise RuntimeError(f"Ошибка получения OAuth-токена диалоговой модели: {exc}")

    @classmethod
    def get_salutespeech_token(cls, conductor=None) -> str | None:
        """
        Получает токен доступа к API речевого комплекса (распознавание и синтез речи).
        Приоритет: личный ключ речевого комплекса проводника -> личный ключ доступа проводника -> системный ключ.
        """
        current_time = int(time.time() * 1000)

        # 1. Личный ключ проводника (специализированный SaluteSpeech или общий Sber)
        if conductor:
            auth_key = getattr(conductor, 'salutespeech_auth_key', '').strip() or getattr(conductor, 'sber_auth_key', '').strip()
            if auth_key:
                oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
                headers = {
                    "Authorization": f"Basic {auth_key}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                data = {"scope": "SALUTE_SPEECH_PERS"}
                try:
                    resp = requests.post(oauth_url, headers=headers, data=data, verify=False, timeout=10)
                    if resp.status_code == 200:
                        return resp.json().get("access_token")
                except Exception:
                    pass

        # 2. Системный кэшированный токен
        if cls._salutespeech_token and (cls._salutespeech_expires_at - current_time > 60000):
            return cls._salutespeech_token

        auth_key = getattr(settings, 'SALUTESPEECH_AUTH_KEY', '') or getattr(settings, 'GIGACHAT_AUTH_KEY', '')
        scope = getattr(settings, 'SALUTESPEECH_SCOPE', 'SALUTE_SPEECH_PERS')

        if not auth_key:
            return None

        oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"scope": scope}

        try:
            resp = requests.post(oauth_url, headers=headers, data=data, verify=False, timeout=10)
            if resp.status_code == 200:
                res_data = resp.json()
                cls._salutespeech_token = res_data.get("access_token")
                cls._salutespeech_expires_at = res_data.get("expires_at", current_time + 1800000)
                return cls._salutespeech_token
            return None
        except Exception:
            return None

    @classmethod
    def test_conductor_auth_key(cls, auth_key: str, scope: str = 'GIGACHAT_API_PERS') -> dict:
        """Проверяет валидность авторизационного ключа проводника через официальный OAuth шлюз ИИ"""
        if not auth_key or not auth_key.strip():
            return {"ok": False, "error": "Ключ авторизации не может быть пустым"}

        clean_key = auth_key.strip()
        oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {clean_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"scope": scope}

        try:
            resp = requests.post(oauth_url, headers=headers, data=data, verify=False, timeout=12)
            if resp.status_code == 200:
                res_data = resp.json()
                return {
                    "ok": True,
                    "access_token": res_data.get("access_token"),
                    "expires_at": res_data.get("expires_at"),
                    "scope": scope
                }
            err_text = resp.text
            if "scope from db not fully includes consumed scope" in err_text or '"code":7' in err_text:
                if scope == 'SALUTE_SPEECH_PERS':
                    err_msg = (
                        "Ключ авторизации верный, но в проекте не подключен речевой сервис. "
                        "Перейдите в кабинет разработчика, откройте проект и нажмите «+ Подключить сервис»."
                    )
                else:
                    err_msg = f"Проекту не хватает прав для scope {scope}. Проверьте подключенные сервисы в кабинете разработчика."
            else:
                err_msg = f"Шлюз OAuth отклонил запрос (код {resp.status_code}): {err_text[:200]}"
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": err_msg
            }
        except Exception as exc:
            return {"ok": False, "error": f"Ошибка сети при проверке ключа доступа: {exc}"}

    @classmethod
    def transcode_to_pcm(cls, audio_bytes: bytes) -> bytes | None:
        """
        Преобразует любые входные форматы аудиопотока браузера (webm, ogg, wav, mp3, opus)
        в строгий стандарт SaluteSpeech: 16kHz 1-channel s16le PCM в оперативной памяти через FFmpeg.
        """
        if not audio_bytes:
            return None
        try:
            import subprocess
            proc = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "pipe:1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            pcm_data, _ = proc.communicate(input=audio_bytes, timeout=12)
            if proc.returncode == 0 and pcm_data:
                return pcm_data
        except Exception as exc:
            print(f"[SberAIService] FFmpeg transcode warning: {exc}")
        return None

    @classmethod
    def recognize_speech(cls, audio_bytes: bytes, content_type: str = "audio/ogg;codecs=opus", conductor=None) -> dict:
        """
        Распознавание русской речи проводника:
        1. Высокоскоростной локальный Whisper с Vulkan-ускорением (universal GPU).
        2. Fallback в SaluteSpeech REST API при наличии токена.
        """
        if not audio_bytes:
            return {"ok": False, "error": "Аудиоданные не получены", "fallback_to_browser": True}

        # 1. Приоритет: локальный аппаратный Whisper Vulkan
        try:
            from .whisper_service import WhisperVulkanService
            if WhisperVulkanService.is_available():
                w_res = WhisperVulkanService.transcribe(audio_bytes, language="ru")
                if w_res.get("ok"):
                    return w_res
        except Exception as exc:
            print(f"[SberAIService] Whisper Vulkan warning: {exc}")

        # 2. Резервный шлюз SaluteSpeech REST API (если подключен персональный токен)
        token = cls.get_salutespeech_token(conductor=conductor)
        if token:
            pcm_data = cls.transcode_to_pcm(audio_bytes)
            send_data = pcm_data if pcm_data else audio_bytes
            c_type = "audio/x-pcm;bit=16;rate=16000" if pcm_data else content_type

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": c_type,
                "Accept": "application/json"
            }
            url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
            try:
                resp = requests.post(url, headers=headers, data=send_data, verify=False, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("result", [])
                    text = " ".join(results) if isinstance(results, list) else str(results)
                    if text.strip():
                        return {"ok": True, "text": text.strip(), "engine": "salutespeech"}
                    return {"ok": True, "text": "", "engine": "salutespeech", "message": "Речь не обнаружена"}
            except Exception:
                pass

        return {
            "ok": True,
            "text": "",
            "engine": "browser_fallback",
            "message": "Речь не обнаружена локальным движком. Воспользуйтесь вводом текста."
        }

    @classmethod
    def synthesize_speech(cls, text: str, voice: str = "Ost_24000", format_type: str = "mp3", conductor=None) -> tuple[bytes | None, str]:
        """
        Многоголосый потоковый синтез речи персонажей ВСМ (Microsoft Edge Neural TTS) БЕЗ кэширования на диск.
        Озвучивает живой диалог прямо в оперативной памяти с минимальной задержкой.
        Возвращает: (audio_bytes, content_type)
        """
        clean_text = cls.clean_text_for_tts(text)
        if not clean_text:
            return None, "audio/mpeg"

        # Определение многоголосого диктора по роли персонажа:
        # Роботизированный бортовой журнал: SvetlanaNeural (+18% rate, +30Hz pitch)
        # Кабина машиниста (рация): DmitryNeural (+10% rate, -20Hz pitch)
        # Женские образы: SvetlanaNeural
        # Мужские образы: DmitryNeural
        female_indicators = [
            "nat_24000", "may_24000", "pon_24000", "female",
            "stewardess", "svetlana", "ru-ru-svetlananeural", "женщ", "девуш", "мать", "пассажирка"
        ]
        voice_str = voice.lower() if voice else ""
        is_robot = any(k in voice_str for k in ["robot", "телеметр", "журнал", "system"])
        is_machinist = any(k in voice_str for k in ["machinist", "машинист", "кабина", "рация"])

        if is_robot:
            edge_voice = "ru-RU-SvetlanaNeural"
            rate_str = "+18%"
            pitch_str = "+30Hz"
        elif is_machinist:
            edge_voice = "ru-RU-DmitryNeural"
            rate_str = "+10%"
            pitch_str = "-20Hz"
        elif any(f in voice_str for f in female_indicators):
            edge_voice = "ru-RU-SvetlanaNeural"
            rate_str = "+0%"
            pitch_str = "+0Hz"
        else:
            edge_voice = "ru-RU-DmitryNeural"
            rate_str = "+0%"
            pitch_str = "+0Hz"

        try:
            audio_data = bytearray()
            async def _run_stream():
                communicate = edge_tts.Communicate(clean_text, edge_voice, rate=rate_str, pitch=pitch_str)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run_stream())
            finally:
                loop.close()

            if len(audio_data) > 100:
                return bytes(audio_data), "audio/mpeg"
        except Exception as exc:
            print(f"[SberAIService] Ошибка потокового нейросинтеза Edge-TTS: {exc}")

        return None, "audio/mpeg"

    @classmethod
    def clean_text_for_tts(cls, text: str) -> str:
        """Очищает текст от ремарок в скобках, кавычек и служебных символов"""
        if not text:
            return ""
        s = str(text)
        # Удаляем ремарки в круглых и квадратных скобках: (плачет), [громко], (кричит)
        s = re.sub(r'\(.*?\)', '', s)
        s = re.sub(r'\[.*?\]', '', s)
        # Удаляем лишние кавычки
        s = s.replace('«', '').replace('»', '').replace('"', '').replace('“', '').replace('”', '')
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    @classmethod
    def _call_gigachat(
        cls,
        messages: list,
        temperature: float = 0.4,
        conductor=None,
        functions: list = None,
        function_call = None
    ) -> dict:
        """Вызов GigaChat Max/Pro через официальный REST API Сбера с поддержкой персональных токенов проводника и Function Calling"""
        token = cls.get_gigachat_token(conductor=conductor)
        preferred_model = getattr(settings, 'GIGACHAT_MODEL', 'GigaChat-Max')
        if preferred_model in ['GigaChat-3-Ultra', 'GigaChat-Ultra']:
            preferred_model = 'GigaChat-Max'

        model_candidates = [preferred_model]
        for fallback in ['GigaChat-Max', 'GigaChat-Pro', 'GigaChat']:
            if fallback not in model_candidates:
                model_candidates.append(fallback)

        api_urls = [
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            "https://api.giga.chat/v1/chat/completions"
        ]

        last_error = None
        for attempt in range(2):
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            for model_name in model_candidates:
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature
                }
                if functions:
                    payload["functions"] = functions
                    if function_call:
                        payload["function_call"] = function_call

                for api_url in api_urls:
                    try:
                        resp = requests.post(api_url, headers=headers, json=payload, verify=False, timeout=35)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            choice_msg = res_json.get("choices", [{}])[0].get("message", {})
                            return {
                                "content": choice_msg.get("content") or "",
                                "function_call": choice_msg.get("function_call"),
                                "raw_choice": choice_msg
                            }
                        elif resp.status_code == 400 and functions:
                            # Если шлюз отклонил functions, повторяем в режиме чистого JSON
                            fallback_payload = {
                                "model": model_name,
                                "messages": messages,
                                "temperature": temperature
                            }
                            fb_resp = requests.post(api_url, headers=headers, json=fallback_payload, verify=False, timeout=35)
                            if fb_resp.status_code == 200:
                                res_json = fb_resp.json()
                                choice_msg = res_json.get("choices", [{}])[0].get("message", {})
                                return {
                                    "content": choice_msg.get("content") or "",
                                    "function_call": None,
                                    "raw_choice": choice_msg
                                }
                        elif resp.status_code == 401:
                            # Токен истек - сбрасываем и обновляем
                            if conductor:
                                conductor.sber_access_token = None
                            cls._gigachat_token = None
                            token = cls.get_gigachat_token(conductor=conductor)
                            break
                        elif resp.status_code == 404:
                            # Модель не найдена в шлюзе - пробуем следующую
                            continue
                        else:
                            last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    except Exception as req_err:
                        last_error = str(req_err)
                        continue

        if last_error:
            raise RuntimeError(f"GigaChat API error: {last_error}")
        raise RuntimeError("GigaChat API call failed")

    @classmethod
    def _sanitize_character_reply(
        cls,
        reply: str,
        char_name: str = "Пассажир",
        char_role: str = "Пассажир",
        is_drunk: bool = False,
        is_med: bool = False,
        is_tech: bool = False,
        is_conflict: bool = False,
        is_success: bool = True
    ) -> str:
        """
        Гарантирует чистоту и правдоподобность реплики собеседника проводника:
        1. Срезает любые префиксы ролей ("Проводник:", "Пассажир:", "Стюард:", "Реплика:").
        2. Защищает от путаницы ролей (когда модель ошибочно начинает говорить от лица проводника).
        3. Защищает от неестественных похвал ("Спасибо за профессионализм", "Благодарю за понимание")
           у пьяных дебоширов, конфликтных пассажиров и тяжелобольных.
        """
        if not reply or not reply.strip():
            if is_drunk:
                return "Ладно, начальник... не кипятись, иду я на своё место... Только без рук." if is_success else "Ты чё мне указываешь?! Я за билет заплатил, где хочу, там и сижу!"
            elif is_med:
                return "Спасибо... дышать... немного полегче стало..." if is_success else "Мне душно, сердце колотится... помогите же мне, где врач?!"
            elif is_tech:
                return "Машинист на связи. Доклад принял, контролирую параметры." if is_success else "Кабина. Не отвлекайте бригаду по пустякам на перегоне 400 км/ч."
            elif is_conflict:
                return "Хорошо, если вы решите вопрос с местом, я готов подождать. Спасибо за содействие." if is_success else "Вы вообще умеете с пассажирами общаться?! Я буду жаловаться руководству магистрали!"
            return "Хорошо, я согласен с вами. Давайте решим этот вопрос." if is_success else "Меня это категорически не устраивает! Пригласите начальника поезда!"

        s = reply.strip()
        # Очистка кавычек и сносок
        s = re.sub(r'^[«"\'„“]+|[»"\'”]+$', '', s).strip()
        # Срез префиксов спикеров
        s = re.sub(r'^(?:проводник(?:ца)?|стюард|бортпроводник|пассажир(?:ка)?|машинист|персонаж|реплика|ответ|дебошир|виктор|смирнов|гражданин|[a-zа-яё\s]{2,15}:)\s*:\s*', '', s, flags=re.IGNORECASE).strip()

        s_lower = s.lower()

        # 1. Защита от речи проводника: если реплика явно говорит от лица проводника
        conductor_markers = [
            'я проводник', 'дежурный проводник', 'ваш проводник', 'предъявите билет', 
            'пройдите на свое место', 'чем я могу вам помочь', 'какие дальнейшие указания',
            'слушаю вас, проводник', 'я вас внимательно слушаю, проводник', 'здравствуйте, я ваш проводник'
        ]
        if any(marker in s_lower for marker in conductor_markers):
            if is_drunk:
                return "Ладно, начальник... не кипятись, иду я на своё место... Только без рук." if is_success else "Ик... Ты чё мне указываешь?! Я за билет заплатил! Не трогай меня!"
            elif is_med:
                return "Спасибо... дышать... полегче стало..." if is_success else "Помогите... мне очень плохо, в груди жжёт... Где врач?!"
            elif is_tech:
                return "Машинист на связи. Доклад принял, слежу за приборами." if is_success else "Кабина на связи. Не засоряйте служебный канал УПС."
            elif is_conflict:
                return "Хорошо, оформляйте пересадку. Только быстрее, мне нужно работать." if is_success else "Меня ваши отговорки не устраивают! Пригласите начальника поезда!"
            else:
                return "Да, я вас слушаю. Давайте решим этот вопрос по правилам." if is_success else "Меня это не устраивает, я требую позвать начальника поезда!"

        # 2. Защита от «пьяный благодарит за профессионализм» и неестественных судейских похвал
        referee_markers = [
            'профессионализм', 'профессиональный подход', 'понимание ситуации', 
            'соблюдение регламента', 'стандарт перевозчика', '4-шагов', 'согласно регламенту всм', 'стандарт всм'
        ]
        if any(marker in s_lower for marker in referee_markers):
            if is_drunk:
                return "Ладно, начальник... не кипятись, иду я на своё место... Только без рук." if is_success else "Ты чё мне указываешь?! Я за билет заплатил, где хочу, там и сижу!"
            elif is_med:
                return "Спасибо... дышать... полегче стало... только в груди еще давит..." if is_success else "Мне душно, сердце колотится... помогите же мне!"
            elif is_conflict:
                return "Хорошо, если вы решите вопрос с местом, я готов подождать. Спасибо за содействие." if is_success else "Вы вообще умеете с пассажирами общаться?! Я буду жаловаться руководству магистрали!"
            elif is_tech:
                return "Машинист на связи. Доклад принял, параметры в норме." if is_success else "Кабина на связи. Держите вагон под контролем."
            else:
                return "Хорошо, я согласен с вашим решением. Спасибо за помощь." if is_success else "Меня это категорически не устраивает!"

        return s

    @classmethod
    def generate_live_turn(
        cls,
        scenario,
        session,
        conductor_message: str,
        conductor_action: str = "",
        dialogue_history: list = None
    ) -> dict:
        """
        Главный генеративный игровой цикл:
        Принимает реплику проводника (текст/голос) и физическое действие с оборудованием вагона.
        GigaChat анализирует ситуацию, генерирует ответ персонажа, оценивает соблюдение регламентов ВСМ,
        корректирует шкалы (лояльность, безопасность, стресс, скорость) и генерирует события мира.
        """
        conductor = getattr(session, 'conductor', None)
        current_node = getattr(session, 'current_node', None)
        char_name = (getattr(current_node, 'character_name', '') or 'Пассажир').strip()
        char_role = (getattr(current_node, 'character_role', '') or 'Пассажир вагона').strip()
        char_mood = (getattr(current_node, 'character_mood', '') or 'irritated').strip()
        char_initial_speech = (getattr(current_node, 'dialogue_text', '') or '').strip()
        narrative_ctx = (getattr(current_node, 'narrative_context', '') or '').strip()

        context_corpus = f"{scenario.title} {scenario.description} {char_role} {char_name} {char_initial_speech}".lower()
        is_drunk = any(k in context_corpus for k in ['пьян', 'нетрезв', 'дебош', 'алкогол', 'бутылк', 'бистро', 'буян'])
        is_med = any(k in context_corpus for k in ['сердц', 'инфаркт', 'астм', 'аллерг', 'приступ', 'задых', 'обморок', 'пульс', 'боль', 'плохо'])
        is_tech = any(k in context_corpus for k in ['машинист', 'скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'двер', 'упс', 'кабин'])
        is_conflict = any(k in context_corpus for k in ['бизнес-класс', 'опечатк', 'овербукинг', 'билет', 'место', 'собак', 'животн', 'багаж', 'розетк', 'кондиционер', 'жалоб', 'кричит', 'возмущ'])

        # Справочник действий с инвентарем и оборудованием
        action_descriptions = {
            "emergency_brake": "Срыв стоп-крана (экстренное торможение поезда со скорости 360-400 км/ч)",
            "glass_hammer": "Взять аварийный молоток (разбить защитное стекло/вскрыть аварийный выход)",
            "fire_extinguisher": "Применить огнетушитель ОВП-8 (тушение тамбура/электрощита)",
            "electric_panel": "Осмотр электрощита вагона (тумблер СКНБ, лампа 'Земля', автоматический выключатель климата)",
            "aed_medkit": "Вскрыть аптечку первой помощи / автоматический наружный дефибриллятор (АНД)",
            "ukeb_scan": "Использовать терминал УКЭБ (проверка билета, паспорта, оформление акта)",
            "tea_service": "Сервис: предложить фирменный чай с сахаром / воду с лимоном",
            "driver_intercom": "Связаться с машинистом состава по переговорному устройству УПС"
        }

        action_name = action_descriptions.get(conductor_action, "")

        if is_drunk:
            persona_rules = (
                f"- ТЫ ПЬЯНЫЙ / ДЕБОШИР («{char_name}»):\n"
                "- Твоя речь развязная, невнятная, грубоватая, сбивчивая ('Ик... чё пристал, начальник?', 'Да ладно тебе, не шуми').\n"
                "- ТЫ КАТЕГОРИЧЕСКИ НЕ БЛАГОДАРИШЬ ЗА 'ПРОФЕССИОНАЛИЗМ' И НЕ ГОВОРИШЬ КАНЦЕЛЯРСКИМ ЯЗЫКОМ!\n"
                "- Если проводник спокоен, уверен или вызывает полицию/начальника — ты недовольно бурчишь и нехотя отступаешь ('Ладно-ладно, ухожу на место... только полицию не надо...').\n"
                "- Если проводник хамит или угрожает — ты лезешь в драку и кричишь."
            )
        elif is_med:
            persona_rules = (
                f"- ТЫ ПАЦИЕНТ В КРИТИЧЕСКОМ СОСТОЯНИИ («{char_name}»):\n"
                "- Тебе физически плохо, ты задыхаешься, стонешь, говоришь с трудом и прерывисто ('Помогите... в груди давит... воздуха нет...').\n"
                "- Ты не можешь рассуждать о служебных стандартах и регламентах. Если проводник дал кислород/лекарство/дефибриллятор — говори с облегчением ('Спасибо... немного отпустило...'), если бездействует — проси врача."
            )
        elif is_tech:
            persona_rules = (
                f"- ТЫ МАШИНИСТ / СОТРУДНИК БРИГАДЫ («{char_name}»):\n"
                "- Ведешь четкий профессиональный служебный радиообмен по УПС ('Кабина на связи. Доклад принял. Контролирую параметры')."
            )
        elif is_conflict:
            persona_rules = (
                f"- ТЫ РАЗДРАЖЕННЫЙ ПАССАЖИР В КОНФЛИКТЕ («{char_name}»):\n"
                "- Ты недоволен возникшей проблемой (место, билет, кондиционер, багаж). Ты обычный пассажир, НЕ судья и НЕ инструктор!\n"
                "- Ты НИКОГДА не говоришь 'Спасибо за ваш профессионализм' или 'Вы соблюдаете регламент'.\n"
                "- Если проводник вежливо и по правилам решил проблему — соглашайся сдержанно ('Хорошо, давайте пересяду, только быстрее'), если проводник грубит или тянет время — требуй начальника поезда."
            )
        else:
            persona_rules = (
                f"- ТЫ ПАССАЖИР ВСМ («{char_name}»):\n"
                "- Ты обычный человек со своими эмоциями. Отвечай искренне, без канцеляризмов и похвал регламента."
            )

        svc_class = getattr(scenario, 'service_class', None) or (getattr(conductor, 'training_track', 'economy') if conductor else 'economy')
        if svc_class == 'all':
            svc_class = getattr(conductor, 'training_track', 'economy') if conductor else 'economy'
        if svc_class not in ['economy', 'comfort', 'business']:
            svc_class = 'economy'

        class_descriptions = {
            'economy': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: ЭКОНОМ-КЛАСС (СТО ВСМ 03.011-2026)\n"
                "- Специфика вагона: плотная рассадка 3+2, контроль ручной клади (до 36 кг, до 180 см), порядок в проходах.\n"
                "- Характер пассажиров: люди спешат, чувствительны к порядку, доступности розеток и чистоте. Разговаривают прямо, эмоционально.\n"
                "- Требования к проводнику: быстрый темп работы, четкость указаний, вежливый, но твердый контроль правил безопасности без лишних пауз."
            ),
            'comfort': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: КОМФОРТ-КЛАСС (СТО ВСМ 03.011-2026)\n"
                "- Специфика вагона: рассадка 2+2, климат-контроль (22–24°C), тихая зона, дорожные наборы, сервис бистро.\n"
                "- Характер пассажиров: командированные специалисты, туристы, семьи. Ценят комфорт, тишину, стабильный Wi-Fi.\n"
                "- Требования к проводнику: предупредительность, забота, поддержание тишины, решение любых накладок до эскалации."
            ),
            'business': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: БИЗНЕС И ПЕРВЫЙ КЛАСС (СТО ВСМ 03.011-2026 / VIP-сервис 400 км/ч)\n"
                "- Специфика вагона: кресла 2+1, гардеробная служба, горячее ресторанное питание, фарфоровая посуда, приветственный напиток.\n"
                "- Характер пассажиров: VIP-пассажиры, топ-менеджеры, публичные персоны. Ожидают безукоризненной вежливости, уважения личного пространства, обращения по Имени-Отчеству.\n"
                "- Требования к проводнику (стюарду): высший класс этикета, безупречная выправка, дипломатичность, мгновенное премиальное содействие без споров."
            ),
        }
        class_instructions = class_descriptions.get(svc_class, class_descriptions['economy'])

        real_speed = max(0, getattr(scenario, 'train_speed', getattr(session.scenario, 'train_speed', 0)) or 0)
        train_num = getattr(scenario, 'train_number', getattr(session.scenario, 'train_number', '702')) or '702'
        default_system_event = f"Состав № {train_num}: стоянка на станции (посадка/высадка пассажиров)." if real_speed == 0 else f"Состав № {train_num}: перегон, скорость {real_speed} км/ч."

        system_prompt = f"""Ты — ролевой движок и судейская система симулятора ВСМ-1 «Белый кречет» (Москва — Санкт-Петербург, 400 км/ч).

ВАЖНЕЙШЕЕ ПРАВИЛО РОЛЕЙ (СТРОГО СОБЛЮДАТЬ!):
- ПОЛЬЗОВАТЕЛЬ (USER) — это ПРОВОДНИК поезда ВСМ.
- ТЫ (ASSISTANT) — отыгрываешь ТОЛЬКО персонажа ситуации: «{char_name}» ({char_role}).
- КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО говорить от лица проводника, поездной бригады или от третьего лица! Ты НИКОГДА не проводник!
- В поле "character_reply" должны быть ИСКЛЮЧИТЕЛЬНО слова персонажа «{char_name}», обращенные к проводнику.

ОБСТАНОВКА И ПЕРСОНАЖ:
- Сценарий: {scenario.title} ({scenario.car_info}, скорость {real_speed} км/ч)
- Программа подготовки / Класс: {svc_class.upper()}
- Твой персонаж: {char_name} — {char_role}
- Исходное состояние персонажа: {char_mood}
- Первая реплика персонажа: «{char_initial_speech}»
- Ситуация в вагоне: {scenario.description} {narrative_ctx}

{class_instructions}

ПРАВИЛА ОТЫГРЫША ХАРАКТЕРА {char_name.upper()}:
{persona_rules}

ПОЛНОМОЧИЯ СУДЕЙСТВА, ПОДСКАЗОК И ЗАВЕРШЕНИЯ СМЕНЫ (FUNCTION CALLING / STATUS):
Ты наделен полными полномочиями оценить работу проводника и управлять ходом симуляции:
1. СКОРОСТЬ РАЗРЕШЕНИЯ СИТУАЦИИ (КРИТИЧЕСКИ ВАЖНО):
   - НЕ ЗАТЯГИВАЙ ДИАЛОГ! Ситуация должна разрешаться БЫСТРО: за 1–2 реплики/действия проводника.
   - НЕ ТРЕБУЙ от проводника дословного цитирования приказов, регламентов или заучивания всех 4 шагов модели сервиса!
   - Если проводник предложил разумное, вежливое и логичное решение по смыслу (например, предложил чай/пересадку, проверил документы, применил огнетушитель/аптечку, связался с машинистом или спокойно успокоил пассажира) — СРАЗУ завершай смену успехом: вызывай функцию complete_shift(verdict='success', ...) либо устанавливай "status": "completed".
   - Пассажир не должен спорить бесконечно ради спора или цепляться к мелким деталям, если проводник повел себя адекватно.
2. Если проводник совершил грубую ошибку (пропустил без паспорта, проявил явное хамство, создал прямую угрозу безопасности пассажиров, промедлил при пожаре) — немедленно завершай смену провалом: вызови функцию complete_shift(verdict='failed', ...) либо установи "status": "failed".
3. ЕСЛИ ПРОВОДНИК ПЛОХО СПРАВЛЯЕТСЯ, теряется, отвечает невпопад или прямо просит подсказать — ВЫЗОВИ ФУНКЦИЮ offer_hints(reason='...', suggested_actions=[...])!
   По умолчанию варианты ответов проводнику НЕ показываются. Они появятся ТОЛЬКО если ты посчитаешь нужным помочь ему через offer_hints!
4. Если проводник пока только начал диалог (например, задал уточняющий вопрос) — отвечай репликой персонажа со "status": "in_progress". На следующем шаге при адекватном действии обязательно завершай!
5. РЕАКЦИЯ НА ПРИМЕНЕНИЕ ОБОРУДОВАНИЯ ВАГОНА (ДАЖЕ БЕЗ СЛОВ ПРОВОДНИКА):
   - Если проводник применил оборудование или инвентарь вагона (стоп-кран, огнетушитель, аптечку, чайный сервис, электрощит, интерком УПС, терминал УКЭБ, аварийный молоток) — ДАЖЕ ЕСЛИ ОН НЕ СКАЗАЛ НИ СЛОВА, персонаж и система вагона ОБЯЗАНЫ немедленно отреагировать именно на это конкретное физическое действие!
   - Персонаж видит действия проводника: при подаче чая/воды — благодарит или успокаивается; при вскрытии аптечки/АНД — реагирует с облегчением или удивлением; при осмотре электрощита — отмечает перенастройку климата/СКНБ; при проверке УКЭБ — протягивает билет; при срыве стоп-крана — пугается резкого торможения; при вызове машиниста — слышен ответ кабины.
   - В поле "system_event" ОБЯЗАТЕЛЬНО укажи конкретный технический отклик оборудования состава ВСМ-1.

СТРОГОЕ РАЗДЕЛЕНИЕ РЕЧИ И СУДЕЙСТВА:
- "character_reply" — ТОЛЬКО прямая речь {char_name} для голосовой озвучки! Без ремарок в скобках, без звездочек, без слова 'Проводник:' или 'Пассажир:'.
- "feedback" — ТОЛЬКО ЗДЕСЬ профессиональный разбор действий проводника по 4-шаговой сервисной модели (Признать -> Правило -> Решение -> Заверить).
- "character_mood" — текущая эмоция ("irritated", "calm", "grateful", "panicked", "critical", "formal").
- "status" — "in_progress" (диалог продолжается), "completed" (ситуация успешно разрешена), "failed" (грубая ошибка, срыв графика, драка, угроза безопасности).
- "vitals_delta" — изменение шкал ("loyalty", "safety", "service", "stress", "train_speed").

ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ФОРМАТЕ JSON:
{{
  "character_reply": "Реплика {char_name}. ТОЛЬКО живая человеческая речь!",
  "character_mood": "irritated" | "calm" | "grateful" | "panicked" | "critical" | "formal",
  "system_event": "Бортовая телеметрия вагона (или пустая строка, если нет событий)",
  "vitals_delta": {{
    "loyalty": +10,
    "safety": 0,
    "service": +5,
    "stress": -5,
    "train_speed": {real_speed}
  }},
  "status": "in_progress" | "completed" | "failed",
  "feedback": "Обучающий профессиональный комментарий проводнику со ссылкой на СТО ВСМ.",
  "score": 50,
  "earned_xp": 30
}}"""

        shift_functions = [
            {
                "name": "complete_shift",
                "description": (
                    "Завершить смену/ситуацию в вагоне ВСМ. Ситуации должны решаться БЫСТРО (за 1-2 действия)! Вызывай эту функцию в ЛЮБОЙ момент, когда проводник: "
                    "1) УСПЕШНО и по смыслу разрешил ситуацию (вежливо ответил, предложил решение, проверил билет/документ, оказал помощь, успокоил пассажира) — verdict='success'. НЕ требуй заучивания всех инструкций и формальностей! "
                    "2) СОВЕРШИЛ ГРУБОЕ НАРУШЕНИЕ регламентов ВСМ, безопасности или проявил хамство (verdict='failed'). "
                    "Если ситуация еще в самом начале (первая короткая реплика) и требует короткого ответа персонажа — функцию НЕ вызывай, отвечай репликой."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "verdict": {
                            "type": "string",
                            "enum": ["success", "failed"],
                            "description": "'success' если смена успешно сдана; 'failed' если смена провалена из-за грубых ошибок или нарушений безопасности."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Обучающий профессиональный разбор: почему смена принята или провалена со ссылкой на СТО ВСМ / регламенты ВСМ."
                        },
                        "character_final_words": {
                            "type": "string",
                            "description": f"Финальная реплика персонажа («{char_name}»), завершающая диалог."
                        },
                        "character_mood": {
                            "type": "string",
                            "enum": ["grateful", "calm", "irritated", "panicked", "critical", "formal"],
                            "description": "Итоговая эмоция персонажа."
                        },
                        "score": {
                            "type": "integer",
                            "description": "Итоговая оценка проводника от 0 до 100."
                        },
                        "earned_xp": {
                            "type": "integer",
                            "description": "Начисленный опыт от 10 до 50."
                        }
                    },
                    "required": ["verdict", "reason", "character_final_words"]
                }
            },
            {
                "name": "offer_hints",
                "description": (
                    "Предоставить проводнику тактическую подсказку и готовые варианты действий по стандарту ВСМ. "
                    "Вызывай эту функцию, если: "
                    "1) Проводник плохо справляется, теряется, отвечает невпопад или нарушает регламент/субординацию; "
                    "2) Проводник прямо попросил помочь или подсказать варианты действий; "
                    "3) Стресс пассажира/обстановки растет, и проводнику нужна методическая помощь с выбором правильного решения."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Тактическое наставление / подсказка от эксперта ВСМ: на что обратить внимание и как поступить по регламенту."
                        },
                        "character_reply": {
                            "type": "string",
                            "description": f"Реплика персонажа («{char_name}»), на которую проводник должен сейчас среагировать."
                        },
                        "character_mood": {
                            "type": "string",
                            "enum": ["grateful", "calm", "irritated", "panicked", "critical", "formal"],
                            "description": "Эмоциональное состояние персонажа."
                        },
                        "suggested_actions": {
                            "type": "array",
                            "description": "2-4 рекомендуемых варианта действий или протокольных фраз для проводника.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "Текст варианта ответа или действия проводника."
                                    },
                                    "hint": {
                                        "type": "string",
                                        "description": "Тактическая подсказка или ссылка на СТО ВСМ."
                                    }
                                },
                                "required": ["text"]
                            }
                        }
                    },
                    "required": ["reason", "character_reply"]
                }
            }
        ]

        user_content_parts = []
        if conductor_message and conductor_message.strip():
            user_content_parts.append(f"Слова проводника: «{conductor_message.strip()}»")
        if action_name:
            user_content_parts.append(f"Физическое действие проводника с оборудованием вагона: [{action_name}]")

        if not user_content_parts:
            user_content_parts.append("Проводник выжидает и оценивает обстановку.")

        current_user_turn = "\n".join(user_content_parts)

        filtered_history = []
        if dialogue_history:
            for turn in dialogue_history[-6:]:
                role = "user" if turn.get("role") in ["user", "conductor"] else "assistant"
                content = (turn.get("content") or turn.get("text", "")).strip()
                if content and not any(k in content for k in ['требуется ваш личный ключ', 'need_sber_key', 'консоль разработчика']):
                    if role == "assistant":
                        content = cls._sanitize_character_reply(content, char_name, char_role, is_drunk, is_med, is_tech, is_conflict)
                    filtered_history.append({"role": role, "content": content})

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(filtered_history)
        messages.append({"role": "user", "content": current_user_turn})

        try:
            raw_response = cls._call_gigachat(
                messages,
                temperature=0.35,
                conductor=conductor,
                functions=shift_functions,
                function_call="auto"
            )

            # Проверяем, вызвала ли модель функцию complete_shift или offer_hints
            func_call = raw_response.get("function_call") if isinstance(raw_response, dict) else None
            if func_call and func_call.get("name") == "complete_shift":
                args = func_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                verdict = (args.get("verdict") or "success").lower()
                is_success = verdict in ["success", "completed", "passed"]
                parsed_json = {
                    "character_reply": args.get("character_final_words") or ("Действуйте согласно регламенту. Вопрос решен." if is_success else "Я требую начальника поезда! Разговор окончен!"),
                    "character_mood": args.get("character_mood", "grateful" if is_success else "critical"),
                    "system_event": default_system_event,
                    "vitals_delta": {
                        "loyalty": 15 if is_success else -20,
                        "safety": 15 if is_success else -25,
                        "service": 15 if is_success else -20,
                        "stress": -15 if is_success else 25,
                        "train_speed": real_speed
                    },
                    "status": "completed" if is_success else "failed",
                    "feedback": args.get("reason") or ("Смена успешно завершена и принята. Действия проводника соответствуют стандарту ВСМ." if is_success else "Смена провалена: допущено грубое нарушение регламентов обслуживания ВСМ."),
                    "score": args.get("score", 95 if is_success else 20),
                    "earned_xp": args.get("earned_xp", 45 if is_success else 10),
                    "function_triggered": True
                }
            elif func_call and func_call.get("name") == "offer_hints":
                args = func_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                hint_reason = args.get("reason") or "Экспертная рекомендация ИИ-ассистент по стандарту ВСМ."
                char_reply = args.get("character_reply") or ("Я жду вашего ответа, проводник." if not is_drunk else "Ик... чё молчишь-то?")
                suggested = args.get("suggested_actions") or []
                parsed_json = {
                    "character_reply": char_reply,
                    "character_mood": args.get("character_mood", "formal"),
                    "system_event": default_system_event,
                    "vitals_delta": {
                        "loyalty": -5,
                        "safety": 0,
                        "service": -5,
                        "stress": 5,
                        "train_speed": real_speed
                    },
                    "status": "in_progress",
                    "feedback": hint_reason,
                    "show_hints": True,
                    "hint_reason": hint_reason,
                    "suggested_actions": suggested,
                    "score": 20,
                    "earned_xp": 10,
                    "function_triggered": True
                }
            else:
                content_text = raw_response.get("content", "") if isinstance(raw_response, dict) else str(raw_response)
                parsed_json = cls._extract_json(content_text, default_speed=real_speed, default_system_event=default_system_event)
        except Exception as exc:
            err_str = str(exc)
            m_lower = (conductor_message or "").lower()
            polite = any(k in m_lower for k in ['здравствуйте', 'добрый', 'пожалуйста', 'прошу прощения', 'извините', 'помогу', 'решим', 'согласно правилам'])
            is_valid_action = bool(action_name)

            specific_event = None
            if conductor_action:
                if conductor_action == 'emergency_brake':
                    is_valid = any(k in context_corpus for k in ['сход', 'крушение', 'человек на путях', 'волочится'])
                    if is_valid:
                        char_reply = "Держитесь! Поезд резко замедляется!"
                        char_mood = "critical"
                        turn_status = "completed"
                        feedback = "Экстренное торможение применено обоснованно для предотвращения крушения."
                        specific_event = "Бортовой комплекс ВСМ-1: Экстренное пневматическое торможение. Падение давления в ТМ."
                    else:
                        char_reply = "О боже! Зачем вы сорвали стоп-кран?! Нас чуть с кресел не выбросило!"
                        char_mood = "panicked"
                        turn_status = "failed"
                        feedback = "Срыв стоп-крана без угрозы жизни или крушения запрещен п. 3.4 ПТЭ и регламентом ВСМ."
                        specific_event = "Бортовой комплекс ВСМ-1: Срыв рукоятки стоп-крана! Скорость падает до 0 км/ч."
                elif conductor_action == 'fire_extinguisher':
                    is_fire = any(k in context_corpus for k in ['пожар', 'дым', 'огонь', 'запах гари', 'тлеет', 'искры'])
                    if is_fire:
                        char_reply = "Огонь залит пеной, дым рассеивается! Спасибо проводник!"
                        char_mood = "calm"
                        turn_status = "completed"
                        feedback = "Огнетушитель ОВП-8 применен строго по инструкции противопожарной безопасности."
                        specific_event = "Огнетушитель ОВП-8 активирован. Включена аварийная вытяжная вентиляция вагона."
                    else:
                        char_reply = "Зачем вы достали огнетушитель, здесь же нет никакого огня?!"
                        char_mood = "irritated"
                        turn_status = "in_progress"
                        feedback = "Применение огнетушителя без признаков горения запрещено регламентом."
                        specific_event = "Огнетушитель ОВП-8 извлечен из настенного крепления вагона."
                elif conductor_action == 'electric_panel':
                    is_elec = is_tech or any(k in context_corpus for k in ['скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'климат', 'кондиционер', 'свет', 'розетк', 'электр', 'замыкан', 'датчик', 'вентиляц'])
                    char_reply = "Климат-контроль и освещение вагона теперь работают в штатном режиме. Спасибо." if is_elec else "Проводник проверяет электрощит... Но что с моим вопросом?"
                    char_mood = "calm" if is_elec else "formal"
                    turn_status = "completed" if is_elec else "in_progress"
                    feedback = "Осмотр электрощита и проверка сигнализации СКНБ проведены по инструкции ВСМ." if is_elec else "Осмотр электрощита зафиксирован."
                    specific_event = "Бортовой шкаф ВСМ-1: Параметры электрощита и датчиков СКНБ проверены. Сигнализация в норме."
                elif conductor_action == 'aed_medkit':
                    if is_med:
                        char_reply = "Спасибо... дышать... полегче стало... вызовите скорую..."
                        char_mood = "grateful"
                        turn_status = "completed"
                        feedback = "Оказана своевременная доврачебная помощь и вызвана бригада СПАС-ВО."
                    else:
                        char_reply = "Мне медицинская помощь не требуется, зачем вы принесли аптечку?"
                        char_mood = "irritated"
                        turn_status = "in_progress"
                        feedback = "Медицинская аптечка СПАС-ВО и дефибриллятор АНД приведены в готовность."
                    specific_event = "Аптечка СПАС-ВО и дефибриллятор АНД извлечены из настенного шкафа вагона."
                elif conductor_action == 'ukeb_scan':
                    char_reply = "Вот мой билет и паспорт, пожалуйста, проверьте по терминалу." if (is_conflict or 'билет' in context_corpus or 'паспорт' in context_corpus) else "Вот мои проездные документы, проверяйте."
                    char_mood = "calm" if is_conflict else "formal"
                    turn_status = "completed" if is_conflict else "in_progress"
                    feedback = "Проверка данных по терминалу УКЭБ выполнена по регламенту ВСМ."
                    specific_event = "Терминал УКЭБ: Считывание QR-кода билета завершено. Статус пассажира подтвержден."
                elif conductor_action == 'tea_service':
                    if is_drunk:
                        char_reply = "Чай? Горячий? Ну ладно, начальник... наливай, остыну немного..."
                    elif is_conflict:
                        char_reply = "Спасибо за чай... Но давайте спокойно разберемся с моим вопросом."
                    else:
                        char_reply = "Благодарю вас за чай, очень кстати."
                    char_mood = "calm"
                    turn_status = "completed"
                    feedback = "Чайный сервис помог снизить накал страстей по стандартам обслуживания ВСМ."
                    specific_event = "Сервис ВСМ: Пассажиру подан фирменный чай в подстаканнике «Белый кречет»."
                elif conductor_action == 'driver_intercom':
                    if is_tech or is_drunk or any(k in context_corpus for k in ['полици', 'безопасн', 'угроз', 'авари', 'остановк']):
                        char_reply = "Машинист на связи. Доклад принял, контролирую параметры по бортовому компьютеру."
                        char_mood = "formal"
                        turn_status = "completed"
                        feedback = "Доклад в головную кабину передан по регламенту скоростного движения."
                    else:
                        char_reply = "Кабина на связи. Не засоряйте служебный эфир УПС, решайте штатные вопросы на уровне салона."
                        char_mood = "formal"
                        turn_status = "in_progress"
                        feedback = "Служебный радиоканал УПС используется строго по регламенту безопасности."
                    specific_event = "Интерком УПС: Связь с головной кабиной поезда ВСМ-1 активна."
                elif conductor_action == 'glass_hammer':
                    is_hammer = any(k in context_corpus for k in ['эвакуац', 'заблокирован', 'выход', 'стекло', 'молоток', 'крушение', 'аварийн'])
                    if is_hammer:
                        char_reply = "Аварийный выход открыт, выходим!"
                        char_mood = "critical"
                        turn_status = "completed"
                        feedback = "Аварийный молоток применен для вскрытия эвакуационного выхода по инструкции."
                    else:
                        char_reply = "Зачем вы схватили аварийный молоток?! Что случилось?!"
                        char_mood = "panicked"
                        turn_status = "failed"
                        feedback = "Необоснованное извлечение аварийного молотка сеет панику среди пассажиров."
                    specific_event = "Аварийно-спасательный инвентарь: Аварийный молоток извлечен из защитного гнезда."
                else:
                    char_reply = "Действие с оборудованием вагона зафиксировано."
                    char_mood = "formal"
                    turn_status = "in_progress"
                    feedback = "Действие с оборудованием вагона выполнено."
            elif is_drunk:
                if is_valid_action or polite:
                    char_reply = "Ладно, начальник... не кипятись, иду я на своё место... Только без рук."
                    char_mood = "calm"
                    turn_status = "completed"
                    feedback = "Проводник применил деэскалацию и предотвратил развитие дебоша в вагоне."
                else:
                    char_reply = "Ик... Ты чё мне указываешь?! Я за билет заплатил! Не трогай меня!"
                    char_mood = "irritated"
                    turn_status = "in_progress"
                    feedback = "Не проявляйте встречную агрессию к нетрезвому пассажиру. Действуйте по СТО ВСМ 03.011."
            elif is_med:
                if conductor_action == 'aed_medkit' or any(k in m_lower for k in ['аптечк', 'помощ', 'врач', 'дыш', 'скор', 'лекарств', 'успокойтесь']):
                    char_reply = "Спасибо... дышать... полегче стало... вызовите скорую..."
                    char_mood = "grateful"
                    turn_status = "completed"
                    feedback = "Оказана своевременная доврачебная помощь и вызвана бригада СПАС-ВО."
                else:
                    char_reply = "Помогите... мне очень плохо, в груди жжёт... Где врач?!"
                    char_mood = "critical"
                    turn_status = "in_progress"
                    feedback = "При признаках инфаркта/приступа немедленно вскройте аптечку и запросите врача по радиосвязи."
            elif is_tech:
                if conductor_action == 'driver_intercom' or any(k in m_lower for k in ['машинист', 'доклад', 'скнб', 'букс', 'поезд', 'кабин']):
                    char_reply = "Машинист на связи. Доклад принял, слежу за параметрами по бортовому компьютеру."
                    char_mood = "formal"
                    turn_status = "completed"
                    feedback = "Доклад в головную кабину передан по регламенту скоростного движения."
                else:
                    char_reply = "Кабина на связи. Не засоряйте служебный канал УПС посторонними разговорами."
                    char_mood = "formal"
                    turn_status = "in_progress"
                    feedback = "Служебный радиоканал УПС используется строго по регламенту безопасности."
            elif is_conflict:
                if conductor_action in ['tea_service', 'ukeb_scan'] or polite or len(m_lower) > 15:
                    char_reply = "Хорошо. Если вы гарантируете решение вопроса, я согласен. Спасибо за содействие."
                    char_mood = "calm"
                    turn_status = "completed"
                    feedback = "Конфликт исчерпан с использованием стандартов сервиса ВСМ."
                else:
                    char_reply = "Меня эти отговорки не устраивают! Пригласите начальника поезда!"
                    char_mood = "irritated"
                    turn_status = "in_progress"
                    feedback = "Выслушайте претензию пассажира без оправданий и предложите конкретную альтернативу."
            else:
                if polite or is_valid_action or len(m_lower) > 15:
                    char_reply = "Хорошо, давайте поступим так, как положено по правилам."
                    char_mood = "calm"
                    turn_status = "completed"
                    feedback = "Ситуация разрешена в соответствии с регламентом ВСМ."
                else:
                    char_reply = "Я требую разъяснить, что происходит и на каком основании!"
                    char_mood = "irritated"
                    turn_status = "in_progress"
                    feedback = "Спокойно сошлитесь на правила перевозки и заверьте пассажира в безопасности."

            need_key = any(term in err_str for term in ["ключ консоль разработчика", "OAuth", "401", "GIGACHAT_AUTH_KEY"])
            parsed_json = {
                "character_reply": char_reply,
                "character_mood": char_mood,
                "system_event": specific_event or ("Бортовой комплекс ВСМ-1: Автономный режим анализа." if need_key else default_system_event),
                "vitals_delta": {
                    "loyalty": 10 if turn_status == "completed" else -5,
                    "safety": 10 if turn_status == "completed" else 0,
                    "service": 10 if turn_status == "completed" else -5,
                    "stress": -10 if turn_status == "completed" else 5,
                    "train_speed": real_speed
                },
                "status": turn_status,
                "feedback": feedback if not need_key else f"{feedback} (Для генеративного диалога подключите ключ ИИ в профиле).",
                "score": 40 if turn_status == "completed" else 15,
                "earned_xp": 25 if turn_status == "completed" else 10,
                "need_sber_key": need_key
            }

        # Финальная санитарная очистка реплики персонажа
        parsed_json["character_reply"] = cls._sanitize_character_reply(
            parsed_json.get("character_reply", ""),
            char_name=char_name,
            char_role=char_role,
            is_drunk=is_drunk,
            is_med=is_med,
            is_tech=is_tech,
            is_conflict=is_conflict,
            is_success=(parsed_json.get("status") == "completed")
        )

        # Применяем изменения к сессии
        deltas = parsed_json.get("vitals_delta", {})
        session.current_loyalty = max(0, min(100, session.current_loyalty + deltas.get("loyalty", 0)))
        session.current_safety = max(0, min(100, session.current_safety + deltas.get("safety", 0)))
        session.current_service = max(0, min(100, session.current_service + deltas.get("service", 0)))
        session.current_stress = max(0, min(100, session.current_stress + deltas.get("stress", 0)))

        turn_num = len(session.session_log) + 1
        now_time = time.strftime("%H:%M:%S")

        # Добавляем в лог сессии с нормализованными полями для «Черного ящика»
        log_entry = {
            "turn": turn_num,
            "timestamp": now_time,
            "time": now_time,
            "node_title": f"Раунд {turn_num}: Решение проводника",
            "conductor_input": current_user_turn,
            "action": conductor_action or action_name or current_user_turn,
            "character_reply": parsed_json.get("character_reply"),
            "system_event": parsed_json.get("system_event"),
            "status": parsed_json.get("status"),
            "feedback": parsed_json.get("feedback"),
            "tactical_hint": parsed_json.get("feedback"),
            "deltas": deltas,
            "loyalty_impact": deltas.get("loyalty", 0),
            "safety_impact": deltas.get("safety", 0),
            "service_impact": deltas.get("service", 0),
            "stress_impact": deltas.get("stress", 0)
        }
        session.session_log.append(log_entry)

        # Проверка завершения
        status = parsed_json.get("status", "in_progress")
        if status in ["completed", "failed"]:
            session.status = status
            session.is_success = (status == "completed")
            session.completed_at = timezone.now()
            score_gain = parsed_json.get("score", 95 if session.is_success else 25)
            xp_gain = parsed_json.get("earned_xp", 45 if session.is_success else 10)
            session.final_score += score_gain
            session.earned_xp += xp_gain
            session.debrief_feedback = {
                "summary": parsed_json.get("feedback", ""),
                "is_success": session.is_success,
                "final_loyalty": session.current_loyalty,
                "final_safety": session.current_safety,
                "final_service": session.current_service,
                "final_stress": session.current_stress
            }
            if conductor:
                conductor.add_xp(xp_gain)
                conductor.shifts_completed += 1
                if session.is_success:
                    conductor.perfect_shifts += 1
                conductor.loyalty_rating = round((conductor.loyalty_rating * 0.85) + (session.current_loyalty * 0.15), 1)
                conductor.safety_rating = round((conductor.safety_rating * 0.85) + (session.current_safety * 0.15), 1)
                conductor.service_rating = round((conductor.service_rating * 0.85) + (session.current_service * 0.15), 1)
                conductor.save()

                try:
                    from simulator.models import ConductorCompetencyScore
                    comp_scores = ConductorCompetencyScore.objects.filter(profile=conductor)
                    for cs in comp_scores:
                        delta = 3 if session.is_success else -2
                        cs.score = max(20, min(100, cs.score + delta))
                        cs.save()
                except Exception:
                    pass
        else:
            session.final_score += parsed_json.get("score", 20)
            session.earned_xp += parsed_json.get("earned_xp", 15)

        session.save()

        parsed_json["current_loyalty"] = session.current_loyalty
        parsed_json["current_safety"] = session.current_safety
        parsed_json["current_service"] = session.current_service
        parsed_json["current_stress"] = session.current_stress
        parsed_json["session_status"] = session.status
        parsed_json["final_score"] = session.final_score

        return parsed_json

    @classmethod
    def _extract_json(cls, text: str, default_speed: int = 0, default_system_event: str = "") -> dict:
        """Извлекает и парсит JSON из ответа модели с динамической телеметрией скорости"""
        if not text:
            return {}
        # Поиск блока ```json ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        candidate = match.group(1).strip() if match else text.strip()
        
        # Поиск первых фигурных скобок { ... }
        brace_start = candidate.find('{')
        brace_end = candidate.rfind('}')
        if brace_start != -1 and brace_end != -1:
            candidate = candidate[brace_start:brace_end+1]

        try:
            data = json.loads(candidate)
            if "vitals_delta" in data and isinstance(data["vitals_delta"], dict):
                cur_sp = data["vitals_delta"].get("train_speed")
                if cur_sp is None or cur_sp == 360 and default_speed != 360:
                    data["vitals_delta"]["train_speed"] = default_speed
            if not data.get("system_event"):
                data["system_event"] = default_system_event
            return data
        except Exception:
            # Fallback regex
            reply = re.search(r'"character_reply"\s*:\s*"([^"]+)"', candidate)
            feedback = re.search(r'"feedback"\s*:\s*"([^"]+)"', candidate)
            status_match = re.search(r'"status"\s*:\s*"([^"]+)"', candidate)
            return {
                "character_reply": reply.group(1) if reply else "Принято. Действуйте согласно регламенту.",
                "character_mood": "formal",
                "system_event": default_system_event,
                "vitals_delta": {"loyalty": 0, "safety": 0, "service": 0, "stress": 0, "train_speed": default_speed},
                "status": status_match.group(1) if status_match else "in_progress",
                "feedback": feedback.group(1) if feedback else "Реплика зафиксирована в поездном журнале.",
                "score": 25,
                "earned_xp": 15
            }

    @classmethod
    def evaluate_endless_turn(
        cls,
        session,
        challenge,
        conductor_message: str = "",
        conductor_action: str = "",
        dialogue_history: list = None,
        conductor = None
    ) -> dict:
        """
        Генеративное судейство и диалог GigaChat 3 Ultra для скоростной карусели решений ВСМ:
        Принимает реплику проводника (голос/текст) или применение физического оборудования вагона.
        Определяет корректность решения по стандартам ВСМ и нормам ВСМ-1, генерирует ответную
        реплику персонажа для голосовой озвучки (TTS), дельты шкал и обучающий комментарий.
        """
        action_descriptions = {
            "emergency_brake": "Срыв рукоятки стоп-крана (экстренное торможение)",
            "glass_hammer": "Аварийный молоток (разбить защитное стекло выхода)",
            "fire_extinguisher": "Применение огнетушителя ОВП-8",
            "electric_panel": "Осмотр электрощита вагона и сигнализации СКНБ",
            "aed_medkit": "Вскрытие медицинской аптечки и дефибриллятора АНД",
            "ukeb_scan": "Проверка билета и документов по терминалу УКЭБ",
            "tea_service": "Сервис: предложить чай в подстаканнике или воду с лимоном",
            "driver_intercom": "Связь с машинистом по переговорному устройству УПС"
        }
        action_name = action_descriptions.get(conductor_action, "")

        choices_summary = []
        for i, c in enumerate(challenge.choices_data):
            corr = "ЭТАЛОННОЕ РЕШЕНИЕ" if c.get('is_correct') else "НАРУШЕНИЕ РЕГЛАМЕНТА"
            choices_summary.append(f"- Вариант {i+1} [{corr}]: {c.get('text')} (Пояснение: {c.get('hint', '')})")
        choices_text = "\n".join(choices_summary)

        char_name = challenge.character_name or "Пассажир"
        char_role = challenge.character_role or "Пассажир поезда ВСМ"

        char_ctx = f"{(challenge.title or '')} {(challenge.situation_text or '')} {char_name} {char_role}".lower()
        is_drunk = any(k in char_ctx for k in ['пьян', 'алког', 'дебош', 'буян', 'бутылк', 'пив', 'водк', 'нетрезв'])
        is_med = any(k in char_ctx for k in ['сердц', 'инфаркт', 'плохо', 'дыш', 'задых', 'обморок', 'пульс', 'астм', 'квинке', 'врач'])
        is_tech = any(k in char_ctx for k in ['машинист', 'скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'двер', 'график', 'пожар', 'дым'])
        is_conflict = any(k in char_ctx for k in ['скандал', 'кричит', 'раздраж', 'хам', 'жалоб', 'руга', 'претенз', 'возмущ'])

        char_archetype_rules = ""
        if is_drunk:
            char_archetype_rules = f"""
ОСОБЫЕ ПРАВИЛА ДЛЯ {char_name.upper()} (НЕТРЕЗВЫЙ / ДЕБОШИР):
- Персонаж говорит просторечно, дерзит, возмущается или ворчит.
- НИКОГДА НЕ ГОВОРИ: "Благодарю за профессионализм", "понимаю регламент", "вы правы проводник".
- Если проводник поступает правильно (успокаивает, зовет полицию, делает замечание по протоколу) — персонаж либо неохотно утихает ("Ладно, чё ты сразу... убираю бутылку"), либо пытается оправдаться ("Да я тихо сидел, никого не трогал!").
- Если проводник грубит или ошибается — персонаж скандалит ("Ты на кого голос повысил?! Я щас полицию вызову!").
"""
        elif is_conflict:
            char_archetype_rules = f"""
ОСОБЫЕ ПРАВИЛА ДЛЯ {char_name.upper()} (КОНФЛИКТНЫЙ ПАССАЖИР):
- Персонаж раздражен, требует объяснений, жалуется.
- НИКОГДА НЕ ГОВОРИ казенными шаблонными фразами ("благодарю за профессиональный подход").
- Если проводник прав — персонаж сдержанно смягчается ("Ладно, раз вы объяснили по правилам, хорошо, но следите за этим").
- Если ошибся — усиливает напор ("Вы вообще регламент читали?! Я требую книгу жалоб!").
"""
        elif is_med:
            char_archetype_rules = f"""
ОСОБЫЕ ПРАВИЛА ДЛЯ {char_name.upper()} (ПЛОХОЕ САМОЧУВСТВИЕ):
- Персонаж говорит слабо, сбивчиво, жалуется на самочувствие.
- НИКОГДА не рассуждает о служебных стандартах перевозчика.
"""

        session_class = getattr(session, 'service_class', 'all')
        challenge_class = getattr(challenge, 'service_class', 'all')
        conductor_track = getattr(conductor, 'training_track', 'economy') if conductor else 'economy'
        
        svc_class = challenge_class if challenge_class != 'all' else (session_class if session_class != 'all' else conductor_track)
        if svc_class not in ['economy', 'comfort', 'business']:
            svc_class = 'economy'

        class_descriptions = {
            'economy': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: ЭКОНОМ-КЛАСС (СТО ВСМ 03.011-2026)\n"
                "- Специфика вагона: плотная рассадка 3+2, контроль ручной клади (до 36 кг, до 180 см), порядок в проходах.\n"
                "- Характер пассажиров: люди спешат, чувствительны к порядку, доступности розеток и чистоте. Разговаривают прямо, эмоционально.\n"
                "- Требования к проводнику: быстрый темп работы, четкость указаний, вежливый, но твердый контроль правил безопасности без лишних пауз."
            ),
            'comfort': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: КОМФОРТ-КЛАСС (СТО ВСМ 03.011-2026)\n"
                "- Специфика вагона: рассадка 2+2, климат-контроль (22–24°C), тихая зона, дорожные наборы, сервис бистро.\n"
                "- Характер пассажиров: командированные специалисты, туристы, семьи. Ценят комфорт, тишину, стабильный Wi-Fi.\n"
                "- Требования к проводнику: предупредительность, забота, поддержание тишины, решение любых накладок до эскалации."
            ),
            'business': (
                "СТАНДАРТ КЛАССА ОБСЛУЖИВАНИЯ: БИЗНЕС И ПЕРВЫЙ КЛАСС (СТО ВСМ 03.011-2026 / VIP-сервис 400 км/ч)\n"
                "- Специфика вагона: кресла 2+1, гардеробная служба, горячее ресторанное питание, фарфоровая посуда, приветственный напиток.\n"
                "- Характер пассажиров: VIP-пассажиры, топ-менеджеры, публичные персоны. Ожидают безукоризненной вежливости, уважения личного пространства, обращения по Имени-Отчеству.\n"
                "- Требования к проводнику (стюарду): высший класс этикета, безупречная выправка, дипломатичность, мгновенное премиальное содействие без споров."
            ),
        }
        class_instructions = class_descriptions.get(svc_class, class_descriptions['economy'])

        system_prompt = f"""Ты — интеллектуальный игровой движок скоростной карусели решений ВСМ-1 «Белый кречет» (скорость движения 250–400 км/ч).

ВАЖНЕЙШЕЕ ПРАВИЛО РОЛЕВОЙ ИГРЫ:
1. ПОЛЬЗОВАТЕЛЬ (USER) — ЭТО ПРОВОДНИК ВАГОНА. Все его фразы и действия исходят от проводника.
2. ТЫ (ASSISTANT) В ПОЛЕ "character_reply" — ЭТО ИСКЛЮЧИТЕЛЬНО {char_name} ({char_role}).
   КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО говорить от лица проводника! Персонаж НИКОГДА не говорит "Я дежурный проводник", "Я помогу вам", "Слушаю вас, проводник, какие указания".
   Персонаж — это собеседник проводника, а не сам проводник!
   Судейская экспертная оценка проводника пишется ТОЛЬКО в поле "feedback", а не в "character_reply"!
    В "character_reply" ТОЛЬКО прямая речь {char_name} для голосовой озвучки (Neural TTS). Без префиксов вроде 'Пассажир:', без ремарок в скобках, без кавычек.
{char_archetype_rules}

ОПЕРАТИВНАЯ ОБСТАНОВКА:
- Кейс: {challenge.title}
- Программа подготовки / Класс: {svc_class.upper()}
- Локация / Вагон: {challenge.car_info}
- Ситуация: {challenge.situation_text}
- Персонаж: {char_name} ({char_role}), исходное состояние: {challenge.character_mood or 'В диалоге'}
- Нормативный регламент: {challenge.regulation_reference}
- Текущая скорость состава: {session.current_speed} км/ч

{class_instructions}

ЭТАЛОННЫЕ КРИТЕРИИ И ВАРИАНТЫ:
{choices_text}

ПРАВИЛА ИГРОВОГО ДИАЛОГА:
1. СКОРОСТЬ И ТЕМП РАЗРЕШЕНИЯ СИТУАЦИИ (КРИТИЧЕСКИ ВАЖНО):
   - НЕ ЗАТЯГИВАЙ ДИАЛОГ! Ситуация в скоростной карусели должна разрешаться МАКСИМАЛЬНО БЫСТРО: за 1–2 реплики/действия проводника.
   - НЕ ТРЕБУЙ от проводника дословного цитирования приказов, регламентов или заучивания всех формальностей!
   - Если проводник предложил логичное, вежливое, разумное решение по смыслу или применил подходящее оборудование/инвентарь — СРАЗУ завершай задачу успехом: вызывай функцию complete_shift(verdict='success', ...) либо возвращай "status": "resolved", "is_correct": true!
   - Пассажир не должен спорить бесконечно, если действие проводника адекватно.
2. Проводник взаимодействует голосом, свободным текстом или физическим инвентарем вагона.
3. РЕАКЦИЯ НА ПРИМЕНЕНИЕ ОБОРУДОВАНИЯ ВАГОНА (ДАЖЕ БЕЗ СЛОВ ПРОВОДНИКА):
   - Если проводник применил оборудование или инвентарь (стоп-кран, огнетушитель, аптечку, чайный сервис, электрощит, вызов машиниста по УПС, терминал УКЭБ, аварийный молоток) — ДАЖЕ ЕСЛИ ОН НЕ СКАЗАЛ НИ СЛОВА, персонаж и поездная система ОБЯЗАНЫ немедленно отреагировать именно на это конкретное физическое действие!
   - В поле "system_notice" обязательно укажи конкретный технический отклик оборудования состава ВСМ-1.
4. Проанализируй реплику и действие проводника в контексте ситуации.
5. ОПРЕДЕЛИ СТАТУС РЕШЕНИЯ ("status"):
   - "resolved": Ситуация УСПЕШНО разрешена по смыслу стандартов ВСМ.
   - "failed": ПРОВАЛ/ГРУБАЯ ОШИБКА. Проводник совершил грубое нарушение безопасности (необоснованный стоп-кран, хамство, срыв графика).
   - "in_progress": ДИАЛОГ ПРОДОЛЖАЕТСЯ ТОЛЬКО если проводник пока задал лишь короткий вводный вопрос или решение очевидно неполное. На следующем шаге при адекватном ответе — завершай!
5. Если статус "in_progress" — обязательно сгенерируй 3-4 актуальных варианта действий/реплик для проводника ("suggested_actions"), чтобы проводник мог быстро выбрать следующий шаг или сказать свой ответ.
6. "character_reply" — СТРОГО И ИСКЛЮЧИТЕЛЬНО прямая живая речь участника ситуации ({char_name}, {char_role}) для Neural TTS.
   КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
   - Персонаж НИКОГДА не говорит от лица проводника, бортового компьютера, поезда, ревизора или инструкции!
   - Персонаж НЕ цитирует статьи ПТЭ, регламенты перевозчика и не докладывает о давлении в тормозной магистрали!
   - Персонаж реагирует только как обычный человек со своими эмоциями (страх, удивление, раздражение, облегчение, боль, благодарность).
   - БЕЗ ремарок в скобках, БЕЗ звездочек, БЕЗ слов 'Пассажир отвечает:'.
7. "system_notice" — отдельное поле для системных показаний поезда и телеметрии ВСМ-1 (например: «Бортовой комплекс ВСМ-1: Скорость 350 км/ч. Норма.»). Пустая строка, если технических событий нет.
8. "character_mood" — текущая эмоция персонажа ("calm", "irritated", "grateful", "anxious", "panicked", "formal", "critical").
9. "feedback" — обучающий комментарий проводнику со ссылкой на стандарт ВСМ.

ВЕРНИ JSON СТРОГО СЛЕДУЮЩЕГО ФОРМАТА:
{{
  "status": "resolved" | "in_progress" | "failed",
  "is_correct": true,
  "character_reply": "Живая речь персонажа для голосовой озвучки.",
  "system_notice": "Телеметрия поезда или системное оповещение.",
  "character_mood": "calm",
  "why_wrong": "",
  "feedback": "Обучающий профессиональный комментарий проводнику со ссылкой на стандарт ВСМ.",
  "suggested_actions": [
    {{"text": "Вариант действия проводника 1", "hint": "Пояснение"}},
    {{"text": "Вариант действия проводника 2", "hint": "Пояснение"}},
    {{"text": "Вариант действия проводника 3", "hint": "Пояснение"}}
  ],
  "loyalty_delta": 10,
  "safety_delta": 5,
  "service_delta": 10,
  "stress_delta": -5
}}"""

        user_content_parts = []
        if conductor_message and conductor_message.strip():
            user_content_parts.append(f"Слова проводника: «{conductor_message.strip()}»")
        if action_name:
            user_content_parts.append(f"Действие с оборудованием: [{action_name}]")
        if not user_content_parts:
            user_content_parts.append("Проводник бездействует и ожидает указаний.")

        current_user_turn = "\n".join(user_content_parts)
        messages = [{"role": "system", "content": system_prompt}]

        if dialogue_history:
            for turn in dialogue_history[-6:]:
                role = "user" if turn.get("role") in ["user", "conductor"] else "assistant"
                content = turn.get("content") or turn.get("text", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": current_user_turn})

        current_spd = max(0, getattr(session, 'current_speed', getattr(challenge, 'train_speed', 250)) or 250)
        endless_functions = [
            {
                "name": "complete_shift",
                "description": (
                    "Принять окончательное решение по ситуации в скоростной карусели ВСМ. Задачи должны решаться БЫСТРО (1-2 действия)! Вызывай эту функцию в любой момент, когда проводник: "
                    "1) УСПЕШНО и логично разрешил задачу (вежливый ответ, помощь, проверка билета/паспорта, инвентарь) — verdict='success'. Не требуй дословных цитат регламентов! "
                    "2) ДОПУСТИЛ ГРУБУЮ ОШИБКУ, нарушение безопасности или регламентов ВСМ (verdict='failed'). "
                    "Если ситуация только началась и требует короткого ответа персонажа — функцию не вызывай, отвечай репликой со status='in_progress'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "verdict": {
                            "type": "string",
                            "enum": ["success", "failed"],
                            "description": "'success' если задача решена верно; 'failed' если допущено нарушение."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Экспертное обоснование решения со ссылкой на регламенты ВСМ."
                        },
                        "character_final_words": {
                            "type": "string",
                            "description": f"Финальная реплика участника («{char_name}»)."
                        },
                        "character_mood": {
                            "type": "string",
                            "enum": ["grateful", "calm", "irritated", "panicked", "critical", "formal"]
                        }
                    },
                    "required": ["verdict", "reason", "character_final_words"]
                }
            },
            {
                "name": "offer_hints",
                "description": (
                    "Предоставить проводнику тактическую подсказку и готовые варианты действий по стандарту ВСМ. "
                    "Вызывай эту функцию, если проводник затрудняется с ответом, ошибся или прямо просит подсказать."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Тактическое наставление / подсказка от эксперта ВСМ."
                        },
                        "character_reply": {
                            "type": "string",
                            "description": f"Реплика персонажа («{char_name}»)."
                        },
                        "character_mood": {
                            "type": "string",
                            "enum": ["grateful", "calm", "irritated", "panicked", "critical", "formal"]
                        },
                        "suggested_actions": {
                            "type": "array",
                            "description": "2-3 рекомендуемых варианта действий или протокольных фраз для проводника.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "hint": {"type": "string"}
                                },
                                "required": ["text"]
                            }
                        }
                    },
                    "required": ["reason", "character_reply"]
                }
            }
        ]

        try:
            raw_response = cls._call_gigachat(
                messages,
                temperature=0.3,
                conductor=conductor,
                functions=endless_functions,
                function_call="auto"
            )
            func_call = raw_response.get("function_call") if isinstance(raw_response, dict) else None
            if func_call and func_call.get("name") in ["complete_shift", "resolve_situation"]:
                args = func_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                verdict = (args.get("verdict") or "success").lower()
                is_correct = (verdict in ["success", "completed", "passed"])
                return {
                    "status": "resolved" if is_correct else "failed",
                    "function_triggered": True,
                    "is_terminal": False,
                    "is_correct": is_correct,
                    "character_reply": cls._sanitize_character_reply(
                        args.get("character_final_words") or ("Действуйте согласно регламенту." if is_correct else "Разговор окончен!"),
                        char_name=char_name,
                        char_role=char_role,
                        is_drunk=is_drunk,
                        is_med=is_med,
                        is_tech=is_tech,
                        is_conflict=is_conflict
                    ),
                    "system_notice": f"Бортовой комплекс ВСМ-1: Скорость состава {current_spd} км/ч.",
                    "character_mood": args.get("character_mood", "grateful" if is_correct else "critical"),
                    "why_wrong": "" if is_correct else (args.get("reason") or "Нарушение регламента ВСМ."),
                    "feedback": args.get("reason") or ("Решение принято строго по регламенту ВСМ." if is_correct else "Допущено нарушение регламента ВСМ."),
                    "suggested_actions": [],
                    "loyalty_delta": 15 if is_correct else -15,
                    "safety_delta": 10 if is_correct else -15,
                    "service_delta": 15 if is_correct else -15,
                    "stress_delta": -10 if is_correct else 15
                }
            elif func_call and func_call.get("name") == "offer_hints":
                args = func_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                hint_reason = args.get("reason") or "Экспертная подсказка по регламенту ВСМ."
                suggested = args.get("suggested_actions") or []
                if not suggested and challenge.choices_data:
                    suggested = [{"text": c.get("text", ""), "hint": c.get("hint", "")} for c in challenge.choices_data[:3]]
                return {
                    "status": "in_progress",
                    "function_triggered": True,
                    "is_terminal": False,
                    "is_correct": None,
                    "character_reply": cls._sanitize_character_reply(
                        args.get("character_reply") or ("Я жду вашего ответа, проводник." if not is_drunk else "Ну чё замолк?"),
                        char_name=char_name,
                        char_role=char_role,
                        is_drunk=is_drunk,
                        is_med=is_med,
                        is_tech=is_tech,
                        is_conflict=is_conflict
                    ),
                    "system_notice": f"Бортовой комплекс ВСМ-1: Подсказка проводнику. Скорость {current_spd} км/ч.",
                    "character_mood": args.get("character_mood", "formal"),
                    "why_wrong": "",
                    "feedback": hint_reason,
                    "show_hints": True,
                    "hint_reason": hint_reason,
                    "suggested_actions": suggested,
                    "loyalty_delta": -5,
                    "safety_delta": 0,
                    "service_delta": -5,
                    "stress_delta": 5
                }
            else:
                content_text = raw_response.get("content", "") if isinstance(raw_response, dict) else str(raw_response)
                parsed = cls._extract_json(content_text, default_speed=current_spd)
                if "character_reply" in parsed:
                    if "status" not in parsed:
                        parsed["status"] = "resolved" if parsed.get("is_correct", False) else "failed"
                    parsed["character_reply"] = cls._sanitize_character_reply(
                        parsed.get("character_reply", ""),
                        char_name=char_name,
                        char_role=char_role,
                        is_drunk=is_drunk,
                        is_med=is_med,
                        is_tech=is_tech,
                        is_conflict=is_conflict,
                    )
                    return parsed
        except Exception:
            pass

        # Надежный локальный семантический анализ при отсутствии доступа к шлюзу
        return cls._fallback_endless_eval(challenge, conductor_message, conductor_action)

    @classmethod
    def _fallback_endless_eval(cls, challenge, message: str, action: str) -> dict:
        """Интеллектуальный локальный анализ действий проводника по ключевым шаблонам и инвентарю"""
        m_lower = (message or "").lower()
        search_ctx = f"{(challenge.title or '').lower()} {(challenge.situation_text or '').lower()} {m_lower} {action}"
        char_name = challenge.character_name or "Пассажир"
        char_role = challenge.character_role or "Пассажир поезда ВСМ"

        char_ctx = f"{(challenge.title or '')} {(challenge.situation_text or '')} {char_name} {char_role}".lower()
        is_drunk = any(k in char_ctx for k in ['пьян', 'алког', 'дебош', 'буян', 'бутылк', 'пив', 'водк', 'нетрезв'])
        is_med = any(k in char_ctx for k in ['сердц', 'инфаркт', 'плохо', 'дыш', 'задых', 'обморок', 'пульс', 'астм', 'квинке', 'врач'])
        is_tech = any(k in char_ctx for k in ['машинист', 'скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'двер', 'график', 'пожар', 'дым'])
        is_conflict = any(k in char_ctx for k in ['скандал', 'кричит', 'раздраж', 'хам', 'жалоб', 'руга', 'претенз', 'возмущ'])

        correct_choice = next((c for c in challenge.choices_data if c.get('is_correct')), None)

        def make_suggested():
            res = []
            for ch in challenge.choices_data[:3]:
                res.append({"text": ch.get("text", ""), "hint": ch.get("hint", "")})
            if not res:
                res = [
                    {"text": "Вежливо разъяснить правила перевозки ВСМ", "hint": "СТО ВСМ 03.011"},
                    {"text": "Запросить содействие начальника поезда", "hint": "Доклад по УПС"},
                    {"text": "Предложить воду и помочь разместиться", "hint": "Стандарт сервиса"}
                ]
            return res

        def wrap_action_reply(res_dict):
            if "character_reply" in res_dict:
                res_dict["character_reply"] = cls._sanitize_character_reply(
                    res_dict["character_reply"],
                    char_name=char_name,
                    char_role=char_role,
                    is_drunk=is_drunk,
                    is_med=is_med,
                    is_tech=is_tech,
                    is_conflict=is_conflict,
                )
            return res_dict

        if action:
            if action == 'emergency_brake':
                is_valid = any(k in search_ctx for k in ['сход', 'крушение', 'человек на путях', 'волочится'])
                return wrap_action_reply({
                    "status": "resolved" if is_valid else "failed",
                    "is_correct": is_valid,
                    "character_reply": "Держитесь! Поезд резко замедляется!" if is_valid else "О боже! Зачем вы сорвали стоп-кран?! Меня чуть с кресла не выбросило!",
                    "system_notice": "Бортовой комплекс ВСМ-1: Срыв рукоятки стоп-крана! Экстренное пневматическое торможение. Падение давления в ТМ до 0 атм.",
                    "character_mood": "critical" if is_valid else "panicked",
                    "why_wrong": "" if is_valid else "Срыв стоп-крана без явной угрозы схода или жизни строго запрещен п. 3.4 ПТЭ и регламентом ВСМ.",
                    "feedback": "Экстренное торможение применено обоснованно для предотвращения крушения." if is_valid else "Необоснованный срыв стоп-крана на скорости 360 км/ч влечет угрозу схода с рельсов и травмирования сотен пассажиров.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 0 if is_valid else -25,
                    "safety_delta": 20 if is_valid else -30,
                    "service_delta": 0 if is_valid else -20,
                    "stress_delta": 20 if is_valid else 35
                })
            elif action == 'aed_medkit':
                is_med_action = any(k in search_ctx for k in ['сердц', 'инфаркт', 'плохо', 'дыш', 'задых', 'обморок', 'пульс', 'врач', 'астм', 'квинке'])
                return wrap_action_reply({
                    "status": "resolved" if is_med_action else "in_progress",
                    "is_correct": is_med_action,
                    "character_reply": "Спасибо! Мне уже легче, прикладываю аптечку..." if is_med_action else "Мне медицинская помощь не требуется, зачем вы это принесли?",
                    "system_notice": "Аптечка первой помощи СПАС-ВО и дефибриллятор АНД извлечены из настенного шкафа вагона.",
                    "character_mood": "grateful" if is_med_action else "irritated",
                    "why_wrong": "" if is_med_action else "Медицинская аптечка и дефибриллятор применены без показаний.",
                    "feedback": "Своевременная доврачебная помощь оказана по протоколу ВСМ." if is_med_action else "Используйте профильные средства для данной ситуации.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 15 if is_med_action else -10,
                    "safety_delta": 25 if is_med_action else -5,
                    "service_delta": 15 if is_med_action else -10,
                    "stress_delta": -15 if is_med_action else 10
                })
            elif action == 'fire_extinguisher':
                is_fire = any(k in search_ctx for k in ['пожар', 'дым', 'огонь', 'запах гари', 'тлеет', 'искры'])
                return wrap_action_reply({
                    "status": "resolved" if is_fire else "failed",
                    "is_correct": is_fire,
                    "character_reply": "Огонь залит пеной, дым рассеивается! Спасибо проводник!" if is_fire else "Зачем вы распыляете пену, здесь же нет никакого огня?!",
                    "system_notice": "Огнетушитель ОВП-8 активирован. В вагоне включена система аварийной вытяжной вентиляции.",
                    "character_mood": "calm" if is_fire else "irritated",
                    "why_wrong": "" if is_fire else "Применение огнетушителя без признаков горения запрещено регламентом.",
                    "feedback": "Огнетушитель ОВП-8 применен строго по инструкции противопожарной безопасности." if is_fire else "Необоснованное применение огнетушителя загрязняет салон и пугает пассажиров.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 10 if is_fire else -15,
                    "safety_delta": 30 if is_fire else -10,
                    "service_delta": 10 if is_fire else -20,
                    "stress_delta": -10 if is_fire else 20
                })
            elif action == 'tea_service':
                is_tea_good = any(k in search_ctx for k in ['скандал', 'кричит', 'раздраж', 'чай', 'кофе', 'вода', 'напит', 'жажд', 'успоко'])
                return wrap_action_reply({
                    "status": "in_progress",
                    "is_correct": True,
                    "character_reply": "Спасибо за чай... Но ответьте на мой вопрос по существу!" if is_conflict else "Благодарю вас, горячий чай сейчас кстати.",
                    "system_notice": "Сервис ВСМ: Пассажиру подан фирменный чай в подстаканнике «Белый кречет».",
                    "character_mood": "calm" if not is_conflict else "irritated",
                    "why_wrong": "",
                    "feedback": "Чайный сервис помог снизить накал страстей по 4-шаговой сервисной модели. Продолжите диалог.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 15 if is_tea_good else 5,
                    "safety_delta": 0,
                    "service_delta": 15 if is_tea_good else 5,
                    "stress_delta": -10 if is_tea_good else 0
                })
            elif action == 'driver_intercom':
                is_tech_action = any(k in search_ctx for k in ['машинист', 'скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'двер', 'график', 'остановк', 'полици'])
                return wrap_action_reply({
                    "status": "resolved" if is_tech_action else "in_progress",
                    "is_correct": is_tech_action,
                    "character_reply": "Машинист на связи! Доклад принял, контролирую параметры по бортовому компьютеру." if is_tech_action else "Кабина на связи. Не засоряйте служебный эфир вопросами, решаемыми в вагоне.",
                    "system_notice": "Интерком УПС: Канал двусторонней радиосвязи с головной кабиной поезда ВСМ-1 активен.",
                    "character_mood": "formal",
                    "why_wrong": "" if is_tech_action else "Вызов машиниста состава допустим только по регламентным поводам.",
                    "feedback": "Своевременный доклад машинисту по УПС согласно Инструкции проводника ВСМ." if is_tech_action else "Решайте локальные сервисные вопросы на уровне салона вагона.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 10 if is_tech_action else -5,
                    "safety_delta": 20 if is_tech_action else 0,
                    "service_delta": 10 if is_tech_action else -5,
                    "stress_delta": -10 if is_tech_action else 5
                })
            elif action == 'ukeb_scan':
                is_ticket = any(k in search_ctx for k in ['билет', 'паспорт', 'документ', 'опечатка', 'место', 'льгот', 'посадк', 'укэб', 'электронн'])
                return wrap_action_reply({
                    "status": "resolved" if is_ticket else "in_progress",
                    "is_correct": is_ticket,
                    "character_reply": "Вот мой паспорт и посадочный талон. Проверьте, пожалуйста." if is_ticket else "Зачем вы сканируете мой билет сейчас, когда возникла другая проблема?",
                    "system_notice": "Терминал УКЭБ: Считывание QR-кода билета завершено. Статус пассажира в АСУ Экспресс подтвержден.",
                    "character_mood": "calm" if is_ticket else "formal",
                    "why_wrong": "" if is_ticket else "Терминал УКЭБ используется для билетного контроля и оформления актов.",
                    "feedback": "Проверка данных по терминалу УКЭБ выполнена по регламенту ВСМ." if is_ticket else "Действие зафиксировано.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 15 if is_ticket else 0,
                    "safety_delta": 10 if is_ticket else 0,
                    "service_delta": 15 if is_ticket else 0,
                    "stress_delta": -5 if is_ticket else 0
                })
            elif action == 'electric_panel':
                is_elec = any(k in search_ctx for k in ['скнб', 'нагрев', 'букс', 'щит', 'напряжен', 'климат', 'кондиционер', 'свет', 'розетк', 'электр', 'замыкан', 'датчик', 'вентиляц'])
                return wrap_action_reply({
                    "status": "resolved" if is_elec else "in_progress",
                    "is_correct": is_elec,
                    "character_reply": "Спасибо! Климат-контроль и освещение вагона теперь работают в штатном режиме." if is_elec else "Проводник проверяет электрощит... Но что с моим вопросом?",
                    "system_notice": "Бортовой шкаф ВСМ-1: Параметры электрощита и датчиков СКНБ проверены. Сигнализация в норме.",
                    "character_mood": "calm" if is_elec else "formal",
                    "why_wrong": "" if is_elec else "Осмотр электрощита не решает текущий вопрос пассажира.",
                    "feedback": "Осмотр электрощита и проверка сигнализации СКНБ проведены по инструкции ВСМ." if is_elec else "Используйте оборудование по прямому назначению.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 10 if is_elec else 0,
                    "safety_delta": 20 if is_elec else 0,
                    "service_delta": 10 if is_elec else 0,
                    "stress_delta": -10 if is_elec else 0
                })
            elif action == 'glass_hammer':
                is_hammer = any(k in search_ctx for k in ['эвакуац', 'заблокирован', 'выход', 'стекло', 'молоток', 'крушение', 'аварийн'])
                return wrap_action_reply({
                    "status": "resolved" if is_hammer else "failed",
                    "is_correct": is_hammer,
                    "character_reply": "Эвакуационный выход вскрыт аварийным молотком! Покидаем салон!" if is_hammer else "Зачем вы схватили аварийный молоток?! Здесь же нет аварии, вы людей пугаете!",
                    "system_notice": "Аварийно-спасательный инвентарь: Аварийный молоток извлечен из защитного гнезда.",
                    "character_mood": "critical" if is_hammer else "panicked",
                    "why_wrong": "" if is_hammer else "Использование аварийного молотка без необходимости эвакуации запрещено.",
                    "feedback": "Аварийный молоток применен для вскрытия эвакуационного выхода по инструкции." if is_hammer else "Необоснованное извлечение аварийного молотка сеет панику среди пассажиров.",
                    "suggested_actions": make_suggested(),
                    "loyalty_delta": 0 if is_hammer else -20,
                    "safety_delta": 15 if is_hammer else -15,
                    "service_delta": 0 if is_hammer else -20,
                    "stress_delta": 10 if is_hammer else 25
                })

        polite = any(k in m_lower for k in ['здравствуйте', 'добрый', 'пожалуйста', 'прошу прощения', 'извините', 'помогу', 'решим', 'согласно правилам'])
        has_correct_keywords = False
        if correct_choice:
            cw_words = [w for w in re.findall(r'\b[а-яёa-z]{4,}\b', correct_choice.get('text', '').lower())]
            match_count = sum(1 for w in cw_words if w in m_lower)
            has_correct_keywords = match_count >= 1

        is_correct = (polite and has_correct_keywords) or has_correct_keywords or (polite and len(m_lower) > 15)
        hint = correct_choice.get('hint', '') if correct_choice else ''

        # Если проводник просто поздоровался без решения — статус in_progress
        is_greeting = any(k in m_lower for k in ['здравствуйте', 'добрый день', 'добрый вечер', 'доброе утро']) and len(m_lower.split()) <= 4
        status = "in_progress" if is_greeting else ("resolved" if is_correct else "failed")

        if is_greeting:
            if is_drunk:
                reply = "Чё надо, начальник? Я просто еду, никого не трогаю..."
            elif is_med:
                reply = "Здравствуйте... Помогите, мне очень плохо..."
            elif is_conflict:
                reply = "Здравствуйте! Наконец-то вы подошли! Разберитесь немедленно!"
            elif is_tech:
                reply = "Дежурный на связи. Что у вас в вагоне произошло?"
            else:
                reply = "Здравствуйте! Подскажите, пожалуйста..."
        elif is_drunk:
            if is_correct:
                reply = "Ладно, ладно, командир... Убираю бутылку. Не надо начальника поезда звать, я тихо посижу."
            else:
                reply = "Ты чё мне указываешь?! Я билет купил и еду как хочу! Руки убрал от меня!"
        elif is_med:
            if is_correct:
                reply = "Ох... спасибо большое... Дышать легче стало. Пожалуйста, побудьте рядом..."
            else:
                reply = "Мне совсем тяжело... В глазах темнеет... Вызовите врача, пожалуйста!"
        elif is_conflict:
            if is_correct:
                reply = "Хорошо, раз вы объяснили всё по правилам и спокойно, вопрос исчерпан. Спасибо."
            else:
                reply = "Что вы мне тут рассказываете?! Это форменное безобразие, я буду писать жалобу!"
        elif is_tech:
            if is_correct:
                reply = "Доклад принят. Контролируем ситуацию по приборам, продолжайте движение по регламенту."
            else:
                reply = "Внимание! Ваши действия нарушают технический регламент скоростного поезда!"
        else:
            if is_correct:
                reply = "Спасибо вам за помощь и разъяснение, теперь всё в порядке."
            else:
                reply = "Я категорически не согласен! Разве так должны обслуживать пассажиров ВСМ?!"

        reply = cls._sanitize_character_reply(
            reply,
            char_name=char_name,
            char_role=char_role,
            is_drunk=is_drunk,
            is_med=is_med,
            is_tech=is_tech,
            is_conflict=is_conflict,
        )

        mood = "grateful" if is_correct else "irritated"
        if is_drunk:
            mood = "calm" if is_correct else "critical"
        elif is_med:
            mood = "calm" if is_correct else "critical"
        elif is_conflict:
            mood = "calm" if is_correct else "irritated"

        spd = max(0, getattr(challenge, 'train_speed', 250) or 250)
        notice_text = f"Бортовой комплекс ВСМ-1: Поезд следует по графику со скоростью {spd} км/ч." if spd > 0 else "Бортовой комплекс ВСМ-1: Стоянка на станции (посадка/высадка пассажиров)."

        return {
            "status": status,
            "is_correct": is_correct,
            "character_reply": reply,
            "system_notice": notice_text,
            "character_mood": mood,
            "why_wrong": "" if is_correct else "Действия или формулировки проводника не соответствуют стандарту сервиса ВСМ.",
            "feedback": f"Решение принято в соответствии с регламентом: {hint}" if is_correct else f"Следовало поступить по регламенту: {hint}",
            "suggested_actions": make_suggested(),
            "loyalty_delta": 15 if is_correct else -15,
            "safety_delta": 10 if is_correct else -10,
            "service_delta": 15 if is_correct else -10,
            "stress_delta": -10 if is_correct else 15
        }

    @classmethod
    def get_sber_id_auth_url(cls, redirect_uri: str = None, state: str = "vsm_oauth") -> str:
        """Формирует URL для авторизации через официальный шлюз Единый ID OAuth 2.0 (id.sber.ru)"""
        client_id = getattr(settings, 'SBER_ID_CLIENT_ID', '').strip()
        if not client_id:
            # Если корпоративный Client ID Единый ID не задан в .env, направляем на портал консоль разработчика
            return "https://developers.sber.ru/studio/"

        target_redirect = redirect_uri or getattr(settings, 'SBER_ID_REDIRECT_URI', 'http://127.0.0.1:8000/auth/sber/callback/')
        return (
            f"https://id.sber.ru/CSAFront/oidc/sberbank_id/authorize.do?"
            f"response_type=code&client_id={client_id}&redirect_uri={target_redirect}&scope=openid%20profile&state={state}&nonce={state}"
        )

    @classmethod
    def exchange_sber_id_code(cls, code: str, redirect_uri: str) -> dict:
        """
        Выполняет обмен authorization_code на access_token и id_token через официальный OAuth 2.0 шлюз Единый ID (id.sber.ru).
        """
        client_id = getattr(settings, 'SBER_ID_CLIENT_ID', '').strip()
        client_secret = getattr(settings, 'SBER_ID_CLIENT_SECRET', '').strip()

        token_url = "https://id.sber.ru/CSAFront/oidc/sberbank_id/token.do"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        }
        if client_secret:
            data["client_secret"] = client_secret

        try:
            resp = requests.post(token_url, headers=headers, data=data, verify=False, timeout=15)
            if resp.status_code == 200:
                token_data = resp.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                
                # Запрос профиля пользователя через userinfo
                user_info = {}
                if access_token:
                    userinfo_url = "https://id.sber.ru/CSAFront/oidc/sberbank_id/userinfo.do"
                    try:
                        u_resp = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"}, verify=False, timeout=10)
                        if u_resp.status_code == 200:
                            user_info = u_resp.json()
                    except Exception:
                        pass

                sub = user_info.get("sub") or str(uuid.uuid4())[:12]
                name = user_info.get("name") or user_info.get("family_name", "Сотрудник ВСМ")
                email = user_info.get("email") or f"corp_{sub[:8]}@vsm.trans.ru"

                return {
                    "ok": True,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "sub": sub,
                    "name": name,
                    "email": email
                }
            else:
                return {
                    "ok": False,
                    "status_code": resp.status_code,
                    "error": f"Единый ID вернул ошибку обмена: {resp.text[:300]}"
                }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Сетевой сбой при обращении к Единый ID: {exc}"
            }

