from django import template

register = template.Library()

@register.filter
def status_row_class(status):
    return {
        'PRE': 'table-warning',
        'RDY': 'table-info',
        'SHP': 'table-success'
    }.get(status, '')