from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Retorna dictionary.get(key), mas se dictionary for None
    devolve None (em vez de estourar).
    """
    try:
        return dictionary.get(key)
    except Exception:
        return None


@register.filter
def get_field(form, field_name):
    """
    Dado um Form ou SubForm, retorna o BoundField form[field_name]
    para poder chamar label_tag, errors, etc.
    """
    try:
        return form[field_name]
    except Exception:
        return None