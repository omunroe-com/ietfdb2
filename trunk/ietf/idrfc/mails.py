# generation of mails 

import textwrap
from datetime import datetime, date, time, timedelta

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.urlresolvers import reverse as urlreverse

from ietf.utils.mail import send_mail, send_mail_text
from ietf.idtracker.models import *
from ietf.ipr.search import iprs_from_docs
from ietf.ietfworkflows.streams import (get_stream_from_draft)
from ietf.ietfworkflows.models import (Stream)

def email_state_changed(request, doc, text):
    to = [x.strip() for x in doc.idinternal.state_change_notice_to.replace(';', ',').split(',')]
    if to:
        send_mail(request, to, None,
              "ID Tracker State Update Notice: %s" % doc.file_tag(),
              "idrfc/state_changed_email.txt",
              dict(text=text,
                   url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()))

def html_to_text(html):
    return strip_tags(html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("<br>", "\n"))
    
def email_owner(request, doc, owner, changed_by, text, subject=None):
    if not owner or not changed_by or owner == changed_by:
        return

    to = u"%s <%s>" % owner.person.email()
    send_mail(request, to,
              "DraftTracker Mail System <iesg-secretary@ietf.org>",
              "%s updated by %s" % (doc.file_tag(), changed_by),
              "idrfc/change_notice.txt",
              dict(text=html_to_text(text),
                   doc=doc,
                   url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()))

def full_intended_status(intended_status):
    s = str(intended_status)
    # FIXME: this should perhaps be defined in the db
    if "Informational" in s:
        return "an Informational RFC"
    elif "Experimental" in s:
        return "an Experimental RFC"
    elif "Proposed" in s:
        return "a Proposed Standard"
    elif "Draft" in s:
        return "a Draft Standard"
    elif "BCP" in s:
        return "a BCP"
    elif "Standard" in s:
        return "a Full Standard"
    elif "Request" in s or "None" in s:
        return "*** YOU MUST SELECT AN INTENDED STATUS FOR THIS DRAFT AND REGENERATE THIS TEXT ***"
    else:
        return "a %s" % s
    
def generate_last_call_announcement(request, doc):
    status = full_intended_status(doc.intended_status).replace("a ", "").replace("an ", "")
    
    expiration_date = date.today() + timedelta(days=14)
    cc = []
    if doc.group.acronym_id == Acronym.INDIVIDUAL_SUBMITTER:
        group = "an individual submitter"
        expiration_date += timedelta(days=14)
    else:
        group = "the %s WG (%s)" % (doc.group.name, doc.group.acronym)
        cc.append(doc.group.ietfwg.email_address)

    urls = []
    docs = [d.document() for d in doc.idinternal.ballot_set()]
    for d in docs:
        d.full_status = full_intended_status(d.intended_status)
        d.filled_title = textwrap.fill(d.title, width=70, subsequent_indent=" " * 3)
        urls.append(settings.IDTRACKER_BASE_URL + d.idinternal.get_absolute_url())
    
    iprs, docs = iprs_from_docs(docs)
    if iprs:
        ipr_links = [ urlreverse("ietf.ipr.views.show", kwargs=dict(ipr_id=i.ipr_id)) for i in iprs]
        ipr_links = [ settings.IDTRACKER_BASE_URL+url if not url.startswith("http") else url for url in ipr_links ]
    else:
        ipr_links = None

    return render_to_string("idrfc/last_call_announcement.txt",
                            dict(doc=doc,
                                 doc_url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url(),
                                 expiration_date=expiration_date.strftime("%Y-%m-%d"), #.strftime("%B %-d, %Y"),
                                 cc=", ".join("<%s>" % e for e in cc),
                                 group=group,
                                 docs=docs,
                                 urls=urls,
                                 status=status,
                                 impl_report="Draft" in status or "Full" in status,
                                 ipr_links=ipr_links,
                                 )
                            )

