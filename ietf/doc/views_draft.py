# changing state and metadata on Internet Drafts

import re, os, datetime, json
from textwrap import dedent

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.core.urlresolvers import reverse as urlreverse
from django.template.loader import render_to_string
from django.template import RequestContext
from django import forms
from django.utils.html import strip_tags
from django.db.models import Max
from django.conf import settings
from django.forms.util import ErrorList
from django.contrib.auth.decorators import login_required
from django.template.defaultfilters import pluralize

from ietf.utils.mail import send_mail_text, send_mail_message
from ietf.ietfauth.utils import role_required
from ietf.ietfauth.utils import has_role, is_authorized_in_doc_stream, user_is_person
from ietf.iesg.models import TelechatDate
from ietf.doc.mails import *
from ietf.doc.lastcall import request_last_call
from ietf.utils.textupload import get_cleaned_text_file_content
from ietf.person.forms import EmailsField
from ietf.group.models import Group
from ietf.secr.lib import jsonapi

from ietf.doc.models import *
from ietf.doc.utils import *
from ietf.name.models import IntendedStdLevelName, DocTagName, StreamName
from ietf.person.models import Person, Email
from ietf.message.models import Message

class ChangeStateForm(forms.Form):
    state = forms.ModelChoiceField(State.objects.filter(used=True, type="draft-iesg"), empty_label=None, required=True)
    substate = forms.ModelChoiceField(DocTagName.objects.filter(slug__in=IESG_SUBSTATE_TAGS), required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        retclean = self.cleaned_data
        state = self.cleaned_data.get('state', '(None)')
        tag = self.cleaned_data.get('substate','')
        comment = self.cleaned_data['comment'].strip()
        doc = get_object_or_404(Document, docalias__name=self.docname)
        prev = doc.get_state("draft-iesg")
    
        # tag handling is a bit awkward since the UI still works
        # as if IESG tags are a substate
        prev_tag = doc.tags.filter(slug__in=IESG_SUBSTATE_TAGS)
        prev_tag = prev_tag[0] if prev_tag else None

        if state == prev and tag == prev_tag:
            self._errors['comment'] = ErrorList([u'State not changed. Comments entered will be lost with no state change. Please go back and use the Add Comment feature on the history tab to add comments without changing state.'])
        return retclean

@role_required('Area Director','Secretariat')
def change_state(request, name):
    """Change IESG state of Internet Draft, notifying parties as necessary
    and logging the change as a comment."""
    doc = get_object_or_404(Document, docalias__name=name)
    if (not doc.latest_event(type="started_iesg_process")) or doc.get_state_slug() == "expired":
        raise Http404()

    login = request.user.person

    if request.method == 'POST':
        form = ChangeStateForm(request.POST)
        form.docname=name
        if form.is_valid():
            new_state = form.cleaned_data['state']
            prev_state = doc.get_state("draft-iesg")

            tag = form.cleaned_data['substate']
            comment = form.cleaned_data['comment'].strip()

            # tag handling is a bit awkward since the UI still works
            # as if IESG tags are a substate
            prev_tags = doc.tags.filter(slug__in=IESG_SUBSTATE_TAGS)
            new_tags = [tag] if tag else []
            if new_state != prev_state or set(new_tags) != set(prev_tags):
                save_document_in_history(doc)
                
                doc.set_state(new_state)

                doc.tags.remove(*prev_tags)
                doc.tags.add(*new_tags)

                e = add_state_change_event(doc, login, prev_state, new_state,
                                           prev_tags=prev_tags, new_tags=new_tags)

                msg = e.desc

                if comment:
                    c = DocEvent(type="added_comment")
                    c.doc = doc
                    c.by = login
                    c.desc = comment
                    c.save()

                    msg += "\n" + comment
                
                doc.time = e.time
                doc.save()

                email_state_changed(request, doc, msg)
                email_ad(request, doc, doc.ad, login, msg)


                if prev_state and prev_state.slug in ("ann", "rfcqueue") and new_state.slug not in ("rfcqueue", "pub"):
                    email_pulled_from_rfc_queue(request, doc, comment, prev_state, new_state)

                if new_state.slug in ("iesg-eva", "lc"):
                    if not doc.get_state_slug("draft-iana-review"):
                        doc.set_state(State.objects.get(used=True, type="draft-iana-review", slug="need-rev"))

                if new_state.slug == "lc-req":
                    request_last_call(request, doc)

                    return render_to_response('doc/draft/last_call_requested.html',
                                              dict(doc=doc,
                                                   url=doc.get_absolute_url()),
                                              context_instance=RequestContext(request))
                
            return HttpResponseRedirect(doc.get_absolute_url())

    else:
        state = doc.get_state("draft-iesg")
        t = doc.tags.filter(slug__in=IESG_SUBSTATE_TAGS)
        form = ChangeStateForm(initial=dict(state=state.pk if state else None,
                                            substate=t[0].pk if t else None))
        form.docname=name

    state = doc.get_state("draft-iesg")
    next_states = state.next_states.all() if state else None
    prev_state = None

    hists = doc.history_set.exclude(states=doc.get_state("draft-iesg")).order_by('-time')[:1]
    if hists:
        prev_state = hists[0].get_state("draft-iesg")

    to_iesg_eval = None
    if not doc.latest_event(type="sent_ballot_announcement"):
        if next_states and next_states.filter(slug="iesg-eva"):
            to_iesg_eval = State.objects.get(used=True, type="draft-iesg", slug="iesg-eva")
            next_states = next_states.exclude(slug="iesg-eva")

    return render_to_response('doc/draft/change_state.html',
                              dict(form=form,
                                   doc=doc,
                                   state=state,
                                   prev_state=prev_state,
                                   next_states=next_states,
                                   to_iesg_eval=to_iesg_eval),
                              context_instance=RequestContext(request))

class ChangeIanaStateForm(forms.Form):
    state = forms.ModelChoiceField(State.objects.all(), required=False)

    def __init__(self, state_type, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        choices = State.objects.filter(used=True, type=state_type).order_by("order").values_list("pk", "name")
        self.fields['state'].choices = [("", "-------")] + list(choices)

@role_required('Secretariat', 'IANA')
def change_iana_state(request, name, state_type):
    """Change IANA review state of Internet Draft. Normally, this is done via
    automatic sync, but this form allows one to set it manually."""
    doc = get_object_or_404(Document, docalias__name=name)

    state_type = doc.type_id + "-" + state_type

    prev_state = doc.get_state(state_type)

    if request.method == 'POST':
        form = ChangeIanaStateForm(state_type, request.POST)
        if form.is_valid():
            new_state = form.cleaned_data['state']

            if new_state != prev_state:
                save_document_in_history(doc)
                
                doc.set_state(new_state)

                e = add_state_change_event(doc, request.user.person, prev_state, new_state)

                doc.time = e.time
                doc.save()

            return HttpResponseRedirect(doc.get_absolute_url())

    else:
        form = ChangeIanaStateForm(state_type, initial=dict(state=prev_state.pk if prev_state else None))

    return render_to_response('doc/draft/change_iana_state.html',
                              dict(form=form,
                                   doc=doc),
                              context_instance=RequestContext(request))


    
class ChangeStreamForm(forms.Form):
    stream = forms.ModelChoiceField(StreamName.objects.exclude(slug="legacy"), required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)

@login_required
def change_stream(request, name):
    """Change the stream of a Document of type 'draft', notifying parties as necessary
    and logging the change as a comment."""
    doc = get_object_or_404(Document, docalias__name=name)
    if not doc.type_id=='draft':
        raise Http404()

    if not (has_role(request.user, ("Area Director", "Secretariat")) or
            (request.user.is_authenticated() and
             Role.objects.filter(name="chair",
                                 group__acronym__in=StreamName.objects.values_list("slug", flat=True),
                                 person__user=request.user))):
        return HttpResponseForbidden("You do not have permission to view this page")

    login = request.user.person

    if request.method == 'POST':
        form = ChangeStreamForm(request.POST)
        if form.is_valid():
            new_stream = form.cleaned_data['stream']
            comment = form.cleaned_data['comment'].strip()
            old_stream = doc.stream

            if new_stream != old_stream:
                save_document_in_history(doc)
                
                doc.stream = new_stream
                doc.group = Group.objects.get(type="individ")

                e = DocEvent(doc=doc,by=login,type='changed_document')
                e.desc = u"Stream changed to <b>%s</b> from %s"% (new_stream, old_stream or "None")
                e.save()

                email_desc = e.desc

                if comment:
                    c = DocEvent(doc=doc,by=login,type="added_comment")
                    c.desc = comment
                    c.save()
                    email_desc += "\n"+c.desc
                
                doc.time = e.time
                doc.save()

                email_stream_changed(request, doc, old_stream, new_stream, email_desc)

            return HttpResponseRedirect(doc.get_absolute_url())

    else:
        stream = doc.stream
        form = ChangeStreamForm(initial=dict(stream=stream))

    return render_to_response('doc/draft/change_stream.html',
                              dict(form=form,
                                   doc=doc,
                                   ),
                              context_instance=RequestContext(request))

@jsonapi
def doc_ajax_internet_draft(request):
    if request.method != 'GET' or not request.GET.has_key('term'):
        return { 'success' : False, 'error' : 'No term submitted or not GET' }
    q = request.GET.get('term')
    results = DocAlias.objects.filter(name__icontains=q)
    if (results.count() > 20):
        results = results[:20]
    elif results.count() == 0:
        return { 'success' : False, 'error' : "No results" }
    response = [dict(id=r.id, label=r.name) for r in results]
    return response

def collect_email_addresses(emails, doc):
    for author in doc.authors.all():
        if author.address not in emails:
            emails[author.address] = '"%s"' % (author.person.name)
    if doc.group.acronym != 'none':
        for role in doc.group.role_set.filter(name='chair'):
            if role.email.address not in emails:
                emails[role.email.address] = '"%s"' % (role.person.name)
        if doc.group.type.slug == 'wg':
            address = '%s-ads@tools.ietf.org' % doc.group.acronym
            if address not in emails:
                emails[address] = '"%s-ads"' % (doc.group.acronym)
        elif doc.group.type.slug == 'rg':
            email = doc.group.parent.role_set.filter(name='char')[0].email
            if email.address not in emails:
                emails[email.address] = '"%s"' % (email.person.name)
    if doc.shepherd:
        address = doc.shepherd.email_address();
        if address not in emails:
            emails[address] = '"%s"' % (doc.shepherd.name)
    return emails

class ReplacesForm(forms.Form):
    replaces = forms.CharField(max_length=512,widget=forms.HiddenInput)
    comment = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.doc = kwargs.pop('doc')
        super(ReplacesForm, self).__init__(*args, **kwargs)
        drafts = {}
        for d in self.doc.related_that_doc("replaces"):
            drafts[d.id] = d.document.name
        self.initial['replaces'] = json.dumps(drafts)

    def clean_replaces(self):
        data = self.cleaned_data['replaces'].strip()
        if data:
            ids = [int(x) for x in json.loads(data)]
        else:
            return []
        objects = []
        for id in ids:
            try:
                d = DocAlias.objects.get(pk=id)
            except DocAlias.DoesNotExist, e:
                raise forms.ValidationError("ERROR: %s not found for id %d" % DocAlias._meta.verbos_name, id)
            if d.document == self.doc:
                raise forms.ValidationError("ERROR: A draft can't replace itself")
            if d.document.type_id == "draft" and d.document.get_state_slug() == "rfc":
                raise forms.ValidationError("ERROR: A draft can't replace an RFC")
            objects.append(d)
        return objects

def replaces(request, name):
    """Change 'replaces' set of a Document of type 'draft' , notifying parties 
       as necessary and logging the change as a comment."""
    doc = get_object_or_404(Document, docalias__name=name)
    if doc.type_id != 'draft':
        raise Http404
    if not (has_role(request.user, ("Secretariat", "Area Director"))
            or is_authorized_in_doc_stream(request.user, doc)):
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")
    login = request.user.person
    if request.method == 'POST':
        form = ReplacesForm(request.POST, doc=doc)
        if form.is_valid():
            new_replaces = set(form.cleaned_data['replaces'])
            comment = form.cleaned_data['comment'].strip()
            old_replaces = set(doc.related_that_doc("replaces"))
            if new_replaces != old_replaces:
                save_document_in_history(doc)
                emails = {}
                emails = collect_email_addresses(emails, doc)
                relationship = DocRelationshipName.objects.get(slug='replaces')
                for d in old_replaces:
                    if d not in new_replaces:
                        emails = collect_email_addresses(emails, d.document)
                        RelatedDocument.objects.filter(source=doc, target=d,
                         relationship=relationship).delete()
                for d in new_replaces:
                    if d not in old_replaces:
                        emails = collect_email_addresses(emails, d.document)
                        RelatedDocument.objects.create(source=doc, target=d,
                         relationship=relationship)
                e = DocEvent(doc=doc,by=login,type='changed_document')
                new_replaces_names = ", ".join([d.name for d in new_replaces])
                if not new_replaces_names:
                    new_replaces_names = "None"
                old_replaces_names = ", ".join([d.name for d in old_replaces])
                if not old_replaces_names:
                    old_replaces_names = "None"
                e.desc = u"This document now replaces <b>%s</b> instead of %s"% (new_replaces_names, old_replaces_names)
                e.save()
                email_desc = e.desc.replace(", ", "\n    ")
                if comment:
                    c = DocEvent(doc=doc,by=login,type="added_comment")
                    c.desc = comment
                    c.save()
                    email_desc += "\n"+c.desc
                doc.time = e.time
                doc.save()
                email_list = []
                for key in sorted(emails):
                    if emails[key]:
                        email_list.append('%s <%s>' % (emails[key], key))
                    else:
                        email_list.append('<%s>' % key)
                email_string = ", ".join(email_list)
                send_mail(request, email_string,
                 "DraftTracker Mail System <iesg-secretary@ietf.org>",
                 "%s updated by %s" % (doc.name, login),
                 "doc/mail/change_notice.txt",
                 dict(text=html_to_text(email_desc),
                      doc=doc,
                      url=settings.IDTRACKER_BASE_URL + doc.get_absolute_url()))
            return HttpResponseRedirect(doc.get_absolute_url())
    else:
        form = ReplacesForm(doc=doc)
    return render_to_response('doc/draft/change_replaces.html',
                              dict(form=form,
                                   doc=doc,
                                   ),
                              context_instance=RequestContext(request))

class ChangeIntentionForm(forms.Form):
    intended_std_level = forms.ModelChoiceField(IntendedStdLevelName.objects.filter(used=True), empty_label="(None)", required=True, label="Intended RFC status")
    comment = forms.CharField(widget=forms.Textarea, required=False)

def change_intention(request, name):
    """Change the intended publication status of a Document of type 'draft' , notifying parties 
       as necessary and logging the change as a comment."""
    doc = get_object_or_404(Document, docalias__name=name)
    if doc.type_id != 'draft':
        raise Http404

    if not (has_role(request.user, ("Secretariat", "Area Director"))
            or is_authorized_in_doc_stream(request.user, doc)):
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")

    login = request.user.person

    if request.method == 'POST':
        form = ChangeIntentionForm(request.POST)
        if form.is_valid():
            new_level = form.cleaned_data['intended_std_level']
            comment = form.cleaned_data['comment'].strip()
            old_level = doc.intended_std_level

            if new_level != old_level:
                save_document_in_history(doc)
                
                doc.intended_std_level = new_level

                e = DocEvent(doc=doc,by=login,type='changed_document')
                e.desc = u"Intended Status changed to <b>%s</b> from %s"% (new_level,old_level) 
                e.save()

                email_desc = e.desc

                if comment:
                    c = DocEvent(doc=doc,by=login,type="added_comment")
                    c.desc = comment
                    c.save()
                    email_desc += "\n"+c.desc
                
                doc.time = e.time
                doc.save()

                email_ad(request, doc, doc.ad, login, email_desc)

            return HttpResponseRedirect(doc.get_absolute_url())

    else:
        intended_std_level = doc.intended_std_level
        form = ChangeIntentionForm(initial=dict(intended_std_level=intended_std_level))

    return render_to_response('doc/draft/change_intended_status.html',
                              dict(form=form,
                                   doc=doc,
                                   ),
                              context_instance=RequestContext(request))

class EditInfoForm(forms.Form):
    intended_std_level = forms.ModelChoiceField(IntendedStdLevelName.objects.filter(used=True), empty_label="(None)", required=True, label="Intended RFC status")
    area = forms.ModelChoiceField(Group.objects.filter(type="area", state="active"), empty_label="(None - individual submission)", required=False, label="Assigned to area")
    ad = forms.ModelChoiceField(Person.objects.filter(role__name="ad", role__group__state="active").order_by('name'), label="Responsible AD", empty_label="(None)", required=True)
    create_in_state = forms.ModelChoiceField(State.objects.filter(used=True, type="draft-iesg", slug__in=("pub-req", "watching")), empty_label=None, required=False)
    notify = forms.CharField(max_length=255, label="Notice emails", help_text="Separate email addresses with commas", required=False)
    note = forms.CharField(widget=forms.Textarea, label="IESG note", required=False)
    telechat_date = forms.TypedChoiceField(coerce=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date(), empty_value=None, required=False, widget=forms.Select(attrs={'onchange':'make_bold()'}))
    returning_item = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        # if previous AD is now ex-AD, append that person to the list
        ad_pk = self.initial.get('ad')
        choices = self.fields['ad'].choices
        if ad_pk and ad_pk not in [pk for pk, name in choices]:
            self.fields['ad'].choices = list(choices) + [("", "-------"), (ad_pk, Person.objects.get(pk=ad_pk).plain_name())]
        
        # telechat choices
        dates = [d.date for d in TelechatDate.objects.active().order_by('date')]
        init = kwargs['initial']['telechat_date']
        if init and init not in dates:
            dates.insert(0, init)

        self.fields['telechat_date'].choices = [("", "(not on agenda)")] + [(d, d.strftime("%Y-%m-%d")) for d in dates]

        # returning item is rendered non-standard
        self.standard_fields = [x for x in self.visible_fields() if x.name not in ('returning_item',)]

    def clean_note(self):
        return self.cleaned_data['note'].replace('\r', '').strip()


def get_initial_notify(doc):
    # set change state notice to something sensible
    receivers = []
    if doc.group.type_id in ("individ", "area"):
        for a in doc.authors.all():
            receivers.append(a.address)
    else:
        receivers.append("%s-chairs@%s" % (doc.group.acronym, settings.TOOLS_SERVER))
        for editor in Email.objects.filter(role__name="editor", role__group=doc.group):
            receivers.append(e.address)

    receivers.append("%s@%s" % (doc.name, settings.TOOLS_SERVER))
    return ", ".join(receivers)

def to_iesg(request,name):
    """ Submit an IETF stream document to the IESG for publication """ 
    doc = get_object_or_404(Document, docalias__name=name, stream='ietf')

    if doc.get_state_slug('draft') == "expired" or doc.get_state_slug('draft-iesg') == 'pub-req' :
        raise Http404()

    if not is_authorized_in_doc_stream(request.user, doc):
        raise Http404()
    
    target_state={
        'iesg' : State.objects.get(type='draft-iesg',slug='pub-req'),
        'wg'   : State.objects.get(type='draft-stream-ietf',slug='sub-pub'),
    }

    warn={}
    if not doc.intended_std_level:
        warn['intended_std_level'] = True
    if not doc.shepherd:
        warn['shepherd'] = True
    shepherd_writeup = doc.latest_event(WriteupDocEvent, type="changed_protocol_writeup")
    if not shepherd_writeup:
        warn['shepherd_writeup'] = True
    tags = doc.tags.filter(slug__in=get_tags_for_stream_id(doc.stream_id))
    if tags:
        warn['tags'] = True
    notify = doc.notify
    if not notify:
        notify = get_initial_notify(doc)
    ad = doc.ad or doc.group.ad

    if request.method == 'POST':

        if request.POST.get("confirm", ""): 

            save_document_in_history(doc)

            login = request.user.person

            changes = []

            if not doc.get_state("draft-iesg"):

                e = DocEvent()
                e.type = "started_iesg_process"
                e.by = login
                e.doc = doc
                e.desc = "IESG process started in state <b>%s</b>" % target_state['iesg'].name
                e.save()

            if not doc.get_state('draft-iesg')==target_state['iesg']:
                doc.set_state(target_state['iesg'])
                changes.append("IESG state set to %s" % target_state['iesg'].name)
            if not doc.get_state('draft-ietf-stream')==target_state['wg']:
                doc.set_state(target_state['wg'])
                changes.append("Working group state set to %s" % target_state['wg'].name)

            if not doc.ad == ad :
                doc.ad = ad
                changes.append("Responsible AD changed to %s" % doc.ad)

            if not doc.notify == notify :
                doc.notify = notify
                changes.append("State Change Notice email list changed to %s" % doc.notify)

	    # Get the last available writeup
            previous_writeup = doc.latest_event(WriteupDocEvent,type="changed_protocol_writeup")
            if previous_writeup != None:
                changes.append(previous_writeup.text)

            for c in changes:
                e = DocEvent(doc=doc, by=login)
                e.desc = c
                e.type = "changed_document"
                e.save()

            # Is this still necessary? I remember Henrik planning to have the model take care of this.
            doc.time = datetime.datetime.now()

            doc.save()

            extra = {}
            extra['Cc'] = "%s-chairs@tools.ietf.org, iesg-secretary@ietf.org, %s" % (doc.group.acronym,doc.notify)
            send_mail(request=request,
                      to = doc.ad.email_address(),
                      frm = login.formatted_email(),
                      subject = "Publication has been requested for %s-%s" % (doc.name,doc.rev),
                      template = "doc/submit_to_iesg_email.txt",
                      context = dict(doc=doc,login=login,url="%s%s"%(settings.IDTRACKER_BASE_URL,doc.get_absolute_url()),),
                      extra = extra)

        return HttpResponseRedirect(doc.get_absolute_url())

    return render_to_response('doc/submit_to_iesg.html',
                              dict(doc=doc,
                                   warn=warn,
                                   target_state=target_state,
                                   ad=ad,
                                   shepherd_writeup=shepherd_writeup,
                                   tags=tags,
                                   notify=notify,
                                  ),
                              context_instance=RequestContext(request))

@role_required('Area Director','Secretariat')
def edit_info(request, name):
    """Edit various Internet Draft attributes, notifying parties as
    necessary and logging changes as document events."""
    doc = get_object_or_404(Document, docalias__name=name)
    if doc.get_state_slug() == "expired":
        raise Http404()

    login = request.user.person

    new_document = False
    if not doc.get_state("draft-iesg"): # FIXME: should probably receive "new document" as argument to view instead of this
        new_document = True
        doc.notify = get_initial_notify(doc)

    e = doc.latest_event(TelechatDocEvent, type="scheduled_for_telechat")
    initial_telechat_date = e.telechat_date if e else None
    initial_returning_item = bool(e and e.returning_item)

    if request.method == 'POST':
        form = EditInfoForm(request.POST,
                            initial=dict(ad=doc.ad_id,
                                         telechat_date=initial_telechat_date))
        if form.is_valid():
            save_document_in_history(doc)
            
            r = form.cleaned_data
            if new_document:
                doc.set_state(r['create_in_state'])

                # Is setting the WG state here too much of a hidden side-effect?
                if r['create_in_state'].slug=='pub-req':
                    if doc.stream and ( doc.stream.slug=='ietf' ) and doc.group and ( doc.group.type.name=='WG'):
                        submitted_state = State.objects.get(type='draft-stream-ietf',slug='sub-pub')
                        doc.set_state(submitted_state)
                        e = DocEvent()
                        e.type = "changed_document"
                        e.by = login
                        e.doc = doc
                        e.desc = "Working group state set to %s" % submitted_state.name
                        e.save()

                # fix so Django doesn't barf in the diff below because these
                # fields can't be NULL
                doc.ad = r['ad']

                replaces = Document.objects.filter(docalias__relateddocument__source=doc, docalias__relateddocument__relationship="replaces")
                if replaces:
                    # this should perhaps be somewhere else, e.g. the
                    # place where the replace relationship is established?
                    e = DocEvent()
                    e.type = "added_comment"
                    e.by = Person.objects.get(name="(System)")
                    e.doc = doc
                    e.desc = "Earlier history may be found in the Comment Log for <a href=\"%s\">%s</a>" % (replaces[0], replaces[0].get_absolute_url())
                    e.save()

                e = DocEvent()
                e.type = "started_iesg_process"
                e.by = login
                e.doc = doc
                e.desc = "IESG process started in state <b>%s</b>" % doc.get_state("draft-iesg").name
                e.save()
                    
            orig_ad = doc.ad

            changes = []

            def desc(attr, new, old):
                entry = "%(attr)s changed to <b>%(new)s</b> from <b>%(old)s</b>"
                if new_document:
                    entry = "%(attr)s changed to <b>%(new)s</b>"
                
                return entry % dict(attr=attr, new=new, old=old)
            
            def diff(attr, name):
                v = getattr(doc, attr)
                if r[attr] != v:
                    changes.append(desc(name, r[attr], v))
                    setattr(doc, attr, r[attr])

            # update the attributes, keeping track of what we're doing
            diff('intended_std_level', "Intended Status")
            diff('ad', "Responsible AD")
            diff('notify', "State Change Notice email list")

            if r['note'] != doc.note:
                if not r['note']:
                    if doc.note:
                        changes.append("Note field has been cleared")
                else:
                    if doc.note:
                        changes.append("Note changed to '%s'" % r['note'])
                    else:
                        changes.append("Note added '%s'" % r['note'])
                    
                doc.note = r['note']

            if doc.group.type_id in ("individ", "area"):
                if not r["area"]:
                    r["area"] = Group.objects.get(type="individ")

                if r["area"] != doc.group:
                    if r["area"].type_id == "area":
                        changes.append(u"Assigned to <b>%s</b>" % r["area"].name)
                    else:
                        changes.append(u"No longer assigned to any area")
                    doc.group = r["area"]

            for c in changes:
                e = DocEvent(doc=doc, by=login)
                e.desc = c
                e.type = "changed_document"
                e.save()

            update_telechat(request, doc, login,
                            r['telechat_date'], r['returning_item'])

            doc.time = datetime.datetime.now()

            if changes and not new_document:
                email_ad(request, doc, orig_ad, login, "\n".join(changes))
                
            doc.save()
            return HttpResponseRedirect(doc.get_absolute_url())
    else:
        init = dict(intended_std_level=doc.intended_std_level_id,
                    area=doc.group_id,
                    ad=doc.ad_id,
                    notify=doc.notify,
                    note=doc.note,
                    telechat_date=initial_telechat_date,
                    returning_item=initial_returning_item,
                    )

        form = EditInfoForm(initial=init)

    # optionally filter out some fields
    if not new_document:
        form.standard_fields = [x for x in form.standard_fields if x.name != "create_in_state"]
    if doc.group.type_id not in ("individ", "area"):
        form.standard_fields = [x for x in form.standard_fields if x.name != "area"]

    return render_to_response('doc/draft/edit_info.html',
                              dict(doc=doc,
                                   form=form,
                                   user=request.user,
                                   login=login,
                                   ballot_issued=doc.latest_event(type="sent_ballot_announcement")),
                              context_instance=RequestContext(request))

@role_required('Area Director','Secretariat')
def request_resurrect(request, name):
    """Request resurrect of expired Internet Draft."""
    doc = get_object_or_404(Document, docalias__name=name)
    if doc.get_state_slug() != "expired":
        raise Http404()

    login = request.user.person

    if request.method == 'POST':
        email_resurrect_requested(request, doc, login)
        
        e = DocEvent(doc=doc, by=login)
        e.type = "requested_resurrect"
        e.desc = "Resurrection was requested"
        e.save()
        
        return HttpResponseRedirect(doc.get_absolute_url())
  
    return render_to_response('doc/draft/request_resurrect.html',
                              dict(doc=doc,
                                   back_url=doc.get_absolute_url()),
                              context_instance=RequestContext(request))

@role_required('Secretariat')
def resurrect(request, name):
    """Resurrect expired Internet Draft."""
    doc = get_object_or_404(Document, docalias__name=name)
    if doc.get_state_slug() != "expired":
        raise Http404()

    login = request.user.person

    if request.method == 'POST':
        save_document_in_history(doc)
        
        e = doc.latest_event(type__in=('requested_resurrect', "completed_resurrect"))
        if e and e.type == 'requested_resurrect':
            email_resurrection_completed(request, doc, requester=e.by)
            
        e = DocEvent(doc=doc, by=login)
        e.type = "completed_resurrect"
        e.desc = "Resurrection was completed"
        e.save()
        
        doc.set_state(State.objects.get(used=True, type="draft", slug="active"))
        doc.expires = datetime.datetime.now() + datetime.timedelta(settings.INTERNET_DRAFT_DAYS_TO_EXPIRE)
        doc.time = datetime.datetime.now()
        doc.save()
        return HttpResponseRedirect(doc.get_absolute_url())
  
    return render_to_response('doc/draft/resurrect.html',
                              dict(doc=doc,
                                   back_url=doc.get_absolute_url()),
                              context_instance=RequestContext(request))

class NotifyForm(forms.Form):
    notify = forms.CharField(max_length=255, label="Notice emails", help_text="Separate email addresses with commas", required=False)


@role_required('Area Director', 'Secretariat')
def edit_notices(request, name):
    """Change the set of email addresses document change notificaitions go to."""

    doc = get_object_or_404(Document, type="draft", name=name)

    if request.method == 'POST':

        if "save_addresses" in request.POST:
            form = NotifyForm(request.POST)
            if form.is_valid():

                doc.notify = form.cleaned_data['notify']
                doc.save()

                login = request.user.person
                c = DocEvent(type="added_comment", doc=doc, by=login)
                c.desc = "Notification list changed to : "+doc.notify
                c.save()

                return redirect('doc_view', name=doc.name)

        elif "regenerate_addresses" in request.POST:
            init = { "notify" : get_initial_notify(doc) }
            form = NotifyForm(initial=init)

        # Protect from handcrufted POST
        else:
            init = { "notify" : doc.notify }
            form = NotifyForm(initial=init)

    else:

        init = { "notify" : doc.notify }
        form = NotifyForm(initial=init)

    return render_to_response('doc/draft/change_notify.html',
                              {'form':   form,
                               'doc': doc,
                              },
                              context_instance = RequestContext(request))

class TelechatForm(forms.Form):
    telechat_date = forms.TypedChoiceField(coerce=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date(), empty_value=None, required=False)
    returning_item = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        dates = [d.date for d in TelechatDate.objects.active().order_by('date')]
        init = kwargs['initial'].get("telechat_date")
        if init and init not in dates:
            dates.insert(0, init)

        self.fields['telechat_date'].choices = [("", "(not on agenda)")] + [(d, d.strftime("%Y-%m-%d")) for d in dates]
        

@role_required("Area Director", "Secretariat")
def telechat_date(request, name):
    doc = get_object_or_404(Document, type="draft", name=name)
    login = request.user.person

    e = doc.latest_event(TelechatDocEvent, type="scheduled_for_telechat")
    initial_returning_item = bool(e and e.returning_item)

    initial = dict(telechat_date=e.telechat_date if e else None,
                   returning_item = initial_returning_item,
                  )
    if request.method == "POST":
        form = TelechatForm(request.POST, initial=initial)

        if form.is_valid():
            update_telechat(request, doc, login, form.cleaned_data['telechat_date'],form.cleaned_data['returning_item'])
            return redirect('doc_view', name=doc.name)
    else:
        form = TelechatForm(initial=initial)

    return render_to_response('doc/edit_telechat_date.html',
                              dict(doc=doc,
                                   form=form,
                                   user=request.user,
                                   login=login),
                              context_instance=RequestContext(request))


class IESGNoteForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea, label="IESG note", required=False)

    def clean_note(self):
        # not muning the database content to use html line breaks --
        # that has caused a lot of pain in the past.
        return self.cleaned_data['note'].replace('\r', '').strip()

@role_required("Area Director", "Secretariat")
def edit_iesg_note(request, name):
    doc = get_object_or_404(Document, type="draft", name=name)
    login = request.user.person

    initial = dict(note=doc.note)

    if request.method == "POST":
        form = IESGNoteForm(request.POST, initial=initial)

        if form.is_valid():
            new_note = form.cleaned_data['note']
            if new_note != doc.note:
                if not new_note:
                    if doc.note:
                        log_message = "Note field has been cleared"
                else:
                    if doc.note:
                        log_message = "Note changed to '%s'" % new_note
                    else:
                        log_message = "Note added '%s'" % new_note

                doc.note = new_note
                doc.save()

                c = DocEvent(type="added_comment", doc=doc, by=login)
                c.desc = log_message
                c.save()

            return redirect('doc_view', name=doc.name)
    else:
        form = IESGNoteForm(initial=initial)

    return render_to_response('doc/draft/edit_iesg_note.html',
                              dict(doc=doc,
                                   form=form,
                                   ),
                              context_instance=RequestContext(request))

class ShepherdWriteupUploadForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea, label="Shepherd writeup", help_text="Edit the shepherd writeup", required=False)
    txt = forms.FileField(label=".txt format", help_text="Or upload a .txt file", required=False)

    def clean_content(self):
        return self.cleaned_data["content"].replace("\r", "")

    def clean_txt(self):
        return get_cleaned_text_file_content(self.cleaned_data["txt"])

