# Copyright The IETF Trust 2007, All Rights Reserved

# Portion Copyright (C) 2008-2009 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved. Contact: Pasi Eronen <pasi.eronen@nokia.com>
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
# 
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
# 
#  * Neither the name of the Nokia Corporation and/or its
#    subsidiary(-ies) nor the names of its contributors may be used
#    to endorse or promote products derived from this software
#    without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.conf.urls import patterns
from django.views.generic import RedirectView
from django.conf import settings

urlpatterns = patterns('',
    (r'^telechat/.*$', RedirectView.as_view(url='https://www.ietf.org/iesg/minutes.html', permanent=True)),
    (r'^ann/(?:ind|new|prev)/$', RedirectView.as_view(url="/iesg/decisions/", permanent=True)),
    (r'^telechatdates/$', RedirectView.as_view(url='/admin/iesg/telechatdate/', permanent=True)),

    (r'^decisions/(?:(?P<year>[0-9]{4})/)?$', "ietf.iesg.views.review_decisions"),
    (r'^agenda/(?:%(date)s/)?$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda"),
    (r'^agenda/(?:%(date)s/)?agenda.txt$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda_txt"),
    (r'^agenda/(?:%(date)s/)?agenda.json$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda_json"),
    (r'^agenda/(?:%(date)s/)?scribe_template.html$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda_scribe_template"),
    (r'^agenda/(?:%(date)s/)?moderator_package.html$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda_moderator_package"),
    (r'^agenda/(?:%(date)s/)?agenda_package.txt$' % settings.URL_REGEXPS, "ietf.iesg.views.agenda_package"),

    (r'^agenda/documents.txt$', "ietf.iesg.views.agenda_documents_txt"),
    (r'^agenda/documents/$', "ietf.iesg.views.agenda_documents"),
    (r'^agenda/telechat-(?:%(date)s-)?docs.tgz' % settings.URL_REGEXPS, "ietf.iesg.views.telechat_docs_tarfile"),
    (r'^discusses/$', "ietf.iesg.views.discusses"),
    (r'^milestones/$', "ietf.iesg.views.milestones_needing_review"),
    (r'^photos/$', "ietf.iesg.views.photos"),
)