# Copyright (C) 2009-2010 Nokia Corporation and/or its subsidiary(-ies).
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

from ietf.idtracker.models import InternetDraft, IDInternal, BallotInfo, IESGDiscuss, IESGLogin, DocumentComment, Acronym, IDState
from ietf.idrfc.models import RfcEditorQueue
from ietf.ipr.models import IprRfc, IprDraft, IprDetail
from ietf.doc.models import BallotDocEvent

import re
from datetime import date
from django.utils import simplejson as json
from django.db.models import Q
from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
import types
import debug

BALLOT_ACTIVE_STATES = ['In Last Call',
                        'Waiting for Writeup',
                        'Waiting for AD Go-Ahead',
                        'IESG Evaluation',
                        'IESG Evaluation - Defer']

def jsonify_helper(obj, keys):
    result = {}
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if callable(v):
                v = v()
            if v == None:
                pass
            elif isinstance(v, (types.StringType, types.IntType, types.BooleanType, types.LongType, types.ListType, types.UnicodeType)):
                result[k] = v
            elif isinstance(v, date):
                result[k] = str(v)
            else:
                result[k] = 'Unknown type '+str(type(v))
    return result

# Wrappers to make writing templates less painful

# ---------------------------------------------------------------------------

class IdWrapper:
    _draft = None
    _idinternal = None

    is_id_wrapper = True
    is_rfc_wrapper = False

    draft_name = None
    # Active/Expired/RFC/Withdrawn by Submitter/Replaced/Withdrawn by IETF
    draft_status = None
    # Revision is sometimes incorrect (+1 too large) if status != Active
    latest_revision = None
    # Set if and only if draft_status is "RFC"
    rfc_number = None          
    title = None
    tracker_id = None
    publication_date = None
    ietf_process = None
    
    def __init__(self, draft):
        self.id = self
        if isinstance(draft, IDInternal) and not settings.USE_DB_REDESIGN_PROXY_CLASSES:
            self._idinternal = draft
            self._draft = self._idinternal.draft
        else:
            self._draft = draft
            if draft.idinternal:
                self._idinternal = draft.idinternal
        if self._idinternal:
            self.ietf_process = IetfProcessData(self._idinternal)

        self.draft_name = self._draft.filename
        self.draft_status = str(self._draft.status)
        if self.draft_status == "RFC":
            if self._draft.rfc_number:
                self.rfc_number = self._draft.rfc_number
            else:
                # Handle incorrect database entries
                self.draft_status = "Expired"
        self.latest_revision = self._draft.revision_display()
        self.title = self._draft.title
        self.tracker_id = self._draft.id_document_tag
        self.resurrect_requested_by = self._idinternal.resurrect_requested_by if self._idinternal else None
        self.publication_date = self._draft.revision_date
        if not self.publication_date:
            # should never happen -- but unfortunately it does. Return an
            # obviously bogus date
            self.publication_date = date(1990,1,1)

    def rfc_editor_state(self):
        if settings.USE_DB_REDESIGN_PROXY_CLASSES:
            s = self._draft.get_state("draft-rfceditor")
            if s:
                # extract possible extra states
                tags = self._draft.tags.filter(slug__in=("iana-crd", "ref", "missref"))
                return " ".join([s.name] + [t.slug.replace("-crd", "").upper() for t in tags])
            else:
                return None
        
        try:
            qs = self._draft.rfc_editor_queue_state
            return qs.state
        except RfcEditorQueue.DoesNotExist:
            pass
        return None

    def replaced_by(self):
        try:
            if self._draft.replaced_by:
                return [self._draft.replaced_by.filename]
        except InternetDraft.DoesNotExist:
            pass
        return None
    def replaces(self):
        r = [str(r.filename) for r in self._draft.replaces_set.all()]
        if len(r) > 0:
            return r
        else:
            return None
    def in_ietf_process(self):
        return self.ietf_process != None
    
    def submission(self):
        
        if self._draft.stream_id != u'ietf':
            return self._draft.stream

        if self._draft.group_id == Acronym.INDIVIDUAL_SUBMITTER:
            return "Individual"

        if self._draft.group and self._draft.group.type_id == "area":
            return u"Individual in %s area" % self._draft.group.acronym

        a = self.group_acronym()
        if a:
            if self._draft.stream_id == "ietf" and self._draft.get_state_slug("draft-stream-ietf") == "c-adopt":
                return "candidate for <a href='/wg/%s/'>%s WG</a>" % (a, a)

            return "<a href='/wg/%s/'>%s WG</a>" % (a, a)

        return ""
    submission.allow_tags = True
        
    def search_archive(self):

        if self._idinternal and self._idinternal.stream in ("IRTF","ISE"):
            return "www.ietf.org/mail-archive/web/"

        if self._draft.group_id == Acronym.INDIVIDUAL_SUBMITTER or (settings.USE_DB_REDESIGN_PROXY_CLASSES and self._draft.group.type_id == "area"):
            return "www.ietf.org/mail-archive/web/"
        
        a = self._draft.group_ml_archive()
        if a:
            return a

        return ""

    def file_types(self):
        return self._draft.file_type.split(",")

    def group_acronym(self):
        if self._draft.group_id != 0 and self._draft.group != None and str(self._draft.group) != "none":
            if settings.USE_DB_REDESIGN_PROXY_CLASSES and self._draft.group.type_id == "area":
                return None
            return str(self._draft.group)
        else:
            return None
   
    # TODO: Returning integers here isn't nice
    # 0=Unknown, 1=IETF, 2=IAB, 3=IRTF, 4=Independent
    def stream_id(self):
        if self.draft_name.startswith("draft-iab-"):
            return 2
        elif self.draft_name.startswith("draft-irtf-"):
            return 3
        elif self._idinternal:
            if self._idinternal.stream == "ISE":
                return 4
            else:
                return 1
        elif self.group_acronym():
            return 1
        else:
            return 0

    def draft_name_and_revision(self):
        return self.draft_name+"-"+self.latest_revision

    def friendly_state(self):
        if self.draft_status == "RFC":
            return "<a href=\"%s\">RFC %d</a>" % (reverse('doc_view', args=['rfc%d' % self.rfc_number]), self.rfc_number)
        elif self.draft_status == "Replaced":
            rs = self.replaced_by()
            if rs:
                return "Replaced by <a href=\"%s\">%s</a>" % (reverse('doc_view', args=[rs[0]]),rs[0], ) 
            else:
                return "Replaced"
        elif self.draft_status == "Active":
            if self.in_ietf_process():
                if self.ietf_process.main_state == "Dead":
                    # Many drafts in "Dead" state are not dead; they're
                    # just not currently under IESG processing. Show
                    # them as "I-D Exists (IESG: Dead)" instead...
                    return "I-D Exists (IESG: "+self.ietf_process.state+")"
                elif self.ietf_process.main_state == "In Last Call":
                    return self.ietf_process.state + " (ends "+str(self._idinternal.document().lc_expiration_date)+")"
                else:
                    return self.ietf_process.state
            else:
                return "I-D Exists"
        else:
            if self.in_ietf_process() and self.ietf_process.main_state == "Dead":
                return self.draft_status+" (IESG: "+self.ietf_process.state+")"
            # Expired/Withdrawn by Submitter/IETF
            return self.draft_status

    def abstract(self):
        return self._draft.clean_abstract()

    # TODO: ugly hack
    def authors(self):
        return self._draft.authors

    def expected_expiration_date(self):
        if self.draft_status == "Active" and self._draft.can_expire():
            return self._draft.expiration()
        else:
            return None

    def ad_name(self):
        if self.in_ietf_process():
            return self.ietf_process.ad_name()
        else:
            return None

    def get_absolute_url(self):
        return "/doc/"+self.draft_name+"/"
    def displayname_with_link(self):
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.draft_name_and_revision())

    def to_json(self):
        result = jsonify_helper(self, ['draft_name', 'draft_status', 'latest_revision', 'rfc_number', 'title', 'tracker_id', 'publication_date','rfc_editor_state', 'replaced_by', 'replaces', 'in_ietf_process', 'file_types', 'group_acronym', 'stream_id','friendly_state', 'abstract', 'ad_name'])
        if self.in_ietf_process():
            result['ietf_process'] = self.ietf_process.dict()
        return json.dumps(result, indent=2)

