import requests
import json
import re
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http.response import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Case, When
from django.conf import settings
from django.http import Http404
from random import shuffle

from matrix_bot.tasks import register
from room_stats.models import Room, DailyMembers, Tag, Category, PromotionRequest, Server, RoomStatisticalData, get_period_starting_date
from .rawsql import NEW_ROOMS_FOR_LAST_N_DAYS_QUERY, ROOM_STATISTICS_FOR_PERIOD_QUERY

def check_recaptcha(function):
    def wrap(request, *args, **kwargs):
        request.recaptcha_is_valid = None
        if request.method == 'POST':
            recaptcha_response = request.POST.get('g-recaptcha-response')
            data = {
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result = r.json()
            if result['success']:
                request.recaptcha_is_valid = True
            else:
                request.recaptcha_is_valid = False
                # messages.error(request, 'Invalid reCAPTCHA. Please try again.')
        return function(request, *args, **kwargs)

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap


def render_rooms_paginated(request, queryset, context=None, page_size=30):
    context = context or {}
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    paginator = Paginator(queryset, page_size)
    try:
        rooms = paginator.page(page)
    except EmptyPage:
        rooms = paginator.page(paginator.num_pages)
    context['rooms'] = rooms
    return render(request, 'room_stats/rooms_list.html', context)


def get_daily_members_stats(request, room_id):
    stats = DailyMembers.objects.filter(room_id=room_id).order_by('date')
    result = [{
        'date': s.date,
        'members_count': s.members_count
        } for s in stats]
    return JsonResponse({'result': result})


def room_stats_view(request, room_id):
    room = Room.objects.filter(id=room_id).first()
    if not room:
        raise Http404("Room not found")
    context = {
        'room': room,
    }

    # category edit inline (admin)
    if request.user.id:
        context['categories'] = Category.objects.order_by('name')
        context['admin'] = True

    # members delta
    current_members = DailyMembers.objects.filter(room_id=room_id).last().members_count
    try:
        last_week_members = DailyMembers.objects.filter(
            room_id=room_id,
            date=datetime.now() - timedelta(days=7)
        ).first().members_count
    except AttributeError:
        last_week_members = 0
    try:
        last_month_members = DailyMembers.objects.filter(
            room_id=room_id,
            date=datetime.now() - timedelta(days=30)
        ).first().members_count
    except AttributeError:
        last_month_members = 0
    context['members_weekly_diff'] = current_members - last_week_members
    context['members_monthly_diff'] = current_members - last_month_members

    # promotion details
    pr = room.promotionrequest_set.first()
    already_promoted = True if pr else False
    promotion_pending = already_promoted and not pr.active
    room_too_big = room.members_count > 500
    promotion_available = not (already_promoted or promotion_pending or room_too_big) # all conditions should be false
    promotion_reason = None
    if already_promoted: promotion_reason = "active till %s" % pr.remove_at.strftime("%B %d, %Y")
    if promotion_pending: promotion_reason = "pending review"
    context['promotion_available'] = promotion_available
    context['promotion_reason'] = promotion_reason

    return render(request, 'room_stats/room_details.html', context)

def list_rooms_by_category(request, category_name):
    category = Category.objects.filter(name=category_name).first()
    if not category:
        raise Http404("Category does not exist")
    rooms = Room.objects.filter(categories__id=category.id).order_by('-members_count')
    context = {
        'title': 'Rooms by category: %s' % category.name,
        'header': 'Rooms by category: %s' % category.name
    }
    return render_rooms_paginated(request, rooms, context)

def list_rooms_by_random(request):
    rooms = Room.objects.filter(members_count__gt=5).order_by('?')[:30]
    context = {
        'rooms': rooms,
        'title': "Matrix Rooms: Random",
        'header': 'Random rooms',
        'random_rooms_rating': True
    }
    return render(request, 'room_stats/rooms_list.html', context)

def list_rooms_by_members_count(request):
    # rooms = Room.objects.filter(
    #     members_count__gt=5).order_by('-members_count')[:20]
    # context = {'rooms': rooms}
    # return render(request, 'room_stats/rooms_list.html', context)
    context = {
        'title': 'Matrix Rooms: Top by members',
        'header': 'Top rooms by members'
    }
    rooms = Room.objects.filter(
        members_count__gt=5).order_by('-members_count')
    return render_rooms_paginated(request,rooms, context)

def list_rooms_with_tag(request, tag):
    rooms = Room.objects.filter(topic__iregex='#%s' % tag)
    context = {
        'title': 'Matrix Rooms: by #%s tag' % tag,
        'header': 'Rooms by #%s tag' % tag
    }
    return render_rooms_paginated(request, rooms, context)

def get_tags(show_all=False, limit=None):
    if show_all:
        tags = Tag.objects.annotate(Count('rooms'))
    else:
        tags = Tag.objects.exclude(id__iregex='(anal|blowjobs|porn|sex|kink|adult|piss|amateur)').annotate(Count('rooms'))
    if limit:
        tags = tags.order_by('?')[:limit]
    sizes = [tag.rooms__count for tag in tags]
    clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
    smin, smax = min(sizes), max(sizes)
    for tag in tags:
        tag.relative_size = (clamp(tag.rooms__count, 1, 6) / 5) + 0.6
    return tags

def list_tags(request):
    show_all = request.GET.get('all', None)
    context = {
        'tags': get_tags(show_all),
        'show_all': show_all
    }
    return render(request, 'room_stats/tag_list.html', context)

def list_rooms_by_lang_ru(request):
    rooms = Room.objects.filter(topic__iregex=r'[а-яА-ЯёЁ]+').order_by('-members_count')
    context = {
        'title': 'Matrix Rooms: Cyrillic | Русскоязычные комнаты Matrix',
        'header': 'Русскоязычные комнаты'
    }
    return render_rooms_paginated(request, rooms, context)

from django.contrib.postgres.search import SearchVector
def list_rooms_by_search_term(request, term):
    rooms = Room.objects.annotate(
        search=SearchVector('name', 'aliases', 'topic'),
    ).filter(search=term)
    context = {
        'title': "Matrix Search: %s" % term,
        'header': "Search"
    }
    return render_rooms_paginated(request, rooms, context)

from .rawsql import MOST_INCOMERS_PER_PERIOD_QUERY
def get_most_joinable_rooms(delta, rating='absolute', limit=100):
    rating_to_order_mapper = {
        'absolute': 'delta',
        'relative': 'percentage'
    }
    # supported order_by values: ('delta', 'percentage')
    from_date = datetime.now() - timedelta(days=delta)
    to_date = datetime.now() - timedelta(days=1)
    rooms = Room.objects.raw(
        MOST_INCOMERS_PER_PERIOD_QUERY % {
            'from_date': from_date,
            'to_date': to_date,
            'order_by': rating_to_order_mapper[rating]
        }
    )[:limit]
    return rooms

def list_most_joinable_rooms(request, delta, rating='absolute', limit=250):
    rooms = get_most_joinable_rooms(delta, rating, limit)

    title = "Matrix Trends: Most %s rooms for last %s days" % (
        'joinable' if rating == 'absolute' else 'expansive', delta)
    header = "Most %s rooms (for last %s days)" % (
        'joinable' if rating == 'absolute' else 'expansive', delta)

    context = {
        'rating': rating,
        'title': title,
        'header': header
    }
    return render_rooms_paginated(request, rooms, context=context)

def list_new_rooms(request, delta=3):
    rooms = Room.objects.raw(
        NEW_ROOMS_FOR_LAST_N_DAYS_QUERY % delta
    )[:]
    context = {
        'title': "Matrix Trends: New rooms for last %s days" % delta,
        'header': "New rooms (for last %s days)" % delta
    }
    return render_rooms_paginated(request, rooms, context)


def list_public_rooms(request):
    rooms = Room.objects.filter(
        is_public_readable=True).order_by('-members_count')
    context = {
        'title': 'Matrix Rooms: Top by members (Public)',
        'header': 'Top rooms by members (public)'
    }
    return render_rooms_paginated(request, rooms, context)

@login_required
def set_room_category(request, room_id, category_id):
    room = Room.objects.get(id=room_id)
    category = None if int(category_id) == 0 else Category.objects.get(id=category_id)
    room.category = category
    room.save()
    return JsonResponse({'status': 'ok'})

@login_required
def set_room_categories(request, room_id):
    data = json.loads(request.body)
    category_ids = [int(val) for val in data]
    room = Room.objects.get(pk=room_id)
    room.categories.clear()
    room.categories.add(*category_ids)
    room.save()
    return JsonResponse({'status': 'ok'})


def rooms_by_homeserver(request, homeserver):
    rooms = Room.objects.filter(federated_with__has_key=homeserver).order_by('-members_count')
    context = {
        'title': '%s rooms' % homeserver,
        'header': '%s rooms' % homeserver
    }
    return render_rooms_paginated(request, rooms, context)


def list_rooms_by_activity(request, rating, period, delta):
    try: delta = int(delta)
    except ValueError: delta = 1
    date = datetime.now() - timedelta(days=delta)
    starts_at = (get_period_starting_date(period, date)).date()
    sd = RoomStatisticalData.objects.filter(period=period, starts_at=starts_at).order_by('-%s_total' % rating)[:250]
    sd_obj = {s.room_id: s for s in sd}
    room_ids = [s.room_id for s in sd]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(room_ids)])
    rooms = Room.objects.filter(id__in=room_ids).order_by(preserved)

    for room in rooms:
        room.senders_total = sd_obj[room.id].senders_total
        room.messages_total = sd_obj[room.id].messages_total

    period_verbose = {'d':'day', 'w': 'week', 'm':'month'}[period]
    rating_verbose = {'senders': 'active members', 'messages': 'messages'}[rating]
    context = {
        'header': 'Rooms by most %s per %s (%s)' % (rating_verbose, period_verbose, starts_at),
        'rating': rating,
        'period': period,
        'delta': delta
    }
    return render_rooms_paginated(request, rooms, context)

