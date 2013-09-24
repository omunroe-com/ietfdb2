from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from ietf.nomcom.forms import EditChairForm, EditChairFormPreview, \
                              EditMembersForm, EditMembersFormPreview

urlpatterns = patterns('ietf.nomcom.views',
    url(r'^$', 'index'),
    url(r'^(?P<year>\d{4})/private/$', 'private_index', name='nomcom_private_index'),
    url(r'^(?P<year>\d{4})/private/key/$', 'private_key', name='nomcom_private_key'),
    url(r'^(?P<year>\d{4})/private/nominate/$', 'private_nominate', name='nomcom_private_nominate'),
    url(r'^(?P<year>\d{4})/private/feedback/$', 'private_feedback', name='nomcom_private_feedback'),
    url(r'^(?P<year>\d{4})/private/feedback-email/$', 'private_feedback_email', name='nomcom_private_feedback_email'),
    url(r'^(?P<year>\d{4})/private/questionnaire-response/$', 'private_questionnaire', name='nomcom_private_questionnaire'),
    url(r'^(?P<year>\d{4})/private/view-feedback/$', 'view_feedback', name='nomcom_view_feedback'),
    url(r'^(?P<year>\d{4})/private/view-feedback/unrelated/$', 'view_feedback_unrelated', name='nomcom_view_feedback_unrelated'),
    url(r'^(?P<year>\d{4})/private/view-feedback/pending/$', 'view_feedback_pending', name='nomcom_view_feedback_pending'),
    url(r'^(?P<year>\d{4})/private/view-feedback/nominee/(?P<nominee_id>\d+)$', 'view_feedback_nominee', name='nomcom_view_feedback_nominee'),
    url(r'^(?P<year>\d{4})/private/edit/nominee/(?P<nominee_id>\d+)$', 'edit_nominee', name='nomcom_edit_nominee'),
    url(r'^(?P<year>\d{4})/private/merge/$', 'private_merge', name='nomcom_private_merge'),
    url(r'^(?P<year>\d{4})/private/send-reminder-mail/$', 'send_reminder_mail', name='nomcom_send_reminder_mail'),
    url(r'^(?P<year>\d{4})/private/edit-members/$', EditMembersFormPreview(EditMembersForm), name='nomcom_edit_members'),
    url(r'^(?P<year>\d{4})/private/edit-chair/$', EditChairFormPreview(EditChairForm), name='nomcom_edit_chair'),
    url(r'^(?P<year>\d{4})/private/edit-nomcom/$', 'edit_nomcom', name='nomcom_edit_nomcom'),
    url(r'^(?P<year>\d{4})/private/delete-nomcom/$', 'delete_nomcom', name='nomcom_delete_nomcom'),
    url(r'^deleted/$', direct_to_template, {'template': 'nomcom/deleted.html'}, name='nomcom_deleted'),
    url(r'^(?P<year>\d{4})/private/chair/templates/$', 'list_templates', name='nomcom_list_templates'),
    url(r'^(?P<year>\d{4})/private/chair/templates/(?P<template_id>\d+)/$', 'edit_template', name='nomcom_edit_template'),
    url(r'^(?P<year>\d{4})/private/chair/position/$', 'list_positions', name='nomcom_list_positions'),
    url(r'^(?P<year>\d{4})/private/chair/position/add/$', 'edit_position', name='nomcom_add_position'),
    url(r'^(?P<year>\d{4})/private/chair/position/(?P<position_id>\d+)/$', 'edit_position', name='nomcom_edit_position'),
    url(r'^(?P<year>\d{4})/private/chair/position/(?P<position_id>\d+)/remove/$', 'remove_position', name='nomcom_remove_position'),

    url(r'^(?P<year>\d{4})/$', 'year_index', name='nomcom_year_index'),
    url(r'^(?P<year>\d{4})/requirements/$', 'requirements', name='nomcom_requirements'),
    url(r'^(?P<year>\d{4})/expertise/$', 'requirements', name='nomcom_requirements'),
    url(r'^(?P<year>\d{4})/questionnaires/$', 'questionnaires', name='nomcom_questionnaires'),
    url(r'^(?P<year>\d{4})/feedback/$', 'public_feedback', name='nomcom_public_feedback'),
    url(r'^(?P<year>\d{4})/nominate/$', 'public_nominate', name='nomcom_public_nominate'),
    url(r'^(?P<year>\d{4})/process-nomination-status/(?P<nominee_position_id>\d+)/(?P<state>[\w]+)/(?P<date>[\d]+)/(?P<hash>[a-f0-9]+)/$', 'process_nomination_status', name='nomcom_process_nomination_status'),
    url(r'^ajax/position-text/(?P<position_id>\d+)/$', 'ajax_position_text', name='nomcom_ajax_position_text'),

)
