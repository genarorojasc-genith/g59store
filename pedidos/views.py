from decimal import Decimal
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import Pedido, PedidoDetalle, DatosEnvio, DatosFactura, Cliente
from .forms import ClienteEmailForm, DatosEnvioForm, DatosFacturaForm, PedidoPagoForm
from carrito.cart import Cart
from django.db.models import Q
from usuarios.models import Perfil, PerfilFacturacion

from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

import mercadopago
from django.conf import settings


@login_required
def mis_pedidos(request):
    user = request.user
    q = Q()

    # 1) Si el user tiene Cliente asociado por OneToOne
    cliente = getattr(user, 'cliente', None)
    if cliente:
        q |= Q(cliente=cliente)

    # 2) Además, si el user tiene email, buscar por email del cliente
    if user.email:
        q |= Q(cliente__email__iexact=user.email.strip())

    pedidos = (
        Pedido.objects
        .filter(q)
        .prefetch_related('detalles__producto')
        .order_by('-creado')
        .distinct()
    )

    return render(request, 'pedidos/mis_pedidos.html', {'pedidos': pedidos})






@transaction.atomic
def checkout_iniciar(request):
    cart = Cart(request)

    if len(cart) == 0:
        return redirect('productos:index')

    # Si hay usuario logueado, intenta vincularlo a un Cliente
    cliente = None
    if request.user.is_authenticated:
        cliente, _ = Cliente.objects.get_or_create(
            email=(request.user.email or '').strip().lower() or f'anon_{request.user.id}@invalid.local',
            defaults={'user': request.user}
        )
        if cliente.user is None:
            cliente.user = request.user
            cliente.save(update_fields=['user'])

    # 1) Crear Pedido EN ESTADO "carrito"
    pedido = Pedido.objects.create(
        cliente=cliente,          # puede ser None si es invitado
        estado='carrito',
        estado_pago='pendiente',
        pagado=False,
    )

    # 2) Crear detalles desde el carrito
    for item in cart:
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=item['producto'],
            precio_unitario=item['precio'],
            cantidad=item['quantity'],
        )

    # 3) Calcular total
    pedido.actualizar_total(save=True)

    # 4) Guardar el id del pedido en la sesión para usarlo en el checkout
    request.session['checkout_pedido_id'] = pedido.id

    # 5) Redirigir a la vista que muestra el formulario de datos + pago
    return redirect('pedidos:pedido_crear')




@login_required
def pedido_detalle(request, pedido_id):
    user = request.user

    # Aseguramos que solo pueda ver pedidos suyos (mismo criterio que mis_pedidos)
    q_cliente = Q()
    cliente = getattr(user, 'cliente', None)
    if cliente:
        q_cliente |= Q(cliente=cliente)
    if user.email:
        q_cliente |= Q(cliente__email__iexact=user.email.strip())

    pedido = get_object_or_404(
        Pedido.objects.prefetch_related('detalles__producto'),
        Q(id=pedido_id) & q_cliente
    )

    envio = DatosEnvio.objects.filter(pedido=pedido).first()
    factura = DatosFactura.objects.filter(pedido=pedido).first()

    return render(request, 'pedidos/pedido_detalle.html', {
        'pedido': pedido,
        'envio': envio,
        'factura': factura,
    })




