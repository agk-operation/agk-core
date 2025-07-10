from django import template

register = template.Library()

@register.inclusion_tag('components/_pagination.html', takes_context=True)
def render_pagination(context, page_obj, param='page'):
    """
    Usage: {% render_pagination items_page %}
    Você pode customizar o nome do parâmetro: {% render_pagination items_page 'p' %}
    """
    request = context['request']
    params = request.GET.copy()
    params.pop(param, None)
    return {
        'page_obj': page_obj,
        'param': param,
        'query_string': params.urlencode(),
    }
