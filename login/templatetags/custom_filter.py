from django import template

register = template.Library()

@register.filter
def split_join(value):
    return '_'.join(value.split())