def list_rooms_by_active_audience(request, delta):
    period = 'm'
    try: delta = int(delta)
    except ValueError: delta = 1
    date = datetime.now() - timedelta(days=delta)
    starts_at = (get_period_starting_date(period, date)).date()
    sd = RoomStatisticalData.objects.filter(period=period, starts_at=starts_at)
    sd_obj = {s.room_id: s for s in sd}
    room_ids = [s.room_id for s in sd]
    rooms = Room.objects.filter(id__in=room_ids)
    for room in rooms:
        room.relative_activity = sd_obj[room.id].senders_total / room.members_count
    srooms = sorted(rooms, key=lambda r: -r.relative_activity)
    context = {
        'header': 'Rooms by audience activity (%s)' % starts_at,
        'rating': 'audience_activity',
    }
    return render_rooms_paginated(request, srooms, context)

def list_rooms(request):
    categories = Category.objects.order_by('?')[0:8]
    new_ids = [r.id for r in Room.objects.raw(NEW_ROOMS_FOR_LAST_N_DAYS_QUERY % 30)[:]]
    new = Room.objects.filter(id__in=new_ids, members_count__gte=5).exclude(avatar_url__exact='').exclude(topic__exact='').order_by('?')[:20]
    random = Room.objects.filter(members_count__gt=5).exclude(avatar_url__exact='').exclude(topic__exact='').order_by('?')[:20]
    most_joinable = get_most_joinable_rooms(delta=30, rating='absolute', limit=20)
    most_expanding = get_most_joinable_rooms(delta=30, rating='relative', limit=20)
    tags = get_tags(limit=100)
    context = {
        'categories': categories,
        'new': new,
        'random': random,
        'most_joinable': most_joinable,
        'most_expanding': most_expanding,
        'tags': tags
    }
    return render(request, 'room_stats/index.html', context)

