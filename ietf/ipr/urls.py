# Copyright The IETF Trust 2007, All Rights Reserved

from django.conf.urls.defaults import patterns
from ietf.ipr import models, views, new, search

urlpatterns = patterns('',
     (r'^$', views.showlist),
     (r'^about/$', views.default),
     (r'^ipr-(?P<ipr_id>\d+)/$', views.show),
     (r'^update/$', views.updatelist),
     (r'^update/(?P<ipr_id>\d+)/$', new.update),
     (r'^new-(?P<type>(specific|generic|third-party))/$', new.new),
     (r'^search/$', search.search),     
)

queryset = models.IprDetail.objects.filter(status__in=[1,3])
archive = {'queryset':queryset, 'date_field': 'submitted_date', 'allow_empty':True }

urlpatterns += patterns('django.views.generic.date_based',
	(r'^by-date/$', 'archive_index', archive),
	(r'^(?P<year>\d{4})/$', 'archive_year', archive),
	(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'archive_month', archive),
)


