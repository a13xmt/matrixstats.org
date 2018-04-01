from django.contrib import admin
from django.utils.safestring import mark_safe

from room_stats.models import Room
from room_stats.models import Tag
from room_stats.models import DailyMembers
from room_stats.models import Category
from room_stats.models import PromotionRequest
from django.template.loader import render_to_string

class RoomAdmin(admin.ModelAdmin):
    all_categories = Category.objects.order_by('name')
    def category_widget(self, obj):
        context = {
            'room': obj,
            'categories': RoomAdmin.all_categories
        }
        return render_to_string('admin/widgets/category_widget.html', context)
    category_widget.short_description = "category"

    def categories_widget(self, obj):
        context = {
            'room': obj,
            # FIXME huge performance drop in exchange for realtime categories
            'categories': Category.objects.order_by('name')
        }
        return render_to_string('admin/widgets/categories_widget.html', context)
    categories_widget.short_description = "categories"

    def logo(self, obj):
        if obj.avatar_url is '':
            return ""
        path = obj.get_logo_url()
        img = "<img src='%s' style='height: 50px; width: 50px;'/>" % (
            path,
        )
        return mark_safe(img)
    logo.short_description = "logo"


    list_display = ('logo', 'members_count', 'name', 'topic', 'category_widget', 'categories_widget', 'is_public_readable', 'is_guest_writeable', 'updated_at')
    ordering = ('-members_count', )

    def get_queryset(self, request):
        queryset = super(RoomAdmin, self).get_queryset(request)
        return queryset.prefetch_related('categories')

    class Media:
        js = (
            'vendor/jquery-3.3.1.min.js',
            'vendor/jquery-ui.min.js',
            'vendor/jquery.multiselect.min.js',
            'vendor/toastr.min.js',
            'js/category_widget.js',
        )
        css = {
            'all': ('vendor/toastr.min.css', 'vendor/jquery.multiselect.css', 'vendor/jquery-ui.min.css')
        }


class DailyMembersAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'date','members_count')

class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')

class CategoryAdmin(admin.ModelAdmin):
    def image_preview(self, obj):
        style = "max-width: 100px;"
        return mark_safe("<img src='/static/%s' style='%s'/>" %  (obj.image.name, style))
    image_preview.short_description = 'Image'

    def rooms_count(self, obj):
        return obj.room_set.count()

    list_display = ('image_preview', 'name', 'rooms_count')

class PromotionRequestAdmin(admin.ModelAdmin):
    list_display = ('room', 'description', 'size', 'active', 'created_at', 'remove_at')

admin.site.register(Room, RoomAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(DailyMembers, DailyMembersAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(PromotionRequest, PromotionRequestAdmin)

