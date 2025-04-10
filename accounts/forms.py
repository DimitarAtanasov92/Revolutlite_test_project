from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class RegisterForm(UserCreationForm):
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2')

class LoginForm(AuthenticationForm):
    pass


class VerificationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['id_front', 'id_back', 'selfie_video']