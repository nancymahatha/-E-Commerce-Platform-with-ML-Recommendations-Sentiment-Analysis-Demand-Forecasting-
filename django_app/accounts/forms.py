from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ROLE_CHOICES


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    # for the viva demo you may register as staff to try the demand dashboard
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="customer")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "role"]