def edit_shepherd_writeup(request, name):
    """Change this document's shepherd writeup"""
    doc = get_object_or_404(Document, type="draft", name=name)

    can_edit_stream_info = is_authorized_in_doc_stream(request.user, doc)
    can_edit_shepherd_writeup = can_edit_stream_info or user_is_person(request.user, doc.shepherd) or has_role(request.user, ["Area Director"])

    if not can_edit_shepherd_writeup:
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")

    login = request.user.person

    if request.method == 'POST':
        if "submit_response" in request.POST:
            form = ShepherdWriteupUploadForm(request.POST, request.FILES)
            if form.is_valid():
                
                from_file = form.cleaned_data['txt']
                if from_file:
                     writeup = from_file
                else:
                     writeup = form.cleaned_data['content']
                e = WriteupDocEvent(doc=doc, by=login, type="changed_protocol_writeup")

		# Add the shepherd writeup to description if the document is in submitted for publication state
                stream_state = doc.get_state("draft-stream-%s" % doc.stream_id)
                iesg_state   = doc.get_state("draft-iesg")
                if (iesg_state or (stream_state and stream_state.slug=='sub-pub')):
                    e.desc = writeup
                else:
                    e.desc = "Changed document writeup"

                e.text = writeup
                e.save()
            
                return redirect('doc_view', name=doc.name)

        elif "reset_text" in request.POST:

            init = { "content": render_to_string("doc/shepherd_writeup.txt",dict(doc=doc))}
            form = ShepherdWriteupUploadForm(initial=init)

        # Protect against handcrufted malicious posts
        else:
            form = None

    else:
        form = None

    if not form:
        init = { "content": ""}

        previous_writeup = doc.latest_event(WriteupDocEvent,type="changed_protocol_writeup")
        if previous_writeup:
            init["content"] = previous_writeup.text
        else:
            init["content"] = render_to_string("doc/shepherd_writeup.txt",
                                                dict(doc=doc),
                                              )
        form = ShepherdWriteupUploadForm(initial=init)

    return render_to_response('doc/draft/change_shepherd_writeup.html',
                              {'form': form,
                               'doc' : doc,
                              },
                              context_instance=RequestContext(request))

