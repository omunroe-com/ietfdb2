# Copyright The IETF Trust 2008, All Rights Reserved

# Portion Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
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

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext, loader
from django.http import HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse as urlreverse
from ietf.idtracker.models import Area, IETFWG
from ietf.idrfc.views_search import SearchForm, search_query
from ietf.idrfc.idrfc_wrapper import IdRfcWrapper
from ietf.ipr.models import IprDetail
from ietf.group.models import Group
from ietf.doc.models import State
from ietf.doc.utils import get_chartering_type


def fill_in_charter_info(wg, include_drafts=False):
    from ietf.person.models import Email
    from ietf.doc.models import DocAlias, RelatedDocument

    wg.areadirector = wg.ad.role_email("ad", wg.parent) if wg.ad else None
    wg.chairs = Email.objects.filter(role__group=wg, role__name="chair")
    wg.techadvisors = Email.objects.filter(role__group=wg, role__name="techadv")
    wg.editors = Email.objects.filter(role__group=wg, role__name="editor")
    wg.secretaries = Email.objects.filter(role__group=wg, role__name="secr")
    wg.milestones = wg.groupmilestone_set.filter(state="active").order_by('due')

    if include_drafts:
        aliases = DocAlias.objects.filter(document__type="draft", document__group=wg).select_related('document').order_by("name")
        wg.drafts = []
        wg.rfcs = []
        for a in aliases:
            if a.name.startswith("draft"):
                wg.drafts.append(a)
            else:
                wg.rfcs.append(a)
                a.rel = RelatedDocument.objects.filter(source=a.document).distinct()
                a.invrel = RelatedDocument.objects.filter(target=a).distinct()

def wg_summary_acronym(request):
    areas = Area.active_areas()
    wgs = IETFWG.objects.filter(status=IETFWG.ACTIVE)
    return HttpResponse(loader.render_to_string('wginfo/1wg-summary-by-acronym.txt', {'area_list': areas, 'wg_list': wgs}),mimetype='text/plain; charset=UTF-8')

def wg_summary_area(request):
    wgs = IETFWG.objects.filter(status='1',group_type='1',start_date__isnull=False)
    return HttpResponse(loader.render_to_string('wginfo/1wg-summary.txt', {'wg_list': wgs}),mimetype='text/plain; charset=UTF-8')

def wg_charters(request):
    wgs = IETFWG.objects.filter(status='1',group_type='1',start_date__isnull=False)
    if settings.USE_DB_REDESIGN_PROXY_CLASSES:
        for wg in wgs:
            fill_in_charter_info(wg, include_drafts=True)
    return HttpResponse(loader.render_to_string('wginfo/1wg-charters.txt', {'wg_list': wgs, 'USE_DB_REDESIGN_PROXY_CLASSES': settings.USE_DB_REDESIGN_PROXY_CLASSES}),mimetype='text/plain; charset=UTF-8')

def wg_charters_by_acronym(request):
    wgs = IETFWG.objects.filter(status='1',group_type='1',start_date__isnull=False)
    if settings.USE_DB_REDESIGN_PROXY_CLASSES:
        for wg in wgs:
            fill_in_charter_info(wg, include_drafts=True)
    return HttpResponse(loader.render_to_string('wginfo/1wg-charters-by-acronym.txt', {'wg_list': wgs, 'USE_DB_REDESIGN_PROXY_CLASSES': settings.USE_DB_REDESIGN_PROXY_CLASSES}),mimetype='text/plain; charset=UTF-8')

def wg_dir(request):
    areas = Area.active_areas()
    return render_to_response('wginfo/wg-dir.html', {'areas':areas}, RequestContext(request))

def wg_dirREDESIGN(request):
    from ietf.group.models import Group, GroupURL
    from ietf.person.models import Email
    
    areas = Group.objects.filter(type="area", state="active").order_by("name")
    for area in areas:
        area.ads = []
        for e in Email.objects.filter(role__group=area, role__name="ad").select_related("person"):
            e.incoming = False
            area.ads.append(e)

        for e in Email.objects.filter(role__group=area, role__name="pre-ad").select_related("person"):
            e.incoming = True
            area.ads.append(e)

        area.ads.sort(key=lambda e: (e.incoming, e.person.name_parts()[3]))
        area.wgs = Group.objects.filter(parent=area, type="wg", state="active").order_by("acronym")
        area.urls = area.groupurl_set.all().order_by("name")
        for wg in area.wgs:
            wg.chairs = sorted(Email.objects.filter(role__group=wg, role__name="chair").select_related("person"), key=lambda e: e.person.name_parts()[3])
            
    return render_to_response('wginfo/wg-dirREDESIGN.html', {'areas':areas}, RequestContext(request))

if settings.USE_DB_REDESIGN_PROXY_CLASSES:
    wg_dir = wg_dirREDESIGN

def bofs(request):
    groups = Group.objects.filter(type="wg", state="bof")
    return render_to_response('wginfo/bofs.html',dict(groups=groups),RequestContext(request))

