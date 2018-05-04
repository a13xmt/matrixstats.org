from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
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


@register.filter
def display_server_status(server):
    statuses = {
        'a': {'name': 'assumed', 'color': '#6495ED'},
        'c': {'name': 'confirmed', 'color': '#4682B4'},
        'n': {'name': 'not_exist', 'color': '#888'},
        'd': {'name': 'reg_disabled', 'color': '#888'},
        'r': {'name': 'registered', 'color': 'seagreen'},
        'u': {'name': 'unknown', 'color': 'violet'},
    }
    html = "<span style='color: %s'>%s</span>" % (
        statuses[server.status]['color'],
        statuses[server.status]['name']
    )
    return mark_safe(html)

@register.filter
def display_server_sync_state(server):
    icon = {
        'on': {'class': 'fas fa-caret-up', 'color': 'seagreen'},
        'off': {'class': 'fas fa-caret-down', 'color': '#B22222'},
        'impossible': {'class': 'fas fa-caret-down', 'color': '#888'}
    }
    value = 'off'
    if server.status == 'r' and server.sync_allowed:
        value = 'on'
    elif server.status in ['d', 'a', 'c', 'n']:
        value = 'impossible'
    html = "<i class='%s' style='color: %s;'></i>" % (
        icon[value]['class'],
        icon[value]['color']
    )
    return mark_safe(html)

@register.filter
def highlight_sync_delta(server):
    date = server.last_sync_time
    if not date:
        return "–"
    now = timezone.now()
    delta = (now - date).total_seconds()
    color_map = {
        600: "seagreen", # 10 minutes
        1200: "#94bd77", # 20 minutes
        1800: "#b0be6e", # 30 minutes
        3600: "#c4c56d", # 1 hr
        3600*3: "#d4c86a", # 3 hr
        3600*6: "#f5ce62", # 6 hr
        3600*24: "#e2886c", # 1 day
        3600*48: "#dd776e", # 2 day
        3600*72: "#dd776e", # 3 day
    }
    closest = min(color_map, key=lambda x: abs(x-delta))
    html = "<span style='color: %s'>%s</span" % (
        color_map[closest] if server.sync_allowed else '#888',
        date.strftime("%d/%m/%Y %H:%m"))
    return mark_safe(html)


@register.filter
def highlight_server_stats(stat):
    scn = stat.get('scn')
    if scn is None:
        return mark_safe("<td class='text-center'>–</td>")
    scp = '{:.0f}%'.format(scn)
    color_map = {
        100: 'seagreen',
        90: '#94bd77',
        70: '#b0be6e',
        50: '#e2886c',
        20: '#dd776e',
    }
    closest = min(color_map, key=lambda x: abs(x-scn))

    html = "<td class='text-center' style='color: %s' title='Requests: %s successful, %s failed.'>%s</td>" % (
        color_map[closest],
        stat.get('sc'),
        stat.get('ec'),
        scp
    )
    return mark_safe(html)