class ShepherdForm(forms.Form):
    shepherd = EmailsField(label="Shepherd", required=False)

    def clean_shepherd(self):
        data = self.cleaned_data['shepherd']
        if len(data)>1:
            raise forms.ValidationError("Please choose at most one shepherd.")
        return data

def edit_shepherd(request, name):
    """Change the shepherd for a Document"""
    # TODO - this shouldn't be type="draft" specific
    doc = get_object_or_404(Document, type="draft", name=name)

    can_edit_stream_info = is_authorized_in_doc_stream(request.user, doc)

    if not can_edit_stream_info:
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")

    if request.method == 'POST':
        form = ShepherdForm(request.POST)
        if form.is_valid():

            if form.cleaned_data['shepherd']:
                doc.shepherd = form.cleaned_data['shepherd'][0].person
            else:
                doc.shepherd = None
            doc.save()
   
            login = request.user.person
            c = DocEvent(type="added_comment", doc=doc, by=login)
            c.desc = "Document shepherd changed to "+ (doc.shepherd.name if doc.shepherd else "(None)")
            c.save()

            return redirect('doc_view', name=doc.name)

    else:
        current_shepherd = None
        if doc.shepherd:
            e = doc.shepherd.email_set.order_by("-active", "-time")
            if e:
                current_shepherd=e[0].pk
        init = { "shepherd": current_shepherd}
        form = ShepherdForm(initial=init)

    return render_to_response('doc/change_shepherd.html',
                              {'form':   form,
                               'doc': doc,
                              },
                              context_instance = RequestContext(request))