def list_categories(request):
    categories = list(Category.objects.annotate(Count('room'))[:])
    shuffle(categories) # order_by('?') doesn't work with annotations
    context = {'categories': categories}
    return render(request, 'room_stats/categories.html', context)

def list_ratings(request):
    context = {}
    return render(request, 'room_stats/ratings.html', context)


@check_recaptcha
def promote_room(request):
    if request.recaptcha_is_valid:
        description = request.POST.get('description')
        room_id = request.POST.get('room_id')
        room = Room.objects.get(pk=room_id)
        pr = PromotionRequest.objects.filter(room=room).first()
        if pr:
            response = {
                'success': False,
                'message': 'ALREADY_PROMOTED'
            }
        else:
            size = 's' if room.members_count <= 50 else 'm'
            pr = PromotionRequest(
                room=room,
                description=description,
                size=size,
                active= True if len(description) == 0 else False,
                remove_at=datetime.now() + timedelta(days=7 if size == 's' else 14)
            )
            pr.save()
            response = {
                'success': True,
                'premoderation': True if description else False
            }
        return JsonResponse(response)
    else:
        return JsonResponse({ 'success': False, 'message': 'INVALID_CAPTCHA'}, status=403)

def list_promoted_rooms(request, size=None):
    promotions = PromotionRequest.objects.filter(size=size, active=True)
    rooms = Room.objects.filter(pk__in=[p.room.id for p in promotions])
    print(promotions)
    print(rooms)
    context = {
    }
    # return render(request, 'room_stats/promoted_rooms.html', context)
    return render_rooms_paginated(request, rooms, context)


