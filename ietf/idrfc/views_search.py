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

import re, datetime

from django import forms
from django.shortcuts import render_to_response
from django.db.models import Q
from django.template import RequestContext
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect

from ietf.idrfc.expire import expirable_draft
from ietf.utils import normalize_draftname
from ietf.doc.models import *
from ietf.person.models import *
from ietf.group.models import *
from ietf.ipr.models import IprDocAlias
from ietf.idindex.index import active_drafts_index_by_group

class SearchForm(forms.Form):
    name = forms.CharField(required=False)
    rfcs = forms.BooleanField(required=False, initial=True)
    activedrafts = forms.BooleanField(required=False, initial=True)
    olddrafts = forms.BooleanField(required=False, initial=False)

    by = forms.ChoiceField(choices=[(x,x) for x in ('author','group','area','ad','state')], required=False, initial='wg', label='Foobar')
    author = forms.CharField(required=False)
    group = forms.CharField(required=False)
    area = forms.ModelChoiceField(Group.objects.filter(type="area", state="active").order_by('name'), empty_label="any area", required=False)
    ad = forms.ChoiceField(choices=(), required=False)
    state = forms.ModelChoiceField(State.objects.filter(type="draft-iesg"), empty_label="any state", required=False)
    substate = forms.ChoiceField(choices=(), required=False)

    sort = forms.ChoiceField(choices=(("document", "Document"), ("title", "Title"), ("date", "Date"), ("status", "Status"), ("ipr", "Ipr"), ("ad", "AD")), required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        responsible = Document.objects.values_list('ad', flat=True).distinct()
        active_ads = list(Person.objects.filter(role__name="ad",
                                                role__group__type="area",
                                                role__group__state="active").distinct())
        inactive_ads = list(((Person.objects.filter(pk__in=responsible) | Person.objects.filter(role__name="pre-ad",
                                                                                              role__group__type="area",
                                                                                              role__group__state="active")).distinct())
                            .exclude(pk__in=[x.pk for x in active_ads]))
        extract_last_name = lambda x: x.name_parts()[3]
        active_ads.sort(key=extract_last_name)
        inactive_ads.sort(key=extract_last_name)

        self.fields['ad'].choices = c = [('', 'any AD')] + [(ad.pk, ad.plain_name()) for ad in active_ads] + [('', '------------------')] + [(ad.pk, ad.name) for ad in inactive_ads]
        self.fields['substate'].choices = [('', 'any substate'), ('0', 'no substate')] + [(n.slug, n.name) for n in DocTagName.objects.filter(slug__in=IESG_SUBSTATE_TAGS)]

    def clean_name(self):
        value = self.cleaned_data.get('name','')
        return normalize_draftname(value)

    def clean(self):
        q = self.cleaned_data
        # Reset query['by'] if needed
        if 'by' in q:
            for k in ('author', 'group', 'area', 'ad'):
                if q['by'] == k and not q.get(k):
                    q['by'] = None
            if q['by'] == 'state' and not (q.get("state") or q.get('substate')):
                q['by'] = None
        # Reset other fields
        for k in ('author','group', 'area', 'ad'):
            if k != q['by']:
                q[k] = ""
        if q['by'] != 'state':
            q['state'] = q['substate'] = None
        return q

def wrap_value(v):
    return lambda: v

def fill_in_search_attributes(docs):
    # fill in some attributes for the search results to save some
    # hairy template code and avoid repeated SQL queries - remaining
    # queries we don't handle here are mostly implicit many-to-many
    # relations for which there is poor support in Django 1.2

    docs_dict = dict((d.pk, d) for d in docs)
    doc_ids = docs_dict.keys()

    rfc_aliases = dict(DocAlias.objects.filter(name__startswith="rfc", document__in=doc_ids).values_list("document_id", "name"))

    # latest event cache
    event_types = ("published_rfc",
                   "changed_ballot_position",
                   "started_iesg_process",
                   "new_revision")
    for d in docs:
        d.latest_event_cache = dict()
        for e in event_types:
            d.latest_event_cache[e] = None

    for e in DocEvent.objects.filter(doc__in=doc_ids, type__in=event_types).order_by('time'):
        docs_dict[e.doc_id].latest_event_cache[e.type] = e

    # IPR
    for d in docs:
        d.iprs = []

    ipr_docaliases = IprDocAlias.objects.filter(doc_alias__document__in=doc_ids).select_related('doc_alias')
    for a in ipr_docaliases:
        docs_dict[a.doc_alias.document_id].iprs.append(a)

    # telechat date, can't do this with above query as we need to get TelechatDocEvents out
    seen = set()
    for e in TelechatDocEvent.objects.filter(doc__in=doc_ids, type="scheduled_for_telechat").order_by('-time'):
        if e.doc_id not in seen:
            d = docs_dict[e.doc_id]
            d.telechat_date = wrap_value(d.telechat_date(e))
            seen.add(e.doc_id)

    # misc
    for d in docs:
        # emulate canonical name which is used by a lot of the utils
        d.canonical_name = wrap_value(rfc_aliases[d.pk] if d.pk in rfc_aliases else d.name)

        if d.rfc_number() != None and d.latest_event_cache["published_rfc"]:
            d.latest_revision_date = d.latest_event_cache["published_rfc"].time
        elif d.latest_event_cache["new_revision"]:
            d.latest_revision_date = d.latest_event_cache["new_revision"].time
        else:
            d.latest_revision_date = d.time

        if d.get_state_slug() == "rfc":
            d.search_heading = "RFCs"
        elif d.get_state_slug() == "active":
            d.search_heading = "Active Internet-Drafts"
        else:
            d.search_heading = "Old Internet-Drafts"

        d.expirable = expirable_draft(d)

        if d.get_state_slug() != "rfc":
            d.milestones = d.groupmilestone_set.filter(state="active").order_by("time").select_related("group")



    # RFCs

    # errata
    erratas = set(Document.objects.filter(tags="errata", name__in=rfc_aliases.keys()).distinct().values_list("name", flat=True))
    for d in docs:
        d.has_errata = d.name in erratas

    # obsoleted/updated by
    for a in rfc_aliases:
        d = docs_dict[a]
        d.obsoleted_by_list = []
        d.updated_by_list = []

    xed_by = RelatedDocument.objects.filter(target__name__in=rfc_aliases.values(),
                                            relationship__in=("obs", "updates")).select_related('target__document_id')
    rel_rfc_aliases = dict(DocAlias.objects.filter(name__startswith="rfc",
                                                   document__in=[rel.source_id for rel in xed_by]).values_list('document_id', 'name'))
    for rel in xed_by:
        d = docs_dict[rel.target.document_id]
        if rel.relationship_id == "obs":
            l = d.obsoleted_by_list
        elif rel.relationship_id == "updates":
            l = d.updated_by_list
        l.append(rel_rfc_aliases[rel.source_id].upper())
        l.sort()


def retrieve_search_results(form):
    """Takes a validated SearchForm and return the results."""
    if not form.is_valid():
        raise ValueError("SearchForm doesn't validate: %s" % form.errors)
        
    query = form.cleaned_data

    if not (query['activedrafts'] or query['olddrafts'] or query['rfcs']):
        return ([], {})

    MAX = 500

    docs = Document.objects.filter(type="draft")

    # name
    if query["name"]:
        docs = docs.filter(Q(docalias__name__icontains=query["name"]) |
                           Q(title__icontains=query["name"])).distinct()

    # rfc/active/old check buttons
    allowed_states = []
    if query["rfcs"]:
        allowed_states.append("rfc")
    if query["activedrafts"]:
        allowed_states.append("active")
    if query["olddrafts"]:
        allowed_states.extend(['repl', 'expired', 'auth-rm', 'ietf-rm'])

    docs = docs.filter(states__type="draft", states__slug__in=allowed_states)

    # radio choices
    by = query["by"]
    if by == "author":
        docs = docs.filter(authors__person__name__icontains=query["author"])
    elif by == "group":
        docs = docs.filter(group__acronym=query["group"])
    elif by == "area":
        docs = docs.filter(Q(group__type="wg", group__parent=query["area"]) |
                           Q(group=query["area"])).distinct()
    elif by == "ad":
        docs = docs.filter(ad=query["ad"])
    elif by == "state":
        if query["state"]:
            docs = docs.filter(states=query["state"])
        if query["substate"]:
            docs = docs.filter(tags=query["substate"])

    # evaluate and fill in attribute results immediately to cut down
    # the number of queries
    results = list(docs.select_related("states", "ad", "ad__person", "std_level", "intended_std_level", "group", "stream")[:MAX])

    fill_in_search_attributes(results)

    # sort
    def sort_key(d):
        res = []

        rfc_num = d.rfc_number()

        if rfc_num != None:
            res.append(2)
        elif d.get_state_slug() == "active":
            res.append(1)
        else:
            res.append(3)

        if query["sort"] == "title":
            res.append(d.title)
        elif query["sort"] == "date":
            res.append(str(d.latest_revision_date))
        elif query["sort"] == "status":
            if rfc_num != None:
                res.append(int(rfc_num))
            else:
                res.append(d.get_state().order if d.get_state() else None)
        elif query["sort"] == "ipr":
            res.append(len(d.iprs))
        elif query["sort"] == "ad":
            if rfc_num != None:
                res.append(int(rfc_num))
            elif d.get_state_slug() == "active":
                if d.get_state("draft-iesg"):
                    res.append(d.get_state("draft-iesg").order)
                else:
                    res.append(0)
        else:
            if rfc_num != None:
                res.append(int(rfc_num))
            else:
                res.append(d.canonical_name())

        return res

    results.sort(key=sort_key)

    # fill in a meta dict with some information for rendering the result table
    meta = {}
    if len(results) == MAX:
        meta['max'] = MAX
    meta['by'] = query['by']
    meta['advanced'] = bool(query['by'])

    meta['headers'] = [{'title': 'Document', 'key':'document'},
                       {'title': 'Title', 'key':'title'},
                       {'title': 'Date', 'key':'date'},
                       {'title': 'Status', 'key':'status', 'colspan':'2'},
                       {'title': 'IPR', 'key':'ipr'},
                       {'title': 'Area Director', 'key':'ad'}]

    if hasattr(form.data, "urlencode"): # form was fed a Django QueryDict, not local plain dict
        d = form.data.copy()
        for h in meta['headers']:
            d["sort"] = h["key"]
            h["sort_url"] = "?" + d.urlencode()
            if h['key'] == query.get('sort'):
                h['sorted'] = True

    return (results, meta)


def search(request):
    if request.GET:
        # backwards compatibility
        get_params = request.GET.copy()
        if 'activeDrafts' in request.GET:
            get_params['activedrafts'] = request.GET['activeDrafts']
        if 'oldDrafts' in request.GET:
            get_params['olddrafts'] = request.GET['oldDrafts']
        if 'subState' in request.GET:
            get_params['substate'] = request.GET['subState']

        form = SearchForm(get_params)
        if not form.is_valid():
            return HttpResponseBadRequest("form not valid: %s" % form.errors)

        results, meta = retrieve_search_results(form)
        meta['searching'] = True
    else:
        form = SearchForm()
        results = []
        meta = { 'by': None, 'advanced': False, 'searching': False }

    return render_to_response('doc/search.html',
                              {'form':form, 'docs':results, 'meta':meta, 'show_add_to_list': True },
                              context_instance=RequestContext(request))

def drafts_for_ad(request, name):
    ad = None
    responsible = Document.objects.values_list('ad', flat=True).distinct()
    for p in Person.objects.filter(Q(role__name__in=("pre-ad", "ad"),
                                     role__group__type="area",
                                     role__group__state="active")
                                   | Q(pk__in=responsible)).distinct():
        if name == p.full_name_as_key():
            ad = p
            break
    if not ad:
        raise Http404
    form = SearchForm({'by':'ad','ad': ad.id,
                       'rfcs':'on', 'activedrafts':'on', 'olddrafts':'on',
                       'sort': 'status'})
    results, meta = retrieve_search_results(form)

    for d in results:
        if d.get_state_slug() == "active":
            iesg_state = d.get_state("draft-iesg")
            if iesg_state:
                if iesg_state.slug == "dead":
                    d.search_heading = "IESG Dead Internet-Drafts"
                else:
                    d.search_heading = "%s Internet-Drafts" % iesg_state.name

    return render_to_response('doc/drafts_for_ad.html',
                              { 'form':form, 'docs':results, 'meta':meta, 'ad_name': ad.plain_name() },
                              context_instance=RequestContext(request))

def drafts_in_last_call(request):
    lc_state = State.objects.get(type="draft-iesg", slug="lc").pk
    form = SearchForm({'by':'state','state': lc_state, 'rfcs':'on', 'activedrafts':'on'})
    results, meta = retrieve_search_results(form)

    return render_to_response('doc/drafts_in_last_call.html',
                              { 'form':form, 'docs':results, 'meta':meta },
                              context_instance=RequestContext(request))

def drafts_in_iesg_process(request, last_call_only=None):
    if last_call_only:
        states = State.objects.filter(type="draft-iesg", slug__in=("lc", "writeupw", "goaheadw"))
        title = "Documents in Last Call"
    else:
        states = State.objects.filter(type="draft-iesg").exclude(slug__in=('pub', 'dead', 'watching', 'rfcqueue'))
        title = "Documents in IESG process"

    grouped_docs = []

    for s in states.order_by("order"):
        docs = Document.objects.filter(type="draft", states=s).distinct().order_by("time").select_related("ad", "group", "group__parent")
        if docs:
            if s.slug == "lc":
                for d in docs:
                    e = d.latest_event(LastCallDocEvent, type="sent_last_call")
                    d.lc_expires = e.expires if e else datetime.datetime.min
                docs = list(docs)
                docs.sort(key=lambda d: d.lc_expires)

            grouped_docs.append((s, docs))

    return render_to_response('doc/drafts_in_iesg_process.html', {
            "grouped_docs": grouped_docs,
            "title": title,
            "last_call_only": last_call_only,
            }, context_instance=RequestContext(request))

def index_all_drafts(request):
    # try to be efficient since this view returns a lot of data
    categories = []

    for s in ("active", "rfc", "expired", "repl", "auth-rm", "ietf-rm"):
        state = State.objects.get(type="draft", slug=s)

        if state.slug == "rfc":
            heading = "RFCs"
        elif state.slug in ("ietf-rm", "auth-rm"):
            heading = "Internet-Drafts %s" % state.name
        else:
            heading = "%s Internet-Drafts" % state.name

        draft_names = DocAlias.objects.filter(document__states=state).values_list("name", "document")

        names = []
        names_to_skip = set()
        for name, doc in draft_names:
            sort_key = name
            if name != doc:
                if not name.startswith("rfc"):
                    name, doc = doc, name
                names_to_skip.add(doc)

            if name.startswith("rfc"):
                name = name.upper()
                sort_key = -int(name[3:])

            names.append((name, sort_key))

        names.sort(key=lambda t: t[1])

        names = ['<a href="/doc/' + name + '/">' + name +'</a>'
                 for name, _ in names if name not in names_to_skip]

        categories.append((state,
                      heading,
                      len(names),
                      "<br>".join(names)
                      ))
    return render_to_response('doc/index_all_drafts.html', { "categories": categories },
                              context_instance=RequestContext(request))

def index_active_drafts(request):
    groups = active_drafts_index_by_group()

    return render_to_response("doc/index_active_drafts.html", { 'groups': groups }, context_instance=RequestContext(request))
