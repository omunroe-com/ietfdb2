from django.conf import settings

from ietf.idtracker.models import InternetDraft, DocumentComment, BallotInfo, IESGLogin
from ietf.idrfc.mails import *
from ietf.ietfauth.decorators import has_role

def add_document_comment(request, doc, text, ballot=None):
    if request:
        login = IESGLogin.objects.get(login_name=request.user.username)
    else:
        login = None

    c = DocumentComment()
    c.document = doc.idinternal
    c.public_flag = True
    c.version = doc.revision_display()
    c.comment_text = text
    c.created_by = login
    if ballot:
        c.ballot = ballot
    c.rfc_flag = doc.idinternal.rfc_flag
    c.save()

def generate_ballot(request, doc):
    ballot = BallotInfo()
    ballot.ballot = doc.idinternal.ballot_id
    ballot.active = False
    ballot.last_call_text = generate_last_call_announcement(request, doc)
    ballot.approval_text = generate_approval_mail(request, doc)
    ballot.ballot_writeup = render_to_string("idrfc/ballot_writeup.txt")
    ballot.save()
    doc.idinternal.ballot = ballot
    return ballot
    
def log_state_changed(request, doc, by, email_watch_list=True, note=''):
    change = u"State changed to <b>%s</b> from %s." % (
        doc.idinternal.docstate(),
        format_document_state(doc.idinternal.prev_state,
                              doc.idinternal.prev_sub_state))
    if note:
        change += "<br>%s" % note

    c = DocumentComment()
    c.document = doc.idinternal
    c.public_flag = True
    c.version = doc.revision_display()
    c.comment_text = change

    if doc.idinternal.docstate()=="In Last Call":
        c.comment_text += "\n\n<b>The following Last Call Announcement was sent out:</b>\n\n"
        c.comment_text += doc.idinternal.ballot.last_call_text


    if isinstance(by, IESGLogin):
        c.created_by = by
    c.result_state = doc.idinternal.cur_state
    c.origin_state = doc.idinternal.prev_state
    c.rfc_flag = doc.idinternal.rfc_flag
    c.save()

    if email_watch_list:
        email_state_changed(request, doc, strip_tags(change))

    return change

def log_state_changedREDESIGN(request, doc, by, prev_iesg_state, prev_iesg_tag):
    from ietf.doc.models import DocEvent

    state = doc.get_state("draft-iesg")

    state_name = state.name
    tags = doc.tags.filter(slug__in=('point', 'ad-f-up', 'need-rev', 'extpty'))
    if tags:
        state_name += "::" + tags[0].name

    prev_state_name = prev_iesg_state.name if prev_iesg_state else "I-D Exists"
    if prev_iesg_tag:
        prev_state_name += "::" + prev_iesg_tag.name

    e = DocEvent(doc=doc, by=by)
    e.type = "changed_document"
    e.desc = u"State changed to <b>%s</b> from %s" % (state_name, prev_state_name)
    e.save()
    return e


if settings.USE_DB_REDESIGN_PROXY_CLASSES:
    log_state_changed = log_state_changedREDESIGN

       
def update_telechat(request, idinternal, new_telechat_date, new_returning_item=None):
    on_agenda = bool(new_telechat_date)

    if new_returning_item == None:
        new_returning_item = idinternal.returning_item
    
    returning_item_changed = False
    if idinternal.returning_item != bool(new_returning_item):
        idinternal.returning_item = bool(new_returning_item)
        returning_item_changed = True

    # auto-update returning item
    if (not returning_item_changed and
        on_agenda and idinternal.agenda
        and new_telechat_date != idinternal.telechat_date):
        idinternal.returning_item = True

    # update agenda
    doc = idinternal.document()
    if bool(idinternal.agenda) != on_agenda:
        if on_agenda:
            add_document_comment(request, doc,
                                 "Placed on agenda for telechat - %s" % new_telechat_date)
            idinternal.telechat_date = new_telechat_date
        else:
            add_document_comment(request, doc,
                                 "Removed from agenda for telechat")
        idinternal.agenda = on_agenda
    elif on_agenda and new_telechat_date != idinternal.telechat_date:
        add_document_comment(request, doc,
                             "Telechat date has been changed to <b>%s</b> from <b>%s</b>" %
                             (new_telechat_date,
                              idinternal.telechat_date))
        idinternal.telechat_date = new_telechat_date

def update_telechatREDESIGN(request, doc, by, new_telechat_date, new_returning_item=None):
    from ietf.doc.models import TelechatDocEvent
    
    on_agenda = bool(new_telechat_date)

    prev = doc.latest_event(TelechatDocEvent, type="scheduled_for_telechat")
    prev_returning = bool(prev and prev.returning_item)
    prev_telechat = prev.telechat_date if prev else None
    prev_agenda = bool(prev_telechat)
    
    returning_item_changed = bool(new_returning_item != None and new_returning_item != prev_returning)

    if new_returning_item == None:
        returning = prev_returning
    else:
        returning = new_returning_item

    if returning == prev_returning and new_telechat_date == prev_telechat:
        # fully updated, nothing to do
        return

    # auto-update returning item
    if (not returning_item_changed and on_agenda and prev_agenda
        and new_telechat_date != prev_telechat):
        returning = True

    e = TelechatDocEvent()
    e.type = "scheduled_for_telechat"
    e.by = by
    e.doc = doc
    e.returning_item = returning
    e.telechat_date = new_telechat_date
    
    if on_agenda != prev_agenda:
        if on_agenda:
            e.desc = "Placed on agenda for telechat - %s" % (new_telechat_date)
        else:
            e.desc = "Removed from agenda for telechat"
    elif on_agenda and new_telechat_date != prev_telechat:
        e.desc = "Telechat date has been changed to <b>%s</b> from <b>%s</b>" % (
            new_telechat_date, prev_telechat)
    else:
        # we didn't reschedule but flipped returning item bit - let's
        # just explain that
        if returning:
            e.desc = "Set telechat returning item indication"
        else:
            e.desc = "Removed telechat returning item indication"

    e.save()

if settings.USE_DB_REDESIGN_PROXY_CLASSES:
    update_telechat = update_telechatREDESIGN

def can_edit_base(doc, user):
    return user.is_authenticated() and (
        has_role(user, ["Secretariat", "Area Director"]) or
        doc.group.role_set.filter(name__in=("chair", "auth", "delegate"), person__user=user)
        )

can_edit_intended_std_level = can_edit_base
can_edit_consensus = can_edit_base
can_edit_shepherd = can_edit_base

def can_edit_shepherd_writeup(doc, user):
     if user.is_authenticated():
         if Person.objects.filter(user=user).count():
             return can_edit_base(doc,user) or (doc.shepherd==user.person)
     return False

def nice_consensus(consensus):
    mapping = {
        None: "Unknown",
        True: "Yes",
        False: "No"
        }
    return mapping[consensus]
    
