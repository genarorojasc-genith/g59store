from django.urls import path
from . import views

urlpatterns = [
    path('registrarse/', views.registrarse, name='registrarse'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/facturacion/', views.perfil_facturacion_view, name='perfil_facturacion'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta, name='activar_cuenta'),
]
