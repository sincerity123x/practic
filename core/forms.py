from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


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