class AdForm(forms.Form):
    ad = forms.ModelChoiceField(Person.objects.filter(role__name="ad", role__group__state="active").order_by('name'), 
                                label="Shepherding AD", empty_label="(None)", required=True)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        # if previous AD is now ex-AD, append that person to the list
        ad_pk = self.initial.get('ad')
        choices = self.fields['ad'].choices
        if ad_pk and ad_pk not in [pk for pk, name in choices]:
            self.fields['ad'].choices = list(choices) + [("", "-------"), (ad_pk, Person.objects.get(pk=ad_pk).plain_name())]

@role_required("Area Director", "Secretariat")
def edit_ad(request, name):
    """Change the shepherding Area Director for this draft."""

    doc = get_object_or_404(Document, type="draft", name=name)

    if request.method == 'POST':
        form = AdForm(request.POST)
        if form.is_valid():

            doc.ad = form.cleaned_data['ad']
            doc.save()
    
            login = request.user.person
            c = DocEvent(type="added_comment", doc=doc, by=login)
            c.desc = "Shepherding AD changed to "+doc.ad.name
            c.save()

            return redirect('doc_view', name=doc.name)

    else:
        init = { "ad" : doc.ad_id }
        form = AdForm(initial=init)

    return render_to_response('doc/draft/change_ad.html',
                              {'form':   form,
                               'doc': doc,
                              },
                              context_instance = RequestContext(request))

