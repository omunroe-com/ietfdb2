import os, shutil, json

from django.core.urlresolvers import reverse as urlreverse
from django.conf import settings

from pyquery import PyQuery

from ietf.utils.test_data import make_test_data
from ietf.doc.models import *
from ietf.person.models import Person
from ietf.group.models import Group, GroupMilestone
from ietf.name.models import StreamName
from ietf.iesg.models import *
from ietf.utils.test_utils import TestCase, login_testing_unauthorized
from ietf.iesg.agenda import get_agenda_date, agenda_data

class IESGTests(TestCase):
    def test_feed(self):
        draft = make_test_data()
        draft.set_state(State.objects.get(type="draft-iesg", slug="iesg-eva"))

        pos = BallotPositionDocEvent()
        pos.ballot = draft.latest_event(BallotDocEvent, type="created_ballot")
        pos.pos_id = "discuss"
        pos.type = "changed_ballot_position"
        pos.doc = draft
        pos.ad = pos.by = Person.objects.get(user__username="ad")
        pos.save()

        r = self.client.get(urlreverse("ietf.iesg.views.discusses"))
        self.assertEqual(r.status_code, 200)

        self.assertTrue(draft.name in r.content)
        self.assertTrue(pos.ad.plain_name() in r.content)

    def test_milestones_needing_review(self):
        draft = make_test_data()

        m = GroupMilestone.objects.create(group=draft.group,
                                          state_id="review",
                                          desc="Test milestone",
                                          due=datetime.date.today())

        url = urlreverse("ietf.iesg.views.milestones_needing_review")
        login_testing_unauthorized(self, "ad", url)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(m.desc in r.content)

    def test_review_decisions(self):
        draft = make_test_data()

        e = DocEvent(type="iesg_approved")
        e.doc = draft
        e.by = Person.objects.get(name="Aread Irector")
        e.save()

        url = urlreverse('ietf.iesg.views.review_decisions')

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(draft.name in r.content)