def generate_approval_mail(request, doc):
    if doc.idinternal.cur_state_id in IDState.DO_NOT_PUBLISH_STATES or doc.idinternal.via_rfc_editor:
        return generate_approval_mail_rfc_editor(request, doc)
    
    status = full_intended_status(doc.intended_status).replace("a ", "").replace("an ", "")
    if "an " in full_intended_status(doc.intended_status):
        action_type = "Document"
    else:
        action_type = "Protocol"
    
    cc = settings.DOC_APPROVAL_EMAIL_CC

    if doc.group.ietfwg.group_type.type != "AG" and not doc.group.name.endswith("Working Group"):
        doc.group.name_with_wg = doc.group.name + " Working Group"
        cc.append("%s mailing list <%s>" % (doc.group.acronym, doc.group.ietfwg.email_address))
        cc.append("%s chair <%s-chairs@tools.ietf.org>" % (doc.group.acronym, doc.group.acronym))
    else:
        doc.group.name_with_wg = doc.group.name

    docs = [d.document() for d in doc.idinternal.ballot_set()]
    for d in docs:
        d.full_status = full_intended_status(d.intended_status)
        d.filled_title = textwrap.fill(d.title, width=70, subsequent_indent=" " * 3)

    if doc.group.acronym_id == Acronym.INDIVIDUAL_SUBMITTER:
        if len(docs) > 1:
            made_by = "These documents have been reviewed in the IETF but are not the products of an IETF Working Group."
        else:
            made_by = "This document has been reviewed in the IETF but is not the product of an IETF Working Group.";
    else:
        if len(docs) > 1:
            made_by = "These documents are products of the %s." % doc.group.name_with_wg
        else:
            made_by = "This document is the product of the %s." % doc.group.name_with_wg
    
    director = doc.idinternal.job_owner
    other_director = IESGLogin.objects.filter(person__in=[ad.person for ad in doc.group.ietfwg.area_directors()]).exclude(id=doc.idinternal.job_owner_id)
    if doc.group.acronym_id != Acronym.INDIVIDUAL_SUBMITTER and other_director:
        contacts = "The IESG contact persons are %s and %s." % (director, other_director[0])
    else:
        contacts = "The IESG contact person is %s." % director

    doc_type = "RFC" if type(doc) == Rfc else "Internet Draft"
        
    return render_to_string("idrfc/approval_mail.txt",
                            dict(doc=doc,
                                 doc_url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url(),
                                 cc=",\n    ".join(cc),
                                 docs=docs,
                                 doc_type=doc_type,
                                 made_by=made_by,
                                 contacts=contacts,
                                 status=status,
                                 action_type=action_type,
                                 )
                            )

def generate_approval_mail_rfc_editor(request, doc):
    full_status = full_intended_status(doc.intended_status)
    status = full_status.replace("a ", "").replace("an ", "")
    disapproved = doc.idinternal.cur_state_id in IDState.DO_NOT_PUBLISH_STATES
    doc_type = "RFC" if type(doc) == Rfc else "Internet Draft"
    
    stream = get_stream_from_draft(doc)
    to = ", ".join([u"%s <%s>" % x.email() for x in stream.get_chairs_for_document(doc) ])
    if stream.name == "IRTF":
    	# also send to the IRSG
        to += ", Internet Research Steering Group (IRSG) <irsg@irtf.org>"

    return render_to_string("idrfc/approval_mail_rfc_editor.txt",
                            dict(doc=doc,
                                 doc_url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url(),
                                 doc_type=doc_type,
                                 status=status,
                                 full_status=full_status,
                                 disapproved=disapproved,
                                 to=to,
                                 )
                            )

def send_last_call_request(request, doc, ballot):
    to = "iesg-secretary@ietf.org"
    frm = '"DraftTracker Mail System" <iesg-secretary@ietf.org>'
    docs = [d.document() for d in doc.idinternal.ballot_set()]
    
    send_mail(request, to, frm,
              "Last Call: %s" % doc.file_tag(),
              "idrfc/last_call_request.txt",
              dict(docs=docs,
                   doc_url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()))

def email_resurrect_requested(request, doc, by):
    to = "I-D Administrator <internet-drafts@ietf.org>"
    frm = u"%s <%s>" % by.person.email()
    send_mail(request, to, frm,
              "I-D Resurrection Request",
              "idrfc/resurrect_request_email.txt",
              dict(doc=doc,
                   by=frm,
                   url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()))

