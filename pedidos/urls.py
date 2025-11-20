from django.urls import path
from . import views

app_name = 'pedidos'

urlpatterns = [
    # Crear pedido (checkout)
    path('checkout/', views.checkout_iniciar, name='checkout_iniciar'),
    path('crear/', views.pedido_crear, name='pedido_crear'),

    # Ver pedidos del usuario autenticado
    path('mis/', views.mis_pedidos, name='mis_pedidos'),

    # (Opcional) ver detalle de un pedido específico    
    path('<int:pedido_id>/', views.pedido_detalle, name='pedido_detalle'),

     # --- Panel vendedor ---
    path('panel/', views.panel_pedidos, name='panel_pedidos'),
    path('panel/<int:pedido_id>/', views.panel_pedido_detalle, name='panel_pedido_detalle'),
    path('panel/<int:pedido_id>/estado/', views.panel_pedido_cambiar_estado, name='panel_pedido_cambiar_estado'),
]