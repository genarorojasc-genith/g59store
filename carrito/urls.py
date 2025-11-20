from django.urls import path
from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.cart_detail, name='detalle'),
    path('agregar/<int:producto_id>/', views.cart_add, name='agregar'),
    path('eliminar/<int:producto_id>/', views.cart_remove, name='eliminar'),
    path('actualizar/<int:producto_id>/', views.cart_update, name='actualizar'),
    path('vaciar/', views.cart_clear, name='vaciar'),
]
