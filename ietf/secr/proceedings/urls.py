from django.conf.urls import patterns, url

urlpatterns = patterns('ietf.secr.proceedings.views',
    url(r'^$', 'main', name='proceedings'),
    url(r'^ajax/generate-proceedings/(?P<meeting_num>\d{1,3})/$', 'ajax_generate_proceedings', name='proceedings_ajax_generate_proceedings'),
    url(r'^ajax/order-slide/$', 'ajax_order_slide', name='proceedings_ajax_order_slide'),
    # special offline URL for testing proceedings build
    url(r'^build/(?P<meeting_num>\d{1,3}|interim-\d{4}-[A-Za-z0-9_\-\+]+)/(?P<acronym>[A-Za-z0-9_\-\+]+)/$',
        'build', name='proceedings_build'),
    url(r'^delete/(?P<slide_id>[A-Za-z0-9._\-\+]+)/$', 'delete_material', name='proceedings_delete_material'),
    url(r'^edit-slide/(?P<slide_id>[A-Za-z0-9._\-\+]+)/$', 'edit_slide', name='proceedings_edit_slide'),
    url(r'^move-slide/(?P<slide_id>[A-Za-z0-9._\-\+]+)/(?P<direction>(up|down))/$',
        'move_slide', name='proceedings_move_slide'),
    url(r'^process-pdfs/(?P<meeting_num>\d{1,3})/$', 'process_pdfs', name='proceedings_process_pdfs'),
    url(r'^progress-report/(?P<meeting_num>\d{1,3})/$', 'progress_report', name='proceedings_progress_report'),
    url(r'^replace-slide/(?P<slide_id>[A-Za-z0-9._\-\+]+)/$', 'replace_slide', name='proceedings_replace_slide'),
    url(r'^(?P<meeting_num>\d{1,3})/$', 'select', name='proceedings_select'),
    url(r'^(?P<meeting_num>\d{1,3})/recording/$', 'recording', name='proceedings_recording'),
    url(r'^(?P<meeting_num>\d{1,3})/recording/edit/(?P<name>[A-Za-z0-9_\-\+]+)$', 'recording_edit', name='proceedings_recording_edit'),
    # NOTE: we have two entries here which both map to upload_unified, passing session_id or acronym
    url(r'^(?P<meeting_num>\d{1,3}|interim-\d{4}-[A-Za-z0-9_\-\+]+)/(?P<session_id>\d{1,6})/$',
        'upload_unified', name='proceedings_upload_unified'),
    url(r'^(?P<meeting_num>\d{1,3}|interim-\d{4}-[A-Za-z0-9_\-\+]+)/(?P<acronym>[A-Za-z0-9_\-\+]+)/$',
        'upload_unified', name='proceedings_upload_unified'),
    # interim stuff
    url(r'^interim/$', 'select_interim', name='proceedings_select_interim'),
    url(r'^interim/(?P<meeting_num>interim-\d{4}-[A-Za-z0-9_\-\+]+)/delete/$', 'delete_interim_meeting',
        name='proceedings_delete_interim_meeting'),
    url(r'^interim/(?P<acronym>[A-Za-z0-9_\-\+]+)/$', 'interim', name='proceedings_interim'),
)