class ConsensusForm(forms.Form):
    consensus = forms.ChoiceField(choices=(("", "Unknown"), ("Yes", "Yes"), ("No", "No")), required=True)

def edit_consensus(request, name):
    """Change whether the draft is a consensus document or not."""

    doc = get_object_or_404(Document, type="draft", name=name)

    if not (has_role(request.user, ("Secretariat", "Area Director"))
            or is_authorized_in_doc_stream(request.user, doc)):
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")

    e = doc.latest_event(ConsensusDocEvent, type="changed_consensus")
    prev_consensus = e and e.consensus

    if request.method == 'POST':
        form = ConsensusForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["consensus"] != bool(prev_consensus):
                e = ConsensusDocEvent(doc=doc, type="changed_consensus", by=request.user.person)
                e.consensus = form.cleaned_data["consensus"] == "Yes"

                e.desc = "Changed consensus to <b>%s</b> from %s" % (nice_consensus(e.consensus),
                                                                     nice_consensus(prev_consensus))

                e.save()

            return redirect('doc_view', name=doc.name)

    else:
        form = ConsensusForm(initial=dict(consensus=nice_consensus(prev_consensus).replace("Unknown", "")))

    return render_to_response('doc/draft/change_consensus.html',
                              {'form': form,
                               'doc': doc,
                              },
                              context_instance = RequestContext(request))

