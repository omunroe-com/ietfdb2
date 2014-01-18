from django.conf.urls import patterns, url

urlpatterns = patterns('ietf.doc.views_status_change',
    url(r'^state/$',                 "change_state",   name='status_change_change_state'),
    url(r'^submit/$',                "submit",         name='status_change_submit'),
    url(r'^notices/$',               "edit_notices",   name='status_change_notices'),
    url(r'^ad/$',                    "edit_ad",        name='status_change_ad'),
    url(r'^approve/$',               "approve",        name='status_change_approve'),
    url(r'^telechat/$',              "telechat_date",  name='status_change_telechat_date'),
    url(r'^relations/$',             "edit_relations", name='status_change_relations'),
    url(r'^last-call/$',             "last_call",      name='status_change_last_call'),
)

