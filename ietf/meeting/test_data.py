import datetime

from ietf.doc.models import Document, State
from ietf.group.models import Group
from ietf.meeting.models import Meeting, Room, TimeSlot, Session, Schedule, ScheduledSession, ResourceAssociation, SessionPresentation
from ietf.name.models import RoomResourceName
from ietf.person.models import Person
from ietf.utils.test_data import make_test_data


def make_meeting_test_data():
    if not Group.objects.filter(acronym='mars'):
        make_test_data()
    system_person = Person.objects.get(name="(System)")
    plainman = Person.objects.get(user__username="plain")
    #secretary = Person.objects.get(user__username="secretary") ## not used

    meeting = Meeting.objects.get(number="42", type="ietf")
    schedule = Schedule.objects.create(meeting=meeting, owner=plainman, name="test-agenda", visible=True, public=True)
    pname = RoomResourceName.objects.create(name='projector',slug='proj')
    projector = ResourceAssociation.objects.create(name=pname,icon="notfound.png",desc="Basic projector")
    room = Room.objects.create(meeting=meeting, name="Test Room", capacity=123)
    breakfast_room = Room.objects.create(meeting=meeting, name="Breakfast Room", capacity=40)
    room.session_types.add("session")
    breakfast_room.session_types.add("lead")
    room.resources = [projector]

    # mars WG
    mars = Group.objects.get(acronym='mars')
    slot = TimeSlot.objects.create(meeting=meeting, type_id="session", duration=30 * 60, location=room,
                                   time=datetime.datetime.combine(datetime.date.today(), datetime.time(9, 30)))
    mars_session = Session.objects.create(meeting=meeting, group=mars,
                                          attendees=10, requested_by=system_person,
                                          requested_duration=20, status_id="schedw",
                                          scheduled=datetime.datetime.now(),type_id="session")
    mars_session.resources = [projector]
    ScheduledSession.objects.create(timeslot=slot, session=mars_session, schedule=schedule)

    # ames WG
    slot = TimeSlot.objects.create(meeting=meeting, type_id="session", duration=30 * 60, location=room,
                                   time=datetime.datetime.combine(datetime.date.today(), datetime.time(10, 30)))
    ames_session = Session.objects.create(meeting=meeting, group=Group.objects.get(acronym="ames"),
                                          attendees=10, requested_by=system_person,
                                          requested_duration=20, status_id="schedw",
                                          scheduled=datetime.datetime.now(),type_id="session")
    ScheduledSession.objects.create(timeslot=slot, session=ames_session, schedule=schedule)

    # IESG breakfast
    breakfast_slot = TimeSlot.objects.create(meeting=meeting, type_id="lead", duration=90 * 60,
                                   location=breakfast_room, 
                                   time=datetime.datetime.combine(datetime.date.today(),datetime.time(7,0)))
    iesg_session = Session.objects.create(meeting=meeting, group=Group.objects.get(acronym="iesg"),
                                          name="IESG Breakfast",
                                          attendees=25, requested_by=system_person,
                                          requested_duration=20, status_id="schedw",
                                          scheduled=datetime.datetime.now(),type_id="lead")
    ScheduledSession.objects.create(timeslot=breakfast_slot, session=iesg_session, schedule=schedule)

    meeting.agenda = schedule
    meeting.save()

    doc = Document.objects.create(name='agenda-mars-ietf-42', type_id='agenda', title="Agenda", external_url="agenda-mars.txt",group=mars,rev='00')
    doc.set_state(State.objects.get(type=doc.type_id, slug="active"))
    mars_session.sessionpresentation_set.add(SessionPresentation(session=mars_session,document=doc,rev=doc.rev))

    doc = Document.objects.create(name='minutes-mars-ietf-42', type_id='minutes', title="Minutes", external_url="minutes-mars.txt",group=mars,rev='00')
    doc.set_state(State.objects.get(type=doc.type_id, slug="active"))
    mars_session.sessionpresentation_set.add(SessionPresentation(session=mars_session,document=doc,rev=doc.rev))

    doc = Document.objects.create(name='slides-mars-ietf-42', type_id='slides', title="Slideshow", external_url="slides-mars.txt",group=mars,rev='00')
    doc.set_state(State.objects.get(type=doc.type_id, slug="active"))
    doc.set_state(State.objects.get(type='reuse_policy',slug='single'))
    mars_session.sessionpresentation_set.add(SessionPresentation(session=mars_session,document=doc,rev=doc.rev))

    doc = Document.objects.create(name='slides-mars-ietf-42-deleted', type_id='slides', title="Bad Slideshow", external_url="slides-mars-deleted.txt",group=mars,rev='00')
    doc.set_state(State.objects.get(type=doc.type_id, slug="deleted"))
    doc.set_state(State.objects.get(type='reuse_policy',slug='single'))
    mars_session.sessionpresentation_set.add(SessionPresentation(session=mars_session,document=doc,rev=doc.rev))
    
    return meeting