class PublicationForm(forms.Form):
    subject = forms.CharField(max_length=200, required=True)
    body = forms.CharField(widget=forms.Textarea, required=True)

def request_publication(request, name):
    """Request publication by RFC Editor for a document which hasn't
    been through the IESG ballot process."""

    doc = get_object_or_404(Document, type="draft", name=name, stream__in=("iab", "ise", "irtf"))

    if not is_authorized_in_doc_stream(request.user, doc):
        return HttpResponseForbidden("You do not have the necessary permissions to view this page")

    consensus_event = doc.latest_event(ConsensusDocEvent, type="changed_consensus")

    m = Message()
    m.frm = request.user.person.formatted_email()
    m.to = "RFC Editor <rfc-editor@rfc-editor.org>"
    m.by = request.user.person

    next_state = State.objects.get(used=True, type="draft-stream-%s" % doc.stream.slug, slug="rfc-edit")

    if request.method == 'POST' and not request.POST.get("reset"):
        form = PublicationForm(request.POST)
        if form.is_valid():
            if not request.REQUEST.get("skiprfceditorpost"):
                # start by notifying the RFC Editor
                import ietf.sync.rfceditor
                response, error = ietf.sync.rfceditor.post_approved_draft(settings.RFC_EDITOR_SYNC_NOTIFICATION_URL, doc.name)
                if error:
                    return render_to_response('doc/draft/rfceditor_post_approved_draft_failed.html',
                                      dict(name=doc.name,
                                           response=response,
                                           error=error),
                                      context_instance=RequestContext(request))

            m.subject = form.cleaned_data["subject"]
            m.body = form.cleaned_data["body"]
            m.save()

            if doc.group.acronym != "none":
                m.related_groups = [doc.group]
            m.related_docs = [doc]

            send_mail_message(request, m)

            # IANA copy
            m.to = settings.IANA_APPROVE_EMAIL
            send_mail_message(request, m, extra=extra_automation_headers(doc))

            e = DocEvent(doc=doc, type="requested_publication", by=request.user.person)
            e.desc = "Sent request for publication to the RFC Editor"
            e.save()

            # change state
            prev_state = doc.get_state(next_state.type_id)
            if next_state != prev_state:
                doc.set_state(next_state)
                e = add_state_change_event(doc, request.user.person, prev_state, next_state)
                doc.time = e.time
                doc.save()

            return redirect('doc_view', name=doc.name)

    else:
        if doc.intended_std_level_id in ("std", "ds", "ps", "bcp"):
            action = "Protocol Action"
        else:
            action = "Document Action"

        from ietf.doc.templatetags.mail_filters import std_level_prompt

        subject = "%s: '%s' to %s (%s-%s.txt)" % (action, doc.title, std_level_prompt(doc), doc.name, doc.rev)

        body = generate_publication_request(request, doc)

        form = PublicationForm(initial=dict(subject=subject,
                                            body=body))

    return render_to_response('doc/draft/request_publication.html',
                              dict(form=form,
                                   doc=doc,
                                   message=m,
                                   next_state=next_state,
                                   consensus_filled_in=consensus_event != None,
                                   ),
                              context_instance = RequestContext(request))

