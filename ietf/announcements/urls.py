# Copyright The IETF Trust 2007, All Rights Reserved

from django.conf.urls.defaults import patterns
from ietf.announcements.models import Announcement

nomcom_dict = {
    'queryset': Announcement.objects.all().filter(nomcom=True)
}

urlpatterns = patterns('',
    (r'^nomcom/(?P<object_id>\d+)/$', 'django.views.generic.list_detail.object_detail', nomcom_dict)
)
