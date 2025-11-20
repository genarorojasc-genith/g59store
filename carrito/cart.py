from decimal import Decimal
from django.conf import settings
from productos.models import Producto

CART_SESSION_ID = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, producto, quantity=1, override_quantity=False):
        product_id = str(producto.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'precio': str(producto.precio),
            }

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        self.save()

    def save(self):
        # Guarda el carrito limpio en la sesión
        self.session[CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, producto):
        product_id = str(producto.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        productos = Producto.objects.filter(id__in=product_ids)

        for producto in productos:
            item = self.cart[str(producto.id)].copy()  # 👈 COPIA, NO TOCAS LA SESIÓN
            item['producto'] = producto
            item['precio'] = Decimal(item['precio'])  # ok
            item['total'] = item['precio'] * item['quantity']
            yield item

        


    def __len__(self):
        # Cantidad total de ítems (suma de cantidades)
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['precio']) * item['quantity'] for item in self.cart.values())


    def clear(self):
        # forma 1
        self.session[CART_SESSION_ID] = {}
        self.session.modified = True