class AdoptDraftForm(forms.Form):
    group = forms.ModelChoiceField(queryset=Group.objects.filter(type__in=["wg", "rg"], state="active").order_by("-type", "acronym"), required=True, empty_label=None)
    comment = forms.CharField(widget=forms.Textarea, required=False, label="Comment", help_text="Optional comment explaining the reasons for the adoption")
    weeks = forms.IntegerField(required=False, label="Expected weeks in adoption state")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")

        super(AdoptDraftForm, self).__init__(*args, **kwargs)

        if has_role(user, "Secretariat"):
            pass # all groups
        else:
            self.fields["group"].queryset = self.fields["group"].queryset.filter(role__person__user=user, role__name__in=("chair", "delegate", "secr")).distinct()

        self.fields['group'].choices = [(g.pk, '%s - %s' % (g.acronym, g.name)) for g in self.fields["group"].queryset]


@login_required
def adopt_draft(request, name):
    doc = get_object_or_404(Document, type="draft", name=name)

    if not can_adopt_draft(request.user, doc):
        return HttpResponseForbidden("You don't have permission to access this page")

    if request.method == 'POST':
        form = AdoptDraftForm(request.POST, user=request.user)

        if form.is_valid():
            # adopt
            by = request.user.person

            save_document_in_history(doc)

            doc.time = datetime.datetime.now()

            group = form.cleaned_data["group"]
            if group.type.slug == "rg":
                new_stream = StreamName.objects.get(slug="irtf")                
                adopt_state_slug = "active"
            else:
                new_stream = StreamName.objects.get(slug="ietf")                
                adopt_state_slug = "c-adopt"

            # stream
            if doc.stream != new_stream:
                e = DocEvent(type="changed_stream", time=doc.time, by=by, doc=doc)
                e.desc = u"Changed stream to <b>%s</b>" % new_stream.name
                if doc.stream:
                    e.desc += u" from %s" % doc.stream.name
                e.save()
                doc.stream = new_stream

            # group
            if group != doc.group:
                e = DocEvent(type="changed_group", time=doc.time, by=by, doc=doc)
                e.desc = u"Changed group to <b>%s (%s)</b>" % (group.name, group.acronym.upper())
                if doc.group.type_id != "individ":
                    e.desc += " from %s (%s)" % (doc.group.name, doc.group.acronym.upper())
                e.save()
                doc.group = group

            doc.save()

            # state
            prev_state = doc.get_state("draft-stream-%s" % doc.stream_id)
            new_state = State.objects.get(slug=adopt_state_slug, type="draft-stream-%s" % doc.stream_id, used=True)
            if new_state != prev_state:
                doc.set_state(new_state)
                e = add_state_change_event(doc, by, prev_state, new_state, timestamp=doc.time)

                due_date = None
                if form.cleaned_data["weeks"] != None:
                    due_date = datetime.date.today() + datetime.timedelta(weeks=form.cleaned_data["weeks"])

                update_reminder(doc, "stream-s", e, due_date)

            # comment
            comment = form.cleaned_data["comment"].strip()
            if comment:
                e = DocEvent(type="added_comment", time=doc.time, by=by, doc=doc)
                e.desc = comment
                e.save()

            email_draft_adopted(request, doc, by, comment)
                
            return HttpResponseRedirect(doc.get_absolute_url())
    else:
        form = AdoptDraftForm(user=request.user)

    return render_to_response('doc/draft/adopt_draft.html',
                              {'doc': doc,
                               'form': form,
                              },
                              context_instance=RequestContext(request))

