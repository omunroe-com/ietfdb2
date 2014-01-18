import StringIO
import os, shutil, datetime

from django.core.urlresolvers import reverse as urlreverse
from django.conf import settings

from pyquery import PyQuery
import debug

from ietf.doc.models import *
from ietf.doc.utils import *
from ietf.name.models import *
from ietf.group.models import *
from ietf.person.models import *
from ietf.meeting.models import Meeting, MeetingTypeName
from ietf.iesg.models import TelechatDate
from ietf.utils.test_utils import login_testing_unauthorized
from ietf.utils.test_data import make_test_data
from ietf.utils.mail import outbox
from ietf.utils import TestCase


class ChangeStateTests(TestCase):
    def test_change_state(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="ad-eval"))

        url = urlreverse('doc_change_state', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        first_state = draft.get_state("draft-iesg")
        next_states = first_state.next_states

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=state]')), 1)
        
        if next_states:
            self.assertTrue(len(q('.next-states form input[type=hidden]')) > 0)

            
        # faulty post
        r = self.client.post(url, dict(state=State.objects.get(used=True, type="draft", slug="active").pk))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)
        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state("draft-iesg"), first_state)

        
        # change state
        events_before = draft.docevent_set.count()
        mailbox_before = len(outbox)
        draft.tags.add("ad-f-up")
        
        r = self.client.post(url,
                             dict(state=State.objects.get(used=True, type="draft-iesg", slug="review-e").pk,
                                  substate="point",
                                  comment="Test comment"))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug("draft-iesg"), "review-e")
        self.assertTrue(not draft.tags.filter(slug="ad-f-up"))
        self.assertTrue(draft.tags.filter(slug="point"))
        self.assertEqual(draft.docevent_set.count(), events_before + 2)
        self.assertTrue("Test comment" in draft.docevent_set.all()[0].desc)
        self.assertTrue("State changed" in draft.docevent_set.all()[1].desc)
        self.assertEqual(len(outbox), mailbox_before + 2)
        self.assertTrue("State Update Notice" in outbox[-2]['Subject'])
        self.assertTrue(draft.name in outbox[-1]['Subject'])

        
        # check that we got a previous state now
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('.prev-state form input[name="state"]')), 1)

    def test_pull_from_rfc_queue(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="rfcqueue"))

        url = urlreverse('doc_change_state', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        # change state
        mailbox_before = len(outbox)

        r = self.client.post(url,
                             dict(state=State.objects.get(used=True, type="draft-iesg", slug="review-e").pk,
                                  substate="",
                                  comment="Test comment"))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug("draft-iesg"), "review-e")
        self.assertEqual(len(outbox), mailbox_before + 2 + 1)
        self.assertTrue(draft.name in outbox[-1]['Subject'])
        self.assertTrue("changed state" in outbox[-1]['Subject'])
        self.assertTrue("is no longer" in str(outbox[-1]))
        self.assertTrue("Test comment" in str(outbox[-1]))

    def test_change_iana_state(self):
        draft = make_test_data()

        first_state = State.objects.get(used=True, type="draft-iana-review", slug="need-rev")
        next_state = State.objects.get(used=True, type="draft-iana-review", slug="ok-noact")
        draft.set_state(first_state)

        url = urlreverse('doc_change_iana_state', kwargs=dict(name=draft.name, state_type="iana-review"))
        login_testing_unauthorized(self, "iana", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=state]')), 1)
        
        # faulty post
        r = self.client.post(url, dict(state="foobarbaz"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)
        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state("draft-iana-review"), first_state)

        # change state
        r = self.client.post(url, dict(state=next_state.pk))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state("draft-iana-review"), next_state)

    def test_request_last_call(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="ad-eval"))

        self.client.login(remote_user="secretary")
        url = urlreverse('doc_change_state', kwargs=dict(name=draft.name))

        mailbox_before = len(outbox)
        
        self.assertTrue(not draft.latest_event(type="changed_ballot_writeup_text"))
        r = self.client.post(url, dict(state=State.objects.get(used=True, type="draft-iesg", slug="lc-req").pk))
        self.assertContains(r, "Your request to issue the Last Call")

        # last call text
        e = draft.latest_event(WriteupDocEvent, type="changed_last_call_text")
        self.assertTrue(e)
        self.assertTrue("The IESG has received" in e.text)
        self.assertTrue(draft.title in e.text)
        self.assertTrue(draft.get_absolute_url() in e.text)

        # approval text
        e = draft.latest_event(WriteupDocEvent, type="changed_ballot_approval_text")
        self.assertTrue(e)
        self.assertTrue("The IESG has approved" in e.text)
        self.assertTrue(draft.title in e.text)
        self.assertTrue(draft.get_absolute_url() in e.text)

        # ballot writeup
        e = draft.latest_event(WriteupDocEvent, type="changed_ballot_writeup_text")
        self.assertTrue(e)
        self.assertTrue("Technical Summary" in e.text)

        # mail notice
        self.assertTrue(len(outbox) > mailbox_before)
        self.assertTrue("Last Call:" in outbox[-1]['Subject'])

        # comment
        self.assertTrue("Last call was requested" in draft.latest_event().desc)
        

