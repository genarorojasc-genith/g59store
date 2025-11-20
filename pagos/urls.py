from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    # Mercado Pago
    path('mercadopago/<int:pedido_id>/', views.pagar_mercadopago, name='pagar_mercadopago'),
    path('mercadopago/exito/', views.mp_exito, name='mp_exito'),
    path('mercadopago/fallo/', views.mp_fallo, name='mp_fallo'),
    path('mercadopago/pendiente/', views.mp_pendiente, name='mp_pendiente'),

    # Transbank (luego lo ordenamos igual)
    path('transbank/<int:pedido_id>/', views.transbank_iniciar, name='transbank_iniciar'),
]
