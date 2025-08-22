from django import template

register = template.Library()

@register.filter
def get_bound_field(form, field_name):
    return form[field_name]