class ChangeStreamStateForm(forms.Form):
    new_state = forms.ModelChoiceField(queryset=State.objects.filter(used=True), label='State', help_text=u"Only select 'Submitted to IESG for Publication' to correct errors. Use the document's main page to request publication.")
    weeks = forms.IntegerField(label='Expected weeks in state',required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False, help_text="Optional comment for the document history")
    tags = forms.ModelMultipleChoiceField(queryset=DocTagName.objects.filter(used=True), widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, **kwargs):
        doc = kwargs.pop("doc")
        state_type = kwargs.pop("state_type")
        super(ChangeStreamStateForm, self).__init__(*args, **kwargs)

        f = self.fields["new_state"]
        f.queryset = f.queryset.filter(type=state_type)
        if doc.group:
            unused_states = doc.group.unused_states.values_list("pk", flat=True)
            f.queryset = f.queryset.exclude(pk__in=unused_states)
        f.label = state_type.label

        f = self.fields['tags']
        f.queryset = f.queryset.filter(slug__in=get_tags_for_stream_id(doc.stream_id))
        if doc.group:
            unused_tags = doc.group.unused_tags.values_list("pk", flat=True)
            f.queryset = f.queryset.exclude(pk__in=unused_tags)

def next_states_for_stream_state(doc, state_type, current_state):
    # find next states
    next_states = []
    if current_state:
        next_states = current_state.next_states.all()

        if doc.stream_id == "ietf" and doc.group:
            transitions = doc.group.groupstatetransitions_set.filter(state=current_state)
            if transitions:
                next_states = transitions[0].next_states.all()
    else:
        # return the initial state
        states = State.objects.filter(used=True, type=state_type).order_by('order')
        if states:
            next_states = states[:1]

    if doc.group:
        unused_states = doc.group.unused_states.values_list("pk", flat=True)
        next_states = [n for n in next_states if n.pk not in unused_states]

    return next_states

@login_required
def change_stream_state(request, name, state_type):
    doc = get_object_or_404(Document, type="draft", name=name)
    if not doc.stream:
        raise Http404

    state_type = get_object_or_404(StateType, slug=state_type)

    if not is_authorized_in_doc_stream(request.user, doc):
        return HttpResponseForbidden("You don't have permission to access this page")

    prev_state = doc.get_state(state_type.slug)
    next_states = next_states_for_stream_state(doc, state_type, prev_state)

    if request.method == 'POST':
        form = ChangeStreamStateForm(request.POST, doc=doc, state_type=state_type)
        if form.is_valid():
            by = request.user.person

            save_document_in_history(doc)

            doc.time = datetime.datetime.now()
            comment = form.cleaned_data["comment"].strip()

            # state
            new_state = form.cleaned_data["new_state"]
            if new_state != prev_state:
                doc.set_state(new_state)
                e = add_state_change_event(doc, by, prev_state, new_state, timestamp=doc.time)

                due_date = None
                if form.cleaned_data["weeks"] != None:
                    due_date = datetime.date.today() + datetime.timedelta(weeks=form.cleaned_data["weeks"])

                update_reminder(doc, "stream-s", e, due_date)

                email_stream_state_changed(request, doc, prev_state, new_state, by, comment)

            # tags
            existing_tags = set(doc.tags.all())
            new_tags = set(form.cleaned_data["tags"])

            if existing_tags != new_tags:
                doc.tags = new_tags

                e = DocEvent(type="changed_document", time=doc.time, by=by, doc=doc)
                added_tags = new_tags - existing_tags
                removed_tags = existing_tags - new_tags
                l = []
                if added_tags:
                    l.append(u"Tag%s %s set." % (pluralize(added_tags), ", ".join(t.name for t in added_tags)))
                if removed_tags:
                    l.append(u"Tag%s %s cleared." % (pluralize(removed_tags), ", ".join(t.name for t in removed_tags)))
                e.desc = " ".join(l)
                e.save()

                email_stream_tags_changed(request, doc, added_tags, removed_tags, by, comment)

            # comment
            if comment:
                e = DocEvent(type="added_comment", time=doc.time, by=by, doc=doc)
                e.desc = comment
                e.save()

            return HttpResponseRedirect(doc.get_absolute_url())
    else:
        form = ChangeStreamStateForm(initial=dict(new_state=prev_state.pk if prev_state else None),
                                     doc=doc, state_type=state_type)

    milestones = doc.groupmilestone_set.all()


    return render_to_response("doc/draft/change_stream_state.html",
                              {"doc": doc,
                               "form": form,
                               "milestones": milestones,
                               "state_type": state_type,
                               "next_states": next_states,
                              },
                              context_instance=RequestContext(request))