# ---------------------------------------------------------------------------

class RfcWrapper:
    _rfc = None
    _rfcindex = None
    _idinternal = None

    is_id_wrapper = False
    is_rfc_wrapper = True

    rfc_number = None
    title = None
    publication_date = None
    maturity_level = None
    ietf_process = None
    draft_name = None
    
    def __init__(self, rfcindex, rfc=None, idinternal=None):
        self._rfcindex = rfcindex
        self._rfc = rfc
        self._idinternal = idinternal
        self.rfc = self

        if not self._idinternal:
            if settings.USE_DB_REDESIGN_PROXY_CLASSES:
                pub = rfcindex.rfc_published_date
                started = rfcindex.started_iesg_process if hasattr(rfcindex, 'started_iesg_process') else rfcindex.latest_event(type="started_iesg_process")
                if pub and started and pub < started.time.date():
                    self._idinternal = rfcindex
            else:
                try:
                    self._idinternal = IDInternal.objects.get(rfc_flag=1, draft=self._rfcindex.rfc_number)
                except IDInternal.DoesNotExist:
                    pass
            
        if self._idinternal:
            self.ietf_process = IetfProcessData(self._idinternal)

        self.rfc_number = self._rfcindex.rfc_number
        self.title = self._rfcindex.title
        self.publication_date = self._rfcindex.rfc_published_date
        self.maturity_level = self._rfcindex.current_status
        if not self.maturity_level:
            self.maturity_level = "Unknown"

        if settings.USE_DB_REDESIGN_PROXY_CLASSES:
            if not rfcindex.name.startswith('rfc'):
                self.draft_name = rfcindex.name
            return # we've already done the lookup while importing so skip the rest

        ids = InternetDraft.objects.filter(rfc_number=self.rfc_number)
        if len(ids) >= 1:
            self.draft_name = ids[0].filename
        elif self._rfcindex and self._rfcindex.draft:
            # rfcindex occasionally includes drafts that were not
            # really submitted to IETF (e.g. April 1st)
            ids = InternetDraft.objects.filter(filename=self._rfcindex.draft)
            if len(ids) > 0:
                self.draft_name = self._rfcindex.draft
            
    def _rfc_doc_list(self, name):
        if (not self._rfcindex) or (not getattr(self._rfcindex, name)):
            return None
        else:
            s = getattr(self._rfcindex, name)
            s = s.replace(",", ",  ")
            s = re.sub("([A-Z])([0-9])", "\\1 \\2", s)
            return s
    def obsoleted_by(self):
        return self._rfc_doc_list("obsoleted_by")
    def obsoletes(self):
        return self._rfc_doc_list("obsoletes")
    def updated_by(self):
        return self._rfc_doc_list("updated_by")
    def updates(self):
        return self._rfc_doc_list("updates")
    def also(self):
        return self._rfc_doc_list("also")
    def has_errata(self):
        return self._rfcindex and (self._rfcindex.has_errata > 0)
    def stream_name(self):
        if not self._rfcindex:
            return None
        else:
            x = self._rfcindex.stream
            if x == "INDEPENDENT":
                return "Independent Submission Stream"
            elif x == "LEGACY":
                return "Legacy Stream"
            else:
                return x+" Stream"

    def in_ietf_process(self):
        return self.ietf_process != None

    def file_types(self):
        types = self._rfcindex.file_formats
        types = types.replace("ascii","txt")
        return ["."+x for x in types.split(",")]

    def friendly_state(self):
        if self.in_ietf_process():
            s = self.ietf_process.main_state
            if not s in ["RFC Published", "AD is watching", "Dead"]:
                return "RFC %d (%s)<br/>%s (to %s)" % (self.rfc_number, self.maturity_level, self.ietf_process.state, self.ietf_process.intended_maturity_level())
        return "RFC %d (%s)" % (self.rfc_number, self.maturity_level)

    def ad_name(self):
        if self.in_ietf_process():
            return self.ietf_process.ad_name()
        else:
            # TODO: get AD name of the draft
            return None
    def filename(self):
        debug.show('self')
        debug.show('self._rfc')
        debug.show('self._rfcindex')
        debug.show('self._rfcindex.filename')
        return self._rfcindex.filename

    @models.permalink
    def get_absolute_url(self):
        return ('ietf.idrfc.views_doc.document_main', ['rfc%s' % (str(self.rfc_number))])
    def displayname_with_link(self):
        return '<a href="%s">RFC %d</a>' % (self.get_absolute_url(), self.rfc_number)

    def to_json(self):
        result = jsonify_helper(self, ['rfc_number', 'title', 'publication_date', 'maturity_level', 'obsoleted_by','obsoletes','updated_by','updates','also','has_errata','stream_name','file_types','in_ietf_process', 'friendly_state'])
        if self.in_ietf_process():
            result['ietf_process'] = self.ietf_process.dict()
        return json.dumps(result, indent=2)

