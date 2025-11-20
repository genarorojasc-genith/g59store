from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto, Categoria
from .forms import ProductoForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from django.db.models.deletion import ProtectedError
from django.contrib import messages


def inicio(request):
    # Hasta 8 productos marcados como destacados
    productos_destacados = Producto.objects.filter(destacado=True)[:8]
    return render(request, 'inicio.html', {
        'productos_destacados': productos_destacados,
    })



def index(request):
    categoria_id = request.GET.get('categoria')

    productos = Producto.objects.filter(activo=True)
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    categorias = Categoria.objects.all()

    contexto = {
        'productos': productos,
        'categorias': categorias,
        'categoria_seleccionada': int(categoria_id) if categoria_id else None,
    }
    return render(request, 'productos/index.html', contexto)


def detalle(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'productos/detalle.html', {'producto': producto})

# ---------- PANEL DE PRODUCTOS (solo staff) ----------

@login_required
def panel_productos(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    # Acciones masivas
    if request.method == 'POST':
        ids = request.POST.getlist('productos')   # lista de IDs marcados
        accion = request.POST.get('accion')

        if not ids:
            messages.warning(request, 'No seleccionaste ningún producto.')
            return redirect('productos:panel_productos')

        productos_sel = Producto.objects.filter(pk__in=ids)

        if accion == 'eliminar':
            eliminados = 0
            protegidos = []

            for p in productos_sel:
                try:
                    p.delete()
                    eliminados += 1
                except ProtectedError:
                    protegidos.append(p.nombre)

            if eliminados:
                messages.success(request, f'Se eliminaron {eliminados} producto(s).')

            if protegidos:
                messages.error(
                    request,
                    'No se pudieron eliminar estos productos porque tienen pedidos asociados: '
                    + ', '.join(protegidos)
                )

        elif accion == 'activar':
            actualizados = productos_sel.update(activo=True)
            messages.success(request, f'Se activaron {actualizados} producto(s).')

        elif accion == 'desactivar':
            actualizados = productos_sel.update(activo=False)
            messages.success(request, f'Se desactivaron {actualizados} producto(s).')

        else:
            messages.error(request, 'Acción no válida.')

        return redirect('productos:panel_productos')

    # GET normal: mostrar listado
    productos = (
        Producto.objects
        .select_related('categoria')
        .order_by('nombre')
    )
    return render(request, 'productos/panel_lista.html', {
        'productos': productos,
    })



@login_required
def formulario(request):
    """Crear nuevo producto desde el panel."""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('productos:panel_productos')
    else:
        form = ProductoForm()

    return render(request, 'productos/formulario.html', {
        'form': form,
        'titulo': 'Crear nuevo producto',
    })


@login_required
def editar_producto(request, producto_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('productos:panel_productos')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'productos/formulario.html', {
        'form': form,
        'producto': producto,
        'titulo': f'Editar producto: {producto.nombre}',
    })


@login_required
def eliminar_producto(request, producto_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == 'POST':
        try:
            producto.delete()
            messages.success(request, f'El producto "{producto.nombre}" fue eliminado.')
        except ProtectedError:
            messages.error(
                request,
                f'No puedes eliminar "{producto.nombre}" porque ya tiene pedidos asociados. '
                'En un ecommerce real se recomienda desactivarlo en vez de borrarlo.'
            )

    return redirect('productos:panel_productos')
