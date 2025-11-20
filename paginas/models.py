from django.db import models

class PaginaInformativa(models.Model):
    slug = models.SlugField(unique=True)  # ej: 'envios', 'cambios', 'contacto'
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Página informativa'
        verbose_name_plural = 'Páginas informativas'

    def __str__(self):
        return self.titulo
