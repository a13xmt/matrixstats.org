from django import template
import re

register = template.Library()

@register.filter
def format_lines(value):
    return re.sub(
        r" [\|•]{1,2} ",
        "\n\n",
        value
    )
