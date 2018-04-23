"""matrix_stats URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from room_stats import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin/room/(?P<room_id>\![a-zA-Z0-9\.\:\_\-]*)/setcategory/(?P<category_id>[0-9]*)', views.set_room_category),
    url(r'^admin/room/(?P<room_id>\![a-zA-Z0-9\.\:\_\-]*)/setcategories/', views.set_room_categories),
    url(r'^admin/update_server_recaptcha/', views.set_server_recaptcha),

    url(r'^stats/(?P<room_id>\![a-zA-Z0-9\.\:\_]*)/',
        views.get_daily_members_stats
    ),
    url(r'^room/(?P<room_id>\![a-zA-Z0-9\.\:\_\-]*)$',
        views.room_stats_view, name='room-stats',
    ),
    url(r'^$', views.list_rooms),
    url(r'^category/(?P<category_name>[a-zA-Z0-9\.\s]+)/', views.list_rooms_by_category, name='rooms-by-category'),

    url(r'^new/1d/$', views.list_new_rooms, kwargs={'delta': 1}, name='new-1d'),
    url(r'^new/3d/$', views.list_new_rooms, kwargs={'delta': 3}, name='new-3d'),
    url(r'^new/weekly/$', views.list_new_rooms, kwargs={'delta': 7}, name='new-weekly'),
    url(r'^new/monthly/$', views.list_new_rooms, kwargs={'delta': 30}, name='new-monthly'),

    url(r'^top/abs/weekly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 7, 'rating': 'absolute'}, name='top-abs-weekly'),
    url(r'^top/abs/monthly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 30, 'rating': 'absolute'}, name='top-abs-monthly'),
    url(r'^top/abs/quarterly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 90, 'rating': 'absolute'}, name='top-abs-quarterly'),
    url(r'^top/rel/weekly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 7, 'rating': 'relative'}, name='top-rel-weekly'),
    url(r'^top/rel/monthly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 30, 'rating': 'relative'}, name='top-rel-monthly'),
    url(r'^top/rel/quarterly/$', views.list_most_joinable_rooms, kwargs={
        'delta': 90, 'rating': 'relative'}, name='top-rel-quarterly'),

    url(r'^promoted/small/$', views.list_promoted_rooms, kwargs={
        'size': 's' }, name='promoted-small'),
    url(r'^promoted/medium/$', views.list_promoted_rooms, kwargs={
        'size': 'm' }, name='promoted-medium'),


    url(r'^simple/$', views.index_simple, name='simple'),
    url(r'^ratings/$', views.list_ratings, name='ratings'),
    url(r'^categories/$', views.list_categories, name='categories'),
    url(r'^promote/$', views.promote_room, name='promote'),
    url(r'^about/$', views.about, name='about'),
    url(r'^bot/$', views.bot, name='bot'),
    url(r'^homeservers/$', views.list_homeservers, name='homeservers'),

    url(r'^rooms/top/$', views.list_rooms_by_members_count),

    url(r'^rooms/random/', views.list_rooms_by_random, name='random'),
    url(r'^rooms/public/', views.list_public_rooms, name='public'),
    url(r'^rooms/cyrillic/', views.list_rooms_by_lang_ru, name='cyrillic'),
    url(r'^rooms/tags/', views.list_tags, name='tags'),
    url(r'^rooms/tag/(?P<tag>\w+)/', views.list_rooms_with_tag, name='rooms-with-tag'),
    url(r'^rooms/homeserver/(?P<homeserver>[a-zA-Z0-9\.]+)/', views.rooms_by_homeserver, name='rooms-by-homeserver'),

    url(r'^rooms/search/(?P<term>\w+)/', views.list_rooms_by_search_term, name='rooms-with-search-term'),


]
