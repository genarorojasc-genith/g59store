# common/email_utils.py

import logging
import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_email(to_email, subject, template_name, context):
    """
    Envía un correo usando Mailgun API.
    """

    # DEBUG: ver qué ve Django en producción
    print("DEBUG MAILGUN DOMAIN:", repr(getattr(settings, "MAILGUN_DOMAIN", None)))
    print("DEBUG MAILGUN API_KEY set?:", bool(getattr(settings, "MAILGUN_API_KEY", None)))

    api_key = getattr(settings, "MAILGUN_API_KEY", None)
    domain = getattr(settings, "MAILGUN_DOMAIN", None)

    if not api_key or not domain:
        logger.error("Mailgun no configurado. Falta API_KEY o DOMAIN.")
        return False

    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{domain}/messages",
            auth=("api", api_key),
            data={
                # IMPORTANTE: que el from use un dominio válido en Mailgun
                "from": getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    "no-reply@mg.g59store.cl",
                ),
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            },
            timeout=10,
        )

        print("DEBUG MAILGUN RESPONSE:", response.status_code, response.text)

        if response.status_code != 200:
            logger.error("Error Mailgun %s: %s", response.status_code, response.text)
            return False

        return True

    except Exception as e:
        logger.exception("Error enviando correo con Mailgun: %s", e)
        return False