class EditInfoTests(TestCase):
    def test_edit_info(self):
        draft = make_test_data()
        url = urlreverse('doc_edit_info', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=intended_std_level]')), 1)

        prev_ad = draft.ad
        # faulty post
        r = self.client.post(url, dict(ad="123456789"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)
        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.ad, prev_ad)

        # edit info
        events_before = draft.docevent_set.count()
        mailbox_before = len(outbox)

        new_ad = Person.objects.get(name="Ad No1")

        r = self.client.post(url,
                             dict(intended_std_level=str(draft.intended_std_level.pk),
                                  stream=draft.stream_id,
                                  ad=str(new_ad.pk),
                                  notify="test@example.com",
                                  note="New note",
                                  telechat_date="",
                                  ))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.ad, new_ad)
        self.assertEqual(draft.note, "New note")
        self.assertTrue(not draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat"))
        self.assertEqual(draft.docevent_set.count(), events_before + 3)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue(draft.name in outbox[-1]['Subject'])

    def test_edit_telechat_date(self):
        draft = make_test_data()
        
        url = urlreverse('doc_edit_info', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        data = dict(intended_std_level=str(draft.intended_std_level_id),
                    stream=draft.stream_id,
                    ad=str(draft.ad_id),
                    notify="test@example.com",
                    note="",
                    )

        # add to telechat
        self.assertTrue(not draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat"))
        data["telechat_date"] = TelechatDate.objects.active()[0].date.isoformat()
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertTrue(draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat"))
        self.assertEqual(draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat").telechat_date, TelechatDate.objects.active()[0].date)

        # change telechat
        data["telechat_date"] = TelechatDate.objects.active()[1].date.isoformat()
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat").telechat_date, TelechatDate.objects.active()[1].date)

        # remove from agenda
        data["telechat_date"] = ""
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertTrue(not draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat").telechat_date)

    def test_start_iesg_process_on_draft(self):
        make_test_data()

        draft = Document.objects.create(
            name="draft-ietf-mars-test2",
            time=datetime.datetime.now(),
            type_id="draft",
            title="Testing adding a draft",
            stream=None,
            group=Group.objects.get(acronym="mars"),
            abstract="Test test test.",
            rev="01",
            pages=2,
            intended_std_level_id="ps",
            shepherd=None,
            ad=None,
            expires=datetime.datetime.now() + datetime.timedelta(days=settings.INTERNET_DRAFT_DAYS_TO_EXPIRE),
            )
        doc_alias = DocAlias.objects.create(
            document=draft,
            name=draft.name,
            )

        DocumentAuthor.objects.create(
            document=draft,
            author=Email.objects.get(address="aread@ietf.org"),
            order=1
            )
        
        url = urlreverse('doc_edit_info', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=intended_std_level]')), 1)
        self.assertTrue('@' in q('form input[name=notify]')[0].get('value'))

        # add
        events_before = draft.docevent_set.count()
        mailbox_before = len(outbox)

        ad = Person.objects.get(name="Aread Irector")

        r = self.client.post(url,
                             dict(intended_std_level=str(draft.intended_std_level_id),
                                  ad=ad.pk,
                                  create_in_state=State.objects.get(used=True, type="draft-iesg", slug="watching").pk,
                                  notify="test@example.com",
                                  note="This is a note",
                                  telechat_date="",
                                  ))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug("draft-iesg"), "watching")
        self.assertEqual(draft.ad, ad)
        self.assertEqual(draft.note, "This is a note")
        self.assertTrue(not draft.latest_event(TelechatDocEvent, type="scheduled_for_telechat"))
        self.assertEqual(draft.docevent_set.count(), events_before + 3)
        events = list(draft.docevent_set.order_by('time', 'id'))
        self.assertEqual(events[-3].type, "started_iesg_process")
        self.assertEqual(len(outbox), mailbox_before)

        # Redo, starting in publication requested to make sure WG state is also set
        draft.unset_state('draft-iesg')
        draft.set_state(State.objects.get(type='draft-stream-ietf',slug='writeupw'))
        draft.stream = StreamName.objects.get(slug='ietf')
        draft.save()
        r = self.client.post(url,
                             dict(intended_std_level=str(draft.intended_std_level_id),
                                  ad=ad.pk,
                                  create_in_state=State.objects.get(used=True, type="draft-iesg", slug="pub-req").pk,
                                  notify="test@example.com",
                                  note="This is a note",
                                  telechat_date="",
                                  ))
        self.assertEqual(r.status_code, 302)
        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug('draft-iesg'),'pub-req')
        self.assertEqual(draft.get_state_slug('draft-stream-ietf'),'sub-pub')

    def test_edit_consensus(self):
        draft = make_test_data()
        
        url = urlreverse('doc_edit_consensus', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "secretary", url)

        self.assertTrue(not draft.latest_event(ConsensusDocEvent, type="changed_consensus"))
        r = self.client.post(url, dict(consensus="Yes"))
        self.assertEqual(r.status_code, 302)

        self.assertEqual(draft.latest_event(ConsensusDocEvent, type="changed_consensus").consensus, True)


class ResurrectTests(TestCase):
    def test_request_resurrect(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft", slug="expired"))

        url = urlreverse('doc_request_resurrect', kwargs=dict(name=draft.name))
        
        login_testing_unauthorized(self, "ad", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[type=submit]')), 1)


        # request resurrect
        events_before = draft.docevent_set.count()
        mailbox_before = len(outbox)
        
        r = self.client.post(url, dict())
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.docevent_set.count(), events_before + 1)
        e = draft.latest_event(type="requested_resurrect")
        self.assertTrue(e)
        self.assertEqual(e.by, Person.objects.get(name="Aread Irector"))
        self.assertTrue("Resurrection" in e.desc)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("Resurrection" in outbox[-1]['Subject'])

    def test_resurrect(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft", slug="expired"))

        DocEvent.objects.create(doc=draft,
                             type="requested_resurrect",
                             by=Person.objects.get(name="Aread Irector"))

        url = urlreverse('doc_resurrect', kwargs=dict(name=draft.name))
        
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[type=submit]')), 1)

        # complete resurrect
        events_before = draft.docevent_set.count()
        mailbox_before = len(outbox)
        
        r = self.client.post(url, dict())
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.docevent_set.count(), events_before + 1)
        self.assertEqual(draft.latest_event().type, "completed_resurrect")
        self.assertEqual(draft.get_state_slug(), "active")
        self.assertTrue(draft.expires >= datetime.datetime.now() + datetime.timedelta(days=settings.INTERNET_DRAFT_DAYS_TO_EXPIRE - 1))
        self.assertEqual(len(outbox), mailbox_before + 1)


class ExpireIDsTests(TestCase):
    def setUp(self):
        self.id_dir = os.path.abspath("tmp-id-dir")
        self.archive_dir = os.path.abspath("tmp-id-archive")
        os.mkdir(self.id_dir)
        os.mkdir(self.archive_dir)
        os.mkdir(os.path.join(self.archive_dir, "unknown_ids"))
        os.mkdir(os.path.join(self.archive_dir, "deleted_tombstones"))
        os.mkdir(os.path.join(self.archive_dir, "expired_without_tombstone"))
        
        settings.INTERNET_DRAFT_PATH = self.id_dir
        settings.INTERNET_DRAFT_ARCHIVE_DIR = self.archive_dir

    def tearDown(self):
        shutil.rmtree(self.id_dir)
        shutil.rmtree(self.archive_dir)

    def write_draft_file(self, name, size):
        f = open(os.path.join(self.id_dir, name), 'w')
        f.write("a" * size)
        f.close()
        
    def test_in_draft_expire_freeze(self):
        from ietf.doc.expire import in_draft_expire_freeze

        Meeting.objects.create(number="123",
                               type=MeetingTypeName.objects.get(slug="ietf"),
                               date=datetime.date.today())
        second_cut_off = Meeting.get_second_cut_off()
        ietf_monday = Meeting.get_ietf_monday()

        self.assertTrue(not in_draft_expire_freeze(datetime.datetime.combine(second_cut_off - datetime.timedelta(days=7), datetime.time(0, 0, 0))))
        self.assertTrue(not in_draft_expire_freeze(datetime.datetime.combine(second_cut_off, datetime.time(0, 0, 0))))
        self.assertTrue(in_draft_expire_freeze(datetime.datetime.combine(second_cut_off + datetime.timedelta(days=7), datetime.time(0, 0, 0))))
        self.assertTrue(in_draft_expire_freeze(datetime.datetime.combine(ietf_monday - datetime.timedelta(days=1), datetime.time(0, 0, 0))))
        self.assertTrue(not in_draft_expire_freeze(datetime.datetime.combine(ietf_monday, datetime.time(0, 0, 0))))
        
    def test_warn_expirable_drafts(self):
        from ietf.doc.expire import get_soon_to_expire_drafts, send_expire_warning_for_draft

        draft = make_test_data()

        self.assertEqual(len(list(get_soon_to_expire_drafts(14))), 0)

        # hack into expirable state
        draft.unset_state("draft-iesg")
        draft.expires = datetime.datetime.now() + datetime.timedelta(days=10)
        draft.save()

        self.assertEqual(len(list(get_soon_to_expire_drafts(14))), 1)
        
        # test send warning
        mailbox_before = len(outbox)

        send_expire_warning_for_draft(draft)

        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("aread@ietf.org" in str(outbox[-1])) # author
        self.assertTrue("marschairman@ietf.org" in str(outbox[-1]))
        
    def test_expire_drafts(self):
        from ietf.doc.expire import get_expired_drafts, send_expire_notice_for_draft, expire_draft

        draft = make_test_data()
        
        self.assertEqual(len(list(get_expired_drafts())), 0)
        
        # hack into expirable state
        draft.unset_state("draft-iesg")
        draft.expires = datetime.datetime.now()
        draft.save()

        self.assertEqual(len(list(get_expired_drafts())), 1)

        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="watching"))

        self.assertEqual(len(list(get_expired_drafts())), 1)

        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="iesg-eva"))

        self.assertEqual(len(list(get_expired_drafts())), 0)
        
        # test notice
        mailbox_before = len(outbox)

        send_expire_notice_for_draft(draft)

        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("expired" in outbox[-1]["Subject"])

        # test expiry
        txt = "%s-%s.txt" % (draft.name, draft.rev)
        self.write_draft_file(txt, 5000)

        expire_draft(draft)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug(), "expired")
        self.assertEqual(draft.get_state_slug("draft-iesg"), "dead")
        self.assertTrue(draft.latest_event(type="expired_document"))
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, txt)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, txt)))

    def test_clean_up_draft_files(self):
        draft = make_test_data()
        
        from ietf.doc.expire import clean_up_draft_files

        # put unknown file
        unknown = "draft-i-am-unknown-01.txt"
        self.write_draft_file(unknown, 5000)

        clean_up_draft_files()
        
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, unknown)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, "unknown_ids", unknown)))

        
        # put file with malformed name (no revision)
        malformed = draft.name + ".txt"
        self.write_draft_file(malformed, 5000)

        clean_up_draft_files()
        
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, malformed)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, "unknown_ids", malformed)))

        
        # RFC draft
        draft.set_state(State.objects.get(used=True, type="draft", slug="rfc"))
        draft.save()

        txt = "%s-%s.txt" % (draft.name, draft.rev)
        self.write_draft_file(txt, 5000)
        pdf = "%s-%s.pdf" % (draft.name, draft.rev)
        self.write_draft_file(pdf, 5000)

        clean_up_draft_files()
        
        # txt files shouldn't be moved (for some reason)
        self.assertTrue(os.path.exists(os.path.join(self.id_dir, txt)))
        
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, pdf)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, "unknown_ids", pdf)))


        # expire draft
        draft.set_state(State.objects.get(used=True, type="draft", slug="expired"))
        draft.expires = datetime.datetime.now() - datetime.timedelta(days=1)
        draft.save()

        e = DocEvent()
        e.doc = draft
        e.by = Person.objects.get(name="(System)")
        e.type = "expired_document"
        e.text = "Document has expired"
        e.time = draft.expires
        e.save()

        # expired without tombstone
        txt = "%s-%s.txt" % (draft.name, draft.rev)
        self.write_draft_file(txt, 5000)

        clean_up_draft_files()
        
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, txt)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, "expired_without_tombstone", txt)))
        

        # expired with tombstone
        revision_before = draft.rev

        txt = "%s-%s.txt" % (draft.name, draft.rev)
        self.write_draft_file(txt, 1000) # < 1500 means tombstone

        clean_up_draft_files()
        
        self.assertTrue(not os.path.exists(os.path.join(self.id_dir, txt)))
        self.assertTrue(os.path.exists(os.path.join(self.archive_dir, "deleted_tombstones", txt)))


