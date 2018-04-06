from datetime import datetime, timedelta
from django.utils import timezone
from django.templatetags.static import static
from django.contrib.postgres.fields import JSONField

import re

from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='category/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "categories"

class CategoryRequest(models.Model):
    room_id = models.CharField(max_length=255)
    existing_category = models.ForeignKey(Category, blank=True, null=True, on_delete=models.SET_NULL)
    proposed_category = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sender_ip = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)

class Room(models.Model):
    id = models.CharField(max_length=511, primary_key=True)
    name = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, blank=True, null=True, on_delete=models.SET_NULL, related_name='%(class)s_old')
    categories = models.ManyToManyField(Category, blank=True)
    aliases = models.TextField(blank=True, null=True)
    topic = models.TextField(blank=True, null=True)
    members_count = models.IntegerField()
    avatar_url = models.TextField(blank=True, null=True)
    is_public_readable = models.BooleanField()
    is_guest_writeable = models.BooleanField()
    inactive = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return "(%s) %s" % (self.members_count, self.name)

    def get_short_name(self, max_len=20):
        if len(self.name) < 1 :
            return self.aliases.split(',')[0].split(':')[0]
        elif len(self.name) < max_len:
            return self.name
        else:
            t = self.name.split(':')[0].split('/')[0].split("|")[0].split(',')[0].split('—')[0]
            tw = t[0:max_len].split(' ')
            return ' '.join(tw[:-1]) if len(tw) > 1 else tw[0]
            # return ' '.join(self.name[:max_len+1].split(' ')[0:-1]) + '...'

    def get_alias(self):
        return self.aliases.split(', ')[0]

    def get_logo_url(self):
        if self.avatar_url:
            return self.avatar_url
        else:
            return static('img/no-logo.png')

    def topic_split(self):
        return re.sub(r" [\|•]{1,2} ", "\n\n", self.topic)


class PromotionRequest(models.Model):
    SIZE_CHOICES = (('s', 'small'), ('m', 'medium'))
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    description = models.TextField(max_length=1024, blank=True, null=True)
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    remove_at = models.DateTimeField()

class DailyMembers(models.Model):
    id = models.CharField(max_length=511, primary_key=True, editable=False)
    room_id = models.CharField(max_length=511, db_index=True)
    members_count = models.IntegerField()
    date = models.DateField(default=datetime.now, editable=False, db_index=True)#auto_now=True)

    def save(self):
        self.id = "%s-%s" % ( self.room_id, self.date.strftime("%Y%m%d"))
        super(DailyMembers, self).save()

    class Meta:
        verbose_name_plural = "Daily Members"

class Tag(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    rooms = models.ManyToManyField(Room)
    updated_at = models.DateTimeField(auto_now=True)

class Server(models.Model):
    STATUS_CHOICES = (
        ('a', 'assumed'),
        ('c', 'confirmed'),
        ('n', 'not_exist'),
        ('p', 'captcha_required'),
        ('r', 'registered'),
        ('u', 'unknown'),
    )
    hostname = models.CharField(max_length=255)
    port = models.IntegerField(default=80)
    login = models.CharField(max_length=127, blank=True, null=True)
    password = models.CharField(max_length=127, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='a')
    data = JSONField(default=dict, blank=True, null=True)
    last_response_data = JSONField(default=dict, blank=True, null=True)
    last_response_code = models.IntegerField(blank=True, null=True)

    def api(self, path, suffix="/_matrix/client/r0"):
        result = "%s%s%s" % (self.hostname, suffix, path)
        print(result)
        return result