def email_resurrection_completed(request, doc):
    to = u"%s <%s>" % doc.idinternal.resurrect_requested_by.person.email()
    frm = "I-D Administrator <internet-drafts-reply@ietf.org>"
    send_mail(request, to, frm,
              "I-D Resurrection Completed - %s" % doc.file_tag(),
              "idrfc/resurrect_completed_email.txt",
              dict(doc=doc,
                   by=frm,
                   url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()))

def email_ballot_deferred(request, doc, by, telechat_date):
    to = "iesg@ietf.org"
    frm = "DraftTracker Mail System <iesg-secretary@ietf.org>"
    send_mail(request, to, frm,
              "IESG Deferred Ballot notification: %s" % doc.file_tag(),
              "idrfc/ballot_deferred_email.txt",
              dict(doc=doc,
                   by=by,
                   telechat_date=telechat_date))

def generate_issue_ballot_mail(request, doc):
    full_status = full_intended_status(doc.intended_status)
    status = full_status.replace("a ", "").replace("an ", "")

    ads = IESGLogin.objects.filter(user_level__in=(IESGLogin.AD_LEVEL, IESGLogin.INACTIVE_AD_LEVEL)).order_by('user_level', 'last_name')
    positions = dict((p.ad_id, p) for p in doc.idinternal.ballot.positions.all())
    
    # format positions
    ad_positions = []
    for ad in ads:
        p = positions.get(ad.id)
        if not p:
            continue

        def formatted(val):
            if val > 0:
                return "[ X ]"
            elif val < 0:
                return "[ . ]"
            else:
                return "[   ]"

        fmt = u"%-21s%-10s%-11s%-9s%-10s" % (
            unicode(ad)[:21],
            formatted(p.yes),
            formatted(p.noobj),
            formatted(p.discuss),
            "[ R ]" if p.recuse else formatted(p.abstain),
            )
        ad_positions.append((ad, fmt))
        
    active_ad_positions = filter(lambda t: t[0].user_level == IESGLogin.AD_LEVEL, ad_positions)
    inactive_ad_positions = filter(lambda t: t[0].user_level == IESGLogin.INACTIVE_AD_LEVEL, ad_positions)

    # arrange discusses and comments
    ad_feedback = []
    discusses = dict((p.ad_id, p) for p in doc.idinternal.ballot.discusses.all()
                     if p.ad_id in positions and positions[p.ad_id].discuss == 1)
    comments = dict((p.ad_id, p) for p in doc.idinternal.ballot.comments.all())
    for ad in ads:
        d = discusses.get(ad.id)
        c = comments.get(ad.id)
        if ad.user_level != IESGLogin.AD_LEVEL or not (c or d):
            continue

        ad_feedback.append((ad, d, c))
    
    return render_to_string("idrfc/issue_ballot_mail.txt",
                            dict(doc=doc,
                                 doc_url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url(),
                                 status=status,
                                 active_ad_positions=active_ad_positions,
                                 inactive_ad_positions=inactive_ad_positions,
                                 ad_feedback=ad_feedback
                                 )
                            )
    
def email_iana(request, doc, to, msg):
    # fix up message and send message to IANA for each in ballot set
    import email
    parsed_msg = email.message_from_string(msg.encode("utf-8"))

    for i in doc.idinternal.ballot_set():
        extra = {}
        extra["Reply-To"] = "noreply@ietf.org"
        extra["X-IETF-Draft-string"] = i.document().filename
        extra["X-IETF-Draft-revision"] = i.document().revision_display()
    
        send_mail_text(request, "To: IANA <%s>" % to,
                       parsed_msg["From"], parsed_msg["Subject"],
                       parsed_msg.get_payload(),
                       extra=extra,
                       bcc="fenner@research.att.com")

def email_last_call_expired(doc):
    text = "IETF Last Call has ended, and the state has been changed to\n%s." % doc.idinternal.cur_state.state
    
    send_mail(None,
              "iesg@ietf.org",
              "DraftTracker Mail System <iesg-secretary@ietf.org>",
              "Last Call Expired: %s" % doc.file_tag(),
              "idrfc/change_notice.txt",
              dict(text=text,
                   doc=doc,
                   url=settings.IDTRACKER_BASE_URL + doc.idinternal.get_absolute_url()),
              cc="iesg-secretary@ietf.org")

