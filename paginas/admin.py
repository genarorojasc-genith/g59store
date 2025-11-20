from django.contrib import admin
from .models import PaginaInformativa

@admin.register(PaginaInformativa)
class PaginaInformativaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'slug', 'activo')
    list_filter = ('activo',)
    search_fields = ('titulo', 'slug')
