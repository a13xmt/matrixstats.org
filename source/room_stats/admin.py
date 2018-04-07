from django.contrib import admin
from django.utils.safestring import mark_safe

from room_stats.models import Room
from room_stats.models import Tag
from room_stats.models import DailyMembers
from room_stats.models import Category
from room_stats.models import PromotionRequest
from room_stats.models import Server
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


import json
class ServerAdmin(admin.ModelAdmin):

    def prettify_data(self, obj):
        return mark_safe("<pre style='max-width: 500px; overflow: hidden;'>%s</pre>" % json.dumps(obj.data, indent=4, sort_keys=True))
    prettify_data.short_description = "data (prettifyed)"

    def render_captcha(self, obj):
        server_captcha_key = obj.data.get("params", {}).get("m.login.recaptcha", {}).get("public_key", None)
        # captcha should be rendered only if it required
        # so we need to ensure that server registration process
        # was stuck at captcha point
        reg_active_stage_index = obj.data.get("reg_active_stage_index")
        reg_chosen_flow = obj.data.get("reg_chosen_flow")
        reg_active_stage_progress = obj.data.get("reg_active_stage_progress")
        recaptcha_stage_is_active = False
        if reg_chosen_flow and reg_active_stage_index is not None:
            recaptcha_stage_is_active = reg_chosen_flow[reg_active_stage_index] == "m.login.recaptcha"
        user_action_required = reg_active_stage_progress == "USER_ACTION_REQUIRED"
        html = ""
        if user_action_required and recaptcha_stage_is_active and server_captcha_key:
            context = {
                'server_id': obj.id,
                'server_captcha_key': server_captcha_key
            }
            html = render_to_string('admin/widgets/server_recaptcha.html', context)
        return mark_safe(html)
    render_captcha.short_description = "recaptcha"

    list_display = ('hostname', 'login', 'status', 'prettify_data', 'last_response_data', 'last_response_code', 'render_captcha' )
    class Media:
        js = (
            "https://www.google.com/recaptcha/api.js?onload=onloadCallback",
            "vendor/jquery-3.3.1.min.js",
            'vendor/toastr.min.js',
            "js/admin_recaptcha_widget.js",
        )
        css = {
            'all': ('vendor/toastr.min.css',)
        }


admin.site.register(Room, RoomAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(DailyMembers, DailyMembersAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(PromotionRequest, PromotionRequestAdmin)
admin.site.register(Server, ServerAdmin)

