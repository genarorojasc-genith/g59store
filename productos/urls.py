from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.index, name='index'),                 # /  → listado
    path('<int:producto_id>/', views.detalle, name='detalle'), # /1, /2, etc.

        # Panel de productos (solo staff)
    path('panel/', views.panel_productos, name='panel_productos'),
    path('panel/nuevo/', views.formulario, name='panel_nuevo'),
    path('panel/<int:producto_id>/editar/', views.editar_producto, name='panel_editar'),
    path('panel/<int:producto_id>/eliminar/', views.eliminar_producto, name='panel_eliminar'),
]
