from django.conf.urls import patterns
from ietf.person import ajax

urlpatterns = patterns('',
        (r'^search/$', "ietf.person.views.ajax_search_emails", None, 'ajax_search_emails'),
        (r'^(?P<personid>[a-z0-9]+).json$', ajax.person_json),
)
