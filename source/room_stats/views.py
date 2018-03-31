import requests
import json
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http.response import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.conf import settings
from django.http import Http404
from random import shuffle

from room_stats.models import Room, DailyMembers, Tag, ServerStats, Category, PromotionRequest
from .rawsql import NEW_ROOMS_FOR_LAST_N_DAYS_QUERY

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


def render_rooms_paginated(request, queryset, context={}, page_size=30):
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, page_size)
    try:
        rooms = paginator.page(page)
    except EmptyPage:
        rooms = paginator.page(paginator.num_pages)
    context['rooms'] = rooms
    return render(request, 'room_stats/rooms_list.html', context)


def get_daily_members_stats(request, room_id, days=30):
    from_date = datetime.now() - timedelta(days=int(days)-1)
    dm = DailyMembers.objects.filter(
        room_id=room_id,
        date__gte=from_date,
    )
    result = []
    for day in dm:
        result.append({
            'date': day.date,
            'members_count': day.members_count
        })
    return JsonResponse({'result':result})

def room_stats_view(request, room_id):
    room = Room.objects.get(id=room_id)

    # graph
    days = 30
    from_date = datetime.now() - timedelta(days=int(days))
    dm = DailyMembers.objects.filter(
        room_id=room_id,
        date__gte=from_date,
    ).order_by('date')
    points = []
    for day in dm:
        points.append({
            'x': day.date.strftime("%d-%m-%Y"),
            'y': day.members_count
        })
    labels = str([ point['x'] for point in points ])
    context = {
        'room': room,
        'points': points,
        'labels': labels,
    }

    if request.user.id:
        context['categories'] = Category.objects.order_by('name')
        context['admin'] = True

    # members delta
    current_members = dm.last().members_count
    try:
        last_week_members = dm.filter(
            date=datetime.now() - timedelta(days=7)
        ).first().members_count
    except AttributeError:
        last_week_members = 0
    try:
        last_month_members = dm.filter(
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

# FIXME optimize query and add daily/weekly/monthly stats
def list_server_stats(request, server):
    server_stats = reversed(ServerStats.objects.filter(server=server).order_by('-id')[:1800])
    points = []

    LATENCY_GROUP_SIZE = 6;
    latency_group = []
    for stat in server_stats:
        latency_group.append(stat.latency)
        if len(latency_group) == LATENCY_GROUP_SIZE:
            points.append({
                'x': stat.date.strftime("%H:%M %d-%m-%Y"),
                'y': sum(latency_group) / LATENCY_GROUP_SIZE
            })
            latency_group = []
        # points.append({
        #     'x': stat.date.strftime("%H:%M %d-%m-%Y"),
        #     'y': stat.latency
        # })
    labels = str([ point['x'] for point in points ])
    context = {
        'points': points,
        'labels': labels,
        'server': server
    }
    return render(request, 'room_stats/server_stats.html', context)

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