class ExpireLastCallTests(TestCase):
    def test_expire_last_call(self):
        from ietf.doc.lastcall import get_expired_last_calls, expire_last_call
        
        # check that non-expirable drafts aren't expired

        draft = make_test_data()
        draft.set_state(State.objects.get(used=True, type="draft-iesg", slug="lc"))

        secretary = Person.objects.get(name="Sec Retary")
        
        self.assertEqual(len(list(get_expired_last_calls())), 0)

        e = LastCallDocEvent()
        e.doc = draft
        e.by = secretary
        e.type = "sent_last_call"
        e.text = "Last call sent"
        e.expires = datetime.datetime.now() + datetime.timedelta(days=14)
        e.save()
        
        self.assertEqual(len(list(get_expired_last_calls())), 0)

        # test expired
        e = LastCallDocEvent()
        e.doc = draft
        e.by = secretary
        e.type = "sent_last_call"
        e.text = "Last call sent"
        e.expires = datetime.datetime.now()
        e.save()
        
        drafts = list(get_expired_last_calls())
        self.assertEqual(len(drafts), 1)

        # expire it
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()
        
        expire_last_call(drafts[0])

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug("draft-iesg"), "writeupw")
        self.assertEqual(draft.docevent_set.count(), events_before + 1)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("Last Call Expired" in outbox[-1]["Subject"])


