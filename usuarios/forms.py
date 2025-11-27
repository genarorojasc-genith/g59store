from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Perfil, PerfilFacturacion



class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    class Meta:
        model = User
        # Si usas el correo como usuario, no necesitas pedir username aparte
        fields = ("email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()

        # validamos SOLO contra auth_user
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"].lower()

        # usamos el email como username
        user.username = email
        user.email = email

        if commit:
            user.save()
        return user


class PerfilForm(forms.ModelForm):
    nombre = forms.CharField(
        label="Nombre completo",
        max_length=150,
        required=False,
    )

    class Meta:
        model = Perfil
        fields = [
            'nombre',
            'rut_usuario',
            'telefono',
            'direccion_usuario',
            'ciudad',
        ]
        labels = {
            'nombre': 'Nombre',
            'rut_usuario': 'RUT',
            'telefono': 'Teléfono',
            'direccion_usuario': 'Dirección',
            'ciudad': 'Ciudad',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Si el perfil NO tiene nombre y hay user, rellenamos desde user.first_name
        if user and not self.instance.pk:
            if not self.instance.nombre:
                self.fields['nombre'].initial = user.first_name

    def save(self, user=None, commit=True):
        perfil = super().save(commit=False)

        if user is not None:
            perfil.user = user

        if commit:
            perfil.save()

        # guardamos el nombre también en User.first_name
        if user is not None:
            user.first_name = self.cleaned_data.get('nombre', '') or ''
            if commit:
                user.save()

        return perfil



class PerfilFacturacionForm(forms.ModelForm):
    class Meta:
        model = PerfilFacturacion
        fields = [
            'rut_facturacion',
            'razon_social',
            'giro',
            'direccion_facturacion',
            'ciudad_facturacion',
        ]
        labels = {
            'rut_facturacion': 'RUT',
            'razon_social': 'Razón social / Nombre',
            'giro': 'Giro',
            'direccion_facturacion': 'Dirección',
            'ciudad_facturacion': 'Ciudad',
        }

    def save(self, user=None, commit=True):
        perfil_fact = super().save(commit=False)

        if user is not None:
            perfil_fact.user = user

        if commit:
            perfil_fact.save()

        return perfil_fact

