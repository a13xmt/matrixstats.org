from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def format_lines(value):
    return re.sub(
        r" [\|•]{1,3} ",
        "\n\n",
        value
    )
