from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Author, Post


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Имя пользователя")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Email")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Только буквы, цифры и @/./+/-/_."
        self.fields["password1"].help_text = "Минимум 8 символов."
        self.fields["password2"].help_text = ""


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("title", "text", "tier")
        labels = {
            "title": "Заголовок",
            "text": "Текст",
            "tier": "Доступ",
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 10}),
        }

    def __init__(self, author, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tier"].queryset = author.tiers.order_by("price")
        self.fields["tier"].empty_label = "Бесплатно для всех"
        self.fields["tier"].required = False
        self.fields["tier"].label_from_instance = lambda tier: "{} — {} ₽".format(tier.name, tier.price)


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ("name", "category", "about")
        labels = {
            "name": "Имя",
            "category": "Категория",
            "about": "О себе",
        }
        widgets = {
            "about": forms.Textarea(attrs={"rows": 4}),
        }
