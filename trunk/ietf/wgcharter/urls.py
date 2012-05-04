# Copyright The IETF Trust 2011, All Rights Reserved

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^state/$', "ietf.wgcharter.views.change_state", name='charter_change_state'),
    url(r'^(?P<option>initcharter|recharter|abandon)/$', "ietf.wgcharter.views.change_state", name='charter_startstop_process'),
    url(r'^telechat/$', "ietf.wgcharter.views.telechat_date", name='charter_telechat_date'),
    url(r'^(?P<ann>action|review)/$', "ietf.wgcharter.views.announcement_text"),
    url(r'^ballotwriteupnotes/$', "ietf.wgcharter.views.ballot_writeupnotes"),
    url(r'^approve/$', "ietf.wgcharter.views.approve", name='charter_approve'),
    url(r'^submit/$', "ietf.wgcharter.views.submit", name='charter_submit'),

)
