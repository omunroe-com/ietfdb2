from django.conf.urls import patterns
from django.views.generic import RedirectView

from ietf.doc.feeds import DocumentChangesFeed, InLastCallFeed
from ietf.wginfo.feeds import GroupChangesFeed
from ietf.iesg.feeds import IESGAgendaFeed
from ietf.ipr.feeds import LatestIprDisclosuresFeed
from ietf.liaisons.feeds import LiaisonStatementsFeed
from ietf.meeting.feeds import LatestMeetingMaterialFeed

urlpatterns = patterns(
    '',
    (r'^comments/(?P<remainder>.*)/$', RedirectView.as_view(url='/feed/document-changes/%(remainder)s/')),
    (r'^document-changes/(?P<name>[A-Za-z0-9._+-]+)/$', DocumentChangesFeed()),
    (r'^last-call/$', InLastCallFeed()),
    (r'^group-changes/(?P<acronym>[a-zA-Z0-9-]+)/$', GroupChangesFeed()),
    (r'^iesg-agenda/$', IESGAgendaFeed()),
    (r'^ipr/$', LatestIprDisclosuresFeed()),
    (r'^liaison/(?P<kind>recent|from|to|subject)/(?:(?P<search>[^/]+)/)?$', LiaisonStatementsFeed()),
    (r'^wg-proceedings/$', LatestMeetingMaterialFeed()),
)
