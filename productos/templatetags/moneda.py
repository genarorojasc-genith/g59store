from django import template

register = template.Library()

@register.filter
def formato_pesos(value):
    """
    Convierte un número en algo tipo: $50.000
    """
    try:
        # pasamos a entero (sin decimales)
        numero = int(round(float(value)))
    except (TypeError, ValueError):
        return value  # si no es número, lo devolvemos tal cual

    # formato con separador de miles por coma
    formateado = f"{numero:,}"
    # cambiamos coma por punto -> 50,000 -> 50.000
    formateado = formateado.replace(",", ".")

    return f"${formateado}"
