from django.conf.urls import url
from django.conf import settings
from ietf.meeting.views import OldUploadRedirect

urlpatterns = [
    url(r'^$', 'ietf.secr.proceedings.views.main', name='proceedings'),
    url(r'^ajax/generate-proceedings/(?P<meeting_num>\d{1,3})/$', 'ietf.secr.proceedings.views.ajax_generate_proceedings', name='proceedings_ajax_generate_proceedings'),
    # special offline URL for testing proceedings build
    url(r'^process-pdfs/(?P<meeting_num>\d{1,3})/$', 'ietf.secr.proceedings.views.process_pdfs', name='proceedings_process_pdfs'),
    url(r'^progress-report/(?P<meeting_num>\d{1,3})/$', 'ietf.secr.proceedings.views.progress_report', name='proceedings_progress_report'),
    url(r'^(?P<meeting_num>\d{1,3})/$', 'ietf.secr.proceedings.views.select', name='proceedings_select'),
    url(r'^(?P<meeting_num>\d{1,3})/recording/$', 'ietf.secr.proceedings.views.recording', name='proceedings_recording'),
    url(r'^(?P<meeting_num>\d{1,3})/recording/edit/(?P<name>[A-Za-z0-9_\-\+]+)$', 'ietf.secr.proceedings.views.recording_edit', name='proceedings_recording_edit'),
    url(r'^(?P<num>\d{1,3}|interim-\d{4}-[A-Za-z0-9_\-\+]+)/%(acronym)s/$' % settings.URL_REGEXPS,
         OldUploadRedirect.as_view(permanent=True)),
]
