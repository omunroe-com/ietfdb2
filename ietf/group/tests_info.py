import os
import shutil
import calendar
import datetime
import json

from pyquery import PyQuery
from tempfile import NamedTemporaryFile
import debug                            # pyflakes:ignore

from django.conf import settings
from django.core.urlresolvers import reverse as urlreverse

from ietf.doc.models import Document, DocAlias, DocEvent, State
from ietf.group.models import Group, GroupEvent, GroupMilestone, GroupStateTransitions, MilestoneGroupEvent
from ietf.group.utils import save_group_in_history
from ietf.name.models import DocTagName, GroupStateName
from ietf.person.models import Person, Email
from ietf.utils.test_utils import TestCase
from ietf.utils.mail import outbox
from ietf.utils.test_data import make_test_data
from ietf.utils.test_utils import login_testing_unauthorized
from ietf.group.mails import ( email_milestone_review_reminder, email_milestones_due,
    email_milestones_overdue, groups_needing_milestones_due_reminder,
    groups_needing_milestones_overdue_reminder, groups_with_milestones_needing_review )

class GroupPagesTests(TestCase):
    def setUp(self):
        self.charter_dir = os.path.abspath("tmp-charter-dir")
        os.mkdir(self.charter_dir)
        settings.CHARTER_PATH = self.charter_dir

    def tearDown(self):
        shutil.rmtree(self.charter_dir)

    def test_active_groups(self):
        draft = make_test_data()
        group = draft.group

        url = urlreverse('ietf.group.info.active_groups', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.parent.name in r.content)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.ad_role().person.plain_name() in r.content)

        url = urlreverse('ietf.group.info.active_groups', kwargs=dict(group_type="rg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_wg_summaries(self):
        draft = make_test_data()
        group = draft.group

        chair = Email.objects.filter(role__group=group, role__name="chair")[0]

        with open(os.path.join(self.charter_dir, "%s-%s.txt" % (group.charter.canonical_name(), group.charter.rev)), "w") as f:
            f.write("This is a charter.")

        url = urlreverse('ietf.group.info.wg_summary_area', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.parent.name in r.content)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(chair.address in r.content)

        url = urlreverse('ietf.group.info.wg_summary_acronym', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(chair.address in r.content)
        
        url = urlreverse('ietf.group.info.wg_charters', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.ad_role().person.plain_name() in r.content)
        self.assertTrue(chair.address in r.content)
        self.assertTrue("This is a charter." in r.content)

        url = urlreverse('ietf.group.info.wg_charters_by_acronym', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.ad_role().person.plain_name() in r.content)
        self.assertTrue(chair.address in r.content)
        self.assertTrue("This is a charter." in r.content)

    def test_chartering_groups(self):
        draft = make_test_data()
        group = draft.group
        group.charter.set_state(State.objects.get(used=True, type="charter", slug="intrev"))

        url = urlreverse('ietf.group.info.chartering_groups')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('#content a:contains("%s")' % group.acronym)), 1)

    def test_concluded_groups(self):
        draft = make_test_data()
        group = draft.group
        group.state = GroupStateName.objects.get(used=True, slug="conclude")
        group.save()

        url = urlreverse('ietf.group.info.concluded_groups')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('#content a:contains("%s")' % group.acronym)), 1)

    def test_bofs(self):
        draft = make_test_data()
        group = draft.group
        group.state_id = "bof"
        group.save()

        url = urlreverse('ietf.group.info.bofs', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('#content a:contains("%s")' % group.acronym)), 1)
        
    def test_group_documents(self):
        draft = make_test_data()
        group = draft.group

        draft2 = Document.objects.create(
            name="draft-somebody-mars-test",
            time=datetime.datetime.now(),
            type_id="draft",
            title="Test By Somebody",
            stream_id="ietf",
            group=Group.objects.get(type="individ"),
            abstract="Abstract.",
            rev="01",
            pages=2,
            intended_std_level_id="ps",
            shepherd=None,
            ad=None,
            expires=datetime.datetime.now() + datetime.timedelta(days=10),
            notify="",
            note="",
            )

        draft2.set_state(State.objects.get(used=True, type="draft", slug="active"))
        DocAlias.objects.create(
            document=draft2,
            name=draft2.name,
            )

        url = urlreverse('ietf.group.info.group_documents', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(draft.name in r.content)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.acronym in r.content)

        self.assertTrue(draft2.name in r.content)

        # Make sure that a logged in user is presented with an opportunity to add results to their community list
        self.client.login(username="secretary", password="secretary+password")
        r = self.client.get(url)
        q = PyQuery(r.content)
        self.assertTrue(any([draft2.name in x.attrib['href'] for x in q('table td a.community-list-add-remove-doc')]))

        # test the txt version too while we're at it
        url = urlreverse('ietf.group.info.group_documents_txt', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(draft.name in r.content)
        self.assertTrue(draft2.name in r.content)

    def test_group_charter(self):
        draft = make_test_data()
        group = draft.group

        with open(os.path.join(self.charter_dir, "%s-%s.txt" % (group.charter.canonical_name(), group.charter.rev)), "w") as f:
            f.write("This is a charter.")

        milestone = GroupMilestone.objects.create(
            group=group,
            state_id="active",
            desc="Get Work Done",
            due=datetime.date.today() + datetime.timedelta(days=100))
        milestone.docs.add(draft)

        url = group.about_url()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue("This is a charter." in r.content)
        self.assertTrue(milestone.desc in r.content)
        self.assertTrue(milestone.docs.all()[0].name in r.content)

    def test_group_about(self):
        make_test_data()
        group = Group.objects.create(
            type_id="team",
            acronym="testteam",
            name="Test Team",
            description="The test team is testing.",
            state_id="active",
        )

        url = group.about_url()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(group.name in r.content)
        self.assertTrue(group.acronym in r.content)
        self.assertTrue(group.description in r.content)

    def test_materials(self):
        make_test_data()
        group = Group.objects.create(type_id="team", acronym="testteam", name="Test Team", state_id="active")

        doc = Document.objects.create(
            name="slides-testteam-test-slides",
            rev="00",
            title="Test Slides",
            group=group,
            type_id="slides",
        )
        doc.set_state(State.objects.get(type="slides", slug="active"))
        DocAlias.objects.create(name=doc.name, document=doc)

        url = urlreverse("group_materials", kwargs={ 'acronym': group.acronym })
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(doc.title in r.content)
        self.assertTrue(doc.name in r.content)

        # try deleting the document and check it's gone
        doc.set_state(State.objects.get(type="slides", slug="deleted"))

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(doc.title not in r.content)

    def test_history(self):
        draft = make_test_data()
        group = draft.group

        e = GroupEvent.objects.create(
            group=group,
            desc="Something happened.",
            type="added_comment",
            by=Person.objects.get(name="(System)"))

        url = urlreverse('ietf.group.info.history', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(e.desc in r.content)

    def test_feed(self):
        draft = make_test_data()
        group = draft.group

        ge = GroupEvent.objects.create(
            group=group,
            desc="Something happened.",
            type="added_comment",
            by=Person.objects.get(name="(System)"))

        de = DocEvent.objects.create(
            doc=group.charter,
            desc="Something else happened.",
            type="added_comment",
            by=Person.objects.get(name="(System)"))

        r = self.client.get("/feed/group-changes/%s/" % group.acronym)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(ge.desc in r.content)
        self.assertTrue(de.desc in r.content)


class GroupEditTests(TestCase):
    def setUp(self):
        self.charter_dir = os.path.abspath("tmp-charter-dir")
        os.mkdir(self.charter_dir)
        settings.CHARTER_PATH = self.charter_dir

    def tearDown(self):
        shutil.rmtree(self.charter_dir)

    def test_create(self):
        make_test_data()

        url = urlreverse('group_create', kwargs=dict(group_type="wg"))
        login_testing_unauthorized(self, "secretary", url)

        num_wgs = len(Group.objects.filter(type="wg"))

        bof_state = GroupStateName.objects.get(slug="bof")

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[name=acronym]')), 1)

        # faulty post
        r = self.client.post(url, dict(acronym="foobarbaz")) # No name
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        self.assertEqual(len(Group.objects.filter(type="wg")), num_wgs)

        # acronym contains non-alphanumeric
        r = self.client.post(url, dict(acronym="test...", name="Testing WG", state=bof_state.pk))
        self.assertEqual(r.status_code, 200)

        # acronym contains hyphen
        r = self.client.post(url, dict(acronym="test-wg", name="Testing WG", state=bof_state.pk))
        self.assertEqual(r.status_code, 200)

        # acronym too short
        r = self.client.post(url, dict(acronym="t", name="Testing WG", state=bof_state.pk))
        self.assertEqual(r.status_code, 200)

        # acronym doesn't start with an alpha character
        r = self.client.post(url, dict(acronym="1startwithalpha", name="Testing WG", state=bof_state.pk))
        self.assertEqual(r.status_code, 200)

        # creation
        r = self.client.post(url, dict(acronym="testwg", name="Testing WG", state=bof_state.pk))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(Group.objects.filter(type="wg")), num_wgs + 1)
        group = Group.objects.get(acronym="testwg")
        self.assertEqual(group.name, "Testing WG")
        self.assertEqual(group.charter.name, "charter-ietf-testwg")
        self.assertEqual(group.charter.rev, "00-00")

    def test_create_based_on_existing_bof(self):
        make_test_data()

        url = urlreverse('group_create', kwargs=dict(group_type="wg"))
        login_testing_unauthorized(self, "secretary", url)

        group = Group.objects.get(acronym="mars")

        # try hijacking area - faulty
        r = self.client.post(url, dict(name="Test", acronym=group.parent.acronym))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        self.assertEqual(len(q('form input[name="confirm_acronym"]')), 0) # can't confirm us out of this

        # try elevating BoF to WG
        group.state_id = "bof"
        group.save()

        r = self.client.post(url, dict(name="Test", acronym=group.acronym))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        self.assertEqual(len(q('form input[name="confirm_acronym"]')), 1)

        self.assertEqual(Group.objects.get(acronym=group.acronym).state_id, "bof")

        # confirm elevation
        state = GroupStateName.objects.get(slug="proposed")
        r = self.client.post(url, dict(name="Test", acronym=group.acronym, confirm_acronym="1", state=state.pk))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Group.objects.get(acronym=group.acronym).state_id, "proposed")
        self.assertEqual(Group.objects.get(acronym=group.acronym).name, "Test")

    def test_edit_info(self):
        make_test_data()
        group = Group.objects.get(acronym="mars")

        url = urlreverse('group_edit', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=parent]')), 1)
        self.assertEqual(len(q('form input[name=acronym]')), 1)

        # faulty post
        Group.objects.create(name="Collision Test Group", acronym="collide")
        r = self.client.post(url, dict(acronym="collide"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)

        # create old acronym
        group.acronym = "oldmars"
        group.save()
        save_group_in_history(group)
        group.acronym = "mars"
        group.save()

        # post with warning
        r = self.client.post(url, dict(acronym="oldmars"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        
        # edit info
        with open(os.path.join(self.charter_dir, "%s-%s.txt" % (group.charter.canonical_name(), group.charter.rev)), "w") as f:
            f.write("This is a charter.")
        area = group.parent
        ad = Person.objects.get(name="Aread Irector")
        state = GroupStateName.objects.get(slug="bof")
        r = self.client.post(url,
                             dict(name="Mars Not Special Interest Group",
                                  acronym="mars",
                                  parent=area.pk,
                                  ad=ad.pk,
                                  state=state.pk,
                                  chairs="aread@ietf.org, ad1@ietf.org",
                                  secretaries="aread@ietf.org, ad1@ietf.org, ad2@ietf.org",
                                  techadv="aread@ietf.org",
                                  delegates="ad2@ietf.org",
                                  list_email="mars@mail",
                                  list_subscribe="subscribe.mars",
                                  list_archive="archive.mars",
                                  urls="http://mars.mars (MARS site)"
                                  ))
        self.assertEqual(r.status_code, 302)

        group = Group.objects.get(acronym="mars")
        self.assertEqual(group.name, "Mars Not Special Interest Group")
        self.assertEqual(group.parent, area)
        self.assertEqual(group.ad_role().person, ad)
        for k in ("chair", "secr", "techadv"):
            self.assertTrue(group.role_set.filter(name=k, email__address="aread@ietf.org"))
        self.assertTrue(group.role_set.filter(name="delegate", email__address="ad2@ietf.org"))
        self.assertEqual(group.list_email, "mars@mail")
        self.assertEqual(group.list_subscribe, "subscribe.mars")
        self.assertEqual(group.list_archive, "archive.mars")
        self.assertEqual(group.groupurl_set.all()[0].url, "http://mars.mars")
        self.assertEqual(group.groupurl_set.all()[0].name, "MARS site")
        self.assertTrue(os.path.exists(os.path.join(self.charter_dir, "%s-%s.txt" % (group.charter.canonical_name(), group.charter.rev))))

    def test_conclude(self):
        make_test_data()

        group = Group.objects.get(acronym="mars")

        url = urlreverse('ietf.group.edit.conclude', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form textarea[name=instructions]')), 1)
        
        # faulty post
        r = self.client.post(url, dict(instructions="")) # No instructions
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)

        # request conclusion
        mailbox_before = len(outbox)
        r = self.client.post(url, dict(instructions="Test instructions"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(outbox), mailbox_before + 1)
        # the WG remains active until the Secretariat takes action
        group = Group.objects.get(acronym=group.acronym)
        self.assertEqual(group.state_id, "active")

class MilestoneTests(TestCase):
    def create_test_milestones(self):
        draft = make_test_data()

        group = Group.objects.get(acronym="mars")

        m1 = GroupMilestone.objects.create(id=1,
                                           group=group,
                                           desc="Test 1",
                                           due=datetime.date.today(),
                                           resolved="",
                                           state_id="active")
        m1.docs = [draft]

        m2 = GroupMilestone.objects.create(id=2,
                                           group=group,
                                           desc="Test 2",
                                           due=datetime.date.today(),
                                           resolved="",
                                           state_id="charter")
        m2.docs = [draft]

        return (m1, m2, group)

    def last_day_of_month(self, d):
        return datetime.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


    def test_milestone_sets(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(m1.desc in r.content)
        self.assertTrue(m2.desc not in r.content)

        url = urlreverse('group_edit_charter_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(m1.desc not in r.content)
        self.assertTrue(m2.desc in r.content)

    def test_add_milestone(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        milestones_before = GroupMilestone.objects.count()
        events_before = group.groupevent_set.count()
        docs = Document.objects.filter(type="draft").values_list("name", flat=True)

        due = self.last_day_of_month(datetime.date.today() + datetime.timedelta(days=365))

        # faulty post
        r = self.client.post(url, { 'prefix': "m-1",
                                    'm-1-id': "-1",
                                    'm-1-desc': "", # no description
                                    'm-1-due': due.strftime("%B %Y"),
                                    'm-1-resolved': "",
                                    'm-1-docs': ",".join(docs),
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before)

        # add
        mailbox_before = len(outbox)
        r = self.client.post(url, { 'prefix': "m-1",
                                    'm-1-id': "-1",
                                    'm-1-desc': "Test 3",
                                    'm-1-due': due.strftime("%B %Y"),
                                    'm-1-resolved': "",
                                    'm-1-docs': ",".join(docs),
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before + 1)
        self.assertEqual(group.groupevent_set.count(), events_before + 1)

        m = GroupMilestone.objects.get(desc="Test 3")
        self.assertEqual(m.state_id, "active")
        self.assertEqual(m.due, due)
        self.assertEqual(m.resolved, "")
        self.assertEqual(set(m.docs.values_list("name", flat=True)), set(docs))
        self.assertTrue("Added milestone" in m.milestonegroupevent_set.all()[0].desc)
        self.assertEqual(len(outbox),mailbox_before+2)
        self.assertFalse(any('Review Required' in x['Subject'] for x in outbox[-2:]))

    def test_add_milestone_as_chair(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "marschairman", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        milestones_before = GroupMilestone.objects.count()
        events_before = group.groupevent_set.count()
        due = self.last_day_of_month(datetime.date.today() + datetime.timedelta(days=365))

        # add
        mailbox_before = len(outbox)
        r = self.client.post(url, { 'prefix': "m-1",
                                    'm-1-id': -1,
                                    'm-1-desc': "Test 3",
                                    'm-1-due': due.strftime("%B %Y"),
                                    'm-1-resolved': "",
                                    'm-1-docs': "",
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before + 1)

        m = GroupMilestone.objects.get(desc="Test 3")
        self.assertEqual(m.state_id, "review")
        self.assertEqual(group.groupevent_set.count(), events_before + 1)
        self.assertTrue("for review" in m.milestonegroupevent_set.all()[0].desc)
        self.assertEqual(len(outbox),mailbox_before+1)
        self.assertTrue('Review Required' in outbox[-1]['Subject'])
        self.assertFalse(group.list_email in outbox[-1]['To'])

    def test_accept_milestone(self):
        m1, m2, group = self.create_test_milestones()
        m1.state_id = "review"
        m1.save()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "ad", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        events_before = group.groupevent_set.count()

        # add
        r = self.client.post(url, { 'prefix': "m1",
                                    'm1-id': m1.id,
                                    'm1-desc': m1.desc,
                                    'm1-due': m1.due.strftime("%B %Y"),
                                    'm1-resolved': m1.resolved,
                                    'm1-docs': ",".join(m1.docs.values_list("name", flat=True)),
                                    'm1-review': "accept",
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 302)

        m = GroupMilestone.objects.get(pk=m1.pk)
        self.assertEqual(m.state_id, "active")
        self.assertEqual(group.groupevent_set.count(), events_before + 1)
        self.assertTrue("to active from review" in m.milestonegroupevent_set.all()[0].desc)
        
    def test_delete_milestone(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        milestones_before = GroupMilestone.objects.count()
        events_before = group.groupevent_set.count()

        # delete
        r = self.client.post(url, { 'prefix': "m1",
                                    'm1-id': m1.id,
                                    'm1-desc': m1.desc,
                                    'm1-due': m1.due.strftime("%B %Y"),
                                    'm1-resolved': "",
                                    'm1-docs': ",".join(m1.docs.values_list("name", flat=True)),
                                    'm1-delete': "checked",
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before)
        self.assertEqual(group.groupevent_set.count(), events_before + 1)

        m = GroupMilestone.objects.get(pk=m1.pk)
        self.assertEqual(m.state_id, "deleted")
        self.assertTrue("Deleted milestone" in m.milestonegroupevent_set.all()[0].desc)

    def test_edit_milestone(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_edit_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        milestones_before = GroupMilestone.objects.count()
        events_before = group.groupevent_set.count()
        docs = Document.objects.filter(type="draft").values_list("name", flat=True)

        due = self.last_day_of_month(datetime.date.today() + datetime.timedelta(days=365))

        # faulty post
        r = self.client.post(url, { 'prefix': "m1",
                                    'm1-id': m1.id,
                                    'm1-desc': "", # no description
                                    'm1-due': due.strftime("%B %Y"),
                                    'm1-resolved': "",
                                    'm1-docs': ",".join(docs),
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form .has-error')) > 0)
        m = GroupMilestone.objects.get(pk=m1.pk)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before)
        self.assertEqual(m.due, m1.due)

        # edit
        mailbox_before = len(outbox)
        r = self.client.post(url, { 'prefix': "m1",
                                    'm1-id': m1.id,
                                    'm1-desc': "Test 2 - changed",
                                    'm1-due': due.strftime("%B %Y"),
                                    'm1-resolved': "Done",
                                    'm1-resolved_checkbox': "checked",
                                    'm1-docs': ",".join(docs),
                                    'action': "save",
                                    })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(GroupMilestone.objects.count(), milestones_before)
        self.assertEqual(group.groupevent_set.count(), events_before + 1)

        m = GroupMilestone.objects.get(pk=m1.pk)
        self.assertEqual(m.state_id, "active")
        self.assertEqual(m.due, due)
        self.assertEqual(m.resolved, "Done")
        self.assertEqual(set(m.docs.values_list("name", flat=True)), set(docs))
        self.assertTrue("Changed milestone" in m.milestonegroupevent_set.all()[0].desc)
        self.assertEqual(len(outbox), mailbox_before + 2)
        self.assertTrue("Milestones changed" in outbox[-2]["Subject"])
        self.assertTrue(group.ad_role().email.address in str(outbox[-2]))
        self.assertTrue("Milestones changed" in outbox[-1]["Subject"])
        self.assertTrue(group.list_email in str(outbox[-1]))

    def test_reset_charter_milestones(self):
        m1, m2, group = self.create_test_milestones()

        url = urlreverse('group_reset_charter_milestones', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(q('input[name=milestone]').val(), str(m1.pk))

        events_before = group.charter.docevent_set.count()

        # reset
        r = self.client.post(url, dict(milestone=[str(m1.pk)]))
        self.assertEqual(r.status_code, 302)

        self.assertEqual(GroupMilestone.objects.get(pk=m1.pk).state_id, "active")
        self.assertEqual(GroupMilestone.objects.get(pk=m2.pk).state_id, "deleted")
        self.assertEqual(GroupMilestone.objects.filter(due=m1.due, desc=m1.desc, state="charter").count(), 1)

        self.assertEqual(group.charter.docevent_set.count(), events_before + 2) # 1 delete, 1 add

    def test_send_review_needed_reminders(self):
        make_test_data()

        group = Group.objects.get(acronym="mars")
        person = Person.objects.get(user__username="marschairman")

        m1 = GroupMilestone.objects.create(group=group,
                                           desc="Test 1",
                                           due=datetime.date.today(),
                                           resolved="",
                                           state_id="review")
        MilestoneGroupEvent.objects.create(
            group=group, type="changed_milestone",
            by=person, desc='Added milestone "%s"' % m1.desc, milestone=m1,
            time=datetime.datetime.now() - datetime.timedelta(seconds=60))

        # send
        mailbox_before = len(outbox)
        for g in groups_with_milestones_needing_review():
            email_milestone_review_reminder(g)

        self.assertEqual(len(outbox), mailbox_before) # too early to send reminder


        # add earlier added milestone
        m2 = GroupMilestone.objects.create(group=group,
                                           desc="Test 2",
                                           due=datetime.date.today(),
                                           resolved="",
                                           state_id="review")
        MilestoneGroupEvent.objects.create(
            group=group, type="changed_milestone",
            by=person, desc='Added milestone "%s"' % m2.desc, milestone=m2,
            time=datetime.datetime.now() - datetime.timedelta(days=10))

        # send
        mailbox_before = len(outbox)
        for g in groups_with_milestones_needing_review():
            email_milestone_review_reminder(g)

        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue(group.acronym in outbox[-1]["Subject"])
        self.assertTrue(m1.desc in unicode(outbox[-1]))
        self.assertTrue(m2.desc in unicode(outbox[-1]))

    def test_send_milestones_due_reminders(self):
        make_test_data()

        group = Group.objects.get(acronym="mars")

        early_warning_days = 30

        # due dates here aren't aligned on the last day of the month,
        # but everything should still work

        m1 = GroupMilestone.objects.create(group=group,
                                           desc="Test 1",
                                           due=datetime.date.today(),
                                           resolved="Done",
                                           state_id="active")
        m2 = GroupMilestone.objects.create(group=group,
                                           desc="Test 2",
                                           due=datetime.date.today() + datetime.timedelta(days=early_warning_days - 10),
                                           resolved="",
                                           state_id="active")

        # send
        mailbox_before = len(outbox)
        for g in groups_needing_milestones_due_reminder(early_warning_days):
            email_milestones_due(g, early_warning_days)

        self.assertEqual(len(outbox), mailbox_before) # none found

        m1.resolved = ""
        m1.save()

        m2.due = datetime.date.today() + datetime.timedelta(days=early_warning_days)
        m2.save()

        # send
        mailbox_before = len(outbox)
        for g in groups_needing_milestones_due_reminder(early_warning_days):
            email_milestones_due(g, early_warning_days)

        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue(group.acronym in outbox[-1]["Subject"])
        self.assertTrue(m1.desc in unicode(outbox[-1]))
        self.assertTrue(m2.desc in unicode(outbox[-1]))

    def test_send_milestones_overdue_reminders(self):
        make_test_data()

        group = Group.objects.get(acronym="mars")

        # due dates here aren't aligned on the last day of the month,
        # but everything should still work

        m1 = GroupMilestone.objects.create(group=group,
                                           desc="Test 1",
                                           due=datetime.date.today() - datetime.timedelta(days=200),
                                           resolved="Done",
                                           state_id="active")
        m2 = GroupMilestone.objects.create(group=group,
                                           desc="Test 2",
                                           due=datetime.date.today() - datetime.timedelta(days=10),
                                           resolved="",
                                           state_id="active")

        # send
        mailbox_before = len(outbox)
        for g in groups_needing_milestones_overdue_reminder(grace_period=30):
            email_milestones_overdue(g)

        self.assertEqual(len(outbox), mailbox_before) # none found

        m1.resolved = ""
        m1.save()

        m2.due = self.last_day_of_month(datetime.date.today() - datetime.timedelta(days=300))
        m2.save()
        
        # send
        mailbox_before = len(outbox)
        for g in groups_needing_milestones_overdue_reminder(grace_period=30):
            email_milestones_overdue(g)

        self.assertEqual(len(outbox), mailbox_before + 1)
        self.assertTrue(group.acronym in outbox[-1]["Subject"])
        self.assertTrue(m1.desc in unicode(outbox[-1]))
        self.assertTrue(m2.desc in unicode(outbox[-1]))

class CustomizeWorkflowTests(TestCase):
    def test_customize_workflow(self):
        make_test_data()

        group = Group.objects.get(acronym="mars")

        url = urlreverse('ietf.group.edit.customize_workflow', kwargs=dict(group_type=group.type_id, acronym=group.acronym))
        login_testing_unauthorized(self, "secretary", url)

        state = State.objects.get(used=True, type="draft-stream-ietf", slug="wg-lc")
        self.assertTrue(state not in group.unused_states.all())

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q("form.set-state").find("input[name=state][value='%s']" % state.pk).parents("form").find("input[name=active][value='0']")), 1)

        # deactivate state
        r = self.client.post(url,
                             dict(action="setstateactive",
                                  state=state.pk,
                                  active="0"))
        self.assertEqual(r.status_code, 302)
        r = self.client.get(url)
        q = PyQuery(r.content)
        self.assertEqual(len(q("form.set-state").find("input[name=state][value='%s']" % state.pk).parents("form").find("input[name=active][value='1']")), 1)
        group = Group.objects.get(acronym=group.acronym)
        self.assertTrue(state in group.unused_states.all())

        # change next states
        state = State.objects.get(used=True, type="draft-stream-ietf", slug="wg-doc")
        next_states = State.objects.filter(used=True, type=b"draft-stream-ietf", slug__in=["parked", "dead", "wait-wgw", 'sub-pub']).values_list('pk', flat=True)
        r = self.client.post(url,
                             dict(action="setnextstates",
                                  state=state.pk,
                                  next_states=next_states))
        self.assertEqual(r.status_code, 302)
        r = self.client.get(url)
        q = PyQuery(r.content)
        self.assertEqual(len(q("form.set-next-states").find("input[name=state][value='%s']" % state.pk).parents('form').find("input[name=next_states][checked=checked]")), len(next_states))
        transitions = GroupStateTransitions.objects.filter(group=group, state=state)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(set(transitions[0].next_states.values_list("pk", flat=True)), set(next_states))

        # change them back to default
        next_states = state.next_states.values_list("pk", flat=True)
        r = self.client.post(url,
                             dict(action="setnextstates",
                                  state=state.pk,
                                  next_states=next_states))
        self.assertEqual(r.status_code, 302)
        r = self.client.get(url)
        q = PyQuery(r.content)
        transitions = GroupStateTransitions.objects.filter(group=group, state=state)
        self.assertEqual(len(transitions), 0)

        # deactivate tag
        tag = DocTagName.objects.get(slug="w-expert")
        r = self.client.post(url,
                             dict(action="settagactive",
                                  tag=tag.pk,
                                  active="0"))
        self.assertEqual(r.status_code, 302)
        r = self.client.get(url)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form').find('input[name=tag][value="%s"]' % tag.pk).parents("form").find("input[name=active]")), 1)
        group = Group.objects.get(acronym=group.acronym)
        self.assertTrue(tag in group.unused_tags.all())

class EmailAliasesTests(TestCase):

    def setUp(self):
        make_test_data()
        self.group_alias_file = NamedTemporaryFile(delete=False)
        self.group_alias_file.write("""# Generated by hand at 2015-02-12_16:30:52
virtual.ietf.org anything
mars-ads@ietf.org                                                xfilter-mars-ads
expand-mars-ads@virtual.ietf.org                                 aread@ietf.org
mars-chairs@ietf.org                                             xfilter-mars-chairs
expand-mars-chairs@virtual.ietf.org                              mars_chair@ietf.org
ames-ads@ietf.org                                                xfilter-mars-ads
expand-ames-ads@virtual.ietf.org                                 aread@ietf.org
ames-chairs@ietf.org                                             xfilter-mars-chairs
expand-ames-chairs@virtual.ietf.org                              mars_chair@ietf.org
""")
        self.group_alias_file.close()
        settings.GROUP_VIRTUAL_PATH = self.group_alias_file.name

    def tearDown(self):
        os.unlink(self.group_alias_file.name)

    def testNothing(self):
        url = urlreverse('ietf.group.info.email_aliases', kwargs=dict(acronym="mars"))
        r = self.client.get(url)
        self.assertTrue(all([x in r.content for x in ['mars-ads@','mars-chairs@']]))
        self.assertFalse(any([x in r.content for x in ['ames-ads@','ames-chairs@']]))

        url = urlreverse('ietf.group.info.email_aliases', kwargs=dict())
        login_testing_unauthorized(self, "plain", url)
        r = self.client.get(url)
        self.assertTrue(all([x in r.content for x in ['mars-ads@','mars-chairs@','ames-ads@','ames-chairs@']]))

        url = urlreverse('ietf.group.info.email_aliases', kwargs=dict(group_type="wg"))
        r = self.client.get(url)
        self.assertTrue('mars-ads@' in r.content)

        url = urlreverse('ietf.group.info.email_aliases', kwargs=dict(group_type="rg"))
        r = self.client.get(url)
        self.assertFalse('mars-ads@' in r.content)


class AjaxTests(TestCase):
    def test_group_menu_data(self):
        make_test_data()

        r = self.client.get(urlreverse("group_menu_data"))
        self.assertEqual(r.status_code, 200)

        parents = json.loads(r.content)

        area = Group.objects.get(type="area", acronym="farfut")
        self.assertTrue(str(area.id) in parents)

        mars_wg_data = None
        for g in parents[str(area.id)]:
            if g["acronym"] == "mars":
                mars_wg_data = g
                break
        self.assertTrue(mars_wg_data)

        mars_wg = Group.objects.get(acronym="mars")
        self.assertEqual(mars_wg_data["name"], mars_wg.name)

