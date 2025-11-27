from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_email(to_email, subject, template_name, context=None, from_email=None):
    """
    Envía un correo HTML usando el backend configurado en Django
    (en tu caso SendGrid via API).
    """
    if context is None:
        context = {}

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    # Renderizamos el HTML del correo
    html_body = render_to_string(template_name, context)

    # Cuerpo de texto plano (mínimo, por compatibilidad)
    text_body = context.get(
        "text_body",
        "Este correo contiene contenido HTML. "
        "Si no lo ves correctamente, habilita la visualización de HTML."
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
