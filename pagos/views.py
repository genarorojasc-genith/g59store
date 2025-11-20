import mercadopago
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages

from pedidos.models import Pedido
from carrito.cart import Cart


def pagar_mercadopago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, pagado=False)

    sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    preference_data = {
        "items": [
            {
                "title": f"Pedido #{pedido.id}",
                "quantity": 1,
                "currency_id": "CLP",
                "unit_price": float(pedido.total),
            }
        ],
        "back_urls": {
            "success": request.build_absolute_uri(reverse("pagos:mp_exito")),
            "failure": request.build_absolute_uri(reverse("pagos:mp_fallo")),
            "pending": request.build_absolute_uri(reverse("pagos:mp_pendiente")),
        },
        "auto_return": "approved",
    }

    preference = sdk.preference().create(preference_data)

    # 👇 Para ver qué está devolviendo Mercado Pago en la terminal
    print("MP preference response:", preference)

    resp = preference.get("response") or {}

    # Intentamos usar init_point o sandbox_init_point
    checkout_url = resp.get("init_point") or resp.get("sandbox_init_point")

    if not checkout_url:
        # Nada de KeyError: ahora respondemos con el error que devuelva MP
        return HttpResponse(
            f"No se recibió URL de checkout desde Mercado Pago. Respuesta: {resp}",
            status=500,
        )

    return redirect(checkout_url)


def mp_exito(request):
    """
    Mercado Pago redirige acá cuando el pago se aprueba.
    Marcamos el pedido como pagado y vaciamos el carrito.
    """
    pedido_id = request.session.get("checkout_pedido_id")

    if not pedido_id:
        # No encontramos el pedido en la sesión, pero al menos no rompemos todo
        return HttpResponse(
            "Pago aprobado, pero no se encontró un pedido en sesión.",
            status=200,
        )

    pedido = get_object_or_404(Pedido, id=pedido_id)

    payment_id = request.GET.get("payment_id", "")

    pedido.estado_pago = "aprobado"
    pedido.pagado = True
    pedido.transaccion_id = payment_id or f"mp-sim-{pedido.id}"
    pedido.save()

    cart = Cart(request)
    cart.clear()

    messages.success(request, "Tu pago en Mercado Pago fue aprobado.")
    return HttpResponse(f"Pago aprobado. Pedido #{pedido.id} marcado como pagado.")


def mp_fallo(request):
    """
    Mercado Pago redirige acá cuando el pago falla.
    """
    pedido_id = request.session.get("checkout_pedido_id")

    if pedido_id:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        pedido.estado_pago = "rechazado"
        pedido.save()

    messages.error(request, "Tu pago fue rechazado o hubo un problema.")
    return HttpResponse("Pago fallido.")


def mp_pendiente(request):
    """
    Mercado Pago redirige acá cuando el pago queda pendiente.
    """
    pedido_id = request.session.get("checkout_pedido_id")

    if pedido_id:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        pedido.estado_pago = "pendiente"
        pedido.save()

    messages.info(request, "Tu pago quedó pendiente en Mercado Pago.")
    return HttpResponse("Pago pendiente.")


def transbank_iniciar(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, pagado=False)

    # 🔹 AQUÍ iría la integración real con Webpay (Transbank):
    # - Crear transacción
    # - Redirigir a la URL de Webpay

    # Por ahora: simulamos pago aprobado
    pedido.estado_pago = "aprobado"
    pedido.pagado = True
    pedido.transaccion_id = f'tbk-sim-{pedido.id}'
    pedido.save()

    cart = Cart(request)
    cart.clear()

    return HttpResponse(f"Pago Transbank simulado OK para pedido #{pedido.id}.")
