from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Perfil, PerfilFacturacion


class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Correo electrónico"
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'input-borde'}),
        help_text=(
            "<ul class='text-xs text-gray-500 mt-1 list-disc pl-4'>"
            "<li>Debe contener al menos 8 caracteres.</li>"
            "<li>No puede ser muy similar a tu información personal.</li>"
            "<li>No puede ser una contraseña de uso común.</li>"
            "<li>No puede ser completamente numérica.</li>"
            "</ul>"
        )
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'input-borde'}),
        help_text="<p class='text-xs text-gray-500 mt-1'>Repite la misma contraseña para verificarla.</p>"
    )

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        # ✅ aquí SÍ validamos que no exista antes
        if User.objects.filter(username=email).exists() \
           or User.objects.filter(email=email).exists():
            raise ValidationError("Ya existe una cuenta con este correo.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email'].lower()
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
