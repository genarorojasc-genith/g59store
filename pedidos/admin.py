from django.contrib import admin
from .models import (
    Cliente,
    Pedido,
    PedidoDetalle,
    DatosEnvio,
    DatosFactura,
    DocumentoTributario,
)


class PedidoDetalleInline(admin.TabularInline):
    model = PedidoDetalle
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'estado',
        'estado_pago',
        'pagado',
        'total',
        'creado',
    )
    list_filter = ('estado', 'estado_pago', 'pagado', 'creado')
    search_fields = ('id', 'cliente__email', 'cliente__user__username')
    inlines = [PedidoDetalleInline]


admin.site.register(Cliente)
admin.site.register(DatosEnvio)
admin.site.register(DatosFactura)
admin.site.register(DocumentoTributario)
