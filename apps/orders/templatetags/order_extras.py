from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr_name):
    """
    Retorna getattr(obj, attr_name) ou None se não existir.
    Permite fazer {{ obj|get_attr:"campo" }} no template.
    """
    try:
        return getattr(obj, attr_name)
    except Exception:
        return None