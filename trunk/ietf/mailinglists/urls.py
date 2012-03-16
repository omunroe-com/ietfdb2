# Copyright The IETF Trust 2007, All Rights Reserved

from django.conf.urls.defaults import patterns
from ietf.idtracker.models import IETFWG

http_archive_wg_queryset = IETFWG.objects.filter(email_archive__startswith='http')

urlpatterns = patterns('django.views.generic.list_detail',
     (r'^wg/$', 'object_list', { 'queryset': http_archive_wg_queryset, 'template_name': 'mailinglists/wgwebmail_list.html' }),
)
urlpatterns += patterns('',
     (r'^nonwg/$', 'django.views.generic.simple.redirect_to', { 'url': 'http://www.ietf.org/list/nonwg.html'}),
     (r'^nonwg/update/$', 'django.views.generic.simple.redirect_to', { 'url': 'http://www.ietf.org/list/nonwg.html'}),
     (r'^request/$', 'django.views.generic.simple.redirect_to', { 'url': 'http://www.ietf.org/list/request.html' }),
)
