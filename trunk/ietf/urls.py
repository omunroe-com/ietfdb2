# Copyright The IETF Trust 2007, 2009, All Rights Reserved

import django
from django.conf.urls.defaults import patterns, include, handler404, handler500
from django.contrib import admin

from ietf.iesg.feeds import IESGAgenda
from ietf.idtracker.feeds import DocumentComments, InLastCall
from ietf.ipr.feeds import LatestIprDisclosures
from ietf.proceedings.feeds import LatestWgProceedingsActivity
from ietf.liaisons.feeds import Liaisons

from ietf.idtracker.sitemaps import IDTrackerMap, DraftMap
from ietf.liaisons.sitemaps import LiaisonMap
from ietf.ipr.sitemaps import IPRMap
from ietf.announcements.sitemaps import NOMCOMAnnouncementsMap

from django.conf import settings

admin.autodiscover()

feeds = {
    'iesg-agenda': IESGAgenda,
    'last-call': InLastCall,
    'comments': DocumentComments,
    'ipr': LatestIprDisclosures,
    'liaison': Liaisons,
    'wg-proceedings' : LatestWgProceedingsActivity
}

sitemaps = {
    'idtracker': IDTrackerMap,
    'drafts': DraftMap,
    'liaison': LiaisonMap,
    'ipr': IPRMap,
    'nomcom-announcements': NOMCOMAnnouncementsMap,
}

urlpatterns = patterns('',
    (r'^feed/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
              { 'feed_dict': feeds}),
    (r'^sitemap.xml$', 'django.contrib.sitemaps.views.index',
              { 'sitemaps': sitemaps}),
    (r'^sitemap-(?P<section>.+).xml$', 'django.contrib.sitemaps.views.sitemap',
              {'sitemaps': sitemaps}),
    (r'^ann/', include('ietf.announcements.urls')),
    (r'^idtracker/', include('ietf.idtracker.urls')),
    (r'^drafts/', include('ietf.idindex.urls')),
    (r'^iesg/', include('ietf.iesg.urls')),
    (r'^liaison/', include('ietf.liaisons.urls')),
    (r'^list/', include('ietf.mailinglists.urls')),
    (r'^(?P<path>public)/', include('ietf.redirects.urls')),
    (r'^ipr/', include('ietf.ipr.urls')),
    (r'^meeting/', include('ietf.meeting.urls')),
    (r'^accounts/', include('ietf.ietfauth.urls')),
    (r'^doc/', include('ietf.idrfc.urls')),
    (r'^wg/', include('ietf.wginfo.urls')),
    (r'^cookies/', include('ietf.cookies.urls')),

    (r'^$', 'ietf.idrfc.views.main'),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    ('^admin/', include(admin.site.urls)),

    # Google webmaster tools verification url
    (r'^googlea30ad1dacffb5e5b.html', 'django.views.generic.simple.direct_to_template', { 'template': 'googlea30ad1dacffb5e5b.html' }),
)

if settings.SERVER_MODE in ('development', 'test'):
    urlpatterns += patterns('',
        (r'^(?P<path>(?:images|css|js)/.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
        (r'^_test500/$', lambda x: None),
	)
