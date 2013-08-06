from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('ietf.dbtemplate.views',
    url(r'^(?P<acronym>[\w.@+-]+)/$', 'template_list', name='template_list'),
    url(r'^(?P<acronym>[\w.@+-]+)/(?P<template_id>[\d]+)/$', 'template_edit', name='template_edit'),
)