# ---------------------------------------------------------------------------

class IetfProcessData:
    _idinternal = None
    main_state = None
    sub_state = None
    state = None
    _ballot = None
    def __init__(self, idinternal):
        self._idinternal = idinternal
        i = self._idinternal
        self.main_state = str(i.cur_state)
        if i.cur_sub_state_id > 0:
            self.sub_state = str(i.cur_sub_state)
            self.state = self.main_state + "::" + self.sub_state
        else:
            self.sub_state = None
            self.state = self.main_state
    
    def has_iesg_ballot(self):
        try:
            if self._idinternal.ballot.ballot_issued:
                return True
        except BallotInfo.DoesNotExist:
            pass
        return False
    
    def has_active_iesg_ballot(self):
        if not self.has_iesg_ballot():
            return False
        if not self.main_state in BALLOT_ACTIVE_STATES:
            return False
        if (not self._idinternal.rfc_flag) and self._idinternal.draft.status_id != 1:
            # Active
            return False
        return True

    # don't call this unless has_[active_]iesg_ballot returns True
    def iesg_ballot(self):
        if not self._ballot:
            self._ballot = BallotWrapper(self._idinternal)
        return self._ballot

    # don't call this unless has_[active_]iesg_ballot returns True
    def iesg_ballot_needed( self ):
	standardsTrack = 'Standard' in self.intended_maturity_level() or \
			self.intended_maturity_level() in ("BCP", "Best Current Practice")
	return self.iesg_ballot().ballot.needed( standardsTrack )

    def ad_name(self):
        return str(self._idinternal.job_owner)

    def iesg_note(self):
        if self._idinternal.note:
            n = self._idinternal.note
            # Hide unnecessary note of form "RFC 1234"
            if re.match("^RFC\s*\d+$", n):
                return None
            return n
        else:
            return None

    def state_date(self):
        try:
            if settings.USE_DB_REDESIGN_PROXY_CLASSES:
                return self._idinternal.docevent_set.filter(
                    Q(desc__istartswith="Draft Added by ")|
                    Q(desc__istartswith="Draft Added in state ")|
                    Q(desc__istartswith="Draft added in state ")|
                    Q(desc__istartswith="State changed to ")|
                    Q(desc__istartswith="State Changes to ")|
                    Q(desc__istartswith="Sub state has been changed to ")|
                    Q(desc__istartswith="State has been changed to ")|
                    Q(desc__istartswith="IESG has approved and state has been changed to")|
                    Q(desc__istartswith="IESG process started in state")).order_by('-time')[0].time.date()
            return self._idinternal.comments().filter(
                Q(comment_text__istartswith="Draft Added by ")|
                Q(comment_text__istartswith="Draft Added in state ")|
                Q(comment_text__istartswith="Draft added in state ")|
                Q(comment_text__istartswith="State changed to ")|
                Q(comment_text__istartswith="State Changes to ")|
                Q(comment_text__istartswith="Sub state has been changed to ")|
                Q(comment_text__istartswith="State has been changed to ")|
                Q(comment_text__istartswith="IESG has approved and state has been changed to")).order_by('-id')[0].date
        except IndexError:
            # should never happen -- return an obviously bogus date
            return date(1990,1,1)

    def dict(self):
        result = {'main_state':self.main_state,
                  'sub_state':self.sub_state,
                  'state':self.state,
                  'state_date':str(self.state_date()),
                  'has_iesg_ballot':self.has_iesg_ballot(),
                  'has_active_iesg_ballot':self.has_active_iesg_ballot(),
                  'ad_name':self.ad_name(),
                  'intended_maturity_level':self.intended_maturity_level(),
                  'telechat_date':self.telechat_date()}
        if result['telechat_date']:
            result['telechat_date'] = str(result['telechat_date'])
            result['telechat_returning_item'] = self.telechat_returning_item()
        if self.iesg_note():
            result['iesg_note'] = self.iesg_note()
        if self.has_iesg_ballot():
            result['iesg_ballot'] = self.iesg_ballot().dict()
        return result

    def intended_maturity_level(self):
        if self._idinternal.rfc_flag:
            s = str(self._idinternal.document().intended_status)
            # rfc_intend_status table uses different names, argh!
            if s == "Proposed":
                s = "Proposed Standard"
            elif s == "Draft":
                s = "Draft Standard"
            elif s == "None":
                s = None
        else:
            s = str(self._idinternal.draft.intended_status)
            if s == "None":
                s = None
            elif s == "Request":
                s = None
        return s

    def telechat_date(self):
        # return date only if it's on upcoming agenda
        if self._idinternal.agenda:
            return self._idinternal.telechat_date
        else:
            return None
        
    def telechat_returning_item(self):
        # should be called only if telechat_date() returns non-None
        return bool(self._idinternal.returning_item)

    def state_change_notice_to(self):
        return self._idinternal.state_change_notice_to

    # comment_log?

