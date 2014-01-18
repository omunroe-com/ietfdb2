# Copyright The IETF Trust 2011, All Rights Reserved

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^state/$', "ietf.doc.views_charter.change_state", name='charter_change_state'),
    url(r'^(?P<option>initcharter|recharter|abandon)/$', "ietf.doc.views_charter.change_state", name='charter_startstop_process'),
    url(r'^telechat/$', "ietf.doc.views_charter.telechat_date", name='charter_telechat_date'),
    url(r'^notify/$', "ietf.doc.views_charter.edit_notify", name='charter_edit_notify'),
    url(r'^ad/$', "ietf.doc.views_charter.edit_ad", name='charter_edit_ad'),
    url(r'^(?P<ann>action|review)/$', "ietf.doc.views_charter.announcement_text", name="charter_edit_announcement"),
    url(r'^ballotwriteupnotes/$', "ietf.doc.views_charter.ballot_writeupnotes"),
    url(r'^approve/$', "ietf.doc.views_charter.approve", name='charter_approve'),
    url(r'^submit/$', "ietf.doc.views_charter.submit", name='charter_submit'),
    url(r'^submit/(?P<option>initcharter|recharter)/$', "ietf.doc.views_charter.submit", name='charter_submit'), # shouldn't be here
    url(r'^withmilestones-(?P<rev>[0-9-]+).txt$', "ietf.doc.views_charter.charter_with_milestones_txt", name='charter_with_milestones_txt'),
)
