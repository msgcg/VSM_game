import base64
from django import forms
from django.contrib.auth.models import User
from .models import ConductorProfile


DEPOT_CHOICES = [
    ('Москва-Октябрьская ВСМ', 'Депо Москва-Октябрьская (Северо-Западная дирекция ВСМ)'),
    ('Санкт-Петербург Главный ВСМ', 'Депо Санкт-Петербург Главный (Октябрьская ВСМ)'),
    ('Новая Тверь ВСМ', 'Депо Новая Тверь (Опорная станция ВСМ-1)'),
    ('Валдай ВСМ', 'Депо Валдай (Центральный участок ВСМ-1)'),
    ('Великий Новгород ВСМ', 'Депо Великий Новгород (Высокоскоростной сектор)'),
]

AVATAR_CHOICES = [
    ('avatar_1.svg', 'Форменная фуражка ВСМ (мужской образ 1)'),
    ('avatar_2.svg', 'Старший стюард ВСМ (женский образ 1)'),
    ('avatar_3.svg', 'Инструктор поездных бригад (мужской образ 2)'),
    ('avatar_4.svg', 'Стюард бизнес-класса (женский образ 2)'),
    ('avatar_5.svg', 'Стажер высокоскоростной линии (мужской образ 3)'),
]


class ConductorRegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        min_length=3,
        required=True,
        label="Логин проводника",
        widget=forms.TextInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'например, ivan_smirnov',
            'autocomplete': 'username',
        })
    )
    full_name = forms.CharField(
        max_length=150,
        min_length=4,
        required=True,
        label="ФИО сотрудника",
        widget=forms.TextInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'например, Смирнов Иван Алексеевич',
        })
    )
    email = forms.EmailField(
        required=False,
        label="Электронная почта",
        widget=forms.EmailInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'ivan.smirnov@vsm.trans.ru (необязательно)',
            'autocomplete': 'email',
        })
    )
    depot = forms.ChoiceField(
        choices=DEPOT_CHOICES,
        required=True,
        initial='Москва-Октябрьская ВСМ',
        label="Депо приписки",
        widget=forms.Select(attrs={
            'class': 'vsm-form-input vsm-form-select',
        })
    )
    avatar = forms.ChoiceField(
        choices=AVATAR_CHOICES,
        required=True,
        initial='avatar_1.svg',
        label="Служебный аватар",
        widget=forms.RadioSelect(attrs={
            'class': 'vsm-avatar-radio',
        })
    )
    password = forms.CharField(
        min_length=6,
        required=True,
        label="Пароль учетной записи",
        widget=forms.PasswordInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Минимум 6 символов',
            'autocomplete': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        min_length=6,
        required=True,
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Повторите пароль',
            'autocomplete': 'new-password',
        })
    )
    sber_client_id = forms.CharField(
        required=False,
        label="Client ID (Идентификатор клиента)",
        widget=forms.TextInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Например: 01a07215-cf66-7ec2-bf49-e602f1f833a6',
            'autocomplete': 'off',
            'style': 'font-family: monospace; font-size: 0.86rem;',
        }),
        help_text="Client ID из раздела параметров подключения в кабинете ИИ-платформы"
    )
    sber_client_secret = forms.CharField(
        required=False,
        label="Client Secret (Секрет клиента)",
        widget=forms.TextInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Например: fce0a0b0-a1d1-4c0b-9bf2-663a40a30efc',
            'autocomplete': 'off',
            'style': 'font-family: monospace; font-size: 0.86rem;',
        }),
        help_text="Client Secret из раздела параметров подключения в кабинете ИИ-платформы"
    )
    sber_auth_key = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Проводник с таким логином уже зарегистрирован в базе ВСМ.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Пароли не совпадают. Пожалуйста, проверьте ввод.")

        client_id = (cleaned_data.get('sber_client_id') or '').strip()
        client_secret = (cleaned_data.get('sber_client_secret') or '').strip()
        auth_key = (cleaned_data.get('sber_auth_key') or '').strip()

        # Если auth_key передан напрямую (например, через API или тесты)
        if auth_key and not client_id and not client_secret:
            try:
                dec = base64.b64decode(auth_key).decode('utf-8', errors='ignore')
                if ':' in dec:
                    parts = dec.split(':', 1)
                    client_id = parts[0]
                    client_secret = parts[1]
                    cleaned_data['sber_client_id'] = client_id
                    cleaned_data['sber_client_secret'] = client_secret
                else:
                    cleaned_data['sber_client_secret'] = auth_key
            except Exception:
                pass
            cleaned_data['sber_auth_key'] = auth_key

        # Автоматическое распознавание: если пользователь вставил объединенный Base64 в одно из полей
        if client_id and not client_secret:
            try:
                dec = base64.b64decode(client_id).decode('utf-8', errors='ignore')
                if ':' in dec:
                    parts = dec.split(':', 1)
                    client_id = parts[0]
                    client_secret = parts[1]
                    cleaned_data['sber_client_id'] = client_id
                    cleaned_data['sber_client_secret'] = client_secret
            except Exception:
                pass
        elif client_secret and not client_id:
            try:
                dec = base64.b64decode(client_secret).decode('utf-8', errors='ignore')
                if ':' in dec:
                    parts = dec.split(':', 1)
                    client_id = parts[0]
                    client_secret = parts[1]
                    cleaned_data['sber_client_id'] = client_id
                    cleaned_data['sber_client_secret'] = client_secret
            except Exception:
                pass

        if client_id and not client_secret:
            self.add_error('sber_client_secret', "Указан Client ID, но не указан Client Secret.")
        elif client_secret and not client_id:
            if not auth_key:
                self.add_error('sber_client_id', "Указан Client Secret, но не указан Client ID.")
        elif client_id and client_secret:
            auth_key = base64.b64encode(f"{client_id}:{client_secret}".encode('utf-8')).decode('utf-8')
            cleaned_data['sber_auth_key'] = auth_key
        elif not auth_key:
            cleaned_data['sber_auth_key'] = ""

        return cleaned_data


class ConductorLoginForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        required=True,
        label="Логин проводника",
        widget=forms.TextInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Логин или табельный номер',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        required=True,
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'vsm-form-input',
            'placeholder': 'Пароль доступа',
            'autocomplete': 'current-password',
        })
    )