# ---------------------------------------------------------------------------

class IdRfcWrapper:
    rfc = None
    id = None
    iprCount = None
    iprUrl = None

    def __init__(self, id, rfc):
        self.id = id
        self.rfc = rfc
        if id:
            iprs = IprDraft.objects.filter(document=self.id.tracker_id, ipr__status__in=[1,3])
            self.iprUrl = "/ipr/search?option=document_search&id_document_tag=" + str(self.id.tracker_id)
        elif rfc:
            iprs = IprRfc.objects.filter(document=self.rfc.rfc_number, ipr__status__in=[1,3]) 
            self.iprUrl = "/ipr/search?option=rfc_search&rfc_search=" + str(self.rfc.rfc_number)
        else:
            raise ValueError("Construction with null id and rfc")
        # iprs is a list of docs which contain IPR
        self.iprCount = len(iprs)
 
    def title(self):
        if self.rfc:
            return self.rfc.title
        else:
            return self.id.title

    def friendly_state(self):
        if self.rfc:
            return self.rfc.friendly_state()
        else:
            return self.id.friendly_state()

    def get_absolute_url(self):
        if self.rfc:
            return self.rfc.get_absolute_url()
        else:
            return self.id.get_absolute_url()

    def comment_count(self):
        if self.rfc:
            return DocumentComment.objects.filter(document=self.rfc.rfc_number,rfc_flag=1).count()
        else:
            return DocumentComment.objects.filter(document=self.id.tracker_id).exclude(rfc_flag=1).count()

    def ad_name(self):
        if self.rfc:
            s = self.rfc.ad_name()
            if s:
                return s
        if self.id:
            return self.id.ad_name()
        return None

    def publication_date(self):
        if self.rfc:
            return self.rfc.publication_date
        else:
            return self.id.publication_date

    def telechat_date(self):
        if self.rfc and self.rfc.in_ietf_process():
            return self.rfc.ietf_process.telechat_date()
        elif self.id and self.id.in_ietf_process():
            return self.id.ietf_process.telechat_date()
        else:
            return None
        
    def view_sort_group(self):
        if self.rfc:
            return 'RFC'
        elif self.id.draft_status == "Active":
            return 'Active Internet-Draft'
        else:
            return 'Old Internet-Draft'

    def view_sort_group_byad(self):
        if self.rfc:
            return 'RFC'
        elif self.id.draft_status == "Active":
            if self.id.in_ietf_process():
               if self.id.ietf_process._idinternal.cur_state_id == IDState.DEAD:
                   return 'IESG Dead Internet-Draft'
               else:
                   return "%s Internet-Draft" % self.id.ietf_process._idinternal.cur_state
            else: 
                return 'Active Internet-Draft'
        else:
            return 'Old Internet-Draft'

    def view_sort_key(self, sort_by=None):
        if sort_by is None:
            if self.rfc:
                return "2%04d" % self.rfc.rfc_number
            elif self.id.draft_status == "Active":
                return "1"+self.id.draft_name
            else:
                return "3"+self.id.draft_name
        else:
            if self.rfc:
                sort_key = "2"
            elif self.id.draft_status == "Active":
                sort_key = "1"
            else:
                sort_key = "3"

            # Depending on what we're sorting on, we may
            # need to do some conversion.
            if sort_by == "title":
                sort_key += self.title()
            elif sort_by == "date":
                sort_key = sort_key + str(self.publication_date())
            elif sort_by == "status":
                if self.rfc:
                    sort_key += "%04d" % self.rfc.rfc_number
                else:
                    sort_key += self.id.draft_status
            elif sort_by == "ipr":
                sort_key += self.iprUrl
            elif sort_by == "ad":
                return self.view_sort_key_byad()
            else:
                # sort default or unknown sort value, revert to default
                if self.rfc:
                    sort_key += "%04d" % self.rfc.rfc_number
                else:
                    sort_key += self.id.draft_name
            
            return sort_key
            
    def view_sort_key_byad(self):
        if self.rfc:
            return "2%04d" % self.rfc.rfc_number
        elif self.id.draft_status == "Active":
            if self.id.in_ietf_process():
                return "11%02d" % (self.id.ietf_process._idinternal.cur_state_id)
            else:
                return "10"
        else:
            return "3"

