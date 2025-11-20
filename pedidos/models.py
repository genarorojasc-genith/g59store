from django.db import models
from productos.models import Producto
from django.contrib.auth.models import User


class Cliente(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cliente'
    )
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email
    
class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('carrito', 'Carrito'),
        ('pendiente_pago', 'Pendiente de pago'),
        ('pagado', 'Pagado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('fallido', 'Fallido'),
    ]

    METODO_PAGO_CHOICES = [
        ('transbank', 'Transbank'),
        ('mercadopago', 'MercadoPago'),
    ]

    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos'
    )

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='carrito',
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    pagado = models.BooleanField(default=False)

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        blank=True,
        null=True,
    )

    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADO_PAGO_CHOICES,
        default='pendiente',
    )

    transaccion_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='ID de la transacción en la pasarela de pago',
    )

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f'Pedido {self.id} ({self.estado})'

    def calcular_total(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())

    def actualizar_total(self, save=True):
        self.total = self.calcular_total()
        if save:
            self.save(update_fields=['total'])



class PedidoDetalle(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name='detalles',
        on_delete=models.CASCADE,
    )
    producto = models.ForeignKey(
        Producto,
        related_name='detalles_pedido',
        on_delete=models.PROTECT,
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f'{self.producto.nombre} x {self.cantidad}'


class DatosEnvio(models.Model):
    pedido = models.OneToOneField(
        Pedido,
        related_name='datos_envio',
        on_delete=models.CASCADE,
    )
    nombre_recibe = models.CharField(max_length=150)
    direccion_recibe = models.CharField(max_length=255)
    ciudad_recibe = models.CharField(max_length=100)

    def __str__(self):
        return f'Envío pedido {self.pedido_id}'



# class DatosFactura(models.Model):
#     pedido = models.OneToOneField(
#         Pedido,
#         related_name='datos_factura',
#         on_delete=models.CASCADE,
#     )
#     rut_facturacion = models.CharField(max_length=20)
#     razon_social = models.CharField(max_length=255)
#     giro = models.CharField(max_length=255, blank=True)
#     direccion_facturacion = models.CharField(max_length=255)
#     ciudad_facturacion = models.CharField(max_length=100)

#     def __str__(self):
#         return f'Factura pedido {self.pedido_id}'
    

class DatosFactura(models.Model):
    pedido = models.OneToOneField(
        Pedido,
        related_name='datos_factura',
        on_delete=models.CASCADE,
    )
    # Todos opcionales (solo se obligan cuando requiere_factura=True)
    rut_facturacion = models.CharField(max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=255, blank=True, null=True)
    giro = models.CharField(max_length=255, blank=True, null=True)
    direccion_facturacion = models.CharField(max_length=255, blank=True, null=True)
    ciudad_facturacion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'Factura pedido {self.pedido_id}'


class DocumentoTributario(models.Model):
    ESTADO_CHOICES = [
        ('pendiente_envio', 'Pendiente envío SII'),
        ('enviado', 'Enviado SII'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]

    TIPO_CHOICES = [
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
    ]

    pedido = models.OneToOneField(
        Pedido,
        related_name='documento_tributario',
        on_delete=models.PROTECT,
    )
    tipo_documento = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente_envio',
    )
    folio = models.CharField(max_length=50, blank=True)

    neto = models.DecimalField(max_digits=12, decimal_places=2)
    iva = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.tipo_documento.upper()} #{self.folio or "SIN FOLIO"}'

