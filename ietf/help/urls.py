from django.conf.urls import url

urlpatterns = [
    url(r'^state/(?P<doc>[-\w]+)/(?P<type>[-\w]+)/?$', 'ietf.help.views.state'),
    url(r'^state/(?P<doc>[-\w]+)/?$', 'ietf.help.views.state'),
    url(r'^state/?$', 'ietf.help.views.state_index'),
]

