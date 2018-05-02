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


@register.filter
def display_room_delta(room, rating):
    cl = lambda x: "neutral" if x==0 else "positive" if x>0 else "negative"
    if rating == 'absolute':
        label = '{:+d}'.format(room.delta)
        html = "<span class='%s'>%s</span>" % (cl(room.delta), label)
    if rating == 'relative':
        if room.members_from == 0 or room.percentage > 300:
            html = "<span class='positive'>New</span>"
        else:
            label = '{:+.2f}%'.format(room.percentage)
            html = "<span class='%s'>%s</span>" % (cl(room.percentage), label)
    if rating == 'senders':
        html = "<span class='neutral'><i class='far fa-user fa-sm'></i> %s</span>" % room.senders_total
    if rating == 'messages':
        html = "<span class='neutral'><i class='far fa-comment-alt fa-sm'></i> %s</span>" % room.messages_total
    if rating == 'audience_activity':
        html = "<span class='neutral'><i class='far fa-user'></i> %s%%</span>" % '{:.2f}'.format(room.relative_activity * 100)
    return mark_safe(html)
