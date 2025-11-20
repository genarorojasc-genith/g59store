from django import forms
from django.core.exceptions import ValidationError
from .models import Pedido, Cliente, DatosEnvio, DatosFactura


# 1) Solo lo que realmente vive en Pedido (p.ej. método de pago)
class PedidoPagoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['metodo_pago']
        labels = {'metodo_pago': 'Método de pago'}


# 2) El email ya no está en Pedido: va a Cliente
# class ClienteEmailForm(forms.ModelForm):
#     class Meta:
#         model = Cliente
#         fields = ['email']
#         labels = {'email': 'Correo de contacto (para boleta y seguimiento)'}

#     def __init__(self, *args, **kwargs):
#         # Si pasas user en kwargs, podemos validar mejor la unicidad
#         self.user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)

#     def clean_email(self):
#         email = self.cleaned_data['email'].strip().lower()
#         # Permitir el mismo email si ya es del mismo cliente
#         qs = Cliente.objects.filter(email=email)
#         if self.instance.pk:
#             qs = qs.exclude(pk=self.instance.pk)

#         if qs.exists():
#             raise ValidationError('Este correo ya está registrado para otro cliente.')
#         return email



class ClienteEmailForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['email']
        labels = {'email': 'Correo de contacto (para boleta y seguimiento)'}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        # Normalizamos, nada más
        email = (self.cleaned_data.get('email') or '').strip().lower()
        return email

    def validate_unique(self):
        """
        Evitar que el ModelForm dispare el error de unicidad de email.
        La lógica de reutilizar/crear Cliente la manejamos en la vista.
        """
        pass



# 3) Datos de envío (OneToOne con Pedido)
class DatosEnvioForm(forms.ModelForm):
    class Meta:
        model = DatosEnvio
        # OJO: nombres exactos de tus campos
        fields = ['nombre_recibe', 'direccion_recibe', 'ciudad_recibe']
        labels = {
            'nombre_recibe': 'Nombre de quien recibe',
            'direccion_recibe': 'Dirección de entrega',
            'ciudad_recibe': 'Ciudad',
        }

    # No incluimos 'pedido' porque lo seteas en la vista:
    # envio = form.save(commit=False); envio.pedido = pedido; envio.save()


# 4) Datos de facturación (OneToOne con Pedido) + checkbox “requiere factura”
class DatosFacturaForm(forms.ModelForm):
    requiere_factura = forms.BooleanField(
        required=False,
        label='¿Requieres factura?',
        help_text='Si no marcas, se emitirá boleta.'
    )

    class Meta:
        model = DatosFactura
        fields = [
            'requiere_factura',   # campo NO de modelo, solo del form
            'rut_facturacion',
            'razon_social',
            'giro',
            'direccion_facturacion',
            'ciudad_facturacion',
        ]
        labels = {
            'rut_facturacion': 'RUT',
            'razon_social': 'Razón social',
            'giro': 'Giro (opcional)',
            'direccion_facturacion': 'Dirección de facturación',
            'ciudad_facturacion': 'Ciudad',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Por defecto, oculta/relaja validación si no se pide factura:
        # (A nivel de frontend puedes esconder estos campos cuando el
        # checkbox no esté marcado. Aquí hacemos la validación dura.)
        self._all_factura_fields = [
            'rut_facturacion',
            'razon_social',
            'direccion_facturacion',
            'ciudad_facturacion',
        ]

    def clean(self):
        cleaned = super().clean()
        requiere = cleaned.get('requiere_factura')

        if requiere:
            # Si requiere factura → validar obligatorio (excepto giro)
            for f in self._all_factura_fields:
                if not cleaned.get(f):
                    self.add_error(f, 'Obligatorio para emitir factura.')
        else:
            # Si NO requiere factura → ignorar completamente los campos
            # Básicamente: los pongo en blanco para evitar validaciones del modelo
            for f in self._all_factura_fields:
                cleaned[f] = None

        return cleaned

