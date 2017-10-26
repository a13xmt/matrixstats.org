from datetime import datetime, timedelta
from django.shortcuts import render
from django.http.response import JsonResponse

from room_stats.models import Room, DailyMembers, Tag

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
    days = 30
    from_date = datetime.now() - timedelta(days=int(days)-1)
    room = Room.objects.get(id=room_id)
    dm = DailyMembers.objects.filter(
        room_id=room_id,
        date__gte=from_date,
    )
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
    return render(request, 'room_stats/room_stats.html', context)

def list_rooms(request):
    return render(request, 'room_stats/rooms.html')

def list_rooms_by_random(request):
    rooms = Room.objects.filter(members_count__gt=5).order_by('?')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

def list_rooms_by_members_count(request):
    rooms = Room.objects.filter(
        members_count__gt=5).order_by('-members_count')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

def list_rooms_with_tags(request):
    rooms = Room.objects.filter(topic__iregex=r'#').order_by('?')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

def list_rooms_with_tag(request, tag):
    rooms = Room.objects.filter(topic__iregex='#%s' % tag).order_by('?')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

def list_tags(request):
    tags = Tag.objects.all()
    context = {'tags': tags}
    return render(request, 'room_stats/tag_list.html', context)


def all_rooms_view(request):
    rooms = Room.objects.filter(members_count__gt=5).order_by('?')[:20] # order_by('-members_count')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

def list_rooms_by_lang_ru(request):
    rooms = Room.objects.filter(topic__iregex=r'[а-яА-ЯёЁ]+').order_by('?')[:20]
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

from django.contrib.postgres.search import SearchVector
def list_rooms_by_search_term(request, term):
    rooms = Room.objects.annotate(
        search=SearchVector('name', 'aliases', 'topic'),
    ).filter(search=term)
    context = {'rooms': rooms}
    return render(request, 'room_stats/rooms_list.html', context)

# Create your views here.

