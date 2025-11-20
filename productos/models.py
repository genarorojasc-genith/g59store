from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='productos'
    )
    creado_en = models.DateTimeField(default=timezone.now)
    destacado = models.BooleanField(default=False)
    codigo_proveedor = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,       # importante para update_or_create
    )
    url_proveedor = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)


    def __str__(self) -> str:
        return self.nombre