def index_simple(request):
    return render(request, 'room_stats/index_simple.html')

def about(request):
    return render(request, 'room_stats/about.html')

def bot(request):
    return redirect("/faq/#bot")

def faq(request):
    return render(request, 'room_stats/faq.html')

@login_required
def set_server_recaptcha(request):
    data = json.loads(request.body)
    server_id = data.get('server_id', None)
    captcha = data.get('captcha', None)
    if not (server_id or captcha):
        return JsonResponse({'success': False, 'message': "INVALID_PARAMS"}, status=403)
    server = Server.objects.get(pk=server_id)
    server.data['reg_captcha_response'] = captcha
    server.data['reg_active_stage_progress'] = "USER_ACTION_COMPLETE"
    server.save(update_fields=['data'])
    register.apply_async((server_id,))
    return JsonResponse({'success': True})


from matrix_bot.resources import rds
def list_homeservers(request):
    servers = Server.objects.all().order_by('id')

    dates = []
    for delta in [2,1,0]:
        dates.append(str((datetime.now() - timedelta(days=delta)).date()))
    for server in servers:
        last_sync = rds.lindex("%s__sync_stats" % server.hostname, 0)
        last_sync = datetime.fromtimestamp(int(last_sync.decode().split(":")[2])) if last_sync else None
        server.last_sync = last_sync
        server.stats = {}
        total = server.data.get('total_rooms', 0)
        owned = server.data.get('owned_rooms', 0)
        server.total = total
        server.owned = owned
        server.room_disp = "%s/%s" % (total, owned) if (total is not 0 and owned is not 0) else ''
        print(server.room_disp)

    for date in dates:
        sc_keys = [ "%s__sc__%s" % (s.hostname, date) for s in servers]
        ec_keys = [ "%s__ec__%s" % (s.hostname, date) for s in servers]
        ed_keys = [ "%s__ed__%s" % (s.hostname, date) for s in servers]
        success_calls = [int(e.decode()) if e else 0 for e in rds.mget(*sc_keys)]
        error_calls = [int(e.decode()) if e else 0 for e in rds.mget(*ec_keys)]
        p = rds.pipeline()
        for ed_key in ed_keys:
            p.lrange(ed_key, 0, 100)
        error_details = p.execute()
        for server, sc, ec, ed in zip(servers, success_calls, error_calls, error_details):
            ed = [e.decode() for e in ed]
            scn = None if sc == 0 else 100 if ec == 0 else (sc / (sc+ec) * 100)
            server.stats[date] = {
                'sc': sc,
                'ec': ec,
                'ed': ed,
                'scn': scn
            }
    context = {
        'servers': servers,
        'dates': dates
    }
    return render(request, 'room_stats/homeservers.html', context)

