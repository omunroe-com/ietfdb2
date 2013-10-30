import sys
from django.test              import Client
from ietf.meeting.tests.ttest import AgendaTransactionalTestCase
from ietf.utils import TestCase
from ietf.name.models     import SessionStatusName
from ietf.person.models   import Person
from ietf.group.models    import Group
from ietf.meeting.models  import TimeSlot, Session, Meeting, ScheduledSession
from ietf.meeting.helpers import get_meeting, get_schedule

import debug

class AgendaInfoTestCase(TestCase):
    # See ietf.utils.test_utils.TestCase for the use of perma_fixtures vs. fixtures
    perma_fixtures = [ 'names.xml',  # ietf/names/fixtures/names.xml for MeetingTypeName, and TimeSlotTypeName
                 'meeting83.json',
                 'constraint83.json',
                 'workinggroups.json',
                 'groupgroup.json',
                 'person.json', 'users.json' ]

    def test_SessionUnicode(self):
        m1 = get_meeting("83")
        g1 = Group.objects.get(acronym = "pkix")
        p1 = Person.objects.get(pk = 5376)       # Russ Housley
        st1 = SessionStatusName.objects.get(slug = "appr")
        s1 = m1.session_set.create(name = "newone", group = g1, requested_by = p1, status = st1)
        self.assertEqual(s1.__unicode__(), "IETF-83: pkix (unscheduled)[22090]")

    def test_AgendaInfo(self):
        from ietf.meeting.views import agenda_info
        num = '83'
        timeslots, update, meeting, venue, ads, plenaryw_agenda, plenaryt_agenda = agenda_info(num)
        # I think that "timeslots" here, is unique times, not actually
        # the timeslots array itself.
        self.assertEqual(len(timeslots),26)
        self.assertEqual(meeting.number,'83')
        self.assertEqual(venue.meeting_num, "83")
        # will change as more ADs are added to fixtures
        self.assertEqual(len(ads), 8)

    def test_AgendaInfoReturnsSortedTimeSlots(self):
        from ietf.meeting.views import agenda_info
        num = '83'
        timeslots, update, meeting, venue, ads, plenaryw_agenda, plenaryt_agenda = agenda_info(num)
        for slotnum in range(0,len(timeslots)-1):
            # debug
            #sys.stdout.write("%d: %s vs %d: %s\n" % (timeslots[slotnum].pk,
            #                                         timeslots[slotnum].time,
            #                                         timeslots[slotnum+1].pk,
            #                                         timeslots[slotnum+1].time))
            self.assertTrue(timeslots[slotnum].time < timeslots[slotnum+1].time)

    # this tests that a slot at 11:20 AM on Friday, has slot 10 minutes later
    # after it
    def test_TimeSlot2408_has_SlotToTheRight(self):
        ss2408 = ScheduledSession.objects.get(pk = 2408)
        self.assertTrue(ss2408.slot_to_the_right)

    # this tests that a slot 9-11:30am on Wednesday, has no following slot,
    # as the slot purpose to the right is non-session.
    def test_TimeSlot2517_hasno_SlotToTheRight(self):
        ss2517 = ScheduledSession.objects.get(pk = 2517)
        self.assertFalse(ss2517.slot_to_the_right)

    # this tests that a slot 13:00-15:00 on Tuesday has no following slot,
    # as the gap to the next slot (at 15:20) is too long (there is a break)
    def test_TimeSlot2418_hasno_SlotToTheRight(self):
        ss2418 = ScheduledSession.objects.get(pk = 2418)
        self.assertFalse(ss2418.slot_to_the_right)

    def test_AgendaInfoNotFound(self):
        from django.http import Http404
        from ietf.meeting.views import agenda_info
        num = '83b'
        try:
            timeslots, update, meeting, venue, ads, plenaryw_agenda, plenaryt_agenda = agenda_info(num)
            # fail!!!
            self.assertFalse(True)
        except Http404:
            pass

    def test_DoNotGetSchedule(self):
        from django.http import Http404
        num = '83'
        from ietf.meeting.views import get_meeting, get_schedule
        meeting = get_meeting(num)
        try:
            na = get_schedule(meeting, "none:83")
        except Http404:
            False

    def test_GetSchedule(self):
        num = '83'
        from ietf.meeting.views import get_meeting, get_schedule
        meeting = get_meeting(num)
        na = get_schedule(meeting, "mtg:83")
        self.assertIsNotNone(na)

    def test_sessionstr(self):
        num = '83'
        from ietf.meeting.views import get_meeting
        meeting = get_meeting(num)
        session1= Session.objects.get(pk=2157)
        self.assertEqual(session1.__unicode__(), u"IETF-83: pkix 0900[2157]")

    def test_sessionstr_interim(self):
        """
        Need a fixture for a meeting that is interim
        """
        pass

    def test_serialize_constraint(self):
        session1  = Session.objects.get(pk=2157)
        host_scheme  = "http://datatracker.ietf.org"
        json_dict = session1.constraints_dict(host_scheme)
        self.assertEqual(len(json_dict), 25)

    def test_avtcore_has_two_slots(self):
        mtg83 = get_meeting(83)
        sch83 = get_schedule(mtg83, "mtg:83")
        avtcore = mtg83.session_set.get(group__acronym='avtcore')
        self.assertEqual(avtcore.pk, 2216)  # sanity check
        self.assertEqual(len(avtcore.scheduledsession_set.filter(schedule = sch83)), 2)

    def test_clue_has_ad_present(self):
        mtg83 = get_meeting(83)
        clue83 = mtg83.session_set.filter(group__acronym='clue')[0]
        is_present = clue83.people_constraints
        self.assertIsNotNone(is_present, "why is constraint list none")
        self.assertEqual(len(is_present), 3)