@transaction.atomic
def pedido_crear(request):
    cart = Cart(request)

    # Tomar el pedido que se creó al ir desde el carrito
    pedido_id = request.session.get('checkout_pedido_id')
    if not pedido_id:
        messages.error(request, 'No se encontró un pedido en curso.')
        return redirect('carrito:detalle')

    pedido = get_object_or_404(Pedido, id=pedido_id, pagado=False)

    # Cliente asociado (puede venir de antes o ser None)
    cliente = pedido.cliente

    # Perfiles del usuario (si está logueado)
    perfil = None
    perfil_facturacion = None
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
        except Perfil.DoesNotExist:
            perfil = None

        try:
            perfil_facturacion = request.user.perfil_facturacion
        except PerfilFacturacion.DoesNotExist:
            perfil_facturacion = None

    # Si el user está logueado y el pedido aún no tiene cliente, lo enlazamos
    if request.user.is_authenticated and not cliente:
        cliente, _ = Cliente.objects.get_or_create(
            email=(request.user.email or '').strip().lower() or f'anon_{request.user.id}@invalid.local',
            defaults={'user': request.user}
        )
        if cliente.user is None:
            cliente.user = request.user
            cliente.save(update_fields=['user'])
        pedido.cliente = cliente
        pedido.save(update_fields=['cliente'])

    if request.method == 'POST':
        f_cliente = ClienteEmailForm(request.POST, instance=cliente)
        f_envio   = DatosEnvioForm(request.POST)
        f_fact    = DatosFacturaForm(request.POST)
        f_pedido  = PedidoPagoForm(request.POST, instance=pedido)

        requiere_factura = f_fact.data.get('requiere_factura') == 'on'

        forms_ok = (
            f_cliente.is_valid() and
            f_envio.is_valid() and
            f_pedido.is_valid() and
            (f_fact.is_valid() if requiere_factura else True)
        )

        if not forms_ok:
            messages.error(request, 'Revisa los datos del formulario.')
            return render(request, 'pedidos/pedido_crear.html', {
                'cart': cart,
                'form_cliente': f_cliente,
                'form_envio': f_envio,
                'form_factura': f_fact,
                'form_pedido': f_pedido,
                'pedido': pedido,
                'perfil': perfil,
                'perfil_facturacion': perfil_facturacion,
            })

        # 1) Guardar / REUTILIZAR cliente por email
        email = f_cliente.cleaned_data['email']

        cliente, created = Cliente.objects.get_or_create(
            email=email,
            defaults={}
        )

        # Si el usuario está logueado y el cliente no tiene user, lo enlazamos
        if request.user.is_authenticated and not cliente.user:
            cliente.user = request.user
            cliente.save(update_fields=['user'])

        # 2) Guardar método de pago en el pedido
        pedido = f_pedido.save(commit=False)

        metodo = pedido.metodo_pago

        comision = settings.METODO_PAGO_COMISIONES.get(metodo, Decimal('0'))
        subtotal = pedido.total or Decimal('0')

        factor = Decimal('1') + comision
        total_final = (subtotal * factor).quantize(Decimal('1'))

        pedido.total = total_final

        # Enlazar al pedido
        pedido.cliente = cliente

        # 3) Crear datos de envío
        envio = f_envio.save(commit=False)
        envio.pedido = pedido
        envio.save()

        # 4) Crear factura si corresponde
        if requiere_factura:
            factura = f_fact.save(commit=False)
            factura.pedido = pedido
            factura.save()

        # 5) Cambiar estado del pedido
        pedido.estado = 'pendiente_pago'
        pedido.estado_pago = 'pendiente'
        pedido.pagado = False
        pedido.save()

        # 7) Enviar a la pasarela según método
        metodo = pedido.metodo_pago
        if metodo == 'mercadopago':
            return redirect(reverse('pagos:pagar_mercadopago', args=[pedido.id]))
        elif metodo == 'transbank':
            return redirect(reverse('pagos:transbank_iniciar', args=[pedido.id]))

        messages.info(request, 'Selecciona un método de pago.')
        return redirect('pedidos:pedido_crear')

    else:
        # GET: solo mostrar los forms
        f_cliente = ClienteEmailForm(instance=cliente)
        f_envio   = DatosEnvioForm()
        f_fact    = DatosFacturaForm()
        f_pedido  = PedidoPagoForm(instance=pedido)

    return render(request, 'pedidos/pedido_crear.html', {
        'cart': cart,
        'form_cliente': f_cliente,
        'form_envio': f_envio,
        'form_factura': f_fact,
        'form_pedido': f_pedido,
        'pedido': pedido,
        'perfil': perfil,
        'perfil_facturacion': perfil_facturacion,
    })




#pedidos vendedor


@login_required
def panel_pedidos(request):
    """
    Panel para vendedor:
    Muestra solo pedidos en estados: pagado, enviado, entregado, fallido.
    Permite filtrar por estado y buscar por ID o email cliente.
    """
    if not request.user.is_staff:
        raise PermissionDenied()

    estados_panel = ['pagado', 'enviado', 'entregado', 'fallido']

    estado = request.GET.get('estado', 'Todos')
    buscar = request.GET.get('q', '').strip()

    pedidos = (
        Pedido.objects
        .filter(estado__in=estados_panel)
        .select_related('cliente')
        .order_by('-creado')
    )

    if estado in estados_panel:
        pedidos = pedidos.filter(estado=estado)

    if buscar:
        pedidos = pedidos.filter(
            Q(id__icontains=buscar) |
            Q(cliente__email__icontains=buscar)
        )

    context = {
        'pedidos': pedidos,
        'estado_actual': estado,
        'buscar': buscar,
        'estados_panel': estados_panel,
    }
    return render(request, 'pedidos/panel_pedidos.html', context)





@login_required
def panel_pedido_detalle(request, pedido_id):
    """
    Detalle de un pedido visto desde el panel de vendedor.
    Sin restricción por cliente: solo por rol (is_staff).
    """
    if not request.user.is_staff:
        raise PermissionDenied()

    pedido = get_object_or_404(
        Pedido.objects
        .prefetch_related('detalles__producto')
        .select_related('cliente'),
        id=pedido_id
    )

    envio = DatosEnvio.objects.filter(pedido=pedido).first()
    factura = DatosFactura.objects.filter(pedido=pedido).first()

    return render(request, 'pedidos/panel_pedido_detalle.html', {
        'pedido': pedido,
        'envio': envio,
        'factura': factura,
    })






@require_POST
@login_required
def panel_pedido_cambiar_estado(request, pedido_id):
    """
    Cambia el estado de un pedido desde el panel.
    Flujo permitido:
      - pagado   -> enviado, fallido
      - enviado  -> entregado, fallido
      - entregado / fallido -> sin cambios
    """
    if not request.user.is_staff:
        raise PermissionDenied()

    pedido = get_object_or_404(Pedido, id=pedido_id)
    nuevo_estado = request.POST.get('estado')

    transiciones_validas = {
        'pagado': ['enviado', 'fallido'],
        'enviado': ['entregado', 'fallido'],
        'entregado': [],
        'fallido': [],
    }

    if nuevo_estado not in transiciones_validas.get(pedido.estado, []):
        messages.error(request, 'Cambio de estado no permitido para este pedido.')
    else:
        pedido.estado = nuevo_estado
        pedido.save(update_fields=['estado'])
        messages.success(
            request,
            f'Pedido #{pedido.id} actualizado a {pedido.get_estado_display()}.'
        )

    next_url = request.POST.get('next') or reverse('pedidos:panel_pedido_detalle', args=[pedido.id])
    return redirect(next_url)





