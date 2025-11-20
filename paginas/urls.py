from django.urls import path
from . import views

app_name = 'paginas'

urlpatterns = [
    # === RUTAS DEL PANEL (van primero) ===
    path('panel/', views.panel_paginas, name='panel_paginas'),
    path('panel/<int:pk>/editar/', views.editar_pagina, name='editar_pagina'),

    # === RUTAS PÚBLICAS (al final) ===
    path('<slug:slug>/', views.ver_pagina, name='ver'),
]

