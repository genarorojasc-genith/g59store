from django.db import models
from django.contrib.auth.models import User


class Perfil(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    nombre = models.CharField(max_length=150, blank=True)
    rut_usuario = models.CharField(max_length=20, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion_usuario = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Perfil de {self.user.email or self.user.username}"


class PerfilFacturacion(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil_facturacion'
    )
    rut_facturacion = models.CharField(max_length=20)
    razon_social = models.CharField(max_length=255)
    giro = models.CharField(max_length=255, blank=True)
    direccion_facturacion = models.CharField(max_length=255)
    ciudad_facturacion = models.CharField(max_length=100)

    def __str__(self):
        return f"Facturación de {self.user.email or self.user.username}"
