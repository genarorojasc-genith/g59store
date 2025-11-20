from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages

from productos.models import Producto
from .cart import Cart


@require_POST
def cart_add(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)

    # Cantidad pedida en el formulario (detalle o index)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    # Cantidad que ya hay en el carrito de ese producto
    existing_qty = cart.cart.get(str(producto.id), {}).get('quantity', 0)
    desired_total = existing_qty + quantity

    if producto.stock <= 0:
        messages.warning(request, f'“{producto.nombre}” no tiene stock disponible.')
    elif desired_total > producto.stock:
        messages.warning(
            request,
            f'No puedes agregar más de {producto.stock} unidades de “{producto.nombre}”.'
        )
    else:
        cart.add(producto=producto, quantity=quantity)
        messages.success(request, f'“{producto.nombre}” se agregó al carrito.')

    return redirect('carrito:detalle')


@require_POST
def cart_remove(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)

    cart.remove(producto)
    messages.info(request, f'“{producto.nombre}” se quitó del carrito.')

    return redirect('carrito:detalle')


@require_POST
def cart_update(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    if producto.stock <= 0:
        messages.warning(request, f'“{producto.nombre}” no tiene stock disponible.')
        # No actualizamos el carrito si no hay stock
        return redirect('carrito:detalle')

    if quantity > producto.stock:
        quantity = producto.stock
        messages.warning(
            request,
            f'Solo hay {producto.stock} unidades disponibles de “{producto.nombre}”; se ajustó la cantidad.'
        )
    else:
        messages.success(request, f'Se actualizó la cantidad de “{producto.nombre}”.')

    cart.add(producto=producto, quantity=quantity, override_quantity=True)

    return redirect('carrito:detalle')


@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, 'Carrito vaciado.')
    return redirect('carrito:detalle')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'carrito/detalle.html', {'cart': cart})
