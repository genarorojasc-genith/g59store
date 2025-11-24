# import requests
# from django.conf import settings
# from django.template.loader import render_to_string

# def enviar_correo_activacion(user, activation_link):
#     subject = "Activa tu cuenta en G59 Store"

#     html = render_to_string(
#         "emails/activar_cuenta.html",
#         {"user": user, "activation_link": activation_link}
#     )

#     url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"

#     return requests.post(
#         url,
#         auth=("api", settings.MAILGUN_API_KEY),
#         data={
#             "from": settings.DEFAULT_FROM_EMAIL,
#             "to": user.email,
#             "subject": subject,
#             "html": html,
#         }
#     )



# por ejemplo en app "usuarios" o "common": usuarios/email_utils.py

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_email(to_email, subject, template_name, context):
    """
    Envía un correo usando Mailgun con un template HTML de Django.
    template_name: 'emails/pedido_confirmacion.html', etc.
    """
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        logger.error("Mailgun no configurado. Falta API_KEY o DOMAIN.")
        return False

    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
            auth=("api", settings.MAILGUN_API_KEY),
            data={
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            },
            timeout=10,
        )
        if response.status_code != 200:
            logger.error("Error Mailgun %s: %s", response.status_code, response.text)
            return False
        return True
    except Exception as e:
        logger.exception("Error enviando correo con Mailgun: %s", e)
        return False
