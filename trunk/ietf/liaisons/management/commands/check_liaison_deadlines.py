import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from ietf.liaisons.models import LiaisonDetail
from ietf.liaisons.mail import IETFEmailMessage


PREVIOUS_DAYS = {
    14: 'in two weeks',
    7: 'in one week',
    4: 'in four days',
    3: 'in three days',
    2: 'in two days',
    1: 'tomorrow',
    0: 'today'}


class Command(BaseCommand):
    help = (u"Check liaison deadlines and send a reminder if we are close to its deadline")

    def send_reminder(self, liaison, days_to_go):
        if days_to_go < 0:
            subject = '[Liaison OUT OF DATE] %s' % liaison.title
            days_msg = 'is out of date for %s days' % (-days_to_go)
        else:
            subject = '[Liaison deadline %s] %s' % (PREVIOUS_DAYS[days_to_go], liaison.title)
            days_msg = 'expires %s' % PREVIOUS_DAYS[days_to_go]

        from_email = settings.LIAISON_UNIVERSAL_FROM
        to_email = liaison.to_poc.split(',')
        cc = liaison.cc1.split(',')
        if liaison.technical_contact:
            cc += liaison.technical_contact.split(',')
        if liaison.response_contact:
            cc += liaison.response_contact.split(',')
        bcc = ['statements@ietf.org']
        body = render_to_string('liaisons/liaison_deadline_mail.txt',
                                {'liaison': liaison,
                                 'days_msg': days_msg,
                                })
        mail = IETFEmailMessage(subject=subject,
                                to=to_email,
                                from_email=from_email,
                                cc=cc,
                                bcc=bcc,
                                body=body)
        if not settings.DEBUG:
            mail.send()
            print 'Liaison %05s#: Deadline reminder Sent!' % liaison.pk
        else:
            print 'Liaison %05s#: Deadline reminder Not Sent because in DEBUG mode!' % liaison.pk

    def handle(self, *args, **options):
        today = datetime.date.today()
        query = LiaisonDetail.objects.filter(deadline_date__isnull=False, action_taken=False, deadline_date__gte=today - datetime.timedelta(14))
        for liaison in query:
            delta = liaison.deadline_date - today
            if delta.days < 0 or delta.days in PREVIOUS_DAYS.keys():
                self.send_reminder(liaison, delta.days)