def chartering_wgs(request):
    charter_states = State.objects.filter(used=True, type="charter").exclude(slug__in=("approved", "notrev"))
    groups = Group.objects.filter(type="wg", charter__states__in=charter_states).select_related("state", "charter")


    for g in groups:
        g.chartering_type = get_chartering_type(g.charter)

    return render_to_response('wginfo/chartering_wgs.html',
                              dict(charter_states=charter_states,
                                   groups=groups),
                              RequestContext(request))


def wg_documents(request, acronym):
    wg = get_object_or_404(IETFWG, group_acronym__acronym=acronym, group_type=1)
    concluded = wg.status_id in [ 2, 3, ]
    proposed = (wg.status_id == 4)
    form = SearchForm({'by':'group', 'group':str(wg.group_acronym.acronym),
                       'rfcs':'on', 'activeDrafts':'on'})
    if not form.is_valid():
        raise ValueError("form did not validate")
    (docs,meta) = search_query(form.cleaned_data)

    # get the related docs
    form_related = SearchForm({'by':'group', 'name':'-'+str(wg.group_acronym.acronym)+'-', 'activeDrafts':'on'})
    if not form_related.is_valid():
        raise ValueError("form_related did not validate")
    (docs_related,meta_related) = search_query(form_related.cleaned_data)
    docs_related_pruned = []
    for d in docs_related:
        parts = d.id.draft_name.split("-", 2);
        # canonical form draft-<name|ietf>-wg-etc
        if ( len(parts) >= 3):
            if parts[1] != "ietf" and parts[2].startswith(wg.group_acronym.acronym+"-"):
                docs_related_pruned.append(d)

    docs_related = docs_related_pruned

    # move call for WG adoption to related
    cleaned_docs = []
    related_doc_names = set(d.id.draft_name for d in docs_related)
    for d in docs:
        if d.id and d.id._draft and d.id._draft.stream_id == "ietf" and d.id._draft.get_state_slug("draft-stream-ietf") == "c-adopt":
            if d.id.draft_name not in related_doc_names:
                docs_related.append(d)
        else:
            cleaned_docs.append(d)

    docs = cleaned_docs

    docs_related.sort(key=lambda d: d.id.draft_name)

    return wg, concluded, proposed, docs, meta, docs_related, meta_related

def wg_documents_txt(request, acronym):
    wg, concluded, proposed, docs, meta, docs_related, meta_related = wg_documents(request, acronym)
    return HttpResponse(loader.render_to_string('wginfo/wg_documents.txt', {'wg': wg, 'concluded':concluded, 'proposed':proposed, 'selected':'documents', 'docs':docs,  'meta':meta, 'docs_related':docs_related, 'meta_related':meta_related}),mimetype='text/plain; charset=UTF-8')

def wg_documents_html(request, acronym):
    wg, concluded, proposed, docs, meta, docs_related, meta_related = wg_documents(request, acronym)
    return render_to_response('wginfo/wg_documents.html', {'wg': wg, 'concluded':concluded, 'proposed':proposed, 'selected':'documents', 'docs':docs,  'meta':meta, 'docs_related':docs_related, 'meta_related':meta_related}, RequestContext(request))

def wg_charter(request, acronym):
    wg = get_object_or_404(IETFWG, group_acronym__acronym=acronym, group_type=1)
    concluded = wg.status_id in [ 2, 3, ]
    proposed = (wg.status_id == 4)

    fill_in_charter_info(wg)
    actions = []
    if wg.state_id != "conclude":
        actions.append(("Edit WG", urlreverse("wg_edit", kwargs=dict(acronym=wg.acronym))))

    e = wg.latest_event(type__in=("changed_state", "requested_close",))
    requested_close = wg.state_id != "conclude" and e and e.type == "requested_close"

    if wg.state_id in ("active", "dormant"):
        actions.append(("Request closing WG", urlreverse("wg_conclude", kwargs=dict(acronym=wg.acronym))))

    context = get_wg_menu_context(wg, "charter")
    context.update(dict(
            actions=actions,
            is_chair=request.user.is_authenticated() and wg.role_set.filter(name="chair", person__user=request.user),
            milestones_in_review=wg.groupmilestone_set.filter(state="review"),
            requested_close=requested_close,
            ))

    return render_to_response('wginfo/wg_charter.html',
                              context,
                              RequestContext(request))

def get_wg_menu_context(wg, selected):
    # it would probably be better to refactor wginfo into rendering
    # the menu separately instead of each view having to include the information

    return dict(wg=wg, concluded=wg.state_id == "conclude", proposed=wg.state_id == "proposed", selected=selected)

def history(request, acronym):
    wg = get_object_or_404(Group, acronym=acronym)

    events = wg.groupevent_set.all().select_related('by').order_by('-time', '-id')

    context = get_wg_menu_context(wg, "history")
    context.update(dict(events=events,
                        ))

    wg.group_acronym = wg # hack for compatibility with old templates

    return render_to_response('wginfo/history.html', context, RequestContext(request))