class IndividualInfoFormsTests(TestCase):
    def test_doc_change_stream(self):
        url = urlreverse('doc_change_stream', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.change-stream')),1) 

        # shift to ISE stream
        messages_before = len(outbox)
        r = self.client.post(url,dict(stream="ise",comment="7gRMTjBM"))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.stream_id,'ise')
        self.assertEqual(len(outbox),messages_before+1)
        self.assertTrue('Stream Change Notice' in outbox[-1]['Subject'])
        self.assertTrue('7gRMTjBM' in str(outbox[-1]))
        self.assertTrue('7gRMTjBM' in self.doc.latest_event(DocEvent,type='added_comment').desc)
        # Would be nice to test that the stream managers were in the To header...

        # shift to an unknown stream (it must be possible to throw a document out of any stream)
        r = self.client.post(url,dict(stream=""))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.stream,None)

    def test_doc_change_notify(self):
        url = urlreverse('doc_change_notify', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[name=notify]')),1)

        # Provide a list
        r = self.client.post(url,dict(notify="TJ2APh2P@ietf.org",save_addresses="1"))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.notify,'TJ2APh2P@ietf.org')
        
        # Ask the form to regenerate the list
        r = self.client.post(url,dict(regenerate_addresses="1"))
        self.assertEqual(r.status_code,200)
        self.doc = Document.objects.get(name=self.docname)
        # Regenerate does not save!
        self.assertEqual(self.doc.notify,'TJ2APh2P@ietf.org')
        q = PyQuery(r.content)
        self.assertTrue('TJ2Aph2P' not in q('form input[name=notify]')[0].value)

    def test_doc_change_intended_status(self):
        url = urlreverse('doc_change_intended_status', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.change-intended-status')),1)

        # don't allow status level to be cleared
        r = self.client.post(url,dict(intended_std_level=""))
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)
        
        # change intended status level
        messages_before = len(outbox)
        r = self.client.post(url,dict(intended_std_level="bcp",comment="ZpyQFGmA"))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.intended_std_level_id,'bcp')
        self.assertEqual(len(outbox),messages_before+1)
        self.assertTrue('ZpyQFGmA' in str(outbox[-1]))
        self.assertTrue('ZpyQFGmA' in self.doc.latest_event(DocEvent,type='added_comment').desc)
       
    def test_doc_change_telechat_date(self):
        url = urlreverse('doc_change_telechat_date', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.telechat-date')),1)

        # set a date
        self.assertFalse(self.doc.latest_event(TelechatDocEvent, "scheduled_for_telechat"))
        telechat_date = TelechatDate.objects.active().order_by('date')[0].date
        r = self.client.post(url,dict(telechat_date=telechat_date.isoformat()))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.latest_event(TelechatDocEvent, "scheduled_for_telechat").telechat_date,telechat_date)

        # Take the doc back off any telechat
        r = self.client.post(url,dict(telechat_date=""))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.doc.latest_event(TelechatDocEvent, "scheduled_for_telechat").telechat_date,None)
        
    def test_doc_change_iesg_note(self):
        url = urlreverse('doc_change_iesg_note', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.edit-iesg-note')),1)

        # post
        r = self.client.post(url,dict(note='ZpyQFGmA\r\nZpyQFGmA'))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.note,'ZpyQFGmA\nZpyQFGmA')
        self.assertTrue('ZpyQFGmA' in self.doc.latest_event(DocEvent,type='added_comment').desc)

    def test_doc_change_ad(self):
        url = urlreverse('doc_change_ad', kwargs=dict(name=self.docname))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=ad]')),1)
        
        # change ads
        ad2 = Person.objects.get(name='Ad No2')
        r = self.client.post(url,dict(ad=str(ad2.pk)))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.ad,ad2)
        self.assertTrue(self.doc.latest_event(DocEvent,type="added_comment").desc.startswith('Shepherding AD changed'))

    def test_doc_change_shepherd(self):
        url = urlreverse('doc_edit_shepherd',kwargs=dict(name=self.docname))
        
        login_testing_unauthorized(self, "plain", url)

        r = self.client.get(url)
        self.assertEqual(r.status_code,403)

        # get as the secretariat (and remain secretariat)
        login_testing_unauthorized(self, "secretary", url)

        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[id=id_shepherd]')),1)

        # change the shepherd
        plain = Person.objects.get(name='Plain Man')
        plain_email = plain.email_set.all()[0]
        r = self.client.post(url,dict(shepherd=plain_email))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertEqual(self.doc.shepherd,plain)
        self.assertTrue(self.doc.latest_event(DocEvent,type="added_comment").desc.startswith('Document shepherd changed to Plain Man'))

        ad = Person.objects.get(name='Aread Irector')
        two_answers = "%s,%s" % (plain_email, ad.email_set.all()[0])
        r = self.client.post(url,(dict(shepherd=two_answers)))
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

    def test_doc_view_shepherd_writeup(self):
        url = urlreverse('doc_shepherd_writeup',kwargs=dict(name=self.docname))
  
        # get as a shepherd
        self.client.login(remote_user="plain")

        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('span[id=doc_edit_shepherd_writeup]')),1)

        # Try again when no longer a shepherd.

        self.doc.shepherd = None
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('span[id=doc_edit_shepherd_writeup]')),1)

    def test_doc_change_shepherd_writeup(self):
        url = urlreverse('doc_edit_shepherd_writeup',kwargs=dict(name=self.docname))
  
        # get
        login_testing_unauthorized(self, "secretary", url)

        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form textarea[id=id_content]')),1)

        # direct edit
        r = self.client.post(url,dict(content='here is a new writeup',submit_response="1"))
        self.assertEqual(r.status_code,302)
        self.doc = Document.objects.get(name=self.docname)
        self.assertTrue(self.doc.latest_event(WriteupDocEvent,type="changed_protocol_writeup").text.startswith('here is a new writeup'))

        # file upload
        test_file = StringIO.StringIO("This is a different writeup.")
        test_file.name = "unnamed"
        r = self.client.post(url,dict(txt=test_file,submit_response="1"))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name=self.docname)
        self.assertTrue(self.doc.latest_event(WriteupDocEvent,type="changed_protocol_writeup").text.startswith('This is a different writeup.'))

        # template reset
        r = self.client.post(url,dict(txt=test_file,reset_text="1"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(q('textarea')[0].text.strip().startswith("As required by RFC 4858"))

    def setUp(self):
        make_test_data()
        self.docname='draft-ietf-mars-test'
        self.doc = Document.objects.get(name=self.docname)
        

class SubmitToIesgTests(TestCase):
    def verify_permissions(self):

        def verify_fail(remote_user):
            if remote_user:
                self.client.login(remote_user=remote_user)
            r = self.client.get(url)
            self.assertEqual(r.status_code,404)

        def verify_can_see(remote_user):
            self.client.login(remote_user=remote_user)
            r = self.client.get(url)
            self.assertEqual(r.status_code,200)
            q = PyQuery(r.content)
            self.assertEqual(len(q('form input[name="confirm"]')),1) 

        url = urlreverse('doc_to_iesg', kwargs=dict(name=self.docname))

        for username in [None,'plain','iana','iab chair']:
            verify_fail(username)

        for username in ['marschairman','secretary','ad']:
            verify_can_see(username)
        
    def cancel_submission(self):
        url = urlreverse('doc_to_iesg', kwargs=dict(name=self.docname))
        self.client.login(remote_user='marschairman')

	r = self.client.post(url, dict(cancel="1"))
        self.assertEqual(r.status_code, 302)

        doc = Document.objects.get(pk=self.doc.pk)
        self.assertTrue(doc.get_state('draft-iesg')==None)

    def confirm_submission(self):
        url = urlreverse('doc_to_iesg', kwargs=dict(name=self.docname))
        self.client.login(remote_user='marschairman')

        docevent_count_pre = self.doc.docevent_set.count()
        mailbox_before = len(outbox)

	r = self.client.post(url, dict(confirm="1"))
        self.assertEqual(r.status_code, 302)

        doc = Document.objects.get(pk=self.doc.pk)
        self.assertTrue(doc.get_state('draft-iesg').slug=='pub-req')
        self.assertTrue(doc.get_state('draft-stream-ietf').slug=='sub-pub')
        self.assertTrue(doc.ad!=None)
        self.assertTrue(doc.docevent_set.count() != docevent_count_pre)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("Publication has been requested" in outbox[-1]['Subject'])

    def setUp(self):
        make_test_data()
        self.docname='draft-ietf-mars-test'
        self.doc = Document.objects.get(name=self.docname)
        self.doc.unset_state('draft-iesg') 


class RequestPublicationTests(TestCase):
    def test_request_publication(self):
        draft = make_test_data()
        draft.stream = StreamName.objects.get(slug="iab")
        draft.group = Group.objects.get(acronym="iab")
        draft.intended_std_level = IntendedStdLevelName.objects.get(slug="inf")
        draft.save()
        draft.set_state(State.objects.get(used=True, type="draft-stream-iab", slug="approved"))

        url = urlreverse('doc_request_publication', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "iab-chair", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        subject = q('input#id_subject')[0].get("value")
        self.assertTrue("Document Action" in subject)
        body = q('.request-publication #id_body').text()
        self.assertTrue("Informational" in body)
        self.assertTrue("IAB" in body)

        # approve
        mailbox_before = len(outbox)

        r = self.client.post(url, dict(subject=subject, body=body, skiprfceditorpost="1"))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(name=draft.name)
        self.assertEqual(draft.get_state_slug("draft-stream-iab"), "rfc-edit")
        self.assertEqual(len(outbox), mailbox_before + 2)
        self.assertTrue("Document Action" in outbox[-2]['Subject'])
        self.assertTrue("Document Action" in draft.message_set.order_by("-time")[0].subject)
        # the IANA copy
        self.assertTrue("Document Action" in outbox[-1]['Subject'])
        self.assertTrue(not outbox[-1]['CC'])

class AdoptDraftTests(TestCase):
    def test_adopt_document(self):
        draft = make_test_data()
        draft.stream = None
        draft.group = Group.objects.get(type="individ")
        draft.save()
        draft.unset_state("draft-stream-ietf")

        url = urlreverse('doc_adopt_draft', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name="group"] option')), 1) # we can only select "mars"

        # adopt in mars WG
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()
        r = self.client.post(url,
                             dict(comment="some comment",
                                  group=Group.objects.get(acronym="mars").pk,
                                  weeks="10"))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEqual(draft.group.acronym, "mars")
        self.assertEqual(draft.stream_id, "ietf")
        self.assertEqual(draft.docevent_set.count() - events_before, 4)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("adopted" in outbox[-1]["Subject"].lower())
        self.assertTrue("marschairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("marsdelegate@ietf.org" in unicode(outbox[-1]))

class ChangeStreamStateTests(TestCase):
    def test_set_tags(self):
        draft = make_test_data()
        draft.tags = DocTagName.objects.filter(slug="w-expert")
        draft.group.unused_tags.add("w-refdoc")

        url = urlreverse('doc_change_stream_state', kwargs=dict(name=draft.name, state_type="draft-stream-ietf"))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        # make sure the unused tags are hidden
        unused = draft.group.unused_tags.values_list("slug", flat=True)
        for t in q("input[name=tags]"):
            self.assertTrue(t.attrib["value"] not in unused)

        # set tags
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()
        r = self.client.post(url,
                             dict(new_state=draft.get_state("draft-stream-%s" % draft.stream_id).pk,
                                  comment="some comment",
                                  weeks="10",
                                  tags=["need-aut", "sheph-u"],
                                  ))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEqual(draft.tags.count(), 2)
        self.assertEqual(draft.tags.filter(slug="w-expert").count(), 0)
        self.assertEqual(draft.tags.filter(slug="need-aut").count(), 1)
        self.assertEqual(draft.tags.filter(slug="sheph-u").count(), 1)
        self.assertEqual(draft.docevent_set.count() - events_before, 2)
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("tags changed" in outbox[-1]["Subject"].lower())
        self.assertTrue("marschairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("marsdelegate@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("plain@example.com" in unicode(outbox[-1]))

    def test_set_state(self):
        draft = make_test_data()

        url = urlreverse('doc_change_stream_state', kwargs=dict(name=draft.name, state_type="draft-stream-ietf"))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        # make sure the unused states are hidden
        unused = draft.group.unused_states.values_list("pk", flat=True)
        for t in q("select[name=new_state]").find("option[name=tags]"):
            self.assertTrue(t.attrib["value"] not in unused)
        self.assertEqual(len(q('select[name=new_state]')), 1)

        # set new state
        old_state = draft.get_state("draft-stream-%s" % draft.stream_id )
        new_state = State.objects.get(used=True, type="draft-stream-%s" % draft.stream_id, slug="parked")
        self.assertNotEqual(old_state, new_state)
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()

        r = self.client.post(url,
                             dict(new_state=new_state.pk,
                                  comment="some comment",
                                  weeks="10",
                                  tags=[t.pk for t in draft.tags.filter(slug__in=get_tags_for_stream_id(draft.stream_id))],
                                  ))
        self.assertEqual(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEqual(draft.get_state("draft-stream-%s" % draft.stream_id), new_state)
        self.assertEqual(draft.docevent_set.count() - events_before, 2)
        reminder = DocReminder.objects.filter(event__doc=draft, type="stream-s")
        self.assertEqual(len(reminder), 1)
        due = datetime.datetime.now() + datetime.timedelta(weeks=10)
        self.assertTrue(due - datetime.timedelta(days=1) <= reminder[0].due <= due + datetime.timedelta(days=1))
        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue("state changed" in outbox[-1]["Subject"].lower())
        self.assertTrue("marschairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("marsdelegate@ietf.org" in unicode(outbox[-1]))