class IESGAgendaTests(TestCase):
    def setUp(self):
        make_test_data()

        ise_draft = Document.objects.get(name="draft-imaginary-independent-submission")
        ise_draft.stream = StreamName.objects.get(slug="ise")
        ise_draft.save()

        self.telechat_docs = {
            "ietf_draft": Document.objects.get(name="draft-ietf-mars-test"),
            "ise_draft": ise_draft,
            "conflrev": Document.objects.get(name="conflict-review-imaginary-irtf-submission"),
            "statchg": Document.objects.get(name="status-change-imaginary-mid-review"),
            "charter": Document.objects.filter(type="charter")[0],
            }

        by = Person.objects.get(name="Aread Irector")
        date = get_agenda_date()

        self.draft_dir = os.path.abspath("tmp-agenda-draft-dir")
        os.mkdir(self.draft_dir)
        settings.INTERNET_DRAFT_PATH = self.draft_dir

        for d in self.telechat_docs.values():
            TelechatDocEvent.objects.create(type="scheduled_for_telechat",
                                            doc=d,
                                            by=by,
                                            telechat_date=date,
                                            returning_item=True)


    def tearDown(self):
        shutil.rmtree(self.draft_dir)

    def test_fill_in_agenda_docs(self):
        draft = self.telechat_docs["ietf_draft"]
        statchg = self.telechat_docs["statchg"]
        conflrev = self.telechat_docs["conflrev"]
        charter = self.telechat_docs["charter"]

        # put on agenda
        date = datetime.date.today() + datetime.timedelta(days=50)
        TelechatDate.objects.create(date=date)
        telechat_event = TelechatDocEvent.objects.create(
            type="scheduled_for_telechat",
            doc=draft,
            by=Person.objects.get(name="Aread Irector"),
            telechat_date=date,
            returning_item=False)
        date_str = date.isoformat()

        # 2.1 protocol WG submissions
        draft.intended_std_level_id = "ps"
        draft.group = Group.objects.get(acronym="mars")
        draft.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="iesg-eva"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.1.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.1.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="pub-req"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.1.3"]["docs"])

        # 2.2 protocol individual submissions
        draft.group = Group.objects.get(type="individ")
        draft.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="iesg-eva"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.2.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.2.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="pub-req"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["2.2.3"]["docs"])

        # 3.1 document WG submissions
        draft.intended_std_level_id = "inf"
        draft.group = Group.objects.get(acronym="mars")
        draft.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="iesg-eva"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.1.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.1.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="pub-req"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.1.3"]["docs"])

        # 3.2 document individual submissions
        draft.group = Group.objects.get(type="individ")
        draft.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="iesg-eva"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.2.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.2.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        draft.set_state(State.objects.get(type="draft-iesg", slug="pub-req"))
        self.assertTrue(draft in agenda_data(date_str)["sections"]["3.2.3"]["docs"])

        # 2.3 protocol status changes
        telechat_event.doc = statchg
        telechat_event.save()

        relation = RelatedDocument.objects.create(
            source=statchg,
            target=DocAlias.objects.filter(name__startswith='rfc', document__std_level="ps")[0],
            relationship_id="tohist")

        statchg.group = Group.objects.get(acronym="mars")
        statchg.save()
        statchg.set_state(State.objects.get(type="statchg", slug="iesgeval"))
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["2.3.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["2.3.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        statchg.set_state(State.objects.get(type="statchg", slug="adrev"))
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["2.3.3"]["docs"])
        
        # 3.3 document status changes
        relation.target = DocAlias.objects.filter(name__startswith='rfc', document__std_level="inf")[0]
        relation.save()

        statchg.group = Group.objects.get(acronym="mars")
        statchg.save()
        statchg.set_state(State.objects.get(type="statchg", slug="iesgeval"))
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["3.3.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["3.3.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        statchg.set_state(State.objects.get(type="statchg", slug="adrev"))
        self.assertTrue(statchg in agenda_data(date_str)["sections"]["3.3.3"]["docs"])

        # 3.4 IRTF/ISE conflict reviews
        telechat_event.doc = conflrev
        telechat_event.save()

        conflrev.group = Group.objects.get(acronym="mars")
        conflrev.save()
        conflrev.set_state(State.objects.get(type="conflrev", slug="iesgeval"))
        self.assertTrue(conflrev in agenda_data(date_str)["sections"]["3.4.1"]["docs"])

        telechat_event.returning_item = True
        telechat_event.save()
        self.assertTrue(conflrev in agenda_data(date_str)["sections"]["3.4.2"]["docs"])

        telechat_event.returning_item = False
        telechat_event.save()
        conflrev.set_state(State.objects.get(type="conflrev", slug="needshep"))
        self.assertTrue(conflrev in agenda_data(date_str)["sections"]["3.4.3"]["docs"])


        # 4 WGs
        telechat_event.doc = charter
        telechat_event.save()

        charter.group = Group.objects.get(acronym="mars")
        charter.save()

        charter.group.state_id = "bof"
        charter.group.save()

        charter.set_state(State.objects.get(type="charter", slug="infrev"))
        self.assertTrue(charter in agenda_data(date_str)["sections"]["4.1.1"]["docs"])

        charter.set_state(State.objects.get(type="charter", slug="iesgrev"))
        self.assertTrue(charter in agenda_data(date_str)["sections"]["4.1.2"]["docs"])

        charter.group.state_id = "active"
        charter.group.save()

        charter.set_state(State.objects.get(type="charter", slug="infrev"))
        self.assertTrue(charter in agenda_data(date_str)["sections"]["4.2.1"]["docs"])

        charter.set_state(State.objects.get(type="charter", slug="iesgrev"))
        self.assertTrue(charter in agenda_data(date_str)["sections"]["4.2.2"]["docs"])

        #for n, s in agenda_data(date_str)["sections"].iteritems():
        #    print n, s.get("docs") if "docs" in s else s["title"]

    def test_feed(self):
        r = self.client.get("/feed/iesg-agenda/")
        self.assertEqual(r.status_code, 200)

        for d in self.telechat_docs.values():
            self.assertTrue(d.name in r.content)
            self.assertTrue(d.title in r.content)

    def test_agenda_json(self):
        r = self.client.get(urlreverse("ietf.iesg.views.agenda_json"))
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            if d.type_id == "charter":
                self.assertTrue(d.group.name in r.content, "%s not in response" % k)
                self.assertTrue(d.group.acronym in r.content, "%s acronym not in response" % k)
            else:
                self.assertTrue(d.name in r.content, "%s not in response" % k)
                self.assertTrue(d.title in r.content, "%s title not in response" % k)

        self.assertTrue(json.loads(r.content))

    def test_agenda(self):
        r = self.client.get(urlreverse("ietf.iesg.views.agenda"))
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            self.assertTrue(d.name in r.content, "%s not in response" % k)
            self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_txt(self):
        r = self.client.get(urlreverse("ietf.iesg.views.agenda_txt"))
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            if d.type_id == "charter":
                self.assertTrue(d.group.name in r.content, "%s not in response" % k)
                self.assertTrue(d.group.acronym in r.content, "%s acronym not in response" % k)
            else:
                self.assertTrue(d.name in r.content, "%s not in response" % k)
                self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_scribe_template(self):
        r = self.client.get(urlreverse("ietf.iesg.views.agenda_scribe_template"))
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            if d.type_id == "charter":
                continue # scribe template doesn't contain chartering info

            self.assertTrue(d.name in r.content, "%s not in response" % k)
            self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_moderator_package(self):
        url = urlreverse("ietf.iesg.views.agenda_moderator_package")
        login_testing_unauthorized(self, "secretary", url)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            if d.type_id == "charter":
                self.assertTrue(d.group.name in r.content, "%s not in response" % k)
                self.assertTrue(d.group.acronym in r.content, "%s acronym not in response" % k)
            else:
                self.assertTrue(d.name in r.content, "%s not in response" % k)
                self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_package(self):
        url = urlreverse("ietf.iesg.views.agenda_package")
        login_testing_unauthorized(self, "secretary", url)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            if d.type_id == "charter":
                self.assertTrue(d.group.name in r.content, "%s not in response" % k)
                self.assertTrue(d.group.acronym in r.content, "%s acronym not in response" % k)
            else:
                self.assertTrue(d.name in r.content, "%s not in response" % k)
                self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_documents_txt(self):
        url = urlreverse("ietf.iesg.views.agenda_documents_txt")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            self.assertTrue(d.name in r.content, "%s not in response" % k)

    def test_agenda_documents(self):
        url = urlreverse("ietf.iesg.views.agenda_documents")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        for k, d in self.telechat_docs.iteritems():
            self.assertTrue(d.name in r.content, "%s not in response" % k)
            self.assertTrue(d.title in r.content, "%s title not in response" % k)

    def test_agenda_telechat_docs(self):
        d1 = self.telechat_docs["ietf_draft"]
        d2 = self.telechat_docs["ise_draft"]

        d1_filename = "%s-%s.txt" % (d1.name, d1.rev)
        d2_filename = "%s-%s.txt" % (d2.name, d2.rev)

        with open(os.path.join(self.draft_dir, d1_filename), "w") as f:
            f.write("test content")

        url = urlreverse("ietf.iesg.views.telechat_docs_tarfile", kwargs=dict(date=get_agenda_date().isoformat()))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        import tarfile, StringIO

        tar = tarfile.open(None, fileobj=StringIO.StringIO(r.content))
        names = tar.getnames()
        self.assertTrue(d1_filename in names)
        self.assertTrue(d2_filename not in names)
        self.assertTrue("manifest.txt" in names)

        f = tar.extractfile(d1_filename)
        self.assertEqual(f.read(), "test content")

        f = tar.extractfile("manifest.txt")
        lines = list(f.readlines())
        self.assertTrue("Included" in [l for l in lines if d1_filename in l][0])
        self.assertTrue("Not found" in [l for l in lines if d2_filename in l][0])

class RescheduleOnAgendaTests(TestCase):
    def test_reschedule(self):
        draft = make_test_data()

        # add to schedule
        e = TelechatDocEvent(type="scheduled_for_telechat")
        e.doc = draft
        e.by = Person.objects.get(name="Aread Irector")
        e.telechat_date = TelechatDate.objects.active()[0].date
        e.returning_item = True
        e.save()
        
        form_id = draft.pk
        telechat_date_before = e.telechat_date
        
        url = urlreverse('ietf.iesg.views.agenda_documents')
        
        self.client.login(remote_user="secretary")

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        
        self.assertEqual(len(q('form select[name=%s-telechat_date]' % form_id)), 1)
        self.assertEqual(len(q('form input[name=%s-clear_returning_item]' % form_id)), 1)

        # reschedule
        events_before = draft.docevent_set.count()
        d = TelechatDate.objects.active()[3].date

        r = self.client.post(url, { '%s-telechat_date' % form_id: d.isoformat(),
                                    '%s-clear_returning_item' % form_id: "1" })

        self.assertEqual(r.status_code, 302)

        # check that it moved below the right header in the DOM on the
        # agenda docs page
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        d_header_pos = r.content.find("IESG telechat %s" % d.isoformat())
        draft_pos = r.content.find(draft.name)
        self.assertTrue(d_header_pos < draft_pos)

        self.assertTrue(draft.latest_event(TelechatDocEvent, "scheduled_for_telechat"))
        self.assertEqual(draft.latest_event(TelechatDocEvent, "scheduled_for_telechat").telechat_date, d)
        self.assertTrue(not draft.latest_event(TelechatDocEvent, "scheduled_for_telechat").returning_item)
        self.assertEqual(draft.docevent_set.count(), events_before + 1)

class DeferUndeferTestCase(TestCase):
    def helper_test_defer(self,name):

        doc = Document.objects.get(name=name)
        url = urlreverse('doc_defer_ballot',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # some additional setup
        dates = TelechatDate.objects.active().order_by("date")
        first_date = dates[0].date
        second_date = dates[1].date

        e = TelechatDocEvent(type="scheduled_for_telechat",
                             doc = doc,
                             by = Person.objects.get(name="Aread Irector"),
                             telechat_date = first_date,
                             returning_item = False, 
                            )
        e.save()

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.defer')),1)

        # defer
        self.assertEqual(doc.telechat_date(), first_date)
        r = self.client.post(url,dict())
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name=name)
        self.assertEqual(doc.telechat_date(), second_date)
        self.assertTrue(doc.returning_item())
        defer_states = dict(draft=['draft-iesg','defer'],conflrev=['conflrev','defer'])
        if doc.type_id in defer_states:
           self.assertEqual(doc.get_state(defer_states[doc.type_id][0]).slug,defer_states[doc.type_id][1])


    def helper_test_undefer(self,name):

        doc = Document.objects.get(name=name)
        url = urlreverse('doc_undefer_ballot',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # some additional setup
        dates = TelechatDate.objects.active().order_by("date")
        first_date = dates[0].date
        second_date = dates[1].date

        e = TelechatDocEvent(type="scheduled_for_telechat",
                             doc = doc,
                             by = Person.objects.get(name="Aread Irector"),
                             telechat_date = second_date,
                             returning_item = True, 
                            )
        e.save()
        defer_states = dict(draft=['draft-iesg','defer'],conflrev=['conflrev','defer'])
        if doc.type_id in defer_states:
            doc.set_state(State.objects.get(used=True, type=defer_states[doc.type_id][0],slug=defer_states[doc.type_id][1]))
            doc.save()

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.undefer')),1)

        # undefer
        self.assertEqual(doc.telechat_date(), second_date)
        r = self.client.post(url,dict())
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name=name)
        self.assertEqual(doc.telechat_date(), first_date)
        self.assertTrue(doc.returning_item()) 
        undefer_states = dict(draft=['draft-iesg','iesg-eva'],conflrev=['conflrev','iesgeval'])
        if doc.type_id in undefer_states:
           self.assertEqual(doc.get_state(undefer_states[doc.type_id][0]).slug,undefer_states[doc.type_id][1])

    def test_defer_draft(self):
        self.helper_test_defer('draft-ietf-mars-test')

    def test_defer_conflict_review(self):
        self.helper_test_defer('conflict-review-imaginary-irtf-submission')

    def test_undefer_draft(self):
        self.helper_test_undefer('draft-ietf-mars-test')

    def test_undefer_conflict_review(self):
        self.helper_test_undefer('conflict-review-imaginary-irtf-submission')

    # when charters support being deferred, be sure to test them here

    def setUp(self):
        make_test_data()