# ---------------------------------------------------------------------------

class BallotWrapper:
    _idinternal = None
    ballot = None
    ballot_active = False
    _positions = None
    position_values = ["Discuss", "Yes", "No Objection", "Abstain", "Recuse", "No Record"]

    def __init__(self, idinternal):
        self._idinternal = idinternal
        self.ballot = idinternal.ballot
        if not idinternal.rfc_flag:
            self.ballot_active = self.ballot.ballot_issued and (str(idinternal.cur_state) in BALLOT_ACTIVE_STATES) and str(idinternal.draft.status)=="Active";
        else:
            self.ballot_active = self.ballot.ballot_issued and (str(idinternal.cur_state) in BALLOT_ACTIVE_STATES)
        self._ballot_set = None

    def approval_text(self):
        return self.ballot.approval_text
    def ballot_writeup(self):
        return self.ballot.ballot_writeup
    def is_active(self):
        return self.ballot_active
    def ballot_id(self):
        return self._idinternal.ballot_id
    def was_deferred(self):
        return self.ballot.defer
    def deferred_by(self):
        return self.ballot.defer_by
    def deferred_date(self):
        return self.ballot.defer_date
    def is_ballot_set(self):
        if not self._ballot_set:
            self._ballot_set = self._idinternal.ballot_set()
        return len(list(self._ballot_set)) > 1
    def ballot_set_other(self):
        if not self.is_ballot_set():
            return []
        else:
            return self._ballot_set.exclude(draft=self._idinternal)

    def _init(self):
        if not settings.USE_DB_REDESIGN_PROXY_CLASSES:
            self.old_init()
            return

        from ietf.person.models import Person
        from ietf.doc.models import BallotPositionDocEvent, NewRevisionDocEvent

        active_ads = Person.objects.filter(role__name="ad", role__group__state="active").distinct()
        
        positions = []
        seen = {}

        new_revisions = list(NewRevisionDocEvent.objects.filter(doc=self.ballot, type="new_revision").order_by('-time', '-id'))

        ballot = self.ballot.latest_event(BallotDocEvent, type="created_ballot")

	for pos in BallotPositionDocEvent.objects.filter(doc=self.ballot, type="changed_ballot_position", ballot=ballot).select_related('ad').order_by("-time", '-id'):
            if pos.ad not in seen:
                p = dict(ad_name=pos.ad.plain_name(),
                         ad_username=pos.ad.pk, # ought to rename this in doc_ballot_list
                         position=pos.pos.name,
                         is_old_ad=pos.ad not in active_ads,
                         old_positions=[])

                rev = pos.doc.rev
                for n in new_revisions:
                    if n.time <= pos.time:
                        rev = n.rev
                        break

                if pos.pos.slug == "discuss":
                    p["has_text"] = True
                    p["discuss_text"] = pos.discuss
                    p["discuss_date"] = pos.discuss_time.date()
                    p["discuss_revision"] = rev

                if pos.comment:
                    p["has_text"] = True
                    p["comment_text"] = pos.comment
                    p["comment_date"] = pos.comment_time.date()
                    p["comment_revision"] = rev

                positions.append(p)
                seen[pos.ad] = p
            else:
                latest = seen[pos.ad]
                if latest["old_positions"]:
                    prev = latest["old_positions"][-1]
                else:
                    prev = latest["position"]
                    
                if prev != pos.pos.name:
                    seen[pos.ad]["old_positions"].append(pos.pos.name)

        # add any missing ADs as No Record
        if self.ballot_active:
            for ad in active_ads:
                if ad not in seen:
                    d = dict(ad_name=ad.plain_name(),
                             ad_username=ad.pk,
                             position="No Record",
                             )
                    positions.append(d)

        self._positions = positions
        
    def old_init(self):
        try:
            ads = set()
        except NameError:
            # for Python 2.3 
            from sets import Set as set
            ads = set()

        positions = []
        all_comments = self.ballot.comments.all().select_related('ad')
        for p in self.ballot.positions.all().select_related('ad'):
            po = create_position_object(self.ballot, p, all_comments)
            #if not self.ballot_active:
            #    if 'is_old_ad' in po:
            #        del po['is_old_ad']
            ads.add(str(p.ad))
            positions.append(po)
        for c in all_comments:
            if (str(c.ad) not in ads) and c.ad.is_current_ad():
                positions.append({'has_text':True,
                                  'comment_text':c.text,
                                  'comment_date':c.date,
                                  'comment_revision':str(c.revision),
                                  'ad_name':str(c.ad),
                                  'ad_username': c.ad.login_name,
                                  'position':'No Record',
                                  'is_old_ad':False})
                ads.add(str(c.ad))
        if self.ballot_active:
            for ad in IESGLogin.active_iesg():
                if str(ad) not in ads:
                    positions.append(dict(ad_name=str(ad),
                                          ad_username=ad.login_name,
                                          position="No Record"))
        self._positions = positions

    def position_for_ad(self, ad_name):
        pl = self.position_list()
        for p in pl:
            if p["ad_name"] == ad_name:
                return p["position"]
        return None

    def position_list(self):
        if not self._positions:
            self._init()
        return self._positions

    def get(self, v):
        return [p for p in self.position_list() if p['position']==v]

    def get_discuss(self):
        return self.get("Discuss")
    def get_yes(self):
        return self.get("Yes")
    def get_no_objection(self):
        return self.get("No Objection")
    def get_abstain(self):
        return self.get("Abstain")
    def get_recuse(self):
        return self.get("Recuse")
    def get_no_record(self):
        return self.get("No Record")

    def get_texts(self):
        return [p for p in self.position_list() if ('has_text' in p) and p['has_text']]

    def dict(self):
        summary = {}
        for key in self.position_values:
            tag = key.lower().replace(" ", "_")
            summary[tag] = [ pos["ad_name"] for pos in self.get(key) ]
        positions = self.position_list()
        for i in range(len(positions)):
            for key in ["comment_date", "discuss_date", ]:
                if key in positions[i]:
                    positions[i][key] = positions[i][key].strftime("%Y-%m-%d")
        return {
            "active": self.is_active(),
            "approval_text": self.approval_text(),
            "ballot_writeup": self.ballot_writeup(),
            "ballot_id": self.ballot_id(),
            "deferred_by": unicode(self.deferred_by()),
            "deferred_date": self.deferred_date() and self.deferred_date().strftime("%Y-%m-%d") ,
            "positions": positions,
            "summary": summary,
            "was_deferred": self.was_deferred(),
        }

