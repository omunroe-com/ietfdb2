import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse as urlreverse

from ietf.utils.mail import send_mail_text
from ietf.liaisons.utils import role_persons_with_fixed_email
from ietf.group.models import Role

def send_liaison_by_email(request, liaison):
    subject = u'New Liaison Statement, "%s"' % (liaison.title)
    from_email = settings.LIAISON_UNIVERSAL_FROM
    to_email = liaison.to_contact.split(',')
    cc = liaison.cc.split(',')
    if liaison.technical_contact:
        cc += liaison.technical_contact.split(',')
    if liaison.response_contact:
        cc += liaison.response_contact.split(',')
    bcc = ['statements@ietf.org']
    body = render_to_string('liaisons/liaison_mail.txt', dict(
            liaison=liaison,
            url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_detail", kwargs=dict(object_id=liaison.pk)),
            referenced_url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_detail", kwargs=dict(object_id=liaison.related_to.pk)) if liaison.related_to else None,
            ))

    send_mail_text(request, to_email, from_email, subject, body, cc=", ".join(cc), bcc=", ".join(bcc))

def notify_pending_by_email(request, liaison):

    # Broken: this does not find the list of approvers for the sending body
    # For now, we are sending to statements@ietf.org so the Secretariat can nudge
    # Bug 880: https://trac.tools.ietf.org/tools/ietfdb/ticket/880
    #
    # from ietf.liaisons.utils import IETFHM
    #
    # from_entity = IETFHM.get_entity_by_key(liaison.from_raw_code)
    # if not from_entity:
    #    return None
    # to_email = []
    # for person in from_entity.can_approve():
    #     to_email.append('%s <%s>' % person.email())
    subject = u'New Liaison Statement, "%s" needs your approval' % (liaison.title)
    from_email = settings.LIAISON_UNIVERSAL_FROM
    body = render_to_string('liaisons/pending_liaison_mail.txt', dict(
            liaison=liaison,
            url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_approval_detail", kwargs=dict(object_id=liaison.pk)),
            referenced_url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_detail", kwargs=dict(object_id=liaison.related_to.pk)) if liaison.related_to else None,
            ))
    # send_mail_text(request, to_email, from_email, subject, body)
    send_mail_text(request, ['statements@ietf.org'], from_email, subject, body)

def send_sdo_reminder(sdo):
    roles = Role.objects.filter(name="liaiman", group=sdo)
    if not roles: # no manager to contact
        return None

    manager_role = roles[0]
    
    subject = 'Request for update of list of authorized individuals'
    to_email = manager_role.email.address
    name = manager_role.person.plain_name()

    authorized_list = role_persons_with_fixed_email(sdo, "auth")
    body = render_to_string('liaisons/sdo_reminder.txt', dict(
            manager_name=name,
            sdo_name=sdo.name,
            individuals=authorized_list,
            ))
    
    send_mail_text(None, to_email, settings.LIAISON_UNIVERSAL_FROM, subject, body)

    return body

def possibly_send_deadline_reminder(liaison):
    PREVIOUS_DAYS = {
        14: 'in two weeks',
        7: 'in one week',
        4: 'in four days',
        3: 'in three days',
        2: 'in two days',
        1: 'tomorrow',
        0: 'today'
        }
    
    days_to_go = (liaison.deadline - datetime.date.today()).days
    if not (days_to_go < 0 or days_to_go in PREVIOUS_DAYS.keys()):
        return None # no reminder
            
    if days_to_go < 0:
        subject = '[Liaison OUT OF DATE] %s' % liaison.title
        days_msg = 'is out of date for %s days' % (-days_to_go)
    else:
        subject = '[Liaison deadline %s] %s' % (PREVIOUS_DAYS[days_to_go], liaison.title)
        days_msg = 'expires %s' % PREVIOUS_DAYS[days_to_go]

    from_email = settings.LIAISON_UNIVERSAL_FROM
    to_email = liaison.to_contact.split(',')
    cc = liaison.cc.split(',')
    if liaison.technical_contact:
        cc += liaison.technical_contact.split(',')
    if liaison.response_contact:
        cc += liaison.response_contact.split(',')
    bcc = 'statements@ietf.org'
    body = render_to_string('liaisons/liaison_deadline_mail.txt',
                            dict(liaison=liaison,
                                 days_msg=days_msg,
                                 url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_approval_detail", kwargs=dict(object_id=liaison.pk)),
                                 referenced_url=settings.IDTRACKER_BASE_URL + urlreverse("liaison_detail", kwargs=dict(object_id=liaison.related_to.pk)) if liaison.related_to else None,
                                 ))
    
    send_mail_text(None, to_email, from_email, subject, body, cc=cc, bcc=bcc)

    return body