@check_recaptcha
def add_homeserver(request):
    if request.recaptcha_is_valid:
        hostname = request.POST.get('hostname')
        hostname = re.sub('[^a-zA-Z0-9\.\:\_\-]+', '', hostname)
        hs = Server.objects.filter(hostname=hostname).first()
        if hs:
            return JsonResponse({'success': False, 'message': 'ALREADY_EXISTS'})
        hs = Server(hostname=hostname, sync_interval=600)
        hs.save()
        return JsonResponse({'success': True, 'message': 'CREATED'})
    else:
        return JsonResponse({'success': False, 'message': 'INVALID_CAPTCHA'}, status=403)

def get_room_statistics(request, room_id):
    periods = ['d','w','m']
    intervals = {
        'd': '1 day',
        'w': '7 day',
        'm': '1 month'
    }
    room = Room.objects.filter(pk=room_id).first()
    if not room:
        raise Http404("There is no such statistics")

    result = {}
    for period in periods:
        stats = RoomStatisticalData.objects.raw(
            ROOM_STATISTICS_FOR_PERIOD_QUERY % {
                'room_id': room_id,
                'period': period,
                'interval': intervals[period]
            }
        )
        # Empty if just two date borders inside
        if len(stats[:]) <= 2:
            raise Http404("There is no such statistics")
        senders = [{
            'date': s.starts_at,
            'value': s.senders_total,
            'index': 'senders'
        } for s in stats]

        messages = [{
            'date': s.starts_at,
            'value': s.messages_total,
            'index': 'messages'
        } for s in stats]

        ovdmx_messages = max([s.messages_total for s in stats]) * 1.1
        ovdmx_senders = ovdmx_messages * 0.5

        result[period] = {}
        result[period]['senders'] = senders
        result[period]['messages'] = messages
        result[period]['ovdmx_senders'] = ovdmx_senders
        result[period]['ovdmx_messages'] = ovdmx_messages
    return JsonResponse(result)

def get_homeserver_stats(request, homeserver):
    server = Server.objects.filter(hostname=homeserver).first()
    if not server:
        raise Http404("There is no such server")
    dates = []
    for delta in [2,1,0]:
        dates.append(str((datetime.now() - timedelta(days=delta)).date()))

    result = {}
    for date in dates:
        sts_key = "%s__sts__%s" % (server.hostname, date)
        ets_key = "%s__ets__%s" % (server.hostname, date)

        success_timestamps = [ int(t.decode()) for t in rds.smembers(sts_key) ]
        error_timestamps = [ int(t.decode()) for t in rds.smembers(ets_key) ]

        # Builds map with statistical values
        PERIOD = 86400
        CHUNK_SIZE = 600
        chunks = int(PERIOD / CHUNK_SIZE)
        stats = [{'s': 0, 'e': 0} for i in range(0, chunks)]

        # Calculates corresponding chunk for given timestamp
        assign_chunk = lambda ts: int( ts / CHUNK_SIZE )

        # Calculates success ratio for requests
        success_ratio = lambda sc,ec: None if sc == 0 else 100 if ec == 0 else (sc / (sc+ec) * 100)

        for ts in success_timestamps:
            chunk = assign_chunk(ts)
            stats[chunk]['s'] += 1;

        for ts in error_timestamps:
            chunk = assign_chunk(ts)
            stats[chunk]['e'] += 1;

        for item in stats:
            item['r'] = success_ratio(item['s'], item['e'])

        result[date] = stats
    return JsonResponse(result)


def get_homeserver_details(request, homeserver):
    server = Server.objects.filter(hostname=homeserver).first()
    if not server:
        raise Http404("There is no such server")
    context = {'server': server}
    return render(request, "room_stats/homeserver_details.html", context)


def api_get_rooms(request):
    rooms = Room.objects.prefetch_related('categories')
    result = [{
        'id': room.id,
        'homeserver': room.id.split(':')[-1],
        'name': room.name,
        'categories': [category.name for category in room.categories.all()],
        'aliases': room.aliases.split(', '),
        'topic': room.topic,
        'members_count': room.members_count,
        'avatar_url': room.avatar_url,
        'is_public_readable': room.is_public_readable,
        'is_guest_writeable': room.is_guest_writeable,
        'created_at': room.created_at,
        'updated_at': room.updated_at,
        'federated_with': [key for key in room.federated_with.keys()]
    } for room in rooms]
    return JsonResponse({'rooms': result})


