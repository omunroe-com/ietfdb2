
from ietf.secr.drafts import views
from ietf.utils.urls import url

urlpatterns = [
    url(r'^$', views.search),
    url(r'^approvals/$', views.approvals),
    url(r'^dates/$', views.dates),
    url(r'^nudge-report/$', views.nudge_report),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/$', views.view),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/abstract/$', views.abstract),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/authors/$', views.authors),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/author_delete/(?P<oid>\d{1,6})$', views.author_delete),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/confirm/$', views.confirm),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/do_action/$', views.do_action),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/edit/$', views.edit),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/extend/$', views.extend),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/email/$', views.email),
    url(r'^(?P<id>[A-Za-z0-9._\-\+]+)/withdraw/$', views.withdraw),
]
