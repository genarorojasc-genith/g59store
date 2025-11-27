from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator

from .forms import RegistroForm, PerfilForm, PerfilFacturacionForm
from .models import Perfil, PerfilFacturacion

from common.email_utils import send_email
from django.db import IntegrityError

def registrarse(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False
                user.save()
            except IntegrityError:
                # por si algo extraño se cuela igual
                form.add_error('email', 'Ya existe una cuenta con este correo.')
            else:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
                activation_link = f"{protocol}://{domain}/usuarios/activar/{uid}/{token}/"

                send_email(
                    to_email=user.email,
                    subject='Activa tu cuenta en G59 Store',
                    template_name='emails/activar_cuenta.html',
                    context={
                        'user': user,
                        'activation_link': activation_link,
                    },
                )

                messages.success(request, 'Cuenta creada. Revisa tu correo para activarla.')
                return redirect('login')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registrarse.html', {'form': form})



def activar_cuenta(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Tu cuenta fue activada. Ya puedes iniciar sesión.')
        return redirect('login')
    else:
        messages.error(request, 'El enlace de activación no es válido o ya fue usado.')
        return redirect('inicio')



@login_required
def perfil_view(request):
    perfil, created = Perfil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil, user=request.user)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil')  # ajusta al nombre de tu url
    else:
        form = PerfilForm(instance=perfil, user=request.user)

    return render(request, 'usuarios/perfil.html', {'form': form})


@login_required
def perfil_facturacion_view(request):
    perfil_fact, created = PerfilFacturacion.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PerfilFacturacionForm(request.POST, instance=perfil_fact)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'Datos de facturación actualizados.')
            return redirect('perfil_facturacion')  # ajusta al nombre de tu url
    else:
        form = PerfilFacturacionForm(instance=perfil_fact)

    return render(request, 'usuarios/perfil_facturacion.html', {'form': form})