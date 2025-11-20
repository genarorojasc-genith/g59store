from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

@login_required
def home(request):
    """
    Home del panel de administración.
    Punto de entrada para gestión de pedidos y, después, análisis, etc.
    """
    if not request.user.is_staff:
        raise PermissionDenied()

    return render(request, 'panel/home.html', {})
