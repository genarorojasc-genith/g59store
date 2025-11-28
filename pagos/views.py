import mercadopago
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages

from pedidos.models import Pedido
from carrito.cart import Cart

from common.email_utils import send_email
from django.shortcuts import render



def pagar_mercadopago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, pagado=False)
    # Guardamos el id del pedido en sesión para las vistas de exito/fallo/pendiente
    request.session["checkout_pedido_id"] = pedido.id

    # Si tu modelo Pedido tiene campo metodo_pago, lo dejamos seteado
    if hasattr(pedido, "metodo_pago"):
        pedido.metodo_pago = "mercadopago"
        pedido.save(update_fields=["metodo_pago"])

    # SDK Mercado Pago con el Access Token de settings
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



def enviar_correo_confirmacion_pedido(pedido):
    """
    Envía el correo de confirmación de pedido usando la función común send_email.
    Intenta usar el email del cliente asociado al pedido.
    """
    # buscamos un correo razonable
    to_email = None

    cliente = getattr(pedido, "cliente", None)
    if cliente and getattr(cliente, "email", None):
        to_email = cliente.email
    elif getattr(pedido, "email", None):
        to_email = pedido.email

    if not to_email:
        # si no hay correo, no intentamos mandar nada
        return

    send_email(
        to_email=to_email,
        subject=f"Confirmación de compra #{pedido.id}",
        template_name="emails/pedido_confirmacion.html",
        context={"pedido": pedido},
    )




def mp_exito(request):
    """
    Mercado Pago redirige acá cuando el pago se aprueba.
    Marcamos el pedido como pagado y vaciamos el carrito.
    """
    pedido_id = request.session.get("checkout_pedido_id")

    if not pedido_id:
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

    # 🔔 Enviar correo de confirmación de pedido
    enviar_correo_confirmacion_pedido(pedido)

    cart = Cart(request)
    cart.clear()

    messages.success(request, "Tu pago en Mercado Pago fue aprobado.")
    return render(request, "pagos/mercadopago_exito.html", {"pedido": pedido})



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

    return render(request, "pagos/transbank_exito.html", {"pedido": pedido})
