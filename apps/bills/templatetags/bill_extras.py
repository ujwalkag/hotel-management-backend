from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    return float(value) * float(arg)

@register.filter
def floatval(value):
    return float(value)

@register.filter
def float_sub(val1, val2):
    return float(val1) - float(val2)