def position_to_string(position):
    positions = {"yes":"Yes",
                 "noobj":"No Objection",
                 "discuss":"Discuss",
                 "abstain":"Abstain",
                 "recuse":"Recuse"}
    if not position:
        return "No Record"
    p = None
    for k,v in positions.iteritems():
        if getattr(position, k) > 0:
            p = v
    if not p:
        p = "No Record"
    return p

def create_position_object(ballot, position, all_comments):
    positions = {"yes":"Yes",
                 "noobj":"No Objection",
                 "discuss":"Discuss",
                 "abstain":"Abstain",
                 "recuse":"Recuse"}
    p = None
    for k,v in positions.iteritems():
        if position.__dict__[k] > 0:
            p = v
    if not p:
        p = "No Record"
    r = dict(ad_name=str(position.ad),
             ad_username=position.ad.login_name, 
             position=p)
    if not position.ad.is_current_ad():
        r['is_old_ad'] = True
    else:
        r['is_old_ad'] = False
        
    was = [v for k,v in positions.iteritems() if position.__dict__[k] < 0]
    if len(was) > 0:
        r['old_positions'] = was

    comment = None
    for c in all_comments:
        if c.ad == position.ad:
            comment = c
            break
    if comment and comment.text: 
        r['has_text'] =  True
        r['comment_text'] = comment.text
        r['comment_date'] = comment.date
        r['comment_revision'] = str(comment.revision)

    if p == "Discuss":
        try:
            discuss = ballot.discusses.get(ad=position.ad)
            if discuss.text:
                r['discuss_text'] = discuss.text
            else:
                r['discuss_text'] = '(empty)'
            r['discuss_revision'] = str(discuss.revision)
            r['discuss_date'] = discuss.date
        except IESGDiscuss.DoesNotExist:
            # this should never happen, but unfortunately it does
            # fill in something to keep other parts of the code happy
            r['discuss_text'] = "(error: discuss text not found)"
            r['discuss_revision'] = "00"
            r['discuss_date'] = date(2000, 1,1)
        r['has_text'] = True
    return r

